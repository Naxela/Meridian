@tool
## Attach this script to the atmosphere MeshInstance3D.
## Syncs the shader's sun_direction uniform with a DirectionalLight3D node.
## Works both in-editor and at runtime thanks to @tool.
extends MeshInstance3D

@export var sun_light : DirectionalLight3D

func _process(_delta: float) -> void:
	if not sun_light:
		return

	var mat : ShaderMaterial = null

	# Check surface override first (most common in practice)
	if get_surface_override_material_count() > 0:
		mat = get_surface_override_material(0) as ShaderMaterial

	# Fall back to the mesh's own material
	if not mat and mesh:
		mat = mesh.surface_get_material(0) as ShaderMaterial

	# Fall back to material_override (set on the MeshInstance3D itself)
	if not mat:
		mat = material_override as ShaderMaterial

	if mat:
		mat.set_shader_parameter("sun_direction", sun_light.global_basis.z)
