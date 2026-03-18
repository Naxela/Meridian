extends Node3D

var xr_interface: XRInterface

func _ready():
	xr_interface = XRServer.find_interface("OpenXR")
	if xr_interface and xr_interface.is_initialized():
		print("OpenXR initialized successfully")
		# OpenXR performs its own sync — v-sync must be off
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
		# Route the main viewport output to the HMD
		get_viewport().use_xr = true
	else:
		push_warning("OpenXR not initialized — check that your headset is connected and OpenXR runtime is running")
