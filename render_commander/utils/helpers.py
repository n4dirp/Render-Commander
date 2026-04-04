# ./utils/helpers.py

import json
import os
import shlex
import socket
import sys
import logging
import subprocess
import threading
import pathlib
import shutil
import tempfile

from datetime import datetime
from fractions import Fraction
from pathlib import Path
from typing import Optional

import bpy

from .constants import *
from .. import __package__ as base_package

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


def get_addon_temp_dir(prefs: object) -> Path:
    """Get the temporary directory for addon-specific files."""
    try:
        # Determine if we use user extensions (Blender 4.2+)
        use_user_extension = bpy.app.version >= (4, 2)

        if prefs.use_custom_temp and prefs.custom_temp_path:
            custom = Path(bpy.path.abspath(prefs.custom_temp_path)).resolve()
            if custom.exists():
                return custom / ADDON_NAME

        if use_user_extension:
            try:
                p = Path(bpy.utils.extension_path_user(base_package, create=True))
                if p.exists():
                    return p
            except (OSError, RuntimeError) as e:
                log.warning(f"Could not access user extension path: {e}")

        # Fallback to standard temp directory
        try:
            t = Path(bpy.app.tempdir).resolve().parent
            if not t.exists():
                t = Path(tempfile.gettempdir()).resolve()
            return t / ADDON_NAME
        except (OSError, RuntimeError) as e:
            raise RuntimeError(f"Failed to determine a valid temp directory: {e}")

    except Exception as e:
        log.error(f"Critical error in get_addon_temp_dir: {e}")
        raise


def get_aspect_ratio(width: int, height: int, tolerance: float = 0.02) -> str:
    """Calculate and return the closest common aspect ratio or a fraction."""
    if height == 0 or width == 0:
        return "0x0"

    exact_ratio = width / height
    common_ratios = {
        "32x9": 32 / 9,
        "21x9": 23 / 9,
        "18x9": 18 / 9,
        "17x9": 17 / 9,
        "16x10": 16 / 10,
        "16x9": 16 / 9,
        "5x4": 5 / 4,
        "4x3": 4 / 3,
        "3x2": 3 / 2,
        "2.39x1": 2.39 / 1,
        "1.85x1": 1.85 / 1,
        "1.43x1": 1.43 / 1,
        "1.5x1": 3 / 2,
        "1.375x1": 11 / 8,
        "1.33x1": 4 / 3,
        "1x1": 1.0,
        "9x16": 9 / 16,
    }

    # Find the closest named ratio
    closest_name, closest_value = min(common_ratios.items(), key=lambda x: abs(x[1] - exact_ratio))

    if abs(closest_value - exact_ratio) / exact_ratio <= tolerance:
        return closest_name
    else:
        ratio = Fraction(width, height).limit_denominator()
        return f"{ratio.numerator}x{ratio.denominator}"


def get_nearest_existing_path(path: str) -> Path:
    """Navigate up directory tree to find the nearest existing path."""
    path = Path(path)

    # Traverse upward until we find an existing directory
    while path != path.parent:  # Stop when we hit root (root.parent == root)
        if path.exists() and path.is_dir():
            return path

        path = path.parent

    # Fallback: user's home directory
    return Path.home()


