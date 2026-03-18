import bpy, os
from bpy.props import *

class MX_SceneProperties(bpy.types.PropertyGroup):

    # ===== GODOT PROJECT SETTINGS =====
    mx_godot_project_path : StringProperty(
        name="Godot Project Path",
        description="Path to the Godot project root directory",
        default="",
        subtype='DIR_PATH'
    )

    mx_project_name : StringProperty(
        name="Project Name",
        description="Name of the Godot project (shown in title bar)",
        default=""
    )

    mx_project_version : StringProperty(
        name="Version",
        description="Project version string",
        default="1.0"
    )

    mx_app_icon : StringProperty(
        name="App Icon",
        description="Application icon for the Godot project (.png, .svg)",
        default="",
        subtype='FILE_PATH'
    )

    mx_splash_image : StringProperty(
        name="Boot Splash",
        description="Boot splash screen image for the Godot project (.png)",
        default="",
        subtype='FILE_PATH'
    )

    mx_export_scene_name : StringProperty(
        name="Export Scene Name",
        description="Name for the exported scene (auto-detected from Blender scene if empty)",
        default=""
    )

    mx_auto_export : BoolProperty(
        name="Auto Export on Save",
        description="Automatically export to Godot when saving the Blender file",
        default=False
    )

    # ===== PLATFORM & RENDERER =====
    mx_platform : EnumProperty(
        items=[
            ('DESKTOP', 'Desktop', 'Standard desktop application export'),
            #('WEB',     'Web',     'HTML5 / browser export'),
            ('XR',      'XR',      'VR / AR / WebXR export'),
        ],
        name="Platform",
        description="Target platform for the Godot export",
        default='DESKTOP'
    )

    mx_renderer : EnumProperty(
        items=[
            ('FORWARD_PLUS',  'Forward+',     'Full-featured renderer (Desktop, XR)'),
            ('MOBILE',        'Mobile',        'Optimised for mobile / lower-end hardware (Desktop, XR)'),
            ('COMPATIBILITY', 'Compatibility', 'WebGL2-compatible renderer (Web, XR standalone)'),
        ],
        name="Renderer",
        description="Godot rendering backend",
        default='FORWARD_PLUS'
    )

    mx_platform_initialized : StringProperty(
        name="Initialized Platform",
        description="Platform that the project was last initialized for — used to detect when re-init is needed",
        default=''
    )

    # ===== PUBLISHING =====
    mx_publish_target : EnumProperty(
        items=[
            ('WINDOWS', 'Windows (.exe)',  'Export as a Windows executable'),
            ('WEB',     'Web (HTML5)',      'Export as HTML5 for browsers'),
            ('ANDROID', 'Android (.apk)',  'Export as an Android APK'),
        ],
        name="Target",
        description="Publish target platform",
        default='WINDOWS'
    )

    mx_publish_output_path : StringProperty(
        name="Output Path",
        description="Directory where the published build will be written",
        default="",
        subtype='DIR_PATH'
    )

    # ===== EXPORT FORMAT SETTINGS =====
    mx_export_format : EnumProperty(
        items=[
            ('GLB', 'glTF Binary (.glb)', 'Export as single binary .glb file'),
            ('GLTF', 'glTF Separate (.gltf)', 'Export as .gltf with separate .bin and textures')
        ],
        name="Export Format",
        description="Choose the export format for Godot",
        default='GLB'
    )

    mx_export_copyright : StringProperty(
        name="Copyright",
        description="Legal rights and conditions for the model",
        default=""
    )

    mx_export_image_format : EnumProperty(
        items=[
            ('AUTO', 'Automatic', 'Determine format from texture'),
            ('JPEG', 'JPEG', 'Export textures as JPEG'),
            ('PNG', 'PNG', 'Export textures as PNG')
        ],
        name="Image Format",
        description="Output format for texture images",
        default='AUTO'
    )

    # ===== RENDERING SETTINGS (for Godot scene configuration) =====
    mx_msaa : EnumProperty(
        items=[
            ('0', 'Disabled', 'No MSAA'),
            ('1', '2x', '2x MSAA'),
            ('2', '4x', '4x MSAA'),
            ('3', '8x', '8x MSAA')
        ],
        name="MSAA",
        description="Multi-sample anti-aliasing quality for Godot",
        default='2'
    )

    mx_screen_space_aa : EnumProperty(
        items=[
            ('0', 'Disabled', 'No screen-space AA'),
            ('1', 'FXAA', 'Fast approximate anti-aliasing'),
            ('2', 'SMAA', 'Subpixel morphological anti-aliasing')
        ],
        name="Screen-Space AA",
        description="Screen-space anti-aliasing method",
        default='2'
    )

    mx_taa : BoolProperty(
        name="TAA (Temporal Anti-Aliasing)",
        description="Enable temporal anti-aliasing in Godot",
        default=True
    )

    mx_use_debanding : BoolProperty(
        name="Use Debanding",
        description="Enable debanding to reduce color banding artifacts",
        default=True
    )

    mx_scaling_3d_mode : EnumProperty(
        items=[
            ('0', 'Bilinear', 'Bilinear scaling'),
            ('1', 'FSR 1.0', 'FidelityFX Super Resolution 1.0'),
            ('2', 'FSR 2.2', 'FidelityFX Super Resolution 2.2')
        ],
        name="3D Scaling Mode",
        description="3D viewport scaling/upscaling method",
        default='1'
    )

    mx_scaling_3d_scale : FloatProperty(
        name="3D Scale",
        description="Resolution scale for 3D rendering (lower = better performance)",
        default=1.0,
        min=0.25,
        max=2.0
    )

    mx_fsr_sharpness : FloatProperty(
        name="FSR Sharpness",
        description="Sharpness for FSR upscaling (only applies to FSR modes)",
        default=0.2,
        min=0.0,
        max=2.0
    )

    # ===== TONEMAP SETTINGS =====
    mx_tonemap_mode : EnumProperty(
        items=[
            ('0', 'Linear', 'Linear tonemapping'),
            ('1', 'Reinhard', 'Reinhard tonemapping'),
            ('2', 'Filmic', 'Filmic tonemapping'),
            ('3', 'ACES', 'ACES tonemapping')
        ],
        name="Tonemap Mode",
        description="Tonemapping operator for HDR rendering",
        default='1'
    )

    mx_tonemap_exposure : FloatProperty(
        name="Tonemap Exposure",
        description="Exposure adjustment for tonemapping",
        default=1.59,
        min=0.01,
        max=8.0
    )

    mx_tonemap_white : FloatProperty(
        name="Tonemap White",
        description="White point for tonemapping",
        default=16.0,
        min=0.0,
        max=16.0
    )

    # ===== GLOW/BLOOM SETTINGS =====
    mx_glow_enabled : BoolProperty(
        name="Enable Glow",
        description="Enable glow/bloom effect in Godot",
        default=True
    )

    mx_glow_intensity : FloatProperty(
        name="Glow Intensity",
        description="Overall glow intensity",
        default=0.8,
        min=0.0,
        max=8.0
    )

    mx_glow_strength : FloatProperty(
        name="Glow Strength",
        description="Glow strength multiplier",
        default=0.66,
        min=0.0,
        max=2.0
    )

    mx_glow_bloom : FloatProperty(
        name="Glow Bloom",
        description="Amount of bloom effect",
        default=0.67,
        min=0.0,
        max=1.0
    )

    mx_glow_blend_mode : EnumProperty(
        items=[
            ('0', 'Additive', 'Additive blending'),
            ('1', 'Screen', 'Screen blending'),
            ('2', 'Softlight', 'Softlight blending'),
            ('3', 'Replace', 'Replace blending'),
            ('4', 'Mix', 'Mix blending')
        ],
        name="Glow Blend Mode",
        description="Blending mode for glow effect",
        default='1'
    )

    mx_glow_hdr_threshold : FloatProperty(
        name="HDR Threshold",
        description="Brightness threshold for glow effect",
        default=1.0,
        min=0.0,
        max=4.0
    )

    mx_glow_hdr_scale : FloatProperty(
        name="HDR Scale",
        description="Scale for HDR glow",
        default=2.0,
        min=0.0,
        max=4.0
    )

    mx_glow_normalized : BoolProperty(
        name="Normalized Glow",
        description="Normalize glow to prevent over-brightening",
        default=True
    )

    # Glow levels (7 mipmap levels)
    mx_glow_level_1 : FloatProperty(name="Level 1", default=1.0, min=0.0, max=1.0)
    mx_glow_level_2 : FloatProperty(name="Level 2", default=1.0, min=0.0, max=1.0)
    mx_glow_level_3 : FloatProperty(name="Level 3", default=1.0, min=0.0, max=1.0)
    mx_glow_level_4 : FloatProperty(name="Level 4", default=1.0, min=0.0, max=1.0)
    mx_glow_level_5 : FloatProperty(name="Level 5", default=1.0, min=0.0, max=1.0)
    mx_glow_level_6 : FloatProperty(name="Level 6", default=1.0, min=0.0, max=1.0)
    mx_glow_level_7 : FloatProperty(name="Level 7", default=1.0, min=0.0, max=1.0)

    # ===== SSR (Screen Space Reflections) =====
    mx_ssr_enabled : BoolProperty(
        name="Enable SSR",
        description="Enable screen-space reflections in Godot",
        default=False
    )

    mx_ssr_max_steps : IntProperty(
        name="Max Steps",
        description="Maximum ray steps for SSR",
        default=64,
        min=1,
        max=512
    )

    mx_ssr_fade_in : FloatProperty(
        name="Fade In",
        description="Fade in distance for reflections",
        default=0.15,
        min=0.0,
        max=2.0
    )

    mx_ssr_fade_out : FloatProperty(
        name="Fade Out",
        description="Fade out distance for reflections",
        default=2.0,
        min=0.0,
        max=10.0
    )

    mx_ssr_depth_tolerance : FloatProperty(
        name="Depth Tolerance",
        description="Depth tolerance for SSR",
        default=0.2,
        min=0.01,
        max=1.0
    )

    # ===== SSAO (Screen Space Ambient Occlusion) =====
    mx_ssao_enabled : BoolProperty(
        name="Enable SSAO",
        description="Enable screen-space ambient occlusion in Godot",
        default=False
    )

    mx_ssao_radius : FloatProperty(
        name="Radius",
        description="SSAO sampling radius",
        default=1.0,
        min=0.01,
        max=16.0
    )

    mx_ssao_intensity : FloatProperty(
        name="Intensity",
        description="SSAO effect intensity",
        default=2.0,
        min=0.0,
        max=16.0
    )

    mx_ssao_power : FloatProperty(
        name="Power",
        description="SSAO power/exponent",
        default=1.5,
        min=0.5,
        max=16.0
    )

    mx_ssao_detail : FloatProperty(
        name="Detail",
        description="SSAO detail level",
        default=0.5,
        min=0.0,
        max=5.0
    )

    mx_ssao_horizon : FloatProperty(
        name="Horizon",
        description="SSAO horizon angle",
        default=0.06,
        min=0.0,
        max=1.0
    )

    mx_ssao_sharpness : FloatProperty(
        name="Sharpness",
        description="SSAO sharpness",
        default=0.98,
        min=0.0,
        max=1.0
    )

    mx_ssao_light_affect : FloatProperty(
        name="Light Affect",
        description="How much SSAO affects direct lighting",
        default=0.0,
        min=0.0,
        max=1.0
    )

    mx_ssao_ao_channel_affect : FloatProperty(
        name="AO Channel Affect",
        description="How much material AO channel affects SSAO",
        default=0.0,
        min=0.0,
        max=1.0
    )

    # ===== SSIL (Screen Space Indirect Lighting) =====
    mx_ssil_enabled : BoolProperty(
        name="Enable SSIL",
        description="Enable screen-space indirect lighting in Godot",
        default=False
    )

    mx_ssil_radius : FloatProperty(
        name="Radius",
        description="SSIL sampling radius",
        default=5.0,
        min=0.01,
        max=16.0
    )

    mx_ssil_intensity : FloatProperty(
        name="Intensity",
        description="SSIL effect intensity",
        default=1.0,
        min=0.0,
        max=16.0
    )

    mx_ssil_sharpness : FloatProperty(
        name="Sharpness",
        description="SSIL sharpness",
        default=0.98,
        min=0.0,
        max=1.0
    )

    mx_ssil_normal_rejection : FloatProperty(
        name="Normal Rejection",
        description="SSIL normal rejection threshold",
        default=1.0,
        min=0.0,
        max=1.0
    )

    # ===== SDFGI (Signed Distance Field Global Illumination) =====
    mx_sdfgi_enabled : BoolProperty(
        name="Enable SDFGI",
        description="Enable signed distance field global illumination in Godot",
        default=False
    )

    mx_sdfgi_use_occlusion : BoolProperty(
        name="Use Occlusion",
        description="Enable SDFGI occlusion",
        default=True
    )

    mx_sdfgi_read_sky_light : BoolProperty(
        name="Read Sky Light",
        description="SDFGI reads sky light",
        default=True
    )

    mx_sdfgi_bounce_feedback : FloatProperty(
        name="Bounce Feedback",
        description="SDFGI bounce feedback amount",
        default=0.5,
        min=0.0,
        max=1.0
    )

    mx_sdfgi_cascades : IntProperty(
        name="Cascades",
        description="Number of SDFGI cascades",
        default=4,
        min=1,
        max=8
    )

    mx_sdfgi_min_cell_size : FloatProperty(
        name="Min Cell Size",
        description="Minimum cell size for SDFGI",
        default=0.2,
        min=0.01,
        max=2.0
    )

    mx_sdfgi_cascade0_distance : FloatProperty(
        name="Cascade 0 Distance",
        description="Distance for first SDFGI cascade",
        default=12.8,
        min=0.1,
        max=100.0
    )

    mx_sdfgi_max_distance : FloatProperty(
        name="Max Distance",
        description="Maximum distance for SDFGI",
        default=204.8,
        min=1.0,
        max=1000.0
    )

    mx_sdfgi_y_scale : EnumProperty(
        items=[
            ('0', '50%', 'Half resolution on Y axis'),
            ('1', '75%', '75% resolution on Y axis'),
            ('2', '100%', 'Full resolution')
        ],
        name="Y Scale",
        description="SDFGI Y-axis resolution",
        default='1'
    )

    mx_sdfgi_energy : FloatProperty(
        name="Energy",
        description="SDFGI energy/intensity",
        default=1.0,
        min=0.0,
        max=8.0
    )

    mx_sdfgi_normal_bias : FloatProperty(
        name="Normal Bias",
        description="SDFGI normal bias",
        default=1.1,
        min=0.0,
        max=10.0
    )

    mx_sdfgi_probe_bias : FloatProperty(
        name="Probe Bias",
        description="SDFGI probe bias",
        default=1.1,
        min=0.0,
        max=10.0
    )

    # ===== FOG SETTINGS =====
    mx_fog_enabled : BoolProperty(
        name="Enable Fog",
        description="Enable fog effect in Godot",
        default=False
    )

    mx_fog_light_color : FloatVectorProperty(
        name="Light Color",
        description="Fog light color",
        subtype='COLOR',
        default=(0.5, 0.6, 0.7),
        min=0.0,
        max=1.0,
        size=3
    )

    mx_fog_light_energy : FloatProperty(
        name="Light Energy",
        description="Fog light energy/intensity",
        default=1.0,
        min=0.0,
        max=16.0
    )

    mx_fog_sun_scatter : FloatProperty(
        name="Sun Scatter",
        description="Amount of sun scattering in fog",
        default=0.0,
        min=0.0,
        max=1.0
    )

    mx_fog_density : FloatProperty(
        name="Density",
        description="Fog density",
        default=0.01,
        min=0.0,
        max=1.0
    )

    mx_fog_aerial_perspective : FloatProperty(
        name="Aerial Perspective",
        description="Aerial perspective amount",
        default=0.0,
        min=0.0,
        max=1.0
    )

    mx_fog_sky_affect : FloatProperty(
        name="Sky Affect",
        description="How much fog affects the sky",
        default=1.0,
        min=0.0,
        max=1.0
    )

    mx_fog_height : FloatProperty(
        name="Height",
        description="Fog height position",
        default=0.0,
        min=-1000.0,
        max=1000.0
    )

    mx_fog_height_density : FloatProperty(
        name="Height Density",
        description="Height-based fog density falloff",
        default=0.0,
        min=-1.0,
        max=1.0
    )

    # ===== VOLUMETRIC FOG SETTINGS =====
    mx_volumetric_fog_enabled : BoolProperty(
        name="Enable Volumetric Fog",
        description="Enable volumetric fog in Godot",
        default=False
    )

    mx_volumetric_fog_density : FloatProperty(
        name="Density",
        description="Volumetric fog density",
        default=0.05,
        min=0.0,
        max=1.0
    )

    mx_volumetric_fog_albedo : FloatVectorProperty(
        name="Albedo",
        description="Volumetric fog albedo/color",
        subtype='COLOR',
        default=(1.0, 1.0, 1.0),
        min=0.0,
        max=1.0,
        size=3
    )

    mx_volumetric_fog_emission : FloatVectorProperty(
        name="Emission",
        description="Volumetric fog emission color",
        subtype='COLOR',
        default=(0.0, 0.0, 0.0),
        min=0.0,
        max=1.0,
        size=3
    )

    mx_volumetric_fog_emission_energy : FloatProperty(
        name="Emission Energy",
        description="Volumetric fog emission energy",
        default=1.0,
        min=0.0,
        max=16.0
    )

    mx_volumetric_fog_gi_inject : FloatProperty(
        name="GI Inject",
        description="How much GI affects volumetric fog",
        default=1.0,
        min=0.0,
        max=16.0
    )

    mx_volumetric_fog_anisotropy : FloatProperty(
        name="Anisotropy",
        description="Volumetric fog anisotropy (-1 to 1)",
        default=0.2,
        min=-1.0,
        max=1.0
    )

    mx_volumetric_fog_length : FloatProperty(
        name="Length",
        description="Volumetric fog length/distance",
        default=64.0,
        min=0.0,
        max=1024.0
    )

    mx_volumetric_fog_detail_spread : FloatProperty(
        name="Detail Spread",
        description="Volumetric fog detail spread",
        default=2.0,
        min=0.5,
        max=6.0
    )

    mx_volumetric_fog_ambient_inject : FloatProperty(
        name="Ambient Inject",
        description="How much ambient light affects volumetric fog",
        default=0.0,
        min=0.0,
        max=16.0
    )

    mx_volumetric_fog_sky_affect : FloatProperty(
        name="Sky Affect",
        description="How much sky affects volumetric fog",
        default=1.0,
        min=0.0,
        max=1.0
    )

    mx_volumetric_fog_temporal_reprojection_enabled : BoolProperty(
        name="Temporal Reprojection",
        description="Enable temporal reprojection for volumetric fog",
        default=True
    )

    mx_volumetric_fog_temporal_reprojection_amount : FloatProperty(
        name="Temporal Reprojection Amount",
        description="Temporal reprojection amount",
        default=0.9,
        min=0.0,
        max=1.0
    )

    # ===== ADJUSTMENTS (Color Correction) =====
    mx_adjustments_enabled : BoolProperty(
        name="Enable Adjustments",
        description="Enable color adjustments in Godot",
        default=False
    )

    mx_adjustments_brightness : FloatProperty(
        name="Brightness",
        description="Scene brightness adjustment",
        default=1.0,
        min=0.0,
        max=8.0
    )

    mx_adjustments_contrast : FloatProperty(
        name="Contrast",
        description="Scene contrast adjustment",
        default=1.0,
        min=0.0,
        max=8.0
    )

    mx_adjustments_saturation : FloatProperty(
        name="Saturation",
        description="Scene saturation adjustment",
        default=1.0,
        min=0.0,
        max=8.0
    )

    mx_adjustments_color_correction : BoolProperty(
        name="Use Color Correction",
        description="Enable LUT-based color correction",
        default=False
    )

    # ===== LIGHTMAP SETTINGS =====
    mx_lightmap_bicubic_filtering : BoolProperty(
        name="Lightmap Bicubic Filtering",
        description="Use bicubic filtering for lightmaps in Godot",
        default=False
    )

    mx_lightmap_compress_mode : EnumProperty(
        name="Compress Mode",
        description="Texture compression mode for imported lightmap textures in Godot",
        items=[
            ('0', "Lossless",          "Lossless compression — best quality, larger file size"),
            ('1', "Lossy",             "Lossy compression — smaller file, some quality loss"),
            ('2', "VRAM Compressed",   "GPU-native compression — fastest at runtime, some quality loss"),
            ('3', "VRAM Uncompressed", "Uncompressed on GPU — highest quality, most VRAM"),
            ('4', "Basis Universal",   "Basis Universal — cross-platform VRAM compression"),
        ],
        default='0'
    )

    mx_lightmap_mipmaps : BoolProperty(
        name="Generate Mipmaps",
        description="Generate mipmaps for lightmap textures (usually not needed for lightmaps)",
        default=False
    )

    mx_lightmap_mode : EnumProperty(
        name="Mode",
        description="How lightmaps are applied in Godot",
        items=[
            ('INDIVIDUAL', 'Individual', 'Apply a separate lightmap texture per object using the StandardPlusAuto shader'),
        ],
        default='INDIVIDUAL'
    )

    # mx_lightmap_mode : EnumProperty(
    #     name="Mode",
    #     description="How lightmaps are applied in Godot",
    #     items=[
    #         ('ATLAS',      'Atlas',      'Pack all lightmaps into a Texture2DArray and use LightmapGIData (current default)'),
    #         ('INDIVIDUAL', 'Individual', 'Apply a separate lightmap texture per object using the StandardPlusAuto shader'),
    #     ],
    #     default='ATLAS'
    # )

    mx_use_lightmapper : BoolProperty(
        name="Use The_Lightmapper Addon",
        description="Integrate with The_Lightmapper addon for baked lighting",
        default=False
    )

    mx_lightmap_export_path : StringProperty(
        name="Lightmap Export Path",
        description="Path to lightmaps folder (default: 'Lightmaps' relative to .blend file)",
        default="Lightmaps",
        subtype='DIR_PATH'
    )

    # ===== LIVELINK SETTINGS =====
    mx_livelink_enabled : BoolProperty(
        name="Enable LiveLink",
        description="Enable live synchronization between Blender and Godot",
        default=False
    )

    mx_livelink_blender_port : IntProperty(
        name="Blender Port",
        description="Port for Blender to listen on",
        default=15703,
        min=1024,
        max=65535
    )

    mx_livelink_godot_port : IntProperty(
        name="Godot Port",
        description="Port to send updates to Godot",
        default=15702,
        min=1024,
        max=65535
    )

    mx_livelink_auto_update : BoolProperty(
        name="Auto Update",
        description="Automatically update Godot when changes are made in Blender",
        default=True
    )

    # ===== MATERIAL CONVERSION SETTINGS =====
    mx_convert_materials : BoolProperty(
        name="Convert Materials to Godot",
        description="Convert Blender materials to Godot StandardMaterial3D",
        default=True
    )

    mx_convert_emission : BoolProperty(
        name="Convert Emission",
        description="Convert emission from Blender materials",
        default=True
    )

    mx_convert_normal_maps : BoolProperty(
        name="Convert Normal Maps",
        description="Convert normal maps from Blender materials",
        default=True
    )

    mx_convert_roughness : BoolProperty(
        name="Convert Roughness",
        description="Convert roughness from Blender materials",
        default=True
    )

    mx_texture_max_size : EnumProperty(
        items=[
            ('512', '512', '512x512'),
            ('1024', '1024', '1024x1024'),
            ('2048', '2048', '2048x2048'),
            ('4096', '4096', '4096x4096'),
            ('8192', '8192', '8192x8192')
        ],
        name="Max Texture Size",
        description="Maximum texture size for export",
        default='2048'
    )

    # ===== ADVANCED EXPORT OPTIONS =====
    mx_export_cameras : BoolProperty(
        name="Export Cameras",
        description="Export camera objects to Godot scene",
        default=True
    )

    mx_export_lights : BoolProperty(
        name="Export Lights",
        description="Export light objects to Godot scene",
        default=True
    )

    mx_export_animations : BoolProperty(
        name="Export Animations",
        description="Export animations to Godot",
        default=True
    )

    mx_export_apply_modifiers : BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers to meshes during GLTF export",
        default=True
    )

    mx_export_custom_properties : BoolProperty(
        name="Export Custom Properties",
        description="Export custom properties as Godot metadata",
        default=True
    )

    mx_create_inherited_scene : BoolProperty(
        name="Create Inherited Scene",
        description="Create an inherited scene in Godot for easier iteration",
        default=True
    )

    # ===== ENVIRONMENT SETTINGS =====
    mx_export_environment : BoolProperty(
        name="Export Environment",
        description="Export world environment settings to Godot",
        default=True
    )

    mx_export_world_override : PointerProperty(
        name="World Override",
        description="Use this World for environment export instead of the active scene world. Leave empty to use the scene's current world",
        type=bpy.types.World
    )

    mx_export_reflection_probes : BoolProperty(
        name="Export Reflection Probes",
        description="Convert light probes to Godot ReflectionProbe nodes",
        default=True
    )

    # ===== NAXPOST COMPOSITOR EFFECT SETTINGS =====
    mx_naxpost_enabled : BoolProperty(
        name="Enable NaxPost Effects",
        description="Add a NaxPost CompositorEffect to the WorldEnvironment (Chromatic Aberration, Vignette, Sharpen, Color Grading)",
        default=False
    )

    # Per-effect toggles
    mx_naxpost_ca_enabled : BoolProperty(name="Chromatic Aberration", default=True)
    mx_naxpost_vignette_enabled : BoolProperty(name="Vignette", default=True)
    mx_naxpost_sharpen_enabled : BoolProperty(name="Sharpen", default=True)
    mx_naxpost_colorgrading_enabled : BoolProperty(name="Color Grading", default=True)

    # Chromatic Aberration
    mx_naxpost_ca_intensity : FloatProperty(
        name="Intensity", default=0.1, min=0.0, max=1.0)
    mx_naxpost_ca_max_samples : IntProperty(
        name="Max Samples", default=32, min=1, max=64)

    # Vignette
    mx_naxpost_vignette_intensity : FloatProperty(
        name="Intensity", default=0.5, min=0.0, max=2.0)
    mx_naxpost_vignette_smoothness : FloatProperty(
        name="Smoothness", default=0.8, min=0.1, max=2.0)
    mx_naxpost_vignette_roundness : FloatProperty(
        name="Roundness", default=1.0, min=0.0, max=1.0)
    mx_naxpost_vignette_color : FloatVectorProperty(
        name="Color", subtype='COLOR', size=3,
        default=(0.0, 0.0, 0.0), min=0.0, max=1.0)

    # Sharpen
    mx_naxpost_sharpen_size : FloatProperty(
        name="Size", default=2.5, min=0.0, max=5.0)
    mx_naxpost_sharpen_strength : FloatProperty(
        name="Strength", default=0.25, min=-5.0, max=5.0)

    # Color Grading — global
    mx_naxpost_whitebalance : FloatProperty(
        name="White Balance", default=6500.0, min=1000.0, max=12000.0)
    mx_naxpost_shadow_max : FloatProperty(
        name="Shadow Max", default=1.0)
    mx_naxpost_highlight_min : FloatProperty(
        name="Highlight Min", default=0.0)
    mx_naxpost_tint : FloatVectorProperty(
        name="Tint", subtype='COLOR', size=3,
        default=(1.0, 1.0, 1.0), min=0.0, max=1.0)
    mx_naxpost_saturation : FloatProperty(name="Saturation", default=1.0, min=0.0, max=4.0)
    mx_naxpost_contrast : FloatProperty(name="Contrast", default=1.0, min=0.0, max=4.0)
    mx_naxpost_gamma : FloatProperty(name="Gamma", default=1.0, min=0.0, max=4.0)
    mx_naxpost_gain : FloatProperty(name="Gain", default=1.0, min=0.0, max=4.0)
    mx_naxpost_offset : FloatProperty(name="Offset", default=1.0)

    # ===== ANAMORPHIC BLOOM SETTINGS =====
    mx_anamorphic_bloom_enabled : BoolProperty(
        name="Enable Anamorphic Bloom",
        description="Add an Anamorphic Bloom CompositorEffect to the WorldEnvironment",
        default=False
    )

    mx_anamorphic_bloom_intensity : FloatProperty(
        name="Intensity", default=0.3, min=0.0, max=5.0)
    mx_anamorphic_bloom_threshold : FloatProperty(
        name="Threshold", default=1.0, min=0.0, max=10.0)
    mx_anamorphic_bloom_soft_knee : FloatProperty(
        name="Soft Knee", default=0.5, min=0.0, max=1.0)
    mx_anamorphic_bloom_strength : FloatProperty(
        name="Strength", default=1.0, min=0.0, max=2.0)
    mx_anamorphic_bloom_mix : FloatProperty(
        name="Mix", default=1.0, min=0.0, max=1.0)
    mx_anamorphic_bloom_hdr_scale : FloatProperty(
        name="HDR Scale", default=2.0, min=0.0, max=8.0)
    mx_anamorphic_bloom_hdr_luminance_cap : FloatProperty(
        name="Luminance Cap", default=12.0, min=0.0, max=256.0)
    mx_anamorphic_bloom_tint_enabled : BoolProperty(
        name="Tint", default=False)
    mx_anamorphic_bloom_tint_color : FloatVectorProperty(
        name="Tint Color", subtype='COLOR', size=3,
        default=(1.0, 0.85, 0.7), min=0.0, max=1.0)
    mx_anamorphic_bloom_horizontal : BoolProperty(
        name="Horizontal Streak", default=True)
    mx_anamorphic_bloom_streak_stretch : FloatProperty(
        name="Streak Stretch", default=4.0, min=1.0, max=16.0)
    mx_anamorphic_bloom_cross_blur_enabled : BoolProperty(
        name="Cross Blur", default=False)
    mx_anamorphic_bloom_cross_blur_strength : FloatProperty(
        name="Cross Blur Strength", default=0.25, min=0.0, max=1.0)
    mx_anamorphic_bloom_blend_mode : EnumProperty(
        name="Blend Mode",
        items=[
            ('0', 'Additive',  'Classic additive bloom'),
            ('1', 'Screen',    'HDR-safe screen blend'),
            ('2', 'Softlight', 'Cinematic softlight'),
            ('3', 'Replace',   'Debug / replace'),
        ],
        default='0'
    )
    mx_anamorphic_bloom_mip_levels : IntProperty(
        name="Mip Levels", default=5, min=2, max=7)