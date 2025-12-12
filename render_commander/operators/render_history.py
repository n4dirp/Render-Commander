from pathlib import Path
import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    open_folder,
)

log = logging.getLogger(__name__)


class RECOM_OT_CleanRenderHistory(Operator):
    """Open a popup to delete render history entries."""

    bl_idname = "recom.clean_render_history"
    bl_label = "Clean Render History List"

    remove_type: EnumProperty(
        name="Remove",
        description="Select items to remove",
        items=[("ALL", "All Items", ""), ("NOT_FOUND", "Items not Found", "")],
        default="ALL",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = get_addon_preferences(context)
        if self.remove_type == "ALL":
            prefs.render_history.clear()
            log.info("Cleared all render history.")
            return {"FINISHED"}

        elif self.remove_type == "NOT_FOUND":
            # Remove entries whose blend file or output folder no longer exist
            for i in reversed(range(len(prefs.render_history))):
                item = prefs.render_history[i]

                blend_path = Path(item.blend_path)
                missing_blend = not blend_path.is_file()

                output_folder = item.output_folder
                missing_output = bool(output_folder) and not Path(output_folder).is_dir()

                if missing_blend or missing_output:
                    prefs.render_history.remove(i)
                    log.info(f"Removed missing render history item: {item.blend_path}")
            return {"FINISHED"}

        else:
            return {"CANCELLED"}


class RECOM_OT_RemoveRenderHistoryItem(Operator):
    """Remove selected render history item"""

    bl_idname = "recom.remove_render_history_item"
    bl_label = "Remove Render History Item"
    bl_description = "Remove selected render history item"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        active_index = prefs.active_render_history_index
        if active_index >= 0 and active_index < len(prefs.render_history):
            # Remove the active history item
            prefs.render_history.remove(active_index)

            # Update active index to point to a valid item (if any remain)
            new_active_index = min(active_index, len(prefs.render_history) - 1)
            if new_active_index >= 0:
                prefs.active_render_history_index = new_active_index
        return {"FINISHED"}


class RECOM_OT_OpenOutputFolder(Operator):
    """Open the output folder in file explorer."""

    bl_idname = "recom.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Opens a folder in your system's file explorer."

    folder_path: StringProperty(name="Folder Path", default="")

    def execute(self, context):
        open_folder(self.folder_path)
        return {"FINISHED"}


classes = (
    RECOM_OT_CleanRenderHistory,
    RECOM_OT_RemoveRenderHistoryItem,
    RECOM_OT_OpenOutputFolder,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
