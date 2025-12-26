# ./operators/presets_settings.py

from pathlib import Path

import bpy
from bpy.types import Operator
from bl_operators.presets import AddPresetBase

from .. import __package__ as base_package
from ..utils.constants import ADDON_NAME


class RECOM_OT_AddOverridesPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_overrides_preset"
    bl_label = "Add Overrides Preset"
    preset_menu = "RECOM_PT_OverridesPresets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.cycles.sampling_override",
        "settings.override_settings.cycles.samples",
        "settings.override_settings.cycles.adaptive_min_samples",
        "settings.override_settings.cycles.time_limit",
        "settings.override_settings.cycles.use_adaptive_sampling",
        "settings.override_settings.cycles.adaptive_threshold",
        #
        "settings.override_settings.cycles.use_denoising",
        "settings.override_settings.cycles.denoiser",
        "settings.override_settings.cycles.denoising_input_passes",
        "settings.override_settings.cycles.denoising_prefilter",
        "settings.override_settings.cycles.denoising_quality",
        "settings.override_settings.cycles.denoising_use_gpu",
        "settings.override_settings.cycles.denoising_store_passes",
        #
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
        #
        "settings.override_settings.cycles.device_override",
        "settings.override_settings.cycles.device",
        "settings.override_settings.cycles.performance_override",
        "settings.override_settings.cycles.use_tiling",
        "settings.override_settings.cycles.tile_size",
        "settings.override_settings.cycles.use_spatial_splits",
        "settings.override_settings.cycles.use_compact_bvh",
        "settings.override_settings.cycles.persistent_data",
        #
        "settings.override_settings.frame_range_override",
        "settings.override_settings.frame_current",
        "settings.override_settings.frame_start",
        "settings.override_settings.frame_end",
        "settings.override_settings.frame_step",
        #
        "settings.override_settings.output_path_override",
        "settings.override_settings.output_directory",
        "settings.override_settings.output_filename",
        #
        "settings.override_settings.file_format_override",
        "settings.override_settings.file_format",
        "settings.override_settings.color_depth",
        "settings.override_settings.codec",
        "settings.override_settings.jpeg_quality",
        #
        "settings.override_settings.format_override",
        #
        "settings.override_settings.resolution_override",
        "settings.override_settings.resolution_mode",
        "settings.override_settings.resolution_x",
        "settings.override_settings.resolution_y",
        "settings.override_settings.render_scale",
        "settings.override_settings.custom_render_scale",
        #
        "settings.override_settings.use_overscan",
        "settings.override_settings.overscan_type",
        "settings.override_settings.overscan_percent",
        "settings.override_settings.overscan_width",
        #
        "settings.override_settings.camera_shift_override",
        "settings.override_settings.camera_shift_x",
        "settings.override_settings.camera_shift_y",
        #
        "settings.override_settings.motion_blur_override",
        "settings.override_settings.use_motion_blur",
        "settings.override_settings.motion_blur_position",
        "settings.override_settings.motion_blur_shutter",
        #
        "settings.override_settings.compositor_override",
        "settings.override_settings.use_compositor",
        "settings.override_settings.compositor_disable_output_files",
        "settings.override_settings.compositor_device",
        #
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
    ]
    preset_subdir = Path(ADDON_NAME) / "override_settings"


class RECOM_OT_AddResolutionPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_resolution_preset"
    bl_label = "Add Resolution Preset"
    preset_menu = "RECOM_PT_ResolutionPresets"
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


class RECOM_OT_AddSamplesPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_samples_preset"
    bl_label = "Add Samples Preset"
    preset_menu = "RECOM_PT_SamplesPresets"
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


class RECOM_OT_AddLightPathsPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_light_paths_preset"
    bl_label = "Add Light Paths Preset"
    preset_menu = "RECOM_PT_LightPathsPresets"
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


class RECOM_OT_AddOutputPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_output_preset"
    bl_label = "Add Output Path Preset"
    preset_menu = "RECOM_PT_OutputPresets"
    preset_defines = ["settings = bpy.context.window_manager.recom_render_settings"]
    preset_values = [
        "settings.override_settings.output_directory",
        "settings.override_settings.output_filename",
    ]
    preset_subdir = Path(ADDON_NAME) / "output_path"


class RECOM_OT_AddEEVEESettingsPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_eevee_preset"
    bl_label = "Add EEVEE Settings Preset"
    preset_menu = "RECOM_PT_EEVEESettingsPresets"
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


class RECOM_OT_AddRenderPreferencesPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_render_preferences_preset"
    bl_label = "Add Render Preferences Preset"
    preset_menu = "RECOM_PT_RenderPreferencesPresets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = [
        "settings.auto_save_before_render",
        "settings.auto_open_output_folder",
        "settings.send_desktop_notifications",
        "settings.write_still",
        #
        "settings.default_render_filename",
        "settings.filename_separator",
        "settings.frame_length_digits",
        #
        "settings.set_system_power",
        "settings.prevent_sleep",
        "settings.prevent_monitor_off",
        "settings.shutdown_after_render",
        "settings.shutdown_type",
        "settings.shutdown_delay",
        #
        "settings.log_to_file",
        "settings.log_to_file_location",
        "settings.save_to_log_folder",
        "settings.log_custom_path",
        #
        "settings.external_terminal",
        "settings.keep_terminal_open",
        "settings.exit_active_session",
        #
        "settings.custom_executable",
        "settings.custom_executable_path",
        #
        "settings.set_ocio",
        "settings.ocio_path",
        #
        "settings.append_python_scripts",
        "settings.additional_scripts",
        #
        "settings.device_parallel",
        "settings.parallel_delay",
        "settings.frame_allocation",
        "settings.multiple_backends",
        #
        "settings.combine_cpu_with_gpus",
        "settings.cpu_threads_limit",
    ]
    preset_subdir = Path(ADDON_NAME) / "render_preferences"


class RECOM_OT_AddCustomExecPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_custom_exec_preset"
    bl_label = "Add Custom Executable Preset"
    preset_menu = "RECOM_PT_CustomExecPresets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = [
        "settings.custom_executable_path",
    ]
    preset_subdir = Path(ADDON_NAME) / "custom_executable"


class RECOM_OT_AddAdditionalScriptPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_additional_script_preset"
    bl_label = "Add Additional Script Preset"
    preset_menu = "RECOM_PT_AdditionalScriptPresets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.additional_scripts"]
    preset_subdir = Path(ADDON_NAME) / "additional_scripts"


class RECOM_OT_AddOCIOPreset(AddPresetBase, Operator):
    bl_idname = "recom.add_ocio_preset"
    bl_label = "Add OCIO Preset"
    preset_menu = "RECOM_PT_OCIOPresets"
    preset_defines = [f"settings = bpy.context.preferences.addons['{base_package}'].preferences"]
    preset_values = ["settings.ocio_path"]
    preset_subdir = Path(ADDON_NAME) / "ocio"


classes = (
    RECOM_OT_AddOverridesPreset,
    RECOM_OT_AddResolutionPreset,
    RECOM_OT_AddSamplesPreset,
    RECOM_OT_AddLightPathsPreset,
    RECOM_OT_AddEEVEESettingsPreset,
    RECOM_OT_AddOutputPreset,
    RECOM_OT_AddRenderPreferencesPreset,
    RECOM_OT_AddCustomExecPreset,
    RECOM_OT_AddAdditionalScriptPreset,
    RECOM_OT_AddOCIOPreset,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
