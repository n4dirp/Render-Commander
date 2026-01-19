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


class RECOM_PT_RenderPreferencesPresets(PresetPanel, Panel):
    bl_label = "Render Preferences Presets"
    preset_subdir = Path(ADDON_NAME) / "render_preferences"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_render_preferences_preset"


class RECOM_PT_RenderPreferences(Panel):
    """Main panel for render preferences"""

    bl_label = "Preferences"
    bl_idname = "RECOM_PT_render_preferences"
    # bl_parent_id = "RECOM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return prefs.visible_panels.preferences and (
            prefs.initial_setup_complete if render_engine == "CYCLES" else True
        )

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("recom.open_pref", text="", icon="SETTINGS", emboss=False)

        RECOM_PT_RenderPreferencesPresets.draw_panel_header(row)

    def draw(self, context):
        pass


class RECOM_PT_DeviceSettings(Panel):
    bl_label = "Render Devices"
    bl_idname = "RECOM_PT_device_settings"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES"

    def draw_header_preset(self, context):
        layout = self.layout
        layout.menu("RECOM_MT_cycles_render_devices_menu", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column()

        row = col.row(align=True)
        row.use_property_split = True
        row.use_property_decorate = False

        backend_row = row.row()
        backend_row.active = (
            False if (prefs.device_parallel and prefs.multiple_backends and prefs.launch_mode != MODE_SINGLE) else True
        )
        backend_row.prop(prefs, "compute_device_type", text="Backend")

        dev_row = col.row()
        if prefs.compute_device_type != "NONE":
            devices_to_display_list = prefs.get_devices_for_display()
            box = dev_row.box()
            row = box.row(align=True)
            row.separator(factor=0.5)
            col = row.column()
            prefs._draw_devices(col, devices_to_display_list)


class RECOM_PT_DeviceIDs(Panel):
    bl_label = "Device ID"
    bl_idname = "RECOM_PT_device_ids"
    bl_parent_id = "RECOM_PT_device_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.cycles_device_ids

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        box = layout.box()
        label_col = box.column(align=True)
        label_col.active = False

        prev_type = None
        for device in prefs.get_devices_for_display():
            if prev_type is not None and device.type != prev_type:
                label_col.separator(type="LINE")

            row = label_col.row(align=True)
            icon = "CHECKBOX_HLT" if device.use else "CHECKBOX_DEHLT"
            row.label(text=device.id, icon=icon)

            prev_type = device.type


class RECOM_PT_DeviceParallel(Panel):
    bl_label = "Device Parallel"
    bl_idname = "RECOM_PT_device_parallel"
    bl_parent_id = "RECOM_PT_device_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES"

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]

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
        row.prop(prefs, "frame_allocation", expand=True, text="Frame Allocation")

        parallel_col.separator(factor=0.4)
        col = parallel_col.column()
        col.prop(prefs, "parallel_delay", text="Start Delay")

        if any(d.type == "CPU" and d.use for d in prefs.devices):
            parallel_col.separator(factor=0.4)

            col_cpu = parallel_col.column(heading="CPU")
            col_cpu.prop(prefs, "combine_cpu_with_gpus", text="Separated Job", invert_checkbox=True)

            col_tl = col_cpu.column()
            # col_tl.active = prefs.combine_cpu_with_gpus
            col_tl.prop(prefs, "cpu_threads_limit", text="Threads")

        row_bk = layout.column()
        row_bk.active = prefs.launch_mode != MODE_SINGLE
        row_bk.prop(prefs, "multiple_backends", text="Multi-Backend")


class RECOM_PT_RenderOptions(Panel):
    bl_label = "Render Options"
    bl_idname = "RECOM_PT_render_options"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings

        col = layout.column(heading="Auto-Save")
        save_row = col.row()
        if settings.use_external_blend:
            save_row.active = False
        save_row.prop(prefs, "auto_save_before_render", text="Blend File")

        row_sub = col.row(heading="")
        row_sub.active = True if not settings.override_settings.output_path_override else False
        row_sub.prop(prefs, "write_still", text="Still Render")

        terminal_col = layout.row(heading="Terminal")
        terminal_col.prop(prefs, "keep_terminal_open", text="Keep Open")

        col = layout.column()
        col.prop(prefs, "send_desktop_notifications", text="Notification")


class RECOM_PT_SystemPower(Panel):
    bl_label = "Power"
    bl_idname = "RECOM_PT_system_power"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.system_power

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "set_system_power", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        layout.active = prefs.set_system_power

        col = layout.column(heading="")
        col.prop(prefs, "prevent_sleep", text="Prevent Sleep")
        if _IS_WINDOWS:
            col.prop(prefs, "prevent_monitor_off", text="Keep Display")

        col = layout.column(heading="After Render")
        row = col.row()
        row.prop(prefs, "shutdown_after_render", text="")

        row2 = row.row()
        row2.active = prefs.shutdown_after_render
        row2.prop(prefs, "shutdown_type", text="")

        col2 = col.column(heading="After Render")
        col2.active = prefs.shutdown_after_render
        if prefs.shutdown_after_render:
            col2.prop(prefs, "shutdown_delay", text="Delay")


class RECOM_PT_LogToFile(Panel):
    bl_label = "Log to File"
    bl_idname = "RECOM_PT_log_to_file"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "log_to_file", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)
        layout.active = prefs.log_to_file

        col = layout.column()
        col.prop(prefs, "log_to_file_location", text="Save Location")

        if prefs.log_to_file_location == "CUSTOM_PATH":
            col.prop(prefs, "log_custom_path", text="", placeholder="Custom Path")


