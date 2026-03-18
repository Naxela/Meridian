import bpy
from bpy.props import *
from bpy.types import Menu, Panel
import os
from ..assetstore.bm import BM_STATUS

class MX_PT_Panel(bpy.types.Panel):
    bl_label = "Meridian - Godot Exporter"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        scene = context.scene
        props = scene.MX_SceneProperties

        # Logo display (if logo is loaded)
        try:
            from .. import logo_handler
            if "main" in logo_handler.preview_collections:
                pcoll = logo_handler.preview_collections["main"]
                if "meridian_logo" in pcoll:
                    # Disable property split for logo section only
                    col = layout.column(align=True)
                    col.use_property_split = False
                    col.use_property_decorate = False

                    row = col.row()
                    row.alignment = 'CENTER'
                    row.scale_y = 1.0
                    row.template_icon(icon_value=pcoll["meridian_logo"].icon_id, scale=10.0)

                    col.separator(factor=0.1)
        except:
            pass  # Logo not loaded, skip display

        # Godot executable warning
        prefs = bpy.context.preferences.addons.get(__package__.split('.')[0])
        godot_path = prefs.preferences.godot_path if prefs else ""
        if not godot_path:
            row = layout.row()
            row.alert = True
            row.label(text="Godot executable not set in addon preferences", icon='ERROR')

        # Workflow Buttons (prominent)
        box = layout.box()
        col = box.column(align=True)

        # Row 1: Initialize Project (full width, larger)
        row = col.row(align=True)
        row.scale_y = 1.3
        row.operator("mx.initialize_project", text="Initialize Project", icon='FILE_NEW')

        # Check if project exists (project.godot file)
        project_exists = bool(props.mx_godot_project_path) and os.path.exists(
            os.path.join(props.mx_godot_project_path, "project.godot")
        )

        # Disable compile/play if platform has changed since last initialize
        platform_ready = (
            project_exists and
            (props.mx_platform_initialized == props.mx_platform)
        )

        if project_exists and props.mx_platform_initialized and props.mx_platform != props.mx_platform_initialized:
            col.label(text=f"Platform changed — re-initialize required", icon='ERROR')

        # Row 2: Compile and Play (side by side, disabled if no project or platform changed)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.enabled = platform_ready
        row.operator("mx.compile", text="Compile", icon='EXPORT')
        row.operator("mx.play", text="Play", icon='PLAY')

        # Row 3: Clean button (full width, smaller, disabled if no project)
        row = col.row(align=True)
        row.scale_y = 1.0
        row.enabled = project_exists
        row.operator("mx.clean_project", text="Clean", icon='TRASH')

        # Platform & Renderer
        box = layout.box()
        col = box.column(align=True)
        col.prop(props, "mx_platform", text="Platform")
        renderer_row = col.row(align=True)
        renderer_row.prop(props, "mx_renderer", text="Renderer")
        if props.mx_platform == 'WEB' and props.mx_renderer != 'COMPATIBILITY':
            renderer_row.label(text="", icon='ERROR')
            col.label(text="Web requires Compatibility renderer", icon='INFO')
        elif props.mx_platform == 'XR' and props.mx_renderer == 'FORWARD_PLUS':
            renderer_row.label(text="", icon='INFO')
            col.label(text="XR: Mobile (desktop VR) or Compatibility (standalone) recommended", icon='INFO')
        elif props.mx_platform != 'WEB' and props.mx_platform != 'XR' and props.mx_renderer == 'COMPATIBILITY':
            renderer_row.label(text="", icon='ERROR')
            col.label(text="Compatibility renderer is for Web / XR standalone only", icon='INFO')

        # Asset Kiosk
        # box = layout.box()
        # col = box.column(align=True)
        # row = col.row(align=True)
        # row.scale_y = 1.2
        # if BM_STATUS["active"]:
        #     row.operator("bm.close_kiosk", text="Close Asset Kiosk", icon='DECORATE_LINKED')
        # else:
        #     row.operator("bm.open_kiosk", text="Asset Kiosk", icon='ASSET_MANAGER')
        # status_row = col.row()
        # status_row.alignment = 'CENTER'
        # if BM_STATUS["connected"]:
        #     status_row.label(text="Connected", icon='CHECKBOX_HLT')
        # elif BM_STATUS["active"]:
        #     status_row.label(text="Server running...", icon='PROP_ON')
        # else:
        #     status_row.label(text="Disconnected", icon='CHECKBOX_DEHLT')

        # Godot Project Path
        box = layout.box()
        col = box.column(align=True)
        row = col.row(align=True)
        row.prop(props, "mx_godot_project_path", text="Project Path")
        row.operator("mx.browse_godot_project", text="", icon='FILE_FOLDER')

        # Show create button if path doesn't exist
        if props.mx_godot_project_path and not os.path.exists(props.mx_godot_project_path):
            col.operator("mx.create_godot_project", icon='FILE_NEW')

        col.prop(props, "mx_project_name")
        col.prop(props, "mx_project_version")
        col.prop(props, "mx_app_icon")
        col.prop(props, "mx_splash_image")
        col.prop(props, "mx_export_scene_name")
        col.prop(props, "mx_auto_export")

        # Export Format
        col.separator()
        col.prop(props, "mx_export_format")


