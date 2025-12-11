import subprocess
import sys
from pathlib import Path
import textwrap

import bpy
from bpy.types import Operator

from ..preferences import get_addon_preferences
from ..utils.helpers import logical_width

_IS_WINDOWS = sys.platform == "win32"


class RECOM_OT_CheckBlenderVersion(Operator):
    """Display Blender version information in a popup window"""

    bl_idname = "recom.check_blender_version"
    bl_label = "Check Blender Version"
    bl_description = (
        "Show detailed Blender version information including build details and compilation flags"
    )

    output_text: bpy.props.StringProperty(
        name="Command Output",
        default="Running command...",
    )

    def execute(self, context):
        prefs = get_addon_preferences(context)
        blender_path = bpy.path.abspath(prefs.custom_executable_path)

        if not blender_path:
            self.report({"ERROR"}, "Custom Blender path is not set in preferences.")
            return {"CANCELLED"}

        if not Path(blender_path).exists():
            self.report({"ERROR"}, f"Blender executable not found at: {blender_path}")
            return {"CANCELLED"}

        try:
            result = subprocess.run(
                [blender_path, "--factory-startup", "--version"],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            self.output_text = result.stdout.strip()
            if not self.output_text:
                self.output_text = "Command ran successfully but produced no output."

        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip() if e.stderr else "No error output."
            self.output_text = (
                f"Error executing command:\n"
                f"Return Code: {e.returncode}\n\n"
                f"--- Error Output ---\n{error_message}"
            )
        except FileNotFoundError:
            self.output_text = f"Error: Executable file not found at '{blender_path}'"
        except Exception as e:
            self.report({"ERROR"}, f"An unexpected error occurred: {e}")
            self.output_text = f"An unexpected error occurred:\n{str(e)}"

        return context.window_manager.invoke_popup(self, width=700)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.active = False

        formatted_output = self.output_text.replace("\t", "    ")
        max_width = 110

        for line in formatted_output.splitlines():
            stripped_line = line.lstrip()
            indent = line[: len(line) - len(stripped_line)]

            if len(line) <= max_width:
                col.label(text=line)
            else:
                wrapper = textwrap.TextWrapper(
                    width=max_width,
                    initial_indent=indent,
                    subsequent_indent="",
                    break_long_words=False,
                )

                wrapped_text = wrapper.fill(text=stripped_line)

                for sub_line in wrapped_text.splitlines():
                    col.label(text=sub_line)


class RECOM_OT_LaunchCustomBlender(Operator):
    """Execute Blender using a user-defined binary path"""

    bl_idname = "recom.launch_custom_blender"
    bl_label = "Launch Blender"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        blender_path = bpy.path.abspath(prefs.custom_executable_path)

        if not Path(blender_path).exists():
            self.report({"ERROR"}, f"Blender executable not found at: {blender_path}")
            return {"CANCELLED"}

        try:
            if _IS_WINDOWS:
                subprocess.Popen([blender_path], shell=True)
            else:
                subprocess.Popen([blender_path])
            self.report({"INFO"}, "Launched custom Blender executable.")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to launch Blender: {str(e)}")
            return {"CANCELLED"}


classes = (
    RECOM_OT_CheckBlenderVersion,
    RECOM_OT_LaunchCustomBlender,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
