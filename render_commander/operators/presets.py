import logging
from pathlib import Path

import bpy
from bl_operators.presets import AddPresetBase
from bpy.types import Operator

from .. import __package__ as base_package
from ..utils.helpers import get_addon_preferences, get_override_settings

log = logging.getLogger(__name__)

BASE_NAME = base_package.split(".")[-1]
PRESET_BASE_PATH = "recom"
PRESET_REGISTRY = {
    # Overrides
    "overrides_main": f"{PRESET_BASE_PATH}/overrides_main",
    "resolution": f"{PRESET_BASE_PATH}/resolution",
    "cycles_samples": f"{PRESET_BASE_PATH}/cycles_samples",
    "output_path": f"{PRESET_BASE_PATH}/output_path",
    "custom_variables": f"{PRESET_BASE_PATH}/custom_variables",
    "advanced_props": f"{PRESET_BASE_PATH}/advanced_props",
    # Preferences
    "render_prefs": f"{PRESET_BASE_PATH}/render_prefs",
    "cmd_args": f"{PRESET_BASE_PATH}/cmd_args",
    "scripts": f"{PRESET_BASE_PATH}/scripts",
}

PROP_TYPE_ATTR_MAP = {
    "BOOL": "value_bool",
    "INT": "value_int",
    "FLOAT": "value_float",
    "STRING": "value_string",
    "VECTOR_3": "value_vector_3",
    "COLOR_4": "value_color_4",
}
ADDON_ID_DEFINE = (
    "addon_id = next((ext.module for ext in "
    f"bpy.context.preferences.addons "
    f"if ext.module.endswith('{BASE_NAME}')), "
    f"'{BASE_NAME}')"
)


def _save_data_path_overrides_preset(context, name, preset_subdir):
    """Helper to write data_path_overrides to a preset python file."""
    clean_name = bpy.path.clean_name(name.strip())
    subdir_path = Path("presets") / preset_subdir
    target_dir = Path(bpy.utils.user_resource("SCRIPTS", path=str(subdir_path), create=True))
    filepath = target_dir / f"{clean_name}.py"

    if not filepath.exists():
        return

    override_settings = get_override_settings(context)
    lines = [
        "\n# Custom API Overrides Collection",
        "override_settings.data_path_overrides.clear()",
    ]

    for item in override_settings.data_path_overrides:
        lines.append("item = override_settings.data_path_overrides.add()")
        lines.append(f"item.name = {repr(item.name)}")
        lines.append(f"item.data_path = {repr(item.data_path)}")
        lines.append(f"item.prop_type = {repr(item.prop_type)}")

        attr = PROP_TYPE_ATTR_MAP.get(item.prop_type)
        if attr:
            val = getattr(item, attr)
            if item.prop_type in ("VECTOR_3", "COLOR_4"):
                val = list(val)
            lines.append(f"item.{attr} = {repr(val)}")

    lines.append(f"override_settings.active_data_path_index = {override_settings.active_data_path_index}")

    try:
        with filepath.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError as e:
        log.error("File Error: Could not save preset. %s", e.strerror)
    except Exception:
        log.exception("Unexpected error saving preset")


