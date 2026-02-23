# ./panels/preferences_panel.py

import sys
from pathlib import Path

import bpy
from bpy.types import Panel, UIList, Operator
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences, RECOM_Preferences
from ..utils.constants import *
from ..utils.helpers import redraw_ui, get_render_engine

_IS_WINDOWS = sys.platform == "win32"

import importlib.util

_WIN11TOAST_AVAILABLE = _IS_WINDOWS and importlib.util.find_spec("win11toast") is not None


# Presets


class RECOM_PT_render_preferences_presets(PresetPanel, Panel):
    bl_label = "Render Preferences Presets"
    preset_subdir = Path(ADDON_NAME) / "render_preferences"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.render_preferences_preset_add"


class RECOM_PT_blender_executable_presets(PresetPanel, Panel):
    bl_label = "Blender Executable Presets"
    preset_subdir = Path(ADDON_NAME) / "custom_executable"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.blender_executable_preset_add"


class RECOM_PT_command_line_arguments_presets(PresetPanel, Panel):
    bl_label = "Command Line Arguments Presets"
    preset_subdir = Path(ADDON_NAME) / "command_line_arguments"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.command_line_arguments_preset_add"


class RECOM_PT_ocio_presets(PresetPanel, Panel):
    bl_label = "OCIO Configuration Presets"
    preset_subdir = Path(ADDON_NAME) / "ocio"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.ocio_preset_add"


class RECOM_PT_additional_script_presets(PresetPanel, Panel):
    bl_label = "Python Scripts Presets"
    preset_subdir = Path(ADDON_NAME) / "additional_scripts"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.additional_script_preset_add"


# Main Panel


class RECOM_PT_render_preferences(Panel):
    """Main panel for render preferences"""

    bl_label = "Preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return prefs.visible_panels.preferences and (
            prefs.initial_setup_complete if render_engine == RE_CYCLES else True
        )

    def draw_header_preset(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.operator("recom.open_pref", text="", icon="PREFERENCES", emboss=False)
        # row.menu("RECOM_MT_preferences_menu", text="", icon="COLLAPSEMENU")
        row.separator(factor=1.0)

        RECOM_PT_render_preferences_presets.draw_panel_header(row)

    def draw(self, context):
        pass


# Environment & Configuration


class RECOM_PT_blender_executable(Panel):
    bl_label = "Blender Executable"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    # bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        RECOM_PT_blender_executable_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        source_row = layout.row()
        source_row.prop(prefs, "blender_executable_source", text="Source", expand=True)

        if prefs.blender_executable_source == "CUSTOM":
            col = layout.column()
            custom_executable_row = col.row()
            custom_executable_row.prop(prefs, "custom_executable_path", text="", placeholder="Blender Path")

            is_active = bool(prefs.custom_executable_path)

            if not is_active:
                return

            info = prefs.custom_executable_version
            if info and "Version:" in info:
                # Split info into lines
                lines = info.splitlines()
                version_line = next((line for line in lines if "Version:" in line), None)
                other_lines = [line for line in lines if "Version:" not in line]

                if version_line:
                    version_row = layout.row(align=False)
                    version_row.label(text=version_line.replace("Version:", "Blender"), icon="BLENDER")
                    version_row.menu("RECOM_MT_custom_blender", text="", icon=ICON_OPTION)


class RECOM_PT_command_line(Panel):
    bl_label = "Command Line"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        pass


class RECOM_PT_command_line_arguments(Panel):
    bl_label = "Arguments"
    bl_parent_id = "RECOM_PT_command_line"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "add_command_line_args", text="")

    def draw_header_preset(self, context):
        RECOM_PT_command_line_arguments_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        row = layout.row()
        prop_row = row.row(align=True)

        arg_row = prop_row.row(align=True)
        arg_row.active = prefs.add_command_line_args
        arg_row.prop(prefs, "custom_command_line_args", text="")

        # Documentation link
        version = bpy.app.version_string
        major, minor, _ = bpy.app.version
        url = f"https://docs.blender.org/manual/en/{major}.{minor}/advanced/command_line/arguments.html"
        row.operator("wm.url_open", text="", icon="URL").url = url


