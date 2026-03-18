import bpy, os, subprocess
from .mx import MX_OperatorBase


class MX_OT_Publish(bpy.types.Operator, MX_OperatorBase):
    bl_idname = "mx.publish"
    bl_label = "Publish"
    bl_description = "Package the Godot project for the selected target using headless export"

    _PLATFORM_MAP = {
        'WINDOWS': ("Windows Desktop", ".exe",  "windows_release_x86_64.exe"),
        'WEB':     ("Web",             ".html", "web_release.zip"),
        'ANDROID': ("Android",         ".apk",  "android_release.apk"),
    }

    needs_template_download: bpy.props.BoolProperty(default=False, options={'HIDDEN', 'SKIP_SAVE'})

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _godot_version(self):
        """Return (dir_version, url_version) e.g. ('4.6.stable', '4.6-stable')."""
        result = subprocess.run(
            [self.godot_path, "--version"],
            capture_output=True, text=True
        )
        raw = result.stdout.strip()
        parts = raw.split(".")
        if len(parts) < 3:
            return None, None
        dir_ver = ".".join(parts[:3])
        url_ver = parts[0] + "." + parts[1] + "-" + parts[2]
        return dir_ver, url_ver

    def _templates_dir(self):
        """Return the OS-appropriate Godot export templates root directory."""
        import platform
        system = platform.system()
        if system == "Windows":
            return os.path.join(os.environ.get("APPDATA", ""), "Godot", "export_templates")
        elif system == "Darwin":
            return os.path.expanduser("~/Library/Application Support/Godot/export_templates")
        else:
            return os.path.expanduser("~/.local/share/godot/export_templates")

    def _templates_present(self, dir_version, template_file):
        path = os.path.join(self._templates_dir(), dir_version, template_file)
        return os.path.exists(path)

    def _download_templates(self, dir_version, url_version):
        """Download and extract export templates from GitHub releases."""
        import urllib.request
        import zipfile
        import tempfile

        filename  = f"Godot_v{url_version}_export_templates.tpz"
        url       = f"https://github.com/godotengine/godot/releases/download/{url_version}/{filename}"
        dest_dir  = os.path.join(self._templates_dir(), dir_version)
        os.makedirs(dest_dir, exist_ok=True)

        print(f"[Publish] Downloading export templates from:\n  {url}")
        print("[Publish] This may take a few minutes (~600 MB)...")

        downloaded = [0]
        def _progress(block_num, block_size, total_size):
            downloaded[0] = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded[0] * 100 // total_size)
                if pct % 10 == 0:
                    print(f"[Publish] Download: {pct}%  ({downloaded[0] // 1_048_576} MB)")

        with tempfile.TemporaryDirectory() as tmp:
            tpz_path = os.path.join(tmp, filename)
            urllib.request.urlretrieve(url, tpz_path, reporthook=_progress)
            print("[Publish] Download complete. Extracting...")

            with zipfile.ZipFile(tpz_path, 'r') as zf:
                members = zf.namelist()
                prefix = members[0].split('/')[0] + '/'
                for member in members:
                    if member == prefix:
                        continue
                    rel = member[len(prefix):]
                    if not rel:
                        continue
                    out_path = os.path.join(dest_dir, rel)
                    if member.endswith('/'):
                        os.makedirs(out_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(out_path), exist_ok=True)
                        with zf.open(member) as src, open(out_path, 'wb') as dst:
                            dst.write(src.read())

        print(f"[Publish] Templates installed to: {dest_dir}")

    def _output_file(self, props, ext):
        base = props.mx_publish_output_path.strip()
        project_name = (props.mx_project_name or "game").replace(" ", "_")
        if not base:
            base = os.path.join(
                props.mx_godot_project_path, "build",
                props.mx_publish_target.lower()
            )
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, project_name + ext)

    def _write_export_presets(self, project_dir, preset_name, output_file):
        godot_output = output_file.replace("\\", "/")
        content = (
            f'[preset.0]\n\n'
            f'name="{preset_name}"\n'
            f'platform="{preset_name}"\n'
            f'runnable=true\n'
            f'dedicated_server=false\n'
            f'custom_features=""\n'
            f'export_filter="all_resources"\n'
            f'include_filter=""\n'
            f'exclude_filter=""\n'
            f'export_path="{godot_output}"\n'
            f'encryption_include_filters=""\n'
            f'encryption_exclude_filters=""\n'
            f'encrypt_pck=false\n'
            f'encrypt_directory=false\n\n'
            f'[preset.0.options]\n\n'
            f'binary_format/embed_pck=true\n'
        )
        presets_path = os.path.join(project_dir, "export_presets.cfg")
        with open(presets_path, 'w') as f:
            f.write(content)
        return presets_path

    # ── Main ──────────────────────────────────────────────────────────────────

    def invoke(self, context, event):
        props = context.scene.MX_SceneProperties
        project_dir = props.mx_godot_project_path

        if not project_dir or not os.path.exists(os.path.join(project_dir, "project.godot")):
            self.report({'ERROR'}, "No Godot project found. Run Initialize Project first.")
            return {'CANCELLED'}

        if not os.path.exists(self.godot_path):
            self.report({'ERROR'}, f"Godot executable not found: {self.godot_path}")
            return {'CANCELLED'}

        _, __, template_file = self._PLATFORM_MAP.get(
            props.mx_publish_target, ("Windows Desktop", ".exe", "windows_release_x86_64.exe")
        )
        dir_version, _ = self._godot_version()
        if not dir_version:
            self.report({'ERROR'}, "Could not detect Godot version from executable.")
            return {'CANCELLED'}

        if not self._templates_present(dir_version, template_file):
            self.needs_template_download = True
            return context.window_manager.invoke_props_dialog(self, width=440)

        self.needs_template_download = False
        return self.execute(context)

    def draw(self, context):
        """Shown only when export templates need to be downloaded."""
        _, __, template_file = self._PLATFORM_MAP.get(
            context.scene.MX_SceneProperties.mx_publish_target,
            ("Windows Desktop", ".exe", "windows_release_x86_64.exe")
        )
        dir_version, _ = self._godot_version()

        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Export templates not found.", icon='ERROR')
        col.label(text=f"Godot version: {dir_version or 'unknown'}")
        col.separator()
        col.label(text="Download ~600 MB from github.com/godotengine/godot?")
        col.label(text="Blender will be unresponsive during the download.", icon='INFO')

    def execute(self, context):
        props = context.scene.MX_SceneProperties
        project_dir = props.mx_godot_project_path

        if not project_dir or not os.path.exists(os.path.join(project_dir, "project.godot")):
            self.report({'ERROR'}, "No Godot project found. Run Initialize Project first.")
            return {'CANCELLED'}

        if not os.path.exists(self.godot_path):
            self.report({'ERROR'}, f"Godot executable not found: {self.godot_path}")
            return {'CANCELLED'}

        preset_name, ext, template_file = self._PLATFORM_MAP.get(
            props.mx_publish_target, ("Windows Desktop", ".exe", "windows_release_x86_64.exe")
        )
        output_file = self._output_file(props, ext)

        wm = context.window_manager
        wm.progress_begin(0, 100)

        try:
            wm.progress_update(5)
            dir_version, url_version = self._godot_version()
            if not dir_version:
                self.report({'ERROR'}, "Could not detect Godot version from executable.")
                return {'CANCELLED'}
            print(f"[Publish] Godot version: {dir_version}")

            wm.progress_update(10)
            if self.needs_template_download:
                self.report({'INFO'}, "Downloading export templates (~600 MB) — check console for progress.")
                try:
                    self._download_templates(dir_version, url_version)
                except Exception as e:
                    self.report({'ERROR'}, f"Failed to download export templates: {e}")
                    return {'CANCELLED'}

                if not self._templates_present(dir_version, template_file):
                    self.report({'ERROR'}, "Templates downloaded but target file still missing. Check console.")
                    return {'CANCELLED'}

            wm.progress_update(20)
            self._write_export_presets(project_dir, preset_name, output_file)
            print(f"[Publish] Preset written for '{preset_name}' → {output_file}")

            wm.progress_update(35)
            print("[Publish] Running headless import...")
            subprocess.run(
                [self.godot_path, "--headless", "--path", project_dir, "--import"],
                capture_output=True, text=True
            )

            wm.progress_update(60)
            print(f"[Publish] Exporting '{preset_name}'...")
            result = subprocess.run(
                [self.godot_path, "--headless", "--path", project_dir,
                 "--export-release", preset_name, output_file],
                capture_output=True, text=True
            )

            wm.progress_update(95)

            if result.returncode != 0:
                print(f"[Publish] stderr:\n{result.stderr}")
                self.report({'ERROR'}, f"Godot export failed (exit {result.returncode}). Check console.")
                return {'CANCELLED'}

            if not os.path.exists(output_file):
                self.report({'ERROR'}, "Export finished but output file not found. Check console.")
                return {'CANCELLED'}

            wm.progress_update(100)
            self.report({'INFO'}, f"Published → {output_file}")
            print(f"[Publish] Done: {output_file}")

        finally:
            wm.progress_end()

        return {'FINISHED'}
