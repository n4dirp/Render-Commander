import subprocess
import json
import threading
import time
from pathlib import Path
import logging
import sys

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
    is_blender_blend_file,
    open_folder,
)

log = logging.getLogger(__name__)


_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


class RECOM_OT_ExtractExternalSceneData(Operator):
    """Read scene information from an external blend file using background process"""

    bl_idname = "recom.extract_external_scene_data"
    bl_label = "Read Scene"
    bl_description = "Read scene information from an external blend file"

    def _async_extract_scene_info(self, context, blend_path):
        def _get_scene_info_from_subprocess(blend_file_path_str):
            blend_file_path = Path(blend_file_path_str)
            if not blend_file_path.is_file():
                log.error(f"Blend file not found: {blend_file_path}")
                return {"error": f"Blend file not found: {blend_file_path}"}

            script_path = Path(__file__).parent / "../utils/extract_scene_info.py"
            script_path = script_path.resolve()
            # print(f"Extractor script path: {script_path}")

            if not script_path.is_file():
                log.error(f"Extractor script not found: {script_path}")
                return {"error": f"Extractor script not found: {script_path}"}

            blender_exe = bpy.app.binary_path
            cmd = [
                str(blender_exe),
                "-b",
                str(blend_file_path),
                "--python",
                str(script_path),
                "--factory-startup",
            ]

            log.debug(f"Executing command: {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    encoding="utf-8",
                    timeout=60,
                )

                if result.stderr:
                    log.debug(f"--- Subprocess STDERR ---\n{result.stderr.strip()}\n--- END STDERR ---")

                if result.returncode != 0:
                    error_message = f"Blender subprocess failed with return code {result.returncode}."
                    log.error(error_message)

                    try:
                        json_output = json.loads(result.stdout.strip().splitlines()[-1])
                        if "error" in json_output:
                            return {
                                "error": f"{error_message} Script error: {json_output['error']}",
                                "details": result.stderr.strip(),
                            }
                    except (json.JSONDecodeError, IndexError):
                        pass
                    return {
                        "error": error_message,
                        "stdout": result.stdout.strip(),
                        "stderr": result.stderr.strip(),
                    }

                output = result.stdout.strip()
                for line in reversed(output.splitlines()):
                    line = line.strip()
                    if not line:
                        continue
                    if not (line.startswith("{") or line.startswith("[")):
                        continue
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        log.warning(f"Failed to decode JSON line: {line}")
                        continue

                log.error("No valid JSON object found in subprocess output.")
                log.debug(f"--- Subprocess STDOUT (when no JSON found) ---\n{output}\n--- END STDOUT ---")
                return {
                    "error": "No valid JSON data returned from script.",
                    "stdout": output,
                }

            except subprocess.TimeoutExpired:
                log.error("Blender subprocess timed out.")
                return {"error": "Blender subprocess timed out."}
            except subprocess.CalledProcessError as e:
                log.exception(f"Error executing Blender subprocess (CalledProcessError):")
                return {"error": str(e), "stdout": e.stdout, "stderr": e.stderr}
            except Exception as exc:
                log.exception(f"An unexpected error occurred during subprocess handling: {str(exc)}")
                import traceback

                traceback.print_exc()
                return {"error": f"Unexpected subprocess error: {str(exc)}"}

        def _callback_fn(context_ref, info_data, duration_secs):
            settings = context_ref.window_manager.recom_render_settings
            if info_data:
                settings.external_scene_info = json.dumps(info_data)

                if "error" in info_data:
                    settings.is_scene_info_loaded = True
                    error_message = info_data.get("error", "Unknown error from external script.")
                    log.error(f"Error extracting scene info: {error_message}")
                else:
                    settings.is_scene_info_loaded = True
                    redraw_ui()
                    log.debug("Scene Info successfully extracted.")
                    # print("Full Scene Info:", info_data)  # Uncomment for verbose success
                log.debug(f"Extraction process finished in {duration_secs:.2f} seconds")
            else:
                settings.external_scene_info = json.dumps({"error": "No data returned from extraction process."})
                settings.is_scene_info_loaded = True
                log.warning("Failed to extract scene info (subprocess returned no valid data or null).")

        def _task():
            settings = context.window_manager.recom_render_settings
            settings.is_scene_info_loaded = False

            start_time = time.time()
            extracted_info = _get_scene_info_from_subprocess(blend_path)
            duration = time.time() - start_time

            def update_ui():
                _callback_fn(context, extracted_info, duration)
                return None

            bpy.app.timers.register(update_ui)

        # Start the background _task in a new thread
        thread = threading.Thread(target=_task)
        thread.daemon = True
        thread.start()

    def execute(self, context):
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings
        external_blend_path = bpy.path.abspath(settings.external_blend_file_path)

        if not external_blend_path:
            self.report({"ERROR"}, "External blend file path not set.")
            return {"CANCELLED"}

        if not Path(external_blend_path).exists():
            self.report({"ERROR"}, f"External blend file not found: {external_blend_path}")
            return {"CANCELLED"}

        # Check if the path is actually a .blend file (basic check)
        if not is_blender_blend_file(external_blend_path):
            self.report({"ERROR"}, f"Specified path is not a .blend file: {external_blend_path}")
            return {"CANCELLED"}

        # context.window_manager.recom_error_message = ""

        # Add to recent files if not already present
        prefs.add_recent_blend_file(external_blend_path)
        context.preferences.is_dirty = True

        log.debug(f"Attempting to extract scene info from: {external_blend_path}")
        self.report(
            {"INFO"},
            "Started extracting scene info in background.",
        )
        self._async_extract_scene_info(context, external_blend_path)

        return {"FINISHED"}


