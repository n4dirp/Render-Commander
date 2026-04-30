import logging
from pathlib import Path

import bpy
from bl_operators.presets import AddPresetBase
from bpy.types import Operator

from .. import __package__ as base_package

log = logging.getLogger(__name__)

BASE_NAME = base_package.split(".")[-1]

PRESET_REGISTRY = {
    # Overrides
    "overrides_main": "recom/overrides_main",
    "resolution": "recom/resolution",
    "cycles_samples": "recom/cycles_samples",
    "output_path": "recom/output_path",
    "custom_variables": "recom/custom_variables",
    "advanced_props": "recom/advanced_props",
    # Preferences
    "render_prefs": "recom/render_prefs",
    "cmd_args": "recom/cmd_args",
    "ocio": "recom/ocio",
    "scripts": "recom/scripts",
}

PROP_TYPE_ATTR_MAP = {
    "BOOL": "value_bool",
    "INT": "value_int",
    "FLOAT": "value_float",
    "STRING": "value_string",
    "VECTOR_3": "value_vector_3",
    "COLOR_4": "value_color_4",
}


def _save_data_path_overrides_preset(context, name, preset_subdir):
    """Helper to write data_path_overrides to a preset python file."""
    clean_name = bpy.path.clean_name(name.strip())
    subdir_path = Path("presets") / preset_subdir
    target_dir = Path(bpy.utils.user_resource("SCRIPTS", path=str(subdir_path), create=True))
    filepath = target_dir / f"{clean_name}.py"

    if not filepath.exists():
        return

    settings = context.window_manager.recom_render_settings.override_settings
    lines = [
        "\n# Custom API Overrides Collection",
        "settings.override_settings.data_path_overrides.clear()",
    ]

    for item in settings.data_path_overrides:
        lines.append("item = settings.override_settings.data_path_overrides.add()")
        lines.append(f"item.name = {repr(item.name)}")
        lines.append(f"item.data_path = {repr(item.data_path)}")
        lines.append(f"item.prop_type = {repr(item.prop_type)}")

        attr = PROP_TYPE_ATTR_MAP.get(item.prop_type)
        if attr:
            val = getattr(item, attr)
            if item.prop_type in ("VECTOR_3", "COLOR_4"):
                val = list(val)
            lines.append(f"item.{attr} = {repr(val)}")

    lines.append(f"settings.override_settings.active_data_path_index = {settings.active_data_path_index}")

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
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        # Cycles Sampling Overrides
        "settings.override_settings.cycles.sampling_override",
        "settings.override_settings.cycles.sampling_mode",
        "settings.override_settings.cycles.sampling_factor",
        "settings.override_settings.cycles.samples",
        "settings.override_settings.cycles.adaptive_min_samples",
        "settings.override_settings.cycles.time_limit",
        "settings.override_settings.cycles.use_adaptive_sampling",
        "settings.override_settings.cycles.adaptive_threshold",
        # Cycles Denoising Settings
        "settings.override_settings.cycles.denoising_override",
        "settings.override_settings.cycles.use_denoising",
        "settings.override_settings.cycles.denoiser",
        "settings.override_settings.cycles.denoising_input_passes",
        "settings.override_settings.cycles.denoising_prefilter",
        "settings.override_settings.cycles.denoising_quality",
        "settings.override_settings.cycles.denoising_use_gpu",
        # Cycles Performance
        "settings.override_settings.cycles.device_override",
        "settings.override_settings.cycles.device",
        "settings.override_settings.cycles.performance_override",
        "settings.override_settings.cycles.use_tiling",
        "settings.override_settings.cycles.tile_size",
        "settings.override_settings.cycles.use_spatial_splits",
        "settings.override_settings.cycles.use_compact_bvh",
        "settings.override_settings.cycles.persistent_data",
        # EEVEE
        "settings.override_settings.eevee_override",
        "settings.override_settings.eevee.samples",
        # Frame Range Settings
        "settings.override_settings.frame_range_override",
        "settings.override_settings.frame_current",
        "settings.override_settings.frame_start",
        "settings.override_settings.frame_end",
        "settings.override_settings.frame_step",
        # Output Path and Format
        "settings.override_settings.output_path_override",
        "settings.override_settings.output_directory",
        "settings.override_settings.output_filename",
        # File Format Settings
        "settings.override_settings.file_format_override",
        "settings.override_settings.file_format",
        "settings.override_settings.color_depth",
        "settings.override_settings.codec",
        "settings.override_settings.jpeg_quality",
        # Resolution Settings
        "settings.override_settings.format_override",
        "settings.override_settings.resolution_override",
        "settings.override_settings.resolution_mode",
        "settings.override_settings.resolution_x",
        "settings.override_settings.resolution_y",
        "settings.override_settings.custom_render_scale",
        # Overscan Settings
        "settings.override_settings.use_overscan",
        "settings.override_settings.overscan_type",
        "settings.override_settings.overscan_percent",
        "settings.override_settings.overscan_width",
        # Motion Blur
        "settings.override_settings.motion_blur_override",
        "settings.override_settings.use_motion_blur",
        "settings.override_settings.motion_blur_position",
        "settings.override_settings.motion_blur_shutter",
        # Compositor Settings
        "settings.override_settings.compositor_override",
        "settings.override_settings.use_compositor",
        "settings.override_settings.compositor_disable_output_files",
        "settings.override_settings.compositor_device",
        # Camera Settings
        "settings.override_settings.cameras_override",
        "settings.override_settings.override_dof",
        "settings.override_settings.use_dof",
        "settings.override_settings.camera_shift_x",
        "settings.override_settings.camera_shift_y",
        # Data
        "settings.override_settings.use_data_path_overrides",
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
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.resolution_override",
        "settings.override_settings.resolution_mode",
        "settings.override_settings.resolution_x",
        "settings.override_settings.resolution_y",
        "settings.override_settings.custom_render_scale",
        "settings.override_settings.use_overscan",
        "settings.override_settings.overscan_type",
        "settings.override_settings.overscan_percent",
        "settings.override_settings.overscan_width",
    ]
    preset_subdir = PRESET_REGISTRY["resolution"]


