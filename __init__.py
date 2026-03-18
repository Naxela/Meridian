"""
Copyright (C) 2025 Alexander "Naxela" Kleemann.
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

bl_info = {
    "name": "Meridian",
    "author": "Alexander 'Naxela' Kleemann",
    "location": "Properties > Render Properties > Meridian",
    "version": (2, 0, 0),
    "blender": (4, 5, 0),
    "description": "Bridging Blender and Godot",
    'tracker_url': "",
    "category": "Import-Export"
}

try:
    import traceback
    import bpy
    import os

    from bpy.utils import register_class, unregister_class
    from bpy.props import StringProperty

    from . import operators, panels, properties, logo_handler
    from .operators.mx_export import mx_auto_export_on_save


    class MX_AddonPreferences(bpy.types.AddonPreferences):
        bl_idname = __package__

        godot_path: StringProperty(
            name="Godot Executable",
            description="Path to the Godot editor executable",
            subtype='FILE_PATH',
            default="",
        )

        def draw(self, context):
            layout = self.layout
            layout.use_property_split = True
            layout.use_property_decorate = False
            col = layout.column()
            col.prop(self, "godot_path", text="Godot Executable")
            if self.godot_path and not os.path.isfile(self.godot_path):
                col.label(text="File not found", icon='ERROR')


    def register():
        register_class(MX_AddonPreferences)
        panels.register()
        operators.register()
        properties.register()
        logo_handler.load_logo()
        bpy.app.handlers.save_post.append(mx_auto_export_on_save)


    def unregister():
        if mx_auto_export_on_save in bpy.app.handlers.save_post:
            bpy.app.handlers.save_post.remove(mx_auto_export_on_save)
        logo_handler.unload_logo()
        panels.unregister()
        operators.unregister()
        properties.unregister()
        unregister_class(MX_AddonPreferences)
        

except Exception:
    print(traceback.format_exc())