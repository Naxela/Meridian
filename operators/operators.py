import bpy, os, json, webbrowser, subprocess, shutil, re

from .. utility import util

from .. operations import compile, filemaker, live_link

import bpy
import os
import json
import subprocess
import threading
import math, mathutils

proc_state = {
    "process": None,
}
class NX_Play(bpy.types.Operator):
    bl_idname = "nx.play"
    bl_label = "Play"
    bl_description = "Start your project directly (no compile)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global proc_state

        if proc_state["process"] is not None:
            self.report({'WARNING'}, "A process is already running!")
            return {'CANCELLED'}

        # Setup paths
        file_path = bpy.data.filepath
        project_directory = os.path.join(os.path.dirname(file_path), "build")
        
        if not os.path.exists(project_directory):
            os.makedirs(project_directory)

        # Validate Electron installation
        electron_exe_path, electron_app_dir = self.get_electron_paths()
        if not self.validate_electron_installation(electron_exe_path, electron_app_dir):
            return {'CANCELLED'}

        # Export scene data
        try:
            self.export_complete_scene(project_directory)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export scene: {e}")
            return {'CANCELLED'}

        # Setup Electron app
        blend_filename = os.path.splitext(os.path.basename(file_path))[0] if file_path else "untitled"
        try:
            self.setup_electron_app(project_directory, electron_app_dir, blend_filename)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to setup Electron app: {e}")
            return {'CANCELLED'}

        # Launch Electron
        self.launch_electron(electron_exe_path, os.path.dirname(electron_exe_path))
        
        self.report({'INFO'}, f"Electron app started successfully!")
        return {"FINISHED"}

    # ============================================================================
    # PATH AND VALIDATION METHODS
    # ============================================================================
    
    def get_electron_paths(self):
        """Get Electron executable and app directory paths"""
        electron_exe_path = bpy.path.abspath(os.path.join(
            bpy.data.scenes["Scene"].NX_SceneProperties.nx_godot_path, 
            "electron.exe"
        ))
        electron_dir = os.path.dirname(electron_exe_path)
        electron_resources_dir = os.path.join(electron_dir, "resources")
        electron_app_dir = os.path.join(electron_resources_dir, "app")
        
        return electron_exe_path, electron_app_dir

    def validate_electron_installation(self, electron_exe_path, electron_app_dir):
        """Validate that Electron is properly installed"""
        if not os.path.exists(electron_exe_path):
            self.report({'ERROR'}, f"Electron binary not found at: {electron_exe_path}")
            return False

        electron_resources_dir = os.path.dirname(electron_app_dir)
        if not os.path.exists(electron_resources_dir):
            self.report({'ERROR'}, f"Electron resources directory not found at: {electron_resources_dir}")
            return False
            
        return True

    # ============================================================================
    # SCENE EXPORT METHODS
    # ============================================================================

    def export_complete_scene(self, project_directory):
        """Export the complete scene including GLB, cameras, and lights"""
        print("Exporting complete scene...")
        
        # Export GLB file
        self.export_glb_scene(project_directory)
        
        # Export scene data for A-Frame
        scene_data = self.create_aframe_scene_data()
        self.save_scene_data(project_directory, scene_data)

    def export_glb_scene(self, project_directory):
        """Export the scene as GLB file"""
        output_file = os.path.join(project_directory, "scene")
        
        bpy.ops.export_scene.gltf(
            filepath=output_file, 
            export_format='GLB', 
            use_visible=True,
            use_active_scene=True,
            export_apply=True,
            export_extras=True,
            export_cameras=False,  # We'll export these separately
            export_lights=False,   # We'll export these separately
            export_attributes=True,
            export_skins=True,
            export_animations=True
        )
        print(f"GLB exported to: {output_file}.glb")

    def create_aframe_scene_data(self):
        """Create A-Frame compatible scene data"""
        scene = bpy.context.scene
        
        scene_data = {
            "name": scene.name,
            "environment": self.get_environment_data(scene),
            "cameras": self.get_aframe_cameras_data(scene),
            "lights": self.get_aframe_lights_data(scene),
            "models": ["scene.glb"]
        }
        
        return scene_data

    def get_environment_data(self, scene):
        """Extract environment/world settings for A-Frame"""
        world = scene.world
        env_data = {
            "background": "color: #222222",  # Default gray
            "fog": None
        }
        
        if world and world.use_nodes:
            # Try to find background color from world shader nodes
            for node in world.node_tree.nodes:
                if node.type == 'BACKGROUND':
                    if hasattr(node.inputs[0], 'default_value'):
                        color = node.inputs[0].default_value
                        hex_color = "#{:02x}{:02x}{:02x}".format(
                            int(color[0] * 255), 
                            int(color[1] * 255), 
                            int(color[2] * 255)
                        )
                        env_data["background"] = f"color: {hex_color}"
                        break
        
        return env_data

    def get_aframe_cameras_data(self, scene):
        """Extract all cameras from the scene for A-Frame"""
        cameras_data = []
        
        for obj in scene.objects:
            if obj.type == 'CAMERA':
                camera_data = self.extract_aframe_camera_data(obj)
                cameras_data.append(camera_data)
                print(f"Exported camera: {obj.name}")
        
        # If no cameras found, create a default one
        if not cameras_data:
            print("No cameras found, creating default camera")
            cameras_data.append(self.create_default_aframe_camera())
        
        return cameras_data

    def extract_aframe_camera_data(self, camera_obj):
        """Extract data from a Blender camera object for A-Frame"""
        camera = camera_obj.data
        scene = bpy.context.scene
        
        # Get world position and rotation
        location = camera_obj.matrix_world.to_translation()
        rotation = camera_obj.matrix_world.to_euler()
        
        # Convert to A-Frame coordinate system (right-handed, Y-up)
        # Blender uses Z-up, so we need to convert
        position = f"{location.x:.3f} {location.z:.3f} {-location.y:.3f}"
        
        # Convert rotation from radians to degrees and adjust for A-Frame
        rot_x = math.degrees(rotation.x) - 90  # Adjust for coordinate system
        rot_y = math.degrees(rotation.z)
        rot_z = math.degrees(-rotation.y)
        rotation_str = f"{rot_x:.1f} {rot_y:.1f} {rot_z:.1f}"
        
        camera_data = {
            "name": camera_obj.name,
            "position": position,
            "rotation": rotation_str,
            "fov": math.degrees(camera.angle) if camera.type == 'PERSP' else 50.0,
            "near": camera.clip_start,
            "far": camera.clip_end,
            "active": camera_obj == scene.camera  # Check if this is the active camera
        }
        
        return camera_data

    def create_default_aframe_camera(self):
        """Create a default camera for A-Frame if none exist"""
        return {
            "name": "DefaultCamera",
            "position": "0 1.6 3",
            "rotation": "0 0 0",
            "fov": 80,
            "near": 0.1,
            "far": 1000,
            "active": True
        }

    def get_aframe_lights_data(self, scene):
        """Extract all lights from the scene for A-Frame"""
        lights_data = []
        
        for obj in scene.objects:
            if obj.type == 'LIGHT':
                light_data = self.extract_aframe_light_data(obj)
                lights_data.append(light_data)
                print(f"Exported light: {obj.name} ({obj.data.type})")
        
        # If no lights found, create default lighting
        if not lights_data:
            print("No lights found, creating default lighting")
            lights_data.extend(self.create_default_aframe_lights())
        
        return lights_data

    def extract_aframe_light_data(self, light_obj):
        """Extract data from a Blender light object for A-Frame"""
        light = light_obj.data
        
        # Get world position and rotation
        location = light_obj.matrix_world.to_translation()
        rotation = light_obj.matrix_world.to_euler()
        
        # Convert to A-Frame coordinate system
        position = f"{location.x:.3f} {location.z:.3f} {-location.y:.3f}"
        
        # Convert rotation
        rot_x = math.degrees(rotation.x) - 90
        rot_y = math.degrees(rotation.z)
        rot_z = math.degrees(-rotation.y)
        rotation_str = f"{rot_x:.1f} {rot_y:.1f} {rot_z:.1f}"
        
        # Convert color to hex
        color = light.color
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(color[0] * 255), 
            int(color[1] * 255), 
            int(color[2] * 255)
        )
        
        # Map Blender light types to A-Frame types
        aframe_type = {
            'SUN': 'directional',
            'POINT': 'point',
            'SPOT': 'spot',
            'AREA': 'point'  # A-Frame doesn't have area lights
        }.get(light.type, 'point')
        
        # Convert Blender light energy to A-Frame intensity
        # Blender uses watts, A-Frame uses much smaller values
        # These conversion factors provide better visual parity
        intensity_conversion = {
            'SUN': 0.01,      # Sun/Directional lights are very strong in Blender
            'POINT': 0.02,    # Point lights need moderate conversion
            'SPOT': 0.02,     # Spot lights similar to point
            'AREA': 0.02      # Area lights (mapped to point)
        }
        
        conversion_factor = intensity_conversion.get(light.type, 0.02)
        aframe_intensity = light.energy * conversion_factor
        
        # Clamp intensity to reasonable A-Frame range (0.01 - 2.0)
        aframe_intensity = max(0.01, min(2.0, aframe_intensity))
        
        light_data = {
            "name": light_obj.name,
            "type": aframe_type,
            "position": position,
            "rotation": rotation_str,
            "color": hex_color,
            "intensity": round(aframe_intensity, 3)
        }
        
        # Add spot light specific properties
        if light.type == 'SPOT':
            light_data["angle"] = math.degrees(light.spot_size)
            light_data["penumbra"] = light.spot_blend
        
        return light_data

    def create_default_aframe_lights(self):
        """Create default lighting for A-Frame if none exist"""
        return [
            {
                "name": "AmbientLight",
                "type": "ambient",
                "color": "#404040",
                "intensity": 0.4
            },
            {
                "name": "DirectionalLight",
                "type": "directional",
                "position": "0 1 1",
                "color": "#ffffff",
                "intensity": 0.6
            }
        ]

    def save_scene_data(self, project_directory, scene_data):
        """Save scene data as JSON file"""
        scene_file = os.path.join(project_directory, "scene_data.json")
        with open(scene_file, 'w') as f:
            json.dump(scene_data, f, indent=2)
        print(f"Scene data saved to: {scene_file}")

    # ============================================================================
    # ELECTRON APP SETUP METHODS
    # ============================================================================

    def setup_electron_app(self, source_dir, target_app_dir, app_name):
        """Setup the Electron application directory"""
        print(f"Setting up Electron app:")
        print(f"  Source: {source_dir}")
        print(f"  Target: {target_app_dir}")
        print(f"  App name: {app_name}")
        
        # Remove existing app directory if it exists
        if os.path.exists(target_app_dir):
            print(f"  Removing existing app directory...")
            shutil.rmtree(target_app_dir)
        
        # Copy project files to app directory
        print(f"  Copying project files...")
        shutil.copytree(source_dir, target_app_dir)
        
        # Create/update essential Electron files
        self.ensure_electron_files(target_app_dir, app_name)
        
        print(f"  Electron app setup complete!")

    def ensure_electron_files(self, app_dir, app_name):
        """Create or update essential Electron files"""
        package_json_path = os.path.join(app_dir, "package.json")
        main_js_path = os.path.join(app_dir, "main.js")
        index_html_path = os.path.join(app_dir, "index.html")
        
        if not os.path.exists(package_json_path):
            self.create_package_json(app_dir, app_name)
        
        if not os.path.exists(main_js_path):
            self.create_main_js(app_dir, app_name)
            
        # Always recreate index.html to include current scene data
        self.create_aframe_html(app_dir, app_name)

    def create_package_json(self, app_dir, app_name):
        """Create package.json for Electron app"""
        package_json = {
            "name": app_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": f"{app_name} A-Frame Application",
            "main": "main.js",
            "scripts": {
                "start": "electron ."
            }
        }
        
        package_json_path = os.path.join(app_dir, "package.json")
        with open(package_json_path, 'w') as f:
            json.dump(package_json, f, indent=2)
        
        print(f"  Created package.json")

    def create_main_js(self, app_dir, app_name):
        """Create main Electron process file"""
        width = str(bpy.data.scenes["Scene"].render.resolution_x / bpy.data.scenes["Scene"].render.resolution_percentage)
        height = str(bpy.data.scenes["Scene"].render.resolution_y / bpy.data.scenes["Scene"].render.resolution_percentage)
        main_js_content = f'''const {{ app, BrowserWindow }} = require('electron');
const path = require('path');

function createWindow() {{
    const mainWindow = new BrowserWindow({{
        width: {width},
        height: {height},
        title: '{app_name}',
        webPreferences: {{
            nodeIntegration: false,
            contextIsolation: true,
            webSecurity: false  // Allow loading local files
        }}
    }});

    // Load the index.html file
    mainWindow.loadFile('index.html');

    // Open DevTools in development
    // mainWindow.webContents.openDevTools();
}}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {{
    if (process.platform !== 'darwin') {{
        app.quit();
    }}
}});

app.on('activate', () => {{
    if (BrowserWindow.getAllWindows().length === 0) {{
        createWindow();
    }}
}});
'''
        
        main_js_path = os.path.join(app_dir, "main.js")
        with open(main_js_path, 'w') as f:
            f.write(main_js_content)
        
        print(f"  Created main.js")

    def create_aframe_html(self, app_dir, app_name):
        """Create A-Frame HTML file with dynamic scene data"""
        # Load the scene data we just created
        scene_data_path = os.path.join(app_dir, "scene_data.json")
        scene_data = {}
        
        if os.path.exists(scene_data_path):
            with open(scene_data_path, 'r') as f:
                scene_data = json.load(f)
        
        # Generate A-Frame HTML content
        html_content = self.generate_aframe_html(app_name, scene_data)
        
        index_html_path = os.path.join(app_dir, "index.html")
        with open(index_html_path, 'w') as f:
            f.write(html_content)
        
        print(f"  Created A-Frame index.html")

    def generate_aframe_html(self, app_name, scene_data):
        """Generate complete A-Frame HTML with cameras and lights"""
        
        # Environment settings
        environment = scene_data.get('environment', {})
        background = environment.get('background', 'color: #222222')
        
        # Generate camera entities
        cameras = scene_data.get('cameras', [])
        camera_html = ""
        active_camera_found = False
        
        for camera in cameras:
            is_active = camera.get('active', False)
            if is_active:
                active_camera_found = True
            
            look_controls = 'look-controls' if is_active else ''
            wasd_controls = 'wasd-controls' if is_active else ''
            
            camera_html += f'''      <a-entity 
        id="{camera['name']}"
        camera="fov: {camera['fov']}; near: {camera['near']}; far: {camera['far']}; active: {str(is_active).lower()}"
        position="{camera['position']}"
        rotation="{camera['rotation']}"
        {look_controls}
        {wasd_controls}>
      </a-entity>
'''
        
        # If no active camera was found, make the first one active
        if not active_camera_found and cameras:
            camera_html = camera_html.replace('active: false', 'active: true', 1)
            camera_html = camera_html.replace('>', 'look-controls wasd-controls>', 1)
        
        # Generate light entities
        lights = scene_data.get('lights', [])
        lights_html = ""
        
        for light in lights:
            light_type = light['type']
            
            if light_type == 'ambient':
                lights_html += f'''      <a-light 
        type="ambient" 
        color="{light['color']}" 
        intensity="{light['intensity']}">
      </a-light>
'''
            elif light_type == 'directional':
                lights_html += f'''      <a-light 
        type="directional" 
        position="{light['position']}" 
        rotation="{light['rotation']}"
        color="{light['color']}" 
        intensity="{light['intensity']}">
      </a-light>
'''
            elif light_type == 'point':
                lights_html += f'''      <a-light 
        type="point" 
        position="{light['position']}" 
        color="{light['color']}" 
        intensity="{light['intensity']}">
      </a-light>
'''
            elif light_type == 'spot':
                angle = light.get('angle', 60)
                penumbra = light.get('penumbra', 0)
                lights_html += f'''      <a-light 
        type="spot" 
        position="{light['position']}" 
        rotation="{light['rotation']}"
        color="{light['color']}" 
        intensity="{light['intensity']}"
        angle="{angle}"
        penumbra="{penumbra}">
      </a-light>
'''
        
        # Generate model entities
        models = scene_data.get('models', ['scene.glb'])
        models_html = ""
        
        for i, model in enumerate(models):
            model_id = f"model{i}"
            models_html += f'''        <a-asset-item id="{model_id}" src="{model}"></a-asset-item>
'''
        
        model_entities = ""
        for i, model in enumerate(models):
            model_id = f"model{i}"
            model_entities += f'''      <a-entity gltf-model="#{model_id}"></a-entity>
'''
        
        # Complete HTML template
        html_content = f'''<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>{app_name}</title>
    <meta name="description" content="{app_name} - A-Frame">
    <script src="https://aframe.io/releases/1.7.0/aframe.min.js"></script>
  </head>
  <body>
    <a-scene background="{background}" vr-mode-ui="enabled: false">
      <a-assets>
{models_html}      </a-assets>

{lights_html}
{camera_html}
{model_entities}
    </a-scene>
  </body>
</html>'''
        
        return html_content

    # ============================================================================
    # ELECTRON LAUNCH METHOD
    # ============================================================================

    def launch_electron(self, electron_exe_path, working_dir):
        """Launch the Electron application in a separate thread"""
        def run_in_thread(cmd, working_dir):
            try:
                print(f"Starting Electron app: {' '.join(cmd)}")
                print(f"Working directory: {working_dir}")
                
                p = subprocess.Popen(cmd, cwd=working_dir)
                proc_state["process"] = p
                p.wait()
                
                print(f"Electron app finished with return code: {p.returncode}")
                
            except Exception as ex:
                print(f"Error running Electron app: {ex}")
            finally:
                proc_state["process"] = None

        cmd = [electron_exe_path]
        thread = threading.Thread(target=run_in_thread, args=(cmd, working_dir))
        thread.daemon = True
        thread.start()


