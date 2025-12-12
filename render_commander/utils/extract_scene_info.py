# utils/extract_scene_info.py

import json
import sys
import logging
import traceback
import struct
import datetime
from datetime import timedelta
from pathlib import Path
import math

import bpy

logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s",
)


def format_modified_date(timestamp: float) -> str:
    """Format timestamp into human-readable date string."""
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
        today = datetime.datetime.now().date()
        yesterday = today - timedelta(days=1)

        if dt.date() == today:
            return f"Today {dt.strftime('%H:%M')}"
        elif dt.date() == yesterday:
            return f"Yesterday {dt.strftime('%H:%M')}"
        else:
            return dt.strftime("%d %B %Y")  # e.g., "09 May 2025"
    except Exception as e:
        logging.error(f"Error formatting date: {e}")
        return "Unknown"


def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable file size string."""
    if size_bytes < 1:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.log(size_bytes, 1024))
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def get_scene_info() -> dict:
    """Extract comprehensive scene information from current Blender context."""
    try:
        context = bpy.context
        scene = context.scene
        render = scene.render

        cycles = scene.cycles if hasattr(scene, "cycles") else None
        eevee = scene.eevee if hasattr(scene, "eevee") else None

        blend_path = Path(bpy.data.filepath)
        modified_time = blend_path.stat().st_mtime
        file_size = blend_path.stat().st_size
        formatted_date = format_modified_date(modified_time)
        render_engine = scene.render.engine
        blender_version = context.blend_data.version

        data = {
            "blend_filepath": str(blend_path),
            "file_size": format_file_size(file_size),
            "blender_version": ".".join(map(str, blender_version)),
            "modified_date": datetime.datetime.fromtimestamp(modified_time).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "modified_date_short": formatted_date,
            "scene_name": scene.name,
            "view_layer": context.view_layer.name,
            "render_engine": render_engine,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "frame_step": scene.frame_step,
            "fps": render.fps,
            "fps_base": render.fps_base,
            "resolution_x": render.resolution_x,
            "resolution_y": render.resolution_y,
            "render_scale": render.resolution_percentage,
            "filepath": bpy.path.abspath(render.filepath),
            "is_movie_format": render.is_movie_format,
            "file_format": render.image_settings.file_format,
            "color_depth": render.image_settings.color_depth,
            "exr_codec": render.image_settings.exr_codec,
            "jpeg_quality": render.image_settings.quality,
            "use_motion_blur": render.use_motion_blur,
            "motion_blur_position": render.motion_blur_position,
            "motion_blur_shutter": render.motion_blur_shutter,
            "camera_name": scene.camera.name if scene.camera else "No Camera",
            "camera_lens": 0,
            "camera_sensor": 0,
            "use_compositor": (True if scene.compositing_node_group else False)
            if bpy.app.version >= (5, 0, 0)
            else scene.use_nodes,
            "compositor_device": render.compositor_device,
        }

        if scene.camera and scene.camera.data:
            if hasattr(scene.camera.data, "lens"):
                data["camera_lens"] = scene.camera.data.lens
            if hasattr(scene.camera.data, "sensor_width"):
                data["camera_sensor"] = scene.camera.data.sensor_width

        if render_engine == "CYCLES":
            if cycles:
                data.update(
                    {
                        "device": cycles.device,
                        "use_adaptive_sampling": cycles.use_adaptive_sampling,
                        "adaptive_threshold": round(cycles.adaptive_threshold, 3),
                        "samples": cycles.samples,
                        "adaptive_min_samples": cycles.adaptive_min_samples,
                        "time_limit": cycles.time_limit,
                        "use_denoising": cycles.use_denoising,
                        "denoiser": cycles.denoiser,
                        "denoising_input_passes": cycles.denoising_input_passes,
                        "denoising_prefilter": cycles.denoising_prefilter,
                        "denoising_quality": cycles.denoising_quality,
                        "use_denoise_gpu": cycles.denoising_use_gpu,
                        "max_bounces": cycles.max_bounces,
                        "diffuse_bounces": cycles.diffuse_bounces,
                        "glossy_bounces": cycles.glossy_bounces,
                        "transmission_bounces": cycles.transparent_max_bounces,
                        "volume_bounces": cycles.volume_bounces,
                        "transparent_bounces": cycles.transparent_max_bounces,
                        "sample_clamp_direct": cycles.sample_clamp_direct,
                        "sample_clamp_indirect": cycles.sample_clamp_indirect,
                        "blur_glossy": cycles.blur_glossy,
                        "caustics_reflective": cycles.caustics_reflective,
                        "caustics_refractive": cycles.caustics_refractive,
                        "use_tiling": cycles.use_auto_tile,
                        "tile_size": cycles.tile_size,
                        "use_spatial_splits": cycles.debug_use_spatial_splits,
                        "use_compact_bvh": cycles.debug_use_compact_bvh,
                        "persistent_data": render.use_persistent_data,
                    }
                )

        elif render_engine in {"BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"}:
            if eevee:
                data.update(
                    {
                        "eevee_samples": eevee.taa_render_samples,
                        "eevee_use_shadows": eevee.use_shadows,
                        "eevee_shadow_ray_count": eevee.shadow_ray_count,
                        "eevee_shadow_step_count": eevee.shadow_step_count,
                        "eevee_use_raytracing": eevee.use_raytracing,
                        "eevee_ray_tracing_method": eevee.ray_tracing_method,
                        "eevee_ray_tracing_resolution": eevee.ray_tracing_options.resolution_scale,
                        "eevee_ray_tracing_denoise": eevee.ray_tracing_options.use_denoise,
                        "eevee_ray_tracing_denoise_temporal": eevee.ray_tracing_options.denoise_temporal,
                        "eevee_fast_gi": eevee.use_fast_gi,
                        "eevee_trace_max_roughness": eevee.ray_tracing_options.trace_max_roughness,
                        "fast_gi_resolution": eevee.fast_gi_resolution,
                        "fast_gi_step_count": eevee.fast_gi_step_count,
                        "fast_gi_distance": eevee.fast_gi_distance,
                        "eevee_volumetric_tile_size": eevee.volumetric_tile_size,
                        "eevee_volume_samples": eevee.volumetric_samples,
                    }
                )

        return data
    except Exception as e:
        logging.error(f"Error extracting scene info: {str(e)}")
        logging.error(traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    try:
        if not bpy.data.filepath:
            err_msg = "No .blend file seems to be loaded in the background Blender process."
            logging.error(err_msg)
            print(json.dumps({"error": err_msg}))
            sys.exit(1)

        info = get_scene_info()
        print(json.dumps(info))
    except Exception as e:
        err_msg = f"Critical error in extract_scene_info.py __main__: {str(e)}"
        logging.error(err_msg)
        logging.error(traceback.format_exc())
        print(json.dumps({"error": err_msg, "traceback": traceback.format_exc()}))
        sys.exit(1)
