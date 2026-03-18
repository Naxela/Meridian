import bpy
from bpy.utils import register_class, unregister_class
from . import mx_export, mx_project, mx_publish, mx_misc, object, livelink
from ..assetstore import bm

classes = [
    # Primary workflow operators
    mx_export.MX_OT_ExportMesh,
    mx_export.MX_OT_InitializeProject,
    mx_export.MX_OT_Compile,
    mx_export.MX_OT_Play,

    # Project management operators
    mx_project.MX_OT_CleanProject,
    mx_project.MX_OT_BrowseGodotProject,
    mx_project.MX_OT_BrowseLightmapPath,
    mx_project.MX_OT_CreateGodotProject,

    # LiveLink operators
    livelink.MX_OT_LiveLink,
    livelink.MX_OT_LiveLinkStop,

    # Misc / deprecated operators
    mx_misc.MX_OT_TestLiveLink,
    mx_misc.MX_OT_RunTests,
    mx_misc.MX_OT_QuickExport,
    mx_misc.MX_OT_RefreshLightmaps,
    mx_misc.MX_OpenEditor,

    # Publishing
    mx_publish.MX_OT_Publish,

    # Object operators (script list)
    object.MX_OT_AddScript,
    object.MX_OT_RemoveScript,
    object.MX_OT_NewScript,
    object.MX_OT_EditScript,
    object.MX_OT_RefreshScripts,
    object.MX_OT_ApplyBundledScript,

    # Add menu
    object.MX_OT_AddDecal,
    object.MX_MT_AddMeridian,

    # Asset Kiosk
    bm.BM_OT_OpenKiosk,
    bm.BM_OT_CloseKiosk,
]

def register():
    for cls in classes:
        register_class(cls)
    bpy.types.VIEW3D_MT_add.append(object.menu_func_add)

def unregister():
    bpy.types.VIEW3D_MT_add.remove(object.menu_func_add)
    for cls in reversed(classes):
        unregister_class(cls)
