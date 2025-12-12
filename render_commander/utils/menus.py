# ./utils/menus.py

from pathlib import Path

import bpy
from bpy.types import Menu

from .constants import *
from ..preferences import get_addon_preferences


class RECOM_MT_ResolvedPath(Menu):
    bl_idname = "RECOM_MT_resolved_path"
    bl_label = "Resolved Path Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.operator("recom.import_output_format", text="Sync Output Path", icon=ICON_SYNC)
        layout.separator()

        layout.prop(prefs, "path_preview", text="Show Resolved Path")
        layout.separator()

        col = layout.column()
        if not prefs.path_preview:
            col.enabled = False

        col.operator("recom.op_copy_text", text="Copy Path", icon="COPYDOWN")
        col.operator("recom.open_folder", text="Open Folder", icon="FOLDER_REDIRECT")


class RECOM_MT_RecentBlendFiles(Menu):
    bl_idname = "RECOM_MT_recent_blend_files"
    bl_label = "Recent External Scenes Menu"

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
        row.label(text="Recent Blend Files")
        row.active = False
        layout.separator()

        # Add recent files to the menu
        for item in reversed(prefs.recent_blend_files):
            op = layout.operator("recom.select_recent_file", text=item.path, icon="FILE_BLEND")
            op.file_path = item.path  # Pass the file path as a parameter

        layout.separator()
        layout.operator("recom.clear_recent_files", text="Clear Recent Files List...", icon="TRASH")


class RECOM_MT_ExternalBlendOptions(Menu):
    bl_idname = "RECOM_MT_external_blend_options"
    bl_label = "External Blend Options"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        file_path = bpy.path.abspath(settings.external_blend_file_path)

        op = layout.operator("recom.open_blend_file", text="Open in Blender", icon="FILE_BLEND")
        op.file_path = file_path

        op_open_in_new_session = layout.operator(
            "recom.open_in_new_blender", text="Open in New Instance"
        )
        op_open_in_new_session.file_path = file_path
        layout.separator()

        op_dir = layout.operator(
            "recom.open_blend_directory", text="Open Blend File Folder", icon="FOLDER_REDIRECT"
        )
        op_dir.file_path = file_path
        layout.separator()

        layout.operator("recom.open_external_scene_info", text="View in Text Editor", icon="TEXT")
        layout.separator()

        layout.prop(prefs, "compact_external_info", text="Compact Scene Info")


class RECOM_MT_ResolutionX(Menu):
    bl_idname = "RECOM_MT_resolution_x"
    bl_label = "Width Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_x = settings.override_settings.resolution_x

        if settings.override_settings.resolution_mode == "SET_HEIGHT":
            layout.enabled = False

        layout.label(text="Set Width")
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
                op = layout.operator("recom.set_resolution_x", text=str(val), icon=icon)
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_ResolutionY(Menu):
    bl_idname = "RECOM_MT_resolution_y"
    bl_label = "Height Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_y = settings.override_settings.resolution_y

        if settings.override_settings.resolution_mode == "SET_WIDTH":
            layout.enabled = False

        layout.label(text="Set Height")
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
                op = layout.operator("recom.set_resolution_y", text=str(val), icon=icon)
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_AdaptiveThreshold(Menu):
    bl_idname = "RECOM_MT_adaptive_threshold"
    bl_label = "Set Adaptive Threshold"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = f"{settings.override_settings.cycles.adaptive_threshold:.4f}"

        layout.label(text="Set Adaptive Threshold")
        layout.separator()

        thresholds = [0.0050, 0.0100, 0.0150, 0.0200, 0.0300, 0.0500, 0.1000]
        for val in thresholds:
            icon = "DOT" if f"{val:.4f}" == current else "BLANK1"
            op = layout.operator("recom.set_adaptive_threshold", text=f"{val:.4f}", icon=icon)
            op.value = val


