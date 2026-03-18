import bpy


class MX_OperatorBase:
    """Base class providing shared state (Godot path) and hide/restore helpers."""

    @property
    def godot_path(self):
        prefs = bpy.context.preferences.addons.get(__package__.split('.')[0])
        if prefs:
            return prefs.preferences.godot_path
        return ""

    def hide_non_exported_objects(self):
        """Temporarily hide objects with mx_export_object disabled and all decal empties.
        Returns list of hidden objects to restore."""
        hidden_objects = []
        for obj in bpy.data.objects:
            obj_props = obj.MX_ObjectProperties
            should_hide = (
                not obj_props.mx_export_object or
                (obj.type == 'EMPTY' and obj_props.mx_is_decal)
            )
            if should_hide and not obj.hide_render:
                obj.hide_render = True
                hidden_objects.append(obj)
        return hidden_objects

    def restore_hidden_objects(self, hidden_objects):
        """Restore objects that were temporarily hidden for export."""
        for obj in hidden_objects:
            obj.hide_render = False
