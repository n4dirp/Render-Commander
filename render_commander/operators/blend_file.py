"""
Handles the logic for interacting with external .blend files. 
It manages background extraction of scene information using a separate 
Blender instance, implements a caching system to store extracted JSON data.
"""

import subprocess
import json
import time
import logging
import sys
import os
import hashlib
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ..utils.constants import EXTERNAL_BLEND_FILE_HISTORY_LIMIT
from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
    is_blend_or_backup_file,
    open_folder,
    get_addon_temp_dir,
)


log = logging.getLogger(__name__)


_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"


# Module-level state to track active extraction safely across operator calls
_extraction_state = {
    "process": None,
    "timer_handle": None,
    "cache_path": None,
    "start_time": 0.0,
    "is_running": False,
}


def _poll_extraction_timer():
    """Standalone timer callback. Never references 'self'."""
    # Safety Check: If Blender is shutting down or process is gone, exit immediately.
    if not _extraction_state["is_running"] or _extraction_state["process"] is None:
        return None

    try:
        # poll() returns None if still running, exit code if finished
        if _extraction_state["process"].poll() is None:
            return 0.5  # Keep polling

        _finalize_extraction()
        return None  # Stop timer
    except Exception as e:
        log.error("Error in extraction timer: %s", e)
        return None


def _finalize_extraction():
    """Reads cache and updates UI. Runs safely outside operator lifecycle."""
    cache_path = _extraction_state["cache_path"]
    info_data = {}

    if cache_path and Path(cache_path).exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                info_data = json.load(f)
        except Exception as e:
            log.error("Failed to read cache file: %s", e)
            info_data = {"error": f"Failed to read cache: {str(e)}"}
    else:
        info_data = {"error": "Extraction finished but cache file is missing."}

    wm = bpy.data.window_managers[0] if bpy.data.window_managers else None
    if wm and hasattr(wm, "recom_render_settings"):
        settings = wm.recom_render_settings
        settings.external_scene_info = json.dumps(info_data)
        settings.is_scene_info_loaded = True

        if "error" in info_data:
            log.error("Extraction error: %s", info_data["error"])
        else:
            log.info("Scene info successfully extracted and cached.")
            redraw_ui()

    duration = time.time() - _extraction_state["start_time"]
    log.debug("Extraction process finished in %.2f seconds", duration)

    # Reset state
    _extraction_state["process"] = None
    _extraction_state["timer_handle"] = None
    _extraction_state["is_running"] = False


def add_recent_blend_file(prefs, new_path):
    for i in reversed(range(len(prefs.recent_blend_files))):
        if prefs.recent_blend_files[i].path == new_path:
            prefs.recent_blend_files.remove(i)

    new_entry = prefs.recent_blend_files.add()
    new_entry.path = new_path

    while len(prefs.recent_blend_files) > EXTERNAL_BLEND_FILE_HISTORY_LIMIT:
        prefs.recent_blend_files.remove(0)


def generate_cache_key(blend_path_obj: Path, script_path: Path) -> str:
    """Generate a cache key based on blend hash and script modification time."""
    try:
        script_mtime = int(script_path.stat().st_mtime)
        path_str = str(blend_path_obj.resolve()).encode('utf-8')
        blend_hash = hashlib.md5(path_str).hexdigest()
    except OSError as e:
        log.warning("Cannot stat cache key file: %s", e)
        safe_path = bpy.path.clean_name(str(blend_path_obj.resolve()))[:100]  # Limit length
        return safe_path  # Fall back to path only

    return f"{blend_hash}_{script_mtime}"


