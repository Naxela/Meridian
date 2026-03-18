# naxpost_compositor_effect.gd
# CompositorEffect version of NaxPost — runs as a compute shader via RenderingDevice.
#
# USAGE:
#   1. Place this script and naxpost_compositor.glsl in your addons/naxpost/ folder.
#   2. In your WorldEnvironment (or Camera3D), create/assign a Compositor resource.
#   3. In the Compositor's effects array, add a new NaxPostCompositorEffect.
#   4. Tweak parameters in the inspector.
#
# REQUIRES: Godot 4.3+ with Vulkan (Forward+ or Mobile) renderer.
# NOTE: This only affects 3D rendering. 2D / CanvasLayer UI is unaffected.

@tool
class_name NaxPostCompositorEffect
extends CompositorEffect

# ─── Effect toggles ──────────────────────────────────────────────────────────
@export_group("Effects")
@export var enable_chromatic_aberration: bool = true
@export var enable_vignette: bool = true
@export var enable_sharpen: bool = true
@export var enable_colorgrading: bool = true

# ─── Chromatic Aberration ────────────────────────────────────────────────────
@export_group("Chromatic Aberration")
@export_range(0.0, 1.0) var ca_intensity: float = 0.025
@export_range(1, 64) var ca_max_samples: int = 32
@export var ca_lut_texture: Texture2D : set = _set_ca_lut_texture

# ─── Vignette ────────────────────────────────────────────────────────────────
@export_group("Vignette")
@export_range(0.0, 2.0) var vignette_intensity: float = 0.5
@export_range(0.1, 2.0) var vignette_smoothness: float = 0.8
@export_range(0.0, 1.0) var vignette_roundness: float = 1.0
@export var vignette_color: Color = Color.BLACK

# ─── Sharpen ─────────────────────────────────────────────────────────────────
@export_group("Sharpen")
@export var sharpen_color: Color = Color.BLACK
@export_range(0.0, 5.0) var sharpen_size: float = 2.5
@export_range(-5.0, 5.0) var sharpen_strength: float = 0.25

# ─── Colorgrading – Global ───────────────────────────────────────────────────
@export_group("Colorgrading")
@export var whitebalance: float = 6500.0
@export var shadow_max: float = 1.0
@export var highlight_min: float = 0.0
@export var tint: Color = Color.WHITE
@export var saturation: float = 1.0
@export var contrast: float = 1.0
@export var gamma: float = 1.0
@export var gain: float = 1.0
@export var offset: float = 1.0

# ─── Colorgrading – Shadows ─────────────────────────────────────────────────
@export_subgroup("Shadows")
@export var shadow_saturation: float = 1.0
@export var shadow_contrast: float = 1.0
@export var shadow_gamma: float = 1.0
@export var shadow_gain: float = 1.0
@export var shadow_offset: float = 1.0

# ─── Colorgrading – Midtones ────────────────────────────────────────────────
@export_subgroup("Midtones")
@export var midtone_saturation: float = 1.0
@export var midtone_contrast: float = 1.0
@export var midtone_gamma: float = 1.0
@export var midtone_gain: float = 1.0
@export var midtone_offset: float = 1.0

# ─── Colorgrading – Highlights ──────────────────────────────────────────────
@export_subgroup("Highlights")
@export var highlight_saturation: float = 1.0
@export var highlight_contrast: float = 1.0
@export var highlight_gamma: float = 1.0
@export var highlight_gain: float = 1.0
@export var highlight_offset: float = 1.0

# ─── Internal state ─────────────────────────────────────────────────────────
var _rd: RenderingDevice
var _shader: RID
var _pipeline: RID
var _copy_shader: RID
var _copy_pipeline: RID
var _lut_rd_texture: RID
var _lut_sampler: RID
var _params_buffer: RID
var _needs_lut_update: bool = true

func _set_ca_lut_texture(value: Texture2D) -> void:
	ca_lut_texture = value
	_needs_lut_update = true

# ─── Lifecycle ───────────────────────────────────────────────────────────────

