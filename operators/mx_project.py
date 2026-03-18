import bpy, os, shutil


class MX_OT_CleanProject(bpy.types.Operator):
    """Clean/remove the Godot project"""
    bl_idname = "mx.clean_project"
    bl_label = "Clean Project"
    bl_description = "Remove the Godot project folder (WARNING: This will delete all project files!)"
    bl_options = {'REGISTER', 'UNDO'}

    confirm: bpy.props.BoolProperty(default=False, options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def draw(self, context):
        layout = self.layout
        layout.label(text="This will permanently delete the Godot project folder!", icon='ERROR')
        layout.label(text="Are you sure you want to continue?")

    def execute(self, context):
        props = context.scene.MX_SceneProperties

        if not props.mx_godot_project_path:
            self.report({'ERROR'}, "No Godot project path set")
            return {'CANCELLED'}

        project_path = props.mx_godot_project_path

        if not os.path.exists(project_path):
            self.report({'WARNING'}, "Project folder does not exist")
            return {'CANCELLED'}

        project_file = os.path.join(project_path, "project.godot")
        if not os.path.exists(project_file):
            self.report({'ERROR'}, "project.godot not found. Not a valid Godot project.")
            return {'CANCELLED'}

        try:
            shutil.rmtree(project_path)
            self.report({'INFO'}, f"Deleted Godot project: {project_path}")
            print(f"Cleaned Godot project folder: {project_path}")
            props.mx_godot_project_path = ""
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete project: {str(e)}")
            return {'CANCELLED'}


class MX_OT_BrowseGodotProject(bpy.types.Operator):
    bl_idname = "mx.browse_godot_project"
    bl_label = "Browse"
    bl_description = "Browse for Godot project directory"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(name="Godot Project Directory", subtype='DIR_PATH')

    def execute(self, context):
        context.scene.MX_SceneProperties.mx_godot_project_path = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        blend_file = bpy.data.filepath
        if blend_file:
            self.directory = os.path.dirname(blend_file)
        else:
            self.directory = os.path.expanduser("~")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MX_OT_BrowseLightmapPath(bpy.types.Operator):
    bl_idname = "mx.browse_lightmap_path"
    bl_label = "Browse"
    bl_description = "Browse for lightmap directory"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(name="Lightmap Directory", subtype='DIR_PATH')

    def execute(self, context):
        context.scene.MX_SceneProperties.mx_lightmap_export_path = self.directory
        return {'FINISHED'}

    def invoke(self, context, event):
        props = context.scene.MX_SceneProperties
        blend_file = bpy.data.filepath
        if blend_file:
            self.directory = os.path.dirname(blend_file)
        elif props.mx_godot_project_path and os.path.exists(props.mx_godot_project_path):
            self.directory = props.mx_godot_project_path
        else:
            self.directory = os.path.expanduser("~")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class MX_OT_CreateGodotProject(bpy.types.Operator):
    bl_idname = "mx.create_godot_project"
    bl_label = "Create"
    bl_description = "Create a new Godot project directory"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Save your Blender file first")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(blend_file)
        blend_name = os.path.splitext(os.path.basename(blend_file))[0]
        project_dir = os.path.join(blend_dir, f"{blend_name}_godot")

        if not os.path.exists(project_dir):
            os.makedirs(project_dir)
            self.report({'INFO'}, f"Created: {project_dir}")

        context.scene.MX_SceneProperties.mx_godot_project_path = project_dir
        return {'FINISHED'}