class MX_PT_ExportOptions(bpy.types.Panel):
    bl_label = "Export Options"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties

        col = layout.column(align=True)
        col.prop(props, "mx_export_cameras")
        col.prop(props, "mx_export_lights")
        col.prop(props, "mx_export_animations")
        col.prop(props, "mx_export_environment")
        if props.mx_export_environment:
            col.prop(props, "mx_export_world_override")
        col.prop(props, "mx_export_reflection_probes")
        col.prop(props, "mx_export_apply_modifiers")
        col.prop(props, "mx_export_custom_properties")

        col.separator()
        col.prop(props, "mx_create_inherited_scene")

        col.separator()
        col.prop(props, "mx_export_copyright")
        col.prop(props, "mx_export_image_format")


class MX_PT_MaterialConversion(bpy.types.Panel):
    bl_label = "Material Conversion"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties

        col = layout.column(align=True)
        col.prop(props, "mx_convert_materials")

        # Only show conversion options if enabled
        if props.mx_convert_materials:
            box = layout.box()
            col = box.column(align=True)
            col.prop(props, "mx_convert_emission")
            col.prop(props, "mx_convert_normal_maps")
            col.prop(props, "mx_convert_roughness")
            col.separator()
            col.prop(props, "mx_texture_max_size")


class MX_PT_Lightmapper(bpy.types.Panel):
    bl_label = "Lightmapper Integration"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_use_lightmapper", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties

        # Disable if lightmapper not enabled
        layout.enabled = props.mx_use_lightmapper

        col = layout.column(align=True)
        col.prop(props, "mx_lightmap_mode")
        col.separator(factor=0.5)
        row = col.row(align=True)
        row.prop(props, "mx_lightmap_export_path", text="Export Path")
        row.operator("mx.browse_lightmap_path", text="", icon='FILE_FOLDER')
        col.prop(props, "mx_lightmap_bicubic_filtering")
        col.prop(props, "mx_lightmap_compress_mode")
        col.prop(props, "mx_lightmap_mipmaps")

        # Integration info
        # box = layout.box()
        # col = box.column(align=True)
        # col.label(text="The_Lightmapper Integration:", icon='INFO')
        # col.label(text="• Bake lightmaps in Blender")
        # col.label(text="• Auto-export to Godot project")
        # col.label(text="• Set per-object resolution in Object Properties")

class MX_PT_GodotRendering(bpy.types.Panel):
    bl_label = "Godot Rendering Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties

        # Anti-aliasing
        box = layout.box()
        box.label(text="Anti-Aliasing", icon='ANTIALIASED')
        col = box.column(align=True)
        col.prop(props, "mx_msaa")
        col.prop(props, "mx_screen_space_aa")
        col.prop(props, "mx_taa")
        col.prop(props, "mx_use_debanding")

        # 3D Scaling
        box = layout.box()
        box.label(text="3D Scaling", icon='FULLSCREEN_ENTER')
        col = box.column(align=True)
        col.prop(props, "mx_scaling_3d_mode")
        col.prop(props, "mx_scaling_3d_scale")
        if props.mx_scaling_3d_mode in ['1', '2']:  # FSR modes
            col.prop(props, "mx_fsr_sharpness")


class MX_PT_GodotTonemapping(bpy.types.Panel):
    bl_label = "Tonemapping"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties

        col = layout.column(align=True)
        col.prop(props, "mx_tonemap_mode")
        col.prop(props, "mx_tonemap_exposure")
        col.prop(props, "mx_tonemap_white")


class MX_PT_GodotGlow(bpy.types.Panel):
    bl_label = "Glow / Bloom"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_glow_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_glow_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_glow_intensity")
        col.prop(props, "mx_glow_strength")
        col.prop(props, "mx_glow_bloom")
        col.prop(props, "mx_glow_blend_mode")
        col.prop(props, "mx_glow_hdr_threshold")
        col.prop(props, "mx_glow_hdr_scale")
        col.prop(props, "mx_glow_normalized")

        # Glow levels
        box = layout.box()
        box.label(text="Glow Levels (Mipmaps)", icon='OUTLINER_DATA_LIGHTPROBE')
        col = box.column(align=True)
        col.prop(props, "mx_glow_level_1")
        col.prop(props, "mx_glow_level_2")
        col.prop(props, "mx_glow_level_3")
        col.prop(props, "mx_glow_level_4")
        col.prop(props, "mx_glow_level_5")
        col.prop(props, "mx_glow_level_6")
        col.prop(props, "mx_glow_level_7")


