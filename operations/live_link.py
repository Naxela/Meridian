import bpy
import requests
import json
import math
import os
from typing import Any, Type

bl_info = {
    "name": "Blender to Bevy Live Connection",
    "author": "YourName",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "category": "Object",
    "description": "Live connection between Blender and Bevy using BRP",
}

# BRP connection settings
BRP_HOST = "127.0.0.1"
BRP_PORT = 15702  # Default BRP port

# Any object can act as a message bus owner
msgbus_owner = object()

# Use a module-level variable without double underscores to avoid name mangling
is_running = False
"""Whether live connection is currently active"""

# Component names
LIGHT_COMPONENT_NAME = "bevy_pbr::light::point_light::PointLight"  # Default, will be confirmed/updated at runtime

def send_brp_request(method, params):

    global is_running

    """Send a request to the Bevy Remote Protocol server."""
    url = f"http://{BRP_HOST}:{BRP_PORT}"
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "id": 1,
        "params": params
    }
    
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        #print(f"BRP request error: {e}")
        is_running = False
        return None

def query_entity_by_nestid(nx_id, namespace):
    """Query for an entity with a specific NESTID."""
    query_result = send_brp_request("bevy/query", {
        "data": {
            "components": [namespace+"::NESTID"],
            "has": [namespace+"::NESTID"]
        },
        "filter": {
            "with": [namespace+"::NESTID"]
        }
    })
    
    if not query_result or "result" not in query_result:
        return None
    
    for entity in query_result["result"]:
        nestid = entity["components"].get(namespace+"::NESTID")
        if nestid == nx_id:
            return entity["entity"]

def updatePostProcess(self, context):

    print("TODO UPDATE POSTPROCESS")
    print(self)
    print(context)

def get_object_matrix_bevy(obj):
    """Convert Blender matrix to Bevy-compatible format with refined spotlight handling."""
    mat = obj.matrix_world.copy()
    loc, rot, scale = mat.decompose()
    
    # Convert to Bevy coordinate system
    bevy_loc = [loc.x, loc.z, -loc.y]
    
    # Special handling for spotlights
    if obj.type == 'LIGHT' and (obj.data.type == 'SPOT' or obj.data.type == 'SUN'):
        import mathutils
        
        # First rotate 180° around Z axis (this part works fine according to feedback)
        z_rotation = mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(180.0))
        
        # Then rotate -90° around X to correct the X axis misalignment
        x_correction = mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0))
        
        # Apply both rotations to the original rotation
        # Order matters for quaternion multiplication
        adjusted_rot = rot @ z_rotation @ x_correction
        
        # Convert the adjusted quaternion to Bevy coordinate system
        bevy_rot = [adjusted_rot.x, adjusted_rot.z, -adjusted_rot.y, adjusted_rot.w]
    else:
        # Regular rotation conversion for other objects
        bevy_rot = [rot.x, rot.z, -rot.y, rot.w]
    
    bevy_scale = [scale.x, scale.z, scale.y]
    
    return {
        "translation": bevy_loc,
        "rotation": bevy_rot,
        "scale": bevy_scale
    }

def start():
    """Start the live connection session."""
    global is_running, LIGHT_COMPONENT_NAME
    
    if is_running:
        return
    
    print("Starting Blender to Bevy live connection")
    
    # Test the connection
    test_result = send_brp_request("bevy/query", {})
    if not test_result:
        print("Failed to connect to Bevy BRP server")
        return
    
    # Set up listeners for transforms
    listen(bpy.types.Object, "location", "obj_location")
    listen(bpy.types.Object, "rotation_euler", "obj_rotation")
    listen(bpy.types.Object, "scale", "obj_scale")
    
    # Set up listeners for lights
    for light_type in (bpy.types.PointLight, bpy.types.SpotLight, bpy.types.SunLight, bpy.types.AreaLight):
        listen(light_type, "color", "light_color")
        listen(light_type, "energy", "light_energy")
    
    # Add depsgraph update handler
    if depsgraph_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)
    
    is_running = True
    print("Blender to Bevy live connection started")

def stop():
    """Stop the live connection session."""
    global is_running
    
    if not is_running:
        return
    
    is_running = False
    
    # Clear message bus subscriptions
    bpy.msgbus.clear_by_owner(msgbus_owner)
    
    # Remove depsgraph update handler
    if depsgraph_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    
    print("Blender to Bevy live connection stopped")

