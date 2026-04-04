# ./utils/menus.py

import json
from pathlib import Path

import bpy
from bpy.types import Menu

from .constants import *
from ..preferences import get_addon_preferences


class RECOM_MT_resolved_path(Menu):
    bl_label = "Resolved Path Menu"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)
        layout.label(text="Show")
        layout.separator()
        layout.prop(prefs, "path_preview", text="Resolved Path")
        layout.prop(prefs, "show_custom_variables_panel", text="Custom Variables")


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

        op_dir = layout.operator("recom.open_blend_directory", text="Open Blend File Path", icon="FILE_FOLDER")
        op_dir.file_path = file_path

        try:
            output_path = json.loads(settings.external_scene_info).get("filepath", "//")
        except:
            output_path = "//"
        op_open_output_folder = layout.operator("recom.open_output_folder", text="Open Output Path")
        op_open_output_folder.folder_path = output_path

        if prefs.debug_mode:
            layout.separator()
            layout.operator("recom.open_external_scene_info", text="View in Text Editor", icon="TEXT")

            layout.separator()
            layout.prop(prefs, "compact_external_info", text="Compact Scene Info")


class RECOM_MT_resolution_x(Menu):
    bl_label = "Width Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_x = settings.override_settings.resolution_x

        if settings.override_settings.resolution_mode == "SET_HEIGHT":
            layout.enabled = False

        layout.label(text="Resolution Width")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text=f"Swap Width and Height", icon="UV_SYNC_SELECT")
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
                op = layout.operator("recom.set_resolution_x", text=f"{str(val)} px", icon=icon)
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_resolution_y(Menu):
    bl_label = "Height Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_y = settings.override_settings.resolution_y

        if settings.override_settings.resolution_mode == "SET_WIDTH":
            layout.enabled = False

        layout.label(text="Resolution Height")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text=f"Swap Width and Height", icon="UV_SYNC_SELECT")
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
                op = layout.operator("recom.set_resolution_y", text=f"{str(val)} px", icon=icon)
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


class RECOM_MT_eevee_samples(Menu):
    bl_label = "Samples Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.eevee.samples

        layout.label(text="Render Samples")
        layout.separator()

        values = [64, 128, 256, 512, 1024]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_eevee_samples", text=str(val), icon=icon)
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
        prefs = get_addon_preferences(context)

        layout.operator("recom.import_from_cycles_settings", text="Import Device Settings", icon=ICON_SYNC)
        layout.operator("recom.reinitialize_devices", icon="FILE_REFRESH")
        layout.separator()
        layout.operator("recom.cycles_device_ids", text="Show Device IDs", icon="INFO")


class RECOM_MT_scripts(Menu):
    bl_label = "Import Scripts Menu"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)
        scripts_dir = (
            Path(prefs.scripts_directory)
            if prefs.scripts_directory
            else Path(__file__).resolve().parent.parent / "scripts"
        )

        tittle_row = layout.row()
        tittle_row.active = False
        tittle_row.label(text="Import Scripts")
        layout.separator()

        if scripts_dir.exists():
            scripts = list(scripts_dir.rglob("*.py"))

            if scripts:
                scripts.sort()

                for script_path in scripts:
                    relative_path = script_path.relative_to(scripts_dir)
                    clean_parts = [bpy.path.display_name(part) for part in relative_path.with_suffix("").parts]
                    display_name = " / ".join(clean_parts)
                    op = layout.operator("recom.add_script_from_menu", text=display_name, icon="FILE_SCRIPT")
                    op.script_path = str(script_path)

                layout.separator()

        layout.operator("recom.change_scripts_directory", text="Change Directory...", icon="FILE_FOLDER")


class RECOM_MT_script_options(Menu):
    bl_label = "Script Options Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        script_index = prefs.active_script_index
        scripts = prefs.additional_scripts

        if script_index < 0 or script_index >= len(prefs.additional_scripts):
            layout.active = False
            layout.label(text="No Script Selected")
            return

        script = prefs.additional_scripts[script_index]

        script_name = Path(script.script_path).name if script.script_path else "Empty Path"
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

        last_index = len(scripts) - 1

        move_up_row = layout.row(align=True)
        move_up_row.active = script_index > 0
        move_up_op = move_up_row.operator("recom.script_list_move_item", icon="TRIA_UP", text="Move Up")
        move_up_op.direction = "UP"

        move_down_row = layout.row(align=True)
        move_down_row.active = script_index < last_index
        move_down_op = move_down_row.operator("recom.script_list_move_item", icon="TRIA_DOWN", text="Move Down")
        move_down_op.direction = "DOWN"

        layout.separator()
        layout.operator("recom.open_script", text="Open in Text Editor", icon="TEXT")


