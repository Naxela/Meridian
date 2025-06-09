import bpy
from bpy.props import *
from bpy.types import Menu, Panel

class NEST_PT_MaterialMenu(bpy.types.Panel):
    bl_label = "NEST Engine"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"
    #bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        mat = bpy.context.material

        if mat:

            if mat.NEST_MaterialProperties:
                mat_props = mat.NEST_MaterialProperties
                layout.use_property_split = True
                layout.use_property_decorate = False

                row = layout.row(align=True)
                row.label(text="Material settings")
                row = layout.row(align=True)
                
                row.prop(mat_props, 'nest_material_reflectance')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_texture_x_expression')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_texture_y_expression')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_blend_mode')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_diffuse_transmission')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_specular_transmission')
                row = layout.row(align=True)
                row.prop(mat_props, 'nest_material_ior')
                row = layout.row(align=True)