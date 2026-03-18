import bpy, os, json, re, shutil
from ..utility import util


def generate_godot_scene(cameras, lights, probes, scene_name, env_data, props,
                         has_model=True, use_lightmaps=False,
                         script_assignments=None, decals=None):
    """Generate a Godot main.tscn with cameras, lights, probes, environment, decals."""

    if not script_assignments:
        script_assignments = {}
    if not decals:
        decals = []

    lmbake_res_path = "res://assets/lightmaps/lightmap_data.lmbake"
    lmbake_abs_path = os.path.join(props.mx_godot_project_path, "assets", "lightmaps", "lightmap_data.lmbake")
    has_lmbake = use_lightmaps and os.path.exists(lmbake_abs_path)

    has_naxpost = getattr(props, 'mx_naxpost_enabled', False)
    has_anamorphic = getattr(props, 'mx_anamorphic_bloom_enabled', False)
    has_compositor = has_naxpost or has_anamorphic

    load_steps = 2
    if has_model:
        load_steps += 1
    if has_lmbake:
        load_steps += 2
    if has_naxpost:
        load_steps += 2
    if has_anamorphic:
        load_steps += 2
    if has_compositor:
        load_steps += 1

    naxpost_path = os.path.join(props.mx_godot_project_path, "addons", "naxpost", "naxpost.gd")
    naxpost_exists = os.path.exists(naxpost_path)
    if naxpost_exists:
        load_steps += 1

    if env_data['type'] == 'hdri' and env_data['hdri_godot_path']:
        load_steps += 2
    elif env_data['type'] == 'procedural_sky':
        load_steps += 2

    unique_scripts = set(script_assignments.values())
    load_steps += len(unique_scripts)

    cams_with_attrs = [c for c in cameras if c.get('attributes', {}).get('type', 'DISABLED') != 'DISABLED']
    load_steps += len(cams_with_attrs)

    _decal_tex_slots = ['albedo_src', 'normal_src', 'orm_src', 'emission_src']
    for dec in decals:
        for slot in _decal_tex_slots:
            if dec.get(slot):
                load_steps += 1

    is_xr = props.mx_platform == 'XR'
    if is_xr:
        load_steps += 1

    scene_content = f"[gd_scene load_steps={load_steps} format=3]\n\n"

    ext_resource_id = 1

    if has_model:
        scene_content += f'[ext_resource type="PackedScene" path="res://scenes/{scene_name}.tscn" id="{ext_resource_id}_model"]\n'
        ext_resource_id += 1

    xr_init_id = None
    if is_xr:
        scene_content += f'[ext_resource type="Script" path="res://scripts/xr_init.gd" id="{ext_resource_id}_xr_init"]\n'
        xr_init_id = ext_resource_id
        ext_resource_id += 1

    if naxpost_exists:
        scene_content += f'[ext_resource type="Script" path="res://addons/naxpost/naxpost.gd" id="{ext_resource_id}_naxpost"]\n'
        naxpost_id = ext_resource_id
        ext_resource_id += 1

    naxpost_effect_id = None
    if has_naxpost:
        scene_content += f'[ext_resource type="Script" path="res://addons/naxpost/naxpost_compositor_effect.gd" id="{ext_resource_id}_naxpost_effect"]\n'
        naxpost_effect_id = ext_resource_id
        ext_resource_id += 1

    anamorphic_effect_id = None
    if has_anamorphic:
        scene_content += f'[ext_resource type="Script" path="res://addons/naxpost/anamorphic_bloom.gd" id="{ext_resource_id}_anamorphic_effect"]\n'
        anamorphic_effect_id = ext_resource_id
        ext_resource_id += 1

    lmbake_id = None
    disable_culling_id = None
    if has_lmbake:
        scene_content += f'[ext_resource type="LightmapGIData" path="{lmbake_res_path}" id="{ext_resource_id}_lmbake"]\n'
        lmbake_id = ext_resource_id
        ext_resource_id += 1
        scene_content += f'[ext_resource type="Script" path="res://scripts/disable_culling.gd" id="{ext_resource_id}_disable_culling"]\n'
        disable_culling_id = ext_resource_id
        ext_resource_id += 1

    hdri_texture_id = None
    if env_data['type'] == 'hdri' and env_data['hdri_godot_path']:
        scene_content += f'[ext_resource type="Texture2D" path="{env_data["hdri_godot_path"]}" id="{ext_resource_id}_hdri"]\n'
        hdri_texture_id = ext_resource_id
        ext_resource_id += 1

    decal_tex_ids = {}
    decal_tex_keys = [
        ('albedo_src',   'albedo_name',   'texture_albedo'),
        ('normal_src',   'normal_name',   'texture_normal'),
        ('orm_src',      'orm_name',      'texture_orm'),
        ('emission_src', 'emission_name', 'texture_emission'),
    ]
    for dec in decals:
        for src_key, name_key, _ in decal_tex_keys:
            src_path = dec.get(src_key)
            if not src_path:
                continue
            filename = os.path.basename(src_path)
            dest_dir = os.path.join(props.mx_godot_project_path, "assets", "textures")
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, filename)
            if not os.path.exists(dest_path):
                shutil.copy2(src_path, dest_path)
                print(f"  Copied decal texture: {filename}")
            godot_path_str = f"res://assets/textures/{filename}"
            res_id = f"{ext_resource_id}_decaltex"
            scene_content += f'[ext_resource type="Texture2D" path="{godot_path_str}" id="{res_id}"]\n'
            decal_tex_ids[(dec['name'], src_key)] = res_id
            ext_resource_id += 1

    script_id_map = {}
    for script_file in sorted(unique_scripts):
        res_id = f"{ext_resource_id}_script"
        scene_content += f'[ext_resource type="Script" path="res://scripts/{script_file}" id="{res_id}"]\n'
        script_id_map[script_file] = res_id
        ext_resource_id += 1

    scene_content += '\n'

    has_sky = False

    if env_data['type'] == 'hdri' and hdri_texture_id:
        scene_content += '[sub_resource type="PanoramaSkyMaterial" id="PanoramaSkyMaterial_1"]\n'
        scene_content += f'panorama = ExtResource("{hdri_texture_id}_hdri")\n'
        scene_content += f'energy_multiplier = {env_data["strength"]}\n'
        scene_content += '\n'
        scene_content += '[sub_resource type="Sky" id="Sky_1"]\n'
        scene_content += 'sky_material = SubResource("PanoramaSkyMaterial_1")\n'
        scene_content += '\n'
        has_sky = True

    elif env_data['type'] == 'procedural_sky' and env_data.get('sky_params'):
        sky_params = env_data['sky_params']
        scene_content += '[sub_resource type="PhysicalSkyMaterial" id="PhysicalSkyMaterial_1"]\n'
        scene_content += f'rayleigh_coefficient = {sky_params["rayleigh_coefficient"]}\n'
        rc = sky_params['rayleigh_color']
        scene_content += f'rayleigh_color = Color({rc[0]}, {rc[1]}, {rc[2]}, 1)\n'
        scene_content += f'mie_coefficient = {sky_params["mie_coefficient"]}\n'
        scene_content += f'mie_eccentricity = {sky_params["mie_eccentricity"]}\n'
        mc = sky_params['mie_color']
        scene_content += f'mie_color = Color({mc[0]}, {mc[1]}, {mc[2]}, 1)\n'
        scene_content += f'turbidity = {sky_params["turbidity"]}\n'
        scene_content += f'sun_disk_scale = {sky_params["sun_size"]}\n'
        gc = sky_params['ground_color']
        scene_content += f'ground_color = Color({gc[0]}, {gc[1]}, {gc[2]}, 1)\n'
        scene_content += f'exposure = {sky_params["exposure"]}\n'
        scene_content += f'energy_multiplier = {sky_params["energy_multiplier"]}\n'
        scene_content += '\n'
        scene_content += '[sub_resource type="Sky" id="Sky_1"]\n'
        scene_content += 'sky_material = SubResource("PhysicalSkyMaterial_1")\n'
        scene_content += '\n'
        has_sky = True

    scene_content += '[sub_resource type="Environment" id="Environment_default"]\n'

    if has_sky:
        scene_content += 'background_mode = 2\n'
        scene_content += 'sky = SubResource("Sky_1")\n'
        scene_content += 'ambient_light_source = 2\n'
        scene_content += 'reflected_light_source = 2\n'
    elif env_data['type'] == 'color':
        scene_content += 'background_mode = 1\n'
        bc = env_data['background_color']
        scene_content += f'background_color = Color({bc[0]}, {bc[1]}, {bc[2]}, 1)\n'

    scene_content += f'tonemap_mode = {props.mx_tonemap_mode}\n'
    scene_content += f'tonemap_exposure = {props.mx_tonemap_exposure}\n'
    scene_content += f'tonemap_white = {props.mx_tonemap_white}\n'

    if props.mx_glow_enabled:
        scene_content += 'glow_enabled = true\n'
        scene_content += f'glow_levels/1 = {props.mx_glow_level_1}\n'
        scene_content += f'glow_levels/2 = {props.mx_glow_level_2}\n'
        scene_content += f'glow_levels/3 = {props.mx_glow_level_3}\n'
        scene_content += f'glow_levels/4 = {props.mx_glow_level_4}\n'
        scene_content += f'glow_levels/5 = {props.mx_glow_level_5}\n'
        scene_content += f'glow_levels/6 = {props.mx_glow_level_6}\n'
        scene_content += f'glow_levels/7 = {props.mx_glow_level_7}\n'
        scene_content += f'glow_normalized = {"true" if props.mx_glow_normalized else "false"}\n'
        scene_content += f'glow_intensity = {props.mx_glow_intensity}\n'
        scene_content += f'glow_strength = {props.mx_glow_strength}\n'
        scene_content += f'glow_bloom = {props.mx_glow_bloom}\n'
        scene_content += f'glow_blend_mode = {props.mx_glow_blend_mode}\n'
        scene_content += f'glow_hdr_threshold = {props.mx_glow_hdr_threshold}\n'
        scene_content += f'glow_hdr_scale = {props.mx_glow_hdr_scale}\n'

    if props.mx_ssr_enabled:
        scene_content += 'ssr_enabled = true\n'
        scene_content += f'ssr_max_steps = {props.mx_ssr_max_steps}\n'
        scene_content += f'ssr_fade_in = {props.mx_ssr_fade_in}\n'
        scene_content += f'ssr_fade_out = {props.mx_ssr_fade_out}\n'
        scene_content += f'ssr_depth_tolerance = {props.mx_ssr_depth_tolerance}\n'

    if props.mx_ssao_enabled:
        scene_content += 'ssao_enabled = true\n'
        scene_content += f'ssao_radius = {props.mx_ssao_radius}\n'
        scene_content += f'ssao_intensity = {props.mx_ssao_intensity}\n'
        scene_content += f'ssao_power = {props.mx_ssao_power}\n'
        scene_content += f'ssao_detail = {props.mx_ssao_detail}\n'
        scene_content += f'ssao_horizon = {props.mx_ssao_horizon}\n'
        scene_content += f'ssao_sharpness = {props.mx_ssao_sharpness}\n'
        scene_content += f'ssao_light_affect = {props.mx_ssao_light_affect}\n'
        scene_content += f'ssao_ao_channel_affect = {props.mx_ssao_ao_channel_affect}\n'

    if props.mx_ssil_enabled:
        scene_content += 'ssil_enabled = true\n'
        scene_content += f'ssil_radius = {props.mx_ssil_radius}\n'
        scene_content += f'ssil_intensity = {props.mx_ssil_intensity}\n'
        scene_content += f'ssil_sharpness = {props.mx_ssil_sharpness}\n'
        scene_content += f'ssil_normal_rejection = {props.mx_ssil_normal_rejection}\n'

    if props.mx_sdfgi_enabled:
        scene_content += 'sdfgi_enabled = true\n'
        scene_content += f'sdfgi_use_occlusion = {str(props.mx_sdfgi_use_occlusion).lower()}\n'
        scene_content += f'sdfgi_read_sky_light = {str(props.mx_sdfgi_read_sky_light).lower()}\n'
        scene_content += f'sdfgi_bounce_feedback = {props.mx_sdfgi_bounce_feedback}\n'
        scene_content += f'sdfgi_cascades = {props.mx_sdfgi_cascades}\n'
        scene_content += f'sdfgi_min_cell_size = {props.mx_sdfgi_min_cell_size}\n'
        scene_content += f'sdfgi_cascade0_distance = {props.mx_sdfgi_cascade0_distance}\n'
        scene_content += f'sdfgi_max_distance = {props.mx_sdfgi_max_distance}\n'
        scene_content += f'sdfgi_y_scale = {props.mx_sdfgi_y_scale}\n'
        scene_content += f'sdfgi_energy = {props.mx_sdfgi_energy}\n'
        scene_content += f'sdfgi_normal_bias = {props.mx_sdfgi_normal_bias}\n'
        scene_content += f'sdfgi_probe_bias = {props.mx_sdfgi_probe_bias}\n'

    if props.mx_fog_enabled:
        scene_content += 'fog_enabled = true\n'
        fc = props.mx_fog_light_color
        scene_content += f'fog_light_color = Color({fc[0]}, {fc[1]}, {fc[2]}, 1)\n'
        scene_content += f'fog_light_energy = {props.mx_fog_light_energy}\n'
        scene_content += f'fog_sun_scatter = {props.mx_fog_sun_scatter}\n'
        scene_content += f'fog_density = {props.mx_fog_density}\n'
        scene_content += f'fog_aerial_perspective = {props.mx_fog_aerial_perspective}\n'
        scene_content += f'fog_sky_affect = {props.mx_fog_sky_affect}\n'
        scene_content += f'fog_height = {props.mx_fog_height}\n'
        scene_content += f'fog_height_density = {props.mx_fog_height_density}\n'

    if props.mx_volumetric_fog_enabled:
        scene_content += 'volumetric_fog_enabled = true\n'
        scene_content += f'volumetric_fog_density = {props.mx_volumetric_fog_density}\n'
        va = props.mx_volumetric_fog_albedo
        scene_content += f'volumetric_fog_albedo = Color({va[0]}, {va[1]}, {va[2]}, 1)\n'
        ve = props.mx_volumetric_fog_emission
        scene_content += f'volumetric_fog_emission = Color({ve[0]}, {ve[1]}, {ve[2]}, 1)\n'
        scene_content += f'volumetric_fog_emission_energy = {props.mx_volumetric_fog_emission_energy}\n'
        scene_content += f'volumetric_fog_gi_inject = {props.mx_volumetric_fog_gi_inject}\n'
        scene_content += f'volumetric_fog_anisotropy = {props.mx_volumetric_fog_anisotropy}\n'
        scene_content += f'volumetric_fog_length = {props.mx_volumetric_fog_length}\n'
        scene_content += f'volumetric_fog_detail_spread = {props.mx_volumetric_fog_detail_spread}\n'
        scene_content += f'volumetric_fog_ambient_inject = {props.mx_volumetric_fog_ambient_inject}\n'
        scene_content += f'volumetric_fog_sky_affect = {props.mx_volumetric_fog_sky_affect}\n'
        scene_content += f'volumetric_fog_temporal_reprojection_enabled = {str(props.mx_volumetric_fog_temporal_reprojection_enabled).lower()}\n'
        scene_content += f'volumetric_fog_temporal_reprojection_amount = {props.mx_volumetric_fog_temporal_reprojection_amount}\n'

    if props.mx_adjustments_enabled:
        scene_content += 'adjustment_enabled = true\n'
        scene_content += f'adjustment_brightness = {props.mx_adjustments_brightness}\n'
        scene_content += f'adjustment_contrast = {props.mx_adjustments_contrast}\n'
        scene_content += f'adjustment_saturation = {props.mx_adjustments_saturation}\n'

    scene_content += '\n'

    compositor_effect_ids = []

    if has_naxpost:
        p = props
        scene_content += '[sub_resource type="CompositorEffect" id="CompositorEffect_naxpost"]\n'
        scene_content += f'script = ExtResource("{naxpost_effect_id}_naxpost_effect")\n'
        scene_content += 'enabled = true\n'
        scene_content += 'effect_callback_type = 4\n'
        scene_content += f'enable_chromatic_aberration = {"true" if p.mx_naxpost_ca_enabled else "false"}\n'
        scene_content += f'enable_vignette = {"true" if p.mx_naxpost_vignette_enabled else "false"}\n'
        scene_content += f'enable_sharpen = {"true" if p.mx_naxpost_sharpen_enabled else "false"}\n'
        scene_content += f'enable_colorgrading = {"true" if p.mx_naxpost_colorgrading_enabled else "false"}\n'
        scene_content += f'ca_intensity = {p.mx_naxpost_ca_intensity}\n'
        scene_content += f'ca_max_samples = {p.mx_naxpost_ca_max_samples}\n'
        scene_content += f'vignette_intensity = {p.mx_naxpost_vignette_intensity}\n'
        scene_content += f'vignette_smoothness = {p.mx_naxpost_vignette_smoothness}\n'
        scene_content += f'vignette_roundness = {p.mx_naxpost_vignette_roundness}\n'
        vc = p.mx_naxpost_vignette_color
        scene_content += f'vignette_color = Color({vc[0]}, {vc[1]}, {vc[2]}, 1)\n'
        scene_content += f'sharpen_size = {p.mx_naxpost_sharpen_size}\n'
        scene_content += f'sharpen_strength = {p.mx_naxpost_sharpen_strength}\n'
        scene_content += f'whitebalance = {p.mx_naxpost_whitebalance}\n'
        scene_content += f'shadow_max = {p.mx_naxpost_shadow_max}\n'
        scene_content += f'highlight_min = {p.mx_naxpost_highlight_min}\n'
        tc = p.mx_naxpost_tint
        scene_content += f'tint = Color({tc[0]}, {tc[1]}, {tc[2]}, 1)\n'
        scene_content += f'saturation = {p.mx_naxpost_saturation}\n'
        scene_content += f'contrast = {p.mx_naxpost_contrast}\n'
        scene_content += f'gamma = {p.mx_naxpost_gamma}\n'
        scene_content += f'gain = {p.mx_naxpost_gain}\n'
        scene_content += f'offset = {p.mx_naxpost_offset}\n'
        scene_content += '\n'
        compositor_effect_ids.append('SubResource("CompositorEffect_naxpost")')

    if has_anamorphic:
        p = props
        scene_content += '[sub_resource type="CompositorEffect" id="CompositorEffect_anamorphic"]\n'
        scene_content += f'script = ExtResource("{anamorphic_effect_id}_anamorphic_effect")\n'
        scene_content += 'enabled = true\n'
        scene_content += 'effect_callback_type = 4\n'
        scene_content += f'intensity = {p.mx_anamorphic_bloom_intensity}\n'
        scene_content += f'threshold = {p.mx_anamorphic_bloom_threshold}\n'
        scene_content += f'soft_knee = {p.mx_anamorphic_bloom_soft_knee}\n'
        scene_content += f'strength = {p.mx_anamorphic_bloom_strength}\n'
        scene_content += f'bloom_mix = {p.mx_anamorphic_bloom_mix}\n'
        scene_content += f'hdr_scale = {p.mx_anamorphic_bloom_hdr_scale}\n'
        scene_content += f'hdr_luminance_cap = {p.mx_anamorphic_bloom_hdr_luminance_cap}\n'
        scene_content += f'tint_enabled = {"true" if p.mx_anamorphic_bloom_tint_enabled else "false"}\n'
        btc = p.mx_anamorphic_bloom_tint_color
        scene_content += f'tint_color = Color({btc[0]}, {btc[1]}, {btc[2]}, 1)\n'
        scene_content += f'horizontal = {"true" if p.mx_anamorphic_bloom_horizontal else "false"}\n'
        scene_content += f'streak_stretch = {p.mx_anamorphic_bloom_streak_stretch}\n'
        scene_content += f'cross_blur_enabled = {"true" if p.mx_anamorphic_bloom_cross_blur_enabled else "false"}\n'
        scene_content += f'cross_blur_strength = {p.mx_anamorphic_bloom_cross_blur_strength}\n'
        scene_content += f'blend_mode = {p.mx_anamorphic_bloom_blend_mode}\n'
        scene_content += f'mip_levels = {p.mx_anamorphic_bloom_mip_levels}\n'
        scene_content += '\n'
        compositor_effect_ids.append('SubResource("CompositorEffect_anamorphic")')

    if has_compositor:
        effects_array = ', '.join(compositor_effect_ids)
        scene_content += '[sub_resource type="Compositor" id="Compositor_1"]\n'
        scene_content += f'compositor_effects = Array[CompositorEffect]([{effects_array}])\n'
        scene_content += '\n'

    for cam in cams_with_attrs:
        safe_cam = util.safe_name(cam['name'])
        attrs = cam['attributes']
        attr_type = attrs['type']
        res_type = 'CameraAttributesPractical' if attr_type == 'PRACTICAL' else 'CameraAttributesPhysical'
        scene_content += f'[sub_resource type="{res_type}" id="CameraAttr_{safe_cam}"]\n'
        if attr_type == 'PRACTICAL':
            scene_content += f'dof_blur_far_enabled = {"true" if attrs["dof_far_enabled"] else "false"}\n'
            scene_content += f'dof_blur_near_enabled = {"true" if attrs["dof_near_enabled"] else "false"}\n'
            scene_content += f'dof_blur_amount = {attrs["dof_amount"]}\n'
            scene_content += f'auto_exposure_min_sensitivity = {attrs["auto_exp_min_sensitivity"]}\n'
            scene_content += f'auto_exposure_max_sensitivity = {attrs["auto_exp_max_sensitivity"]}\n'
        else:
            scene_content += f'frustum_focus_distance = {attrs["frustum_focus_distance"]}\n'
            scene_content += f'frustum_focal_length = {attrs["frustum_focal_length"]}\n'
            scene_content += f'frustum_near = {attrs["frustum_near"]}\n'
            scene_content += f'frustum_far = {attrs["frustum_far"]}\n'
            scene_content += f'auto_exposure_min_exposure_value = {attrs["phys_auto_exp_min"]}\n'
            scene_content += f'auto_exposure_max_exposure_value = {attrs["phys_auto_exp_max"]}\n'
        scene_content += f'exposure_multiplier = {attrs["exposure_multiplier"]}\n'
        scene_content += f'auto_exposure_enabled = {"true" if attrs["auto_exp_enabled"] else "false"}\n'
        scene_content += f'auto_exposure_scale = {attrs["auto_exp_scale"]}\n'
        scene_content += f'auto_exposure_speed = {attrs["auto_exp_speed"]}\n'
        scene_content += '\n'

    scene_content += '[node name="Main" type="Node3D"]\n'
    if is_xr and xr_init_id:
        scene_content += f'script = ExtResource("{xr_init_id}_xr_init")\n'
    scene_content += '\n'

    scene_content += '[node name="BakedGI" type="DirectionalLight3D" parent="."]\n'
    scene_content += 'light_color = Color(0, 0, 0, 1)\n'
    scene_content += 'light_energy = 0.0\n'
    scene_content += 'editor_only = true\n\n'

    if is_xr:
        scene_content += '[node name="XROrigin" type="XROrigin3D" parent="."]\n\n'
        scene_content += '[node name="XRCamera" type="XRCamera3D" parent="XROrigin"]\n'
        scene_content += 'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.7, 0)\n'
        scene_content += '\n'
        scene_content += '[node name="LeftHand" type="XRController3D" parent="XROrigin"]\n'
        scene_content += 'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, -0.5, 1.0, -0.5)\n'
        scene_content += 'tracker = &"left_hand"\n'
        scene_content += '\n'
        scene_content += '[node name="RightHand" type="XRController3D" parent="XROrigin"]\n'
        scene_content += 'transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0.5, 1.0, -0.5)\n'
        scene_content += 'tracker = &"right_hand"\n'
        scene_content += '\n'

    for i, cam in enumerate(cameras):
        if is_xr:
            continue
        safe_cam_name = util.safe_name(cam['name'])
        scene_content += f'[node name="{safe_cam_name}" type="Camera3D" parent="."]\n'
        scene_content += f'transform = {cam["transform"]}\n'
        scene_content += f'fov = {cam["fov"]}\n'
        scene_content += f'near = {cam["near"]}\n'
        scene_content += f'far = {cam["far"]}\n'
        if cam.get('render_layers', 1) != 1:
            scene_content += f'layers = {cam["render_layers"]}\n'
        if cam.get('attributes', {}).get('type', 'DISABLED') != 'DISABLED':
            scene_content += f'attributes = SubResource("CameraAttr_{safe_cam_name}")\n'
        if i == 0:
            scene_content += 'current = true\n'
        if safe_cam_name in script_assignments:
            res_id = script_id_map[script_assignments[safe_cam_name]]
            scene_content += f'script = ExtResource("{res_id}")\n'
        scene_content += '\n'

    for light in lights:
        safe_light_name = util.safe_name(light['name'])
        if light['type'] == 'SUN':
            godot_type = "DirectionalLight3D"
        elif light['type'] == 'POINT':
            godot_type = "OmniLight3D"
        elif light['type'] == 'SPOT':
            godot_type = "SpotLight3D"
        else:
            continue
        scene_content += f'[node name="{safe_light_name}" type="{godot_type}" parent="."]\n'
        scene_content += f'transform = {light["transform"]}\n'
        scene_content += f'light_energy = {light["energy"]}\n'
        scene_content += f'light_color = Color({light["color"][0]}, {light["color"][1]}, {light["color"][2]}, 1)\n'
        scene_content += f'shadow_enabled = {str(light.get("shadow_enabled", True)).lower()}\n'
        if light.get('render_layers', 1) != 1:
            scene_content += f'layers = {light["render_layers"]}\n'
        if light['type'] in ['POINT', 'SPOT']:
            scene_content += f'omni_range = {light.get("range", 10.0)}\n'
        if light['type'] == 'SPOT':
            scene_content += f'spot_angle = {light.get("spot_angle", 45)}\n'
        if safe_light_name in script_assignments:
            res_id = script_id_map[script_assignments[safe_light_name]]
            scene_content += f'script = ExtResource("{res_id}")\n'
        scene_content += '\n'

    for probe in probes:
        safe_probe_name = util.safe_name(probe['name'])
        update_mode_map = {'ONCE': 0, 'ALWAYS': 1}
        ambient_mode_map = {'DISABLED': 0, 'ENVIRONMENT': 1, 'CONSTANT_COLOR': 2}
        scene_content += f'[node name="{safe_probe_name}" type="ReflectionProbe" parent="."]\n'
        scene_content += f'transform = {probe["transform"]}\n'
        size = probe['size']
        scene_content += f'size = Vector3({size[0]}, {size[1]}, {size[2]})\n'
        if probe.get('render_layers', 1) != 1:
            scene_content += f'layers = {probe["render_layers"]}\n'
        scene_content += f'update_mode = {update_mode_map.get(probe.get("update_mode", "ONCE"), 0)}\n'
        scene_content += f'intensity = {probe.get("intensity", 1.0)}\n'
        scene_content += f'max_distance = {probe.get("max_distance", 0.0)}\n'
        scene_content += f'ambient_mode = {ambient_mode_map.get(probe.get("ambient_mode", "DISABLED"), 0)}\n'
        scene_content += f'cull_mask = {probe.get("cull_mask", 1048575)}\n'
        scene_content += f'reflection_mask = {probe.get("reflection_mask", 1048575)}\n'
        scene_content += f'box_projection = {"true" if probe.get("box_projection", True) else "false"}\n'
        scene_content += f'interior = {"true" if probe.get("interior", False) else "false"}\n'
        scene_content += f'enable_shadows = {"true" if probe.get("enable_shadows", False) else "false"}\n'
        scene_content += f'blend_distance = {probe.get("blend_distance", 0.0)}\n'
        scene_content += '\n'

    if has_model:
        scene_content += f'[node name="{scene_name}" parent="." instance=ExtResource("1_model")]\n\n'

    if has_lmbake:
        scene_content += '[node name="LightmapGI" type="LightmapGI" parent="."]\n'
        scene_content += f'light_data = ExtResource("{lmbake_id}_lmbake")\n'
        scene_content += f'script = ExtResource("{disable_culling_id}_disable_culling")\n\n'

    for dec in decals:
        safe_dec = util.safe_name(dec['name'])
        scene_content += f'[node name="{safe_dec}" type="Decal" parent="."]\n'
        scene_content += f'transform = {dec["transform"]}\n'
        sz = dec['size']
        scene_content += f'size = Vector3({sz[0]}, {sz[1]}, {sz[2]})\n'
        for src_key, _, prop_name in [
            ('albedo_src',   'albedo_name',   'texture_albedo'),
            ('normal_src',   'normal_name',   'texture_normal'),
            ('orm_src',      'orm_name',      'texture_orm'),
            ('emission_src', 'emission_name', 'texture_emission'),
        ]:
            tex_id = decal_tex_ids.get((dec['name'], src_key))
            if tex_id:
                scene_content += f'{prop_name} = ExtResource("{tex_id}")\n'
        scene_content += f'emission_energy = {dec["emission_energy"]}\n'
        mc = dec['modulate']
        scene_content += f'modulate = Color({mc[0]}, {mc[1]}, {mc[2]}, {mc[3]})\n'
        scene_content += f'albedo_mix = {dec["albedo_mix"]}\n'
        scene_content += f'normal_fade = {dec["normal_fade"]}\n'
        scene_content += f'upper_fade = {dec["upper_fade"]}\n'
        scene_content += f'lower_fade = {dec["lower_fade"]}\n'
        scene_content += f'distance_fade_enabled = {"true" if dec["distance_fade"] else "false"}\n'
        if dec['distance_fade']:
            scene_content += f'distance_fade_begin = {dec["distance_fade_begin"]}\n'
            scene_content += f'distance_fade_length = {dec["distance_fade_length"]}\n'
        if dec['cull_mask'] != 1048575:
            scene_content += f'cull_mask = {dec["cull_mask"]}\n'
        scene_content += '\n'

    scene_content += '[node name="WorldEnvironment" type="WorldEnvironment" parent="."]\n'
    scene_content += 'environment = SubResource("Environment_default")\n'
    if has_compositor:
        scene_content += 'compositor = SubResource("Compositor_1")\n'
    scene_content += '\n'

    if naxpost_exists:
        scene_content += '[node name="NaxPostController" type="Node" parent="."]\n'
        scene_content += f'script = ExtResource("{naxpost_id}_naxpost")\n'

    return scene_content


