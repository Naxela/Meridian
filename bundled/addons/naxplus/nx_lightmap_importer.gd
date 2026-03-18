@tool
extends EditorPlugin

## Meridian Utilities — Godot 4.6 Editor Plugin
##
## Reads pre-baked HDR lightmap atlases + manifest.json produced by Blender,
## builds a LightmapGIData resource (Texture2DArray + user registrations),
## and assigns it to a LightmapGI node in the scene.  No custom shaders needed.

# ── Configuration (loaded from res://scene_config.json) ──────────────────────
var scene_name: String = "exported_scene"
var auto_close_after_automation: bool = true
var script_assignments: Dictionary = {}
var lightmap_bicubic_filtering: bool = false
var lightmap_mode: String = "atlas"  # "atlas" or "individual"

# ── UI ───────────────────────────────────────────────────────────────────────
var popup_menu: PopupMenu

# ── Constants ────────────────────────────────────────────────────────────────
const LIGHTMAPS_DIR      := "res://assets/lightmaps"
const LIGHTMAPS_DIR_ALT  := "res://assets/Lightmaps"
const MANIFEST_FILE      := "manifest.json"
const FLAG_LIGHTMAPS     := "res://.lightmaps_applied"
const FLAG_SCRIPTS       := "res://.scripts_pending"

# ─────────────────────────────────────────────────────────────────────────────
#  Plugin lifecycle
# ─────────────────────────────────────────────────────────────────────────────

func _enter_tree():
	_load_scene_config()
	_build_menu()

	# Skip automation in headless / import mode
	if DisplayServer.get_name() == "headless":
		print("[Meridian] Headless mode — skipping automation")
		return

	if not FileAccess.file_exists(FLAG_LIGHTMAPS):
		print("[Meridian] First run — will apply lightmaps + scripts")
		await get_tree().process_frame
		await get_tree().process_frame
		call_deferred("_run_full_setup")
	elif FileAccess.file_exists(FLAG_SCRIPTS):
		print("[Meridian] Scripts pending — will apply scripts only")
		await get_tree().process_frame
		await get_tree().process_frame
		call_deferred("_run_script_setup")


func _exit_tree():
	remove_tool_menu_item("Meridian Utilities")
	if popup_menu:
		popup_menu.queue_free()
		popup_menu = null

# ─────────────────────────────────────────────────────────────────────────────
#  Menu
# ─────────────────────────────────────────────────────────────────────────────

func _build_menu():
	popup_menu = PopupMenu.new()
	popup_menu.add_item("Apply Lightmaps (selection)", 0)
	popup_menu.add_item("Apply Lightmaps (whole scene)", 1)
	popup_menu.add_separator()
	popup_menu.add_item("Attach Scripts (current scene)", 2)
	popup_menu.add_item("Update Reflection Probes", 3)
	popup_menu.add_item("Set Render Scale to 4.0", 4)
	popup_menu.id_pressed.connect(_on_menu_item_pressed)
	add_tool_submenu_item("Meridian Utilities", popup_menu)


func _on_menu_item_pressed(id: int):
	match id:
		0: _apply_lightmaps_selection()
		1: _apply_lightmaps_scene()
		2: _attach_scripts_menu()
		3: _update_reflection_probes()
		4: _set_render_scale()

# ─────────────────────────────────────────────────────────────────────────────
#  Config
# ─────────────────────────────────────────────────────────────────────────────

func _load_scene_config():
	var config_path := "res://scene_config.json"
	if not FileAccess.file_exists(config_path):
		print("[Meridian] No scene_config.json — using defaults")
		return

	var file := FileAccess.open(config_path, FileAccess.READ)
	if file == null:
		push_warning("[Meridian] Could not open scene_config.json")
		return

	var json := JSON.new()
	if json.parse(file.get_as_text()) != OK:
		push_warning("[Meridian] Failed to parse scene_config.json")
		return
	file.close()

	var data: Dictionary = json.data
	if data.has("scene_name"):
		scene_name = data["scene_name"]
	if data.has("auto_close_after_automation"):
		auto_close_after_automation = data["auto_close_after_automation"]
	if data.has("script_assignments"):
		script_assignments = data["script_assignments"]
	if data.has("lightmap_bicubic_filtering"):
		lightmap_bicubic_filtering = data["lightmap_bicubic_filtering"]
	if data.has("lightmap_mode"):
		lightmap_mode = data["lightmap_mode"]

	print("[Meridian] Config loaded — scene: %s, scripts: %d, auto_close: %s, lm_mode: %s" % [
		scene_name, script_assignments.size(), auto_close_after_automation, lightmap_mode
	])

