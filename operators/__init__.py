import bpy
from bpy.utils import register_class, unregister_class

from . import operators

classes = [
    operators.NX_Stop,
    operators.NX_Clean,
    operators.NX_Explore,
    operators.NX_Play,

    operators.NX_ModuleListNewItem,
    operators.NX_ModuleListRemoveItem,
    operators.NX_NewJavascriptFile,
    operators.NX_EditJavascriptFile,
    operators.NX_RefreshScripts,
    operators.NX_OpenStore,
]

def register():
    for cls in classes:
        register_class(cls)
        
def unregister():
    for cls in classes:
        unregister_class(cls)