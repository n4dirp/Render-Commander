# ./utils/menus.py

import json
import logging
from pathlib import Path

import bpy
from bpy.types import Menu

from ..utils.helpers import get_addon_preferences, get_scene_info

log = logging.getLogger(__name__)


class RECOM_MT_recent_blend_files(Menu):
    bl_label = "Recent Files Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        if not prefs.recent_blend_files:
            row = layout.row()
            row.active = False
            row.alignment = "CENTER"
            row.label(text="No recent files")
            return

        row = layout.row()
        row.label(text="Recent Files")
        row.active = False
        layout.separator()

        # Add recent files to the menu
        for item in reversed(prefs.recent_blend_files):
            op = layout.operator("recom.select_recent_file", text=item.path, icon="FILE_BLEND")
            op.file_path = item.path  # Pass the file path as a parameter

        layout.separator()
        layout.operator("recom.clear_recent_files", text="Clear Recent Files List...", icon="TRASH")


class RECOM_MT_external_blend_options(Menu):
    bl_label = "External Blend Options"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        file_path = bpy.path.abspath(settings.external_blend_file_path)

        op = layout.operator("recom.open_blend_file", text="Open in Blender", icon="FILE_BLEND")
        op.file_path = file_path

        op_open_in_new_session = layout.operator("recom.open_in_new_blender", text="Open in New Instance")
        op_open_in_new_session.file_path = file_path
        layout.separator()

        op_dir = layout.operator(
            "recom.open_blend_directory",
            text="Open Blend Folder",
            icon="FILE_FOLDER",
        )
        op_dir.file_path = file_path

        try:
            info = get_scene_info(settings)
            output_path = info.get("filepath", "")
            frame_path = info.get("frame_path", "")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            log.error("Error occurred while fetching scene info: %s", e)
        if output_path and frame_path:
            op_open_output_folder = layout.operator("recom.open_blend_output_path", text="Open Output Folder")
            op_open_output_folder.file_path = frame_path

        layout.separator()
        layout.operator(
            "recom.clear_and_reload_scene_info",
            text="Clear Cache & Reload",
            icon="FILE_REFRESH",
        )
        layout.separator()
        layout.prop(prefs, "compact_external_info", text="Compact Scene Info")


class RECOM_MT_script_options(Menu):
    bl_label = "Script Options Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        script_index = prefs.active_script_index

        if script_index < 0 or script_index >= len(prefs.additional_scripts):
            layout.active = False
            layout.label(text="No Script Selected")
            return

        script = prefs.additional_scripts[script_index]

        if not script.script_path:
            layout.active = False

        current_order = script.order
        op_pre = layout.operator(
            "recom.change_script_order",
            text="Append Before Render",
            icon="DOT" if current_order == "PRE" else "BLANK1",
        )
        op_pre.order = "PRE"
        op_post = layout.operator(
            "recom.change_script_order",
            text="Append After Render",
            icon="DOT" if current_order == "POST" else "BLANK1",
        )
        op_post.order = "POST"

        layout.separator()
        layout.operator("recom.open_script", text="Open in Text Editor", icon="TEXT")


class RECOM_MT_render_history_item(Menu):
    bl_label = "History Item Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        render_history = prefs.render_history
        if not render_history:
            layout.active = False
            layout.label(text="No recent renders")
            return

        active_item = render_history[prefs.active_render_history_index]
        blend_exists = active_item.blend_path and Path(active_item.blend_path).exists()

        blend_col = layout.column(align=True)
        if not active_item.blend_path or not blend_exists:
            blend_col.enabled = False

        op_open_blend_file = blend_col.operator("recom.open_blend_file", text="Open in Blender", icon="FILE_BLEND")
        op_open_blend_file.file_path = active_item.blend_path
        op_open_in_new_session = blend_col.operator("recom.open_in_new_blender", text="Open in New Instance")
        op_open_in_new_session.file_path = active_item.blend_path
        blend_col.separator()
        blend_col.operator(
            "recom.select_recent_file", text="Read Blend File", icon="ZOOM_ALL"
        ).file_path = active_item.blend_path

        blend_col.separator()
        blend_col.operator("recom.open_output_folder", text="Open Blend Folder", icon="FILE_FOLDER").folder_path = str(
            Path(active_item.blend_path).parent
        )

        blend_col.operator("recom.open_output_folder", text="Open Scripts Folder").folder_path = active_item.export_path

        layout.separator()
        layout.operator("recom.remove_render_history_item", text="Remove from History", icon="TRASH")


class RECOM_MT_cycles_render_devices(Menu):
    bl_label = "Cycles Render Devices Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.operator("recom.reinitialize_devices", icon="FILE_REFRESH")
        layout.separator()
        layout.prop(prefs, "show_device_id")


classes = (
    RECOM_MT_recent_blend_files,
    RECOM_MT_external_blend_options,
    RECOM_MT_cycles_render_devices,
    RECOM_MT_script_options,
    RECOM_MT_render_history_item,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
