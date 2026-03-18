import bpy, os, subprocess, time, shutil
from ..utility import util
from . import scene_builder, project_setup
from .mx import MX_OperatorBase


def _gltf_supports_image_max_size():
    try:
        bpy.ops.export_scene.gltf.get_rna_type().properties['export_image_max_size']
        return True
    except (KeyError, AttributeError):
        return False

_GLTF_HAS_IMAGE_MAX_SIZE = None  # cached after first check


def _apply_image_max_size(gltf_kwargs, props):
    """Add export_image_max_size to kwargs if the exporter supports it and conversion is enabled."""
    global _GLTF_HAS_IMAGE_MAX_SIZE
    if not props.mx_convert_materials:
        return
    if _GLTF_HAS_IMAGE_MAX_SIZE is None:
        _GLTF_HAS_IMAGE_MAX_SIZE = _gltf_supports_image_max_size()
        if not _GLTF_HAS_IMAGE_MAX_SIZE:
            print("Meridian: export_image_max_size not supported by this Blender's glTF exporter — Max Texture Size setting will have no effect")
    if _GLTF_HAS_IMAGE_MAX_SIZE:
        gltf_kwargs['export_image_max_size'] = int(props.mx_texture_max_size)


# ===== AUTO-EXPORT SAVE HANDLER =====

@bpy.app.handlers.persistent
def mx_auto_export_on_save(dummy):
    """Handler that auto-exports mesh to Godot when saving, if enabled."""
    try:
        props = bpy.context.scene.MX_SceneProperties
        if props.mx_auto_export and props.mx_godot_project_path:
            print("Meridian: Auto-export triggered on save...")
            bpy.ops.mx.export_mesh('EXEC_DEFAULT')
    except Exception as e:
        print(f"Meridian: Auto-export failed: {e}")


# ===== PRIMARY WORKFLOW OPERATORS =====

