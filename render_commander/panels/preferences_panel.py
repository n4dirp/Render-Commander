# ./panels/preferences_panel.py

from pathlib import Path

import bpy
from bpy.types import Panel, UIList
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import (
    RECOM_PT_BasePanel,
    RECOM_PT_SubPanel,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RE_WORKBENCH,
    MODE_SINGLE,
    MODE_SEQ,
    MODE_LIST,
)
from ..utils.helpers import get_render_engine
from ..operators.presets import PRESET_REGISTRY
from ..cycles_devices import _CYCLES_AVAILABLE, get_devices_for_display, draw_devices
from ..operators.background_render import draw_script_filename


# Presets
#################################################


class RECOM_PT_render_preferences_presets(PresetPanel, Panel):
    bl_label = "Render Preferences Presets"
    preset_subdir = PRESET_REGISTRY["render_prefs"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.render_preferences_preset_add"


class RECOM_PT_command_line_arguments_presets(PresetPanel, Panel):
    bl_label = "Command Line Arguments Presets"
    preset_subdir = PRESET_REGISTRY["cmd_args"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.command_line_arguments_preset_add"


class RECOM_PT_ocio_presets(PresetPanel, Panel):
    bl_label = "OCIO Configuration Presets"
    preset_subdir = PRESET_REGISTRY["ocio"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.ocio_preset_add"


class RECOM_PT_additional_script_presets(PresetPanel, Panel):
    bl_label = "Python Scripts Presets"
    preset_subdir = PRESET_REGISTRY["scripts"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.additional_script_preset_add"


# Panels
#################################################


class RECOM_PT_render_preferences(RECOM_PT_SubPanel, Panel):
    """Main panel for render preferences"""

    bl_label = "Render Preferences"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.preferences

    def draw_header_preset(self, context):
        RECOM_PT_render_preferences_presets.draw_panel_header(self.layout)

    def draw(self, context):
        pass


class RECOM_PT_command_line(RECOM_PT_BasePanel, Panel):
    bl_label = "Command Line"
    bl_parent_id = "RECOM_PT_render_preferences"

    def draw(self, context):
        pass


class RECOM_PT_command_line_arguments(RECOM_PT_BasePanel, Panel):
    bl_label = "Arguments"
    bl_parent_id = "RECOM_PT_command_line"
    bl_options = {"DEFAULT_CLOSED"}

    CONFIGURABLE_ARGS = {
        "--log-file",
        "-P",
        "--python",
        "-d",
        "--debug",
        "--verbose",
        "--debug-value",
        "--debug-cycles",
        "-F",
        "--render-format",
    }

    BANNED_ARGS = {
        "-b",
        "--background",
        "-a",
        "--render-anim",
        "-f",
        "--render-frame",
        "-s",
        "--frame-start",
        "-e",
        "--frame-end",
        "-o",
        "--render-output",
    }

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
        layout.active = prefs.add_command_line_args

        raw_args = prefs.custom_command_line_args.split()
        found_banned = [arg for arg in raw_args if arg in self.BANNED_ARGS]
        found_config = [arg for arg in raw_args if arg in self.CONFIGURABLE_ARGS]

        row = layout.row()
        sub = row.row(align=True)

        row_arg = sub.row(align=True)
        if found_banned:
            row_arg.alert = True
        row_arg.prop(prefs, "custom_command_line_args", text="")

        row.operator("recom.open_docs_custom", text="", icon="URL")

        if found_banned:
            col = layout.column(align=True)
            col.label(text="Overlapping arguments detected")
            col.label(text=f"Remove: {', '.join(found_banned)}")

        if found_config:
            col = layout.column(align=True)
            col.label(text="Redundant arguments detected")
            col.label(text=f"Managed: {', '.join(found_config)}")


class RECOM_PT_log_to_file(RECOM_PT_BasePanel, Panel):
    bl_label = "Logging"
    bl_parent_id = "RECOM_PT_command_line"
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

        if prefs.log_to_file_location == "CUSTOM_PATH":
            col.prop(prefs, "log_custom_path", text="", placeholder="Path")

        folder_row = col.row(heading="Subfolder")
        folder_row.prop(prefs, "save_to_log_folder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.save_to_log_folder
        sub_folder_row.prop(prefs, "logs_folder_name", text="")


class RECOM_PT_debug_arguments(RECOM_PT_BasePanel, Panel):
    bl_label = "Debugging"
    bl_parent_id = "RECOM_PT_command_line"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "cmd_debug", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        layout.active = prefs.cmd_debug

        col = layout.column()
        col.prop(prefs, "debug_value", text="Debug Value")
        col.prop(prefs, "verbose_level", text="Verbosity Level")

        col = layout.column()
        col.prop(prefs, "debug_cycles", text="Debug Cycles")


class RECOM_PT_ocio(RECOM_PT_BasePanel, Panel):
    bl_label = "OCIO"
    bl_parent_id = "RECOM_PT_command_line"
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


class RECOM_PT_additional_scripts(RECOM_PT_BasePanel, Panel):
    bl_label = "Scripts"
    bl_parent_id = "RECOM_PT_command_line"
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
        is_post_selected = len(scripts) > 0 and active_index < len(scripts)
        rows = 5 if len(scripts) > 0 else 3

        # UI List for scripts
        row = layout.row()
        row.template_list(
            "RECOM_UL_script_list",
            "",
            prefs,
            "additional_scripts",
            prefs,
            "active_script_index",
            rows=rows,
            item_dyntip_propname="tooltip_display",
        )

        # Side controls
        col = row.column()
        add_col = col.column(align=True)
        add_col.operator("recom.script_list_add_item", icon="ADD", text="")
        sub = add_col.column(align=True)
        sub.enabled = is_post_selected
        sub.operator("recom.script_list_remove_item", icon="REMOVE", text="")

        col.separator(factor=0.5)
        row = col.row(align=True)
        row.enabled = is_post_selected
        row.alignment = "RIGHT"
        row.menu("RECOM_MT_script_options", text="", icon="DOWNARROW_HLT")

        if not is_post_selected:
            return

        col.separator(factor=0.5)
        col = col.column(align=True)
        col.operator("recom.script_list_move_item", icon="TRIA_UP", text="").direction = "UP"
        col.operator("recom.script_list_move_item", icon="TRIA_DOWN", text="").direction = "DOWN"

        active_item = scripts[active_index]
        layout.prop(active_item, "script_path", text="")


class RECOM_UL_script_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.script_path:
            return

        file_path = Path(item.script_path)
        is_python_file = file_path.suffix.lower() == ".py"
        icon = "SCRIPT" if is_python_file else "ERROR"
        if not is_python_file:
            layout.alert = True

        layout.label(text=file_path.name, icon=icon)

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


class RECOM_PT_device_settings(RECOM_PT_BasePanel, Panel):
    bl_label = "Compute Devices"
    bl_parent_id = "RECOM_PT_render_options"

    @classmethod
    def poll(cls, context):
        return get_render_engine(context) == RE_CYCLES and _CYCLES_AVAILABLE

    def draw_header(self, context):
        prefs = get_addon_preferences(context)
        self.layout.prop(prefs, "manage_cycles_devices", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        if not prefs.manage_cycles_devices:
            return
        layout.emboss = "PULLDOWN_MENU"
        layout.menu("RECOM_MT_cycles_render_devices", text="", icon='COLLAPSEMENU')
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        if not prefs.manage_cycles_devices:
            layout.label(text="Uses default Cycles settings")
            return

        col = layout.column()

        is_multi_backend = prefs.device_parallel and prefs.multiple_backends and prefs.launch_mode != MODE_SINGLE
        if not is_multi_backend:
            row = col.row(align=True)
            row.use_property_split = True
            row.use_property_decorate = False
            row.active = not is_multi_backend
            row.prop(prefs, "compute_device_type", text="Backend")

        if prefs.compute_device_type == "NONE" and not (prefs.multiple_backends and prefs.device_parallel):
            return

        col = col.box().column(align=True)
        draw_devices(col, prefs)


class RECOM_PT_device_parallel(RECOM_PT_BasePanel, Panel):
    bl_label = "Device Parallel"
    bl_parent_id = "RECOM_PT_device_settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.launch_mode in {MODE_SEQ, MODE_LIST} and prefs.manage_cycles_devices

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = prefs.manage_cycles_devices and prefs.launch_mode != MODE_SINGLE
        layout.prop(prefs, "device_parallel", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        devices_to_display = get_devices_for_display(prefs)
        selected_devices = [d for d in devices_to_display if d.use]

        layout.active = prefs.manage_cycles_devices and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel

        layout.prop(prefs, "multiple_backends", text="Multi-Backend")

        parallel_col = layout.column()
        parallel_col.active = len(selected_devices) > 1 and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel

        row = parallel_col.row()
        row.active = prefs.launch_mode != MODE_LIST
        row.prop(prefs, "frame_allocation", text="Assignment", expand=True)

        parallel_col.prop(prefs, "parallel_delay", text="Start Delay")

        if any(d.type == "CPU" and d.use for d in prefs.devices):
            parallel_col.separator(factor=0.25)
            col_cpu = parallel_col.column(heading="CPU")
            col_cpu.prop(prefs, "combine_cpu_with_gpus", text="Isolate Job", invert_checkbox=True)

            col_tl = col_cpu.column()
            col_tl.prop(prefs, "cpu_threads_limit", text="Thread Limit")

        # Calculate instances count
        enabled_devices = [d for d in devices_to_display if d.use]
        num_instances = len(enabled_devices)
        if any(d.type == "CPU" and d.use for d in enabled_devices) and prefs.combine_cpu_with_gpus:
            num_instances -= 1
        num_instances = max(num_instances, 1)
        layout.label(text=f"Render Instances: {num_instances}")


class RECOM_PT_render_parallel(RECOM_PT_BasePanel, Panel):
    bl_label = "Multi-Process"
    bl_parent_id = "RECOM_PT_render_options"
    bl_options = {"DEFAULT_CLOSED"}
    
    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH} and prefs.launch_mode in {
            MODE_SEQ,
            MODE_LIST,
        }

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
        col.prop(prefs, "parallel_delay", text="Start Delay")


class RECOM_PT_render_options(RECOM_PT_BasePanel, Panel):
    bl_label = "Advanced Settings"
    bl_parent_id = "RECOM_PT_render_preferences"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings

        root_col = layout.column()

        col = root_col.column(heading="Blender", align=True)
        if not (settings.use_external_blend and settings.external_blend_file_path):
            col.prop(prefs, "auto_save_before_render", text="Save Blend File")
        col.prop(prefs, "exit_active_session", text="Exit Active Session")

        col = root_col.column(heading="Render")
        if prefs.launch_mode == MODE_SINGLE:
            col.prop(prefs, "write_still", text="Write Still")
        else:
            col.prop(prefs, "track_render_time", text="Track Render Time")

        root_col.prop(prefs, "keep_terminal_open")


class RECOM_PT_output_filename(Panel):
    bl_label = "File Output"
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
        col.prop(prefs, "default_render_filename", text="Default Name")
        col.prop(prefs, "frame_length_digits", text="Frame Padding")
        col.prop(prefs, "filename_separator", text="Separator")


class RECOM_PT_export_options(RECOM_PT_BasePanel, Panel):
    bl_label = "Script Export"
    bl_parent_id = "RECOM_PT_render_options"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        col = layout.column()
        col.prop(prefs, "export_output_target", text="Target")
        if prefs.export_output_target == "CUSTOM_PATH":
            col.prop(prefs, "custom_export_path", text="", placeholder="Path")

        folder_row = col.row(heading="Subfolder")
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(prefs, "export_scripts_folder_name", text="")


        col = layout.column(heading="File Name", align=True)
        draw_script_filename(col, prefs)

        col = layout.column(heading="Auto", align=True)
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Folder")

classes = (
    RECOM_PT_render_preferences_presets,
    RECOM_PT_render_preferences,
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
    RECOM_PT_render_options,
    RECOM_PT_output_filename,
    RECOM_PT_export_options,
    RECOM_PT_device_settings,
    RECOM_PT_device_parallel,
    RECOM_PT_render_parallel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