class RECOM_OT_overrides_preset(AddPresetBase, Operator):
    bl_idname = "recom.overrides_preset_add"
    bl_label = "Add Overrides Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_overrides_presets"
    preset_defines = ["override_settings = bpy.context.window_manager.recom_render_settings.override_settings"]
    preset_values = [
        # Cycles Sampling Overrides
        "override_settings.cycles.sampling_override",
        "override_settings.cycles.sampling_mode",
        "override_settings.cycles.sampling_factor",
        "override_settings.cycles.samples",
        "override_settings.cycles.adaptive_min_samples",
        "override_settings.cycles.time_limit",
        "override_settings.cycles.use_adaptive_sampling",
        "override_settings.cycles.adaptive_threshold",
        # Cycles Denoising Settings
        "override_settings.cycles.denoising_override",
        "override_settings.cycles.use_denoising",
        "override_settings.cycles.denoiser",
        "override_settings.cycles.denoising_input_passes",
        "override_settings.cycles.denoising_prefilter",
        "override_settings.cycles.denoising_quality",
        "override_settings.cycles.denoising_use_gpu",
        # Cycles Performance
        "override_settings.cycles.device_override",
        "override_settings.cycles.device",
        "override_settings.cycles.performance_override",
        "override_settings.cycles.use_tiling",
        "override_settings.cycles.tile_size",
        "override_settings.cycles.use_spatial_splits",
        "override_settings.cycles.use_compact_bvh",
        "override_settings.cycles.persistent_data",
        # EEVEE
        "override_settings.eevee_override",
        "override_settings.eevee.samples",
        # Frame Range Settings
        "override_settings.frame_range_override",
        "override_settings.frame_current",
        "override_settings.frame_start",
        "override_settings.frame_end",
        "override_settings.frame_step",
        # Output Path and Format
        "override_settings.output_path_override",
        "override_settings.output_directory",
        "override_settings.output_filename",
        # File Format Settings
        "override_settings.file_format_override",
        "override_settings.file_format",
        "override_settings.color_depth",
        "override_settings.codec",
        "override_settings.quality",
        # Resolution Settings
        "override_settings.format_override",
        "override_settings.resolution_override",
        "override_settings.resolution_mode",
        "override_settings.resolution_x",
        "override_settings.resolution_y",
        "override_settings.custom_render_scale",
        # Overscan Settings
        "override_settings.use_overscan",
        "override_settings.overscan_type",
        "override_settings.overscan_percent",
        "override_settings.overscan_percent_width",
        "override_settings.overscan_percent_height",
        "override_settings.overscan_width",
        "override_settings.overscan_height",
        # Motion Blur
        "override_settings.motion_blur_override",
        "override_settings.use_motion_blur",
        "override_settings.motion_blur_position",
        "override_settings.motion_blur_shutter",
        # Compositor Settings
        "override_settings.compositor_override",
        "override_settings.use_compositor",
        "override_settings.compositor_disable_output_files",
        "override_settings.compositor_device",
        # Camera Settings
        "override_settings.cameras_override",
        "override_settings.override_dof",
        "override_settings.use_dof",
        "override_settings.camera_shift_x",
        "override_settings.camera_shift_y",
        # Data
        "override_settings.use_data_path_overrides",
    ]
    preset_subdir = PRESET_REGISTRY["overrides_main"]

    def execute(self, context):
        result = super().execute(context)

        if result != {"FINISHED"} or getattr(self, "remove_active", False):
            return result

        _save_data_path_overrides_preset(context, self.name, self.preset_subdir)
        return {"FINISHED"}


class RECOM_OT_resolution_preset(AddPresetBase, Operator):
    bl_idname = "recom.resolution_preset_add"
    bl_label = "Add Resolution Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_resolution_presets"
    preset_defines = ["override_settings = bpy.context.window_manager.recom_render_settings.override_settings"]
    preset_values = [
        "override_settings.resolution_override",
        "override_settings.resolution_mode",
        "override_settings.resolution_x",
        "override_settings.resolution_y",
        "override_settings.custom_render_scale",
        "override_settings.use_overscan",
        "override_settings.overscan_type",
        "override_settings.overscan_percent",
        "override_settings.overscan_width",
    ]
    preset_subdir = PRESET_REGISTRY["resolution"]


class RECOM_OT_output_preset(AddPresetBase, Operator):
    bl_idname = "recom.output_preset_add"
    bl_label = "Add Output Path Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_output_presets"
    preset_defines = ["override_settings = bpy.context.window_manager.recom_render_settings.override_settings"]
    preset_values = [
        "override_settings.output_directory",
        "override_settings.output_filename",
    ]
    preset_subdir = PRESET_REGISTRY["output_path"]


class RECOM_OT_samples_preset(AddPresetBase, Operator):
    bl_idname = "recom.samples_preset_add"
    bl_label = "Add Samples Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_samples_presets"
    preset_defines = ["cycles = bpy.context.window_manager.recom_render_settings.override_settings.cycles"]
    preset_values = [
        "cycles.sampling_mode",
        "cycles.sampling_factor",
        "cycles.use_adaptive_sampling",
        "cycles.adaptive_threshold",
        "cycles.samples",
        "cycles.adaptive_min_samples",
        "cycles.time_limit",
        "cycles.use_denoising",
        "cycles.denoiser",
        "cycles.denoising_input_passes",
        "cycles.denoising_prefilter",
        "cycles.denoising_quality",
        "cycles.denoising_use_gpu",
    ]
    preset_subdir = PRESET_REGISTRY["cycles_samples"]


