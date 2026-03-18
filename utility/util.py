import bpy, os, math, shutil


def safe_name(name):
    """Sanitize a name to be a valid Godot node/file name."""
    return name.replace('.', '_').replace(' ', '_')


def bool_vector_to_bitmask(vec):
    """Convert a BoolVectorProperty to a Godot layer bitmask integer."""
    result = 0
    for i, val in enumerate(vec):
        if val:
            result |= (1 << i)
    return result


def get_scene_name(context):
    """Get a clean, filesystem-safe scene name from the active Blender scene."""
    props = context.scene.MX_SceneProperties

    if props.mx_export_scene_name:
        scene_name = props.mx_export_scene_name
    else:
        scene_name = context.scene.name
        if scene_name == "Scene" and bpy.data.filepath:
            scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

    return scene_name.replace(' ', '_').replace('.', '_')


def createFolderStructure(project_dir):
    """Create standard Godot project folder structure."""
    folders = [
        "addons",
        "assets",
        "assets/audio",
        "assets/environment",
        "assets/lightmaps",
        "assets/meshes",
        "assets/textures",
        "assets/videos",
        "scenes",
        "scripts",
        "shaders",
    ]
    for folder in folders:
        folder_path = os.path.join(project_dir, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Created folder: {folder}")
    return folders


def matrix_to_godot_transform(matrix, is_camera=False):
    """Convert a Blender world matrix to a Godot Transform3D string (Y-up)."""
    pos_x = matrix[0][3]
    pos_y = matrix[2][3]
    pos_z = -matrix[1][3]

    if is_camera:
        from mathutils import Matrix
        correction = Matrix.Rotation(math.radians(-90), 4, 'X')
        matrix = matrix @ correction

    bx = (matrix[0][0], matrix[0][1], matrix[0][2])
    by = (matrix[1][0], matrix[1][1], matrix[1][2])
    bz = (matrix[2][0], matrix[2][1], matrix[2][2])

    gx = (bx[0],  bx[2], -bx[1])
    gy = (bz[0],  bz[2], -bz[1])
    gz = (-by[0], -by[2],  by[1])

    return (
        f"Transform3D("
        f"{gx[0]}, {gx[1]}, {gx[2]}, "
        f"{gy[0]}, {gy[1]}, {gy[2]}, "
        f"{gz[0]}, {gz[1]}, {gz[2]}, "
        f"{pos_x}, {pos_y}, {pos_z})"
    )


# ===== ENVIRONMENT HELPERS =====

def process_hdri_texture(tex_node, env_data, project_dir, node_tree):
    """Copy the HDRI file from an Environment Texture node into the project."""
    if tex_node.image:
        image = tex_node.image
        env_data['type'] = 'hdri'

        source_path = bpy.path.abspath(image.filepath)
        dest_dir = os.path.join(project_dir, "assets", "environment")

        if source_path and os.path.exists(source_path):
            filename = os.path.basename(source_path)
            dest_path = os.path.join(dest_dir, filename)
            if not os.path.exists(dest_path):
                shutil.copy2(source_path, dest_path)
                print(f"Copied HDRI: {filename}")
            env_data['hdri_path'] = source_path
            env_data['hdri_godot_path'] = f"res://assets/environment/{filename}"

        elif image.packed_file:
            filename = image.name
            if not filename.endswith(('.hdr', '.exr', '.png', '.jpg')):
                filename += '.exr'
            dest_path = os.path.join(dest_dir, filename)
            image.filepath_raw = dest_path
            image.save()
            env_data['hdri_path'] = dest_path
            env_data['hdri_godot_path'] = f"res://assets/environment/{filename}"

    # Pick up rotation from a Mapping node wired to this texture's Vector input
    vector_input = tex_node.inputs.get('Vector')
    if vector_input and vector_input.links:
        mapping_node = vector_input.links[0].from_node
        if mapping_node.type == 'MAPPING':
            rotation_input = mapping_node.inputs.get('Rotation')
            if rotation_input:
                env_data['rotation'] = rotation_input.default_value[2]

    return env_data


def process_sky_texture(tex_node, env_data):
    """Extract Blender Sky Texture parameters for Godot's PhysicalSkyMaterial."""
    env_data['type'] = 'procedural_sky'

    sky_params = {
        'sky_type': tex_node.sky_type,
        'turbidity': 10.0,
        'ground_albedo': 0.3,
        'sun_elevation': 0.0,
        'sun_rotation': 0.0,
        'sun_size': 1.0,
        'sun_intensity': 1.0,
        'rayleigh_coefficient': 2.0,
        'rayleigh_color': (0.3, 0.405, 0.6),
        'mie_coefficient': 0.005,
        'mie_eccentricity': 0.8,
        'mie_color': (0.69, 0.729, 0.812),
        'ground_color': (0.1, 0.07, 0.034),
        'exposure': 1.0,
        'energy_multiplier': 1.0,
    }

    if hasattr(tex_node, 'turbidity'):
        sky_params['turbidity'] = tex_node.turbidity

    if hasattr(tex_node, 'ground_albedo'):
        ga = tex_node.ground_albedo
        sky_params['ground_albedo'] = ga
        sky_params['ground_color'] = (ga * 0.4, ga * 0.35, ga * 0.2)

    if tex_node.sky_type == 'NISHITA':
        for attr in ('sun_elevation', 'sun_rotation', 'sun_size', 'sun_intensity'):
            if hasattr(tex_node, attr):
                sky_params[attr] = getattr(tex_node, attr)

    elif tex_node.sky_type in ('HOSEK_WILKIE', 'PREETHAM'):
        if hasattr(tex_node, 'sun_direction'):
            sun_dir = tex_node.sun_direction
            sky_params['sun_elevation'] = math.asin(max(-1.0, min(1.0, sun_dir[2])))
            sky_params['sun_rotation'] = math.atan2(sun_dir[0], sun_dir[1])

    sky_params['exposure'] = env_data.get('strength', 1.0)
    sky_params['turbidity'] = min(100.0, sky_params['turbidity'] * 10.0)

    env_data['sky_params'] = sky_params
    return env_data


def extract_environment_data(project_dir, world=None):
    """Extract sky/environment data from Blender's World node tree."""
    env_data = {
        'type': 'none',
        'hdri_path': None,
        'hdri_godot_path': None,
        'sky_params': None,
        'background_color': (0.05, 0.05, 0.05),
        'strength': 1.0,
        'rotation': 0.0,
    }

    world = world or bpy.context.scene.world
    if not world or not world.use_nodes:
        return env_data

    node_tree = world.node_tree
    nodes = node_tree.nodes

    output_node = next((n for n in nodes if n.type == 'OUTPUT_WORLD'), None)
    if not output_node:
        return env_data

    surface_input = output_node.inputs.get('Surface')
    if not surface_input or not surface_input.links:
        return env_data

    connected_node = surface_input.links[0].from_node

    if connected_node.type == 'BACKGROUND':
        strength_input = connected_node.inputs.get('Strength')
        if strength_input:
            env_data['strength'] = strength_input.default_value

        color_input = connected_node.inputs.get('Color')
        if color_input and color_input.links:
            color_source = color_input.links[0].from_node

            if color_source.type == 'TEX_ENVIRONMENT':
                env_data = process_hdri_texture(color_source, env_data, project_dir, node_tree)

            elif color_source.type == 'TEX_SKY':
                env_data = process_sky_texture(color_source, env_data)

            elif color_source.type == 'MAPPING':
                rotation_input = color_source.inputs.get('Rotation')
                if rotation_input:
                    env_data['rotation'] = rotation_input.default_value[2]

                # Find the texture node wired through this Mapping node
                for node in nodes:
                    if node.type not in ('TEX_ENVIRONMENT', 'TEX_SKY'):
                        continue
                    vec_in = node.inputs.get('Vector')
                    if vec_in and vec_in.links and vec_in.links[0].from_node == color_source:
                        if node.type == 'TEX_ENVIRONMENT':
                            env_data = process_hdri_texture(node, env_data, project_dir, node_tree)
                        else:
                            env_data = process_sky_texture(node, env_data)
                        break

        elif color_input:
            color = color_input.default_value
            env_data['type'] = 'color'
            env_data['background_color'] = (color[0], color[1], color[2])

    elif connected_node.type == 'TEX_ENVIRONMENT':
        env_data = process_hdri_texture(connected_node, env_data, project_dir, node_tree)

    elif connected_node.type == 'TEX_SKY':
        env_data = process_sky_texture(connected_node, env_data)

    return env_data


# ===== SCENE EXTRACTION =====

def extract_cameras_and_lights():
    """Extract camera and light data from the current Blender scene."""
    from .. import calibration

    cameras = []
    lights = []

    for obj in bpy.data.objects:
        if obj.hide_render:
            continue

        obj_props = obj.MX_ObjectProperties
        if not obj_props.mx_export_object:
            continue

        if obj.type == 'CAMERA':
            cam_data = obj.data
            attr_type = obj_props.mx_camera_attributes_type
            cam_attrs = {'type': attr_type}
            if attr_type != 'DISABLED':
                cam_attrs.update({
                    'exposure_multiplier': obj_props.mx_cam_exposure_multiplier,
                    'auto_exp_enabled': obj_props.mx_cam_auto_exp_enabled,
                    'auto_exp_scale': obj_props.mx_cam_auto_exp_scale,
                    'auto_exp_speed': obj_props.mx_cam_auto_exp_speed,
                })
            if attr_type == 'PRACTICAL':
                cam_attrs.update({
                    'dof_far_enabled': obj_props.mx_cam_dof_far_enabled,
                    'dof_near_enabled': obj_props.mx_cam_dof_near_enabled,
                    'dof_amount': obj_props.mx_cam_dof_amount,
                    'auto_exp_min_sensitivity': obj_props.mx_cam_auto_exp_min_sensitivity,
                    'auto_exp_max_sensitivity': obj_props.mx_cam_auto_exp_max_sensitivity,
                })
            elif attr_type == 'PHYSICAL':
                cam_attrs.update({
                    'frustum_focus_distance': obj_props.mx_cam_frustum_focus_distance,
                    'frustum_focal_length': obj_props.mx_cam_frustum_focal_length,
                    'frustum_near': obj_props.mx_cam_frustum_near,
                    'frustum_far': obj_props.mx_cam_frustum_far,
                    'phys_auto_exp_min': obj_props.mx_cam_phys_auto_exp_min,
                    'phys_auto_exp_max': obj_props.mx_cam_phys_auto_exp_max,
                })
            cameras.append({
                'name': obj.name,
                'transform': matrix_to_godot_transform(obj.matrix_world, is_camera=True),
                'fov': math.degrees(cam_data.angle),
                'near': cam_data.clip_start,
                'far': cam_data.clip_end,
                'render_layers': bool_vector_to_bitmask(obj_props.mx_render_layers),
                'attributes': cam_attrs,
            })

        elif obj.type == 'LIGHT':
            light_data = obj.data
            light_type = light_data.type

            light_info = {
                'name': obj.name,
                'transform': matrix_to_godot_transform(obj.matrix_world, is_camera=True),
                'type': light_type,
                'energy': calibration.calibrate_light_energy(light_type, light_data.energy),
                'color': (light_data.color[0], light_data.color[1], light_data.color[2]),
                'shadow_enabled': light_data.use_shadow,
                'render_layers': bool_vector_to_bitmask(obj_props.mx_render_layers),
            }

            if light_type == 'POINT':
                light_info['range'] = light_data.distance if light_data.use_custom_distance else 10.0
            elif light_type == 'SPOT':
                light_info['range'] = light_data.distance if light_data.use_custom_distance else 10.0
                light_info['spot_angle'] = math.degrees(light_data.spot_size)
                light_info['spot_blend'] = light_data.spot_blend

            lights.append(light_info)

    return cameras, lights


def extract_reflection_probes():
    """Extract reflection probe data from Blender light probes."""
    probes = []

    for obj in bpy.data.objects:
        if obj.type != 'LIGHT_PROBE':
            continue

        obj_props = obj.MX_ObjectProperties
        if not obj_props.mx_export_object:
            continue

        probe_data = obj.data
        if probe_data.type not in ('CUBE', 'SPHERE'):
            continue

        influence = probe_data.influence_distance
        scale = obj.scale

        probes.append({
            'name': obj.name,
            'transform': matrix_to_godot_transform(obj.matrix_world),
            'type': probe_data.type,
            'clip_start': probe_data.clip_start,
            'clip_end': probe_data.clip_end,
            'falloff': probe_data.falloff if hasattr(probe_data, 'falloff') else 0.1,
            'render_layers': bool_vector_to_bitmask(obj_props.mx_render_layers),
            'update_mode': obj_props.mx_reflection_update_mode,
            'intensity': obj_props.mx_reflection_intensity,
            'max_distance': obj_props.mx_reflection_max_distance,
            'ambient_mode': obj_props.mx_reflection_ambient_mode,
            'cull_mask': bool_vector_to_bitmask(obj_props.mx_reflection_cull_mask),
            'reflection_mask': bool_vector_to_bitmask(obj_props.mx_reflection_reflection_mask),
            'box_projection': obj_props.mx_reflection_box_projection,
            'interior': obj_props.mx_reflection_interior,
            'enable_shadows': obj_props.mx_reflection_enable_shadows,
            'blend_distance': obj_props.mx_reflection_blend_distance,
            # Blender Z → Godot Y, Blender Y → Godot Z
            'size': (influence * scale.x * 2.0, influence * scale.z * 2.0, influence * scale.y * 2.0),
            'shape': 'box',
        })

    return probes


# ===== MATERIAL CONVERSION HELPERS =====

def prepare_materials_for_export(props):
    """
    Temporarily modify Principled BSDF materials based on conversion settings.
    Strips emission/normal/roughness channels when the corresponding toggle is off.
    Returns a saved_state list to pass to restore_materials_after_export().
    Does nothing and returns [] when mx_convert_materials is False.
    """
    if not props.mx_convert_materials:
        return []

    saved_state = []

    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue

        nt = mat.node_tree
        saved_links = []
        saved_values = []

        for node in nt.nodes:
            if node.type != 'BSDF_PRINCIPLED':
                continue

            if not props.mx_convert_emission:
                strength = node.inputs.get('Emission Strength')
                if strength:
                    saved_values.append((strength, strength.default_value))
                    strength.default_value = 0.0
                emission = node.inputs.get('Emission Color')
                if emission:
                    for link in list(emission.links):
                        saved_links.append((nt, link.from_socket, link.to_socket))
                        nt.links.remove(link)

            if not props.mx_convert_normal_maps:
                normal = node.inputs.get('Normal')
                if normal:
                    for link in list(normal.links):
                        saved_links.append((nt, link.from_socket, link.to_socket))
                        nt.links.remove(link)

            if not props.mx_convert_roughness:
                roughness = node.inputs.get('Roughness')
                if roughness:
                    for link in list(roughness.links):
                        saved_links.append((nt, link.from_socket, link.to_socket))
                        nt.links.remove(link)

        if saved_links or saved_values:
            saved_state.append((mat, saved_links, saved_values))

    return saved_state


def restore_materials_after_export(saved_state):
    """Restore materials modified by prepare_materials_for_export()."""
    for mat, saved_links, saved_values in saved_state:
        nt = mat.node_tree
        for node_tree, from_socket, to_socket in saved_links:
            node_tree.links.new(from_socket, to_socket)
        for socket, value in saved_values:
            socket.default_value = value


def extract_decals():
    """Extract Decal data from EMPTY objects tagged with mx_is_decal."""
    decals = []

    for obj in bpy.data.objects:
        if obj.type != 'EMPTY':
            continue
        if obj.hide_render:
            continue

        obj_props = obj.MX_ObjectProperties
        if not obj_props.mx_export_object:
            continue
        if not obj_props.mx_is_decal:
            continue

        # Decompose world matrix → position + rotation, strip scale from basis
        loc, rot, obj_scale = obj.matrix_world.decompose()
        rot_mat = rot.to_matrix().to_4x4()
        rot_mat.translation = loc
        transform_str = matrix_to_godot_transform(rot_mat)

        # mx_decal_size is the base size; multiply by object scale so Blender
        # scaling the EMPTY directly controls the Godot Decal projection volume.
        # Axis remap: Blender X→Godot X, Blender Z→Godot Y, Blender Y→Godot Z
        base = obj_props.mx_decal_size
        size = (base[0] * obj_scale.x, base[1] * obj_scale.z, base[2] * obj_scale.y)
        col = obj_props.mx_decal_modulate

        def _img_path(img):
            if img is None:
                return None
            src = bpy.path.abspath(img.filepath) if img.filepath else None
            return src if src and os.path.exists(src) else None

        decals.append({
            'name': obj.name,
            'transform': transform_str,
            'size': (size[0], size[1], size[2]),
            'albedo_src':    _img_path(obj_props.mx_decal_albedo_tex),
            'normal_src':    _img_path(obj_props.mx_decal_normal_tex),
            'orm_src':       _img_path(obj_props.mx_decal_orm_tex),
            'emission_src':  _img_path(obj_props.mx_decal_emission_tex),
            'albedo_name':   obj_props.mx_decal_albedo_tex.name   if obj_props.mx_decal_albedo_tex   else None,
            'normal_name':   obj_props.mx_decal_normal_tex.name   if obj_props.mx_decal_normal_tex   else None,
            'orm_name':      obj_props.mx_decal_orm_tex.name      if obj_props.mx_decal_orm_tex      else None,
            'emission_name': obj_props.mx_decal_emission_tex.name if obj_props.mx_decal_emission_tex else None,
            'emission_energy': obj_props.mx_decal_emission_energy,
            'modulate': (col[0], col[1], col[2], col[3]),
            'albedo_mix':   obj_props.mx_decal_albedo_mix,
            'normal_fade':  obj_props.mx_decal_normal_fade,
            'upper_fade':   obj_props.mx_decal_upper_fade,
            'lower_fade':   obj_props.mx_decal_lower_fade,
            'distance_fade': obj_props.mx_decal_distance_fade,
            'distance_fade_begin':  obj_props.mx_decal_distance_fade_begin,
            'distance_fade_length': obj_props.mx_decal_distance_fade_length,
            'cull_mask': bool_vector_to_bitmask(obj_props.mx_decal_cull_mask),
        })

    return decals

