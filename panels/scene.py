import bpy
import subprocess
import os

from ..utility import util
from ..operators.operators import proc_state

from bpy.types import (
    Panel,
    AddonPreferences,
    Operator,
    PropertyGroup,
)

def project_generated():

    return True

class NX_PT_Panel(bpy.types.Panel):
    bl_label = "NX Bridge"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        file_path = bpy.data.filepath

class NX_PT_Player(bpy.types.Panel):
    bl_label = "Player"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row(align=True)

        sceneProperties = scene.NX_SceneProperties
        global proc_state

        if project_generated():

            row.label(text="Meridian Engine build 1 / A-Frame 1.70")
            row = layout.row(align=True)

            if proc_state["process"] is None:
                # No process running -> show Start button
                row.operator("nx.play")
            else:
                # Process running -> show Stop button
                row.operator("nx.stop")

            row.operator("nx.clean")
        else:
            row.operator("nx.generate")
            row = layout.row(align=True)
            row.label(text="Project needs to be generated first")

        row = layout.row(align=True)
        box = layout.box().column()
        #box.label(text="ABCDEFG")
        
        box.prop(scene.NX_SceneProperties, "nx_godot_path")
        box.prop(scene.NX_SceneProperties, "nx_rendering")
        box.prop(scene.NX_SceneProperties, "nx_platform")
        box.prop(scene.NX_SceneProperties, "nest_fullscreen")
        box.prop(scene.NX_SceneProperties, "nest_vsync")

        #if not sceneProperties.nest_platform == "WebGL" and not sceneProperties.nest_platform == "WebGPU":
            #box.prop(scene.NX_SceneProperties, "nest_debug")

        #box.prop(scene.NX_SceneProperties, "nest_live_linking")
        
        #box.prop(scene.NX_SceneProperties, "nest_bloom")
        #box.prop(scene.NX_SceneProperties, "nest_default_camera")
        #box.prop(scene.NX_SceneProperties, "nest_cargo_crates")
        box.operator("nx.explore")
        #if sceneProperties.nest_gltf_mode == "Separate":
        #    box.prop(scene.NX_SceneProperties, "nest_preprocess_assets")

        #PREPROCESSING
        if sceneProperties.nest_gltf_mode == "Separate" and sceneProperties.nest_preprocess_assets:
            pass #TODO OPTIONS!

        box.operator("nx.open_store")

class NX_PT_Publisher(bpy.types.Panel):
    bl_label = "Renderer"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    #bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    @classmethod
    def poll(cls, context):
        file_path = bpy.data.filepath

        return bool(file_path)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row(align=True)

        # Create a box and add properties to it
        box = layout.box().column()
        box.prop(scene.NX_SceneProperties, "nest_postprocess_tonemapper")

        # TODO Shadow settings
        #box.prop(scene.NX_SceneProperties, "nx_enable_shadows")
        
        #SSAO Properties
        box.prop(scene.NX_SceneProperties, "nest_postprocess_ssao")

        #TODO
        #if scene.NX_SceneProperties.nest_postprocess_ssao:
        #    box.label(text="SSAO Settings here...")

        box.prop(scene.NX_SceneProperties, "nx_postprocess_bloom")

        box.prop(scene.NX_SceneProperties, "nx_postprocess_antialiasing")

        if scene.NX_SceneProperties.nx_postprocess_antialiasing:

            box.prop(scene.NX_SceneProperties, "nx_postprocess_antialiasing_mode")

        box.prop(scene.NX_SceneProperties, "nest_postprocess_dof")

        if scene.NX_SceneProperties.nest_postprocess_dof:
            box.label(text="Depth of Field Settings here...")

        box.prop(scene.NX_SceneProperties, "nest_postprocess_ca")

        if scene.NX_SceneProperties.nest_postprocess_ca:

            box.prop(scene.NX_SceneProperties, "nest_postprocess_ca_samples")
            box.prop(scene.NX_SceneProperties, "nest_postprocess_ca_intensity")


        box.prop(scene.NX_SceneProperties, "nest_postprocess_vignette")
        box.prop(scene.NX_SceneProperties, "nest_import_lightmaps")

        if scene.NX_SceneProperties.nest_import_lightmaps:
            box.prop(scene.NX_SceneProperties, "nest_import_lightmap_directory")

class NX_PT_Project(bpy.types.Panel):
    bl_label = "Project"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    @classmethod
    def poll(cls, context):
        file_path = bpy.data.filepath
        file_pathx = False

        # Check if the file has been saved
        return bool(file_pathx)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False
        row = layout.row(align=True)

        if project_generated():
            row.operator("nx.compile_start")
            row.operator("nx.clean")
        else:
            row.operator("nx.generate")
            row = layout.row(align=True)
            row.label(text="Project needs to be generated first")

        row = layout.row(align=True)
        box = layout.box().column()
        box.label(text="ABCDEFG")

        #row = layout.row(align=True)
        #row.prop(scene.NX_SceneProperties, "nest_postprocess_tonemapper")

class NX_PT_Settings(bpy.types.Panel):
    bl_label = "Settings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    @classmethod
    def poll(cls, context):
        file_path = bpy.data.filepath
        file_pathx = False

        # Check if the file has been saved
        return bool(file_pathx)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        # row = layout.row(align=True)
        # row.label(text="Environment:", icon="WORLD")
        row = layout.row(align=True)
        row.prop(scene.NX_SceneProperties, "nest_postprocess_tonemapper")
        row = layout.row(align=True)
        row.prop(scene.NX_SceneProperties, "nest_platform")
        row = layout.row(align=True)
        row.prop(scene.NX_SceneProperties, "nest_rendering")
        row = layout.row(align=True)
        row.prop(scene.NX_SceneProperties, "nest_shadows")
        row = layout.row(align=True)
        row.prop(scene.NX_SceneProperties, "nest_bloom")
        
        #row.operator("nx.compile")

class NX_PT_Shadows(bpy.types.Panel):
    bl_label = "Shadows"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    @classmethod
    def poll(cls, context):
        file_path = bpy.data.filepath
        file_pathx = False

        # Check if the file has been saved
        return bool(file_pathx)
    
    def draw_header(self, context):

        scene = context.scene
        sceneProperties = scene.NX_SceneProperties
        self.layout.prop(sceneProperties, "nx_enable_shadows", text="")

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()

class NX_PT_Postprocessing(bpy.types.Panel):
    bl_label = "Postprocessing"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = "NX_PT_Panel"

    @classmethod
    def poll(cls, context):
        file_path = bpy.data.filepath
        file_pathx = False

        # Check if the file has been saved
        return bool(file_pathx)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.use_property_split = True
        layout.use_property_decorate = False

        sceneProperties = scene.NX_SceneProperties