class RECOM_OT_ExtractExternalSceneData(Operator):
    """Read scene information from an external blend file using a background process"""

    bl_idname = "recom.extract_external_scene_data"
    bl_label = "Read Blend File"
    bl_description = "Read scene information from an external blend file"

    @classmethod
    def description(cls, context, properties):
        if _extraction_state["is_running"]:
            return "Scene data extraction in progress"
        pass

    def execute(self, context):
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings
        external_blend_path = bpy.path.abspath(settings.external_blend_file_path)

        if not external_blend_path:
            self.report({"ERROR"}, "External blend file path not set")
            return {"CANCELLED"}

        blend_path_obj = Path(external_blend_path)
        if not blend_path_obj.exists():
            self.report({"ERROR"}, f"External blend file not found: {external_blend_path}")
            return {"CANCELLED"}

        if not is_blend_or_backup_file(external_blend_path):
            self.report({"ERROR"}, "Specified path is not a .blend file")
            return {"CANCELLED"}

        if _extraction_state["is_running"]:
            self.report({"WARNING"}, "Extraction already in progress. Please wait or cancel")
            return {"CANCELLED"}

        # Add to recent files
        add_recent_blend_file(prefs, external_blend_path)
        context.preferences.is_dirty = True

        # Prepare paths
        script_path = (Path(__file__).parent / "../utils/extract_scene_info.py").resolve()
        if not script_path.is_file():
            self.report({"ERROR"}, f"Extractor script not found: {script_path}")
            return {"CANCELLED"}

        temp_dir = get_addon_temp_dir()
        cache_dir = temp_dir / "blend_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_key = generate_cache_key(blend_path_obj, script_path)
        cache_path = cache_dir / f"{cache_key}.json"

        # Check for existing valid & up-to-date cache
        if cache_path.exists():
            try:
                blend_mtime = blend_path_obj.stat().st_mtime
                cache_mtime = cache_path.stat().st_mtime

                # Only use cache if blend file hasn't been modified since caching
                if blend_mtime <= cache_mtime:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)

                    # Ensure cache doesn't contain a previous extraction error
                    if "error" not in cached_data:
                        settings.external_scene_info = json.dumps(cached_data)
                        settings.is_scene_info_loaded = True
                        log.info('Loaded scene info from cache: "%s"', cache_path.name)
                        redraw_ui()
                        self.report({"INFO"}, f"Loaded cached scene info for {blend_path_obj.name}")
                        return {"FINISHED"}

                    log.debug("Cache contains previous error, will re-extract.")
                else:
                    log.debug("Blend file modified after cache, will re-extract.")
            except (json.JSONDecodeError, Exception) as e:
                log.debug("Cache invalid or unreadable, will re‑extract: %s", e)

        # Proceed with background extraction if cache is missing/stale/invalid
        settings.is_scene_info_loaded = False
        settings.external_scene_info = json.dumps({"info": "Extracting scene data... Please wait."})

        _extraction_state["cache_path"] = cache_path
        _extraction_state["start_time"] = time.time()
        _extraction_state["is_running"] = True

        env = os.environ.copy()
        env["BLEND_EXTRACT_CACHE_PATH"] = str(cache_path)

        kwargs = {}
        if _IS_WINDOWS:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        cmd = [
            bpy.app.binary_path,
            "-b",
            external_blend_path,
            "--python",
            str(script_path),
            "--factory-startup",
        ]

        log.info('Launching background extraction: "%s"', " ".join(cmd))
        _extraction_state["process"] = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            **kwargs,
        )

        _extraction_state["timer_handle"] = bpy.app.timers.register(_poll_extraction_timer, first_interval=0.5)

        self.report({"INFO"}, "Reading scene in background")
        return {"FINISHED"}


class RECOM_OT_CancelExtraction(Operator):
    """Cancel the ongoing external scene extraction"""

    bl_idname = "recom.cancel_extraction"
    bl_label = "Cancel Extraction"
    bl_description = "Stop the current background extraction process"

    def execute(self, context):
        if not _extraction_state["is_running"]:
            self.report({"WARNING"}, "No active extraction to cancel")
            return {"CANCELLED"}

        # Kill subprocess if still running
        if _extraction_state["process"] and _extraction_state["process"].poll() is None:
            try:
                _extraction_state["process"].kill()
                _extraction_state["process"].wait(timeout=2)
            except Exception as e:
                log.warning("Failed to cleanly kill extraction process: %s", e)

        # Unregister timer
        if _extraction_state["timer_handle"]:
            try:
                bpy.app.timers.unregister(_extraction_state["timer_handle"])
            except ValueError:
                pass

        # Update UI state
        settings = context.window_manager.recom_render_settings
        settings.external_scene_info = json.dumps({"error": "Extraction cancelled by user."})
        settings.is_scene_info_loaded = True
        try:
            redraw_ui()
        except Exception:
            pass

        # Reset state
        _extraction_state["process"] = None
        _extraction_state["timer_handle"] = None
        _extraction_state["is_running"] = False

        self.report({"INFO"}, "Extraction cancelled")
        return {"FINISHED"}


