import bpy, math, mathutils, os, json, glob, re

class WorkingDir:
    """Context manager for safely changing the current working directory."""
    def __init__(self, cwd: str):
        self.cwd = cwd
        self.prev_cwd = os.getcwd()

    def __enter__(self):
        os.chdir(self.cwd)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.prev_cwd)

#MATH/VECTOR/MATRIX HELPERS
def get_object_matrix_y_axis(obj):
    matrix_world = obj.matrix_world

    # Create a rotation matrix (rotating -90 degrees around X-axis)
    rot_x_90 = mathutils.Matrix.Rotation(-math.pi / 2, 4, 'X')

    # Apply the rotation to the world matrix
    adjusted_matrix = rot_x_90 @ matrix_world

    # Flatten the matrix into a list
    matrix_flat = [val for row in adjusted_matrix for val in row]
    return(matrix_flat)

def ensureFilesave():

    currentSavePath = bpy.data.filepath

    if currentSavePath:
        return True
    else:
        return False

def getObjectParent(obj):
    if(obj.parent):
        return obj.parent["nx_id"]
    else:
        return None

def is_generated_project_present():

    currentSavePath = bpy.data.filepath
    currentSaveDir = os.path.dirname(currentSavePath)

    project_name = "nx-build"
    directory = os.path.join(currentSaveDir, project_name)  # Set your desired path here

    package_json_path = os.path.join(directory, 'package.json')

    # Check if package.json exists
    if not os.path.isfile(package_json_path):
        return False

    # Optional: Validate the contents of package.json
    try:
        with open(package_json_path, 'r') as file:
            package_data = json.load(file)

        return True
        # You can add more checks here to validate the structure of package.json
        # For example, check if certain fields exist:
        # if 'name' in package_data and 'scripts' in package_data:
        #     if package_data['name'] == 'test':
        #         return True
        #     else:
        #         return False
        # else:
        #     return False

    except json.JSONDecodeError:
        # The file is not a valid JSON
        return False

    return False

def get_addon_path():

    #Get the path of the blender addon
    current_file_path = os.path.realpath(__file__)
    
    # Get the directory containing the current file, which is the addon's directory.
    addon_path = os.path.dirname(current_file_path)
    
    # Get the parent directory of the addon's directory.
    parent_path = os.path.dirname(addon_path)

    return parent_path

def get_bundled_path():

    #Get the path of the bundled folder within the addon folder

    addon_path = bpy.path.abspath(get_addon_path())

    bundled_path = os.path.join(addon_path, "bundled")

    return bundled_path

def get_bundled_scripts_path():

    bundled_scripts_path = os.path.join(get_bundled_path(), "scripts")

    return bundled_scripts_path

def get_binaries_path():

    #Get the path of the bundled folder within the addon folder

    addon_path = bpy.path.abspath(get_addon_path())

    binaries_path = os.path.join(addon_path, "binaries")

    return binaries_path

def get_project_path():

    currentSavePath = bpy.data.filepath
    currentSaveDir = os.path.dirname(currentSavePath)

    #project_name = "nx-build"
    #directory = os.path.join(currentSaveDir, project_name)  # Set your desired path here

    #if(not os.path.exists(directory)):
    #    os.mkdir(directory)

    return currentSaveDir


# [dependencies]
# bevy = { version = "0.15.2", features = ["png", "jpeg", "bevy_ui", "asset_processor", "mp3", "bevy_remote", "serialize"]}
# wasm-logger = "0.2"
# log = "0.4"
# wasm-bindgen = "0.2.100"
# serde = { version = "1.0", features = ["derive"] }
# serde_json = "1.0"
# bevy_panorbit_camera = "0.21.1"
# bevy_blendy_cameras = "0.6"
# webbrowser = "1.0.3"
# meval = "0.2"

