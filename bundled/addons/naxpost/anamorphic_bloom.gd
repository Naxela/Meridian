@tool
extends CompositorEffect
class_name AnamorphicBloom

## Anamorphic Bloom CompositorEffect for Godot 4.3+
##
## A multi-pass, mip-chain based anamorphic bloom effect using compute shaders.
## Produces directional bloom streaks (horizontal or vertical) similar to
## Cyberpunk 2077, Alien Isolation, etc.
##
## Includes all features from Godot's native glow system plus anamorphic extras.
##
## SETUP:
## 1. Place all .glsl files alongside this script in your project
## 2. Create a Compositor resource on your WorldEnvironment or Camera3D
## 3. Add this effect to the compositor's effects array
## 4. Tweak the exported parameters in the inspector
##
## PIPELINE OVERVIEW (per frame):
##   Pass 1 - Prefilter:  Extract bright pixels above threshold (full res -> half res)
##   Pass 2 - Downsample: Progressive downsample through mip chain
##   Pass 3 - Blur:       1D directional Gaussian blur at each mip level
##   Pass 4 - Upsample:   Progressive upsample + weighted blend back up the chain
##   Pass 5 - Composite:  Blend final bloom result onto the scene color buffer

# ─── Exported Parameters ─────────────────────────────────────────────────────

@export_group("Bloom")
## Overall intensity of the bloom effect (0 = off).
@export_range(0.0, 5.0, 0.01) var intensity: float = 0.3
## Luminance threshold - pixels below this brightness won't bloom.
## Equivalent to Godot's HDR Threshold.
@export_range(0.0, 10.0, 0.01) var threshold: float = 1.0
## Soft knee for threshold transition (0 = hard cutoff, 1 = very soft).
@export_range(0.0, 1.0, 0.01) var soft_knee: float = 0.5
## Pre-multiplier on input luminance before thresholding.
## Higher values = more of the scene contributes to bloom.
## Equivalent to Godot's Strength.
@export_range(0.0, 2.0, 0.01) var strength: float = 1.0
## Overall mix factor (0 = no bloom visible, 1 = full bloom).
## Useful for fading bloom in/out at runtime.
## Equivalent to Godot's Bloom slider.
@export_range(0.0, 1.0, 0.01) var bloom_mix: float = 1.0

@export_group("HDR")
## Controls how aggressively HDR values (above 1.0) contribute to bloom.
## At 1.0 this is neutral. Higher values amplify super-bright areas more.
## Equivalent to Godot's HDR Scale.
@export_range(0.0, 8.0, 0.01) var hdr_scale: float = 2.0
## Maximum luminance allowed into the bloom pipeline.
## Clamps extremely bright pixels to prevent firefly artifacts.
## Set to 0 to disable. Equivalent to Godot's HDR Luminance Cap.
@export_range(0.0, 256.0, 0.1) var hdr_luminance_cap: float = 12.0

@export_group("Tint")
## Enable color tinting of the bloom.
@export var tint_enabled: bool = false
## Color tint applied to the bloom before compositing.
@export var tint_color: Color = Color(1.0, 0.85, 0.7, 1.0)

@export_group("Streak")
## If true, streak is horizontal (anamorphic lens flare). If false, vertical.
@export var horizontal: bool = true
## How elongated the streak is. Higher = longer streaks.
## This controls the aspect ratio of the blur kernel.
@export_range(1.0, 16.0, 0.1) var streak_stretch: float = 4.0

@export_group("Cross Blur")
## Enable a secondary blur perpendicular to the streak direction.
## This adds a subtle "fill" that softens the harsh directionality.
@export var cross_blur_enabled: bool = false
## Strength of the cross blur relative to the main streak (0 = none, 1 = equal).
@export_range(0.0, 1.0, 0.01) var cross_blur_strength: float = 0.25

