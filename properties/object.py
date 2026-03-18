import bpy
from bpy.props import *
import os


def _update_is_decal(self, context):
    """When mx_is_decal is toggled on, switch the Empty display to Cube."""
    obj = context.active_object
    if obj and obj.type == 'EMPTY' and self.mx_is_decal:
        obj.empty_display_type = 'CUBE'


def get_custom_scripts(self, context):
    """Get list of custom scripts from {blend_dir}/scripts/ folder"""
    items = [('NONE', "Select Script...", "Choose a custom script")]

    blend_file = bpy.data.filepath
    if blend_file:
        scripts_dir = os.path.join(os.path.dirname(blend_file), "scripts")
        if os.path.isdir(scripts_dir):
            for file in sorted(os.listdir(scripts_dir)):
                if file.endswith('.gd'):
                    script_name = os.path.splitext(file)[0]
                    items.append((file, script_name, f"Custom script: {script_name}"))

    return items


def get_addon_bundled_scripts(self, context):
    """Get list of bundled scripts from addon's bundled/scripts folder"""
    items = [('NONE', "Select Script...", "Choose a bundled script")]

    # Get addon directory
    addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    bundled_scripts_dir = os.path.join(addon_dir, "bundled", "scripts")

    if os.path.exists(bundled_scripts_dir):
        for file in os.listdir(bundled_scripts_dir):
            if file.endswith('.gd'):
                script_name = os.path.splitext(file)[0]
                items.append((file, script_name, f"Bundled script: {script_name}"))

    return items


def update_script_name_from_custom(self, context):
    """Auto-update entry name when custom script selection changes"""
    if self.custom_script and self.custom_script != 'NONE':
        self.name = os.path.splitext(self.custom_script)[0]


def update_script_name_from_bundled(self, context):
    """Auto-update entry name when bundled script selection changes"""
    if self.bundled_script and self.bundled_script != 'NONE':
        self.name = os.path.splitext(self.bundled_script)[0]


class MX_ScriptItem(bpy.types.PropertyGroup):
    """Individual script entry in the scripts list"""

    name: StringProperty(
        name="Script Name",
        description="Name of the script",
        default="NewScript"
    )

    enabled: BoolProperty(
        name="Enabled",
        description="Enable/disable this script",
        default=True
    )

    script_type: EnumProperty(
        name="Type",
        description="Type of script",
        items=[
            ('GDSCRIPT', "GDScript", "Custom GDScript file"),
            ('BUNDLED', "Bundled", "Bundled script from addon"),
        ],
        default='GDSCRIPT'
    )

    custom_script: EnumProperty(
        name="Custom Script",
        description="Select a custom script from the project scripts folder",
        items=get_custom_scripts,
        update=update_script_name_from_custom
    )

    script_path: StringProperty(
        name="Script Path",
        description="Path to the script file (filename only, e.g. printer.gd)",
        default=""
    )

    bundled_script: EnumProperty(
        name="Bundled Script",
        description="Select a bundled script",
        items=get_addon_bundled_scripts,
        update=update_script_name_from_bundled
    )

    parameters: StringProperty(
        name="Parameters",
        description="Script parameters (comma-separated key=value pairs)",
        default=""
    )


