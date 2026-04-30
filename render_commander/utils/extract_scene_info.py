"""Scene Metadata Extraction Utility for Render Commander Addon"""

import json
import logging
import os
import sys
import traceback
from pathlib import Path

import bpy

logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s",
)

BLENDER_5_0 = (5, 0, 0)


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    size = float(size_bytes)
    MAX_SIZE_INDEX = len(size_name) - 1
    while size >= 1024 and i < MAX_SIZE_INDEX:
        size /= 1024
        i += 1
    formatted = f"{size:.0f}".rstrip("0").rstrip(".")
    return f"{formatted} {size_name[i]}"


def get_render_enabled_cameras_in_frame_range():
    """Instantly counts active cameras by checking Timeline Markers"""
    scene = bpy.context.scene
    start_frame = scene.frame_start
    end_frame = scene.frame_end

    camera_markers = [m for m in scene.timeline_markers if m.camera]

    if not camera_markers:
        return 1 if scene.camera else 0

    active_cameras = set()
    camera_markers.sort(key=lambda m: m.frame)

    active_at_start = None
    for m in camera_markers:
        if m.frame <= start_frame:
            active_at_start = m.camera
        else:
            break

    if active_at_start:
        active_cameras.add(active_at_start.name)
    elif scene.camera and camera_markers[0].frame > start_frame:
        active_cameras.add(scene.camera.name)

    for m in camera_markers:
        if start_frame < m.frame <= end_frame:
            active_cameras.add(m.camera.name)

    return len(active_cameras)


def get_scene_info() -> dict:
    try:
        context = bpy.context
        scene = context.scene
        render = scene.render
        cycles = scene.cycles if hasattr(scene, "cycles") else None
        eevee = scene.eevee if hasattr(scene, "eevee") else None

        blend_path = Path(bpy.data.filepath)
        modified_time = blend_path.stat().st_mtime
        file_size = blend_path.stat().st_size

        data = {
            "blend_filepath": str(blend_path),
            "file_size": format_file_size(file_size),
            "version_file": ".".join(map(str, context.blend_data.version)),
            "modified_date": modified_time,
            "modified_date_short": None,
            "scene_name": scene.name,
            "view_layer": context.view_layer.name,
            "view_layer_count": sum(1 for layer in scene.view_layers if layer.use),
            "viewlayer_names": ", ".join(layer.name for layer in scene.view_layers if layer.use),
            "render_engine": scene.render.engine,
            "view_transform": scene.view_settings.view_transform,
            "look": scene.view_settings.look,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "frame_step": scene.frame_step,
            "fps": render.fps,
            "fps_base": render.fps_base,
            "resolution_x": render.resolution_x,
            "resolution_y": render.resolution_y,
            "render_scale": render.resolution_percentage,
            "filepath": render.filepath,
            "frame_path": scene.render.frame_path(),
            "is_movie_format": render.is_movie_format,
            "file_format": render.image_settings.file_format,
            "color_depth": render.image_settings.color_depth,
        }

        if scene.camera:
            camera_data = {
                "camera_name": scene.camera.name,
            }
            if hasattr(scene.camera.data, "lens"):
                camera_data["camera_lens"] = scene.camera.data.lens
            if hasattr(scene.camera.data, "sensor_width"):
                camera_data["camera_sensor"] = scene.camera.data.sensor_width
            data.update(camera_data)
            data["camera_render_count"] = get_render_enabled_cameras_in_frame_range()

        data["use_motion_blur"] = render.use_motion_blur
        if render.use_motion_blur:
            data.update(
                {
                    "motion_blur_position": render.motion_blur_position,
                    "motion_blur_shutter": render.motion_blur_shutter,
                }
            )

        if render.image_settings.file_format == "OPEN_EXR":
            data["exr_codec"] = render.image_settings.exr_codec

        if render.image_settings.file_format == "JPEG":
            data["jpeg_quality"] = render.image_settings.quality

        use_compositor = render.use_compositing and (
            bool(scene.compositing_node_group) if bpy.app.version >= BLENDER_5_0 else scene.use_nodes
        )
        if use_compositor:
            data.update(
                {
                    "use_compositor": True,
                    "compositor_device": render.compositor_device,
                }
            )
        elif render.use_compositing:
            # Compositing is enabled but no nodes active - still report it
            data["use_compositor"] = False

        if scene.render.engine == "CYCLES" and cycles:
            # Base Cycles settings
            data.update(
                {
                    "device": cycles.device,
                    "samples": cycles.samples,
                    "time_limit": cycles.time_limit,
                    "use_spatial_splits": cycles.debug_use_spatial_splits,
                    "use_compact_bvh": cycles.debug_use_compact_bvh,
                    "persistent_data": render.use_persistent_data,
                }
            )

            # Only add adaptive sampling settings if adaptive sampling is enabled
            data["use_adaptive_sampling"] = cycles.use_adaptive_sampling
            if cycles.use_adaptive_sampling:
                data.update(
                    {
                        "adaptive_threshold": round(cycles.adaptive_threshold, 3),
                        "adaptive_min_samples": cycles.adaptive_min_samples,
                    }
                )

            # Only add denoising settings if denoising is enabled
            data["use_denoising"] = cycles.use_denoising
            if cycles.use_denoising:
                data.update(
                    {
                        "denoiser": cycles.denoiser,
                        "denoising_input_passes": cycles.denoising_input_passes,
                        "denoising_prefilter": cycles.denoising_prefilter,
                        "denoising_quality": cycles.denoising_quality,
                        "use_denoise_gpu": cycles.denoising_use_gpu,
                    }
                )

            # Only add tile size if tiling is enabled
            data["use_tiling"] = cycles.use_auto_tile
            if cycles.use_auto_tile:
                data["tile_size"] = cycles.tile_size

        elif scene.render.engine in {"BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"} and eevee:
            data.update(
                {
                    "eevee_samples": eevee.taa_render_samples,
                    "eevee_use_raytracing": eevee.use_raytracing,
                }
            )

        return data
    except Exception as e:
        logging.error("Error extracting scene info: %s", str(e))
        logging.error("%s", traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    try:
        if not bpy.data.filepath:
            error_str = "No .blend file seems to be loaded in the background Blender process."
            logging.error("%s", error_str)
            sys.exit(1)

        info = get_scene_info()

        # Write to cache file if path provided via environment variable
        cache_path = os.environ.get("BLEND_EXTRACT_CACHE_PATH")
        if cache_path:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=4)
            logging.info("Scene info written to cache: %s", cache_file)
        else:
            # Fallback to stdout if running manually
            print(json.dumps(info))

    except Exception as e:
        error_str = f"Critical error in extract_scene_info.py: {str(e)}"
        logging.error("%s", error_str)
        logging.error("%s", traceback.format_exc())

        # Still write error to cache if available
        cache_path = os.environ.get("BLEND_EXTRACT_CACHE_PATH")
        if cache_path:
            Path(cache_path).write_text(
                json.dumps({"error": error_str, "traceback": traceback.format_exc()}),
                encoding="utf-8",
            )
        else:
            print(json.dumps({"error": error_str, "traceback": traceback.format_exc()}))
        sys.exit(1)
