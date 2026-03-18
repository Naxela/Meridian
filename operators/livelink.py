import bpy
import socket
import json
import time
import math
import threading
from bpy.app.handlers import persistent
from mathutils import Matrix

# ===== MODULE-LEVEL STATE =====

_socket = None
_connected = False
_running = False
_reconnecting = False
_reconnect_failures = 0
_lock = threading.Lock()
_last_update = {}  # obj_name -> float (time of last successful send)

MAX_RECONNECT_ATTEMPTS = 5  # stop LiveLink after this many consecutive failures

THROTTLE = 0.1  # minimum seconds between updates per object

# Debug flag — set to False to silence verbose output
DEBUG = True

def _dbg(*args):
    if DEBUG:
        print("Meridian LiveLink [DBG]:", *args)


def is_connected():
    return _connected


def is_running():
    return _running


def is_reconnecting():
    return _reconnecting


def _connect_async(port):
    """Run connect() in a background thread so the main thread never blocks."""
    global _reconnecting, _reconnect_failures, _running
    try:
        success = connect(port)
        if success:
            _reconnect_failures = 0
        else:
            _reconnect_failures += 1
            if _reconnect_failures >= MAX_RECONNECT_ATTEMPTS:
                print(f"Meridian LiveLink: Gave up after {MAX_RECONNECT_ATTEMPTS} failed attempts — stopping.")
                _running = False
    finally:
        _reconnecting = False


# ===== CONNECTION HELPERS =====

def connect(port):
    global _socket, _connected
    _do_disconnect()
    _dbg(f"Attempting connection to localhost:{port} ...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(('localhost', port))
        sock.settimeout(0.05)
        with _lock:
            _socket = sock
            _connected = True
        print(f"Meridian LiveLink: Connected to Godot on port {port}")
        return True
    except Exception as e:
        print(f"Meridian LiveLink: Connection failed: {e}")
        return False


def _do_disconnect():
    global _socket, _connected, _reconnect_failures
    with _lock:
        if _socket:
            _dbg("Closing socket")
            try:
                _socket.close()
            except Exception:
                pass
            _socket = None
        _connected = False
    _last_update.clear()
    _reconnect_failures = 0


def send(data):
    global _connected
    if not _connected:
        return False
    try:
        msg = (json.dumps(data) + '\n').encode('utf-8')
        with _lock:
            if _socket:
                _socket.sendall(msg)
        _dbg(f"Sent → name='{data.get('name')}'")
        return True
    except Exception as e:
        print(f"Meridian LiveLink: Disconnected ({e})")
        _do_disconnect()
        return False


# ===== PAYLOAD BUILDER =====

_CAM_CORRECTION = Matrix.Rotation(math.radians(-90), 4, 'X')

def _build_payload(obj):
    """
    Build the transform payload in the format the Godot plugin expects:
      { name, position, basis_x, basis_y, basis_z }

    The Godot plugin sets transform.basis.{x,y,z} (columns) from the received
    vectors and then calls transform.basis = transform.basis.inverse().
    We need M.inverse() = F (desired Godot basis with scale).
    Therefore M = F.inverse() = S.inverse() * R.T, whose columns are:
      col i = (gx[i]/sx, gy[i]/sy, gz[i]/sz)
    This preserves the object's non-uniform scale in Godot.
    """
    loc, rot, blender_scale = obj.matrix_world.decompose()
    rot = rot.conjugated()
    mat = rot.to_matrix().to_4x4()
    mat.translation = loc

    # Apply the same -90° X correction used for cameras and lights in the static export
    if obj.type in ('CAMERA', 'LIGHT'):
        mat = mat @ _CAM_CORRECTION

    # Blender matrix rows (pure rotation part, no scale)
    bx = (mat[0][0], mat[0][1], mat[0][2])
    by = (mat[1][0], mat[1][1], mat[1][2])
    bz = (mat[2][0], mat[2][1], mat[2][2])

    # Convert Blender Z-up basis columns → Godot Y-up basis columns (unit vectors)
    gx = ( bx[0],  bx[2], -bx[1])   # Godot X col
    gy = ( bz[0],  bz[2], -bz[1])   # Godot Y col
    gz = (-by[0], -by[2],  by[1])   # Godot Z col

    # Map Blender scale axes to Godot axes: Blender X→Godot X, Blender Z→Godot Y, Blender Y→Godot Z
    sx = blender_scale.x if blender_scale.x != 0.0 else 1.0
    sy = blender_scale.z if blender_scale.z != 0.0 else 1.0
    sz = blender_scale.y if blender_scale.y != 0.0 else 1.0

    # Godot node names have dots/spaces replaced with underscores (GLTF export convention)
    godot_name = obj.name.replace('.', '_').replace(' ', '_')

    return {
        'name':    godot_name,
        'position': [mat[0][3], mat[2][3], -mat[1][3]],
        'basis_x': [gx[0]/sx, gy[0]/sy, gz[0]/sz],   # col 0 of M = F.inverse()
        'basis_y': [gx[1]/sx, gy[1]/sy, gz[1]/sz],   # col 1
        'basis_z': [gx[2]/sx, gy[2]/sy, gz[2]/sz],   # col 2
    }


# ===== DEPSGRAPH HANDLER =====

_handler_call_count = 0

@persistent
def _depsgraph_handler(scene, depsgraph):
    global _handler_call_count
    _handler_call_count += 1

    # Log every 100th call so we can confirm the handler is alive
    if DEBUG and _handler_call_count % 100 == 0:
        _dbg(f"Handler alive (call #{_handler_call_count}), running={_running}, connected={_connected}")

    if not _running or not _connected:
        return

    try:
        props = bpy.context.scene.MX_SceneProperties
        if not props.mx_livelink_enabled:
            _dbg("Handler skipped: mx_livelink_enabled is False")
            return
        if not props.mx_livelink_auto_update:
            _dbg("Handler skipped: mx_livelink_auto_update is False")
            return

        now = time.time()
        all_updates = list(depsgraph.updates)
        obj_updates = [u for u in all_updates if isinstance(u.id, bpy.types.Object)]
        transform_updates = [u for u in obj_updates if u.is_updated_transform]

        if DEBUG and (obj_updates or transform_updates):
            _dbg(f"depsgraph updates: total={len(all_updates)}, objects={len(obj_updates)}, transforms={len(transform_updates)}")

        for update in transform_updates:
            obj = update.id
            name = obj.name

            elapsed = now - _last_update.get(name, 0.0)
            if elapsed < THROTTLE:
                _dbg(f"  Throttled '{name}' ({elapsed:.3f}s < {THROTTLE}s)")
                continue

            _last_update[name] = now
            payload = _build_payload(obj)
            ok = send(payload)
            _dbg(f"  Update '{name}' → '{payload['name']}' (type={obj.type}) send={'OK' if ok else 'FAILED'} pos={payload['position']}")

    except Exception as e:
        print(f"Meridian LiveLink handler error: {e}")
        import traceback
        traceback.print_exc()


def _register_handler():
    if _depsgraph_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_depsgraph_handler)
        _dbg("depsgraph_update_post handler registered")
    else:
        _dbg("depsgraph_update_post handler already registered")


