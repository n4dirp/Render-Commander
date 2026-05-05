# ./utils/helpers.py

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Union

import bpy

from .. import __package__ as base_package
from .constants import RESERVED_TOKENS

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


def get_addon_settings(context):
    """Helper function to retrieve override settings from context."""
    return context.window_manager.recom_render_settings


def get_override_settings(context):
    """Helper function to retrieve override settings from context."""
    return get_addon_settings(context).override_settings


def get_addon_preferences(context=None):
    """Get addon preferences from Blender context."""
    ctx = context or bpy.context

    addon = ctx.preferences.addons.get(base_package)
    if addon is None:
        return None

    return addon.preferences


def get_addon_temp_dir() -> Path:
    """Get the temporary directory for addon-specific files."""
    try:
        return Path(bpy.utils.extension_path_user(base_package, create=True))
    except Exception as e:
        log.error("Failed to get addon extension directory for '%s': %s", base_package, e)
        raise


def replace_variables(prefs, path_template: str) -> str:
    """Replace template variables in a path with context-specific values."""
    if not prefs:
        return path_template

    try:
        variables_map = {var.token: var.value for var in prefs.custom_variables if var.token not in RESERVED_TOKENS}

        def replacement_func(match):
            var_name = match.group(1)

            # Bypass reserved tokens > keep original {token}
            if var_name in RESERVED_TOKENS:
                return match.group(0)

            return variables_map.get(var_name, match.group(0))

        resolved_path_segment = re.sub(r"(?<!\{)\{(\w+)\}(?!\})", replacement_func, path_template)

        return resolved_path_segment

    except Exception as e:
        log.error("[replace_variables] Failed to process path: '%s' - %s", path_template, e)
        raise


def redraw_ui(mode: str = "VIEW_3D") -> None:
    """
    Redraw Blender UI areas.

    Args:
        mode:
            "VIEW_3D" -> redraw only 3D viewports
            "ALL"     -> redraw every UI area
            any other Blender area type (e.g. "IMAGE_EDITOR")
    """

    for window in bpy.context.window_manager.windows:
        screen = window.screen

        for area in screen.areas:
            if mode == "ALL":
                area.tag_redraw()

            elif area.type == mode:
                area.tag_redraw()


def is_blend_or_backup_file(file_path: str) -> bool:
    """Check if a file is a valid Blender blend file."""
    if file_path.startswith("//"):
        file_path = bpy.path.abspath(file_path)

    path = Path(file_path)
    return path.is_file() and path.suffix.lower() in (
        ".blend",
        ".blend1",
        ".blend2",
        ".blend3",
    )


def open_folder(folder_path: str) -> bool:
    """Open a folder in the system's default file explorer."""
    if not folder_path:
        log.error("No folder path provided.")
        return False

    # Check UNC prefix
    is_unc = str(folder_path).startswith("//")

    try:
        if is_unc:
            folder_path = bpy.path.abspath(folder_path)

        path = Path(folder_path).expanduser().resolve()

    except Exception as e:
        log.error("Invalid path format: %s", e)
        return False

    if path.exists() and not path.is_dir():
        log.error("Path exists but is a file. Aborting to prevent execution.")
        return False

    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.error("Failed to create directory: %s", e)
        return False

    try:
        safe_path_str = str(path)
        if _IS_WINDOWS:
            os.startfile(safe_path_str)
        elif _IS_MACOS:
            subprocess.Popen(["open", safe_path_str])
        elif _IS_LINUX:
            subprocess.Popen(["xdg-open", safe_path_str])
        else:
            log.error("Unsupported OS.")
            return False

        log.debug('Opened folder: "%s"', path)
        return True

    except Exception as e:
        log.error("Failed to open folder: %s", e)
        return False


def get_default_resolution(context) -> tuple:
    """Get the default resolution from scene or external info."""
    settings = get_addon_settings(context)
    fallback_res_x = 1
    fallback_res_y = 1

    if settings.use_external_blend and settings.external_blend_file_path:
        try:
            info = json.loads(settings.external_scene_info) if settings.external_scene_info else {}
            res_x = info.get("resolution_x", fallback_res_x)
            res_y = info.get("resolution_y", fallback_res_x)
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            log.error("Failed to parse external scene info: %s", e)
            res_x, res_y = fallback_res_x, fallback_res_y
    else:
        res_x = context.scene.render.resolution_x
        res_y = context.scene.render.resolution_y
    return (int(res_x), int(res_y))