# Initialize process state
proc_state = {"process": None}

class NX_Stop(bpy.types.Operator):
    bl_idname = "nx.stop"
    bl_label = "Stop"
    bl_description = "Stop your project"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        global proc_state

        p = proc_state["process"]
        if p is None:
            self.report({'WARNING'}, "No process is running!")
            return {'CANCELLED'}

        # Check if process is still running
        if p.poll() is not None:
            self.report({'INFO'}, "Process has already finished")
            proc_state["process"] = None
            return {'FINISHED'}

        # Politely ask process to terminate
        try:
            p.terminate()  # On Windows, this sends CTRL-BREAK for console apps
            
            # Optional: Wait a bit for graceful shutdown, then force kill if needed
            try:
                p.wait(timeout=5)  # Wait up to 5 seconds
                self.report({'INFO'}, "Process terminated gracefully")
            except subprocess.TimeoutExpired:
                p.kill()  # Force kill if it doesn't respond
                self.report({'INFO'}, "Process force-killed after timeout")
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to terminate: {e}")
            return {'CANCELLED'}

        # Clear the process reference
        proc_state["process"] = None
        return {'FINISHED'}
    
class NX_Clean(bpy.types.Operator):
    bl_idname = "nx.clean"
    bl_label = "Clean"
    bl_description = "Clean your project"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        file_path = bpy.data.filepath
        if not file_path:
            self.report({'ERROR'}, "Please save your Blender project first.")
            return {"CANCELLED"}

        project_directory = os.path.join(os.path.dirname(file_path), "build")

        try:
            subprocess.run(["cargo", "clean"], cwd=project_directory, check=True)
            self.report({'INFO'}, "Project cleaned successfully.")
        except Exception as e:
            print(f"Unexpected error: {e}")

        return {"FINISHED"}
    
