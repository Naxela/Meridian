@tool
extends Node

# Server for receiving from Blender
var server: TCPServer
var receive_client: StreamPeerTCP
var receive_port: int = 15702
var message_buffer: String = ""

# Client for sending to Blender
var send_client: StreamPeerTCP
var send_port: int = 15703
var send_connected: bool = false

# Track last known transforms
var last_transforms: Dictionary = {}
var last_send_time: Dictionary = {}
var SEND_INTERVAL: float = 0.016

# Editor tracking
var editor_interface: EditorInterface = null
var last_check_time: float = 0.0
var CHECK_INTERVAL: float = 0.016

# Debug
var debug_mode: bool = true  # Set to true for verbose logging
var changes_detected: int = 0

func set_editor_interface(ei: EditorInterface):
	editor_interface = ei
	print("✓ EditorInterface set")

func _ready():
	print("\n=== Live Link Server Starting ===")
	
	# Start server for receiving
	server = TCPServer.new()
	if server.listen(receive_port) == OK:
		print("✓ Receiving server started on port %d" % receive_port)
	else:
		push_error("✗ Failed to start receiving server")
	
	# Connect client for sending
	_connect_to_blender()

func _connect_to_blender():
	print("⟳ Connecting to Blender's server on port %d..." % send_port)
	send_client = StreamPeerTCP.new()
	var err = send_client.connect_to_host("127.0.0.1", send_port)
	if err == OK:
		print("  Connection initiated...")
	else:
		push_error("✗ Failed to connect: %d" % err)

func _process(delta):
	if not server:
		return
	
	# === POLL SEND CLIENT ===
	if send_client:
		send_client.poll()
		var status = send_client.get_status()
		
		if status == StreamPeerTCP.STATUS_CONNECTED:
			if not send_connected:
				send_connected = true
				print("✓✓✓ SENDING CONNECTION ESTABLISHED! ✓✓✓")
				print("    Bidirectional sync is now active!")
		elif status == StreamPeerTCP.STATUS_ERROR:
			if send_connected:
				print("✗ Sending connection lost")
			send_connected = false
			send_client = null
	
	# === RECEIVE FROM BLENDER ===
	if server.is_connection_available():
		receive_client = server.take_connection()
		message_buffer = ""
		print("✓ Blender connected for receiving")
	
	if receive_client:
		var status = receive_client.get_status()
		
		if status == StreamPeerTCP.STATUS_CONNECTED:
			for i in range(10):
				var available = receive_client.get_available_bytes()
				if available > 0:
					if debug_mode:
						print("\n[BLENDER→GODOT] Received %d bytes" % available)
					
					var new_data = receive_client.get_utf8_string(available)
					message_buffer += new_data
					_process_receive_buffer()
				else:
					break
		elif status == StreamPeerTCP.STATUS_NONE or status == StreamPeerTCP.STATUS_ERROR:
			print("✗ Receiving connection lost")
			receive_client = null
			message_buffer = ""
	
	# === CHECK FOR GODOT CHANGES TO SEND ===
	if send_connected:
		var current_time = Time.get_ticks_msec() / 1000.0
		if current_time - last_check_time >= CHECK_INTERVAL:
			_check_and_send_changes()
			last_check_time = current_time
	
	changes_detected += 1

func _process_receive_buffer():
	while "\n" in message_buffer:
		var newline_pos = message_buffer.find("\n")
		var json_str = message_buffer.substr(0, newline_pos)
		message_buffer = message_buffer.substr(newline_pos + 1)
		
		if json_str.strip_edges() != "":
			_handle_blender_update(json_str)

func _handle_blender_update(json_str: String):
	if debug_mode:
		print("[BLENDER→GODOT] Parsing JSON...")
	
	var json = JSON.new()
	if json.parse(json_str) != OK:
		if debug_mode:
			print("  ✗ JSON parse error")
		return
	
	var data = json.data
	var node_name = data.get("name", "")
	
	if debug_mode:
		print("  Node: %s" % node_name)
	
	if not editor_interface:
		return
	
	var edited_scene = editor_interface.get_edited_scene_root()
	if not edited_scene:
		return
	
	var node = _find_node_by_name(edited_scene, node_name)
	if not node or not node is Node3D:
		if debug_mode:
			print("  ✗ Node '%s' not found or not Node3D" % node_name)
		return
	
	if data.has("position") and data.has("basis_x"):
		var pos = data["position"]
		var basis_x = data["basis_x"]
		var basis_y = data["basis_y"]
		var basis_z = data["basis_z"]
		
		var transform = Transform3D()
		transform.basis.x = Vector3(basis_x[0], basis_x[1], basis_x[2])
		transform.basis.y = Vector3(basis_y[0], basis_y[1], basis_y[2])
		transform.basis.z = Vector3(basis_z[0], basis_z[1], basis_z[2])
		transform.origin = Vector3(pos[0], pos[1], pos[2])
		transform.basis = transform.basis.inverse()
		
		node.transform = transform
		last_transforms[node_name] = transform
		
		if debug_mode:
			print("  ✓ Transform applied: pos=%s" % transform.origin)

func _check_and_send_changes():
	if not send_connected or not editor_interface:
		return
	
	var edited_scene = editor_interface.get_edited_scene_root()
	if not edited_scene:
		return
	
	_check_node_for_changes(edited_scene)

func _check_node_for_changes(node: Node):
	if node is Node3D:
		var current_transform = node.transform
		var node_name = node.name
		
		if not last_transforms.has(node_name) or not _transforms_equal(last_transforms[node_name], current_transform):
			var current_time = Time.get_ticks_msec() / 1000.0
			if not last_send_time.has(node_name) or (current_time - last_send_time[node_name]) >= SEND_INTERVAL:
				if debug_mode:
					print("\n[GODOT→BLENDER] Sending '%s'" % node_name)
				_send_transform_to_blender(node)
				last_transforms[node_name] = current_transform
				last_send_time[node_name] = current_time
	
	for child in node.get_children():
		_check_node_for_changes(child)

func _transforms_equal(t1: Transform3D, t2: Transform3D) -> bool:
	var EPSILON = 0.0001
	return t1.origin.distance_to(t2.origin) < EPSILON and \
	       t1.basis.x.distance_to(t2.basis.x) < EPSILON and \
	       t1.basis.y.distance_to(t2.basis.y) < EPSILON and \
	       t1.basis.z.distance_to(t2.basis.z) < EPSILON

func _send_transform_to_blender(node: Node3D):
	if not send_client or send_client.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		return
	
	var transform = node.transform
	var basis = transform.basis.inverse()
	
	var message = {
		"name": node.name,
		"type": "MESH",
		"position": [transform.origin.x, transform.origin.y, transform.origin.z],
		"basis_x": [basis.x.x, basis.x.y, basis.x.z],
		"basis_y": [basis.y.x, basis.y.y, basis.y.z],
		"basis_z": [basis.z.x, basis.z.y, basis.z.z]
	}
	
	var json_str = JSON.stringify(message) + "\n"
	var result = send_client.put_data(json_str.to_utf8_buffer())
	
	if result != OK:
		if debug_mode:
			print("  ✗ Failed to send: %d" % result)
	elif debug_mode:
		print("  ✓ Sent successfully")

func _find_node_by_name(root: Node, node_name: String) -> Node:
	if root.name == node_name:
		return root
	for child in root.get_children():
		var result = _find_node_by_name(child, node_name)
		if result:
			return result
	return null

func _exit_tree():
	if receive_client:
		receive_client.disconnect_from_host()
	if send_client:
		send_client.disconnect_from_host()
	if server:
		server.stop()