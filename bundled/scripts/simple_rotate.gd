extends Node3D

@export var rotation_speed: float = 1.0

func _process(delta):
	rotate_y(rotation_speed * delta)
