import bpy, os, json, re, shutil, time
from ..utility import util


def createGodotProject(project_dir, props):
    """Create/update project.godot with rendering, platform, and app settings."""

    if not os.path.exists(project_dir):
        os.makedirs(project_dir)

    icon_godot_path = ""
    splash_godot_path = ""

    if props.mx_app_icon:
        icon_src = bpy.path.abspath(props.mx_app_icon)
        if os.path.isfile(icon_src):
            icon_filename = os.path.basename(icon_src)
            icon_dest = os.path.join(project_dir, icon_filename)
            shutil.copy2(icon_src, icon_dest)
            icon_godot_path = f"res://{icon_filename}"
            print(f"Copied app icon: {icon_filename}")

    splash_src = ""
    if props.mx_splash_image:
        splash_src = bpy.path.abspath(props.mx_splash_image)
    if not splash_src or not os.path.isfile(splash_src):
        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        splash_src = os.path.join(addon_dir, "logo.png")

    if os.path.isfile(splash_src):
        splash_filename = os.path.basename(splash_src)
        splash_dest = os.path.join(project_dir, splash_filename)
        shutil.copy2(splash_src, splash_dest)
        splash_godot_path = f"res://{splash_filename}"
        print(f"Copied boot splash: {splash_filename}")

    project_file = os.path.join(project_dir, "project.godot")

    renderer_feature = {
        'FORWARD_PLUS':  'Forward Plus',
        'MOBILE':        'Mobile',
        'COMPATIBILITY': 'GL Compatibility',
    }.get(props.mx_renderer, 'Forward Plus')

    project_content = f"""; Engine configuration file.

config_version=5

[application]

config/name="{props.mx_project_name or 'Blender Export'}"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.6", "{renderer_feature}")
"""

    if icon_godot_path:
        project_content += f'config/icon="{icon_godot_path}"\n'

    if splash_godot_path:
        project_content += f'boot_splash/image="{splash_godot_path}"\n'
        project_content += 'boot_splash/stretch_mode=0\n'

    project_content += f"""
[rendering]
anti_aliasing/quality/msaa_3d={props.mx_msaa}
anti_aliasing/quality/screen_space_aa={props.mx_screen_space_aa}
anti_aliasing/quality/use_taa={str(props.mx_taa).lower()}
anti_aliasing/quality/use_debanding={str(props.mx_use_debanding).lower()}
scaling_3d/mode={props.mx_scaling_3d_mode}
scaling_3d/scale={props.mx_scaling_3d_scale}
scaling_3d/fsr_sharpness={props.mx_fsr_sharpness}

"""

    if props.mx_platform == 'XR':
        project_content += """[xr]
openxr/enabled=true
shaders/enabled=true

[physics]
common/physics_ticks_per_second=90

"""

    if props.mx_use_lightmapper:
        project_content += """[editor_plugins]

enabled=PackedStringArray("res://addons/naxplus/plugin.cfg", "res://addons/blender_livelink/plugin.cfg")

"""

    with open(project_file, 'w') as f:
        f.write(project_content)

    print(f"Created/Updated project.godot")
    return project_dir


def create_scene_config(project_dir, scene_name, props, script_assignments=None):
    """Write scene_config.json for Godot plugins to read."""

    config_path = os.path.join(project_dir, "scene_config.json")

    config_data = {
        "project_name": props.mx_project_name or "Blender Export",
        "project_version": props.mx_project_version,
        "scene_name": scene_name,
        "export_timestamp": time.time(),
        "blender_version": bpy.app.version_string,
        "livelink": props.mx_livelink_enabled,
        "livelink_godot_port": props.mx_livelink_godot_port,
        "livelink_blender_port": props.mx_livelink_blender_port,
        "lightmap_mode": props.mx_lightmap_mode.lower(),
        "lightmap_bicubic_filtering": props.mx_lightmap_bicubic_filtering,
        "auto_close_after_automation": True,
        "script_assignments": script_assignments or {}
    }

    with open(config_path, 'w') as f:
        json.dump(config_data, f, indent=4)

    print(f"Created scene config")
    if script_assignments:
        print(f"  Script assignments: {len(script_assignments)}")


