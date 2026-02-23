# ./operators/presets_settings.py

from pathlib import Path

import bpy
from bpy.types import Operator
from bl_operators.presets import AddPresetBase

from .. import __package__ as base_package
from ..utils.constants import ADDON_NAME


class RECOM_OT_overrides_preset(AddPresetBase, Operator):
    bl_idname = "recom.overrides_preset_add"
    bl_label = "Add Overrides Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_overrides_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        # Cycles Sampling Overrides
        "settings.override_settings.cycles.sampling_override",
        "settings.override_settings.cycles.samples",
        "settings.override_settings.cycles.adaptive_min_samples",
        "settings.override_settings.cycles.time_limit",
        "settings.override_settings.cycles.use_adaptive_sampling",
        "settings.override_settings.cycles.adaptive_threshold",
        # Cycles Denoising Settings
        "settings.override_settings.cycles.use_denoising",
        "settings.override_settings.cycles.denoiser",
        "settings.override_settings.cycles.denoising_input_passes",
        "settings.override_settings.cycles.denoising_prefilter",
        "settings.override_settings.cycles.denoising_quality",
        "settings.override_settings.cycles.denoising_use_gpu",
        "settings.override_settings.cycles.denoising_store_passes",
        # Cycles Light Paths
        "settings.override_settings.cycles.light_path_override",
        "settings.override_settings.cycles.max_bounces",
        "settings.override_settings.cycles.diffuse_bounces",
        "settings.override_settings.cycles.glossy_bounces",
        "settings.override_settings.cycles.transmission_bounces",
        "settings.override_settings.cycles.volume_bounces",
        "settings.override_settings.cycles.transparent_bounces",
        "settings.override_settings.cycles.sample_clamp_direct",
        "settings.override_settings.cycles.sample_clamp_indirect",
        "settings.override_settings.cycles.caustics_reflective",
        "settings.override_settings.cycles.caustics_refractive",
        "settings.override_settings.cycles.blur_glossy",
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
        "settings.override_settings.eevee.use_shadows",
        "settings.override_settings.eevee.shadow_ray_count",
        "settings.override_settings.eevee.shadow_step_count",
        "settings.override_settings.eevee.use_raytracing",
        "settings.override_settings.eevee.ray_tracing_method",
        "settings.override_settings.eevee.ray_tracing_resolution",
        "settings.override_settings.eevee.ray_tracing_denoise",
        "settings.override_settings.eevee.ray_tracing_denoise_temporal",
        "settings.override_settings.eevee.fast_gi",
        "settings.override_settings.eevee.trace_max_roughness",
        "settings.override_settings.eevee.fast_gi_resolution",
        "settings.override_settings.eevee.fast_gi_step_count",
        "settings.override_settings.eevee.fast_gi_distance",
        "settings.override_settings.eevee.volumetric_tile_size",
        "settings.override_settings.eevee.volume_samples",
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
        # "settings.override_settings.render_scale",
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
    ]
    preset_subdir = Path(ADDON_NAME) / "override_settings"


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
        "settings.override_settings.render_scale",
        "settings.override_settings.custom_render_scale",
        "settings.override_settings.use_overscan",
        "settings.override_settings.overscan_type",
        "settings.override_settings.overscan_percent",
        "settings.override_settings.overscan_width",
    ]
    preset_subdir = Path(ADDON_NAME) / "resolution"


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
    preset_subdir = Path(ADDON_NAME) / "output_path"


class RECOM_OT_samples_preset(AddPresetBase, Operator):
    bl_idname = "recom.samples_preset_add"
    bl_label = "Add Samples Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_samples_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
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
        "settings.override_settings.cycles.denoising_store_passes",
    ]
    preset_subdir = Path(ADDON_NAME) / "samples"


class RECOM_OT_light_paths_preset(AddPresetBase, Operator):
    bl_idname = "recom.light_paths_preset_add"
    bl_label = "Add Light Paths Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_light_paths_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.cycles.max_bounces",
        "settings.override_settings.cycles.diffuse_bounces",
        "settings.override_settings.cycles.glossy_bounces",
        "settings.override_settings.cycles.transmission_bounces",
        "settings.override_settings.cycles.volume_bounces",
        "settings.override_settings.cycles.transparent_bounces",
        "settings.override_settings.cycles.sample_clamp_direct",
        "settings.override_settings.cycles.sample_clamp_indirect",
        "settings.override_settings.cycles.caustics_reflective",
        "settings.override_settings.cycles.caustics_refractive",
        "settings.override_settings.cycles.blur_glossy",
    ]
    preset_subdir = Path(ADDON_NAME) / "light_paths"