def create_cargo_manifest(name, version, edition, debug, append="", xr=False, webgl=False):

    if bpy.data.scenes["Scene"].NX_SceneProperties.nest_platform == "WebGL":
        bevy_features = """["png", "jpeg", "bevy_ui", "mp3"]"""
    else:
        bevy_features = """["png", "jpeg", "bevy_ui", "asset_processor", "mp3", "bevy_remote", "serialize"]"""

    cargo = """
[package]
name = \"""" + name + """\"
version = \"""" + version + """\"
edition = \"""" + edition + """\"

[profile.dev]
# Completely disable warnings in development builds
warnings = false

# Or, for Bevy specifically, you can use an override:
[profile.dev.package."*"]
opt-level = 3

[dependencies]
bevy = { version = "0.15.2", features = """ + bevy_features + """}
wasm-logger = "0.2"
log = "0.4"
wasm-bindgen = "0.2.100"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
bevy_blendy_cameras = "0.6"
meval = "0.2"
"""

    if append != "":
        cargo += append

    if xr:
        cargo += """
bevy_mod_openxr.git = "https://github.com/awtterpip/bevy_oxr.git"
bevy_mod_xr.git = "https://github.com/awtterpip/bevy_oxr.git"
bevy_xr_utils.git = "https://github.com/awtterpip/bevy_oxr.git"
openxr = "0.19.0"
        """

    if debug:
        cargo += """
bevy-inspector-egui = "=0.30.0"
        """



    cargo += """
[features]
        """

    if debug:
        cargo += """
debug_inspector = []
        """

    if xr:
        cargo += """
xr_mode = []
        """  
    

    return cargo

def create_index_html(name):
    index = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>"""+name+"""</title>
</head>
<body>
    <script type="module">
        import init from "./"""+name+""".js";
        init();
    </script>
    <style>
        body {
            margin: 0px;
            overflow: hidden;
        }
    </style>
</body>
</html>
    """

    return index

def get_build_path():

    project_path = get_project_path()

    directory = os.path.join(project_path, "nx-build")  # Set your desired path here

    if(not os.path.exists(directory)):
        os.mkdir(directory)

    return directory

def get_assets_path():

    project_path = get_project_path()

    directory = os.path.join(project_path, "assets")  # Set your desired path here

    if(not os.path.exists(directory)):
        os.mkdir(directory)

    return directory

def get_sources_path():

    project_path = get_project_path()

    directory = os.path.join(project_path, "Sources")  # Set your desired path here

    if(not os.path.exists(directory)):
        os.mkdir(directory)

    return directory

def get_shaders_path():

    project_path = get_project_path()

    directory = os.path.join(project_path, "Shaders")  # Set your desired path here

    if(not os.path.exists(directory)):
        os.mkdir(directory)

    return directory

def get_file_name():

    #Get the filename without extension and without path

    currentSavePath = bpy.data.filepath

    if currentSavePath:

        file_name = os.path.basename(currentSavePath)
        file_name = os.path.splitext(file_name)[0]

        return file_name
    
    return None

def fetchBundledScriptProps(bundled_script):

    print("Fetching bundled script props")
    print(bundled_script, bundled_script.nx_module_script, bundled_script.nx_module_script_format)

    #with open(filename, 'r', encoding='utf-8') as sourcefile:
    #    source = sourcefile.read()

    #if source == '':
    #    return

def getBundledScripts():

    world = bpy.data.worlds['NX']

    scripts_list = world.NX_bundled_list

    scripts_list.clear()

    sources_path = get_bundled_scripts_path()

    print(sources_path)

    if os.path.isdir(sources_path):
        with WorkingDir(sources_path):

            print("Testing in: ", sources_path)

            for file in glob.glob('**/*.rs', recursive=True):

                mod = file.rsplit('.', 1)[0]
                mod = mod.replace('\\', '/')
                mod_parts = mod.rsplit('/')
                if re.match('^[A-Z][A-Za-z0-9_]*$', mod_parts[-1]):
                    scripts_list.add().name = mod.replace('/', '.')
                #    fetch_script_props(file)
                    
    print("//Getting bundled scripts")
    print(scripts_list)

def getProjectJSScripts():

    world = bpy.data.worlds['NX']

    scripts_list = world.NX_scripts_list

    scripts_list.clear()

    sources_path = get_sources_path()

    if os.path.isdir(sources_path):
        with WorkingDir(sources_path):

            # Glob supports recursive search since python 3.5 so it should cover both blender 2.79 and 2.8 integrated python
            for file in glob.glob('**/*.rs', recursive=True):

                print("/////")
                print(file)

                mod = file.rsplit('.', 1)[0]
                mod = mod.replace('\\', '/')
                mod_parts = mod.rsplit('/')
                if re.match('^[A-Z][A-Za-z0-9_]*$', mod_parts[-1]):
                    scripts_list.add().name = mod.replace('/', '.')

    print("//Getting project scripts")
    print(scripts_list)