func _init() -> void:
	effect_callback_type = EFFECT_CALLBACK_TYPE_POST_TRANSPARENT
	RenderingServer.call_on_render_thread(_initialize_compute)

func _notification(what: int) -> void:
	if what == NOTIFICATION_PREDELETE:
		_cleanup()

func _cleanup() -> void:
	if not _rd:
		return
	# Free GPU resources we own
	for rid in [_lut_rd_texture, _lut_sampler, _params_buffer, _copy_shader, _shader]:
		if rid and rid.is_valid():
			_rd.free_rid(rid)
	_lut_rd_texture = RID()
	_lut_sampler = RID()
	_params_buffer = RID()
	_pipeline = RID()
	_shader = RID()
	_copy_pipeline = RID()
	_copy_shader = RID()

# ─── Compute initialisation (runs on render thread) ─────────────────────────

func _initialize_compute() -> void:
	_rd = RenderingServer.get_rendering_device()
	if not _rd:
		push_error("NaxPost: Could not get RenderingDevice.")
		return

	# Load and compile the GLSL compute shader
	# ── Adjust this path to wherever you place the .glsl file ──
	var shader_file := load("res://addons/naxpost/naxpost_compositor.glsl")
	if not shader_file:
		push_error("NaxPost: Could not load naxpost_compositor.glsl — check the path.")
		return

	var shader_spirv: RDShaderSPIRV = shader_file.get_spirv()
	if shader_spirv == null:
		push_error("NaxPost: SPIR-V compilation failed.")
		return

	_shader = _rd.shader_create_from_spirv(shader_spirv)
	if not _shader.is_valid():
		push_error("NaxPost: Shader creation failed.")
		return

	_pipeline = _rd.compute_pipeline_create(_shader)

	# Load and compile the copy shader (used to snapshot screen before effects)
	var copy_file := load("res://addons/naxpost/naxpost_copy.glsl")
	if not copy_file:
		push_error("NaxPost: Could not load naxpost_copy.glsl — check the path.")
		return

	var copy_spirv: RDShaderSPIRV = copy_file.get_spirv()
	if copy_spirv == null:
		push_error("NaxPost: Copy shader SPIR-V compilation failed.")
		return

	_copy_shader = _rd.shader_create_from_spirv(copy_spirv)
	if not _copy_shader.is_valid():
		push_error("NaxPost: Copy shader creation failed.")
		return

	_copy_pipeline = _rd.compute_pipeline_create(_copy_shader)

	# Sampler for the chromatic aberration LUT
	var ss := RDSamplerState.new()
	ss.min_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ss.mag_filter = RenderingDevice.SAMPLER_FILTER_LINEAR
	ss.repeat_u = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	ss.repeat_v = RenderingDevice.SAMPLER_REPEAT_MODE_CLAMP_TO_EDGE
	_lut_sampler = _rd.sampler_create(ss)

	# Create the uniform buffer for our parameters (will be updated every frame)
	# 448 bytes of actual data, padded to 512 for alignment safety.
	var initial_data := PackedByteArray()
	initial_data.resize(512)
	initial_data.fill(0)
	_params_buffer = _rd.uniform_buffer_create(512, initial_data)

# ─── LUT texture upload ─────────────────────────────────────────────────────

func _ensure_lut_texture() -> void:
	if not _needs_lut_update:
		return
	_needs_lut_update = false

	if _lut_rd_texture.is_valid():
		_rd.free_rid(_lut_rd_texture)
		_lut_rd_texture = RID()

	var img: Image
	if ca_lut_texture:
		img = ca_lut_texture.get_image()
	else:
		img = Image.create(3, 1, false, Image.FORMAT_RGBAF)
		img.set_pixel(0, 0, Color(1, 0, 0, 1))
		img.set_pixel(1, 0, Color(0, 1, 0, 1))
		img.set_pixel(2, 0, Color(0, 0, 1, 1))

	img.convert(Image.FORMAT_RGBAF)

	var tf := RDTextureFormat.new()
	tf.texture_type = RenderingDevice.TEXTURE_TYPE_2D
	tf.width = img.get_width()
	tf.height = img.get_height()
	tf.format = RenderingDevice.DATA_FORMAT_R32G32B32A32_SFLOAT
	tf.usage_bits = (
		RenderingDevice.TEXTURE_USAGE_SAMPLING_BIT |
		RenderingDevice.TEXTURE_USAGE_CAN_UPDATE_BIT
	)
	_lut_rd_texture = _rd.texture_create(tf, RDTextureView.new(), [img.get_data()])

