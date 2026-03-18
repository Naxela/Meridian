import bpy
import os
import subprocess
import shutil


class MX_OT_AddScript(bpy.types.Operator):
    """Add a new script to the list"""
    bl_idname = "mx.add_script"
    bl_label = "Add Script"
    bl_description = "Add a new script to this object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        props = obj.MX_ObjectProperties
        script = props.mx_scripts.add()
        script.name = f"Script_{len(props.mx_scripts)}"
        script.script_type = 'GDSCRIPT'
        script.enabled = True

        props.mx_scripts_index = len(props.mx_scripts) - 1

        return {'FINISHED'}


class MX_OT_RemoveScript(bpy.types.Operator):
    """Remove the selected script from the list"""
    bl_idname = "mx.remove_script"
    bl_label = "Remove Script"
    bl_description = "Remove the selected script from this object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        props = obj.MX_ObjectProperties

        if len(props.mx_scripts) == 0:
            self.report({'WARNING'}, "No scripts to remove")
            return {'CANCELLED'}

        props.mx_scripts.remove(props.mx_scripts_index)

        if props.mx_scripts_index >= len(props.mx_scripts):
            props.mx_scripts_index = len(props.mx_scripts) - 1

        return {'FINISHED'}


class MX_OT_NewScript(bpy.types.Operator):
    """Create a new GDScript file"""
    bl_idname = "mx.new_script"
    bl_label = "New"
    bl_description = "Create a new GDScript file for the selected script entry"
    bl_options = {'REGISTER', 'UNDO'}

    script_name: bpy.props.StringProperty(
        name="Script Name",
        description="Name for the new script",
        default="NewScript"
    )

    def invoke(self, context, event):
        obj = context.active_object
        if obj:
            props = obj.MX_ObjectProperties
            if len(props.mx_scripts) > 0:
                script = props.mx_scripts[props.mx_scripts_index]
                self.script_name = script.name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        props = obj.MX_ObjectProperties

        if len(props.mx_scripts) == 0:
            self.report({'ERROR'}, "No script entry selected. Add a script first.")
            return {'CANCELLED'}

        script = props.mx_scripts[props.mx_scripts_index]

        # Get blend file directory
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Save your Blender file first")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(blend_file)
        scripts_dir = os.path.join(blend_dir, "scripts")

        # Create scripts directory if it doesn't exist
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)

        # Create script file
        script_filename = f"{self.script_name}.gd"
        script_path = os.path.join(scripts_dir, script_filename)

        if os.path.exists(script_path):
            self.report({'WARNING'}, f"Script '{script_filename}' already exists")
            return {'CANCELLED'}

        # Create basic GDScript template
        script_content = f'''extends Node3D

# Script for {obj.name}
# Created from Blender Meridian addon

# Called when the node enters the scene tree for the first time
func _ready():
\tpass


# Called every frame. 'delta' is the elapsed time since the previous frame
func _process(delta):
\tpass
'''

        with open(script_path, 'w') as f:
            f.write(script_content)

        # Update script properties
        script.name = self.script_name
        script.script_type = 'GDSCRIPT'
        script.script_path = script_filename
        script.custom_script = script_filename

        self.report({'INFO'}, f"Created script: {script_filename}")
        return {'FINISHED'}