class RECOM_OT_output_preset(AddPresetBase, Operator):
    bl_idname = "recom.output_preset_add"
    bl_label = "Add Output Path Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_output_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.output_directory",
        "settings.override_settings.output_filename",
    ]
    preset_subdir = PRESET_REGISTRY["output_path"]


class RECOM_OT_samples_preset(AddPresetBase, Operator):
    bl_idname = "recom.samples_preset_add"
    bl_label = "Add Samples Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_samples_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.cycles.sampling_mode",
        "settings.override_settings.cycles.sampling_factor",
        "settings.override_settings.cycles.use_adaptive_sampling",
        "settings.override_settings.cycles.adaptive_threshold",
        "settings.override_settings.cycles.samples",
        "settings.override_settings.cycles.adaptive_min_samples",
        "settings.override_settings.cycles.time_limit",
        "settings.override_settings.cycles.use_denoising",
        "settings.override_settings.cycles.denoiser",
        "settings.override_settings.cycles.denoising_input_passes",
        "settings.override_settings.cycles.denoising_prefilter",
        "settings.override_settings.cycles.denoising_quality",
        "settings.override_settings.cycles.denoising_use_gpu",
    ]
    preset_subdir = PRESET_REGISTRY["cycles_samples"]


class RECOM_OT_override_advanced_properties_preset(AddPresetBase, Operator):
    bl_idname = "recom.override_advanced_properties_preset_add"
    bl_label = "Add Property Overrides Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_override_advanced_property_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.use_data_path_overrides",
        "settings.override_settings.data_path_overrides",
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
        f"addon_id = next((ext.module for ext in bpy.context.preferences.addons if ext.module.endswith('{BASE_NAME}')), '{BASE_NAME}')",
        "settings = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = [
        "settings.auto_save_before_render",
        "settings.write_still",
        "settings.track_render_time",
        "settings.keep_terminal_open",
        # Filename
        "settings.default_render_filename",
        "settings.filename_separator",
        "settings.frame_length_digits",
        # Log to file
        "settings.log_to_file",
        "settings.log_to_file_location",
        "settings.save_to_log_folder",
        "settings.log_custom_path",
        # Command Line Args
        "settings.add_command_line_args",
        "settings.custom_command_line_args",
        # OCIO
        "settings.set_ocio",
        "settings.ocio_path",
        # Scripts
        "settings.append_python_scripts",
        "settings.additional_scripts",
        # Cycles
        "settings.compute_device_type",
        "settings.devices",
        "settings.manage_cycles_devices",
        # Parallel Device
        "settings.device_parallel",
        "settings.frame_allocation",
        "settings.multiple_backends",
        "settings.combine_cpu_with_gpus",
        "settings.cpu_threads_limit",
        # Multi-Process
        "settings.multi_instance",
        "settings.render_iterations",
        # Export Scripts
        "settings.auto_open_exported_folder",
        "settings.export_output_target",
        "settings.custom_export_path",
        "settings.export_scripts_subfolder",
        "settings.export_scripts_folder_name",
        # Script Name
        "settings.use_blend_name_in_script",
        "settings.use_render_type_in_script",
        "settings.use_export_date_in_script",
        "settings.use_frame_range_in_script",
        "settings.custom_script_tag",
        "settings.custom_script_text",
    ]
    preset_subdir = PRESET_REGISTRY["render_prefs"]

    def execute(self, context):
        # Get current settings
        settings = bpy.context.preferences.addons[base_package].preferences

        # If manage_cycles_devices is False, exclude device-related settings
        if not settings.manage_cycles_devices:
            # Create filtered list excluding device settings
            exclude_if_disabled = [
                "settings.compute_device_type",
                "settings.devices",
            ]
            self.preset_values = [val for val in self.preset_values if val not in exclude_if_disabled]

        return super().execute(context)