class RECOM_OT_OpenExternalSceneInfo(Operator):
    """Open externally extracted scene information in Text Editor"""

    bl_idname = "recom.open_external_scene_info"
    bl_label = "Open Imported Scene Data (Read Only)"
    bl_description = "Open the external scene info in the Text Editor (Read Only)"

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        scene_info_str = settings.external_scene_info

        if not scene_info_str:
            self.report({"ERROR"}, "No scene info to open.")
            return {"CANCELLED"}

        try:
            # Parse the JSON string into a Python dict
            scene_info = json.loads(scene_info_str)

            # Pretty-print the JSON with indentation
            formatted_json = json.dumps(scene_info, indent=4)

            # Create or update the text block
            text_name = "External_Scene_Info"
            try:
                text_block = bpy.data.texts[text_name]
                text_block.clear()
                text_block.write(formatted_json)

                # Switch to the text editor and set the active text
                for area in context.window.screen.areas:
                    if area.type == "TEXT_EDITOR":
                        area.spaces[0].text = text_block
                        break

            except KeyError:
                text_block = bpy.data.texts.new(name=text_name)
                text_block.write(formatted_json)

            self.report(
                {"INFO"},
                f"Scene info saved to text block '{text_name}'.",
            )
            return {"FINISHED"}

        except json.JSONDecodeError as e:
            self.report({"ERROR"}, f"Invalid JSON data: {e}")
            return {"CANCELLED"}
        except Exception as e:
            self.report({"ERROR"}, f"Error formatting scene info: {e}")
            return {"CANCELLED"}