def copy_lightmaps(context, props):
    """Copy lightmaps from {blend_dir}/Lightmaps/ to Godot project."""

    if not props.mx_use_lightmapper:
        return

    blend_file_path = bpy.data.filepath
    if not blend_file_path:
        print("Warning: Cannot copy lightmaps - blend file not saved")
        return

    blend_dir = os.path.dirname(blend_file_path)
    source_lightmaps = os.path.join(blend_dir, "Lightmaps")

    if os.path.exists(source_lightmaps) and os.path.isdir(source_lightmaps):
        dest_lightmaps = os.path.join(props.mx_godot_project_path, "assets", "lightmaps")

        texture_extensions = {'.exr', '.hdr', '.png', '.jpg', '.jpeg', '.webp'}
        for item in os.listdir(source_lightmaps):
            source_item = os.path.join(source_lightmaps, item)
            dest_item = os.path.join(dest_lightmaps, item)

            if os.path.isfile(source_item):
                shutil.copy2(source_item, dest_item)
            elif os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item, dirs_exist_ok=True)

        print(f"Lightmaps copied")

        flag_file = os.path.join(props.mx_godot_project_path, ".lightmaps_applied")
        if os.path.exists(flag_file):
            os.remove(flag_file)
            print("Removed old lightmap flag - will re-apply on startup")


def apply_lightmap_import_settings(project_dir, props):
    """Patch lightmap .import files after headless import has run."""

    compress_mode = int(props.mx_lightmap_compress_mode)
    mipmaps = str(props.mx_lightmap_mipmaps).lower()

    lightmaps_dir = os.path.join(project_dir, "assets", "lightmaps")
    if not os.path.isdir(lightmaps_dir):
        return

    texture_extensions = {'.exr', '.hdr', '.png', '.jpg', '.jpeg', '.webp'}
    patched = 0

    for item in os.listdir(lightmaps_dir):
        if os.path.splitext(item)[1].lower() not in texture_extensions:
            continue

        import_path = os.path.join(lightmaps_dir, item + ".import")
        if not os.path.exists(import_path):
            continue

        with open(import_path, 'r') as f:
            content = f.read()

        content = re.sub(r'^compress/mode=\S+', f'compress/mode={compress_mode}', content, flags=re.MULTILINE)
        content = re.sub(r'^mipmaps/generate=\S+', f'mipmaps/generate={mipmaps}', content, flags=re.MULTILINE)

        with open(import_path, 'w') as f:
            f.write(content)

        for ctex_res in re.findall(r'^path[^=]*="(res://[^"]+\.ctex)"', content, flags=re.MULTILINE):
            ctex_abs = os.path.join(project_dir, ctex_res.replace("res://", "").replace("/", os.sep))
            if os.path.exists(ctex_abs):
                os.remove(ctex_abs)
                print(f"  Invalidated cache: {ctex_res}")

        patched += 1
        print(f"Patched import settings: {item} (compress={compress_mode}, mipmaps={mipmaps})")

    print(f"Lightmap import settings applied to {patched} texture(s)")


def copy_custom_scripts(project_dir):
    """Copy .gd files from {blend_dir}/scripts/ to the Godot project's scripts/ folder."""

    blend_file_path = bpy.data.filepath
    if not blend_file_path:
        return

    source_scripts = os.path.join(os.path.dirname(blend_file_path), "scripts")
    if not os.path.isdir(source_scripts):
        return

    dest_scripts = os.path.join(project_dir, "scripts")
    if not os.path.exists(dest_scripts):
        os.makedirs(dest_scripts)

    copied = 0
    for filename in os.listdir(source_scripts):
        if filename.endswith('.gd'):
            src = os.path.join(source_scripts, filename)
            dst = os.path.join(dest_scripts, filename)
            shutil.copy2(src, dst)
            copied += 1

    if copied:
        print(f"Copied {copied} custom script(s)")


def _get_node_path(obj):
    """Return the full Godot node path for a Blender object, following the parent chain.
    e.g. a Cube_005 parented to Cube_004 → 'Cube_004/Cube_005'
    Root-level objects return just their safe name."""
    parts = [util.safe_name(obj.name)]
    parent = obj.parent
    while parent:
        parts.insert(0, util.safe_name(parent.name))
        parent = parent.parent
    return '/'.join(parts)


def collect_script_assignments(context):
    """Return dict of node path → script filename for all enabled scripts.
    Keys use full hierarchy paths (e.g. 'Parent/Child') so the inherited scene
    can write the correct parent= attribute for nested nodes."""

    assignments = {}

    for obj in bpy.data.objects:
        obj_props = obj.MX_ObjectProperties

        if len(obj_props.mx_scripts) > 0:
            for script_item in obj_props.mx_scripts:
                if not script_item.enabled:
                    continue

                script_file = None
                if script_item.script_type == 'BUNDLED' and script_item.bundled_script and script_item.bundled_script != 'NONE':
                    script_file = script_item.bundled_script
                elif script_item.script_type == 'GDSCRIPT':
                    if script_item.custom_script and script_item.custom_script != 'NONE':
                        script_file = script_item.custom_script
                    elif script_item.script_path:
                        script_file = script_item.script_path
                        if script_file.startswith('res://scripts/'):
                            script_file = script_file[len('res://scripts/'):]

                if script_file:
                    node_path = _get_node_path(obj)
                    assignments[node_path] = script_file
                    print(f"Script assignment: {node_path} -> {script_file}")
                    break

    return assignments