def _unregister_handler():
    if _depsgraph_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_depsgraph_handler)
        _dbg("depsgraph_update_post handler unregistered")


# ===== OPERATORS =====

class MX_OT_LiveLink(bpy.types.Operator):
    """Connect to Godot LiveLink and start monitoring scene changes"""
    bl_idname = "mx.livelink_start"
    bl_label = "Start LiveLink"
    bl_options = {'REGISTER'}

    _timer = None

    def modal(self, context, event):
        if not _running:
            _dbg("Modal: _running=False, cancelling")
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if not _connected:
                global _reconnecting
                props = context.scene.MX_SceneProperties
                if not _reconnecting:
                    _reconnecting = True
                    _dbg(f"Modal timer: not connected, retrying on port {props.mx_livelink_godot_port} (async)")
                    threading.Thread(target=_connect_async, args=(props.mx_livelink_godot_port,), daemon=True).start()
                else:
                    _dbg("Modal timer: reconnect already in progress")
            else:
                _dbg("Modal timer: still connected OK")

        return {'PASS_THROUGH'}

    def execute(self, context):
        global _running
        props = context.scene.MX_SceneProperties

        _dbg(f"execute: godot_port={props.mx_livelink_godot_port}, enabled={props.mx_livelink_enabled}, auto_update={props.mx_livelink_auto_update}")

        _running = True
        global _reconnecting
        _reconnecting = True
        threading.Thread(target=_connect_async, args=(props.mx_livelink_godot_port,), daemon=True).start()
        _dbg("Initial connect started (async)")

        _register_handler()

        wm = context.window_manager
        self._timer = wm.event_timer_add(2.0, window=context.window)
        wm.modal_handler_add(self)

        self.report({'INFO'}, "LiveLink started (connecting...)")
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        _dbg("cancel() called")
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        _unregister_handler()
        _do_disconnect()


class MX_OT_LiveLinkStop(bpy.types.Operator):
    """Disconnect from Godot LiveLink"""
    bl_idname = "mx.livelink_stop"
    bl_label = "Stop LiveLink"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _running
        _dbg("Stop operator called")
        _running = False
        _unregister_handler()
        _do_disconnect()
        self.report({'INFO'}, "LiveLink stopped")
        return {'FINISHED'}