@export_group("Levels")
## Enable per-mip intensity weights for artistic control.
## Each weight controls how much that mip level contributes to the final bloom.
## Equivalent to Godot's Glow Levels.
@export var levels_enabled: bool = false
## Normalize mip weights so they sum to 1.0.
## Prevents the bloom from getting brighter as more levels are enabled.
## Equivalent to Godot's Normalized toggle.
@export var normalized: bool = true
## Weight for level 0 (half res - finest detail, tightest glow)
@export_range(0.0, 2.0, 0.01) var level_0: float = 1.0
## Weight for level 1
@export_range(0.0, 2.0, 0.01) var level_1: float = 1.0
## Weight for level 2
@export_range(0.0, 2.0, 0.01) var level_2: float = 1.0
## Weight for level 3
@export_range(0.0, 2.0, 0.01) var level_3: float = 1.0
## Weight for level 4 (lowest res - widest, most diffuse glow)
@export_range(0.0, 2.0, 0.01) var level_4: float = 1.0
## Weight for level 5
@export_range(0.0, 2.0, 0.01) var level_5: float = 1.0
## Weight for level 6
@export_range(0.0, 2.0, 0.01) var level_6: float = 1.0

@export_group("Compositing")
## Blend mode for combining bloom with the scene.
## Additive: bloom += scene (classic, can blow out).
## Screen: softer, preserves highlights (HDR-safe).
## Softlight: subtle, cinematic look.
## Replace: shows only the bloom (useful for debugging/tuning).
@export_enum("Additive", "Screen", "Softlight", "Replace") var blend_mode: int = 0

@export_group("Quality")
## Number of mip levels to use (more = wider bloom, costs more).
@export_range(2, 7, 1) var mip_levels: int = 5

# ─── Internal State ──────────────────────────────────────────────────────────

var rd: RenderingDevice

var prefilter_shader: RID
var prefilter_pipeline: RID

var downsample_shader: RID
var downsample_pipeline: RID

var blur_shader: RID
var blur_pipeline: RID

var upsample_shader: RID
var upsample_pipeline: RID

var composite_shader: RID
var composite_pipeline: RID

var linear_sampler: RID

var context: StringName = &"AnamorphicBloom"

const WORKGROUP_SIZE := 8

# ─── Lifecycle ───────────────────────────────────────────────────────────────

func _init():
	effect_callback_type = EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
	RenderingServer.call_on_render_thread(_initialize_compute)

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		if !is_instance_valid(self):
			return
		if !rd:
			return
		for s in [prefilter_shader, downsample_shader, blur_shader, upsample_shader, composite_shader]:
			if s.is_valid():
				rd.free_rid(s)
		for p in [prefilter_pipeline, downsample_pipeline, blur_pipeline, upsample_pipeline, composite_pipeline]:
			if p.is_valid():
				rd.free_rid(p)
		if linear_sampler.is_valid():
			rd.free_rid(linear_sampler)

func _free_shaders():
	if !rd:
		return
	for s in [prefilter_shader, downsample_shader, blur_shader, upsample_shader, composite_shader]:
		if s.is_valid():
			rd.free_rid(s)
	for p in [prefilter_pipeline, downsample_pipeline, blur_pipeline, upsample_pipeline, composite_pipeline]:
		if p.is_valid():
			rd.free_rid(p)

# ─── Initialization (Render Thread) ─────────────────────────────────────────

func _initialize_compute():
	rd = RenderingServer.get_rendering_device()
	if !rd:
		return

	# Create linear sampler for reading textures
	var sampler_state := RDSamplerState.new()
	sampler_state.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	sampler_state.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	sampler_state.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	linear_sampler = rd.sampler_create(sampler_state)

	# Load and compile all shaders
	prefilter_shader = _load_shader("res://addons/naxpost/prefilter.glsl")
	prefilter_pipeline = rd.compute_pipeline_create(prefilter_shader)

	downsample_shader = _load_shader("res://addons/naxpost/downsample.glsl")
	downsample_pipeline = rd.compute_pipeline_create(downsample_shader)

	blur_shader = _load_shader("res://addons/naxpost/blur.glsl")
	blur_pipeline = rd.compute_pipeline_create(blur_shader)

	upsample_shader = _load_shader("res://addons/naxpost/upsample.glsl")
	upsample_pipeline = rd.compute_pipeline_create(upsample_shader)

	composite_shader = _load_shader("res://addons/naxpost/composite.glsl")
	composite_pipeline = rd.compute_pipeline_create(composite_shader)