class RECOM_OT_ClearAndReloadSceneInfo(Operator):
    """Clear the scene info cache and reload from external blend file"""

    bl_idname = "recom.clear_and_reload_scene_info"
    bl_label = "Clear Cache & Reload Scene Info"
    bl_description = "Clear the scene info cache and reload from external blend file"

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        external_blend_path = bpy.path.abspath(settings.external_blend_file_path)

        if not external_blend_path:
            self.report({"ERROR"}, "External blend file path not set")
            return {"CANCELLED"}

        # Calculate cache path based on the external blend file
        temp_dir = get_addon_temp_dir()
        cache_dir = temp_dir / "blend_cache"
        script_path = (Path(__file__).parent / "../utils/extract_scene_info.py").resolve()

        cache_key = generate_cache_key(Path(external_blend_path), script_path)
        cache_path = cache_dir / f"{cache_key}.json"

        # Delete the cache file if it exists
        if cache_path.exists():
            try:
                cache_path.unlink(missing_ok=True)

                self.report({"INFO"}, "Cleared scene info cache")
                log.info('Cleared scene info cache: "%s"', str(cache_path))

            except Exception as e:
                self.report({"ERROR"}, f"Failed to clear cache")
                log.error('Failed to clear cache: "%s"', e)

                return {"CANCELLED"}

        # Trigger extraction
        bpy.ops.recom.extract_external_scene_data()
        return {"FINISHED"}


class RECOM_OT_SelectRecentFile(Operator):
    bl_idname = "recom.select_recent_file"
    bl_label = "Select Recent File"
    bl_description = "Read Blend File"

    file_path: StringProperty(name="Blend File Path", subtype="FILE_PATH")

    def execute(self, context):
        external_blend_path = self.file_path
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings

        # Check if the file exists
        if not Path(external_blend_path).exists():
            # Remove the file from recent_blend_files
            for i in reversed(range(len(prefs.recent_blend_files))):
                if prefs.recent_blend_files[i].path == external_blend_path:
                    prefs.recent_blend_files.remove(i)
                    context.preferences.is_dirty = True
                    break

            self.report({"WARNING"}, f"File not found: {external_blend_path}. Removed from recent files.")
            return {"CANCELLED"}

        # Set the file path and proceed with extraction
        settings.external_blend_file_path = external_blend_path
        bpy.ops.recom.extract_external_scene_data()
        settings.use_external_blend = True
        self.report({"INFO"}, f"Read: {Path(external_blend_path).name}")
        return {"FINISHED"}


class RECOM_OT_ClearRecentFiles(Operator):
    """Open a popup to delete recent blend files."""

    bl_idname = "recom.clear_recent_files"
    bl_label = "Clear Recent Files List"

    remove_type: EnumProperty(
        name="Remove",
        description="Select items to remove",
        items=[("ALL", "All Items", ""), ("NOT_FOUND", "Items not Found", "")],
        default="ALL",
    )

    def invoke(self, context, event):
        """Show the dialog with the enum property."""
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = get_addon_preferences(context)
        removed_count = 0

        if self.remove_type == "ALL":
            removed_count = len(prefs.recent_blend_files)
            prefs.recent_blend_files.clear()

            context.preferences.is_dirty = True
            log.info("Cleared all recent blend files.")

        elif self.remove_type == "NOT_FOUND":
            for i in reversed(range(len(prefs.recent_blend_files))):
                path = prefs.recent_blend_files[i].path
                if not Path(path).exists():
                    prefs.recent_blend_files.remove(i)
                    removed_count += 1
                    log.info("Removed missing file: %s", path)

            context.preferences.is_dirty = True
        else:
            return {"CANCELLED"}

        label = "item" if removed_count == 1 else "items"
        self.report({"INFO"}, f"Removed {removed_count} {label}")
        return {"FINISHED"}


class RECOM_OT_OpenBlendFile(Operator):
    """Open a .blend file in Blender"""

    bl_idname = "recom.open_blend_file"
    bl_label = "Open Blend File in Blender"

    file_path: StringProperty(name="Blend File Path", subtype="FILE_PATH")

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=self.file_path)
        return {"FINISHED"}


