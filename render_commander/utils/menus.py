# ./utils/menus.py

import json
import logging
from pathlib import Path

import bpy
from bpy.types import Menu

from ..preferences import get_addon_preferences

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


def get_scene_info(settings):
    """Single source of truth for scene info parsing"""
    if not settings.external_scene_info or not settings.is_scene_info_loaded:
        return None

    try:
        info = json.loads(settings.external_scene_info)
        if info.get("blend_filepath", "") == "No Data":
            return None
        return info
    except json.JSONDecodeError as e:
        log.error("Failed to decode JSON: %s", e)
        return None


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

        op_dir = layout.operator("recom.open_blend_directory", text="Open Blend File Path", icon="FILE_FOLDER")
        op_dir.file_path = file_path

        try:
            info = get_scene_info(settings)
            output_path = info.get("filepath", "")
            frame_path = info.get("frame_path", "")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            pass
        if output_path and frame_path:
            op_open_output_folder = layout.operator("recom.open_blend_output_path", text="Open Output Path")
            op_open_output_folder.file_path = frame_path

        layout.separator()
        layout.operator(
            "recom.clear_and_reload_scene_info",
            text="Clear Cache & Reload",
            icon="FILE_REFRESH",
        )
        layout.separator()
        layout.prop(prefs, "compact_external_info", text="Compact Scene Info")


class RECOM_MT_sampling_factor(Menu):
    bl_label = "Sampling Factor Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_value = f"{settings.override_settings.cycles.sampling_factor:.1f}"

        layout.label(text="Sampling Factor")
        layout.separator()

        scale_options = [
            ("25", "25%", "0.25x Samples"),
            ("50", "50%", "0.5x Samples"),
            ("100", "100%", "Original Scene Values"),
            ("150", "150%", "1.5x Samples"),
            ("200", "200%", "2x Samples"),
            ("400", "400%", "4x Samples"),
        ]

        for value, label, description in scale_options:
            icon = "DOT" if f"{float(value):.1f}" == current_value else "BLANK1"

            op = layout.operator("recom.set_sampling_factor", text=label, icon=icon)
            op.value = float(value)


class RECOM_MT_resolution_x(Menu):
    bl_label = "X Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_x = settings.override_settings.resolution_x

        if settings.override_settings.resolution_mode == "SET_HEIGHT":
            layout.enabled = False

        layout.label(text="Resolution X")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text="Swap X and Y", icon="UV_SYNC_SELECT")
        layout.separator()

        sections = {
            "Landscape": [7680, 5120, 3840, 2560, 1280, 854, 640],
            "Portait": [2160, 1920, 720, 480, 360],
            "Square": [8192, 4096, 2048, 1080, 1024, 800, 512, 256],
        }
        section_count = len(sections)

        for i, (label, values) in enumerate(sections.items()):
            for val in values:
                icon = "DOT" if val == current_x else "BLANK1"

                op = layout.operator("recom.set_resolution", text=f"{val} px", icon=icon)
                op.dimension = "X"
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_resolution_y(Menu):
    bl_label = "Y Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_y = settings.override_settings.resolution_y

        if settings.override_settings.resolution_mode == "SET_WIDTH":
            layout.enabled = False

        layout.label(text="Resolution Y")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text="Swap X and Y", icon="UV_SYNC_SELECT")
        layout.separator()

        sections = {
            "Landscape": [4320, 2880, 2160, 1440, 720, 480],
            "Portait": [3840, 2560, 1920, 1350, 1280, 960, 640],
            "Square": [8192, 4096, 2048, 1080, 1024, 800, 512, 256],
        }
        section_count = len(sections)

        for i, (label, values) in enumerate(sections.items()):
            for val in values:
                icon = "DOT" if val == current_y else "BLANK1"

                op = layout.operator("recom.set_resolution", text=f"{val} px", icon=icon)
                op.dimension = "Y"
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_custom_render_scale(Menu):
    bl_label = "Resolution Scale Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_value = f"{settings.override_settings.custom_render_scale:.2f}"

        layout.label(text="Resolution Scale")
        layout.separator()

        scale_options = [
            ("400", "400%", "4x resolution multiplier"),
            ("300", "300%", "3x resolution multiplier"),
            ("200", "200%", "2x resolution multiplier"),
            ("150", "150%", "1.5x resolution multiplier"),
            ("100", "100%", "Native resolution"),
            ("66.67", "66.7% (2/3)", "2/3 resolution"),
            ("50", "50%", "Half resolution"),
            ("33.33", "33.3% (1/3)", "1/3 resolution"),
            ("25", "25%", "Quarter resolution"),
        ]

        for value, label, description in scale_options:
            icon = "DOT" if f"{float(value):.2f}" == current_value else "BLANK1"

            op = layout.operator("recom.set_custom_render_scale", text=label, icon=icon)
            op.value = float(value)  # Convert to float for setting the property