def calculate_auto_width(context) -> int:
    """Calculate auto width based on height and aspect ratio."""
    override_settings = get_override_settings(context)
    default_res = get_default_resolution(context)
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] > 0 else 1.0
    height = override_settings.resolution_y
    return int(height * aspect_ratio)


def calculate_auto_height(context) -> int:
    """Calculate auto height based on width and aspect ratio."""
    override_settings = get_override_settings(context)
    default_res = get_default_resolution(context)
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] > 0 else 1.0
    width = override_settings.resolution_x
    return int(width / aspect_ratio)


def format_to_title_case(input_string: str) -> str:
    """Convert a string to title case (spaces instead of underscores)."""
    if not isinstance(input_string, str):
        return ""

    return input_string.replace("_", " ").lower().title()


def get_render_engine(context) -> str:
    """Determine the render engine used by the current or external scene."""
    settings = get_addon_settings(context)

    if settings.use_external_blend and settings.external_blend_file_path:
        try:
            info = json.loads(settings.external_scene_info)
            engine_name = info.get("render_engine", "")
        except (json.JSONDecodeError, TypeError):
            log.warning("Invalid Scene Info Data")
            return "UNKNOWN"
    else:
        engine_name = context.scene.render.engine

    return engine_name


def resolve_blender_path(text: str) -> tuple[str, Any]:
    """Normalizes shorthand paths and resolves them to a bpy object/value."""
    if not text.startswith("bpy."):
        # Things that belong directly under bpy.context
        if text.startswith(
            (
                "scene.",
                "view_layer.",
                "workspace.",
                "screen.",
                "window.",
                "area.",
                "space_data.",
            )
        ):
            text = "bpy.context." + text
        else:
            text = "bpy.context.scene." + text

    if text == "bpy.context":
        return text, bpy.context
    if text == "bpy.data":
        return text, bpy.data

    # Try path_resolve first (faster & RNA-aware)
    try:
        if text.startswith("bpy.context."):
            return text, bpy.context.path_resolve(text[12:])
        if text.startswith("bpy.data."):
            return text, bpy.data.path_resolve(text[9:])
    except Exception:
        pass  # Fallback to getattr if path_resolve fails on non-RNA paths

    # Fallback: manual traversal
    parts = text.split(".")
    if parts[0] != "bpy":
        raise ValueError(f"Invalid data path: {text}")

    obj = bpy
    for part in parts[1:]:
        try:
            obj = getattr(obj, part)
        except AttributeError as exc:
            raise ValueError(f"Invalid attribute: {part} in path {text}") from exc
    return text, obj


def get_scene_info(settings: Any) -> Union[dict, None]:
    """Single source of truth for scene info parsing"""
    if not settings.external_scene_info or not settings.is_scene_info_loaded:
        return None

    try:
        info = json.loads(settings.external_scene_info)
        if info.get("blend_filepath", "") == "No Data":
            return None
        return info
    except json.JSONDecodeError as e:
        log.error("Failed to decode JSON: %s", e)
        return None


def draw_label_value_box(layout, label: str, value: str = "", factor: float = 0.4, active: bool = False) -> object:
    """Draw a split box with a right-aligned label and left-aligned value."""
    box = layout.box()
    box.active = active
    split = box.split(factor=factor)

    row_label = split.row(align=True)
    row_value = split.row(align=True)

    if value:
        row_value.alignment = "LEFT"
        row_label.alignment = "RIGHT"

    row_label.label(text=label)
    row_value.label(text=str(value))

    return box


def format_timecode(frame_start: int, frame_end: int, fps_real: float, show_hours=False) -> str:
    """Convert a frame range to a formatted timecode string."""
    # Calculate total duration
    total_frames = max(0, frame_end - frame_start + 1)
    total_seconds = total_frames / fps_real if fps_real > 0 else 0

    # Break down into time components
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    # Calculate remaining frames from fractional seconds
    frames = int(round((total_seconds - int(total_seconds)) * fps_real))

    # Handle frame overflow (can happen due to rounding)
    if frames >= fps_real:
        frames = 0
        seconds += 1
        if seconds >= 60:
            seconds = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                hours += 1

    # Format output
    if show_hours is True or (show_hours is None and hours > 0):
        return f"{hours:02}:{minutes:02}:{seconds:02}+{frames:02}"

    return f"{minutes:02}:{seconds:02}+{frames:02}"