def replace_variables(path_template: str) -> str:
    """Replace template variables in a path with context-specific values."""
    try:
        # --- Context Setup ---
        context = bpy.context
        scene = context.scene
        settings = context.window_manager.recom_render_settings
        prefs = context.preferences.addons[".".join(__package__.split(".")[:-1])].preferences
        info = json.loads(settings.external_scene_info)
        ext_scene = settings.use_external_blend and settings.external_blend_file_path

        # --- Blend File Information ---
        blend_file_name_no_ext = ""
        blend_folder_path = Path("")

        blend_file_to_check = None
        if settings.use_external_blend and settings.external_blend_file_path:
            blend_file_to_check = Path(bpy.path.abspath(settings.external_blend_file_path))
        elif bpy.data.filepath:
            blend_file_to_check = Path(bpy.data.filepath)

        if blend_file_to_check and blend_file_to_check.is_file():
            blend_file_name_no_ext = blend_file_to_check.stem
            blend_folder_path = blend_file_to_check.parent
        elif settings.use_external_blend:
            log.warning(f"External blend file not found: {settings.external_blend_file_path}")
            # Fallbacks are already set

        # Check for Blender's relative path prefix "//"
        if path_template.startswith("//"):
            path_template = str(blend_folder_path / path_template[2:])

        # Scene
        if ext_scene:
            scene_name_val = info.get("scene_name", "")
            view_layer_name_val = info.get("view_layer", "")
        else:
            scene_name_val = scene.name if scene else ""
            view_layer_name_val = context.view_layer.name if context.view_layer else ""

        # Resolution
        resolution_val = ""
        aspect_ratio_val = ""
        width = height = scale = 0

        if settings.override_settings.format_override:
            if settings.override_settings.resolution_override:
                res_x = settings.override_settings.resolution_x
                res_y = settings.override_settings.resolution_y
                if settings.override_settings.resolution_mode == "SET_WIDTH":
                    base_x, base_y = res_x, calculate_auto_height(context)
                elif settings.override_settings.resolution_mode == "SET_HEIGHT":
                    base_x, base_y = calculate_auto_width(context), res_y
                else:  # CUSTOM mode
                    base_x, base_y = res_x, res_y
            else:
                base_x, base_y = get_default_resolution(context)

            scale = settings.override_settings.custom_render_scale / 100

            width, height = int(base_x * scale), int(base_y * scale)
            scale_val = int(scale * 100)
        else:
            width, height = get_default_resolution(context)
            if ext_scene:
                scale_val = info.get("render_scale", "0")
            else:
                scale_val = scene.render.resolution_percentage

        aspect_ratio_val = get_aspect_ratio(width, height, 0.04)
        resolution_val = f"{width}x{height}"
        resolution_width_val = width
        resolution_height_val = height
        resolution_scale_val = scale_val

        # Frame Range
        if settings.override_settings.frame_range_override:
            frame_start_val, frame_end_val, frame_step_val, fps_val = (
                settings.override_settings.frame_start,
                settings.override_settings.frame_end,
                settings.override_settings.frame_step,
                settings.override_settings.fps,
            )
        else:
            if ext_scene:
                frame_start_val = info.get("frame_start", 0)
                frame_end_val = info.get("frame_end", 0)
                frame_step_val = info.get("frame_step", 0)
                fps_val = info.get("fps", 24)
            elif scene:
                frame_start_val = scene.frame_start
                frame_end_val = scene.frame_end
                frame_step_val = scene.frame_step
                fps_val = scene.render.fps if scene.render else 24

        # File Format
        if settings.override_settings.file_format_override:
            file_format_val = settings.override_settings.file_format
        else:
            if ext_scene:
                file_format_val = info.get("file_format", "")
            elif scene and scene.render:
                file_format_val = scene.render.image_settings.file_format
            else:
                file_format_val = ""

        # Camera
        if ext_scene:
            camera_name_val = info.get("camera_name", "")
            camera_lens_val = info.get("camera_lens", "0")
            camera_sensor_w_val = info.get("camera_sensor", "0")
        elif scene and scene.camera:
            camera_name_val = scene.camera.name
            camera_lens_val = int(scene.camera.data.lens)
            camera_sensor_w_val = int(scene.camera.data.sensor_width)
        else:
            camera_name_val, camera_lens_val, camera_sensor_w_val = "", "0", "0"

        # Cycles Render
        # Samples
        if settings.override_settings.cycles.sampling_override:
            samples_val = settings.override_settings.cycles.samples
            noise_threshold_val = f"{settings.override_settings.cycles.adaptive_threshold:.4f}"
        else:
            if ext_scene:
                samples_val = info.get("samples", "0")
                noise_threshold_val = info.get("adaptive_threshold", "0")
            elif scene and scene.cycles:
                samples_val = str(getattr(scene.cycles, "samples", getattr(scene.cycles, "aa_samples", 0)))
                thresh = getattr(scene.cycles, "adaptive_threshold", 0.0)
                noise_threshold_val = f"{thresh:.4f}"
            else:
                samples_val, noise_threshold_val = "0", "0"

        # Color Management
        view_transform_val = ""
        look_val = ""
        if ext_scene:
            view_transform_val = info.get("view_transform", "")
            look_val = info.get("look", "")
        elif scene and scene.view_settings:
            view_transform_val = str(scene.view_settings.view_transform)
            look_val = str(scene.view_settings.look)

        # Date/time
        now = datetime.now()
        date_val = now.strftime("%Y-%m-%d")
        time_val = now.strftime("%H-%M-%S")
        year_val, month_val, day_val = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")

        # System info
        user_val = os.getenv("USERNAME") or os.getenv("USER") or ""
        try:
            hostname_val = socket.gethostname() or ""
        except Exception:
            hostname_val = ""

        os_map = {
            "win32": "Windows",
            "darwin": "MacOS",
            "linux": "Linux",
        }
        os_val = os_map.get(sys.platform, sys.platform)

        render_engine = get_render_engine(context)
        engine_val = RENDER_ENGINE_MAPPING.get(render_engine, render_engine)

        variables_map = {
            "blend_name": blend_file_name_no_ext,
            "blend_dir": str(blend_folder_path),
            "engine": engine_val or "",
            "scene_name": scene_name_val,
            "view_name": view_layer_name_val,
            "aspect": str(aspect_ratio_val).replace(".", "_"),
            "resolution": resolution_val,
            "resolution_width": str(resolution_width_val),
            "resolution_height": str(resolution_height_val),
            "resolution_scale": resolution_scale_val,
            "samples": str(samples_val),
            "thresh": str(noise_threshold_val).replace(".", "_"),
            "view_transform": view_transform_val,
            "look": look_val,
            "frame_end": str(frame_end_val),
            "frame_start": str(frame_start_val),
            "frame_step": str(frame_step_val),
            "fps": str(fps_val),
            "file_format": file_format_val,
            "camera_name": camera_name_val,
            "camera_lens": str(camera_lens_val),
            "camera_sensor": str(camera_sensor_w_val),
            "date": date_val,
            "time": time_val,
            "year": year_val,
            "month": month_val,
            "day": day_val,
            "user": user_val,
            "host": hostname_val,
            "os": os_val,
        }

        variables_map.update({var.token: var.value for var in prefs.custom_variables})

        # Sanitize values
        for key, value in variables_map.items():
            if isinstance(value, str) and key != "blend_dir":
                variables_map[key] = value.replace(":", "-").replace(" ", "_")

        class _EmptyOnMissing(dict):
            def __missing__(self, key):
                return ""

        try:
            resolved_path_segment = path_template.format_map(_EmptyOnMissing(variables_map))
        except ValueError as e:
            log.warning(f"Formatting error for path template: '{path_template}'. Error: {e}")
            return f"Error: Path template formatting issue ({e})"

        return str(Path(resolved_path_segment)) if resolved_path_segment else ""

    except Exception as e:
        log.error(f"[replace_variables] Failed to process path: '{path_template}' - {e}")
        raise