# ─── Parameter packing (std140 layout, matches GLSL Params UBO) ─────────────

func _pack_params() -> PackedByteArray:
	var buf := StreamPeerBuffer.new()
	buf.big_endian = false

	# --- helpers ---
	var pu := func(v: int): buf.put_32(v)           # uint32
	var pf := func(v: float): buf.put_float(v)      # float
	var pv4c := func(c: Color):                       # Color → vec4
		buf.put_float(c.r); buf.put_float(c.g); buf.put_float(c.b); buf.put_float(0.0)
	var pv4f := func(v: float):                       # scalar → vec4(v,v,v,0)
		buf.put_float(v); buf.put_float(v); buf.put_float(v); buf.put_float(0.0)

	# Effect toggles (4 × uint = 16 bytes)
	pu.call(1 if enable_chromatic_aberration else 0)
	pu.call(1 if enable_vignette else 0)
	pu.call(1 if enable_sharpen else 0)
	pu.call(1 if enable_colorgrading else 0)

	# Chromatic Aberration (float, int, pad, pad = 16 bytes)
	pf.call(ca_intensity)
	pu.call(ca_max_samples)
	pf.call(0.0)
	pf.call(0.0)

	# Vignette scalar block (3 floats + pad = 16 bytes)
	pf.call(vignette_intensity)
	pf.call(vignette_smoothness)
	pf.call(vignette_roundness)
	pf.call(0.0)
	# Vignette color vec4 (16 bytes)
	pv4c.call(vignette_color)

	# Sharpen color vec4 (16 bytes)
	pv4c.call(sharpen_color)
	# Sharpen scalars (2 floats + 2 pad = 16 bytes)
	pf.call(sharpen_size)
	pf.call(sharpen_strength)
	pf.call(0.0)
	pf.call(0.0)

	# Colorgrading globals: 3 floats + pad (16 bytes)
	pf.call(whitebalance)
	pf.call(shadow_max)
	pf.call(highlight_min)
	pf.call(0.0)
	# 6 × vec4 (96 bytes)
	pv4c.call(tint)
	pv4f.call(saturation)
	pv4f.call(contrast)
	pv4f.call(gamma)
	pv4f.call(gain)
	pv4f.call(offset)

	# Shadows: 5 × vec4 (80 bytes)
	pv4f.call(shadow_saturation)
	pv4f.call(shadow_contrast)
	pv4f.call(shadow_gamma)
	pv4f.call(shadow_gain)
	pv4f.call(shadow_offset)

	# Midtones: 5 × vec4 (80 bytes)
	pv4f.call(midtone_saturation)
	pv4f.call(midtone_contrast)
	pv4f.call(midtone_gamma)
	pv4f.call(midtone_gain)
	pv4f.call(midtone_offset)

	# Highlights: 5 × vec4 (80 bytes)
	pv4f.call(highlight_saturation)
	pv4f.call(highlight_contrast)
	pv4f.call(highlight_gamma)
	pv4f.call(highlight_gain)
	pv4f.call(highlight_offset)

	return buf.data_array

# ─── Render callback (called every frame on the render thread) ───────────────