class RECOM_OT_eevee_settings_preset(AddPresetBase, Operator):
    bl_idname = "recom.eevee_preset_add"
    bl_label = "Add EEVEE Settings Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_eevee_settings_presets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.eevee.samples",
        "settings.override_settings.eevee.use_shadows",
        "settings.override_settings.eevee.shadow_ray_count",
        "settings.override_settings.eevee.shadow_step_count",
        "settings.override_settings.eevee.use_raytracing",
        "settings.override_settings.eevee.ray_tracing_method",
        "settings.override_settings.eevee.ray_tracing_resolution",
        "settings.override_settings.eevee.ray_tracing_denoise",
        "settings.override_settings.eevee.ray_tracing_denoise_temporal",
        "settings.override_settings.eevee.fast_gi",
        "settings.override_settings.eevee.trace_max_roughness",
        "settings.override_settings.eevee.fast_gi_resolution",
        "settings.override_settings.eevee.fast_gi_step_count",
        "settings.override_settings.eevee.fast_gi_distance",
        "settings.override_settings.eevee.volumetric_tile_size",
        "settings.override_settings.eevee.volume_samples",
    ]
    preset_subdir = Path(ADDON_NAME) / "eevee"


class RECOM_OT_render_preferences_preset(AddPresetBase, Operator):
    bl_idname = "recom.render_preferences_preset_add"
    bl_label = "Add Render Preferences Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_render_preferences_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = [
        "settings.auto_save_before_render",
        "settings.write_still",
        "settings.send_desktop_notifications",
        "settings.auto_open_output_folder",
        "settings.exit_active_session",
        "settings.keep_terminal_open",
        # Filename
        "settings.default_render_filename",
        "settings.filename_separator",
        "settings.frame_length_digits",
        # Power
        "settings.set_system_power",
        "settings.prevent_sleep",
        "settings.prevent_monitor_off",
        "settings.shutdown_after_render",
        "settings.shutdown_type",
        "settings.shutdown_delay",
        # Log to file
        "settings.log_to_file",
        "settings.log_to_file_location",
        "settings.save_to_log_folder",
        "settings.log_custom_path",
        # Command Line Args
        "settings.add_command_line_args",
        "settings.custom_command_line_args",
        # Debugging
        "settings.debug_mode",
        "settings.debug_value",
        "settings.verbose_level",
        "settings.debug_cycles",
        # Executable
        "settings.blender_executable_source",
        "settings.custom_executable_path",
        # OCIO
        "settings.set_ocio",
        "settings.ocio_path",
        # Scripts
        "settings.append_python_scripts",
        "settings.additional_scripts",
        # Parallel Device
        "settings.device_parallel",
        "settings.parallel_delay",
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
        "settings.export_master_script",
        "settings.scripts_directory",
        "settings.export_scripts_subfolder",
        "settings.export_scripts_folder_name",
        # Notifications
        "settings.send_desktop_notifications",
        "settings.notification_detail_level",
        # Power Management
        "settings.set_system_power",
        "settings.prevent_sleep",
        "settings.prevent_monitor_off",
        "settings.shutdown_after_render",
        "settings.shutdown_type",
        "settings.shutdown_delay",
    ]
    preset_subdir = Path(ADDON_NAME) / "render_preferences"


class RECOM_OT_blender_executable_preset(AddPresetBase, Operator):
    bl_idname = "recom.blender_executable_preset_add"
    bl_label = "Add Blender Executable Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_blender_executable_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = [
        "settings.blender_executable_source",
        "settings.custom_executable_path",
    ]
    preset_subdir = Path(ADDON_NAME) / "custom_executable"


class RECOM_OT_additional_script_preset(AddPresetBase, Operator):
    bl_idname = "recom.additional_script_preset_add"
    bl_label = "Add Additional Script Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_additional_script_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.additional_scripts"]
    preset_subdir = Path(ADDON_NAME) / "additional_scripts"


class RECOM_OT_ocio_preset(AddPresetBase, Operator):
    bl_idname = "recom.ocio_preset_add"
    bl_label = "Add OCIO Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_ocio_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.ocio_path"]
    preset_subdir = Path(ADDON_NAME) / "ocio"


class RECOM_OT_command_line_arguments_preset(AddPresetBase, Operator):
    bl_idname = "recom.command_line_arguments_preset_add"
    bl_label = "Add Command Line Arguments Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_command_line_arguments_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.custom_command_line_args"]
    preset_subdir = Path(ADDON_NAME) / "command_line_arguments"


class RECOM_OT_custom_variables_preset(AddPresetBase, Operator):
    bl_idname = "recom.custom_variables_preset_add"
    bl_label = "Add Custom Variables Preset"
    bl_description = "Add or remove a preset"
    preset_menu = "RECOM_PT_custom_variables_presets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.custom_variables"]
    preset_subdir = Path(ADDON_NAME) / "custom_variables"


classes = (
    RECOM_OT_overrides_preset,
    RECOM_OT_resolution_preset,
    RECOM_OT_samples_preset,
    RECOM_OT_light_paths_preset,
    RECOM_OT_eevee_settings_preset,
    RECOM_OT_output_preset,
    RECOM_OT_custom_variables_preset,
    RECOM_OT_render_preferences_preset,
    RECOM_OT_blender_executable_preset,
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