class RECOM_OT_OpenInNewBlender(Operator):
    """Open a .blend file in a new Blender instance"""

    bl_idname = "recom.open_in_new_blender"
    bl_label = "Open in New Blender Instance"

    file_path: StringProperty(name="File Path", subtype="FILE_PATH")

    def execute(self, context):
        file_path = self.file_path
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            self.report({"ERROR"}, f"File not found: {file_path}")
            return {"CANCELLED"}

        blender_path = bpy.app.binary_path

        try:
            if _IS_WINDOWS:
                subprocess.Popen([blender_path, file_path])
            elif _IS_MACOS:
                subprocess.Popen(["open", "-a", "Blender", file_path])
            else:
                subprocess.Popen([blender_path, file_path])
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to open new Blender instance: {e}")
            return {"CANCELLED"}


class RECOM_OT_OpenBlendDirectory(Operator):
    """Open the directory containing the external blend file"""

    bl_idname = "recom.open_blend_directory"
    bl_label = "Open Blend File Directory"

    file_path: StringProperty(name="File Path", subtype="FILE_PATH")

    def execute(self, context):
        path = Path(self.file_path)
        dir_path = path.parent

        if not dir_path.exists():
            self.report({"ERROR"}, f"Directory not found: {dir_path}")
            return {"CANCELLED"}

        open_folder(str(dir_path))

        return {"FINISHED"}


class RECOM_OT_OpenBlendOutputPath(Operator):
    """Open the resolved output path directory"""

    bl_idname = "recom.open_blend_output_path"
    bl_label = "Open File Output Path"
    bl_description = "Open the folder"

    file_path: StringProperty(name="File Path", subtype="FILE_PATH")

    def execute(self, context):
        frame_path_str = self.file_path  # Absolute Path

        if not frame_path_str:
            self.report({"ERROR"}, "No output path available")
            return {"CANCELLED"}

        try:
            normalized_path = frame_path_str.replace("\\", "/")
            dir_path_obj = Path(normalized_path).parent.resolve()
            folder_path_str = f"{dir_path_obj.as_posix().rstrip('/')}/"

            log.debug("Opening output folder: %s (from frame_path: %s)", folder_path_str, frame_path_str)

            success = open_folder(folder_path_str)

            if not success:
                self.report({"ERROR"}, "Failed to open or create output folder")
                return {"CANCELLED"}

            return {"FINISHED"}

        except Exception as e:
            self.report({"ERROR"}, f"Failed to open output path: {str(e)}")
            log.error("Error opening blend output path: %s", e, exc_info=True)
            return {"CANCELLED"}


class RECOM_OT_SelectExternalBlendFile(Operator):
    """Choose an external .blend file to render"""

    bl_idname = "recom.select_external_blend_file"
    bl_label = "Select External Blend File"

    filepath: StringProperty(
        subtype="FILE_PATH",
        options={"HIDDEN"},
    )
    filter_glob: StringProperty(
        default="*.blend;*.blend1;*.blend2;*.blend3",
        options={"HIDDEN"},
    )

    read_scene: BoolProperty(
        name="Read Scene",
        description="Automatically read the scene information",
        default=True,
    )

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        abs_path = bpy.path.abspath(self.filepath)
        settings.external_blend_file_path = abs_path

        log.info("External blend set to: %s", abs_path)

        if self.read_scene and abs_path:
            self.report({"INFO"}, "Reading scene in background")
            bpy.ops.recom.extract_external_scene_data()

        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


classes = (
    RECOM_OT_ExtractExternalSceneData,
    RECOM_OT_CancelExtraction,
    RECOM_OT_ClearAndReloadSceneInfo,
    RECOM_OT_SelectExternalBlendFile,
    RECOM_OT_SelectRecentFile,
    RECOM_OT_ClearRecentFiles,
    RECOM_OT_OpenBlendFile,
    RECOM_OT_OpenBlendOutputPath,
    RECOM_OT_OpenInNewBlender,
    RECOM_OT_OpenBlendDirectory,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    # Cleanup if addon is disabled during extraction
    if _extraction_state["timer_handle"] is not None:
        try:
            bpy.app.timers.unregister(_extraction_state["timer_handle"])
        except Exception as e:
            log.error("Failed to unregister timer during shutdown: %s", e)

    # Kill the background process if it's still running
    if _extraction_state["process"] is not None:
        try:
            if _extraction_state["process"].poll() is None:  # If still running
                _extraction_state["process"].kill()
                _extraction_state["process"].wait(timeout=1)
        except Exception as e:
            log.error("Failed to kill background process during shutdown: %s", e)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    _extraction_state["is_running"] = False
    _extraction_state["process"] = None
    _extraction_state["timer_handle"] = None
