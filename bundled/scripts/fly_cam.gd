extends Camera3D
## Simple fly camera for debugging. Attach directly to a Camera3D node.
##
## Controls:
##   W/S: Forward/Backward
##   A/D: Left/Right
##   Q/E: Down/Up
##   Shift: Speed boost
##   Mouse: Look around
##   Right Mouse Button: Hold to enable mouse look

@export_group("Movement")
@export var move_speed: float = 5.0
@export var fast_speed: float = 15.0
@export var acceleration: float = 10.0

@export_group("Mouse Look")
@export var mouse_sensitivity: float = 0.002
@export var hold_to_look: bool = true
@export var rotation_smoothing: float = 20.0  ## Higher = snappier, lower = floatier

# Internal state
var _velocity: Vector3 = Vector3.ZERO
var _yaw: float = 0.0
var _pitch: float = 0.0
var _target_yaw: float = 0.0
var _target_pitch: float = 0.0
var _mouse_look_active: bool = false

func _ready() -> void:
	_yaw = rotation.y
	_pitch = rotation.x
	_target_yaw = _yaw
	_target_pitch = _pitch

	if not hold_to_look:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			if hold_to_look:
				_mouse_look_active = event.pressed
				if event.pressed:
					Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
				else:
					Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

	if event is InputEventMouseMotion:
		if _mouse_look_active or not hold_to_look:
			_target_yaw -= event.relative.x * mouse_sensitivity
			_target_pitch -= event.relative.y * mouse_sensitivity
			_target_pitch = clamp(_target_pitch, deg_to_rad(-89.0), deg_to_rad(89.0))

	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		_mouse_look_active = false

func _process(delta: float) -> void:
	# Smooth rotation toward target
	_yaw = lerp_angle(_yaw, _target_yaw, rotation_smoothing * delta)
	_pitch = lerp_angle(_pitch, _target_pitch, rotation_smoothing * delta)
	rotation = Vector3(_pitch, _yaw, 0.0)

	# Get input direction
	var input_dir := Vector3.ZERO

	if Input.is_key_pressed(KEY_W): input_dir.z -= 1.0
	if Input.is_key_pressed(KEY_S): input_dir.z += 1.0
	if Input.is_key_pressed(KEY_A): input_dir.x -= 1.0
	if Input.is_key_pressed(KEY_D): input_dir.x += 1.0
	if Input.is_key_pressed(KEY_Q): input_dir.y -= 1.0
	if Input.is_key_pressed(KEY_E): input_dir.y += 1.0

	input_dir = input_dir.normalized()

	var direction := Vector3.ZERO
	direction += global_transform.basis.z * input_dir.z
	direction += global_transform.basis.x * input_dir.x
	direction += Vector3.UP * input_dir.y

	var speed := fast_speed if Input.is_key_pressed(KEY_SHIFT) else move_speed
	var target_velocity := direction * speed
	_velocity = _velocity.lerp(target_velocity, acceleration * delta)

	global_position += _velocity * delta

func reset(pos: Vector3, look_at_target: Vector3 = Vector3.ZERO) -> void:
	global_position = pos
	look_at(look_at_target, Vector3.UP)
	_yaw = rotation.y
	_pitch = rotation.x
	_target_yaw = _yaw
	_target_pitch = _pitch
	_velocity = Vector3.ZERO