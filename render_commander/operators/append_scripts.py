from pathlib import Path
import logging

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, StringProperty, EnumProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
)

log = logging.getLogger(__name__)


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
    bl_description = "Import script from addon"

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
