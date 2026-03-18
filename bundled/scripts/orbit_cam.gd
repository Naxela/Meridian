extends Camera3D
## Simple orbit camera for debugging. Attach directly to a Camera3D node.
##
## Controls:
##   Left Mouse + Drag: Rotate around target
##   Right Mouse + Drag: Pan
##   Mouse Wheel: Zoom in/out

@export var target: Vector3 = Vector3.ZERO
@export var distance: float = 5.0
@export var min_distance: float = 1.0
@export var max_distance: float = 50.0

@export_group("Sensitivity")
@export var rotate_speed: float = 0.005
@export var pan_speed: float = 0.01
@export var zoom_speed: float = 0.5

@export_group("Limits")
@export var min_pitch: float = -89.0  ## Degrees
@export var max_pitch: float = 89.0   ## Degrees

# Internal state
var _yaw: float = 0.0    # Horizontal rotation (radians)
var _pitch: float = 0.0  # Vertical rotation (radians)
var _is_rotating: bool = false
var _is_panning: bool = false


func _ready() -> void:
	# Initialize angles from current camera position
	var offset = global_position - target
	distance = offset.length()
	if distance > 0.001:
		_yaw = atan2(offset.x, offset.z)
		_pitch = asin(clamp(offset.y / distance, -1.0, 1.0))
	_update_camera()


func _unhandled_input(event: InputEvent) -> void:
	# Mouse button events
	if event is InputEventMouseButton:
		match event.button_index:
			MOUSE_BUTTON_LEFT:
				_is_rotating = event.pressed
			MOUSE_BUTTON_RIGHT:
				_is_panning = event.pressed
			MOUSE_BUTTON_WHEEL_UP:
				if event.pressed:
					distance = clamp(distance - zoom_speed, min_distance, max_distance)
					_update_camera()
			MOUSE_BUTTON_WHEEL_DOWN:
				if event.pressed:
					distance = clamp(distance + zoom_speed, min_distance, max_distance)
					_update_camera()
	
	# Mouse motion
	if event is InputEventMouseMotion:
		if _is_rotating:
			_yaw -= event.relative.x * rotate_speed
			_pitch += event.relative.y * rotate_speed
			_pitch = clamp(_pitch, deg_to_rad(min_pitch), deg_to_rad(max_pitch))
			_update_camera()
		
		if _is_panning:
			var right = global_transform.basis.x
			var up = global_transform.basis.y
			target -= right * event.relative.x * pan_speed * distance * 0.1
			target += up * event.relative.y * pan_speed * distance * 0.1
			_update_camera()


func _update_camera() -> void:
	# Calculate position from spherical coordinates
	var offset = Vector3(
		sin(_yaw) * cos(_pitch),
		sin(_pitch),
		cos(_yaw) * cos(_pitch)
	) * distance
	
	global_position = target + offset
	look_at(target, Vector3.UP)


## Reset camera to initial state
func reset(new_target: Vector3 = Vector3.ZERO, new_distance: float = 5.0) -> void:
	target = new_target
	distance = new_distance
	_yaw = 0.0
	_pitch = 0.0
	_update_camera()


## Focus on a specific position
func focus_on(pos: Vector3, keep_distance: bool = true) -> void:
	target = pos
	if not keep_distance:
		distance = 5.0
	_update_camera()