# ─────────────────────────────────────────────────────────────────────────────
#  Lightmap manifest loading
# ─────────────────────────────────────────────────────────────────────────────

func _load_manifest() -> Dictionary:
	"""Returns { "ext": String, "lightmaps": Dictionary } or empty on failure."""
	for dir in [LIGHTMAPS_DIR, LIGHTMAPS_DIR_ALT]:
		var path: String = str(dir) + "/" + MANIFEST_FILE
		if not FileAccess.file_exists(path):
			continue
		var file := FileAccess.open(path, FileAccess.READ)
		if file == null:
			continue
		var json := JSON.new()
		if json.parse(file.get_as_text()) == OK:
			file.close()
			print("[Meridian] Manifest loaded: %s (%d entries)" % [path, json.data.lightmaps.size()])
			return json.data
		file.close()

	push_error("[Meridian] Could not load lightmap manifest")
	return {}

# ─────────────────────────────────────────────────────────────────────────────
#  Core: Build LightmapGIData from pre-baked atlases
# ─────────────────────────────────────────────────────────────────────────────

func _build_lightmap_data(root: Node, lmgi: LightmapGI) -> LightmapGIData:
	var manifest := _load_manifest()
	if manifest.is_empty():
		return null

	var ext: String = manifest.ext
	var lightmaps: Dictionary = manifest.lightmaps

	# 1. Discover unique atlas names → these become slices in the Texture2DArray
	var atlas_names: Array[String] = []
	for obj_name in lightmaps:
		var atlas: String = lightmaps[obj_name]
		if atlas not in atlas_names:
			atlas_names.append(atlas)

	# 2. Load each atlas as a raw Image (not via ResourceLoader — match working pattern)
	var images: Array[Image] = []
	for atlas_name in atlas_names:
		var img := Image.new()
		var load_err := OK
		for dir in [LIGHTMAPS_DIR, LIGHTMAPS_DIR_ALT]:
			var path: String = "%s/%s.%s" % [dir, atlas_name, ext]
			load_err = img.load(ProjectSettings.globalize_path(path))
			if load_err == OK:
				print("[Meridian] Loaded atlas: %s" % path)
				break

		if load_err != OK:
			push_error("[Meridian] Failed to load atlas: %s.%s" % [atlas_name, ext])
			return null
		images.append(img)

	print("[Meridian] Building Texture2DArray: %d slices, %dx%d" % [
		images.size(), images[0].get_width(), images[0].get_height()
	])

	# 3. Create the layered texture
	var tex_array := Texture2DArray.new()
	tex_array.create_from_images(images)

	# 4. Build the flat user_data array for _set_user_data()
	#    Format: [NodePath, Rect2, slice_index, sub_instance, ...] repeating per mesh
	var data := LightmapGIData.new()
	var user_data := []

	var registered := 0
	var skipped := 0
	for obj_name in lightmaps:
		var atlas_name: String = lightmaps[obj_name]
		var slice_index: int = atlas_names.find(atlas_name)

		# Godot's glTF importer replaces "." with "_"
		var node_name := str(obj_name).replace(".", "_")
		var node := _find_node_by_name(root, node_name)

		if node == null or not (node is MeshInstance3D):
			push_warning("[Meridian] No MeshInstance3D for '%s' (node '%s')" % [obj_name, node_name])
			skipped += 1
			continue

		var mesh_inst: MeshInstance3D = node
		mesh_inst.gi_mode = GeometryInstance3D.GI_MODE_STATIC
		_apply_gdprops(mesh_inst)

		# Path relative to the LightmapGI node
		var rel_path := lmgi.get_path_to(mesh_inst)
		user_data.append(NodePath(rel_path))
		user_data.append(Rect2(0, 0, 1, 1))
		user_data.append(slice_index)
		user_data.append(-1)  # sub_instance: -1 = whole mesh

		print("[Meridian]   user: %s → slice %d (path: %s)" % [obj_name, slice_index, rel_path])
		registered += 1

	# Use the internal APIs that actually work
	data._set_user_data(user_data)
	data.set_lightmap_textures([tex_array])

	print("[Meridian] Lightmap users: %d registered, %d skipped" % [registered, skipped])
	return data

