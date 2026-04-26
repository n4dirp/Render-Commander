"""
Provides the logic required to synchronize render settings between 
the current scene, external blend files, and the Render Commander override system.
"""

import json
import logging

import bpy
from bpy.types import Operator

from ..utils.constants import RE_CYCLES, RE_EEVEE_NEXT, RE_EEVEE
from ..preferences import get_addon_preferences
from ..utils.helpers import get_render_engine

log = logging.getLogger(__name__)


class RECOM_OT_ImportAllSettings(Operator):
    """Import selected property values from the current scene / external blend"""

    bl_idname = "recom.import_all_settings"
    bl_label = "Import Scene Values"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        scene = context.scene
        if not scene:
            self.report({"ERROR"}, "No active scene found.")
            return {"CANCELLED"}

        settings = context.window_manager.recom_render_settings
        override_settings = settings.override_settings
        ext_info = None

        if settings.use_external_blend:
            try:
                ext_info = json.loads(settings.external_scene_info)
                if not isinstance(ext_info, dict):
                    raise ValueError("Invalid scene info format")
            except Exception as e:
                log.error("Failed to parse external scene info: %s", e, exc_info=True)
                self.report({"ERROR"}, "Invalid or unreadable external scene info.")
                return {"CANCELLED"}

        try:
            prefs = get_addon_preferences(context)
            prefs_overrides = prefs.override_import_settings
            render_engine = get_render_engine(context)

            if prefs_overrides.import_frame_range:
                self._import_frame_range(scene, override_settings, ext_info)
            if prefs_overrides.import_resolution:
                self._import_manual_resolution(scene, override_settings, ext_info)
            if prefs_overrides.import_output_path:
                self._import_output_path(scene, override_settings, ext_info)
            if prefs_overrides.import_output_format:
                self._import_output_format(scene, override_settings, ext_info)

            if render_engine == RE_CYCLES:
                if prefs_overrides.import_compute_device:
                    self._import_compute_device(scene, override_settings, ext_info)
                if prefs_overrides.import_sampling:
                    self._import_sampling(scene, override_settings, ext_info)
                if prefs_overrides.import_performance:
                    self._import_performance(scene, override_settings, ext_info)
            elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                if prefs_overrides.import_eevee_settings:
                    self._import_eevee_settings(scene, override_settings, ext_info)

            if prefs_overrides.import_motion_blur:
                self._import_motion_blur(scene, override_settings, ext_info)
            if prefs_overrides.import_compositor:
                self._import_compositor(scene, override_settings, ext_info)

            context.area.tag_redraw()
        except Exception as exc:
            log.error("ImportAllSettings failed: %s", exc, exc_info=True)
            self.report({"ERROR"}, f"Import failed: {str(exc)}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def _import_compute_device(self, scene, override_settings, ext_info):
        cycles = override_settings.cycles
        if ext_info is not None:
            cycles.device = str(ext_info.get("cycles_device", "CPU"))
        else:
            cycles.device = str(scene.cycles.device)

        cycles.device_override = True

    def _import_frame_range(self, scene, override_settings, ext_info):
        if ext_info is not None:
            override_settings.frame_current = ext_info.get("frame_current", 1)
            override_settings.frame_start = ext_info.get("frame_start", 1)
            override_settings.frame_end = ext_info.get("frame_end", 250)
            override_settings.frame_step = ext_info.get("frame_step", 1)
        else:
            override_settings.frame_current = scene.frame_current
            override_settings.frame_start = scene.frame_start
            override_settings.frame_end = scene.frame_end
            override_settings.frame_step = scene.frame_step

        override_settings.frame_range_override = True

    def _import_manual_resolution(self, scene, override_settings, ext_info):
        if ext_info is not None:
            override_settings.resolution_x = ext_info.get("resolution_x", 1920)
            override_settings.resolution_y = ext_info.get("resolution_y", 1080)
            current_percentage = ext_info.get("render_scale", 100)
        else:
            override_settings.resolution_x = scene.render.resolution_x
            override_settings.resolution_y = scene.render.resolution_y
            current_percentage = scene.render.resolution_percentage

        override_settings.custom_render_scale = current_percentage
        override_settings.format_override = True

    def _import_sampling(self, scene, override_settings, ext_info):
        cycles = override_settings.cycles
        if ext_info is not None:
            cycles.use_adaptive_sampling = ext_info.get("use_adaptive_sampling", True)
            cycles.adaptive_threshold = ext_info.get("adaptive_threshold", 0.01)
            cycles.samples = ext_info.get("samples", 4096)
            cycles.adaptive_min_samples = ext_info.get("adaptive_min_samples", 0)
            cycles.time_limit = ext_info.get("time_limit", 0.0)
            cycles.use_denoising = ext_info.get("use_denoising", False)
            cycles.denoiser = ext_info.get("denoiser", "OPENIMAGEDENOISE")
            cycles.denoising_input_passes = ext_info.get("denoising_input_passes", "RGB_ALBEDO_NORMAL")
            cycles.denoising_prefilter = ext_info.get("denoising_prefilter", "ACCURATE")
            cycles.denoising_quality = ext_info.get("denoising_quality", "HIGH")
            cycles.denoising_use_gpu = ext_info.get("denoising_use_gpu", False)
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

        cycles.sampling_override = True

    def _import_eevee_settings(self, scene, override_settings, ext_info):
        eevee = override_settings.eevee
        if ext_info is not None:
            eevee.samples = ext_info.get("eevee_samples", 64)
        else:
            eevee.samples = scene.eevee.taa_render_samples

        override_settings.eevee_override = True

    def _import_motion_blur(self, scene, override_settings, ext_info):
        if ext_info is not None:
            override_settings.use_motion_blur = ext_info.get("use_motion_blur", False)
            override_settings.motion_blur_position = ext_info.get("motion_blur_position", "CENTER")
            override_settings.motion_blur_shutter = ext_info.get("motion_blur_shutter", 0.50)
        else:
            override_settings.use_motion_blur = scene.render.use_motion_blur
            override_settings.motion_blur_position = scene.render.motion_blur_position
            override_settings.motion_blur_shutter = scene.render.motion_blur_shutter

        override_settings.motion_blur_override = True

    def _import_output_path(self, scene, override_settings, ext_info):
        full_path = ext_info.get("filepath", "") if ext_info is not None else scene.render.filepath

        if full_path.endswith(("/", "\\")):
            override_settings.output_directory = full_path
            override_settings.output_filename = ""
        else:
            last_slash = full_path.rfind("/")
            last_backslash = full_path.rfind("\\")
            split_idx = max(last_slash, last_backslash)

            if split_idx != -1:
                override_settings.output_directory = full_path[: split_idx + 1]
                override_settings.output_filename = full_path[split_idx + 1 :]
            else:
                override_settings.output_directory = ""
                override_settings.output_filename = full_path

        override_settings.output_path_override = True

    def _import_output_format(self, scene, override_settings, ext_info):
        if ext_info is not None:
            file_format = ext_info.get("file_format", "PNG")
            color_depth_value = str(ext_info.get("color_depth", "16"))

            valid_options = ["16", "32"] if file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"] else ["8", "16"]

            if color_depth_value not in valid_options:
                log.warning(
                    "Invalid color depth '%s' for format '%s'. Using '16' as default.",
                    color_depth_value,
                    file_format,
                )
                color_depth_value = "16"

            override_settings.file_format = file_format
            override_settings.color_depth = color_depth_value
            override_settings.codec = ext_info.get("exr_codec", "ZIP")
            override_settings.jpeg_quality = ext_info.get("jpeg_quality", 85)
        else:
            override_settings.file_format = scene.render.image_settings.file_format
            override_settings.color_depth = str(scene.render.image_settings.color_depth)
            override_settings.codec = scene.render.image_settings.exr_codec
            override_settings.jpeg_quality = scene.render.image_settings.quality

        override_settings.file_format_override = True

    def _import_performance(self, scene, override_settings, ext_info):
        cycles = override_settings.cycles
        if ext_info is not None:
            cycles.use_tiling = ext_info.get("use_tiling", True)
            cycles.tile_size = ext_info.get("tile_size", 2048)
            cycles.use_spatial_splits = ext_info.get("use_spatial_splits", False)
            cycles.use_compact_bvh = ext_info.get("use_compact_bvh", False)
            cycles.persistent_data = ext_info.get("persistent_data", False)
        else:
            cycles.use_tiling = scene.cycles.use_auto_tile
            cycles.tile_size = scene.cycles.tile_size
            cycles.use_spatial_splits = scene.cycles.debug_use_spatial_splits
            cycles.use_compact_bvh = scene.cycles.debug_use_compact_bvh
            cycles.persistent_data = scene.render.use_persistent_data

        cycles.performance_override = True

    def _import_compositor(self, scene, override_settings, ext_info):
        if ext_info is not None:
            override_settings.use_compositor = ext_info.get("use_compositor", False)
            override_settings.compositor_device = ext_info.get("compositor_device", "CPU")
        else:
            if bpy.app.version >= (5, 0, 0):
                use_compositor = bool(scene.compositing_node_group)
            else:
                use_compositor = scene.use_nodes

            override_settings.use_compositor = scene.render.use_compositing and use_compositor
            override_settings.compositor_device = scene.render.compositor_device

        override_settings.compositor_override = True


classes = (RECOM_OT_ImportAllSettings,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
