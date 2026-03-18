import bpy
import os
import json
import socket
import threading
import subprocess

# ── State ─────────────────────────────────────────────────────────────────────

BM_STATUS = {
    "active":    False,   # server loop running
    "connected": False,   # a client is currently connected
    "thread":    None,
    "socket":    None,
    "process":   None,    # Popen handle for the kiosk window
}

_KIOSK_PORT = 12345


def _kiosk_exe_path():
    addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(addon_dir, "binaries", "kiosk", "AssetKiosk.exe")


# ── Socket server ──────────────────────────────────────────────────────────────

def _handle_command(action, header, command=None):
    if action == 0:  # Ping — no-op
        pass
    elif action == 1:  # Query
        pass
    elif action == 2 and command == 1:  # Append scene objects
        filepath = header
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            data_to.objects = list(data_from.objects)
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.collection.objects.link(obj)
        print(f"[AssetKiosk] Appended objects from: {filepath}")


def _server_loop():
    srv = BM_STATUS["socket"]
    srv.bind(("127.0.0.1", _KIOSK_PORT))
    srv.listen(1)
    print(f"[AssetKiosk] Server listening on port {_KIOSK_PORT}")

    while BM_STATUS["active"]:
        try:
            conn, addr = srv.accept()
        except OSError:
            break  # socket was closed externally

        BM_STATUS["connected"] = True
        print(f"[AssetKiosk] Client connected: {addr[0]}:{addr[1]}")

        while BM_STATUS["active"]:
            try:
                data = conn.recv(1024)
            except OSError:
                break

            if not data or data == b"#quit":
                conn.send(b"#quit")
                break

            try:
                msg = json.loads(data.decode())
                _handle_command(
                    msg.get("action"),
                    msg.get("header", ""),
                    msg.get("command"),
                )
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[AssetKiosk] Bad message: {e}")

        conn.close()
        BM_STATUS["connected"] = False
        print("[AssetKiosk] Client disconnected")

    try:
        srv.close()
    except OSError:
        pass
    print("[AssetKiosk] Server closed")


# ── Operators ──────────────────────────────────────────────────────────────────

class BM_OT_OpenKiosk(bpy.types.Operator):
    bl_idname = "bm.open_kiosk"
    bl_label = "Open Asset Kiosk"
    bl_description = "Launch the Asset Kiosk and start the connection server"

    def execute(self, context):
        exe = _kiosk_exe_path()
        if os.path.exists(exe):
            BM_STATUS["process"] = subprocess.Popen([exe])
        else:
            self.report({'WARNING'}, f"Asset Kiosk binary not found at: {exe}")

        BM_STATUS["socket"] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        BM_STATUS["socket"].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        BM_STATUS["active"] = True

        t = threading.Thread(target=_server_loop, daemon=True)
        BM_STATUS["thread"] = t
        t.start()

        return {'FINISHED'}


class BM_OT_CloseKiosk(bpy.types.Operator):
    bl_idname = "bm.close_kiosk"
    bl_label = "Close Asset Kiosk"
    bl_description = "Stop the Asset Kiosk connection server"

    def execute(self, context):
        BM_STATUS["active"] = False
        BM_STATUS["connected"] = False
        try:
            BM_STATUS["socket"].close()
        except OSError:
            pass
        if BM_STATUS["thread"] and BM_STATUS["thread"].is_alive():
            BM_STATUS["thread"].join(timeout=2.0)
        BM_STATUS["thread"] = None
        BM_STATUS["socket"] = None
        proc = BM_STATUS["process"]
        if proc and proc.poll() is None:
            proc.terminate()
        BM_STATUS["process"] = None
        return {'FINISHED'}


classes = [BM_OT_OpenKiosk, BM_OT_CloseKiosk]
