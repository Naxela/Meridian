import bpy, os
from bpy.utils import register_class, unregister_class
from . import scene, object
from ..ui import script_list

classes = [
    # UI Lists
    script_list.MX_UL_ScriptList,

    # Scene panels
    scene.MX_PT_Panel,
    scene.MX_PT_ExportOptions,
    scene.MX_PT_MaterialConversion,
    scene.MX_PT_Lightmapper,
    scene.MX_PT_GodotRendering,
    scene.MX_PT_GodotTonemapping,
    scene.MX_PT_GodotGlow,
    scene.MX_PT_GodotSSR,
    scene.MX_PT_GodotSSAO,
    scene.MX_PT_GodotSSIL,
    scene.MX_PT_GodotSDFGI,
    scene.MX_PT_GodotFog,
    scene.MX_PT_GodotVolumetricFog,
    scene.MX_PT_GodotAdjustments,
    scene.MX_PT_NaxPost,
    scene.MX_PT_LiveLink,
    scene.MX_PT_Publishing,

    # Object panels
    object.MX_PT_ObjectMenu
]

def register():
    for cls in classes:
        register_class(cls)

def unregister():
    for cls in classes:
        unregister_class(cls)