class RECOM_PT_log_to_file(Panel):
    bl_label = "Logging"
    bl_parent_id = "RECOM_PT_command_line"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "log_to_file", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)
        layout.active = prefs.log_to_file

        col = layout.column()
        col.prop(prefs, "log_to_file_location", text="Target")

        # col = layout.column()
        if prefs.log_to_file_location == "CUSTOM_PATH":
            layout.prop(prefs, "log_custom_path", text="", placeholder="Logs Path")

        layout.prop(prefs, "logs_folder_name", text="Sub-Folder")


class RECOM_PT_debug_arguments(Panel):
    bl_label = "Debugging"
    bl_parent_id = "RECOM_PT_command_line"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "debug_mode", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        layout.active = prefs.debug_mode

        col = layout.column()
        col.prop(prefs, "debug_value", text="Debug Value")
        col.prop(prefs, "verbose_level", text="Verbosity Level")

        col = layout.column()
        col.prop(prefs, "debug_cycles", text="Debug Cycles")


class RECOM_PT_ocio(Panel):
    bl_label = "OCIO"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.ocio

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "set_ocio", text="")

    def draw_header_preset(self, context):
        RECOM_PT_ocio_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        layout.active = prefs.set_ocio
        layout.prop(prefs, "ocio_path", text="", placeholder="OCIO File")


class RECOM_PT_additional_scripts(Panel):
    bl_label = "Python Scripts"
    bl_parent_id = "RECOM_PT_command_line"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "append_python_scripts", text="")

    def draw_header_preset(self, context):
        RECOM_PT_additional_script_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        layout.active = prefs.append_python_scripts
        scripts = prefs.additional_scripts
        active_index = prefs.active_script_index

        # UI List for scripts
        row_main = layout.row()
        row_main.template_list(
            "RECOM_UL_script_list",
            "",
            prefs,
            "additional_scripts",
            prefs,
            "active_script_index",
            rows=4,
            item_dyntip_propname="tooltip_display",
        )

        # Side controls
        col = row_main.column()
        col.menu("RECOM_MT_scripts", text="", icon="COLLAPSEMENU")
        col.separator(factor=0.5)

        add_col = col.column(align=True)
        add_col.operator("recom.script_list_add_item", icon="ADD", text="")
        is_post_selected = len(scripts) > 0 and active_index < len(scripts)
        sub = add_col.column(align=True)
        sub.enabled = is_post_selected
        sub.operator("recom.script_list_remove_item", icon="REMOVE", text="")

        col.separator(factor=0.5)
        item_menu_row = col.row(align=True)
        item_menu_row.active = is_post_selected
        item_menu_row.alignment = "RIGHT"
        item_menu_row.menu("RECOM_MT_script_options", text="", icon="DOWNARROW_HLT")


class RECOM_UL_script_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)

            p = Path(item.script_path)
            is_python_file = p.suffix.lower() == ".py"
            icon = "FILE_SCRIPT" if is_python_file else "ERROR"

            if not is_python_file:
                row.alert = True

            row.label(text=p.name)  # , icon=icon)

            # row.prop(item, "script_path", text="", emboss=False)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = []
        flt_neworder = []

        filter_text = self.filter_name.lower().strip() if self.filter_name else ""

        for item in items:
            if filter_text in item.script_path.lower():
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder


# Compute & Execution