def listen(rna_type: Type[bpy.types.bpy_struct], prop: str, event_id: str):
    """Subscribe to RNA updates."""
    bpy.msgbus.subscribe_rna(
        key=(rna_type, prop),
        owner=msgbus_owner,
        args=(event_id,),
        notify=send_event
    )

def depsgraph_update_handler(scene, depsgraph):
    """Handle updates from the dependency graph."""
    if not is_running:
        return

    namespace = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    
    for update in depsgraph.updates:
        if isinstance(update.id, bpy.types.Object):
            obj = update.id
            
            # Skip objects without nx_id
            if "nx_id" not in obj:
                continue
            
            nx_id = obj["nx_id"]
            
            # Query for the entity in Bevy
            entity_id = query_entity_by_nestid(nx_id, namespace)
            if not entity_id:
                continue
            
            # Get transform data
            matrix_data = get_object_matrix_bevy(obj)
            
            # Update the transform in Bevy
            transform_name = "bevy_transform::components::transform::Transform"
            send_brp_request("bevy/insert", {
                "entity": entity_id,
                "components": {
                    transform_name: matrix_data
                }
            })

def send_event(event_id: str, opt_data: Any = None):
    """Handle message bus events."""
    if not is_running or not hasattr(bpy.context, 'object') or bpy.context.object is None:
        return
    
    obj = bpy.context.object
    
    # Skip objects without nx_id
    if "nx_id" not in obj:
        return
    
    nx_id = obj["nx_id"]
    
    # Only process events in object mode
    if obj.mode != "OBJECT":
        return

    namespace = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
    
    # For transform updates, use the regular query function
    if event_id in ("obj_location", "obj_rotation", "obj_scale"):
        entity_id = query_entity_by_nestid(nx_id, namespace)
        if not entity_id:
            return
            
        # Update transform + TODO:: WE NEED TO FIX SPOTLIGHT X-Z shift
        matrix_data = get_object_matrix_bevy(obj)
        transform_name = "bevy_transform::components::transform::Transform"
        send_brp_request("bevy/insert", {
            "entity": entity_id,
            "components": {
                transform_name: matrix_data
            }
        })
    
    # For light updates, use the specialized query function
    elif event_id in ("light_color", "light_energy") and hasattr(obj, 'data'):

        entity_id = query_entity_by_nestid(nx_id, namespace)
        if not entity_id:
            return

        #Check if the entity has a LightController already?
        get_result = send_brp_request("bevy/get", {
            "entity": entity_id,
            "components": [namespace+"::LightController"]
        })

        controller = get_result["result"]["components"][namespace+"::LightController"]

        controller["color"] = {
            "Srgba": {
                "red": obj.data.color[0],
                "green": obj.data.color[1],
                "blue": obj.data.color[2],
                "alpha": 1.0
            }, 
        }

        #Blender to GLTF => 683 lumen/watt / (4 * math.pi) => GLTF to Bevy => Energy * Pi * 4.0
        controller["intensity"] = ((obj.data.energy * 683) / (12.566370614359172)) * math.pi * 4.0
        
        #
        send_brp_request("bevy/insert", {
            "entity": entity_id,
            "components": {
                namespace+"::LightController": controller
            }
        })

# UI Classes
class BevyConnectionPanel(bpy.types.Panel):
    """UI Panel for the Bevy Connection."""
    bl_label = "Bevy Connection"
    bl_idname = "OBJECT_PT_bevy_connection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bevy'
    
    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        if is_running:
            row.operator("bevy.stop_connection", text="Stop Connection")
        else:
            row.operator("bevy.start_connection", text="Start Connection")


class StartBevyConnectionOperator(bpy.types.Operator):
    """Start the Bevy Connection."""
    bl_idname = "bevy.start_connection"
    bl_label = "Start Bevy Connection"
    
    def execute(self, context):
        start()
        return {'FINISHED'}


class StopBevyConnectionOperator(bpy.types.Operator):
    """Stop the Bevy Connection."""
    bl_idname = "bevy.stop_connection"
    bl_label = "Stop Bevy Connection"
    
    def execute(self, context):
        stop()
        return {'FINISHED'}


# Registration
classes = (
    BevyConnectionPanel,
    StartBevyConnectionOperator,
    StopBevyConnectionOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    # Ensure connection is stopped
    stop()

if __name__ == "__main__":
    register()