# ─────────────────────────────────────────────────────────────────────────────
#  Apply LightmapGIData to the scene
# ─────────────────────────────────────────────────────────────────────────────

func _apply_lightmap_data(root: Node) -> bool:
	# Find existing LightmapGI or create one FIRST,
	# so we can compute paths relative to it
	var lmgi: LightmapGI = _find_first_child_of_type(root, "LightmapGI")

	if lmgi == null:
		lmgi = LightmapGI.new()
		lmgi.name = "LightmapGI"
		root.add_child(lmgi)
		lmgi.owner = root
		print("[Meridian] Created new LightmapGI node")

	var data := _build_lightmap_data(root, lmgi)
	if data == null:
		push_error("[Meridian] Failed to build lightmap data")
		return false

	# Save to disk first, then load back — this is required for Godot
	# to properly internalize the resource
	var save_path := "res://assets/lightmaps/lightmap_data.lmbake"
	var save_err := ResourceSaver.save(data, save_path)
	if save_err != OK:
		push_error("[Meridian] Could not save LightmapGIData: %s" % error_string(save_err))
		return false
	print("[Meridian] Saved LightmapGIData to: ", save_path)

	# Load it back from disk and assign
	lmgi.light_data = load(save_path)

	# Attach culling fix script
	var culling_script_path := "res://scripts/disable_culling.gd"
	if ResourceLoader.exists(culling_script_path):
		lmgi.set_script(load(culling_script_path))
		print("[Meridian] Attached disable_culling.gd to LightmapGI")
	else:
		push_warning("[Meridian] disable_culling.gd not found at: %s" % culling_script_path)

	# Mark scene as modified
	EditorInterface.mark_scene_as_unsaved()

	return true

# ─────────────────────────────────────────────────────────────────────────────
#  Individual lightmap mode (StandardPlusAuto shader per object)
# ─────────────────────────────────────────────────────────────────────────────

func _apply_lightmaps_individual(root: Node) -> bool:
	var manifest := _load_manifest()
	if manifest.is_empty():
		return false

	var ext: String = manifest.ext
	var lightmaps: Dictionary = manifest.lightmaps

	var shader_path := "res://assets/StandardPlusAuto.gdshader"
	if not ResourceLoader.exists(shader_path):
		push_error("[Meridian] StandardPlusAuto.gdshader not found at: %s" % shader_path)
		return false

	var shader: Shader = load(shader_path)
	var applied := 0
	var skipped := 0

	for obj_name in lightmaps:
		var lightmap_file: String = lightmaps[obj_name]
		var node_name := str(obj_name).replace(".", "_")
		var node := _find_node_by_name(root, node_name)

		if node == null or not (node is MeshInstance3D):
			push_warning("[Meridian] No MeshInstance3D for '%s' (node '%s')" % [obj_name, node_name])
			skipped += 1
			continue

		var mesh_inst: MeshInstance3D = node

		# Load lightmap texture
		var lm_tex: Texture2D = null
		for dir in [LIGHTMAPS_DIR, LIGHTMAPS_DIR_ALT]:
			var lm_path: String = "%s/%s.%s" % [dir, lightmap_file, ext]
			if ResourceLoader.exists(lm_path):
				lm_tex = load(lm_path)
				print("[Meridian] Loaded individual lightmap: %s" % lm_path)
				break

		if lm_tex == null:
			push_warning("[Meridian] Lightmap texture not found for '%s': %s.%s" % [obj_name, lightmap_file, ext])
			skipped += 1
			continue

		# Build ShaderMaterial, copying albedo from existing surface material where possible
		var mat := ShaderMaterial.new()
		mat.shader = shader

		var existing_mat: Material = mesh_inst.get_surface_override_material(0)
		if existing_mat == null and mesh_inst.mesh != null and mesh_inst.mesh.get_surface_count() > 0:
			existing_mat = mesh_inst.mesh.surface_get_material(0)

		if existing_mat is StandardMaterial3D:
			var std: StandardMaterial3D = existing_mat
			if std.albedo_texture:
				mat.set_shader_parameter("texture_albedo", std.albedo_texture)
			mat.set_shader_parameter("albedo", std.albedo_color)
			mat.set_shader_parameter("roughness", std.roughness)
			mat.set_shader_parameter("metallic", std.metallic)
			mat.set_shader_parameter("specular", std.metallic_specular)

		mat.set_shader_parameter("texture_lightmap", lm_tex)
		mat.set_shader_parameter("use_bicubic_lightmap", lightmap_bicubic_filtering)
		mat.set_shader_parameter("lightmap_strength", 1.0)

		mesh_inst.set_surface_override_material(0, mat)
		mesh_inst.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		_apply_gdprops(mesh_inst)

		print("[Meridian] Individual LM applied: %s → %s.%s" % [obj_name, lightmap_file, ext])
		applied += 1

	print("[Meridian] Individual lightmaps: %d applied, %d skipped" % [applied, skipped])
	EditorInterface.mark_scene_as_unsaved()
	return applied > 0