class RECOM_OT_additional_script_preset(AddPresetBase, Operator):
    bl_idname = "recom.additional_script_preset_add"
    bl_label = "Add Additional Script Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_additional_script_presets"
    preset_defines = [
        f"addon_id = next((ext.module for ext in bpy.context.preferences.addons if ext.module.endswith('{BASE_NAME}')), '{BASE_NAME}')",
        "settings = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["settings.additional_scripts"]
    preset_subdir = PRESET_REGISTRY["scripts"]


class RECOM_OT_ocio_preset(AddPresetBase, Operator):
    bl_idname = "recom.ocio_preset_add"
    bl_label = "Add OCIO Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_ocio_presets"
    preset_defines = [
        f"addon_id = next((ext.module for ext in bpy.context.preferences.addons if ext.module.endswith('{BASE_NAME}')), '{BASE_NAME}')",
        "settings = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["settings.ocio_path"]
    preset_subdir = PRESET_REGISTRY["ocio"]


class RECOM_OT_command_line_arguments_preset(AddPresetBase, Operator):
    bl_idname = "recom.command_line_arguments_preset_add"
    bl_label = "Add Command Line Arguments Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_command_line_arguments_presets"
    preset_defines = [
        f"addon_id = next((ext.module for ext in bpy.context.preferences.addons if ext.module.endswith('{BASE_NAME}')), '{BASE_NAME}')",
        "settings = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["settings.custom_command_line_args"]
    preset_subdir = PRESET_REGISTRY["cmd_args"]


class RECOM_OT_custom_variables_preset(AddPresetBase, Operator):
    bl_idname = "recom.custom_variables_preset_add"
    bl_label = "Add Custom Variables Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_custom_variables_presets"

    preset_defines = [
        f"addon_id = next((ext.module for ext in bpy.context.preferences.addons if ext.module.endswith('{BASE_NAME}')), '{BASE_NAME}')",
        "settings = bpy.context.preferences.addons[addon_id].preferences",
    ]
    preset_values = ["settings.custom_variables"]
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
    RECOM_OT_ocio_preset,
    RECOM_OT_command_line_arguments_preset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
