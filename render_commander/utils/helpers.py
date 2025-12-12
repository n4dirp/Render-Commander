# ./utils/helpers.py

import json
import os
import re
import sys
import logging
import subprocess
import threading
import datetime
import fractions
import string
import pathlib
import shlex
import shutil
import tempfile
import time
import random

from datetime import datetime
from fractions import Fraction
from string import Template
from pathlib import Path
from typing import Optional

import bpy

from .. import __package__ as base_package

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


def get_addon_name() -> str:
    """Get the name of the addon."""
    return base_package


def sanitize_filename(name: str) -> str:
    """Sanitize a filename by replacing invalid characters with underscores."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


def parse_frame_string(frame_str: str) -> list:
    """Parse a frame range string into a sorted list of integers."""
    frames = set()
    tokens = re.findall(r"\d+(?:-\d+)?", frame_str)
    for token in tokens:
        if "-" in token:
            start, end = map(int, token.split("-"))
            frames.update(range(start, end + 1))
        else:
            frames.add(int(token))
    return sorted(frames)


def format_frame_range(frames_list: list) -> str:
    """Format a list of frame numbers into a compact range string."""
    if not frames_list:
        return "[]"

    # Ensure sorting and uniqueness
    sorted_frames = sorted(set(map(int, frames_list)))

    ranges = []
    start = end = sorted_frames[0]

    for num in sorted_frames[1:]:
        if num == end + 1:
            end = num
        else:
            ranges.append((start, end))
            start = end = num
        end = num
    ranges.append((start, end))  # Add the last range

    formatted_ranges = []
    for r in ranges:
        if r[0] == r[1]:
            formatted_ranges.append(f"{r[0]}")
        else:
            formatted_ranges.append(f"{r[0]}-{r[1]}")

    return f"[{', '.join(formatted_ranges)}]"


def get_blender_version(exec_path: str) -> str:
    """Retrieve Blender version from an executable path."""
    exec_path = Path(exec_path)

    if not exec_path.is_file():
        return ""

    try:
        import subprocess

        result = subprocess.run(
            [exec_path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if _IS_WINDOWS else 0,
        )

        for line in result.stdout.splitlines():
            if "Blender" in line:
                parts = line.strip().split()
                for part in parts:
                    if part.count(".") >= 2:
                        return part
        return ""
    except subprocess.CalledProcessError as e:
        log.error(f"Blender version check failed (code {e.returncode}): {e.stderr}")
    except Exception as e:
        log.error(f"Error checking Blender version: {str(e)}")
    return ""


def get_aspect_ratio(width: int, height: int, tolerance: float = 0.02) -> str:
    """Calculate and return the closest common aspect ratio or a fraction."""
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
        blend_file_name_no_ext = "UnknownName"
        blend_folder_path = Path("UnknownPath")

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
            scene_name_val = info.get("scene_name", "UnknownScene")
            view_layer_name_val = info.get("view_layer", "UnknownViewLayer")
        else:
            scene_name_val = scene.name if scene else "UnknownScene"
            view_layer_name_val = context.view_layer.name if context.view_layer else "NoViewLayer"

        # Resolution
        resolution_val = "UnknownResolution"
        aspect_ratio_val = "UnknownAspectRatio"
        width = height = 0

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

            scale = (
                float(settings.override_settings.render_scale)
                if settings.override_settings.render_scale != "CUSTOM"
                else settings.override_settings.custom_render_scale / 100
            )
            width, height = int(base_x * scale), int(base_y * scale)
        else:
            width, height = get_default_resolution(context)
        aspect_ratio_val = get_aspect_ratio(width, height, 0.04)
        resolution_val = f"{width}x{height}"

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
                file_format_val = info.get("file_format", "UnknownFileFormat")
            elif scene and scene.render:
                file_format_val = scene.render.image_settings.file_format
            else:
                file_format_val = "UnknownFileFormat"

        # Camera
        if ext_scene:
            camera_name_val = info.get("camera_name", "NoCamera")
            camera_lens_val = info.get("camera_lens", "0")
            camera_sensor_w_val = info.get("camera_sensor", "0")
        elif scene and scene.camera:
            camera_name_val = scene.camera.name
            camera_lens_val = int(scene.camera.data.lens)
            camera_sensor_w_val = int(scene.camera.data.sensor_width)
        else:
            camera_name_val, camera_lens_val, camera_sensor_w_val = "NoCamera", "0", "0"

        # Samples
        if settings.override_settings.cycles.sampling_override:
            samples_val = settings.override_settings.cycles.samples
            noise_threshold_val = f"{settings.override_settings.cycles.adaptive_threshold:.4f}"
        else:
            if ext_scene:
                samples_val = info.get("samples", "0")
                noise_threshold_val = info.get("adaptive_threshold", "0")
            elif scene and scene.cycles:
                samples_val = str(
                    getattr(scene.cycles, "samples", getattr(scene.cycles, "aa_samples", 0))
                )
                thresh = getattr(scene.cycles, "adaptive_threshold", 0.0)
                noise_threshold_val = f"{thresh:.4f}"
            else:
                samples_val, noise_threshold_val = "0", "0"

        # Blender Version
        blender_version_val = ""
        if "{bl_ver}" in path_template.lower():  # Check lower for case-insensitivity
            if prefs.custom_executable and prefs.custom_executable_path:
                blender_version_val = get_blender_version(prefs.custom_executable_path)
            else:
                blender_version_val = ".".join(map(str, bpy.app.version))

        # Date/time
        now = datetime.now()
        date_val, time_val = now.strftime("%Y-%m-%d"), now.strftime("%H-%M-%S")
        year_val, month_val, day_val = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")

        # System info
        user_val = os.getenv("USERNAME") or os.getenv("USER") or "UnknownUser"
        try:
            hostname_val = socket.gethostname() or "UnknownHost"
        except Exception:
            hostname_val = "UnknownHost"

        variables_map = {
            "blend_name": blend_file_name_no_ext,
            "blend_dir": str(blend_folder_path),
            "bl_ver": str(blender_version_val).replace(".", "_"),
            "engine": get_render_engine(context) or "Unknown",
            "scene_name": scene_name_val,
            "view_name": view_layer_name_val,
            "aspect": str(aspect_ratio_val).replace(".", "_"),
            "resolution": resolution_val,
            "samples": str(samples_val),
            "thresh": str(noise_threshold_val).replace(".", "_"),
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
        }

        # Add custom variables
        for var in prefs.custom_variables:
            variables_map[var.token] = var.value

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


def reset_button_state() -> None:
    """Reset the render button state and redraw UI."""
    try:
        wm = bpy.context.window_manager
        if wm is not None and hasattr(wm, "recom_render_settings"):
            wm.recom_render_settings.disable_render_button = False
            redraw_ui()
    except:
        pass
    return None


def redraw_ui() -> None:
    """Redraw the UI in Blender."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()
    # bpy.context.window_manager.update_tag()


