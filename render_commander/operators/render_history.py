from pathlib import Path
import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import redraw_ui, open_folder

log = logging.getLogger(__name__)


class RECOM_OT_CleanRenderHistory(Operator):
    """Open a popup to delete render history entries."""

    bl_idname = "recom.clean_render_history"
    bl_label = "Clean History List"
    bl_options = {"INTERNAL"}

    remove_type: EnumProperty(
        name="Remove",
        description="Select items to remove",
        items=[("ALL", "All Items", ""), ("NOT_FOUND", "Blend File Not Found", "")],
        default="NOT_FOUND",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        prefs = get_addon_preferences(context)
        removed_count = 0

        if self.remove_type == "ALL":
            removed_count = len(prefs.render_history)
            prefs.render_history.clear()
            log.info("Cleared all render history")

        elif self.remove_type == "NOT_FOUND":
            for i in reversed(range(len(prefs.render_history))):
                item = prefs.render_history[i]

                blend_path_str = item.blend_path
                missing_blend = bool(blend_path_str) and not Path(blend_path_str).is_file()

                if missing_blend:
                    prefs.render_history.remove(i)
                    removed_count += 1
                    log.info("Removed missing render history item: %s", item.blend_path)

        else:
            return {"CANCELLED"}

        redraw_ui()

        if removed_count > 0:
            label = "item" if removed_count == 1 else "items"
            self.report({"INFO"}, f"Removed {removed_count} {label}")
        else:
            self.report({"INFO"}, "No items to remove")

        return {"FINISHED"}


class RECOM_OT_RemoveRenderHistoryItem(Operator):
    """Remove selected render history item"""

    bl_idname = "recom.remove_render_history_item"
    bl_label = "Remove Render History Item"
    bl_description = "Remove selected render history item"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        prefs = get_addon_preferences(context)
        active_index = prefs.active_render_history_index

        if 0 <= active_index < len(prefs.render_history):
            prefs.render_history.remove(active_index)

            new_active_index = min(active_index, len(prefs.render_history) - 1)
            if new_active_index >= 0:
                prefs.active_render_history_index = new_active_index
        return {"FINISHED"}


class RECOM_OT_OpenOutputFolder(Operator):
    """Open the output folder in file explorer."""

    bl_idname = "recom.open_output_folder"
    bl_label = "Open Output Folder"
    bl_description = "Open the folder"
    bl_options = {"INTERNAL"}

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
