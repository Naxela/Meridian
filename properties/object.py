import bpy, os
from bpy.props import *

class NX_ObjectProperties(bpy.types.PropertyGroup):

    nx_object_object_status : EnumProperty(
        items = [('Static', 'Static', 'Mark the object as static for performance optimization'),
                ('Dynamic', 'Dynamic', 'Mark the object as dynamic, for animation or physics')],
                name = "Object type", 
                description="Mark the object as static or dynamic", 
                default='Static')
    
    nx_object_export : BoolProperty(
        name="Export",
        description="Export the model when compiling scene",
        default=True
    )

    nx_object_spawn : BoolProperty(
        name="Spawn",
        description="Spawn with scene (on scene initialization)",
        default=True
    )

    nx_object_visible : BoolProperty(
        name="Visible",
        description="Visible in scene",
        default=True
    )

    nx_object_cast_shadows : BoolProperty(
        name="Cast Shadows",
        description="Set whether the object should cast shadows",
        default=True
    )

    nx_object_receive_shadows : BoolProperty(
        name="Receive Shadows",
        description="Set whether the object should receive shadows",
        default=True
    )

    nx_object_tags : StringProperty(
        name="Tags",
        description="Tags for the object, comma separated",
        default=""
    )

    nx_object_injection_code : StringProperty(
        name="Injection Code",
        description="React Injection component - For instance '<OrbitControls />'",
        default=""
    )

    nx_object_injection : EnumProperty(
        items = [('Custom', 'Custom', 'Write a custom component'),
                ('Bundled', 'Bundled', 'Enable a bundled component')],
                name = "Injection type", 
                description="Select the injection type", 
                default='Custom')
    
    nx_object_injection_bundle : EnumProperty(
        items = [('None', 'None', 'None'),
                ('OrbitControls', 'OrbitControls', 'OrbitControls')],
                name = "", 
                description="Select the bundle type", 
                default='None')

    # Speaker settings

    nx_speaker_autoplay : BoolProperty(
        name="Autoplay",
        description="Set whether the speaker should autoplay",
        default=True
    )

    nx_speaker_loop : BoolProperty(
        name="Loop",
        description="Set whether the speaker should loop",
        default=True
    )

    nx_speaker_stream : BoolProperty(
        name="Stream",
        description="Set whether the speaker should stream",
        default=False
    )

class NX_UL_ModuleList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        custom_icon = 'OBJECT_DATAMODE'

        if self.layout_type in {'DEFAULT', 'COMPACT'}:

            row = layout.row()
            row.separator(factor=0.1)
            row.prop(item, "nx_module_enabled")
            col = row.column()

            if(item.nx_module_script != ""):
                #row.label(text=item.name if item.name != "" else " ", icon=custom_icon, icon_value=custom_icon_value)
                col.label(text=item.nx_module_script)
            else:
                col.label(text="Create script")

class NX_UL_ModuleListItem(bpy.types.PropertyGroup):

    nx_module_enabled : BoolProperty(name="", description="Whether this trait is enabled", default=True, override={"LIBRARY_OVERRIDABLE"})

    nx_module_script: StringProperty(name="Module", description="The module", default="", override={"LIBRARY_OVERRIDABLE"}) #TODO ON UPDATE => FIX PROPS

    nx_module_type : EnumProperty(
        items = [('Bundled', 'Bundled', 'Select a bundled module'),
                 ('Rust', 'Rust', 'Create a Rust module'),],
                name = "Module Type", 
                description="Select the module type",
                default='Bundled')
    
    nx_module_script_format = EnumProperty(
        items = [('TypeScript', 'TypeScript', 'TypeScript format'),
                 ('JavaScript', 'JavaScript', 'JavaScript format'),],
                name = "Script format", 
                description="Select the script format",
                default='JavaScript')