class MX_PT_GodotSSR(bpy.types.Panel):
    bl_label = "SSR (Screen Space Reflections)"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_ssr_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_ssr_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_ssr_max_steps")
        col.prop(props, "mx_ssr_fade_in")
        col.prop(props, "mx_ssr_fade_out")
        col.prop(props, "mx_ssr_depth_tolerance")


class MX_PT_GodotSSAO(bpy.types.Panel):
    bl_label = "SSAO (Screen Space Ambient Occlusion)"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_ssao_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_ssao_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_ssao_radius")
        col.prop(props, "mx_ssao_intensity")
        col.prop(props, "mx_ssao_power")
        col.prop(props, "mx_ssao_detail")
        col.prop(props, "mx_ssao_horizon")
        col.prop(props, "mx_ssao_sharpness")
        col.prop(props, "mx_ssao_light_affect")
        col.prop(props, "mx_ssao_ao_channel_affect")


class MX_PT_GodotSSIL(bpy.types.Panel):
    bl_label = "SSIL (Screen Space Indirect Lighting)"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_ssil_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_ssil_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_ssil_radius")
        col.prop(props, "mx_ssil_intensity")
        col.prop(props, "mx_ssil_sharpness")
        col.prop(props, "mx_ssil_normal_rejection")


class MX_PT_GodotSDFGI(bpy.types.Panel):
    bl_label = "SDFGI (Global Illumination)"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_sdfgi_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_sdfgi_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_sdfgi_use_occlusion")
        col.prop(props, "mx_sdfgi_read_sky_light")
        col.prop(props, "mx_sdfgi_bounce_feedback")

        col.separator()
        col.prop(props, "mx_sdfgi_cascades")
        col.prop(props, "mx_sdfgi_min_cell_size")
        col.prop(props, "mx_sdfgi_cascade0_distance")
        col.prop(props, "mx_sdfgi_max_distance")
        col.prop(props, "mx_sdfgi_y_scale")

        col.separator()
        col.prop(props, "mx_sdfgi_energy")
        col.prop(props, "mx_sdfgi_normal_bias")
        col.prop(props, "mx_sdfgi_probe_bias")


class MX_PT_GodotFog(bpy.types.Panel):
    bl_label = "Fog"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_fog_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_fog_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_fog_light_color")
        col.prop(props, "mx_fog_light_energy")
        col.prop(props, "mx_fog_sun_scatter")
        col.prop(props, "mx_fog_density")
        col.prop(props, "mx_fog_aerial_perspective")
        col.prop(props, "mx_fog_sky_affect")

        col.separator()
        col.prop(props, "mx_fog_height")
        col.prop(props, "mx_fog_height_density")


class MX_PT_GodotVolumetricFog(bpy.types.Panel):
    bl_label = "Volumetric Fog"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_volumetric_fog_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_volumetric_fog_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_volumetric_fog_density")
        col.prop(props, "mx_volumetric_fog_albedo")
        col.prop(props, "mx_volumetric_fog_emission")
        col.prop(props, "mx_volumetric_fog_emission_energy")

        col.separator()
        col.prop(props, "mx_volumetric_fog_gi_inject")
        col.prop(props, "mx_volumetric_fog_anisotropy")
        col.prop(props, "mx_volumetric_fog_length")
        col.prop(props, "mx_volumetric_fog_detail_spread")
        col.prop(props, "mx_volumetric_fog_ambient_inject")
        col.prop(props, "mx_volumetric_fog_sky_affect")

        col.separator()
        col.prop(props, "mx_volumetric_fog_temporal_reprojection_enabled")
        if props.mx_volumetric_fog_temporal_reprojection_enabled:
            col.prop(props, "mx_volumetric_fog_temporal_reprojection_amount")


class MX_PT_GodotAdjustments(bpy.types.Panel):
    bl_label = "Adjustments"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_adjustments_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_adjustments_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_adjustments_brightness")
        col.prop(props, "mx_adjustments_contrast")
        col.prop(props, "mx_adjustments_saturation")
        col.separator()
        col.prop(props, "mx_adjustments_color_correction")