def is_blender_blend_file(file_path: str) -> bool:
    """Check if a file is a valid Blender blend file."""
    if file_path.startswith("//"):
        file_path = bpy.path.abspath(file_path)

    path = Path(file_path)
    return path.is_file() and path.suffix.lower() in (".blend", ".blend1", ".blend2", ".blend3")


def generate_job_id() -> str:
    """Generate a unique job ID using timestamp and random character."""
    timestamp = int(time.time())
    alphabet = string.digits + string.ascii_uppercase  # standard base-36
    base36 = ""
    while timestamp > 0:
        timestamp, rem = divmod(timestamp, 36)
        base36 = alphabet[rem] + base36
    random_char = random.choice(alphabet)
    return base36 + random_char


def get_addon_preferences():
    """Get addon preferences from Blender context."""
    return bpy.context.preferences.addons[base_package].preferences


def open_folder(folder_path: str) -> bool:
    """Open a folder in the system's default file explorer (cross-platform)."""
    if not folder_path:
        log.error("No folder path provided.")
        return False

    folder_path = Path(folder_path).resolve()

    # Create directory first, but don't block on this operation
    try:
        folder_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.error(f"Failed to create directory: {e}")
        return False

    if not folder_path.exists():
        log.error(f"Folder does not exist after creation: '{folder_path}'")
        return False

    # Create a new thread to handle the folder opening
    def open_folder_in_thread():
        try:
            if _IS_WINDOWS:
                os.startfile(folder_path)
            elif _IS_MACOS:
                subprocess.Popen(["open", folder_path])
            elif _IS_LINUX:
                prefs = get_addon_preferences()
                explorer_choice = prefs.linux_file_explorer

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

                cmd = [binary] + extra_args + [folder_path]
                subprocess.Popen(cmd)

            log.info(f"Opened folder in background: '{folder_path}'")

        except Exception as e:
            log.error(f"Failed to open folder in background: {e}")

    threading.Thread(target=open_folder_in_thread, daemon=True).start()

    return True


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
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] else 1.0
    height = settings.override_settings.resolution_y
    return int(height * aspect_ratio)