class RECOM_MT_custom_variables(Menu):
    bl_label = "Variables Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        is_variable_selected = len(prefs.custom_variables) > 0 and prefs.active_custom_variable_index < len(
            prefs.custom_variables
        )

        # Add move buttons
        if not is_variable_selected or len(prefs.custom_variables) < 1:
            layout.enabled = False

        current_index = prefs.active_custom_variable_index
        last_index = len(prefs.custom_variables) - 1

        move_up_row = layout.column(align=True)
        move_up_button = move_up_row.operator("recom.move_custom_variable_up", text="Move Up", icon="TRIA_UP")
        move_up_row.enabled = current_index > 0

        move_down_row = layout.column(align=True)
        move_down_button = move_down_row.operator("recom.move_custom_variable_down", text="Move Down", icon="TRIA_DOWN")
        move_down_row.enabled = current_index < last_index


class RECOM_MT_custom_blender(Menu):
    bl_label = "Blender Executable Menu"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)
        layout.enabled = bool(prefs.custom_executable_path)

        layout.operator("recom.launch_custom_blender", text="Launch Custom Blender", icon="BLANK1")
        layout.operator("recom.check_blender_version", text="Version Details...", icon="BLANK1")


class RECOM_MT_render_history_item(Menu):
    bl_label = "Render Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        render_history = prefs.render_history
        if not render_history:
            layout.active = False
            layout.label(text="No recent renders")
            return

        active_item = render_history[prefs.active_render_history_index]
        blend_filename = Path(active_item.blend_path).name if active_item.blend_path else "Unknown Blend File"
        blend_exists = active_item.blend_path and Path(active_item.blend_path).exists()

        blend_col = layout.column(align=True)
        if not active_item.blend_path or not blend_exists:
            blend_col.enabled = False

        # Open Blend File
        # if blend_exists:
        op_open_blend_file = blend_col.operator("recom.open_blend_file", text="Open in Blender", icon="FILE_BLEND")
        op_open_blend_file.file_path = active_item.blend_path

        op_open_in_new_session = blend_col.operator("recom.open_in_new_blender", text="Open in New Instance")
        op_open_in_new_session.file_path = active_item.blend_path
        blend_col.separator()

        op_load_external_scene = blend_col.operator(
            "recom.select_recent_file", text="Load Blend File", icon="FILE_BLEND"
        )
        op_load_external_scene.file_path = active_item.blend_path
        blend_col.separator()

        op_open_blend_folder = blend_col.operator(
            "recom.open_output_folder", text="Open Blend File Path", icon="FILE_FOLDER"
        )
        op_open_blend_folder.folder_path = str(Path(active_item.blend_path).parent)

        if active_item.output_folder and Path(active_item.output_folder).exists():
            op_open_output_folder = layout.operator("recom.open_output_folder", text="Open Output Path")
            op_open_output_folder.folder_path = active_item.output_folder
        layout.separator()
        remove_op = layout.operator("recom.remove_render_history_item", text="Remove from History", icon="TRASH")


class RECOM_MT_render_history(Menu):
    bl_label = "Render History Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        layout.enabled = bool(prefs.render_history)
        layout.operator("recom.clean_render_history", text="Clear Render History List...", icon="TRASH")


classes = (
    RECOM_MT_resolved_path,
    RECOM_MT_recent_blend_files,
    RECOM_MT_external_blend_options,
    RECOM_MT_resolution_x,
    RECOM_MT_resolution_y,
    RECOM_MT_custom_render_scale,
    RECOM_MT_adaptive_threshold,
    RECOM_MT_samples,
    RECOM_MT_eevee_samples,
    RECOM_MT_adaptive_min_samples,
    RECOM_MT_time_limit,
    RECOM_MT_tile_size,
    RECOM_MT_cycles_render_devices,
    RECOM_MT_scripts,
    RECOM_MT_script_options,
    RECOM_MT_custom_blender,
    RECOM_MT_custom_variables,
    RECOM_MT_render_history_item,
    RECOM_MT_render_history,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
