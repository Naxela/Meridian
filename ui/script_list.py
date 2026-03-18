import bpy


class MX_UL_ScriptList(bpy.types.UIList):
    """UIList for displaying scripts attached to an object"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        script = item

        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Enable toggle
            layout.prop(script, "enabled", text="", emboss=False, icon='CHECKBOX_HLT' if script.enabled else 'CHECKBOX_DEHLT')

            # Script name
            layout.prop(script, "name", text="", emboss=False, icon='FILE_SCRIPT')

            # Script type icon
            if script.script_type == 'BUNDLED':
                layout.label(text="", icon='PACKAGE')
            else:
                layout.label(text="", icon='FILE_TEXT')

        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='FILE_SCRIPT')