def collect_mesh_render_layers():
    """Return dict of node path → bitmask for mesh objects with non-default render layers."""

    overrides = {}
    for obj in bpy.data.objects:
        if obj.type not in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            continue
        obj_props = obj.MX_ObjectProperties
        if not obj_props.mx_export_object:
            continue
        bitmask = util.bool_vector_to_bitmask(obj_props.mx_render_layers)
        if bitmask != 1:
            overrides[_get_node_path(obj)] = bitmask
    return overrides


def split_script_assignments(script_assignments):
    """Split assignments into mesh (inherited scene) vs scene-node (main.tscn) groups.

    Mesh assignments keep their full node path (e.g. 'Parent/Child') so the
    inherited scene can write the correct parent= for nested nodes.
    Camera/light assignments are normalised to just their leaf name because
    main.tscn always places them as direct children of the Main node."""

    mesh_assignments = {}
    scene_node_assignments = {}

    for node_path, script_file in script_assignments.items():
        leaf_name = node_path.split('/')[-1]
        obj = None
        for o in bpy.data.objects:
            if util.safe_name(o.name) == leaf_name:
                obj = o
                break

        if obj and obj.type in ('CAMERA', 'LIGHT', 'LIGHT_PROBE'):
            # main.tscn always emits cameras/lights as root-level nodes → use leaf name
            scene_node_assignments[leaf_name] = script_file
        else:
            mesh_assignments[node_path] = script_file

    return mesh_assignments, scene_node_assignments


def copy_bundled_essential(context, project_dir):
    """Copy essential bundled folders (addons, assets, scripts) — always copied."""

    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    bundled_dir = os.path.join(addon_dir, "bundled")

    print(f"Looking for bundled folder at: {bundled_dir}")

    if not os.path.exists(bundled_dir):
        print(f"Info: Bundled folder not found at: {bundled_dir}")
        return

    if not os.path.isdir(bundled_dir):
        print(f"Warning: Bundled path exists but is not a directory: {bundled_dir}")
        return

    essential_folders = ["addons", "assets", "scripts"]
    copied_count = 0

    for folder in essential_folders:
        source_folder = os.path.join(bundled_dir, folder)

        if os.path.exists(source_folder) and os.path.isdir(source_folder):
            dest_folder = os.path.join(project_dir, folder)
            items = os.listdir(source_folder)

            print(f"Copying {len(items)} items from Bundled/{folder}...")

            for item in items:
                source_item = os.path.join(source_folder, item)
                dest_item = os.path.join(dest_folder, item)

                if os.path.isfile(source_item):
                    shutil.copy2(source_item, dest_item)
                    print(f"  Copied file: {folder}/{item}")
                    copied_count += 1
                elif os.path.isdir(source_item):
                    shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
                    print(f"  Copied folder: {folder}/{item}")
                    copied_count += 1
        else:
            print(f"Info: Bundled/{folder} not found, skipping")

    if copied_count > 0:
        print(f"Essential bundled folders copied ({copied_count} items)")
    else:
        print("No essential bundled items to copy")


def copy_bundled_optional(context, project_dir):
    """Copy optional bundled folders (scenes, shaders) — only with CTRL/SHIFT."""

    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    bundled_dir = os.path.join(addon_dir, "bundled")

    if os.path.exists(bundled_dir) and os.path.isdir(bundled_dir):
        optional_folders = ["scenes", "shaders"]

        for folder in optional_folders:
            source_folder = os.path.join(bundled_dir, folder)

            if os.path.exists(source_folder) and os.path.isdir(source_folder):
                dest_folder = os.path.join(project_dir, folder)

                for item in os.listdir(source_folder):
                    source_item = os.path.join(source_folder, item)
                    dest_item = os.path.join(dest_folder, item)

                    if os.path.isfile(source_item):
                        shutil.copy2(source_item, dest_item)
                    elif os.path.isdir(source_item):
                        shutil.copytree(source_item, dest_item, dirs_exist_ok=True)

        print(f"Optional bundled folders copied (scenes, shaders)")


def copy_bundled_assets(context, project_dir):
    """Copy all bundled assets — essential + optional + custom scripts."""
    copy_bundled_essential(context, project_dir)
    copy_bundled_optional(context, project_dir)
    copy_custom_scripts(project_dir)
