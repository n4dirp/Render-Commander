"""Creates .py scripts and OS-specific shell/batch wrapper files."""

import logging
import shlex
import stat
import sys
from datetime import datetime
from pathlib import Path

import bpy

from ...utils.helpers import get_addon_temp_dir, open_folder
from . import python_script

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
ADDON_INFO = python_script.ADDON_INFO
SAFE_MAX_LENGTH = 180


def _get_log_file_path(prefs, blend_file, log_filename: str, target_dir=None) -> str:
    """Determine the log folder based on preferences and return the full log file path."""
    if not prefs.log_to_file:
        return ""

    def _ensure_dir(path: Path) -> Path:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise OSError(f"Failed to create log directory '{path}'.") from exc
        return path

    logs_folder_name_str = prefs.logs_folder_name if prefs.save_to_log_folder else ""

    if prefs.log_to_file_location == "EXECUTION_FILES" and target_dir:
        log_folder = _ensure_dir(Path(target_dir) / logs_folder_name_str)

    elif prefs.log_to_file_location == "BLEND_PATH":
        base_folder = Path(blend_file).parent.resolve()
        log_folder = _ensure_dir(base_folder / logs_folder_name_str)

    elif prefs.log_to_file_location == "CUSTOM_PATH":
        custom_path_str = prefs.log_custom_path.strip()
        if custom_path_str:
            custom_path = Path(bpy.path.abspath(custom_path_str))
        else:
            custom_path = Path(get_addon_temp_dir())

        log_folder = _ensure_dir(custom_path / logs_folder_name_str)
    else:
        return ""

    return str(log_folder / log_filename)


def _format_frame_range(frames) -> str:
    """Format frame input into a filename-safe string with prefix."""
    prefix = "f"

    if isinstance(frames, list):
        if not frames:
            return f"{prefix}_empty"

        sorted_frames = sorted(set(map(int, frames)))
        ranges = []

        start = end = sorted_frames[0]

        for num in sorted_frames[1:]:
            if num == end + 1:
                end = num
            else:
                ranges.append((start, end))
                start = end = num

        ranges.append((start, end))

        formatted = [f"{s}" if s == e else f"{s}-{e}" for s, e in ranges]

        return f"{prefix}_" + "_".join(formatted)

    elif isinstance(frames, tuple):
        start, end, step = frames

        if start == end:
            return f"{prefix}_{start}"

        result = f"{prefix}_{start}-{end}"
        if step > 1:
            result += f"_s{step}"

        return result

    return f"{prefix}_unknown"


def _resolve_script_base_name(blend_name: str, settings, prefs, frames) -> str:
    """Build a safe, readable base filename for generated scripts."""
    from ...utils.constants import MODE_LIST, MODE_SEQ, MODE_SINGLE

    LAUNCH_MODE_MAP = {
        MODE_SINGLE: "Still",
        MODE_SEQ: "Animation",
        MODE_LIST: "List",
    }

    def _add(parts, value):
        if value:
            parts.append(str(value))

    parts = []

    if prefs.use_export_date_in_script:
        _add(parts, datetime.now().strftime("%m-%d_%H%M%S"))

    if prefs.use_blend_name_in_script:
        _add(parts, bpy.path.clean_name(blend_name))

    if prefs.use_render_type_in_script:
        _add(parts, LAUNCH_MODE_MAP.get(prefs.launch_mode))

    if prefs.custom_script_tag and prefs.custom_script_text:
        _add(parts, bpy.path.clean_name(prefs.custom_script_text))

    render_id = settings.render_id
    _add(parts, render_id)

    if prefs.use_frame_range_in_script:
        _add(parts, _format_frame_range(frames))

    base_name = "_".join(parts)

    if len(base_name) <= SAFE_MAX_LENGTH:
        return base_name

    pivot = base_name.rfind(render_id)

    if pivot == -1:
        return _truncate_simple(base_name)

    prefix = base_name[:pivot].rstrip("_")
    suffix = base_name[pivot:]

    available = SAFE_MAX_LENGTH - len(suffix)

    if available <= 0:
        return _truncate_simple(suffix)

    truncated_prefix = _truncate_with_ellipsis(prefix, available)

    return f"{truncated_prefix}_{suffix}" if truncated_prefix else suffix


def _truncate_simple(value: str) -> str:
    """Hard truncate with ellipsis."""
    if len(value) <= SAFE_MAX_LENGTH:
        return value
    return value[: SAFE_MAX_LENGTH - 3].rstrip("_") + "..."


def _truncate_with_ellipsis(value: str, max_len: int) -> str:
    """Truncate preserving readability."""
    if len(value) <= max_len:
        return value

    if max_len <= 3:
        return value[:max_len]

    return value[: max_len - 3].rstrip("_") + "..."