func _load_shader(path: String) -> RID:
	var shader_file: RDShaderFile = load(path)
	if !shader_file:
		push_error("AnamorphicBloom: Failed to load shader: " + path)
		return RID()
	var spirv = shader_file.get_spirv()
	return rd.shader_create_from_spirv(spirv)

# ─── Texture Management ─────────────────────────────────────────────────────

func _ensure_texture(name: StringName, buffers: RenderSceneBuffersRD, size: Vector2i):
	var fmt := RenderingDevice.DATA_FORMAT_R16G16B16A16_SFLOAT
	var usage := RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT | RenderingDevice.TEXTURE_USAGE_STORAGE_BIT

	if buffers.has_texture(context, name):
		var tf: RDTextureFormat = buffers.get_texture_format(context, name)
		if tf.width != size.x or tf.height != size.y:
			buffers.clear_context(context)

	if !buffers.has_texture(context, name):
		buffers.create_texture(context, name, fmt, usage, RenderingDevice.TEXTURE_SAMPLES_1, size, 1, 1, true, false)

func _get_image_uniform(image: RID, binding: int) -> RDUniform:
	var uniform := RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
	uniform.binding = binding
	uniform.add_id(image)
	return uniform

func _get_sampler_uniform(image: RID, binding: int) -> RDUniform:
	var uniform := RDUniform.new()
	uniform.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
	uniform.binding = binding
	uniform.add_id(linear_sampler)
	uniform.add_id(image)
	return uniform

# ─── Push Constants ──────────────────────────────────────────────────────────

func _make_push_constant(values: Array) -> PackedByteArray:
	## Pack an array of float values into a PackedByteArray, padded to 16-byte alignment.
	var arr := PackedFloat32Array()
	for v in values:
		arr.append(v)
	# Pad to multiple of 4 floats (16 bytes)
	while arr.size() % 4 != 0:
		arr.append(0.0)
	return arr.to_byte_array()

# ─── Dispatch Helper ─────────────────────────────────────────────────────────

func _dispatch(pipeline: RID, shader: RID, uniforms: Array[RDUniform], push_constants: PackedByteArray, groups: Vector3i, label: String = ""):
	if label != "":
		rd.draw_command_begin_label(label, Color.WHITE)

	var uniform_set = UniformSetCacheRD.get_cache(shader, 0, uniforms)
	var compute_list = rd.compute_list_begin()
	rd.compute_list_bind_compute_pipeline(compute_list, pipeline)
	rd.compute_list_bind_uniform_set(compute_list, uniform_set, 0)
	if !push_constants.is_empty():
		rd.compute_list_set_push_constant(compute_list, push_constants, push_constants.size())
	rd.compute_list_dispatch(compute_list, groups.x, groups.y, groups.z)
	rd.compute_list_end()

	if label != "":
		rd.draw_command_end_label()

func _groups_for_size(size: Vector2i) -> Vector3i:
	return Vector3i(
		(size.x - 1) / WORKGROUP_SIZE + 1,
		(size.y - 1) / WORKGROUP_SIZE + 1,
		1
	)

# ─── Level Weights ───────────────────────────────────────────────────────────

func _get_raw_level_weight(index: int) -> float:
	if !levels_enabled:
		return 1.0
	match index:
		0: return level_0
		1: return level_1
		2: return level_2
		3: return level_3
		4: return level_4
		5: return level_5
		6: return level_6
		_: return 1.0

