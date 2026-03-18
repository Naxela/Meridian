import bpy
from bpy.props import *
from bpy.types import Menu, Panel
import os

class MX_PT_ObjectMenu(bpy.types.Panel):
    bl_label = "Meridian - Godot Export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.object
        layout.use_property_split = True
        layout.use_property_decorate = False

        if obj is None:
            layout.label(text="No active object")
            return

        obj_props = obj.MX_ObjectProperties

        # Export control - always stays enabled
        box = layout.box()
        col = box.column(align=True)
        col.prop(obj_props, "mx_export_object")

        # Disable everything below the checkbox when export is off
        export_enabled = obj_props.mx_export_object

        # Mesh-specific settings
        if obj.type == "MESH":
            box = layout.box()
            box.enabled = export_enabled
            box.label(text="Godot Node Settings", icon='OBJECT_DATA')
            col = box.column(align=True)
            col.prop(obj_props, "mx_object_type_override")

            # Collision settings — hidden until export support is implemented
            # LOD settings — hidden until export support is implemented

        # Camera-specific settings
        if obj.type == "CAMERA":
            box = layout.box()
            box.enabled = export_enabled
            box.label(text="Camera Attributes", icon='CAMERA_DATA')
            col = box.column(align=True)
            col.prop(obj_props, "mx_camera_attributes_type")

            attr_type = obj_props.mx_camera_attributes_type

            if attr_type == 'PRACTICAL':
                col.separator(factor=0.5)
                col.label(text="DOF Blur")
                col.prop(obj_props, "mx_cam_dof_far_enabled")
                col.prop(obj_props, "mx_cam_dof_near_enabled")
                col.prop(obj_props, "mx_cam_dof_amount")
                col.separator(factor=0.5)
                col.label(text="Auto Exposure")
                col.prop(obj_props, "mx_cam_auto_exp_min_sensitivity")
                col.prop(obj_props, "mx_cam_auto_exp_max_sensitivity")

            elif attr_type == 'PHYSICAL':
                col.separator(factor=0.5)
                col.label(text="Frustum")
                col.prop(obj_props, "mx_cam_frustum_focus_distance")
                col.prop(obj_props, "mx_cam_frustum_focal_length")
                col.prop(obj_props, "mx_cam_frustum_near")
                col.prop(obj_props, "mx_cam_frustum_far")
                col.separator(factor=0.5)
                col.label(text="Auto Exposure")
                col.prop(obj_props, "mx_cam_phys_auto_exp_min")
                col.prop(obj_props, "mx_cam_phys_auto_exp_max")

            if attr_type != 'DISABLED':
                col.separator(factor=0.5)
                col.label(text="Exposure")
                col.prop(obj_props, "mx_cam_exposure_multiplier")
                col.separator(factor=0.5)
                row = col.row(align=True)
                row.label(text="Auto Exposure")
                row.prop(obj_props, "mx_cam_auto_exp_enabled", text="On")
                if obj_props.mx_cam_auto_exp_enabled:
                    col.prop(obj_props, "mx_cam_auto_exp_scale")
                    col.prop(obj_props, "mx_cam_auto_exp_speed")

        # Render layers (meshes, lights, empties — anything with VisualInstance3D in Godot)
        if obj.type in {"MESH", "LIGHT", "EMPTY"}:
            box = layout.box()
            box.enabled = export_enabled
            box.label(text="Layers", icon='RENDERLAYERS')
            col = box.column(align=True)
            col.prop(obj_props, "mx_render_layers", text="")

        # Decal (EMPTY objects)
        if obj.type == "EMPTY":
            box = layout.box()
            box.enabled = export_enabled
            row = box.row(align=True)
            row.label(text="Decal", icon='MOD_DECIM')
            row.prop(obj_props, "mx_is_decal", text="", toggle=True, icon='CHECKBOX_HLT' if obj_props.mx_is_decal else 'CHECKBOX_DEHLT')

            if obj_props.mx_is_decal:
                col = box.column(align=True)
                col.prop(obj_props, "mx_decal_size", text="Size")
                col.separator(factor=0.5)

                col.label(text="Textures")
                col.prop(obj_props, "mx_decal_albedo_tex")
                col.prop(obj_props, "mx_decal_normal_tex")
                col.prop(obj_props, "mx_decal_orm_tex")
                col.prop(obj_props, "mx_decal_emission_tex")
                col.separator(factor=0.5)

                col.label(text="Parameters")
                col.prop(obj_props, "mx_decal_emission_energy")
                col.prop(obj_props, "mx_decal_modulate")
                col.prop(obj_props, "mx_decal_albedo_mix")
                col.prop(obj_props, "mx_decal_normal_fade")
                col.separator(factor=0.5)

                col.label(text="Vertical Fade")
                col.prop(obj_props, "mx_decal_upper_fade")
                col.prop(obj_props, "mx_decal_lower_fade")
                col.separator(factor=0.5)

                col.label(text="Distance Fade")
                col.prop(obj_props, "mx_decal_distance_fade")
                if obj_props.mx_decal_distance_fade:
                    col.prop(obj_props, "mx_decal_distance_fade_begin")
                    col.prop(obj_props, "mx_decal_distance_fade_length")
                col.separator(factor=0.5)

                col.label(text="Cull Mask")
                col.prop(obj_props, "mx_decal_cull_mask", text="")

        # Reflection probe specific
        if obj.type == "LIGHT_PROBE":
            box = layout.box()
            box.enabled = export_enabled
            box.label(text="Reflection Probe", icon='WORLD')
            col = box.column(align=True)
            col.prop(obj_props, "mx_reflection_update_mode")
            col.prop(obj_props, "mx_reflection_intensity")
            col.prop(obj_props, "mx_reflection_max_distance")
            col.prop(obj_props, "mx_reflection_ambient_mode")
            col.separator(factor=0.5)
            col.prop(obj_props, "mx_reflection_box_projection")
            col.prop(obj_props, "mx_reflection_interior")
            col.prop(obj_props, "mx_reflection_enable_shadows")
            col.prop(obj_props, "mx_reflection_blend_distance")
            col.separator()
            col.label(text="Cull Mask")
            col.prop(obj_props, "mx_reflection_cull_mask", text="")
            col.separator(factor=0.5)
            col.label(text="Reflection Mask")
            col.prop(obj_props, "mx_reflection_reflection_mask", text="")

        # Script Management (all object types) - Armory3D style
        box = layout.box()
        box.enabled = export_enabled
        box.label(text="Scripts", icon='FILE_SCRIPT')
        col = box.column(align=True)

        # Script list with +/- buttons
        row = col.row()
        row.template_list("MX_UL_ScriptList", "", obj_props, "mx_scripts", obj_props, "mx_scripts_index", rows=3)

        # Plus/Minus buttons column
        col_ops = row.column(align=True)
        col_ops.operator("mx.add_script", text="", icon='ADD')
        col_ops.operator("mx.remove_script", text="", icon='REMOVE')

        # Script details (if a script is selected)
        if len(obj_props.mx_scripts) > 0 and obj_props.mx_scripts_index < len(obj_props.mx_scripts):
            script = obj_props.mx_scripts[obj_props.mx_scripts_index]

            col.separator(factor=0.5)

            # Type dropdown
            col.prop(script, "script_type", text="Type")

            # Script selection dropdown based on type
            has_script_selected = False
            if script.script_type == 'GDSCRIPT':
                row = col.row(align=True)
                row.prop(script, "custom_script", text="")
                has_script_selected = script.custom_script and script.custom_script != 'NONE'
            elif script.script_type == 'BUNDLED':
                row = col.row(align=True)
                row.prop(script, "bundled_script", text="")
                row.operator("mx.apply_bundled_script", text="", icon='IMPORT')
                has_script_selected = script.bundled_script and script.bundled_script != 'NONE'

            # Only show buttons and parameters when a script is actually selected
            if has_script_selected:
                # Action buttons row
                col.separator(factor=0.5)
                row = col.row(align=True)
                row.scale_y = 1.1
                row.operator("mx.edit_script", icon='TEXT')
                if script.script_type != 'BUNDLED':
                    row.operator("mx.new_script", icon='FILE_NEW')
                row.operator("mx.refresh_scripts", icon='FILE_REFRESH')

                # Parameters field
                col.separator(factor=0.3)
                col.prop(script, "parameters", text="Parameters")

        # Godot Groups (metadata)
        box = layout.box()
        box.enabled = export_enabled
        box.label(text="Godot Metadata", icon='SCRIPT')
        col = box.column(align=True)
        col.prop(obj_props, "mx_godot_groups")