def redraw_ui() -> None:
    """Redraw the UI in Blender."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    bpy.context.window_manager.update_tag()


def is_blend_or_backup_file(file_path: str) -> bool:
    """Check if a file is a valid Blender blend file."""
    if file_path.startswith("//"):
        file_path = bpy.path.abspath(file_path)

    path = Path(file_path)
    return path.is_file() and path.suffix.lower() in (".blend", ".blend1", ".blend2", ".blend3")


def get_addon_preferences():
    """Get addon preferences from Blender context."""
    return bpy.context.preferences.addons[base_package].preferences


def open_folder(folder_path: str) -> bool:
    """Open a folder in the system's default file explorer (cross-platform)."""
    if not folder_path:
        log.error("No folder path provided.")
        return False

    folder_path = Path(folder_path).resolve()

    try:
        folder_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.error(f"Failed to create directory: {e}")
        return False

    try:
        if _IS_WINDOWS:
            os.startfile(folder_path)

        elif _IS_MACOS:
            subprocess.Popen(["open", str(folder_path)])

        elif _IS_LINUX:
            prefs = get_addon_preferences()

            binary = None
            extra_args = []

            custom_config = getattr(prefs, "linux_explorer_config", "").strip()
            if custom_config:
                cmd_parts = shlex.split(custom_config)  # Safely splits "cmd --arg" into ["cmd", "--arg"]
                if cmd_parts:
                    potential_binary = cmd_parts[0]
                    if shutil.which(potential_binary):
                        binary = potential_binary
                        extra_args = cmd_parts[1:]
                    else:
                        log.warning(f"Custom Linux explorer '{potential_binary}' not found. Falling back.")

            if not binary:
                explorer_choice = getattr(prefs, "linux_file_explorer", "XDG_OPEN")
                explorer_map = {
                    "NAUTILUS": ("nautilus", ["--no-desktop"]),
                    "DOLPHIN": ("dolphin", ["--select"]),
                    "THUNAR": ("thunar", []),
                    "NEMO": ("nemo", []),
                    "XDG_OPEN": ("xdg-open", []),
                }

                binary, extra_args = explorer_map.get(explorer_choice, ("xdg-open", []))

                if not shutil.which(binary):
                    log.warning(f"'{binary}' not found – falling back to xdg-open")
                    binary = "xdg-open"
                    extra_args = []

            # Execute non-blocking process
            subprocess.Popen([binary] + extra_args + [str(folder_path)])

        log.debug(f'Opened folder: "{folder_path}"')
        return True

    except Exception as e:
        log.error(f"Failed to open folder: {e}")
        return False