class MX_PT_NaxPost(bpy.types.Panel):
    bl_label = "Meridian Effects"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_GodotRendering"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_naxpost_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_naxpost_enabled

        # Chromatic Aberration
        box = layout.box()
        row = box.row()
        row.prop(props, "mx_naxpost_ca_enabled", text="Chromatic Aberration")
        col = box.column(align=True)
        col.enabled = props.mx_naxpost_ca_enabled
        col.prop(props, "mx_naxpost_ca_intensity")
        col.prop(props, "mx_naxpost_ca_max_samples")

        # Vignette
        box = layout.box()
        row = box.row()
        row.prop(props, "mx_naxpost_vignette_enabled", text="Vignette")
        col = box.column(align=True)
        col.enabled = props.mx_naxpost_vignette_enabled
        col.prop(props, "mx_naxpost_vignette_intensity")
        col.prop(props, "mx_naxpost_vignette_smoothness")
        col.prop(props, "mx_naxpost_vignette_roundness")
        col.prop(props, "mx_naxpost_vignette_color")

        # Sharpen
        box = layout.box()
        row = box.row()
        row.prop(props, "mx_naxpost_sharpen_enabled", text="Sharpen")
        col = box.column(align=True)
        col.enabled = props.mx_naxpost_sharpen_enabled
        col.prop(props, "mx_naxpost_sharpen_size")
        col.prop(props, "mx_naxpost_sharpen_strength")

        # Color Grading
        box = layout.box()
        row = box.row()
        row.prop(props, "mx_naxpost_colorgrading_enabled", text="Color Grading")
        col = box.column(align=True)
        col.enabled = props.mx_naxpost_colorgrading_enabled
        col.prop(props, "mx_naxpost_whitebalance")
        col.prop(props, "mx_naxpost_shadow_max")
        col.prop(props, "mx_naxpost_highlight_min")
        col.prop(props, "mx_naxpost_tint")
        col.separator()
        col.prop(props, "mx_naxpost_saturation")
        col.prop(props, "mx_naxpost_contrast")
        col.prop(props, "mx_naxpost_gamma")
        col.prop(props, "mx_naxpost_gain")
        col.prop(props, "mx_naxpost_offset")

        # Anamorphic Bloom
        box = layout.box()
        row = box.row()
        row.prop(props, "mx_anamorphic_bloom_enabled", text="Anamorphic Bloom")
        col = box.column(align=True)
        col.enabled = props.mx_anamorphic_bloom_enabled
        col.prop(props, "mx_anamorphic_bloom_intensity")
        col.prop(props, "mx_anamorphic_bloom_threshold")
        col.prop(props, "mx_anamorphic_bloom_soft_knee")
        col.prop(props, "mx_anamorphic_bloom_strength")
        col.prop(props, "mx_anamorphic_bloom_mix")
        col.separator()
        col.prop(props, "mx_anamorphic_bloom_hdr_scale")
        col.prop(props, "mx_anamorphic_bloom_hdr_luminance_cap")
        col.separator()
        col.prop(props, "mx_anamorphic_bloom_horizontal")
        col.prop(props, "mx_anamorphic_bloom_streak_stretch")
        col.prop(props, "mx_anamorphic_bloom_cross_blur_enabled")
        if props.mx_anamorphic_bloom_cross_blur_enabled:
            col.prop(props, "mx_anamorphic_bloom_cross_blur_strength")
        col.separator()
        col.prop(props, "mx_anamorphic_bloom_tint_enabled")
        if props.mx_anamorphic_bloom_tint_enabled:
            col.prop(props, "mx_anamorphic_bloom_tint_color")
        col.separator()
        col.prop(props, "mx_anamorphic_bloom_blend_mode")
        col.prop(props, "mx_anamorphic_bloom_mip_levels")


class MX_PT_Publishing(bpy.types.Panel):
    bl_label = "Publishing"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        props = context.scene.MX_SceneProperties

        col = layout.column(align=True)
        col.prop(props, "mx_publish_target")
        col.prop(props, "mx_publish_output_path")

        layout.separator()
        row = layout.row()
        row.scale_y = 1.4
        row.operator("mx.publish", text="Publish", icon='EXPORT')


class MX_PT_LiveLink(bpy.types.Panel):
    bl_label = "LiveLink"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_parent_id = "MX_PT_Panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        props = context.scene.MX_SceneProperties
        self.layout.prop(props, "mx_livelink_enabled", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        from ..operators import livelink as ll

        props = context.scene.MX_SceneProperties
        layout.enabled = props.mx_livelink_enabled

        col = layout.column(align=True)
        col.prop(props, "mx_livelink_godot_port")
        col.prop(props, "mx_livelink_auto_update")

        col.separator()

        connected = ll.is_connected()
        running = ll.is_running()

        if running:
            label = "Disconnect" if connected else "Reconnecting..."
            icon = 'UNLINKED' if connected else 'TIME'
        else:
            label = "Connect"
            icon = 'LINKED'

        col.operator("mx.test_livelink", text=label, icon=icon)

        # Status box
        box = layout.box()
        status_col = box.column(align=True)
        if connected:
            status_col.label(text="Connected to Godot", icon='CHECKMARK')
        elif running:
            status_col.label(text="Connecting...", icon='TIME')
        else:
            status_col.label(text="Disconnected", icon='X')