class RECOM_MT_Samples(Menu):
    bl_idname = "RECOM_MT_samples"
    bl_label = "Set Samples"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.samples

        layout.label(text="Set Samples")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 6144, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_AdaptiveMinSamples(Menu):
    bl_idname = "RECOM_MT_adaptive_min_samples"
    bl_label = "Set Adaptive Min Samples"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.adaptive_min_samples

        layout.label(text="Set Adaptive Min Samples")
        layout.separator()

        values = [0, 16, 32, 64, 128, 256, 512, 1024]
        for val in values:
            icon = "DOT" if val == current else "BLANK1"

            op = layout.operator("recom.set_adaptive_min_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_TimeLimit(Menu):
    bl_idname = "RECOM_MT_time_limit"
    bl_label = "Set Time Limit"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.time_limit

        layout.label(text="Set Time Limit")
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


class RECOM_MT_TileSize(Menu):
    bl_idname = "RECOM_MT_tile_size"
    bl_label = "Set Tile Size"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.tile_size

        layout.label(text="Set Tile Size")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_tile_size", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_EEVEESamples(Menu):
    bl_idname = "RECOM_MT_eevee_samples"
    bl_label = "Set Samples"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.eevee.samples

        layout.label(text="Set Samples")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_eevee_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_CyclesRenderDevices(Menu):
    bl_idname = "RECOM_MT_cycles_render_devices_menu"
    bl_label = "Cycles Render Devices Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        layout.operator(
            "recom.import_from_cycles_settings",
            text="Import Settings from Cycles",
            icon=ICON_SYNC,
        )
        layout.separator()
        layout.operator(
            "recom.reinitialize_devices",
            text="Refresh Device List",
            icon="FILE_REFRESH",
        )
        layout.separator()
        layout.prop(prefs.visible_panels, "cycles_device_ids", text="Show Device IDs")


class RECOM_MT_Scripts(Menu):
    bl_idname = "RECOM_MT_scripts"
    bl_label = "Import Script Menu"

    def draw(self, context):
        layout = self.layout

        current_file = Path(__file__).resolve()
        addon_root = current_file.parent.parent
        scripts_dir = addon_root / "scripts"

        tittle_row = layout.row()
        tittle_row.active = False
        tittle_row.label(text="Import Script")
        layout.separator()

        if scripts_dir.exists():
            for script_path in scripts_dir.rglob("*.py"):
                relative_path = script_path.relative_to(scripts_dir)
                clean_name = str(relative_path.with_suffix(""))
                display_name = (" - ".join(relative_path.parts)).replace("_", " ").title()
                op = layout.operator("recom.add_script_from_menu", text=display_name, icon="SCRIPT")
                op.script_path = str(script_path)


class RECOM_MT_ScriptOptions(Menu):
    bl_idname = "RECOM_MT_script_options"
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

        """
        layout.label(text=f"{script_name}", icon="FILE_SCRIPT")
        layout.separator()
        """
        # layout.label(text="Append Order")
        # layout.separator(type="SPACE")
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

        # if is_post_selected and len(scripts) > 1:
        last_index = len(scripts) - 1

        move_up_row = layout.row(align=True)
        move_up_row.active = script_index > 0
        move_up_op = move_up_row.operator(
            "recom.script_list_move_item", icon="TRIA_UP", text="Move Up"
        )
        move_up_op.direction = "UP"

        move_down_row = layout.row(align=True)
        move_down_row.active = script_index < last_index
        move_down_op = move_down_row.operator(
            "recom.script_list_move_item", icon="TRIA_DOWN", text="Move Down"
        )
        move_down_op.direction = "DOWN"

        layout.separator()

        layout.operator("recom.open_script", text="Open in Text Editor", icon="TEXT")


class RECOM_MT_CustomVariables(Menu):
    bl_idname = "RECOM_MT_custom_variables"
    bl_label = "Variables Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        is_variable_selected = len(
            prefs.custom_variables
        ) > 0 and prefs.active_custom_variable_index < len(prefs.custom_variables)

        # Add move buttons
        if not is_variable_selected or len(prefs.custom_variables) < 1:
            layout.enabled = False

        current_index = prefs.active_custom_variable_index
        last_index = len(prefs.custom_variables) - 1

        move_up_row = layout.column(align=True)
        move_up_button = move_up_row.operator(
            "recom.move_custom_variable_up", text="Move Up", icon="TRIA_UP"
        )
        move_up_row.enabled = current_index > 0

        move_down_row = layout.column(align=True)
        move_down_button = move_down_row.operator(
            "recom.move_custom_variable_down", text="Move Down", icon="TRIA_DOWN"
        )
        move_down_row.enabled = current_index < last_index