class NX_Explore(bpy.types.Operator):
    bl_idname = "nx.explore"
    bl_label = "Explore"
    bl_description = "Explore your project"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        #Open the path in explorer

        path = util.get_project_path()

        os.startfile(path)

        return {"FINISHED"}
    





def compileToKTX(texture_in, texture_out, HDR, Env=False):

    ktx_path = r"C:\Users\kleem\AppData\Roaming\Blender Foundation\Blender\4.2\scripts\addons\NEST\binaries\ktx"

    ktx_binary = os.path.join(ktx_path, "ktx.exe")
    cmgen_binary = os.path.join(ktx_path, "cmgen.exe")
    ktx2ktx2_binary = os.path.join(ktx_path, "ktx2ktx2.exe")
    ktxsc_binary = os.path.join(ktx_path, "ktxsc.exe")

    asset_folder = os.path.join(util.get_project_path(), "build", "assets")
    
    if HDR:

        cmgen_command = [
            cmgen_binary, 
            "--size=256", 
            "--format=ktx",
            "--deploy=" + asset_folder,
            texture_in
        ]
        subprocess.run(cmgen_command, check=True)

        ktx2ktx2_command_diffuse = [
            ktx2ktx2_binary,
            "-o", os.path.join(asset_folder, "assets_diffuse.ktx2"),
            os.path.join(asset_folder, "assets_skybox.ktx")
        ]
        subprocess.run(ktx2ktx2_command_diffuse, check=True)

        ktx2ktx2_command_specular = [
            ktx2ktx2_binary,
            "-o", os.path.join(asset_folder, "assets_specular.ktx2"),
            os.path.join(asset_folder, "assets_ibl.ktx")
        ]
        subprocess.run(ktx2ktx2_command_specular, check=True)


        ktxsc_command_diffuse = [
            ktxsc_binary,
            "--zcmp","20",
            "-o", os.path.join(asset_folder, "assets_diffuse_zstd.ktx2"),
            os.path.join(asset_folder, "assets_diffuse.ktx2")
        ]
        print(ktxsc_command_diffuse)
        subprocess.run(ktxsc_command_diffuse, check=True)

        ktxsc_command_specular = [
            ktxsc_binary,
            "--zcmp", "20",
            "-o", os.path.join(asset_folder, "assets_specular_zstd.ktx2"),
            os.path.join(asset_folder, "assets_specular.ktx2")
        ]
        subprocess.run(ktxsc_command_specular, check=True)
        
    else:

        ktx_command = [
            ktx_path,
            "create",
            "--generate-mipmap",
            "--zstd", "1",
            "--assign-oetf","srgb",
            "--format", "R8G8B8A8_SRGB",
            texture_in,
            texture_out
        ]

        subprocess.run(ktx_command, check=True)


