func _get_normalized_level_weights(count: int) -> Array[float]:
	## Returns an array of level weights. If normalized is enabled,
	## they are rescaled so their sum equals 1.0.
	var weights: Array[float] = []
	var total := 0.0
	for i in count:
		var w := _get_raw_level_weight(i)
		weights.append(w)
		total += w

	if normalized and total > 0.0:
		for i in count:
			weights[i] /= total

	return weights

# ─── Main Render Callback ───────────────────────────────────────────────────

func _render_callback(p_effect_callback_type, p_render_data):
	if !rd:
		return
	if p_effect_callback_type != EFFECT_CALLBACK_TYPE_POST_TRANSPARENT:
		return
	if intensity <= 0.0 or bloom_mix <= 0.0:
		return

	# Validate shaders
	for s in [prefilter_shader, downsample_shader, blur_shader, upsample_shader, composite_shader]:
		if !s.is_valid():
			return

	var render_scene_buffers: RenderSceneBuffersRD = p_render_data.get_render_scene_buffers()
	if !render_scene_buffers:
		return

	var render_size: Vector2i = render_scene_buffers.get_internal_size()
	if render_size.x == 0 or render_size.y == 0:
		return

	var clamped_mips := clampi(mip_levels, 2, 7)

	# ── Calculate mip sizes ──────────────────────────────────────────────
	# Mip 0 = half resolution of screen
	var mip_sizes: Array[Vector2i] = []
	var current_size := Vector2i(render_size.x / 2, render_size.y / 2)
	for i in clamped_mips:
		mip_sizes.append(current_size)
		current_size = Vector2i(maxi(current_size.x / 2, 1), maxi(current_size.y / 2, 1))

	# ── Pre-compute normalized level weights ─────────────────────────────
	var level_weights := _get_normalized_level_weights(clamped_mips)

	# ── Ensure all intermediate textures exist ───────────────────────────
	for i in clamped_mips:
		_ensure_texture(&"bloom_mip_%d" % i, render_scene_buffers, mip_sizes[i])
		_ensure_texture(&"bloom_blur_%d" % i, render_scene_buffers, mip_sizes[i])

	var view_count = render_scene_buffers.get_view_count()

	for view in range(view_count):
		var color_image: RID = render_scene_buffers.get_color_layer(view)

		# Get all mip and blur texture slices for this view
		var mip_images: Array[RID] = []
		var blur_images: Array[RID] = []
		for i in clamped_mips:
			mip_images.append(render_scene_buffers.get_texture_slice(context, &"bloom_mip_%d" % i, view, 0, 1, 1))
			blur_images.append(render_scene_buffers.get_texture_slice(context, &"bloom_blur_%d" % i, view, 0, 1, 1))

		# ── Pass 1: Prefilter (threshold + downsample to mip 0) ──────
		var prefilter_pc := _make_push_constant([
			threshold, soft_knee,
			float(render_size.x), float(render_size.y),
			strength, hdr_scale, hdr_luminance_cap, 0.0
		])
		var prefilter_uniforms: Array[RDUniform] = [
			_get_sampler_uniform(color_image, 0),
			_get_image_uniform(mip_images[0], 1),
		]
		_dispatch(prefilter_pipeline, prefilter_shader, prefilter_uniforms, prefilter_pc,
			_groups_for_size(mip_sizes[0]), "Bloom Prefilter")

		# ── Pass 2: Progressive Downsample ───────────────────────────
		for i in range(1, clamped_mips):
			var ds_pc := _make_push_constant([
				float(mip_sizes[i - 1].x), float(mip_sizes[i - 1].y),
				float(mip_sizes[i].x), float(mip_sizes[i].y)
			])
			var ds_uniforms: Array[RDUniform] = [
				_get_sampler_uniform(mip_images[i - 1], 0),
				_get_image_uniform(mip_images[i], 1),
			]
			_dispatch(downsample_pipeline, downsample_shader, ds_uniforms, ds_pc,
				_groups_for_size(mip_sizes[i]), "Bloom Downsample %d" % i)

		# ── Pass 3: Directional Blur at each mip level ───────────────
		var dir_x := 1.0 if horizontal else 0.0
		var dir_y := 0.0 if horizontal else 1.0

		for i in range(clamped_mips):
			var blur_pc := _make_push_constant([
				float(mip_sizes[i].x), float(mip_sizes[i].y),
				dir_x * streak_stretch, dir_y * streak_stretch
			])
			# First pass: mip -> blur
			var blur_uniforms_1: Array[RDUniform] = [
				_get_sampler_uniform(mip_images[i], 0),
				_get_image_uniform(blur_images[i], 1),
			]
			_dispatch(blur_pipeline, blur_shader, blur_uniforms_1, blur_pc,
				_groups_for_size(mip_sizes[i]), "Bloom Blur %d pass1" % i)

			# Second pass: blur -> mip (wider blur)
			var blur_uniforms_2: Array[RDUniform] = [
				_get_sampler_uniform(blur_images[i], 0),
				_get_image_uniform(mip_images[i], 1),
			]
			_dispatch(blur_pipeline, blur_shader, blur_uniforms_2, blur_pc,
				_groups_for_size(mip_sizes[i]), "Bloom Blur %d pass2" % i)

			# Optional cross blur: perpendicular to streak direction
			if cross_blur_enabled and cross_blur_strength > 0.0:
				var cross_pc := _make_push_constant([
					float(mip_sizes[i].x), float(mip_sizes[i].y),
					dir_y * cross_blur_strength * streak_stretch * 0.5,
					dir_x * cross_blur_strength * streak_stretch * 0.5
				])
				var cross_uniforms_1: Array[RDUniform] = [
					_get_sampler_uniform(mip_images[i], 0),
					_get_image_uniform(blur_images[i], 1),
				]
				_dispatch(blur_pipeline, blur_shader, cross_uniforms_1, cross_pc,
					_groups_for_size(mip_sizes[i]), "Bloom CrossBlur %d" % i)

				var cross_uniforms_2: Array[RDUniform] = [
					_get_sampler_uniform(blur_images[i], 0),
					_get_image_uniform(mip_images[i], 1),
				]
				_dispatch(blur_pipeline, blur_shader, cross_uniforms_2, cross_pc,
					_groups_for_size(mip_sizes[i]), "Bloom CrossBlur %d pass2" % i)

		# ── Pass 4: Progressive Upsample ─────────────────────────────
		for i in range(clamped_mips - 2, -1, -1):
			var mip_w := level_weights[i + 1]
			var us_pc := _make_push_constant([
				float(mip_sizes[i].x), float(mip_sizes[i].y),
				float(mip_sizes[i + 1].x), float(mip_sizes[i + 1].y),
				mip_w, 0.0, 0.0, 0.0
			])
			var us_uniforms: Array[RDUniform] = [
				_get_sampler_uniform(mip_images[i + 1], 0),
				_get_image_uniform(mip_images[i], 1),
			]
			_dispatch(upsample_pipeline, upsample_shader, us_uniforms, us_pc,
				_groups_for_size(mip_sizes[i]), "Bloom Upsample %d" % i)

		# ── Pass 5: Composite onto scene ─────────────────────────────
		var tint_r := tint_color.r if tint_enabled else 1.0
		var tint_g := tint_color.g if tint_enabled else 1.0
		var tint_b := tint_color.b if tint_enabled else 1.0
		var final_intensity := intensity * level_weights[0]

		var comp_pc := _make_push_constant([
			float(render_size.x), float(render_size.y),
			final_intensity, float(blend_mode),
			tint_r, tint_g, tint_b, bloom_mix
		])
		var comp_uniforms: Array[RDUniform] = [
			_get_sampler_uniform(mip_images[0], 0),
			_get_image_uniform(color_image, 1),
		]
		_dispatch(composite_pipeline, composite_shader, comp_uniforms, comp_pc,
			_groups_for_size(render_size), "Bloom Composite")