class RECOM_MT_adaptive_threshold(Menu):
    bl_label = "Adaptive Threshold Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = f"{settings.override_settings.cycles.adaptive_threshold:.4f}"

        layout.label(text="Adaptive Threshold")
        layout.separator()

        thresholds = [0.0050, 0.0100, 0.0150, 0.0250, 0.0500, 0.1000]
        for val in thresholds:
            icon = "DOT" if f"{val:.4f}" == current else "BLANK1"
            op = layout.operator("recom.set_adaptive_threshold", text=f"{val:.4f}", icon=icon)
            op.value = val


class RECOM_MT_samples(Menu):
    bl_label = "Samples Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.samples

        layout.label(text="Samples")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 6144, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_adaptive_min_samples(Menu):
    bl_label = "Adaptive Min Samples Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.adaptive_min_samples

        layout.label(text="Adaptive Min Samples")
        layout.separator()

        values = [0, 16, 32, 64, 128, 256, 512, 1024]
        for val in values:
            icon = "DOT" if val == current else "BLANK1"

            op = layout.operator("recom.set_adaptive_min_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_time_limit(Menu):
    bl_label = "Time Limit Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.time_limit

        layout.label(text="Time Limit")
        layout.separator()

        time_presets = [
            ("0 s", 0.0),
            ("15 s", 15.0),
            ("30 s", 30.0),
            ("1 min", 60.0),
            ("3 min", 180.0),
            ("5 min", 300.0),
            ("10 min", 600.0),
            ("15 min", 900.0),
            ("20 min", 1200.0),
            ("30 min", 1800.0),
            ("1 hr", 3600.0),
            ("3 hr", 10800.0),
            ("6 hr", 21600.0),
        ]
        for label, seconds in time_presets:
            icon = "DOT" if seconds == current else "BLANK1"

            op = layout.operator("recom.set_time_limit", text=label, icon=icon)
            op.value = seconds


class RECOM_MT_tile_size(Menu):
    bl_label = "Tile Size Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.tile_size

        layout.label(text="Tile Size")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_tile_size", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_cycles_render_devices(Menu):
    bl_label = "Cycles Render Devices Menu"

    def draw(self, context):
        layout = self.layout
        layout.operator("recom.cycles_device_ids", text="Show Device IDs", icon="INFO")
        layout.operator("recom.reinitialize_devices", icon="FILE_REFRESH")


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
        op_load_external_scene = blend_col.operator("recom.select_recent_file", text="Read Blend File", icon="ZOOM_ALL")
        op_load_external_scene.file_path = active_item.blend_path
        blend_col.separator()
        op_open_blend_folder = blend_col.operator(
            "recom.open_output_folder", text="Open Blend File Path", icon="FILE_FOLDER"
        )
        layout.separator()
        layout.operator("recom.remove_render_history_item", text="Remove from History", icon="TRASH")


# Data for Path Variables Menu
PATH_VARIABLES_DATA = {
    "data": [
        ("{blend_dir}", "Blend Directory"),
        ("{blend_name}", "Blend Name"),
        ("", ""),
        ("{fps}", "Frame Rate"),
        ("{resolution_x}", "Resolution X"),
        ("{resolution_y}", "Resolution Y"),
        ("", ""),
        ("{scene_name}", "Scene Name"),
        ("{camera_name}", "Camera Name"),
    ],
}


class RECOM_MT_insert_variable_root(Menu):
    bl_label = "Add Variable Menu"
    bl_description = "Add a variable to the output file path"

    def draw_section(self, layout, title, variables):
        col = layout.column(align=True)
        col.label(text=title)
        col.separator()

        for token, label in variables:
            if not token:
                col.separator()
                continue

            op = col.operator("recom.insert_variable", text=label)
            op.variable = token

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        show_templates = bpy.app.version >= (5, 0)
        has_custom = bool(prefs.custom_variables)

        if not show_templates and not has_custom:
            layout.label(text="No variables available", icon="INFO")
            return

        # Calculate columns based on visible sections only
        num_sections = 1 if show_templates else 0
        extra_column = 1 if has_custom else 0
        columns = num_sections + extra_column

        flow = layout.grid_flow(columns=columns, even_columns=True, even_rows=False, align=True)

        # Draw Path Templates section (Blender 5.0+)
        if show_templates:
            self.draw_section(flow.column(), "Path Templates", PATH_VARIABLES_DATA["data"])

        # Draw Custom Variables section
        if has_custom:
            col = flow.column(align=True)
            col.label(text="Custom")
            col.separator()

            for var in prefs.custom_variables:
                op = col.operator("recom.insert_variable", text=var.name)
                op.variable = f"{{{var.token}}}"


classes = (
    RECOM_MT_recent_blend_files,
    RECOM_MT_external_blend_options,
    RECOM_MT_sampling_factor,
    RECOM_MT_resolution_x,
    RECOM_MT_resolution_y,
    RECOM_MT_custom_render_scale,
    RECOM_MT_adaptive_threshold,
    RECOM_MT_samples,
    RECOM_MT_adaptive_min_samples,
    RECOM_MT_time_limit,
    RECOM_MT_tile_size,
    RECOM_MT_cycles_render_devices,
    RECOM_MT_script_options,
    RECOM_MT_render_history_item,
    RECOM_MT_insert_variable_root,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