class MX_OT_EditScript(bpy.types.Operator):
    """Open the selected script in default editor"""
    bl_idname = "mx.edit_script"
    bl_label = "Edit"
    bl_description = "Open the selected script in your default GDScript editor"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        props = obj.MX_ObjectProperties

        if len(props.mx_scripts) == 0:
            self.report({'ERROR'}, "No script selected")
            return {'CANCELLED'}

        script = props.mx_scripts[props.mx_scripts_index]

        # Get blend file directory
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Save your Blender file first")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(blend_file)
        scripts_dir = os.path.join(blend_dir, "scripts")

        # For bundled scripts, copy to local scripts folder if not already there
        if script.script_type == 'BUNDLED' and script.bundled_script and script.bundled_script != 'NONE':
            addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            bundled_path = os.path.join(addon_dir, "bundled", "scripts", script.bundled_script)

            if not os.path.exists(bundled_path):
                self.report({'ERROR'}, f"Bundled script not found: {script.bundled_script}")
                return {'CANCELLED'}

            if not os.path.exists(scripts_dir):
                os.makedirs(scripts_dir)

            dest_path = os.path.join(scripts_dir, script.bundled_script)
            if not os.path.exists(dest_path):
                shutil.copy2(bundled_path, dest_path)

            # Switch entry from Bundled to GDScript with the local copy selected
            script_filename = script.bundled_script
            script.script_type = 'GDSCRIPT'
            script.custom_script = script_filename
            script.script_path = script_filename
            script.name = os.path.splitext(script_filename)[0]
            self.report({'INFO'}, f"Copied bundled script to scripts/{script_filename} (switched to GDScript)")

            full_path = dest_path

        elif script.script_path:
            # Custom script - resolve path
            script_path = script.script_path.replace("res://", "").replace("res://scripts/", "")
            full_path = os.path.join(scripts_dir, script_path) if not os.path.sep in script_path else os.path.join(blend_dir, script_path)

        elif script.script_type == 'GDSCRIPT' and script.custom_script and script.custom_script != 'NONE':
            # Custom script selected from dropdown
            full_path = os.path.join(scripts_dir, script.custom_script)

        else:
            self.report({'ERROR'}, "No script file associated with this entry")
            return {'CANCELLED'}

        if not os.path.exists(full_path):
            self.report({'ERROR'}, f"Script not found: {full_path}")
            return {'CANCELLED'}

        # Open in default editor
        try:
            if os.name == 'nt':  # Windows
                os.startfile(full_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', full_path])

            self.report({'INFO'}, f"Opened script in default editor")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to open script: {str(e)}")
            return {'CANCELLED'}


class MX_OT_RefreshScripts(bpy.types.Operator):
    """Refresh the bundled scripts list"""
    bl_idname = "mx.refresh_scripts"
    bl_label = "Refresh"
    bl_description = "Refresh the bundled scripts list from the addon folder"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Dynamic EnumProperty callbacks re-evaluate on UI redraw, so just tag a redraw
        for area in context.screen.areas:
            area.tag_redraw()

        self.report({'INFO'}, "Refreshed bundled scripts list")
        return {'FINISHED'}


class MX_OT_ApplyBundledScript(bpy.types.Operator):
    """Apply the selected bundled script to the current entry"""
    bl_idname = "mx.apply_bundled_script"
    bl_label = "Apply Bundled Script"
    bl_description = "Copy and apply the selected bundled script"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No active object")
            return {'CANCELLED'}

        props = obj.MX_ObjectProperties

        if len(props.mx_scripts) == 0:
            self.report({'ERROR'}, "No script entry selected")
            return {'CANCELLED'}

        script = props.mx_scripts[props.mx_scripts_index]

        if script.script_type != 'BUNDLED':
            self.report({'ERROR'}, "Script type must be set to 'Bundled'")
            return {'CANCELLED'}

        if script.bundled_script == 'GDSCRIPT':
            self.report({'ERROR'}, "Please select a bundled script")
            return {'CANCELLED'}

        # Get addon directory
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        bundled_script_path = os.path.join(addon_dir, "bundled", "scripts", script.bundled_script)

        if not os.path.exists(bundled_script_path):
            self.report({'ERROR'}, f"Bundled script not found: {script.bundled_script}")
            return {'CANCELLED'}

        # Get blend file directory
        blend_file = bpy.data.filepath
        if not blend_file:
            self.report({'ERROR'}, "Save your Blender file first")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(blend_file)
        scripts_dir = os.path.join(blend_dir, "scripts")

        # Create scripts directory if needed
        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)

        # Copy bundled script to project
        dest_path = os.path.join(scripts_dir, script.bundled_script)

        if not os.path.exists(dest_path):
            shutil.copy2(bundled_script_path, dest_path)
            print(f"Copied bundled script: {script.bundled_script}")

        # Update script properties
        script_name = os.path.splitext(script.bundled_script)[0]
        script.name = script_name
        script.script_path = f"res://scripts/{script.bundled_script}"

        self.report({'INFO'}, f"Applied bundled script: {script_name}")
        return {'FINISHED'}


# ===== ADD MENU =====

class MX_OT_AddDecal(bpy.types.Operator):
    """Add a Meridian Decal empty to the scene"""
    bl_idname = "mx.add_decal"
    bl_label = "Decal"
    bl_description = "Add a Decal object (exported as a Decal node in Godot)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=context.scene.cursor.location)
        obj = context.active_object
        obj.name = "Decal"
        obj.empty_display_size = 0.25

        # Tag it so the exporter knows this is a Decal
        obj.MX_ObjectProperties.mx_object_subtype = 'DECAL'

        return {'FINISHED'}


class MX_MT_AddMeridian(bpy.types.Menu):
    """Meridian objects submenu in the Add menu"""
    bl_idname = "MX_MT_add_meridian"
    bl_label = "Meridian"

    def draw(self, context):
        layout = self.layout
        layout.operator("mx.add_decal", icon='MESH_PLANE')


def menu_func_add(self, context):
    self.layout.menu("MX_MT_add_meridian", icon='EXPORT')
