# ./operators/operators.py

import logging
import subprocess
import sys
import textwrap
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, EnumProperty, BoolProperty

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import (
    get_addon_temp_dir,
    open_folder,
    redraw_ui,
)


log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"


class RECOM_OT_LoadingButton(Operator):
    bl_idname = "recom.loading_button"
    bl_label = ""
    bl_description = ""

    def execute(self, context):
        return {"FINISHED"}


class RECOM_OT_ContinueSetup(Operator):
    bl_idname = "recom.continue_setup"
    bl_label = "Continue"
    bl_description = "Proceed to the main interface after completing Cycles device configuration."

    def execute(self, context):
        prefs = get_addon_preferences(context)
        prefs.cycles_setup_complete = True
        return {"FINISHED"}


class RECOM_OT_ReinitializeDevices(Operator):
    bl_idname = "recom.reinitialize_devices"
    bl_label = "Refresh Device List"
    bl_description = "Reinitialize all Cycles render devices"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        prefs.rescan_all_devices()
        redraw_ui()

        self.report({"INFO"}, "Device list refreshed successfully")
        return {"FINISHED"}


class RECOM_OT_OpenPreferences(Operator):
    bl_idname = "recom.open_pref"
    bl_label = "Open Preferences"
    bl_description = "Open the add-on preferences panel"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        bpy.ops.screen.userpref_show()
        bpy.context.preferences.active_section = "ADDONS"

        wm = context.window_manager
        wm.addon_search = "Render Commander"

        try:
            bpy.ops.preferences.addon_expand(module="render_commander")
        except RuntimeError as e:
            self.report({"WARNING"}, f"Could not expand addon: {e}")

        return {"FINISHED"}