class NX_ModuleListNewItem(bpy.types.Operator):
    # Add a new item to the list
    bl_idname = "nx_modulelist.new_item"
    bl_label = "Add a new module"
    bl_description = "Add a new module"

    def execute(self, context):
        obj = context.object

        obj.NX_UL_ModuleList.add()

        obj.NX_UL_ModuleListItem = len(obj.NX_UL_ModuleList) - 1
        obj.NX_UL_ModuleList[len(obj.NX_UL_ModuleList) - 1].name = "Module"

        util.getProjectJSScripts()
        util.getBundledScripts()

        return{'FINISHED'}
    
class NX_UL_PostprocessListNewItem(bpy.types.Operator):
    # Add a new item to the list
    bl_idname = "nx_postprocesslist.new_item"
    bl_label = "Add a new postprocess"
    bl_description = "Add a new postprocess"

    def execute(self, context):
        scene = context.scene

        scene.NX_UL_PostprocessList.add()

        scene.NX_UL_PostprocessListItem = len(scene.NX_UL_PostprocessList) - 1
        scene.NX_UL_PostprocessList[len(scene.NX_UL_PostprocessList) - 1].name = "Postprocess"

        return{'FINISHED'}
    
class NX_UL_PostprocessListRemoveItem(bpy.types.Operator):
    # Delete the selected item from the list
    bl_idname = "nx_postprocesslist.delete_item"
    bl_label = "Removes the postprocess"
    bl_description = "Delete a postprocess"

    def execute(self, context):
        scene = context.scene
        list = scene.NX_UL_PostprocessList
        index = scene.NX_UL_PostprocessListItem

        list.remove(index)

        if index > 0:
            index = index - 1

        scene.NX_UL_PostprocessListItem = index

        return{'FINISHED'}
    
