import bpy
import bpy.utils.previews
import os

preview_collections = {}

def load_logo():
    pcoll = bpy.utils.previews.new()
    addon_dir = os.path.dirname(__file__)
    logo_path = os.path.join(addon_dir, "logo.png")
    
    if os.path.exists(logo_path):
        pcoll.load("meridian_logo", logo_path, 'IMAGE')
    
    preview_collections["main"] = pcoll

def unload_logo():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()