def get_default_resolution(context) -> tuple:
    """Get the default resolution from scene or external info."""
    settings = context.window_manager.recom_render_settings
    fallback_res_x = 1
    fallback_res_y = 1

    if settings.use_external_blend and settings.external_blend_file_path:
        try:
            info = json.loads(settings.external_scene_info) if settings.external_scene_info else {}
            res_x = info.get("resolution_x", fallback_res_x)
            res_y = info.get("resolution_y", fallback_res_x)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            log.error(f"Failed to parse external scene info: {e}")
            res_x, res_y = fallback_res_x, fallback_res_x
    else:
        res_x = context.scene.render.resolution_x
        res_y = context.scene.render.resolution_y
    return (int(res_x), int(res_y))


def calculate_auto_width(context) -> int:
    """Calculate auto width based on height and aspect ratio."""
    settings = context.window_manager.recom_render_settings
    default_res = get_default_resolution(context)
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] > 0 else 1.0
    height = settings.override_settings.resolution_y
    return int(height * aspect_ratio)


def calculate_auto_height(context) -> int:
    """Calculate auto height based on width and aspect ratio."""
    settings = context.window_manager.recom_render_settings
    default_res = get_default_resolution(context)
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] > 0 else 1.0
    width = settings.override_settings.resolution_x
    return int(width / aspect_ratio)


def format_to_title_case(input_string: str) -> str:
    """Convert a string to title case (spaces instead of underscores)."""
    if not isinstance(input_string, str):
        return ""

    return input_string.replace("_", " ").lower().title()


def get_render_engine(context) -> str:
    """Determine the render engine used by the current or external scene."""
    settings = context.window_manager.recom_render_settings

    if settings.use_external_blend and settings.external_blend_file_path:
        try:
            info = json.loads(settings.external_scene_info)
            engine_name = info.get("render_engine", "")
        except (json.JSONDecodeError, TypeError):
            log.warning(f"Invalid Scene Info Data")
            return "UNKNOWN"
    else:
        engine_name = context.scene.render.engine

    return engine_name
