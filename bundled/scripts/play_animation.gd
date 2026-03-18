@tool
extends Node3D

@export var animation_name: String = ""
@export var autoplay: bool = true
@export var loop: bool = false

var anim_player: AnimationPlayer

func _ready() -> void:
    if Engine.is_editor_hint():
        return
    
    anim_player = get_tree().current_scene.find_child("AnimationPlayer", true, false)
    if anim_player == null:
        push_warning("[AnimationController] No AnimationPlayer found in scene.")
        return
    if autoplay and animation_name != "":
        play_action(animation_name)

func play_action(anim: String) -> void:
	if anim_player == null:
		push_warning("[AnimationController] No AnimationPlayer available.")
		return
	if anim_player.has_animation(anim):
		anim_player.play(anim)
		if loop:
			anim_player.get_animation(anim).loop_mode = Animation.LOOP_LINEAR
	else:
		push_warning("[AnimationController] Animation not found: '%s'. Available: %s" % [anim, str(anim_player.get_animation_list())])

func stop() -> void:
	if anim_player:
		anim_player.stop()
