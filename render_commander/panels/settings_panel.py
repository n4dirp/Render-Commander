# ./panels/preferences_panel.py

from pathlib import Path

import bpy
from bl_ui.utils import PresetPanel
from bpy.types import Panel, UIList

from ..operators.export import draw_script_filename
from ..operators.presets import PRESET_REGISTRY
from ..utils.constants import (
    MODE_LIST,
    MODE_SINGLE,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RE_WORKBENCH,
    RCBasePanel,
    RCSubPanel,
)
from ..utils.cycles_devices import (
    _CYCLES_AVAILABLE,
    draw_devices,
    get_devices_for_display,
)
from ..utils.helpers import (
    draw_label_value_box,
    get_addon_preferences,
    get_render_engine,
)

CONFIGURABLE_ARGS = {
    "--log-file",
    "-P",
    "--python",
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


class RECOM_PT_render_preferences(RCSubPanel, Panel):
    """Main panel for render preferences"""

    bl_label = "Settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.preferences

    def draw_header_preset(self, context):
        RECOM_PT_render_preferences_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings

        root_col = layout.column(align=True)
        root_col.prop(prefs, "keep_terminal_open")

        row = root_col.column()
        if settings.use_external_blend and settings.external_blend_file_path:
            row.active = False
        row.prop(prefs, "auto_save_before_render", text="Auto Save Blend File")

        sub = root_col.column()
        if prefs.launch_mode == MODE_SINGLE:
            sub.active = False
        sub.prop(prefs, "track_render_time", text="Track Render Time")


class RECOM_PT_output_filename(Panel):
    bl_label = "Output File"
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

        col = layout.column()
        col.prop(prefs, "default_render_filename", text="Filename")
        col.prop(prefs, "frame_length_digits", text="Frame Padding")
        col.prop(prefs, "filename_separator", text="Separator")

        row = layout.row()
        if prefs.launch_mode != MODE_SINGLE:
            row.active = False
        row.prop(prefs, "write_still", text="Write Still")


class RECOM_PT_export_options(RCBasePanel, Panel):
    bl_label = "Export Scripts"
    bl_parent_id = "RECOM_PT_render_preferences"
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

        folder_row = col.row(heading="Add Subfolder")
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(prefs, "export_scripts_folder_name", text="")

        col = layout.column(heading="Script Naming", align=True)
        draw_script_filename(col, prefs)

        col = layout.column(heading="", align=True)
        col.prop(prefs, "auto_open_exported_folder", text="Open in File Explorer")


class RECOM_PT_device_settings(RCBasePanel, Panel):
    bl_label = "Manage Devices"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _CYCLES_AVAILABLE and get_render_engine(context) == RE_CYCLES

    def draw_header(self, context):
        layout = self.layout.row(align=True)
        prefs = get_addon_preferences(context)
        layout.active = get_render_engine(context) == RE_CYCLES
        layout.prop(prefs, "manage_cycles_devices", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        if not prefs.manage_cycles_devices:
            return
        layout.emboss = "PULLDOWN_MENU"
        layout.menu("RECOM_MT_cycles_render_devices", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = get_render_engine(context) == RE_CYCLES

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
            row.prop(prefs, "compute_device_type", text="Backend Type")

        if prefs.compute_device_type == "NONE" and not (prefs.multiple_backends and prefs.device_parallel):
            return

        col = col.box().column(align=True)
        draw_devices(col, prefs)


class RECOM_PT_device_parallel(RCBasePanel, Panel):
    bl_label = "Parallel Rendering"
    bl_parent_id = "RECOM_PT_device_settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.manage_cycles_devices

    def draw_header(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.active = (
            get_render_engine(context) == RE_CYCLES and prefs.manage_cycles_devices and prefs.launch_mode != MODE_SINGLE
        )
        layout.prop(prefs, "device_parallel", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        devices_to_display = get_devices_for_display(prefs)
        selected_devices = [d for d in devices_to_display if d.use]

        layout.active = (
            get_render_engine(context) == RE_CYCLES
            and prefs.manage_cycles_devices
            and prefs.launch_mode != MODE_SINGLE
            and prefs.device_parallel
        )

        layout.prop(prefs, "multiple_backends", text="Multi-Backend")

        parallel_col = layout.column()
        parallel_col.active = len(selected_devices) > 1 and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel

        row = parallel_col.row()
        row.active = prefs.launch_mode != MODE_LIST
        row.prop(prefs, "frame_allocation", text="Distribution", expand=True)

        parallel_col.prop(prefs, "parallel_delay", text="Start Delay")

        if any(d.type == "CPU" and d.use for d in prefs.devices):
            parallel_col.separator(factor=0.25)
            col_cpu = parallel_col.column(heading="")
            col_cpu.prop(prefs, "combine_cpu_with_gpus", text="Combine CPU & GPU")

            col_tl = col_cpu.column()
            col_tl.prop(prefs, "cpu_threads_limit", text="Thread Limit")

        if prefs.device_parallel:
            # Calculate instances count
            enabled_devices = [d for d in devices_to_display if d.use]
            num_instances = len(enabled_devices)
            if any(d.type == "CPU" and d.use for d in enabled_devices) and prefs.combine_cpu_with_gpus:
                num_instances -= 1
            num_instances = max(num_instances, 1)

            draw_label_value_box(layout, "Instances", f"{num_instances}")


class RECOM_PT_render_instances(RCBasePanel, Panel):
    bl_label = "Render Instances"
    bl_parent_id = "RECOM_PT_render_preferences"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        # prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}

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
        row.prop(prefs, "frame_allocation", text="Distribution", expand=True)
        col.prop(prefs, "parallel_delay", text="Start Delay")


class RECOM_PT_command_line_arguments(RCBasePanel, Panel):
    bl_label = "Command Arguments"
    bl_parent_id = "RECOM_PT_render_preferences"
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
        layout.active = prefs.add_command_line_args

        raw_args = prefs.custom_command_line_args.split()
        found_banned = [arg for arg in raw_args if arg in BANNED_ARGS]
        found_config = [arg for arg in raw_args if arg in CONFIGURABLE_ARGS]

        row = layout.row()
        sub = row.row(align=True)

        row_arg = sub.row(align=True)
        if found_banned:
            row_arg.alert = True
        row_arg.prop(prefs, "custom_command_line_args", text="")

        if found_banned:
            box = layout.box()
            box.active = False
            col = box.column(align=True)
            col.label(text="Overlapping arguments detected.", icon="ERROR")
            col.label(text=f"Remove: {', '.join(found_banned)}", icon="BLANK1")

        if found_config:
            box = layout.box()
            box.active = False
            col = box.column(align=True)
            col.label(text="Redundant arguments detected.", icon="INFO")
            col.label(text=f"Managed: {', '.join(found_config)}", icon="BLANK1")


class RECOM_PT_additional_scripts(RCBasePanel, Panel):
    bl_label = "Python Scripts"
    bl_parent_id = "RECOM_PT_render_preferences"
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


class RECOM_UL_script_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.script_path:
            return

        file_path = Path(item.script_path)
        is_python_file = file_path.suffix.lower() == ".py"
        if not is_python_file:
            layout.alert = True

        layout.prop(item, "script_path", text="", emboss=False)

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


class RECOM_PT_log_to_file(RCBasePanel, Panel):
    bl_label = "File Logging"
    bl_parent_id = "RECOM_PT_render_preferences"
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

        folder_row = col.row(heading="Add Subfolder")
        folder_row.prop(prefs, "save_to_log_folder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.save_to_log_folder
        sub_folder_row.prop(prefs, "logs_folder_name", text="")


class RECOM_PT_ocio(RCBasePanel, Panel):
    bl_label = "OCIO"
    bl_parent_id = "RECOM_PT_render_preferences"
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


classes = (
    RECOM_PT_render_preferences_presets,
    RECOM_PT_render_preferences,
    RECOM_PT_output_filename,
    # RECOM_PT_export_options,
    RECOM_PT_render_instances,
    RECOM_PT_device_settings,
    RECOM_PT_device_parallel,
    RECOM_PT_command_line_arguments_presets,
    RECOM_PT_command_line_arguments,
    RECOM_PT_additional_script_presets,
    RECOM_PT_additional_scripts,
    RECOM_UL_script_list,
    RECOM_PT_log_to_file,
    RECOM_PT_ocio_presets,
    RECOM_PT_ocio,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