## Dispatch to atlas or individual mode based on scene_config.
func _apply_lightmaps(root: Node) -> bool:
	if lightmap_mode == "individual":
		return _apply_lightmaps_individual(root)
	return _apply_lightmap_data(root)

# ─────────────────────────────────────────────────────────────────────────────
#  Menu actions
# ─────────────────────────────────────────────────────────────────────────────

func _apply_lightmaps_selection():
	"""Apply lightmaps only for the currently selected mesh instances."""
	var editor := get_editor_interface()
	var root := editor.get_edited_scene_root()
	if root == null:
		push_error("[Meridian] No scene open")
		return

	# For selection-based application we still build the full data,
	# but we could filter — for now, apply to the whole scene.
	# The LightmapGI approach is scene-wide by nature.
	if _apply_lightmaps(root):
		print("[Meridian] Lightmaps applied — remember to save the scene")


func _apply_lightmaps_scene():
	"""Apply lightmaps to the entire current scene."""
	var editor := get_editor_interface()
	var root := editor.get_edited_scene_root()
	if root == null:
		push_error("[Meridian] No scene open")
		return

	if _apply_lightmaps(root):
		print("[Meridian] Lightmaps applied to scene — remember to save")

# ─────────────────────────────────────────────────────────────────────────────
#  Script attachment
# ─────────────────────────────────────────────────────────────────────────────

func _attach_scripts_menu():
	var root := get_editor_interface().get_edited_scene_root()
	if root == null:
		push_error("[Meridian] No scene open")
		return

	var count := _attach_scripts_recursive(root)
	print("[Meridian] Script attachment complete: %d scripts attached" % count)


func _attach_scripts_recursive(node: Node) -> int:
	var count := 0

	if script_assignments.has(node.name):
		var script_path: String = "res://scripts/" + script_assignments[node.name]
		if ResourceLoader.exists(script_path):
			var scr = load(script_path)
			if scr:
				node.set_script(scr)
				print("[Meridian]   + script: %s → %s" % [node.name, script_assignments[node.name]])
				count += 1
		else:
			push_warning("[Meridian]   Script not found: %s" % script_path)
	else:
		# Remove managed scripts that are no longer in assignments
		var current_script = node.get_script()
		if current_script and current_script.resource_path.begins_with("res://scripts/"):
			node.set_script(null)
			print("[Meridian]   - removed script from: %s" % node.name)

	for child in node.get_children():
		count += _attach_scripts_recursive(child)

	return count

# ─────────────────────────────────────────────────────────────────────────────
#  Reflection probes
# ─────────────────────────────────────────────────────────────────────────────

func _update_reflection_probes():
	var root := get_editor_interface().get_edited_scene_root()
	if root == null:
		push_error("[Meridian] No scene open")
		return

	var probes: Array[ReflectionProbe] = []
	_collect_nodes_of_type(root, "ReflectionProbe", probes)

	for probe in probes:
		probe.update_mode = ReflectionProbe.UPDATE_ALWAYS
		await get_tree().process_frame
		probe.update_mode = ReflectionProbe.UPDATE_ONCE
		print("[Meridian] Refreshed probe: ", probe.name)

	print("[Meridian] Reflection probes refreshed: %d" % probes.size())

# ─────────────────────────────────────────────────────────────────────────────
#  Render scale
# ─────────────────────────────────────────────────────────────────────────────

func _set_render_scale():
	ProjectSettings.set_setting("rendering/scaling_3d/scale", 4.0)
	ProjectSettings.save()
	print("[Meridian] Render scale set to 4.0")

# ─────────────────────────────────────────────────────────────────────────────
#  Automation (runs on plugin load when flag files are absent)
# ─────────────────────────────────────────────────────────────────────────────