class NX_ModuleListRemoveItem(bpy.types.Operator):
    # Delete the selected item from the list
    bl_idname = "nx_modulelist.delete_item"
    bl_label = "Removes the module"
    bl_description = "Delete a module"

    @classmethod
    def poll(self, context):
        """ Enable if there's something in the list """
        obj = context.object
        return len(obj.NX_UL_ModuleList) > 0

    def execute(self, context):
        obj = context.object
        list = obj.NX_UL_ModuleList
        index = obj.NX_UL_ModuleListItem

        list.remove(index)

        if index > 0:
            index = index - 1

        obj.NX_UL_ModuleListItem = index

        util.getProjectJSScripts()
        util.getBundledScripts()

        return{'FINISHED'}
    
class NX_NewJavascriptFile(bpy.types.Operator):
    bl_idname = "nx_modulelist.new_script"
    bl_label = "New Script"

    filename: bpy.props.StringProperty(name="Filename (*.rs)")

    def execute(self, context):

        obj = context.object
        list = obj.NX_UL_ModuleList
        index = obj.NX_UL_ModuleListItem

        print("Creating Rust file at sources folder", self.filename)

        if(filemaker.create_rust_file(self.filename)):

            obj.NX_UL_ModuleList[index].nx_module_script = self.filename

            util.fetchBundledScriptProps(obj.NX_UL_ModuleList[index])

            print("Rust file created")

        else:
            
            print("TODO: ERROR")

        util.getProjectJSScripts()
        util.getBundledScripts()

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
    
