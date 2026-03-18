@tool
extends LightmapGI

func _enter_tree() -> void:
	call_deferred("_disable_culling")

func _disable_culling() -> void:
	RenderingServer.instance_set_ignore_culling(get_instance(), true)
