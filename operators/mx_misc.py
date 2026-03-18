import bpy, os
from . import livelink


class MX_OT_TestLiveLink(bpy.types.Operator):
    bl_idname = "mx.test_livelink"
    bl_label = "Connect LiveLink"
    bl_description = "Connect to / disconnect from Godot LiveLink"
    bl_options = {'REGISTER'}

    def execute(self, context):
        props = context.scene.MX_SceneProperties

        if not props.mx_livelink_enabled:
            self.report({'WARNING'}, "LiveLink is not enabled")
            return {'CANCELLED'}

        if livelink.is_running():
            return bpy.ops.mx.livelink_stop()
        else:
            return bpy.ops.mx.livelink_start('INVOKE_DEFAULT')


class MX_OT_RunTests(bpy.types.Operator):
    """Run unit tests for Meridian addon"""
    bl_idname = "mx.run_tests"
    bl_label = "Run Tests"
    bl_description = "Run unit tests for the Meridian addon"
    bl_options = {'REGISTER'}

    def execute(self, context):
        import sys
        import importlib

        addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        if addon_dir not in sys.path:
            sys.path.insert(0, addon_dir)

        try:
            if "tests.run_all_tests" in sys.modules:
                importlib.reload(sys.modules["tests.run_all_tests"])
            from tests import run_all_tests

            print("\n" + "="*70)
            print("Running Meridian Addon Tests...")
            print("="*70 + "\n")

            result = run_all_tests.run_all_tests()

            if result.wasSuccessful():
                self.report({'INFO'}, f"All {result.testsRun} tests passed!")
            else:
                failed = len(result.failures) + len(result.errors)
                self.report({'WARNING'}, f"{failed} test(s) failed. Check console for details.")

            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Test execution failed: {str(e)}")
            print(f"Error running tests: {e}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}


class MX_OT_QuickExport(bpy.types.Operator):
    bl_idname = "mx.quick_export"
    bl_label = "Quick Export"
    bl_description = "Quick export with current settings (Deprecated - use Compile instead)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mx.compile()


class MX_OT_RefreshLightmaps(bpy.types.Operator):
    bl_idname = "mx.refresh_lightmaps"
    bl_label = "Refresh Lightmaps"
    bl_description = "Rebuild lightmaps using The_Lightmapper addon"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.MX_SceneProperties

        if not props.mx_use_lightmapper:
            self.report({'WARNING'}, "Lightmapper integration is not enabled")
            return {'CANCELLED'}

        # TODO: Implement lightmap refresh
        self.report({'INFO'}, "TODO: Implement lightmap refresh and export")
        return {'FINISHED'}


class MX_OpenEditor(bpy.types.Operator):
    bl_idname = "mx.open_editor"
    bl_label = "Open Editor"
    bl_description = "Open external editor (deprecated - use Play with CTRL)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        return bpy.ops.mx.play('INVOKE_DEFAULT')