class MX_OT_ExportMesh(bpy.types.Operator, MX_OperatorBase):
    """Lightweight mesh-only export — used by auto-export on save."""
    bl_idname = "mx.export_mesh"
    bl_label = "Export Mesh"
    bl_description = "Export mesh to Godot without updating scene files (used by auto-export)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.MX_SceneProperties

        if not props.mx_godot_project_path:
            self.report({'ERROR'}, "Godot project path not set.")
            return {'CANCELLED'}

        try:
            scene_name = util.get_scene_name(context)
            meshes_dir = os.path.join(props.mx_godot_project_path, "assets", "meshes")
            export_format = 'GLTF_SEPARATE' if props.mx_export_format == 'GLTF' else 'GLB'
            file_ext = 'gltf' if props.mx_export_format == 'GLTF' else 'glb'
            export_path = os.path.join(meshes_dir, f"{scene_name}.{file_ext}")

            if os.path.isdir(meshes_dir):
                for f in os.listdir(meshes_dir):
                    if f.startswith(scene_name + '.'):
                        os.remove(os.path.join(meshes_dir, f))

            mat_state = util.prepare_materials_for_export(props)
            hidden_objects = self.hide_non_exported_objects()
            try:
                gltf_kwargs = dict(
                    filepath=export_path,
                    export_format=export_format,
                    export_draco_mesh_compression_enable=False,
                    export_apply=props.mx_export_apply_modifiers,
                    export_lights=False,
                    export_cameras=False,
                    export_extras=props.mx_export_custom_properties,
                    use_visible=True,
                    use_renderable=True,
                    use_active_scene=True,
                    export_yup=True,
                    export_animations=props.mx_export_animations,
                )
                _apply_image_max_size(gltf_kwargs, props)
                bpy.ops.export_scene.gltf(**gltf_kwargs)
            finally:
                self.restore_hidden_objects(hidden_objects)
                util.restore_materials_after_export(mat_state)

            print(f"Meridian: Mesh exported → {export_path}")
            self.report({'INFO'}, "Mesh exported")
            return {'FINISHED'}

        except Exception as e:
            print(f"Meridian: Mesh export failed: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


class MX_OT_InitializeProject(bpy.types.Operator, MX_OperatorBase):
    """Initialize a new Godot project with full setup"""
    bl_idname = "mx.initialize_project"
    bl_label = "Initialize Project"
    bl_description = "Create new Godot project with full setup (folders, lightmaps, bundled assets, scene export)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.MX_SceneProperties

        if not props.mx_godot_project_path:
            blend_file = bpy.data.filepath
            if not blend_file:
                self.report({'ERROR'}, "Save your Blender file first")
                return {'CANCELLED'}

            blend_dir = os.path.dirname(blend_file)
            blend_name = os.path.splitext(os.path.basename(blend_file))[0]
            project_dir = os.path.join(blend_dir, f"{blend_name}_godot")
            props.mx_godot_project_path = project_dir
            print(f"Auto-created project path: {project_dir}")

        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            scene_name = util.get_scene_name(context)
            print(f"Initializing project with scene: {scene_name}")
            wm.progress_update(5)

            print("Collecting script assignments...")
            script_assignments = project_setup.collect_script_assignments(context)
            mesh_scripts, scene_node_scripts = project_setup.split_script_assignments(script_assignments)
            mesh_layer_overrides = project_setup.collect_mesh_render_layers()

            print("Creating project structure...")
            project_setup.createGodotProject(props.mx_godot_project_path, props)
            util.createFolderStructure(props.mx_godot_project_path)
            project_setup.create_scene_config(props.mx_godot_project_path, scene_name, props, script_assignments)
            wm.progress_update(15)

            print("Extracting scene data...")
            cameras, lights = util.extract_cameras_and_lights()
            probes = util.extract_reflection_probes()
            decals = util.extract_decals()
            wm.progress_update(20)

            print("Extracting environment data...")
            env_data = util.extract_environment_data(
                props.mx_godot_project_path,
                world=props.mx_export_world_override or bpy.context.scene.world
            )
            wm.progress_update(25)

            print("Copying lightmaps and bundled assets...")
            project_setup.copy_lightmaps(context, props)
            project_setup.copy_bundled_assets(context, props.mx_godot_project_path)
            wm.progress_update(40)

            print("Exporting GLTF/GLB...")
            meshes_dir = os.path.join(props.mx_godot_project_path, "assets", "meshes")
            export_format = 'GLTF_SEPARATE' if props.mx_export_format == 'GLTF' else 'GLB'
            file_ext = 'gltf' if props.mx_export_format == 'GLTF' else 'glb'
            export_path = os.path.join(meshes_dir, f"{scene_name}.{file_ext}")

            mat_state = util.prepare_materials_for_export(props)
            hidden_objects = self.hide_non_exported_objects()
            try:
                gltf_kwargs = dict(
                    filepath=export_path,
                    export_format=export_format,
                    export_draco_mesh_compression_enable=False,
                    export_apply=props.mx_export_apply_modifiers,
                    export_lights=False,
                    export_cameras=False,
                    export_extras=props.mx_export_custom_properties,
                    use_visible=True,
                    use_renderable=True,
                    use_active_scene=True,
                    export_yup=True,
                    export_animations=props.mx_export_animations,
                )
                _apply_image_max_size(gltf_kwargs, props)
                bpy.ops.export_scene.gltf(**gltf_kwargs)
            finally:
                self.restore_hidden_objects(hidden_objects)
                util.restore_materials_after_export(mat_state)
            wm.progress_update(60)

            if props.mx_create_inherited_scene:
                scene_builder.create_inherited_scene_file(
                    props.mx_godot_project_path, scene_name, props,
                    mesh_scripts, mesh_layer_overrides
                )

            print("Creating main scene...")
            scenes_dir = os.path.join(props.mx_godot_project_path, "scenes")
            main_scene_file = os.path.join(scenes_dir, "main.tscn")
            scene_content = scene_builder.generate_godot_scene(
                cameras, lights, probes, scene_name, env_data, props,
                has_model=True, use_lightmaps=props.mx_use_lightmapper,
                script_assignments=scene_node_scripts,
                decals=decals
            )

            with open(main_scene_file, 'w') as f:
                f.write(scene_content)
            wm.progress_update(75)

            if os.path.exists(self.godot_path):
                print("Running Godot import (headless)...")
                subprocess.run(
                    [self.godot_path, "--headless", "--path", props.mx_godot_project_path, "--import"],
                    capture_output=True, text=True
                )
                print("Import complete!")

                if props.mx_use_lightmapper:
                    print("Applying lightmap import settings...")
                    project_setup.apply_lightmap_import_settings(props.mx_godot_project_path, props)

                if props.mx_use_lightmapper:
                    print("Opening Godot editor for lightmap automation...")
                    subprocess.Popen([self.godot_path, "--editor", "--path", props.mx_godot_project_path])

            wm.progress_update(100)
            wm.progress_end()

            props.mx_platform_initialized = props.mx_platform
            self.report({'INFO'}, f"Project initialized: {props.mx_godot_project_path}")
            return {'FINISHED'}

        except Exception as e:
            wm.progress_end()
            print(f"Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Initialization failed: {str(e)}")
            return {'CANCELLED'}


class MX_OT_Compile(bpy.types.Operator, MX_OperatorBase):
    """Compile/export scene to Godot (quick update)"""
    bl_idname = "mx.compile"
    bl_label = "Compile"
    bl_description = "Export GLTF and update scene (CTRL: include lightmaps/bundled + open editor | SHIFT: full compile + play)"
    bl_options = {'REGISTER', 'UNDO'}

    ctrl_held: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    shift_held: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def invoke(self, context, event):
        self.ctrl_held = event.ctrl
        self.shift_held = event.shift

        if self.shift_held:
            print("SHIFT held - will include everything and auto-play")
        elif self.ctrl_held:
            print("CTRL held - will include lightmaps and bundled assets")

        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        props = scene.MX_SceneProperties

        if not props.mx_godot_project_path:
            self.report({'ERROR'}, "Godot project path not set.")
            return {'CANCELLED'}

        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            scene_name = util.get_scene_name(context)
            print(f"Compiling scene: {scene_name}")
            wm.progress_update(10)

            project_setup.copy_bundled_essential(context, props.mx_godot_project_path)
            project_setup.copy_custom_scripts(props.mx_godot_project_path)

            if self.ctrl_held or self.shift_held:
                print("Copying lightmaps and optional bundled assets...")
                project_setup.copy_lightmaps(context, props)
                project_setup.copy_bundled_optional(context, props.mx_godot_project_path)

            wm.progress_update(25)

            print("Extracting scene data...")
            cameras, lights = util.extract_cameras_and_lights()
            probes = util.extract_reflection_probes()
            decals = util.extract_decals()
            env_data = util.extract_environment_data(
                props.mx_godot_project_path,
                world=props.mx_export_world_override or bpy.context.scene.world
            )

            print("Collecting script assignments...")
            script_assignments = project_setup.collect_script_assignments(context)
            mesh_scripts, scene_node_scripts = project_setup.split_script_assignments(script_assignments)
            mesh_layer_overrides = project_setup.collect_mesh_render_layers()
            project_setup.create_scene_config(props.mx_godot_project_path, scene_name, props, script_assignments)
            wm.progress_update(35)

            meshes_dir = os.path.join(props.mx_godot_project_path, "assets", "meshes")
            export_format = 'GLTF_SEPARATE' if props.mx_export_format == 'GLTF' else 'GLB'
            file_ext = 'gltf' if props.mx_export_format == 'GLTF' else 'glb'
            export_path = os.path.join(meshes_dir, f"{scene_name}.{file_ext}")

            if os.path.isdir(meshes_dir):
                for f in os.listdir(meshes_dir):
                    if f.startswith(scene_name + '.'):
                        os.remove(os.path.join(meshes_dir, f))
                        print(f"Cleaned: assets/meshes/{f}")

            import_cache = os.path.join(props.mx_godot_project_path, ".godot", "imported")
            if os.path.isdir(import_cache):
                for f in os.listdir(import_cache):
                    if f.startswith(f"{scene_name}."):
                        cache_path = os.path.join(import_cache, f)
                        if os.path.isfile(cache_path):
                            os.remove(cache_path)
                        elif os.path.isdir(cache_path):
                            shutil.rmtree(cache_path)
                        print(f"Cleaned cache: .godot/imported/{f}")

            inherited_scene_path = os.path.join(props.mx_godot_project_path, "scenes", f"{scene_name}.tscn")
            if os.path.exists(inherited_scene_path):
                os.remove(inherited_scene_path)
                print("Cleaned inherited scene (will be recreated)")

            print("Exporting GLTF/GLB...")
            print(f"Export path: {export_path}")
            print(f"Export format: {export_format}")

            mat_state = util.prepare_materials_for_export(props)
            hidden_objects = self.hide_non_exported_objects()
            try:
                gltf_kwargs = dict(
                    filepath=export_path,
                    export_format=export_format,
                    export_draco_mesh_compression_enable=False,
                    export_apply=props.mx_export_apply_modifiers,
                    export_lights=False,
                    export_cameras=False,
                    export_extras=props.mx_export_custom_properties,
                    use_visible=True,
                    use_renderable=True,
                    use_active_scene=True,
                    export_yup=True,
                    export_animations=props.mx_export_animations,
                )
                _apply_image_max_size(gltf_kwargs, props)
                bpy.ops.export_scene.gltf(**gltf_kwargs)
            finally:
                self.restore_hidden_objects(hidden_objects)
                util.restore_materials_after_export(mat_state)

            if os.path.exists(export_path):
                file_size = os.path.getsize(export_path)
                print(f"GLTF export successful: {export_path} ({file_size} bytes)")
            else:
                print(f"WARNING: GLTF file not found after export: {export_path}")

            wm.progress_update(70)

            scene_builder.create_inherited_scene_file(
                props.mx_godot_project_path, scene_name, props,
                mesh_scripts, mesh_layer_overrides
            )

            print("Updating main scene...")
            scenes_dir = os.path.join(props.mx_godot_project_path, "scenes")
            main_scene_file = os.path.join(scenes_dir, "main.tscn")
            scene_content = scene_builder.generate_godot_scene(
                cameras, lights, probes, scene_name, env_data, props,
                has_model=True, use_lightmaps=props.mx_use_lightmapper,
                script_assignments=scene_node_scripts,
                decals=decals
            )

            with open(main_scene_file, 'w') as f:
                f.write(scene_content)

            wm.progress_update(90)

            if os.path.exists(self.godot_path):
                if os.path.exists(export_path):
                    print(f"GLTF file verified before import: {export_path}")
                else:
                    print(f"WARNING: GLTF file missing before import: {export_path}")

                print("Running quick import...")
                subprocess.run(
                    [self.godot_path, "--headless", "--path", props.mx_godot_project_path, "--import"],
                    capture_output=True, text=True
                )

                if os.path.exists(export_path):
                    print(f"GLTF file verified after import: {export_path}")
                else:
                    print(f"WARNING: GLTF file missing after import: {export_path}")

                if self.shift_held:
                    print("Waiting for import to complete...")
                    import_file = os.path.join(
                        props.mx_godot_project_path, "assets", "meshes",
                        f"{scene_name}.{file_ext}.import"
                    )
                    max_wait = 5.0
                    wait_interval = 0.1
                    elapsed = 0.0
                    while elapsed < max_wait and not os.path.exists(import_file):
                        time.sleep(wait_interval)
                        elapsed += wait_interval

                    if os.path.exists(import_file):
                        time.sleep(0.5)
                        print("Import complete!")
                    else:
                        print(f"Warning: Import file not found after {max_wait}s, launching anyway...")

            if os.path.exists(self.godot_path):
                if self.shift_held:
                    print("Launching Godot...")
                    subprocess.Popen([
                        self.godot_path, "--path", props.mx_godot_project_path,
                        "res://scenes/main.tscn"
                    ])
                elif self.ctrl_held:
                    print("Opening Godot editor for lightmap automation...")
                    subprocess.Popen([
                        self.godot_path, "--editor", "--path", props.mx_godot_project_path
                    ])

            wm.progress_update(100)
            wm.progress_end()

            if self.shift_held:
                self.report({'INFO'}, "Scene compiled and launched successfully")
            elif self.ctrl_held:
                self.report({'INFO'}, "Scene compiled, editor opened for lightmaps")
            else:
                self.report({'INFO'}, "Scene compiled successfully")
            return {'FINISHED'}

        except Exception as e:
            wm.progress_end()
            print(f"Compile failed: {e}")
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Compile failed: {str(e)}")
            return {'CANCELLED'}


class MX_OT_Play(bpy.types.Operator, MX_OperatorBase):
    """Launch Godot project"""
    bl_idname = "mx.play"
    bl_label = "Play"
    bl_description = "Run Godot project (Hold CTRL to open editor instead)"
    bl_options = {'REGISTER', 'UNDO'}

    ctrl_held: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def invoke(self, context, event):
        self.ctrl_held = event.ctrl
        if self.ctrl_held:
            print("CTRL held - will open editor")
        else:
            print("Running project...")
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        props = scene.MX_SceneProperties

        if not props.mx_godot_project_path:
            self.report({'ERROR'}, "Godot project path not set.")
            return {'CANCELLED'}

        project_file = os.path.join(props.mx_godot_project_path, "project.godot")
        if not os.path.exists(project_file):
            self.report({'ERROR'}, "Godot project not found. Initialize project first.")
            return {'CANCELLED'}

        if not os.path.exists(self.godot_path):
            self.report({'ERROR'}, f"Godot executable not found: {self.godot_path}")
            return {'CANCELLED'}

        try:
            print("Refreshing project files...")
            scene_name = util.get_scene_name(context)

            project_setup.copy_custom_scripts(props.mx_godot_project_path)

            script_assignments = project_setup.collect_script_assignments(context)
            mesh_scripts, scene_node_scripts = project_setup.split_script_assignments(script_assignments)
            mesh_layer_overrides = project_setup.collect_mesh_render_layers()

            project_setup.createGodotProject(props.mx_godot_project_path, props)
            project_setup.create_scene_config(props.mx_godot_project_path, scene_name, props, script_assignments)

            inherited_scene_path = os.path.join(props.mx_godot_project_path, "scenes", f"{scene_name}.tscn")
            has_lightmap_data = False
            if os.path.exists(inherited_scene_path):
                with open(inherited_scene_path, 'r') as f:
                    first_line = f.readline()
                    has_lightmap_data = 'format=4' in first_line

            if not has_lightmap_data:
                scene_builder.create_inherited_scene_file(
                    props.mx_godot_project_path, scene_name, props,
                    mesh_scripts, mesh_layer_overrides
                )
            else:
                scene_builder.update_inherited_scene_scripts(
                    props.mx_godot_project_path, scene_name,
                    mesh_scripts, mesh_layer_overrides
                )

            cameras, lights = util.extract_cameras_and_lights()
            probes = util.extract_reflection_probes()
            decals = util.extract_decals()
            env_data = util.extract_environment_data(
                props.mx_godot_project_path,
                world=props.mx_export_world_override or bpy.context.scene.world
            )

            scenes_dir = os.path.join(props.mx_godot_project_path, "scenes")
            main_scene_file = os.path.join(scenes_dir, "main.tscn")
            scene_content = scene_builder.generate_godot_scene(
                cameras, lights, probes, scene_name, env_data, props,
                has_model=True, use_lightmaps=props.mx_use_lightmapper,
                script_assignments=scene_node_scripts,
                decals=decals
            )

            with open(main_scene_file, 'w') as f:
                f.write(scene_content)

            print("Project files refreshed")

            if self.ctrl_held:
                print(f"Opening Godot editor: {props.mx_godot_project_path}")
                subprocess.Popen([self.godot_path, "--editor", "--path", props.mx_godot_project_path])
                self.report({'INFO'}, "Godot editor opened")
            else:
                print(f"Running Godot project: {props.mx_godot_project_path}")
                main_scene = os.path.join(props.mx_godot_project_path, "scenes", "main.tscn")
                if os.path.exists(main_scene):
                    subprocess.Popen([self.godot_path, "--path", props.mx_godot_project_path, "res://scenes/main.tscn"])
                    self.report({'INFO'}, "Godot project running")
                else:
                    self.report({'ERROR'}, "Main scene not found. Compile project first.")
                    return {'CANCELLED'}

            return {'FINISHED'}

        except Exception as e:
            print(f"Launch failed: {e}")
            self.report({'ERROR'}, f"Launch failed: {str(e)}")
            return {'CANCELLED'}