class RECOM_OT_override_advanced_properties_preset(AddPresetBase, Operator):
    bl_idname = "recom.override_advanced_properties_preset_add"
    bl_label = "Add Property Overrides Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_override_advanced_property_presets"
    preset_defines = ["override_settings = bpy.context.window_manager.recom_render_settings.override_settings"]
    preset_values = [
        "override_settings.use_data_path_overrides",
        "override_settings.data_path_overrides",
    ]
    preset_subdir = PRESET_REGISTRY["advanced_props"]

    def execute(self, context):
        result = super().execute(context)

        if result != {"FINISHED"} or getattr(self, "remove_active", False):
            return result

        _save_data_path_overrides_preset(context, self.name, self.preset_subdir)
        return {"FINISHED"}


class RECOM_OT_render_preferences_preset(AddPresetBase, Operator):
    bl_idname = "recom.render_preferences_preset_add"
    bl_label = "Add Render Preferences Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_render_preferences_presets"
    preset_defines = [
        f"addon_id = {ADDON_ID_DEFINE}",
        "prefs = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = [
        "prefs.auto_save_before_render",
        "prefs.write_still",
        "prefs.track_render_time",
        "prefs.keep_terminal_open",
        # Filename
        "prefs.default_render_filename",
        "prefs.filename_separator",
        "prefs.frame_length_digits",
        # Log to file
        "prefs.log_to_file",
        "prefs.log_to_file_location",
        "prefs.save_to_log_folder",
        "prefs.log_custom_path",
        # Command Line Args
        "prefs.add_command_line_args",
        "prefs.custom_command_line_args",
        # OCIO
        "prefs.set_ocio",
        "prefs.ocio_path",
        # Scripts
        "prefs.append_python_scripts",
        "prefs.additional_scripts",
        # Cycles
        "prefs.compute_device_type",
        "prefs.devices",
        "prefs.manage_cycles_devices",
        # Parallel Device
        "prefs.device_parallel",
        "prefs.frame_allocation",
        "prefs.multiple_backends",
        "prefs.combine_cpu_with_gpus",
        "prefs.cpu_threads_limit",
        # Multi-Process
        "prefs.multi_instance",
        "prefs.render_iterations",
        # Script Name
        "prefs.use_blend_name_in_script",
        "prefs.use_render_type_in_script",
        "prefs.use_export_date_in_script",
        "prefs.use_frame_range_in_script",
        "prefs.custom_script_tag",
        "prefs.custom_script_text",
    ]
    preset_subdir = PRESET_REGISTRY["render_prefs"]

    def execute(self, context):
        prefs = get_addon_preferences(context)

        if not prefs.manage_cycles_devices:
            exclude_if_disabled = [
                "prefs.compute_device_type",
                "prefs.devices",
            ]
            self.preset_values = [val for val in self.preset_values if val not in exclude_if_disabled]

        return super().execute(context)


class RECOM_OT_additional_script_preset(AddPresetBase, Operator):
    bl_idname = "recom.additional_script_preset_add"
    bl_label = "Add Additional Script Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_additional_script_presets"
    preset_defines = [
        f"addon_id = {ADDON_ID_DEFINE}",
        "prefs = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["prefs.additional_scripts"]
    preset_subdir = PRESET_REGISTRY["scripts"]


class RECOM_OT_command_line_arguments_preset(AddPresetBase, Operator):
    bl_idname = "recom.command_line_arguments_preset_add"
    bl_label = "Add Command Line Arguments Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_command_line_arguments_presets"
    preset_defines = [
        f"addon_id = {ADDON_ID_DEFINE}",
        "prefs = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["prefs.custom_command_line_args"]
    preset_subdir = PRESET_REGISTRY["cmd_args"]


class RECOM_OT_custom_variables_preset(AddPresetBase, Operator):
    bl_idname = "recom.custom_variables_preset_add"
    bl_label = "Add Custom Variables Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_custom_variables_presets"
    preset_defines = [
        f"addon_id = {ADDON_ID_DEFINE}",
        "prefs = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["prefs.custom_variables"]
    preset_subdir = PRESET_REGISTRY["custom_variables"]


classes = (
    RECOM_OT_overrides_preset,
    RECOM_OT_resolution_preset,
    RECOM_OT_samples_preset,
    RECOM_OT_output_preset,
    RECOM_OT_custom_variables_preset,
    RECOM_OT_override_advanced_properties_preset,
    RECOM_OT_render_preferences_preset,
    RECOM_OT_additional_script_preset,
    RECOM_OT_command_line_arguments_preset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