class RECOM_PT_device_settings(Panel):
    bl_label = "Compute Devices"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        return get_render_engine(context) == RE_CYCLES

    def draw_header_preset(self, context):
        layout = self.layout
        layout.menu("RECOM_MT_cycles_render_devices", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column()

        row = col.row(align=True)
        row.use_property_split = True
        row.use_property_decorate = False

        is_multi_backend = prefs.device_parallel and prefs.multiple_backends and prefs.launch_mode != MODE_SINGLE

        backend_row = row.row(align=True)
        backend_row.active = not is_multi_backend
        backend_row.prop(prefs, "compute_device_type", text="Backend")

        dev_row = layout.row()
        box = dev_row.box()

        col = box.column()
        devices = prefs.get_devices_for_display()

        if prefs.compute_device_type == "NONE" and not (prefs.multiple_backends and prefs.device_parallel):
            for device in devices:
                col.active = False
                col.label(text=device.name)
        else:
            prefs._draw_devices(col, devices)


class RECOM_PT_device_parallel(Panel):
    bl_label = "Device Parallel"
    bl_parent_id = "RECOM_PT_device_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    # bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == RE_CYCLES and prefs.launch_mode in {MODE_SEQ, MODE_LIST}

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.launch_mode != MODE_SINGLE
        layout.prop(prefs, "device_parallel", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        selected_devices = [d for d in prefs.devices if d.type == prefs.compute_device_type and d.use]
        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]

        layout.active = prefs.launch_mode != MODE_SINGLE and prefs.device_parallel
        parallel_col = layout.column()
        parallel_col.active = len(selected_devices) > 1 and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel

        row = parallel_col.row()
        row.active = prefs.launch_mode != MODE_LIST
        row.prop(prefs, "frame_allocation", text="Assignment", expand=True)

        parallel_col.separator(factor=0.25)
        col = parallel_col.column()
        col.prop(prefs, "parallel_delay", text="Start Delay")

        if any(d.type == "CPU" and d.use for d in prefs.devices):
            parallel_col.separator(factor=0.25)

            col_cpu = parallel_col.column(heading="CPU")
            col_cpu.prop(prefs, "combine_cpu_with_gpus", text="Isolate Job", invert_checkbox=True)

            col_tl = col_cpu.column()
            col_tl.prop(prefs, "cpu_threads_limit", text="Thread Limit")

        row_bk = layout.column()
        row_bk.active = prefs.launch_mode != MODE_SINGLE
        row_bk.prop(prefs, "multiple_backends", text="Multi-Backend")


class RECOM_PT_render_parallel(Panel):
    bl_label = "Multi-Process"  # "Render Instances"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    # bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH} and prefs.launch_mode in {MODE_SEQ, MODE_LIST}

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.launch_mode != MODE_SINGLE
        layout.prop(prefs, "multi_instance", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        layout.active = prefs.launch_mode != MODE_SINGLE and prefs.multi_instance

        col = layout.column()
        col.prop(prefs, "render_iterations", text="Process Count")

        row = col.row()
        row.active = prefs.launch_mode != MODE_LIST
        row.prop(prefs, "frame_allocation", text="Assignment", expand=True)

        if prefs.render_iterations > 1:
            col.prop(prefs, "parallel_delay", text="Start Delay")


# Session & Output


class RECOM_PT_render_options(Panel):
    bl_label = "Render Settings"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings

        # Pre-Render Actions
        col = layout.column(heading="Before Render")
        if not (settings.use_external_blend and settings.external_blend_file_path):
            col.prop(prefs, "auto_save_before_render", text="Auto-Save Blend")
        col.prop(prefs, "exit_active_session", text="Exit Active Session")
        col.prop(prefs, "auto_open_output_folder", text="Open Output Folder")

        # Post-Render Actions
        if prefs.launch_mode == MODE_SINGLE:
            col = layout.column(heading="Render")
            col.prop(prefs, "write_still", text="Save Image")

        # Terminal Behavior
        col = layout.column(heading="Terminal")
        col.prop(prefs, "keep_terminal_open", text="Keep Open")

        render_engine = get_render_engine(context)
        is_parallel = prefs.launch_mode in {MODE_SEQ, MODE_LIST} and (
            prefs.device_parallel if render_engine == RE_CYCLES else prefs.multi_instance
        )
        if _IS_WINDOWS and is_parallel:
            col.prop(prefs, "use_windows_terminal_tabs", text="Use Tabs")


class RECOM_PT_output_filename(Panel):
    bl_label = "Output File"
    bl_parent_id = "RECOM_PT_render_options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        col = layout.column()
        col.prop(prefs, "default_render_filename", text=" Filename")

        sub = col.column(heading="Formatting")
        sep_row = sub.row()
        sep_row.prop(prefs, "filename_separator", text="Separator", expand=True)
        sub.prop(prefs, "frame_length_digits", text="Frame Padding")


class RECOM_PT_export_options(Panel):
    bl_label = "Script Export"
    bl_parent_id = "RECOM_PT_render_options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        col = layout.column()
        col.prop(prefs, "export_output_target", text="Target")
        if prefs.export_output_target == "CUSTOM_PATH":
            col = layout.column()
            col.prop(prefs, "custom_export_path", text="", placeholder="Scripts Path")

        col = layout.column()
        folder_row = col.row(heading="Sub-Folder")
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(prefs, "export_scripts_folder_name", text="")

        render_engine = get_render_engine(context)
        is_parallel = prefs.launch_mode in {MODE_SEQ, MODE_LIST} and (
            prefs.device_parallel if render_engine == RE_CYCLES else prefs.multi_instance
        )
        if is_parallel:
            col.prop(prefs, "export_master_script", text="Create Master Script")
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Folder")


# System


class RECOM_PT_notification(Panel):
    bl_label = "Notifications"
    bl_parent_id = "RECOM_PT_render_options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "send_desktop_notifications", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        layout.active = prefs.send_desktop_notifications

        col = layout.column()
        row = col.row()
        row.prop(prefs, "notification_detail_level", text="Detail", expand=True)

        if prefs.notification_detail_level != "SIMPLE" and _IS_WINDOWS and _WIN11TOAST_AVAILABLE:
            sub = layout.column(heading="Content")
            sub.prop(prefs, "notification_show_preview", text="Render Preview")
            sub.prop(prefs, "notification_show_buttons", text="Action Buttons")


class RECOM_PT_system_power(Panel):
    bl_label = "Power Management"
    bl_parent_id = "RECOM_PT_render_options"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "set_system_power", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        layout.active = prefs.set_system_power

        col = layout.column(heading="During Render")
        col.prop(prefs, "prevent_sleep", text="Prevent Sleep")
        if _IS_WINDOWS:
            col.prop(prefs, "prevent_monitor_off", text="Keep Display On")

        col = layout.column(heading="Completion")
        row = col.row()
        row.prop(prefs, "shutdown_after_render", text="")

        row2 = row.row()
        row2.active = prefs.shutdown_after_render
        row2.prop(prefs, "shutdown_type", text="")

        col2 = col.column(heading="")
        col2.active = prefs.shutdown_after_render
        if prefs.shutdown_after_render:
            col2.prop(prefs, "shutdown_delay", text="Delay")


classes = (
    RECOM_PT_render_preferences_presets,
    RECOM_PT_render_preferences,
    # Environment
    RECOM_PT_blender_executable_presets,
    RECOM_PT_blender_executable,
    RECOM_PT_command_line,
    RECOM_PT_command_line_arguments_presets,
    RECOM_PT_command_line_arguments,
    RECOM_PT_additional_script_presets,
    RECOM_PT_additional_scripts,
    RECOM_UL_script_list,
    RECOM_PT_log_to_file,
    RECOM_PT_debug_arguments,
    RECOM_PT_ocio_presets,
    RECOM_PT_ocio,
    # Compute
    RECOM_PT_device_settings,
    RECOM_PT_device_parallel,
    RECOM_PT_render_parallel,
    # Session & Output
    RECOM_PT_render_options,
    RECOM_PT_output_filename,
    RECOM_PT_export_options,
    # System
    RECOM_PT_notification,
    RECOM_PT_system_power,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