def calculate_auto_height(context) -> int:
    """Calculate auto height based on width and aspect ratio."""
    settings = context.window_manager.recom_render_settings
    default_res = get_default_resolution(context)
    aspect_ratio = default_res[0] / default_res[1] if default_res[1] else 1.0
    width = settings.override_settings.resolution_x
    return int(width / aspect_ratio)


def run_in_terminal(prefs, command: str, keep_open: bool = False) -> bool:
    """Run a command in a terminal window, respecting user preferences."""
    try:
        if not command or not isinstance(command, str):
            log.error("Invalid command: Command is empty or not a string.")
            return False

        terminal_commands = {
            "GNOME": "gnome-terminal",
            "XFCE": "xfce4-terminal",
            "KONSOLE": "konsole",
            "XTERM": "xterm",
            "TERMINATOR": "terminator",
        }

        DEFAULT_TERMINAL = "xterm"

        if prefs.set_linux_terminal:
            terminal_cmd = terminal_commands.get(prefs.linux_terminal, DEFAULT_TERMINAL)
        else:
            terminal_cmd = next(
                (t for t in terminal_commands.values() if shutil.which(t)), DEFAULT_TERMINAL
            )

        if not shutil.which(terminal_cmd):
            log.warning(f"Preferred terminal '{terminal_cmd}' not found. Falling back to xterm.")
            terminal_cmd = DEFAULT_TERMINAL

        terminal_args = {
            "gnome-terminal": f'-- bash -c "{command}{"; exec bash" if keep_open else ""}"',
            "xfce4-terminal": f'--hold --command="{command}"'
            if keep_open
            else f'--command="{command}"',
            "konsole": f'--hold -e bash -c "{command}"' if keep_open else f'-e bash -c "{command}"',
            "xterm": f'-hold -e bash -c "{command}"' if keep_open else f'-e bash -c "{command}"',
            "terminator": f'-x bash -c "{command}; bash"'
            if keep_open
            else f'-x bash -c "{command}"',
        }

        final_args = terminal_args.get(terminal_cmd, f'-e bash -c "{command}"')
        full_cmd = f"{terminal_cmd} {final_args}"

        log.debug(f"Launch Command: {full_cmd}")
        subprocess.Popen(full_cmd, shell=True)

        return True

    except Exception as e:
        log.error(f"Failed to launch terminal command: {str(e)}", exc_info=True)
        return False


def shell_quote(arg: str) -> str:
    """Quote a string for safe shell usage across platforms."""
    if _IS_WINDOWS:
        if not arg:
            return '""'

        special_chars = r' \t&()[]{}^=;!\'`+,"~<>|%'
        arg = arg.replace('"', '""')

        if not any(c in special_chars for c in arg):
            return arg

        arg = re.sub(r"([&(){}\[\]^=;!+,\`~<>|%])", r"^\1", arg)

        return f'"{arg}"'
    else:
        return shlex.quote(arg)


def launch_cmd(
    command: str,
    title: Optional[str] = None,
    keep_open: bool = True,
) -> None:
    """Launch a command in a new terminal window with optional title."""
    terminator = "/k" if keep_open else "/c"
    command_parts = []

    if title:
        safe_title = (
            title.replace('"', "")
            .replace("&", "")
            .replace("|", "")
            .replace(">", "")
            .replace("<", "")
        )
        command_parts.append(f'title "{safe_title}"')
    command_parts.append(command)

    inner_command = " & ".join(command_parts)
    full_command = f'start "" cmd {terminator} "{inner_command}"'

    log.debug(f"Launching on Windows: {full_command}")
    subprocess.Popen(full_command, shell=True)


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


def get_default_render_output_path() -> Path:
    """Get the default temporary directory path for renders."""
    return Path(tempfile.gettempdir())


def logical_width(width: int) -> int:
    """Convert screen width to logical width based on UI scale and DPI."""
    if not width:
        return 0

    ui_scale = bpy.context.preferences.system.ui_scale
    dpi = bpy.context.preferences.system.dpi

    logical_width = width / (ui_scale * dpi / 72.0)

    return int(logical_width)