def create_inherited_scene_file(project_dir, scene_name, props,
                                script_assignments=None, layer_assignments=None):
    """Create an inherited .tscn referencing the GLTF, with scripts/layers/lightmap materials."""

    scenes_dir = os.path.join(project_dir, "scenes")
    if not os.path.exists(scenes_dir):
        os.makedirs(scenes_dir)

    inherited_scene_path = os.path.join(scenes_dir, f"{scene_name}.tscn")
    file_ext = 'gltf' if props.mx_export_format == 'GLTF' else 'glb'

    if not script_assignments:
        script_assignments = {}
    if not layer_assignments:
        layer_assignments = {}

    individual_mats = {}
    if props.mx_lightmap_mode == 'INDIVIDUAL':
        manifest_path = os.path.join(project_dir, "assets", "lightmaps", "manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as mf:
                mdata = json.load(mf)
            lm_ext = mdata.get("ext", "hdr")
            for obj_name, lm_file in mdata.get("lightmaps", {}).items():
                individual_mats[util.safe_name(obj_name)] = {
                    'lm_file': lm_file,
                    'lm_ext': lm_ext,
                    'mat_id': f"ShaderMaterial_{util.safe_name(obj_name)}",
                }
            if individual_mats:
                print(f"  Individual lightmap mode: embedding {len(individual_mats)} material(s)")

    unique_scripts = set(script_assignments.values())
    load_steps = 1 + len(unique_scripts)
    if individual_mats:
        load_steps += 1
        load_steps += len(individual_mats)
        load_steps += len(individual_mats)

    scene_content = f'[gd_scene load_steps={load_steps} format=3]\n\n'

    scene_content += f'[ext_resource type="PackedScene" path="res://assets/meshes/{scene_name}.{file_ext}" id="1"]\n'

    script_id_map = {}
    ext_id = 2
    for script_file in sorted(unique_scripts):
        res_id = f"{ext_id}_script"
        scene_content += f'[ext_resource type="Script" path="res://scripts/{script_file}" id="{res_id}"]\n'
        script_id_map[script_file] = res_id
        ext_id += 1

    shader_ext_id = None
    lm_tex_ids = {}
    if individual_mats:
        shader_ext_id = f"{ext_id}_shader"
        scene_content += f'[ext_resource type="Shader" path="res://assets/StandardPlusAuto.gdshader" id="{shader_ext_id}"]\n'
        ext_id += 1
        for sn, info in individual_mats.items():
            lm_res_id = f"{ext_id}_lm_{sn}"
            lm_path = f'res://assets/lightmaps/{info["lm_file"]}.{info["lm_ext"]}'
            scene_content += f'[ext_resource type="Texture2D" path="{lm_path}" id="{lm_res_id}"]\n'
            lm_tex_ids[sn] = lm_res_id
            ext_id += 1

    scene_content += '\n'

    if individual_mats:
        bicubic = str(props.mx_lightmap_bicubic_filtering).lower()
        for sn, info in individual_mats.items():
            scene_content += f'[sub_resource type="ShaderMaterial" id="{info["mat_id"]}"]\n'
            scene_content += f'shader = ExtResource("{shader_ext_id}")\n'
            scene_content += f'shader_parameter/texture_lightmap = ExtResource("{lm_tex_ids[sn]}")\n'
            scene_content += f'shader_parameter/use_bicubic_lightmap = {bicubic}\n'
            scene_content += f'shader_parameter/lightmap_strength = 1.0\n'
            scene_content += '\n'

    scene_content += f'[node name="{scene_name}" instance=ExtResource("1")]\n'

    # script_assignments / layer_assignments keys are full paths (e.g. "Parent/Child")
    # individual_mats keys are leaf names (always direct children of the inherited root)
    all_path_nodes = set(script_assignments.keys()) | set(layer_assignments.keys())
    path_leaf_names = {p.split('/')[-1] for p in all_path_nodes}
    solo_mat_nodes = set(individual_mats.keys()) - path_leaf_names

    for node_path in sorted(all_path_nodes):
        path_parts = node_path.split('/')
        node_name = path_parts[-1]
        parent = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '.'
        scene_content += f'\n[node name="{node_name}" parent="{parent}"]\n'
        if node_path in layer_assignments:
            scene_content += f'layers = {layer_assignments[node_path]}\n'
        if node_path in script_assignments:
            res_id = script_id_map[script_assignments[node_path]]
            scene_content += f'script = ExtResource("{res_id}")\n'
        if node_name in individual_mats:
            mat_id = individual_mats[node_name]['mat_id']
            scene_content += f'surface_material_override/0 = SubResource("{mat_id}")\n'

    for node_name in sorted(solo_mat_nodes):
        scene_content += f'\n[node name="{node_name}" parent="."]\n'
        mat_id = individual_mats[node_name]['mat_id']
        scene_content += f'surface_material_override/0 = SubResource("{mat_id}")\n'

    with open(inherited_scene_path, 'w') as f:
        f.write(scene_content)

    print(f"Created inherited scene at: {inherited_scene_path}")
    if script_assignments:
        print(f"  With {len(script_assignments)} script assignment(s)")
    if layer_assignments:
        print(f"  With {len(layer_assignments)} layer override(s)")
    if individual_mats:
        print(f"  With {len(individual_mats)} individual lightmap material(s)")
    return f"res://scenes/{scene_name}.tscn"


def update_inherited_scene_scripts(project_dir, scene_name,
                                   script_assignments=None, layer_assignments=None):
    """Surgically update script/layer assignments in an inherited scene, preserving lightmap data."""

    if not script_assignments:
        script_assignments = {}
    if not layer_assignments:
        layer_assignments = {}

    inherited_scene_path = os.path.join(project_dir, "scenes", f"{scene_name}.tscn")

    if not os.path.exists(inherited_scene_path):
        print(f"Warning: Inherited scene not found at {inherited_scene_path}")
        return

    with open(inherited_scene_path, 'r') as f:
        lines = f.readlines()
    lines = [line.rstrip('\n') for line in lines]

    valid_ext_ids = set()
    filtered_lines = []
    for line in lines:
        if line.startswith('[ext_resource'):
            id_match = re.search(r'id="([^"]+)"', line)
            if 'type="Script"' in line and 'path="res://scripts/' in line:
                continue
            elif id_match:
                valid_ext_ids.add(id_match.group(1))
        filtered_lines.append(line)
    lines = filtered_lines

    unique_scripts = set(script_assignments.values())
    script_id_map = {}

    if unique_scripts:
        last_ext_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('[ext_resource'):
                last_ext_idx = i

        ext_id = 100
        new_ext_lines = []
        for script_file in sorted(unique_scripts):
            res_id = f"{ext_id}_script"
            new_ext_lines.append(f'[ext_resource type="Script" path="res://scripts/{script_file}" id="{res_id}"]')
            script_id_map[script_file] = res_id
            valid_ext_ids.add(res_id)
            ext_id += 1

        if last_ext_idx >= 0:
            for j, new_line in enumerate(new_ext_lines):
                lines.insert(last_ext_idx + 1 + j, new_line)

    result_lines = []
    i = 0
    nodes_handled = set()

    while i < len(lines):
        line = lines[i]

        if line.startswith('[node name="') and 'parent=' in line:
            name_match = re.search(r'\[node name="([^"]+)"', line)
            parent_match = re.search(r'parent="([^"]+)"', line)
            node_name = name_match.group(1) if name_match else None
            parent_str = parent_match.group(1) if parent_match else '.'
            full_path = node_name if parent_str == '.' else f"{parent_str}/{node_name}"

            result_lines.append(line)
            i += 1

            node_props = []
            while i < len(lines) and lines[i] and not lines[i].startswith('['):
                prop_line = lines[i]
                if prop_line.startswith('script = ExtResource(') or prop_line.startswith('layers = '):
                    i += 1
                    continue
                node_props.append(prop_line)
                i += 1

            inserts = []
            if full_path and full_path in script_assignments:
                script_file = script_assignments[full_path]
                res_id = script_id_map[script_file]
                inserts.append(f'script = ExtResource("{res_id}")')
                nodes_handled.add(full_path)
            if full_path and full_path in layer_assignments:
                inserts.insert(0, f'layers = {layer_assignments[full_path]}')
                nodes_handled.add(full_path)
            for idx, ins in enumerate(inserts):
                node_props.insert(idx, ins)

            result_lines.extend(node_props)
            continue

        else:
            result_lines.append(line)
            i += 1

    all_new_nodes = set(script_assignments.keys()) | set(layer_assignments.keys())
    for node_path in sorted(all_new_nodes):
        if node_path not in nodes_handled:
            path_parts = node_path.split('/')
            node_name = path_parts[-1]
            parent = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else '.'
            result_lines.append('')
            result_lines.append(f'[node name="{node_name}" parent="{parent}"]')
            if node_path in layer_assignments:
                result_lines.append(f'layers = {layer_assignments[node_path]}')
            if node_path in script_assignments:
                script_file = script_assignments[node_path]
                res_id = script_id_map[script_file]
                result_lines.append(f'script = ExtResource("{res_id}")')

    ext_count = sum(1 for line in result_lines if line.startswith('[ext_resource'))
    sub_count = sum(1 for line in result_lines if line.startswith('[sub_resource'))
    load_steps = ext_count + sub_count

    for j, line in enumerate(result_lines):
        if line.startswith('[gd_scene'):
            result_lines[j] = re.sub(r'load_steps=\d+', f'load_steps={load_steps}', line)
            break

    with open(inherited_scene_path, 'w') as f:
        f.write('\n'.join(result_lines))

    print(f"Updated inherited scene scripts (preserved lightmap data)")
    if script_assignments:
        print(f"  Updated {len(script_assignments)} script assignment(s)")