class MX_ObjectProperties(bpy.types.PropertyGroup):

    # ===== EXPORT CONTROL =====
    mx_export_object : BoolProperty(
        name="Export to Godot",
        description="Include this object in Godot export",
        default=True
    )

    mx_object_type_override : EnumProperty(
        items=[
            ('AUTO', 'Auto Detect', 'Automatically determine Godot node type'),
            ('STATICBODY', 'StaticBody3D', 'Export as StaticBody3D with collision'),
            ('RIGIDBODY', 'RigidBody3D', 'Export as RigidBody3D'),
            ('AREA', 'Area3D', 'Export as Area3D'),
            ('MESHINSTANCE', 'MeshInstance3D', 'Export as MeshInstance3D (no physics)')
        ],
        name="Godot Node Type",
        description="Override the Godot node type for this object",
        default='AUTO'
    )

    mx_object_subtype : EnumProperty(
        items=[
            ('NONE', 'None', 'No special subtype'),
            ('DECAL', 'Decal', 'Exported as a Decal node in Godot'),
        ],
        name="Object Subtype",
        description="Special Meridian object subtype",
        default='NONE'
    )

    # ===== VISIBILITY LAYERS =====
    mx_render_layers : BoolVectorProperty(
        name="Render Layers",
        description="Godot VisualInstance3D render layers — which layers this object is visible on",
        size=20,
        default=(True,) + (False,) * 19,
        subtype='LAYER_MEMBER'
    )

    mx_reflection_cull_mask : BoolVectorProperty(
        name="Cull Mask",
        description="Godot ReflectionProbe cull mask — which render layers this probe captures",
        size=20,
        default=(True,) * 20,
        subtype='LAYER_MEMBER'
    )

    mx_reflection_reflection_mask : BoolVectorProperty(
        name="Reflection Mask",
        description="Godot ReflectionProbe reflection mask — which render layers show reflections from this probe",
        size=20,
        default=(True,) * 20,
        subtype='LAYER_MEMBER'
    )

    mx_reflection_update_mode : EnumProperty(
        items=[
            ('ONCE', 'Once (Fast)', 'Capture once on scene load'),
            ('ALWAYS', 'Always', 'Capture every frame (slow)'),
        ],
        name="Update Mode",
        description="When the reflection probe recaptures the scene",
        default='ONCE'
    )

    mx_reflection_intensity : FloatProperty(
        name="Intensity",
        description="Intensity of the reflection probe contribution",
        default=1.0,
        min=0.0,
        max=1.0,
        precision=3
    )

    mx_reflection_max_distance : FloatProperty(
        name="Max Distance",
        description="Maximum distance at which the reflection probe is visible (0 = infinite)",
        default=0.0,
        min=0.0,
        max=16384.0,
        subtype='DISTANCE',
        unit='LENGTH'
    )

    mx_reflection_ambient_mode : EnumProperty(
        items=[
            ('DISABLED', 'Disabled', 'No ambient light from this probe'),
            ('ENVIRONMENT', 'Environment', 'Use scene environment as ambient'),
            ('CONSTANT_COLOR', 'Constant Color', 'Use a constant color as ambient'),
        ],
        name="Ambient Mode",
        description="Ambient light contribution mode for this reflection probe",
        default='DISABLED'
    )

    mx_reflection_box_projection : BoolProperty(
        name="Box Projection",
        description="Enable box projection for this reflection probe (corrects reflections for non-infinitely-distant environments)",
        default=True
    )

    mx_reflection_interior : BoolProperty(
        name="Interior",
        description="When enabled, the probe only captures objects within its volume (for indoor spaces)",
        default=False
    )

    mx_reflection_enable_shadows : BoolProperty(
        name="Enable Shadows",
        description="Enable shadow rendering when capturing the reflection (more accurate but slower)",
        default=False
    )

    mx_reflection_blend_distance : FloatProperty(
        name="Blend Distance",
        description="Distance over which the probe blends into the scene (0 = hard cut, 8 = full blend). Matches Godot's blend_distance range",
        default=0.0,
        min=0.0,
        max=8.0,
        step=0.1,
        precision=3,
        subtype='DISTANCE',
        unit='LENGTH'
    )

    # ===== CAMERA ATTRIBUTES =====
    mx_camera_attributes_type : EnumProperty(
        items=[
            ('DISABLED', 'Disabled', 'No camera attributes resource'),
            ('PRACTICAL', 'Practical', 'CameraAttributesPractical — DOF blur and sensitivity-based auto exposure'),
            ('PHYSICAL', 'Physical', 'CameraAttributesPhysical — physical frustum and EV100-based auto exposure'),
        ],
        name="Attributes",
        description="Godot CameraAttributes resource to attach to this camera",
        default='DISABLED'
    )

    # Shared: Exposure + Auto Exposure (both types)
    mx_cam_exposure_multiplier : FloatProperty(
        name="Multiplier",
        description="Manual exposure multiplier",
        default=1.0, min=0.0, max=256.0, precision=3
    )

    mx_cam_auto_exp_enabled : BoolProperty(
        name="Auto Exposure",
        description="Enable automatic exposure adjustment",
        default=True
    )

    mx_cam_auto_exp_scale : FloatProperty(
        name="Scale",
        description="Auto exposure scale",
        default=0.4, min=0.0, max=8.0, precision=3
    )

    mx_cam_auto_exp_speed : FloatProperty(
        name="Speed",
        description="Auto exposure adjustment speed",
        default=0.5, min=0.0, max=64.0, precision=3
    )

    # Practical-specific
    mx_cam_dof_far_enabled : BoolProperty(
        name="Far Enabled",
        description="Enable far depth-of-field blur",
        default=False
    )

    mx_cam_dof_near_enabled : BoolProperty(
        name="Near Enabled",
        description="Enable near depth-of-field blur",
        default=False
    )

    mx_cam_dof_amount : FloatProperty(
        name="Amount",
        description="DOF blur strength",
        default=0.1, min=0.0, max=1.0, precision=3
    )

    mx_cam_auto_exp_min_sensitivity : FloatProperty(
        name="Min Sensitivity",
        description="Minimum ISO sensitivity for auto exposure",
        default=0.0, min=0.0, max=800.0, precision=1
    )

    mx_cam_auto_exp_max_sensitivity : FloatProperty(
        name="Max Sensitivity",
        description="Maximum ISO sensitivity for auto exposure",
        default=800.0, min=0.0, max=800.0, precision=1
    )

    # Physical-specific
    mx_cam_frustum_focus_distance : FloatProperty(
        name="Focus Distance",
        description="Distance to the focus plane",
        default=10.0, min=0.0,
        subtype='DISTANCE', unit='LENGTH'
    )

    mx_cam_frustum_focal_length : FloatProperty(
        name="Focal Length",
        description="Camera focal length in millimetres",
        default=35.0, min=1.0, max=800.0, precision=1
    )

    mx_cam_frustum_near : FloatProperty(
        name="Near",
        description="Near clip plane distance",
        default=0.05, min=0.001,
        subtype='DISTANCE', unit='LENGTH'
    )

    mx_cam_frustum_far : FloatProperty(
        name="Far",
        description="Far clip plane distance",
        default=4000.0, min=0.1,
        subtype='DISTANCE', unit='LENGTH'
    )

    mx_cam_phys_auto_exp_min : FloatProperty(
        name="Min Exposure Value",
        description="Minimum exposure in EV100",
        default=-8.0, min=-16.0, max=16.0, precision=1
    )

    mx_cam_phys_auto_exp_max : FloatProperty(
        name="Max Exposure Value",
        description="Maximum exposure in EV100",
        default=10.0, min=-16.0, max=16.0, precision=1
    )

    # ===== DECAL SETTINGS =====
    mx_is_decal : BoolProperty(
        name="Is Decal",
        description="Export this Empty as a Godot Decal node",
        default=False,
        update=_update_is_decal
    )

    mx_decal_size : FloatVectorProperty(
        name="Size",
        description="Decal volume size (Godot x=width, y=projection depth, z=height)",
        size=3,
        default=(2.0, 2.0, 2.0),
        min=0.001,
        subtype='XYZ',
        unit='LENGTH'
    )

    # Textures (Blender image datablocks)
    mx_decal_albedo_tex : PointerProperty(name="Albedo",   type=bpy.types.Image, description="Albedo/color decal texture")
    mx_decal_normal_tex : PointerProperty(name="Normal",   type=bpy.types.Image, description="Normal map decal texture")
    mx_decal_orm_tex    : PointerProperty(name="ORM",      type=bpy.types.Image, description="Occlusion/Roughness/Metallic decal texture")
    mx_decal_emission_tex : PointerProperty(name="Emission", type=bpy.types.Image, description="Emission decal texture")

    # Parameters
    mx_decal_emission_energy : FloatProperty(
        name="Emission Energy", default=1.0, min=0.0, max=16.0, precision=3)

    mx_decal_modulate : FloatVectorProperty(
        name="Modulate", size=4, default=(1.0, 1.0, 1.0, 1.0),
        min=0.0, max=1.0, subtype='COLOR')

    mx_decal_albedo_mix : FloatProperty(
        name="Albedo Mix", default=1.0, min=0.0, max=1.0, precision=3)

    mx_decal_normal_fade : FloatProperty(
        name="Normal Fade", default=0.0, min=0.0, max=1.0, precision=3)

    # Vertical Fade
    mx_decal_upper_fade : FloatProperty(
        name="Upper Fade", default=0.3, min=0.0, max=1.0, precision=3)

    mx_decal_lower_fade : FloatProperty(
        name="Lower Fade", default=0.3, min=0.0, max=1.0, precision=3)

    # Distance Fade
    mx_decal_distance_fade : BoolProperty(
        name="Distance Fade", default=True)

    mx_decal_distance_fade_begin : FloatProperty(
        name="Begin", default=40.0, min=0.0, subtype='DISTANCE', unit='LENGTH')

    mx_decal_distance_fade_length : FloatProperty(
        name="Length", default=10.0, min=0.0, subtype='DISTANCE', unit='LENGTH')

    # Cull Mask
    mx_decal_cull_mask : BoolVectorProperty(
        name="Cull Mask",
        description="Layers this decal projects onto",
        size=20,
        default=(True,) * 20,
        subtype='LAYER_MEMBER'
    )

    # ===== COLLISION SETTINGS =====
    mx_collision_enabled : BoolProperty(
        name="Generate Collision",
        description="Generate collision shape for this object in Godot",
        default=False
    )

    mx_collision_type : EnumProperty(
        items=[
            ('CONVEX', 'Convex', 'Convex collision shape'),
            ('TRIMESH', 'Trimesh', 'Triangle mesh collision (for static objects)'),
            ('BOX', 'Box', 'Box collision shape'),
            ('SPHERE', 'Sphere', 'Sphere collision shape'),
            ('CAPSULE', 'Capsule', 'Capsule collision shape')
        ],
        name="Collision Type",
        description="Type of collision shape to generate",
        default='CONVEX'
    )

    mx_collision_layer : IntProperty(
        name="Collision Layer",
        description="Physics collision layer (bitmask)",
        default=1,
        min=0,
        max=2147483647  # Max signed 32-bit int
    )

    mx_collision_mask : IntProperty(
        name="Collision Mask",
        description="Physics collision mask (bitmask)",
        default=1,
        min=0,
        max=2147483647  # Max signed 32-bit int
    )

    # ===== SCRIPT MANAGEMENT =====
    mx_scripts: CollectionProperty(
        type=MX_ScriptItem,
        name="Scripts",
        description="List of scripts attached to this object"
    )

    mx_scripts_index: IntProperty(
        name="Active Script Index",
        description="Index of the currently selected script in the list",
        default=0
    )

    # ===== GODOT METADATA =====
    mx_godot_groups : StringProperty(
        name="Godot Groups",
        description="Comma-separated list of Godot groups for this object",
        default=""
    )

    # ===== LOD SETTINGS =====
    mx_use_lod : BoolProperty(
        name="Use LOD",
        description="Enable Level of Detail for this object",
        default=False
    )

    mx_lod_distance_1 : FloatProperty(
        name="LOD 1 Distance",
        description="Distance for first LOD level",
        default=10.0,
        min=0.1
    )

    mx_lod_distance_2 : FloatProperty(
        name="LOD 2 Distance",
        description="Distance for second LOD level",
        default=20.0,
        min=0.1
    )
