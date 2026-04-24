# ./utils/helpers.py

import json
import os
import sys
import logging
import subprocess
import re
from pathlib import Path

import bpy

from .constants import RESERVED_TOKENS
from .. import __package__ as base_package

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


def get_addon_temp_dir() -> Path:
    """Get the temporary directory for addon-specific files."""
    try:
        return Path(bpy.utils.extension_path_user(base_package, create=True))
    except Exception as e:
        log.error("Failed to get addon extension directory for '%s': %s", base_package, e)
        raise


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
    """
    Replace template variables in a path with context-specific values.
    Used with the Override Output Path
    """
    try:
        context = bpy.context
        prefs = context.preferences.addons[".".join(__package__.split(".")[:-1])].preferences

        variables_map = {
            var.token: var.value
            for var in prefs.custom_variables
            if var.token not in RESERVED_TOKENS  # exclude reserved upfront
        }

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
    settings = context.window_manager.recom_render_settings
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
            log.warning("Invalid Scene Info Data")
            return "UNKNOWN"
    else:
        engine_name = context.scene.render.engine

    return engine_name


def resolve_blender_path(text: str) -> tuple[str, any]:
    """Normalizes shorthand paths and resolves them to a bpy object/value."""
    if not text.startswith("bpy."):
        # Things that belong directly under bpy.context
        if text.startswith(("scene.", "view_layer.", "workspace.", "screen.", "window.", "area.", "space_data.")):
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