class RECOM_OT_ChangeScriptsDirectory(Operator):
    bl_idname = "recom.change_scripts_directory"
    bl_label = "Select Scripts Directory"
    bl_description = "Change the directory for additional Python scripts"

    directory: StringProperty(
        name="Export Directory",
        description="Directory to read python files",
        subtype="DIR_PATH",
    )

    filter_folder: BoolProperty(
        default=True,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def execute(self, context):
        prefs = get_addon_preferences(context)
        # The actual path will be handled in invoke
        prefs.scripts_directory = self.directory
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class RECOM_OT_DeviceID(Operator):
    bl_idname = "recom.cycles_device_ids"
    bl_label = "Show Device IDs"
    bl_description = "Displays the unique identifier of the compute devices"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        blender_path = bpy.path.abspath(prefs.custom_executable_path)

        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        layout.label(text="Device IDs")

        label_col = layout.box().column(align=True)

        prev_type = None
        for device in prefs.get_devices_for_display():
            if prev_type is not None and device.type != prev_type:
                label_col.separator(type="AUTO")

            row = label_col.row(align=True)
            # row.active = False
            icon = "CHECKBOX_HLT" if device.use else "CHECKBOX_DEHLT"
            row.label(text=device.id, icon=icon)

            prev_type = device.type


class RECOM_OT_CleanTempFiles(Operator):
    """Delete residual temporary files."""

    bl_idname = "recom.clean_temp_files"
    bl_label = "Clean Temp Files"
    bl_description = "Delete residual execution scripts and logs"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        prefs = get_addon_preferences(context)
        try:
            temp_dir = get_addon_temp_dir(prefs)
        except:
            return {"CANCELLED"}

        if not temp_dir.exists():
            return {"FINISHED"}

        targets = {".bat", ".sh", ".py", ".log", ".tmp"}
        count, errors = 0, 0
        for f in temp_dir.iterdir():
            if f.is_file() and f.suffix.lower() in targets:
                try:
                    f.unlink()
                    count += 1
                except:
                    errors += 1

        msg = f"Cleaned {count} files." + (f" (Failed: {errors})" if errors else "")
        self.report({"INFO"}, msg if count else "No residual files found.")
        return {"FINISHED"}


class RECOM_OT_OpenTempDir(Operator):
    """Open the addon's temporary directory in file explorer"""

    bl_idname = "recom.open_temp_dir"
    bl_label = "Open Temp Directory"
    bl_description = "Open the addon's temporary directory in file explorer"
    bl_options = {"REGISTER", "INTERNAL"}

    def execute(self, context):
        prefs = get_addon_preferences(context)

        try:
            temp_dir = get_addon_temp_dir(prefs)

            if not temp_dir.exists():
                temp_dir.mkdir(parents=True, exist_ok=True)

            open_folder(temp_dir)
            log.debug(f"Opened temporary directory: {temp_dir}")

        except Exception as e:
            self.report({"ERROR"}, f"Failed to open temp directory: {e}")
            return {"CANCELLED"}

        return {"FINISHED"}


class RECOM_OT_CheckBlenderVersion(Operator):
    bl_idname = "recom.check_blender_version"
    bl_label = "Check Blender Version"
    bl_description = "Display Blender version information in a popup window"

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
                creationflags=subprocess.CREATE_NO_WINDOW if _IS_WINDOWS else 0,
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
        prefs = get_addon_preferences(context)
        blender_path = bpy.path.abspath(prefs.custom_executable_path)

        row = layout.row()
        row.label(text=f"Version Details")

        col = layout.box().column(align=True)

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
    bl_idname = "recom.launch_custom_blender"
    bl_label = "Launch Blender"
    bl_description = "Execute Blender using a user-defined binary path"

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


class RECOM_OT_RemoveAdditionalScript(Operator):
    bl_idname = "recom.remove_additional_script"
    bl_label = "Remove"
    bl_description = "Remove script from List"

    index: IntProperty()

    def execute(self, context):
        prefs = get_addon_preferences(context)
        prefs.additional_scripts.remove(self.index)
        return {"FINISHED"}


class RECOM_OT_AddAdditionalScript(Operator):
    bl_idname = "recom.add_additional_script"
    bl_label = "Add Script"
    bl_description = "Add new python script"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        prefs.additional_scripts.add()
        return {"FINISHED"}


class RECOM_OT_AddScriptFromMenu(Operator):
    bl_idname = "recom.add_script_from_menu"
    bl_label = "Add Script from Menu"
    bl_options = {"REGISTER", "INTERNAL"}
    bl_description = "Import Script"

    script_path: StringProperty()

    def execute(self, context):
        prefs = get_addon_preferences(context)
        script_to_add = self.script_path

        # Check if there's an existing empty script entry
        for script in prefs.additional_scripts:
            if script.script_path == "":
                script.script_path = script_to_add
                log.info(f"Filled existing empty script entry with: {script_to_add}")
                return {"FINISHED"}

        # If no empty entry found, add a new one
        script_entry = prefs.additional_scripts.add()
        script_entry.script_path = script_to_add
        log.info(f"Added new script entry: {script_to_add}")
        return {"FINISHED"}


class RECOM_OT_ScriptAddItem(Operator):
    bl_idname = "recom.script_list_add_item"
    bl_label = "Add Script"
    bl_description = "Add a new script to the list"
    bl_options = {"REGISTER", "UNDO"}

    order: EnumProperty(
        name="Execution Order",
        items=[
            ("PRE", "Pre-Render", "Run before render"),
            ("POST", "Post-Render", "Run after render"),
        ],
        default="PRE",
    )

    filepath: StringProperty(
        name="File Path",
        subtype="FILE_PATH",
        default="",
        description="Select a Python script file",
    )

    filter_glob: StringProperty(
        default="*.py",
        options={"HIDDEN"},
    )

    def invoke(self, context, event):
        """Open the file browser when the operator is invoked"""
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        prefs = get_addon_preferences(context)
        new_item = prefs.additional_scripts.add()
        new_item.script_path = self.filepath
        new_item.order = self.order
        prefs.active_script_index = len(prefs.additional_scripts) - 1
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_ScriptRemoveItem(Operator):
    bl_idname = "recom.script_list_remove_item"
    bl_label = "Remove Script"
    bl_description = "Remove the selected script from the list"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return len(prefs.additional_scripts) > 0

    def execute(self, context):
        prefs = get_addon_preferences(context)
        index = prefs.active_script_index

        prefs.additional_scripts.remove(index)

        new_len = len(prefs.additional_scripts)
        if new_len == 0:
            prefs.active_script_index = 0
        elif index >= new_len:
            prefs.active_script_index = new_len - 1

        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_ScriptMoveItem(Operator):
    bl_idname = "recom.script_list_move_item"
    bl_label = "Move Script"
    bl_description = "Move the selected script within its list"

    direction: EnumProperty(items=[("UP", "Up", ""), ("DOWN", "Down", "")])

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return len(prefs.additional_scripts) > 1

    def execute(self, context):
        prefs = get_addon_preferences(context)
        scripts = prefs.additional_scripts
        active_index = prefs.active_script_index

        relevant_indices = [i for i, s in enumerate(scripts)]

        try:
            current_list_pos = relevant_indices.index(active_index)
        except ValueError:
            return {"CANCELLED"}

        new_list_pos = current_list_pos
        if self.direction == "UP":
            if current_list_pos == 0:
                return {"CANCELLED"}
            new_list_pos -= 1
        else:
            if current_list_pos >= len(relevant_indices) - 1:
                return {"CANCELLED"}
            new_list_pos += 1

        target_index = relevant_indices[new_list_pos]
        scripts.move(active_index, target_index)
        prefs.active_script_index = target_index
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_ScriptItemButton(Operator):
    bl_idname = "recom.script_list_item_button"
    bl_label = "Item Button"
    bl_description = "An example button for each list item"
    index: IntProperty()

    def execute(self, context):
        prefs = get_addon_preferences(context)
        item = prefs.additional_scripts[self.index]
        self.report({"INFO"}, f"Clicked button for '{item.order}' script: {item.script_path}")
        return {"FINISHED"}


class RECOM_OT_OpenScript(Operator):
    bl_idname = "recom.open_script"
    bl_label = "Open Script"
    bl_description = "Opens the currently active external script into Blender's Text Editor."
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        script_index = prefs.active_script_index
        if script_index < 0 or script_index >= len(prefs.additional_scripts):
            return False
        script = prefs.additional_scripts[script_index]
        return script.script_path

    def execute(self, context):
        prefs = get_addon_preferences(context)
        script_index = prefs.active_script_index
        script = prefs.additional_scripts[script_index]

        script_path = Path(script.script_path)

        if not script_path.exists():
            self.report({"ERROR"}, f"Script file not found: {script_path}")
            return {"CANCELLED"}

        try:
            # Create a new text block
            text_name = script_path.name
            text = bpy.data.texts.new(name=text_name)
            text.from_string(script_path.read_text())

            # Switch to the text editor and set the active text
            for area in context.window.screen.areas:
                if area.type == "TEXT_EDITOR":
                    area.spaces[0].text = text
                    break

        except Exception as e:
            self.report({"ERROR"}, f"Failed to open script: {str(e)}")
            return {"CANCELLED"}

        return {"FINISHED"}


class RECOM_OT_ChangeScriptOrder(Operator):
    bl_idname = "recom.change_script_order"
    bl_label = "Change Script Order"
    bl_options = {"REGISTER", "UNDO"}

    order: EnumProperty(items=[("PRE", "Pre-Render", ""), ("POST", "Post-Render", "")])

    def execute(self, context):
        prefs = get_addon_preferences(context)
        script_index = prefs.active_script_index
        script = prefs.additional_scripts[script_index]
        script.order = self.order
        return {"FINISHED"}


classes = (
    RECOM_OT_LoadingButton,
    RECOM_OT_ContinueSetup,
    RECOM_OT_ReinitializeDevices,
    RECOM_OT_OpenPreferences,
    RECOM_OT_ChangeScriptsDirectory,
    RECOM_OT_DeviceID,
    RECOM_OT_CleanTempFiles,
    RECOM_OT_OpenTempDir,
    RECOM_OT_CheckBlenderVersion,
    RECOM_OT_LaunchCustomBlender,
    RECOM_OT_RemoveAdditionalScript,
    RECOM_OT_AddAdditionalScript,
    RECOM_OT_AddScriptFromMenu,
    RECOM_OT_ScriptAddItem,
    RECOM_OT_ScriptRemoveItem,
    RECOM_OT_ScriptMoveItem,
    RECOM_OT_ScriptItemButton,
    RECOM_OT_ChangeScriptOrder,
    RECOM_OT_OpenScript,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
