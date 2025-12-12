import bpy
from bpy.types import Operator

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
)


class RECOM_OT_AddCustomVariable(Operator):
    bl_idname = "recom.add_custom_variable"
    bl_label = "Add Custom Variable"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        existing = prefs.custom_variables

        base_name = "Variable"
        base_token = "var"
        base_value = "value"

        idx = 1
        while (
            any(item.name == f"{base_name} {idx}" for item in existing)
            or any(item.token == f"{base_token}_{idx}" for item in existing)
            or any(item.value == f"{base_value}_{idx}" for item in existing)
        ):
            idx += 1

        new_item = prefs.custom_variables.add()
        new_item.name = f"{base_name} {idx}"
        new_item.token = f"{base_token}_{idx}"
        new_item.value = f"{base_value}_{idx}"

        prefs.active_custom_variable_index = len(prefs.custom_variables) - 1
        return {"FINISHED"}


class RECOM_OT_RemoveCustomVariable(Operator):
    bl_idname = "cbl.remove_custom_variable"
    bl_label = "Remove Custom Variable"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index
        if idx >= 0:
            prefs.custom_variables.remove(idx)
            # Check if the collection is now empty
            if len(prefs.custom_variables) == 0:
                prefs.active_custom_variable_index = -1
            else:
                # Update the active index
                prefs.active_custom_variable_index = max(0, idx - 1)
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_MoveCustomVariableUp(Operator):
    bl_idname = "recom.move_custom_variable_up"
    bl_label = "Move Up"
    bl_description = "Move the selected custom variable up in the list"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index

        if idx > 0:
            # Swap with the previous item
            prefs.custom_variables.move(idx, idx - 1)
            prefs.active_custom_variable_index -= 1

        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_MoveCustomVariableDown(Operator):
    bl_idname = "recom.move_custom_variable_down"
    bl_label = "Move Down"
    bl_description = "Move the selected custom variable down in the list"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index

        if idx < len(prefs.custom_variables) - 1:
            # Swap with the next item
            prefs.custom_variables.move(idx, idx + 1)
            prefs.active_custom_variable_index += 1

        redraw_ui()
        return {"FINISHED"}


classes = (
    RECOM_OT_AddCustomVariable,
    RECOM_OT_RemoveCustomVariable,
    RECOM_OT_MoveCustomVariableUp,
    RECOM_OT_MoveCustomVariableDown,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
