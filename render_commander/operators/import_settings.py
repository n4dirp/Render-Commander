# ./operators/import_settings.py

import os
import json
import logging
from pathlib import Path

import bpy
from bpy.types import Operator

from ..utils.constants import ADDON_NAME
from ..preferences import get_addon_preferences

log = logging.getLogger(__name__)


class RECOM_OT_ImportAllSettings(bpy.types.Operator):
    """Import selected property values from the current scene / external blend"""

    bl_idname = "recom.import_all_settings"
    bl_label = "Import Scene Values"

    def execute(self, context):
        try:
            prefs = get_addon_preferences(context)
            overrides = prefs.override_settings

            if overrides.import_compute_device:
                self._import_compute_device(context)
            if overrides.import_frame_range:
                self._import_frame_range(context)
            if overrides.import_resolution:
                self._import_manual_resolution(context)
            if overrides.import_sampling:
                self._import_sampling(context)
            if overrides.import_light_paths:
                self._import_light_paths(context)
            if overrides.import_eevee_settings:
                self._import_eevee_settings(context)
            if overrides.import_motion_blur:
                self._import_motion_blur(context)
            if overrides.import_output_path:
                self._import_output_path(context)
            if overrides.import_output_format:
                self._import_output_format(context)
            if overrides.import_performance:
                self._import_performance(context)
            if overrides.import_compositor:
                self._import_compositor(context)

            context.area.tag_redraw()
        except Exception as exc:
            log.error(f"ImportAllSettings failed: {exc}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import settings: {exc}")
            return {"CANCELLED"}

        self.report({"INFO"}, "Scene Settings imported")
        return {"FINISHED"}

    def _import_compute_device(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings
            cycles = override_settings.cycles

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    cycles.device = str(info.get("cycles_device", "CPU"))
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error syncing compute device: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                cycles.device = str(scene.cycles.device)

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportComputeDevice: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import compute device: {str(e)}")
            return {"CANCELLED"}

    def _import_frame_range(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    override_settings.frame_current = info.get("frame_current", 1)
                    override_settings.frame_start = info.get("frame_start", 1)
                    override_settings.frame_end = info.get("frame_end", 250)
                    override_settings.frame_step = info.get("frame_step", 1)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing frame range: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                override_settings.frame_current = scene.frame_current
                override_settings.frame_start = scene.frame_start
                override_settings.frame_end = scene.frame_end
                override_settings.frame_step = scene.frame_step

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportFrameRange: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import frame range: {str(e)}")
            return {"CANCELLED"}

    def _import_manual_resolution(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            enum_scale_map = {
                "4.00": 400,
                "3.00": 300,
                "2.00": 200,
                "1.50": 150,
                "1.00": 100,
                "0.6667": 67,
                "0.50": 50,
                "0.3333": 33,
                "0.25": 25,
            }

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    override_settings.resolution_x = info.get("resolution_x", 1920)
                    override_settings.resolution_y = info.get("resolution_y", 1080)
                    current_percentage = info.get("render_scale", 100)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing resolution: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                override_settings.resolution_x = scene.render.resolution_x
                override_settings.resolution_y = scene.render.resolution_y
                current_percentage = scene.render.resolution_percentage

            matched_scale = None
            for scale_str, percentage in enum_scale_map.items():
                if percentage == current_percentage:
                    matched_scale = scale_str
                    break

            if matched_scale:
                override_settings.render_scale = matched_scale
            else:
                override_settings.render_scale = "CUSTOM"
                override_settings.custom_render_scale = current_percentage

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportManualResolution: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import resolution: {str(e)}")
            return {"CANCELLED"}

    def _import_sampling(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings
            cycles = override_settings.cycles

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    cycles.use_adaptive_sampling = info.get("use_adaptive_sampling", True)
                    cycles.adaptive_threshold = info.get("adaptive_threshold", 0.01)
                    cycles.samples = info.get("samples", 4096)
                    cycles.adaptive_min_samples = info.get("adaptive_min_samples", 0)
                    cycles.time_limit = info.get("time_limit", 0.0)
                    cycles.use_denoising = info.get("use_denoising", False)
                    cycles.denoiser = info.get("denoiser", "OPENIMAGEDENOISE")
                    cycles.denoising_input_passes = info.get("denoising_input_passes", "RGB_ALBEDO_NORMAL")
                    cycles.denoising_prefilter = info.get("denoising_prefilter", "ACCURATE")
                    cycles.denoising_quality = info.get("denoising_quality", "HIGH")
                    cycles.denoising_use_gpu = info.get("denoising_use_gpu", False)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing sampling: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                cycles.use_adaptive_sampling = scene.cycles.use_adaptive_sampling
                cycles.adaptive_threshold = scene.cycles.adaptive_threshold
                cycles.samples = scene.cycles.samples
                cycles.adaptive_min_samples = scene.cycles.adaptive_min_samples
                cycles.time_limit = scene.cycles.time_limit
                cycles.use_denoising = scene.cycles.use_denoising
                cycles.denoiser = scene.cycles.denoiser
                cycles.denoising_input_passes = scene.cycles.denoising_input_passes
                cycles.denoising_prefilter = scene.cycles.denoising_prefilter
                cycles.denoising_quality = scene.cycles.denoising_quality
                cycles.denoising_use_gpu = scene.cycles.denoising_use_gpu

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportSampling: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import sampling: {str(e)}")
            return {"CANCELLED"}

    def _import_light_paths(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings
            cycles = override_settings.cycles

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    cycles.max_bounces = info.get("max_bounces", 12)
                    cycles.diffuse_bounces = info.get("diffuse_bounces", 4)
                    cycles.glossy_bounces = info.get("glossy_bounces", 4)
                    cycles.transmission_bounces = info.get("transmission_bounces", 12)
                    cycles.volume_bounces = info.get("volume_bounces", 0)
                    cycles.transparent_bounces = info.get("transparent_bounces", 8)
                    cycles.sample_clamp_direct = info.get("sample_clamp_direct", 0)
                    cycles.sample_clamp_indirect = info.get("sample_clamp_indirect", 10)
                    cycles.blur_glossy = info.get("blur_glossy", 1.0)
                    cycles.caustics_reflective = info.get("caustics_reflective", True)
                    cycles.caustics_refractive = info.get("caustics_refractive", True)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing light paths: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                cycles.max_bounces = scene.cycles.max_bounces
                cycles.diffuse_bounces = scene.cycles.diffuse_bounces
                cycles.glossy_bounces = scene.cycles.glossy_bounces
                cycles.transmission_bounces = scene.cycles.transmission_bounces
                cycles.volume_bounces = scene.cycles.volume_bounces
                cycles.transparent_bounces = scene.cycles.transparent_max_bounces
                cycles.sample_clamp_direct = scene.cycles.sample_clamp_direct
                cycles.sample_clamp_indirect = scene.cycles.sample_clamp_indirect
                cycles.blur_glossy = scene.cycles.blur_glossy
                cycles.caustics_reflective = scene.cycles.caustics_reflective
                cycles.caustics_refractive = scene.cycles.caustics_refractive

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportLightPaths: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import light paths: {str(e)}")
            return {"CANCELLED"}

    def _import_eevee_settings(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings
            eevee = override_settings.eevee

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")

                    eevee.samples = info.get("eevee_samples", 64)

                    eevee.use_shadows = info.get("eevee_use_shadows", True)
                    eevee.shadow_ray_count = info.get("eevee_shadow_ray_count", 1)
                    eevee.shadow_step_count = info.get("eevee_shadow_step_count", 6)

                    eevee.use_raytracing = info.get("eevee_use_raytracing", True)
                    eevee.ray_tracing_method = info.get("eevee_ray_tracing_method", "SCREEN")
                    eevee.ray_tracing_resolution = info.get("eevee_ray_tracing_resolution", "2")

                    eevee.ray_tracing_denoise = info.get("eevee_ray_tracing_denoise", True)
                    eevee.ray_tracing_denoise_temporal = info.get("eevee_ray_tracing_denoise_temporal", True)

                    eevee.fast_gi = info.get("eevee_fast_gi", True)
                    eevee.trace_max_roughness = info.get("eevee_trace_max_roughness", 0.50)
                    eevee.fast_gi_resolution = info.get("fast_gi_resolution", "2")
                    eevee.fast_gi_step_count = info.get("fast_gi_step_count", 8)
                    eevee.fast_gi_distance = info.get("fast_gi_distance", 0)

                    eevee.volumetric_tile_size = info.get("eevee_volumetric_tile_size", "8")
                    eevee.volume_samples = info.get("eevee_volume_samples", 64)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing EEVEE settings: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                eevee.samples = scene.eevee.taa_render_samples

                eevee.use_shadows = scene.eevee.use_shadows
                eevee.shadow_ray_count = scene.eevee.shadow_ray_count
                eevee.shadow_step_count = scene.eevee.shadow_step_count

                eevee.use_raytracing = scene.eevee.use_raytracing
                eevee.ray_tracing_method = scene.eevee.ray_tracing_method
                eevee.ray_tracing_resolution = scene.eevee.ray_tracing_options.resolution_scale
                eevee.ray_tracing_denoise = scene.eevee.ray_tracing_options.use_denoise
                eevee.ray_tracing_denoise_temporal = scene.eevee.ray_tracing_options.denoise_temporal

                eevee.fast_gi = scene.eevee.use_fast_gi
                eevee.trace_max_roughness = scene.eevee.ray_tracing_options.trace_max_roughness
                eevee.fast_gi_resolution = scene.eevee.fast_gi_resolution
                eevee.fast_gi_step_count = scene.eevee.fast_gi_step_count
                eevee.fast_gi_distance = scene.eevee.fast_gi_distance

                eevee.volumetric_tile_size = scene.eevee.volumetric_tile_size
                eevee.volume_samples = scene.eevee.volumetric_samples

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportEEVEESettings: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import EEVEE settings: {str(e)}")
            return {"CANCELLED"}

    def _import_motion_blur(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    override_settings.use_motion_blur = info.get("use_motion_blur", False)
                    override_settings.motion_blur_position = info.get("motion_blur_position", "CENTER")
                    override_settings.motion_blur_shutter = info.get("motion_blur_shutter", 0.50)
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing motion blur: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                override_settings.use_motion_blur = scene.render.use_motion_blur
                override_settings.motion_blur_position = scene.render.motion_blur_position
                override_settings.motion_blur_shutter = scene.render.motion_blur_shutter

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportMotionBlur: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import motion blur: {str(e)}")
            return {"CANCELLED"}

    def _import_output_path(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    full_path = info.get("filepath", "")
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing output path: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                full_path = scene.render.filepath

            abs_path_str = bpy.path.abspath(full_path)
            path_obj = Path(abs_path_str)
            if abs_path_str.endswith(("/", "\\")):
                override_settings.output_directory = str(path_obj)
                override_settings.output_filename = ""
            else:
                override_settings.output_directory = str(path_obj.parent)
                override_settings.output_filename = path_obj.name

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportOutputPath: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import output path: {str(e)}")
            return {"CANCELLED"}

    def _import_output_format(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            is_external = settings.use_external_blend

            try:
                if is_external:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")

                    file_format = info.get("file_format", "PNG")
                    color_depth_value = str(info.get("color_depth", "16"))

                    valid_options = ["16", "32"] if file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"] else ["8", "16"]

                    if color_depth_value not in valid_options:
                        log.warning(
                            f"Invalid color depth '{color_depth_value}' for format '{file_format}'. Using '16' as default."
                        )
                        color_depth_value = "16"

                    override_settings.file_format = file_format
                    override_settings.color_depth = color_depth_value
                    override_settings.codec = info.get("exr_codec", "ZIP")
                    override_settings.jpeg_quality = info.get("jpeg_quality", 85)
                else:
                    override_settings.file_format = scene.render.image_settings.file_format
                    override_settings.color_depth = str(scene.render.image_settings.color_depth)
                    override_settings.codec = scene.render.image_settings.exr_codec
                    override_settings.jpeg_quality = scene.render.image_settings.quality
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse external scene info: {e}")
                self.report({"ERROR"}, "Invalid JSON in external scene info.")
                return {"CANCELLED"}
            except Exception as e:
                log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                self.report(
                    {"ERROR"},
                    f"Error importing output format: {str(e)}",
                )
                return {"CANCELLED"}

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportOutputFormat: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import output format: {str(e)}")
            return {"CANCELLED"}

    def _import_performance(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            cycles = settings.override_settings.cycles

            is_external = settings.use_external_blend

            if is_external:
                try:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")

                    cycles.use_tiling = info.get("use_tiling", True)
                    cycles.tile_size = info.get("tile_size", 2048)
                    cycles.use_spatial_splits = info.get("use_spatial_splits", False)
                    cycles.use_compact_bvh = info.get("use_compact_bvh", False)
                    cycles.persistent_data = info.get("persistent_data", False)

                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse external scene info: {e}")
                    self.report({"ERROR"}, "Invalid JSON in external scene info.")
                    return {"CANCELLED"}
                except Exception as e:
                    log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                    self.report(
                        {"ERROR"},
                        f"Error importing performance settings: {str(e)}",
                    )
                    return {"CANCELLED"}
            else:
                cycles.use_tiling = scene.cycles.use_auto_tile
                cycles.tile_size = scene.cycles.tile_size
                cycles.use_spatial_splits = scene.cycles.debug_use_spatial_splits
                cycles.use_compact_bvh = scene.cycles.debug_use_compact_bvh
                cycles.persistent_data = scene.render.use_persistent_data

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportPerformance: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import performance settings: {str(e)}")
            return {"CANCELLED"}

    def _import_compositor(self, context):
        try:
            scene = context.scene
            if not scene:
                self.report({"ERROR"}, "No active scene found.")
                return {"CANCELLED"}

            settings = context.window_manager.recom_render_settings
            override_settings = settings.override_settings

            is_external = settings.use_external_blend

            try:
                if is_external:
                    info = json.loads(settings.external_scene_info)
                    if not isinstance(info, dict):
                        raise ValueError("Invalid scene info format")
                    use_compositor = info.get("use_compositor", False)
                    compositor_device = info.get("compositor_device", "CPU")
                else:
                    use_compositor = False
                    if bpy.app.version >= (5, 0, 0):
                        use_compositor = True if scene.compositing_node_group else False
                    else:
                        use_compositor = scene.use_nodes
                    compositor_device = scene.render.compositor_device

                override_settings.use_compositor = use_compositor
                override_settings.compositor_device = compositor_device
            except json.JSONDecodeError as e:
                log.error(f"Failed to parse external scene info: {e}")
                self.report({"ERROR"}, "Invalid JSON in external scene info.")
                return {"CANCELLED"}
            except Exception as e:
                log.error(f"Unexpected error loading scene info: {e}", exc_info=True)
                self.report(
                    {"ERROR"},
                    f"Error importing compositor settings: {str(e)}",
                )
                return {"CANCELLED"}

            return {"FINISHED"}
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportCompositor: {e}", exc_info=True)
            self.report({"ERROR"}, f"Failed to import compositor settings: {str(e)}")
            return {"CANCELLED"}


class RECOM_OT_ImportFromCyclesSettings(Operator):
    """Import device settings from Blender's Cycles settings"""

    bl_idname = "recom.import_from_cycles_settings"
    bl_label = "Import Device Settings"
    bl_description = "Get device settings from Blender's Cycles settings"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        try:
            prefs.import_cycles_device_settings()
        except Exception as e:
            log.error(f"Critical error in RECOM_OT_ImportFromCyclesSettings: {e}", exc_info=True)
        return {"FINISHED"}


classes = (
    RECOM_OT_ImportAllSettings,
    RECOM_OT_ImportFromCyclesSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