class RECOM_MT_CustomBlender(Menu):
    bl_idname = "RECOM_MT_custom_blender"
    bl_label = "Blender Executable Menu"

    def draw(self, context):
        layout = self.layout

        layout.operator("recom.launch_custom_blender", text="Run Blender")
        # layout.separator()
        layout.operator("recom.check_blender_version", text="Version Details...")


class RECOM_MT_RenderHistoryItem(Menu):
    bl_idname = "RECOM_MT_render_history_item"
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
        blend_filename = (
            Path(active_item.blend_path).name if active_item.blend_path else "Unknown Blend File"
        )
        blend_exists = active_item.blend_path and Path(active_item.blend_path).exists()

        blend_col = layout.column(align=True)
        if not active_item.blend_path or not blend_exists:
            blend_col.enabled = False
        """
        header_row = blend_col.row()
        header_row.active = False
        header_row.label(text=f"{blend_filename} - {active_item.render_id}")
        blend_col.separator()
        """

        # Open Blend File
        # if blend_exists:
        op_open_blend_file = blend_col.operator(
            "recom.open_blend_file", text="Open in Blender", icon="FILE_BLEND"
        )
        op_open_blend_file.file_path = active_item.blend_path

        op_open_in_new_session = blend_col.operator(
            "recom.open_in_new_blender", text="Open in New Instance"
        )
        op_open_in_new_session.file_path = active_item.blend_path
        blend_col.separator()

        op_load_external_scene = blend_col.operator(
            "recom.select_recent_file", text="Load External Scene", icon="FILE_BLEND"
        )
        op_load_external_scene.file_path = active_item.blend_path
        blend_col.separator()

        op_open_blend_folder = blend_col.operator(
            "recom.open_output_folder", text="Open Blend File Folder", icon="FOLDER_REDIRECT"
        )
        op_open_blend_folder.folder_path = str(Path(active_item.blend_path).parent)

        if active_item.output_folder and Path(active_item.output_folder).exists():
            op_open_output_folder = layout.operator(
                "recom.open_output_folder", text="Open Output Folder"
            )
            op_open_output_folder.folder_path = active_item.output_folder
        layout.separator()
        remove_op = layout.operator(
            "recom.remove_render_history_item", text="Remove from History", icon="TRASH"
        )


class RECOM_MT_RenderHistory(Menu):
    bl_idname = "RECOM_MT_render_history"
    bl_label = "Render History Menu"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        if len(prefs.render_history) > 0:
            layout.operator(
                "recom.clean_render_history",
                text="Clear Render History List...",
                icon="TRASH",
            )
            layout.separator()
        else:
            layout.active = False

        layout.prop(prefs.visible_panels, "render_details", text="Show Render Details")


classes = (
    RECOM_MT_ResolvedPath,
    RECOM_MT_RecentBlendFiles,
    RECOM_MT_ExternalBlendOptions,
    RECOM_MT_ResolutionX,
    RECOM_MT_ResolutionY,
    RECOM_MT_AdaptiveThreshold,
    RECOM_MT_Samples,
    RECOM_MT_EEVEESamples,
    RECOM_MT_AdaptiveMinSamples,
    RECOM_MT_TimeLimit,
    RECOM_MT_TileSize,
    RECOM_MT_CyclesRenderDevices,
    RECOM_MT_Scripts,
    RECOM_MT_ScriptOptions,
    RECOM_MT_CustomBlender,
    RECOM_MT_CustomVariables,
    RECOM_MT_RenderHistoryItem,
    RECOM_MT_RenderHistory,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