class NX_EditJavascriptFile(bpy.types.Operator):
    bl_idname = "nx_modulelist.edit_script"
    bl_label = "Edit Script"

    def execute(self, context):

        obj = context.object
        list = obj.NX_UL_ModuleList
        index = obj.NX_UL_ModuleListItem

        #If file exists in the sources path
        if os.path.exists(os.path.join(util.get_sources_path(), list[index].nx_module_script + ".rs")):
            file = os.path.join(util.get_sources_path(), list[index].nx_module_script + ".rs")
        else:
            #If it doesn't exist, we look into the 
            if os.path.exists(os.path.join(util.get_bundled_scripts_path(), list[index].nx_module_script + ".rs")):
                shutil.copy(os.path.join(util.get_bundled_scripts_path(), list[index].nx_module_script + ".rs"), util.get_sources_path())
                file = os.path.join(util.get_sources_path(), list[index].nx_module_script + ".rs")
            else:
                return {'FINISHED'}

        obj.NX_UL_ModuleList[index].nx_module_type = "Rust"

        os.system(file)

        print("Editing Rust file at sources folder: ", list[index].nx_module_script)

        util.getProjectJSScripts()
        util.getBundledScripts()

        return {'FINISHED'}
    
class NX_RefreshScripts(bpy.types.Operator):
    bl_idname = "nx_modulelist.refresh_scripts"
    bl_label = "Refresh scripts"

    def execute(self, context):

        util.getProjectJSScripts()
        util.getBundledScripts()

        return {'FINISHED'}
    
class NX_OpenStore(bpy.types.Operator):
    bl_idname = "nx.open_store"
    bl_label = "Open Store"

    def execute(self, context):

        subprocess.Popen([os.path.join(util.get_binaries_path(), "blacksmith/Blacksmith-Client.exe")])

        return {'FINISHED'}