class RECOM_PT_CustomExecPresets(PresetPanel, Panel):
    bl_label = "Custom Blender Executable Presets"
    preset_subdir = Path(ADDON_NAME) / "custom_executable"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_custom_exec_preset"


class RECOM_PT_CustomExecutable(Panel):
    bl_label = "Executable"
    bl_idname = "RECOM_PT_custom_executables"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.blender_executable

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "custom_executable", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.custom_executable
        RECOM_PT_CustomExecPresets.draw_panel_header(layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        layout.active = prefs.custom_executable
        col = layout.column()
        col.prop(
            prefs,
            "custom_executable_path",
            text="",
            # icon="BLENDER",
            placeholder="Blender Path",
        )

        if prefs.custom_executable and not prefs.custom_executable_path:
            return

        info = prefs.custom_executable_version
        if info and "Version:" in info:
            row_main = col.row()
            col = row_main.column()
            box = col.box()
            row = box.row(align=True)
            row.separator(factor=0.5)
            col = row.column(align=True)

            # Split info into lines
            lines = info.splitlines()
            version_line = next((line for line in lines if "Version:" in line), None)
            other_lines = [line for line in lines if "Version:" not in line]

            row = col.row(align=True)

            if version_line:
                version_col = row.row(align=True)
                version_col.active = False
                version_col.label(text=version_line)

            row.menu("RECOM_MT_custom_blender", text="", icon="DOWNARROW_HLT")

            for line in other_lines:
                lines_col = col.row(align=True)
                lines_col.active = False
                lines_col.label(text=line)


class RECOM_PT_OCIOPresets(PresetPanel, Panel):
    bl_label = "OCIO Presets"
    preset_subdir = Path(ADDON_NAME) / "ocio"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_ocio_preset"


class RECOM_PT_OCIO(Panel):
    bl_label = "OCIO"
    bl_idname = "RECOM_PT_ocio"
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
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "set_ocio", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.set_ocio
        RECOM_PT_OCIOPresets.draw_panel_header(layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        layout.active = prefs.set_ocio

        col = layout.column()
        col.prop(
            prefs,
            "ocio_path",
            text="",
            # icon="FILE",
            placeholder="OCIO Path",
        )


class RECOM_PT_CustomCommandLineArgumentsPresets(PresetPanel, Panel):
    bl_label = "Custom Command Line Arguments Presets"
    preset_subdir = Path(ADDON_NAME) / "command_line_arguments"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_custom_command_line_preset"


class RECOM_PT_CustomCommandLineArguments(Panel):
    bl_label = "Arguments"
    bl_idname = "RECOM_PT_custom_command_line_arguments"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.command_line_arguments

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "add_command_line_args", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.set_ocio
        RECOM_PT_CustomCommandLineArgumentsPresets.draw_panel_header(layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
        layout.active = prefs.add_command_line_args

        row = layout.row(align=True)
        row.prop(
            prefs,
            "custom_command_line_args",
            text="",
            placeholder="Command Line Arguments",
            # icon="CONSOLE",
        )

        version = bpy.app.version_string
        major, minor, _patch = bpy.app.version
        short_version = f"{major}.{minor}"
        url = f"https://docs.blender.org/manual/en/{short_version}/advanced/command_line/arguments.html"
        row.operator("wm.url_open", text="", icon="URL").url = url


class RECOM_PT_AdditionalScriptPresets(PresetPanel, Panel):
    bl_label = "Additional Script Presets"
    preset_subdir = Path(ADDON_NAME) / "additional_scripts"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_additional_script_preset"


class RECOM_UL_ScriptList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(
                item,
                "script_path",
                text="",
                emboss=False,
                # icon="FILE_SCRIPT",
                placeholder="Path to Python Script",
            )

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


class RECOM_PT_AdditionalScripts(Panel):
    bl_label = "Scripts"
    bl_idname = "RECOM_PT_additional_scripts"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.append_scripts

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.prop(prefs, "append_python_scripts", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.append_python_scripts
        RECOM_PT_AdditionalScriptPresets.draw_panel_header(layout)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        layout.active = prefs.append_python_scripts
        scripts = prefs.additional_scripts
        active_index = prefs.active_script_index

        row_main = layout.row()
        row_main.template_list(
            "RECOM_UL_ScriptList",
            "",
            prefs,
            "additional_scripts",
            prefs,
            "active_script_index",
            rows=4,
            item_dyntip_propname="script_path",
        )

        col = row_main.column()
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

        col.separator(factor=0.5)
        col.menu("RECOM_MT_scripts", text="", icon="COLLAPSEMENU")


classes = (
    RECOM_PT_RenderPreferencesPresets,
    RECOM_PT_RenderPreferences,
    RECOM_PT_DeviceSettings,
    RECOM_PT_DeviceIDs,
    RECOM_PT_DeviceParallel,
    RECOM_PT_RenderOptions,
    RECOM_PT_OCIOPresets,
    RECOM_PT_OCIO,
    RECOM_PT_CustomExecPresets,
    RECOM_PT_CustomExecutable,
    RECOM_PT_CustomCommandLineArgumentsPresets,
    RECOM_PT_CustomCommandLineArguments,
    RECOM_PT_LogToFile,
    RECOM_PT_AdditionalScriptPresets,
    RECOM_PT_AdditionalScripts,
    RECOM_UL_ScriptList,
    RECOM_PT_SystemPower,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
