import bpy, os
from bpy.utils import register_class, unregister_class
from . import scene, object

classes = [
    object.MX_ScriptItem,  # Must be registered before MX_ObjectProperties
    scene.MX_SceneProperties,
    object.MX_ObjectProperties
]

def register():
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.MX_SceneProperties = bpy.props.PointerProperty(type=scene.MX_SceneProperties)
    bpy.types.Object.MX_ObjectProperties = bpy.props.PointerProperty(type=object.MX_ObjectProperties)

def unregister():
    for cls in classes:
        unregister_class(cls)

    del bpy.types.Scene.MX_SceneProperties
    del bpy.types.Object.MX_ObjectProperties