@tool
extends EditorPlugin

var live_link_node: Node

func _enter_tree():
	live_link_node = preload("res://addons/blender_livelink/live_link_server.gd").new()
	# Pass the EditorInterface to the node
	live_link_node.set_editor_interface(get_editor_interface())
	add_child(live_link_node)
	print("Blender Live Link (Bidirectional) enabled")

func _exit_tree():
	if live_link_node:
		live_link_node.queue_free()
	print("Blender Live Link disabled")