def create_process_files(
    self, prefs, settings, blend_file, script_lines, process_id, target_dir, frames
) -> Path | None:
    """Creates the .py script and the OS-specific shell/batch script."""
    blend_name = Path(blend_file).stem
    sanitized_blend_name = bpy.path.clean_name(blend_name)
    base_name = _resolve_script_base_name(sanitized_blend_name, settings, prefs, frames)

    exec_extension = ".bat" if _IS_WINDOWS else ".sh"

    py_filename = f"{base_name}_script{process_id}.py"
    exec_filename = f"{base_name}_worker{process_id}{exec_extension}"
    log_filename = f"{base_name}_worker{process_id}.log"

    try:
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        py_path = target_dir / py_filename
        py_path.write_text("\n".join(script_lines), encoding="utf-8")
    except (OSError, IOError) as exc:
        self.report({"ERROR"}, f"Failed to save python script: {exc}")
        return None

    # Determine Shell/Batch Script Content
    blender_exec = str(bpy.app.binary_path)
    shell_content = []

    def set_env(var: str, val: str, is_path_expr: bool = False, export: bool = False) -> str:
        if _IS_WINDOWS:
            if not is_path_expr:
                val = val.replace("%", "%%")
            return f'set "{var}={val}"'
        prefix = "export " if export else ""
        safe_val = f'"{val}"' if is_path_expr else shlex.quote(val)
        return f"{prefix}{var}={safe_val}"

    def ref_env(var: str) -> str:
        return f'"%{var}%"' if _IS_WINDOWS else f'"${var}"'

    if _IS_WINDOWS:
        shell_content.extend(
            [
                "@echo off",
                f"REM {ADDON_INFO}",
                "",
                'cd /d "%~dp0"',
                "",
            ]
        )
        rc_script_val = f"%~dp0{py_filename}"
        script_check = [
            'if not exist "%RC_SCRIPT%" (',
            '    echo ERROR: Script not found: "%RC_SCRIPT%"',
            "    exit /b 1",
            ")",
        ]
    else:
        shell_content.extend(
            [
                "#!/bin/bash",
                f"# {ADDON_INFO}",
                "",
                'cd "$(dirname "$0")"',
                "",
            ]
        )
        rc_script_val = f"$(pwd)/{py_filename}"
        script_check = [
            'if [ ! -f "$RC_SCRIPT" ]; then',
            '    echo "ERROR: Script not found: $RC_SCRIPT"',
            "    exit 1",
            "fi",
        ]

    shell_content.extend(
        [
            set_env("RC_BLENDER", blender_exec),
            set_env("RC_BLEND", str(blend_file)),
            set_env("RC_SCRIPT", rc_script_val, is_path_expr=True),
            "",
        ]
    )
    shell_content.extend(script_check)

    if prefs.set_ocio and prefs.ocio_path:
        ocio_path = Path(bpy.path.abspath(prefs.ocio_path))
        if ocio_path.exists() and ocio_path.suffix.lower() == ".ocio":
            shell_content.append(set_env("OCIO", str(ocio_path), export=True))
        else:
            log.warning('Invalid OCIO path: "%s"', prefs.ocio_path)

    def add_script_vars(order: str):
        idx = 1
        for entry in prefs.additional_scripts:
            if entry.order == order and entry.script_path:
                abs_path = Path(bpy.path.abspath(entry.script_path)).resolve()
                if abs_path.is_file() and abs_path.suffix.lower() == ".py":
                    shell_content.append(set_env(f"RC_{order}_SCRIPT_{idx}", str(abs_path)))
                    idx += 1
        return idx - 1

    pre_c = add_script_vars("PRE") if prefs.append_python_scripts else 0
    post_c = add_script_vars("POST") if prefs.append_python_scripts else 0

    cmd_parts = [
        ref_env("RC_BLENDER"),
        f"--background {ref_env('RC_BLEND')}",
    ]

    for i in range(1, pre_c + 1):
        cmd_parts.append(f"--python {ref_env(f'RC_PRE_SCRIPT_{i}')}")

    cmd_parts.append(f"--python {ref_env('RC_SCRIPT')}")

    for i in range(1, post_c + 1):
        cmd_parts.append(f"--python {ref_env(f'RC_POST_SCRIPT_{i}')}")

    if prefs.add_command_line_args and prefs.custom_command_line_args.strip():
        cmd_parts.append(prefs.custom_command_line_args.strip())

    if prefs.log_to_file:
        log_file_path = str(_get_log_file_path(prefs, blend_file, log_filename, target_dir))
        shell_content.append(set_env("RC_LOG", log_file_path))
        cmd_parts.append(f"--log-file {ref_env('RC_LOG')}")

    line_continue = " ^" if _IS_WINDOWS else " \\"
    cmd_str = f"{line_continue}\n    ".join(cmd_parts)

    shell_content.extend(
        [
            "",
            f'echo "Executing Render: {blend_name} ({settings.render_id} - worker{process_id})"',
        ]
    )
    if prefs.log_to_file:
        shell_content.append(f"echo Log written to: {ref_env('RC_LOG')}")

    if prefs.parallel_delay > 0 and process_id > 0:
        delay_time = prefs.parallel_delay * process_id
        delay_display = f"{int(delay_time)}s" if delay_time == int(delay_time) else f"{delay_time}s"

        if _IS_WINDOWS:
            shell_content.append(f"echo [Worker {process_id}] Waiting {delay_display}...")
            shell_content.append(f"timeout /t {int(delay_time)} /nobreak")
            shell_content.append(f"echo [Worker {process_id}] Wait complete. Starting render...")
        else:
            shell_content.append(f'echo "[Worker {process_id}] Waiting {delay_display}..."')
            shell_content.append(f"sleep {delay_time}")
            shell_content.append(f'echo "[Worker {process_id}] Wait complete. Starting render..."')

    shell_content.extend(["", cmd_str, ""])

    if prefs.keep_terminal_open:
        shell_content.append("pause" if _IS_WINDOWS else 'read -p "Press enter to exit..."')

    shell_content.append("exit")

    exec_path = target_dir / exec_filename
    try:
        exec_path.write_text("\n".join(shell_content), encoding="utf-8")
        if not _IS_WINDOWS:
            current_mode = exec_path.stat().st_mode
            exec_path.chmod(current_mode | stat.S_IEXEC)
    except (OSError, IOError) as exc:
        self.report({"ERROR"}, f"Failed to save execution file: {exc}")
        return None

    if prefs.auto_open_exported_folder and not settings.folder_opened:
        settings.folder_opened = True
        open_folder(target_dir)

    return exec_path