func _render_callback(p_effect_callback_type: int, p_render_data: RenderData) -> void:
	if not _rd or not _pipeline.is_valid():
		return
	if p_effect_callback_type != EFFECT_CALLBACK_TYPE_POST_TRANSPARENT:
		return

	var render_scene_buffers: RenderSceneBuffersRD = p_render_data.get_render_scene_buffers()
	if not render_scene_buffers:
		return

	var size: Vector2i = render_scene_buffers.get_internal_size()
	if size.x == 0 or size.y == 0:
		return

	_ensure_lut_texture()
	if not _lut_rd_texture.is_valid():
		return

	# Update the params UBO with current values
	var param_data: PackedByteArray = _pack_params()
	_rd.buffer_update(_params_buffer, 0, param_data.size(), param_data)

	var view_count: int = render_scene_buffers.get_view_count()
	for view in range(view_count):
		var color_image: RID = render_scene_buffers.get_color_layer(view)
		if not color_image.is_valid():
			continue

		# Ensure we have a copy texture to read from (avoids read-write race).
		# We use render_scene_buffers to manage the lifetime of the temp texture.
		var context := &"naxpost"
		var source_name := &"source_copy"
		if not render_scene_buffers.has_texture(context, source_name):
			var usage_bits: int = (
				RenderingDevice.TEXTURE_USAGE_STORAGE_BIT
			)
			render_scene_buffers.create_texture(context, source_name, 
				RenderingDevice.DATA_FORMAT_R16G16B16A16_SFLOAT, usage_bits,
				RenderingDevice.TEXTURE_SAMPLES_1, size, 1, 1, true, false)

		var source_image: RID = render_scene_buffers.get_texture(context, source_name)

		# ── Compute-copy the screen into our source texture ──
		var x_groups: int = ceili(float(size.x) / 8.0)
		var y_groups: int = ceili(float(size.y) / 8.0)

		var u_copy_src := RDUniform.new()
		u_copy_src.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
		u_copy_src.binding = 0
		u_copy_src.add_id(color_image)

		var u_copy_dst := RDUniform.new()
		u_copy_dst.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
		u_copy_dst.binding = 1
		u_copy_dst.add_id(source_image)

		var copy_set: RID = UniformSetCacheRD.get_cache(_copy_shader, 0, [u_copy_src, u_copy_dst])

		var copy_list: int = _rd.compute_list_begin()
		_rd.compute_list_bind_compute_pipeline(copy_list, _copy_pipeline)
		_rd.compute_list_bind_uniform_set(copy_list, copy_set, 0)
		_rd.compute_list_dispatch(copy_list, x_groups, y_groups, 1)
		_rd.compute_list_end()

		# ── Set 0: output image (write) + source image (read) + LUT sampler ──
		var u_output := RDUniform.new()
		u_output.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
		u_output.binding = 0
		u_output.add_id(color_image)

		var u_source := RDUniform.new()
		u_source.uniform_type = RenderingDevice.UNIFORM_TYPE_IMAGE
		u_source.binding = 1
		u_source.add_id(source_image)

		var u_lut := RDUniform.new()
		u_lut.uniform_type = RenderingDevice.UNIFORM_TYPE_SAMPLER_WITH_TEXTURE
		u_lut.binding = 2
		u_lut.add_id(_lut_sampler)
		u_lut.add_id(_lut_rd_texture)

		var set0: RID = UniformSetCacheRD.get_cache(_shader, 0, [u_output, u_source, u_lut])

		# ── Set 1: parameters UBO ──
		var u_params := RDUniform.new()
		u_params.uniform_type = RenderingDevice.UNIFORM_TYPE_UNIFORM_BUFFER
		u_params.binding = 0
		u_params.add_id(_params_buffer)

		var set1: RID = UniformSetCacheRD.get_cache(_shader, 1, [u_params])

		# ── Dispatch main effect ──
		var compute_list: int = _rd.compute_list_begin()
		_rd.compute_list_bind_compute_pipeline(compute_list, _pipeline)
		_rd.compute_list_bind_uniform_set(compute_list, set0, 0)
		_rd.compute_list_bind_uniform_set(compute_list, set1, 1)
		_rd.compute_list_dispatch(compute_list, x_groups, y_groups, 1)
		_rd.compute_list_end()