func _run_full_setup():
	print("[Meridian] === Full Scene Setup ===")
	var editor := get_editor_interface()
	await get_tree().create_timer(0.5).timeout

	# Always operate on main.tscn so the LightmapGI node lives there and the
	# node paths in the .lmbake are computed relative to that scene's hierarchy
	# (e.g. ../AtlasTest/A rather than ../A which would be wrong for main.tscn).
	var scene_path: String = "res://scenes/main.tscn"
	if not ResourceLoader.exists(scene_path):
		push_error("[Meridian] Scene not found: " + scene_path)
		return

	editor.open_scene_from_path(scene_path)
	await get_tree().create_timer(1.0).timeout

	var root := editor.get_edited_scene_root()
	if root == null:
		push_error("[Meridian] Failed to load scene")
		return

	# 1. Attach scripts (cameras/lights that live directly in main.tscn)
	var script_count := _attach_scripts_recursive(root)
	print("[Meridian] Scripts attached: %d" % script_count)

	# 2. Apply lightmaps (mode-aware: atlas or individual)
	var lm_ok := _apply_lightmaps(root)
	if not lm_ok:
		push_error("[Meridian] Lightmap application failed")

	# 3. Save main.tscn (already open — no scene switch needed)
	await get_tree().create_timer(1.0).timeout
	var result := editor.save_scene()
	if result != OK:
		push_error("[Meridian] Failed to save scene")
	else:
		print("[Meridian] Scene saved")

	# 4. Write flag
	var flag := FileAccess.open(FLAG_LIGHTMAPS, FileAccess.WRITE)
	if flag:
		flag.store_string("Applied: " + Time.get_datetime_string_from_system())
		flag.close()

	print("[Meridian] === FULL SETUP COMPLETE ===")

	if auto_close_after_automation:
		print("[Meridian] Auto-closing editor...")
		await get_tree().create_timer(0.5).timeout
		get_tree().quit()


func _run_script_setup():
	print("[Meridian] === Script-Only Setup ===")
	var editor := get_editor_interface()
	await get_tree().create_timer(0.5).timeout

	var scene_path: String = "res://scenes/%s.tscn" % scene_name
	if not ResourceLoader.exists(scene_path):
		push_error("[Meridian] Scene not found: " + scene_path)
		return

	editor.open_scene_from_path(scene_path)
	await get_tree().create_timer(1.0).timeout

	var root := editor.get_edited_scene_root()
	if root == null:
		push_error("[Meridian] Failed to load scene")
		return

	var count := _attach_scripts_recursive(root)
	print("[Meridian] Scripts applied: %d" % count)

	await get_tree().create_timer(0.5).timeout
	var result := editor.save_scene()
	if result == OK:
		print("[Meridian] Scene saved")
	else:
		push_error("[Meridian] Failed to save scene")

	DirAccess.remove_absolute(FLAG_SCRIPTS)
	editor.open_scene_from_path("res://scenes/main.tscn")

	print("[Meridian] === SCRIPT SETUP COMPLETE ===")

	if auto_close_after_automation:
		print("[Meridian] Auto-closing editor...")
		await get_tree().create_timer(0.5).timeout
		get_tree().quit()

# ─────────────────────────────────────────────────────────────────────────────
#  Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

func _find_node_by_name(node: Node, target: String) -> Node:
	if node.name == target:
		return node
	for child in node.get_children():
		var result := _find_node_by_name(child, target)
		if result:
			return result
	return null


func _find_first_child_of_type(node: Node, type_name: String) -> Node:
	for child in node.get_children():
		if child.get_class() == type_name:
			return child
		var result := _find_first_child_of_type(child, type_name)
		if result:
			return result
	return null


func _collect_nodes_of_type(node: Node, type_name: String, out: Array):
	if node.get_class() == type_name:
		out.append(node)
	for child in node.get_children():
		_collect_nodes_of_type(child, type_name, out)


func _apply_gdprops(mesh: MeshInstance3D):
	"""Check for GDProps metadata and apply layer overrides."""
	var gd_props = null

	if mesh.has_meta("GDProps"):
		gd_props = mesh.get_meta("GDProps")
	elif mesh.has_meta("extras"):
		var extras = mesh.get_meta("extras")
		if extras is Dictionary and extras.has("GDProps"):
			gd_props = extras["GDProps"]

	if gd_props is Array and "reflective" in gd_props:
		mesh.layers = 2  # Layer 2 only
		print("[Meridian] Layer 2 (reflective): ", mesh.name)