class RECOM_OT_SelectRecentFile(Operator):
    bl_idname = "recom.select_recent_file"
    bl_label = "Select Recent File"
    bl_description = "Read Scene"

    file_path: StringProperty(name="File Path")

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
                    break

            self.report({"WARNING"}, f"File not found: {external_blend_path}. Removed from recent files.")
            return {"CANCELLED"}

        # Set the file path and proceed with extraction
        settings.external_blend_file_path = external_blend_path
        bpy.ops.recom.extract_external_scene_data()
        settings.use_external_blend = True
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
        if self.remove_type == "ALL":
            prefs.recent_blend_files.clear()
            context.preferences.is_dirty = True
            log.info("Cleared all recent blend files.")
            return {"FINISHED"}
        elif self.remove_type == "NOT_FOUND":
            # Remove only those paths that do not exist on disk
            for i in reversed(range(len(prefs.recent_blend_files))):
                path = prefs.recent_blend_files[i].path
                if not Path(path).exists():
                    prefs.recent_blend_files.remove(i)
                    log.info(f"Removed missing file: {path}")
            context.preferences.is_dirty = True
            return {"FINISHED"}
        else:
            return {"CANCELLED"}


class RECOM_OT_OpenBlendFile(Operator):
    """Open a .blend file in Blender"""

    bl_idname = "recom.open_blend_file"
    bl_label = "Open Blend File in Blender"

    file_path: StringProperty()

    def execute(self, context):
        bpy.ops.wm.open_mainfile(filepath=self.file_path)
        return {"FINISHED"}


class RECOM_OT_OpenInNewBlender(Operator):
    """Open a .blend file in a new Blender instance"""

    bl_idname = "recom.open_in_new_blender"
    bl_label = "Open in New Blender Instance"

    file_path: StringProperty(name="File Path", description="Path to the .blend file to open", default="")

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        file_path = self.file_path

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            self.report({"ERROR"}, f"File not found: {file_path}")
            return {"CANCELLED"}

        # Get Blender executable path
        blender_path = bpy.app.binary_path

        try:
            if _IS_WINDOWS:
                # On Windows, use start command to open a new instance
                subprocess.Popen([blender_path, file_path])
            elif _IS_MACOS:
                # macOS: Use 'open' with the -a flag to specify the app
                subprocess.Popen(["open", "-a", "Blender", file_path])
            else:
                # Linux and others: Launch using the same Blender binary
                subprocess.Popen([blender_path, file_path])
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to open new Blender instance: {e}")
            return {"CANCELLED"}


class RECOM_OT_OpenBlendDirectory(Operator):
    """Open the directory containing the external blend file"""

    bl_idname = "recom.open_blend_directory"
    bl_label = "Open Blend File Directory"

    file_path: StringProperty()

    def execute(self, context):
        path = Path(self.file_path)
        dir_path = path.parent

        if not dir_path.exists():
            self.report({"ERROR"}, f"Directory not found: {dir_path}")
            return {"CANCELLED"}

        open_folder(str(dir_path))

        return {"FINISHED"}


class RECOM_OT_SelectExternalBlendFile(Operator):
    """Choose an external .blend file to render"""

    bl_idname = "recom.select_external_blend_file"
    bl_label = "Select External Blend File"

    # The property that will receive the path from the file selector
    filepath: StringProperty(subtype="FILE_PATH", options={"HIDDEN"})
    filter_glob: StringProperty(
        default="*.blend;*.blend1;*.blend2;*.blend3",
        options={"HIDDEN"},
    )

    def execute(self, context):
        """Called after the user picks a file."""
        settings = context.window_manager.recom_render_settings
        abs_path = bpy.path.abspath(self.filepath)
        settings.external_blend_file_path = abs_path

        log.info(f"External blend set to: {abs_path}")

        if abs_path:
            bpy.ops.recom.extract_external_scene_data()

        return {"FINISHED"}

    def invoke(self, context, event):
        """Open the file browser when the operator is invoked"""
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


classes = (
    RECOM_OT_ExtractExternalSceneData,
    RECOM_OT_SelectExternalBlendFile,
    RECOM_OT_OpenExternalSceneInfo,
    RECOM_OT_SelectRecentFile,
    RECOM_OT_ClearRecentFiles,
    RECOM_OT_OpenBlendFile,
    RECOM_OT_OpenInNewBlender,
    RECOM_OT_OpenBlendDirectory,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
