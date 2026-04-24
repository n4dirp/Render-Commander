"""This module is responsible for the programmatic construction of python and executable render scripts."""

import json
import logging
import shlex
import sys
import stat
from datetime import datetime
from pathlib import Path

import bpy

from ..utils.constants import (
    ADDON_VERSION_STR,
    BLENDER_VERSION_STR,
    MODE_SINGLE,
    MODE_SEQ,
    MODE_LIST,
    RE_CYCLES,
    RE_EEVEE_NEXT,
    RE_EEVEE,
)
from ..utils.helpers import (
    get_addon_temp_dir,
    get_render_engine,
    calculate_auto_width,
    calculate_auto_height,
    open_folder,
)


log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
ADDON_INFO = f"Render Commander v{ADDON_VERSION_STR} - Blender v{BLENDER_VERSION_STR}"


def _wrap_in_try(lines, section_name, abort_on_fail=False) -> list[str]:
    """Wraps a list of generated script lines in a try/except block."""
    if not lines:
        return []

    wrapped = ["try:"]
    for line in lines:
        # Add 4 spaces of indentation, but leave empty lines blank to avoid trailing spaces
        wrapped.append(f"    {line}" if line.strip() else "")

    if abort_on_fail:
        wrapped.extend(
            [
                "except Exception as e:",
                f"    raise RuntimeError(f'Render Commander FATAL Error: Failed to apply {section_name} -> {{e}}') from e",
                "",
            ]
        )
    else:
        wrapped.extend(
            [
                "except Exception as e:",
                f"    print(f'Render Commander Warning: Failed to apply {section_name} -> {{e}}')",
                "",
            ]
        )
    return wrapped


def _load_template_script(template_name) -> list[str]:
    """Load a template script from the operators directory."""
    template_path = Path(__file__).parent / "templates" / template_name

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        log.error("Template not found: %s", template_path)
        return []


def _generate_base_script(
    context, prefs, selected_ids, is_animation, frame_start, frame_end, frame_step, start_msg
) -> list[str]:
    """Generate common script parts for both single and parallel rendering."""
    script_lines = []

    settings = context.window_manager.recom_render_settings

    # Start Script
    script_lines.extend(
        [
            f'"""{ADDON_INFO}"""',
            "",
            "import bpy",
            "",
        ]
    )

    if start_msg:
        script_lines.append(f'print("{start_msg}")')
        script_lines.append("")

    _add_render_time_tracking(prefs, script_lines)
    _apply_data_path_overrides(settings, script_lines)
    _apply_motion_blur_settings(settings, script_lines)
    _apply_frame_settings(prefs, is_animation, frame_start, frame_end, frame_step, script_lines)
    _apply_camera_settings(settings, script_lines)
    _apply_resolution_settings(context, settings, script_lines)
    _apply_output_format_settings(settings, script_lines)
    _apply_compositing_settings(settings, script_lines)

    render_engine = get_render_engine(context)
    if render_engine == RE_CYCLES:
        _apply_cycles_settings(prefs, settings, selected_ids, script_lines)
    elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
        _apply_eevee_settings(settings, script_lines)

    return script_lines


def _apply_data_path_overrides(settings, script_lines):
    """Add data paths overrides."""
    try:
        if not settings.override_settings.use_data_path_overrides:
            return

        overrides = settings.override_settings.data_path_overrides
        if not overrides:
            return

        script_lines.append("# Custom API Overrides")
        for item in overrides:
            path = item.data_path

            # Format the value for insertion into the script correctly
            if item.prop_type == "BOOL":
                val_str = str(item.value_bool)
            elif item.prop_type == "INT":
                val_str = str(item.value_int)
            elif item.prop_type == "FLOAT":
                val_str = str(item.value_float)
            elif item.prop_type == "STRING":
                val_str = repr(item.value_string)  # Safer than f"'{...}'"
            elif item.prop_type == "VECTOR_3":
                val_str = str(tuple(item.value_vector_3))
            elif item.prop_type == "COLOR_4":
                val_str = str(tuple(item.value_color_4))
            else:
                log.warning("Unknown property type %s for override %s", item.prop_type, path)
                val_str = "None"

            # Apply using try/except to avoid script crashes on faulty custom setups
            script_lines.extend(
                [
                    "try:",
                    f"    {path} = {val_str}",
                    "except Exception as e:",
                    f"    print(f'Failed to apply custom override {path}: {{e}}')",
                ]
            )
        script_lines.append("")
    except Exception as e:
        log.error("Error applying data path overrides: %s", e, exc_info=True)


def _add_render_time_tracking(prefs, script_lines):
    """Add script lines for tracking render time for animation and frame list."""
    if not prefs.track_render_time:
        return

    generated_lines = []

    if prefs.launch_mode == MODE_SEQ:
        # Load the template lines
        generated_lines.extend(_load_template_script("render_time.py"))
        if generated_lines:
            script_lines.extend(_wrap_in_try(generated_lines, "Render Time Tracking"))
            script_lines.append("")

    elif prefs.launch_mode == MODE_LIST:
        script_lines.extend(
            [
                "import time",
                "",
                "start_time = time.time()",
                "",
            ]
        )


def _apply_motion_blur_settings(settings, script_lines):
    """Apply motion blur override settings."""
    if settings.override_settings.motion_blur_override:
        lines = [
            f"bpy.context.scene.render.use_motion_blur = {settings.override_settings.use_motion_blur}",
            f"bpy.context.scene.render.motion_blur_position = '{settings.override_settings.motion_blur_position}'",
            f"bpy.context.scene.render.motion_blur_shutter = {settings.override_settings.motion_blur_shutter}",
            "",
        ]
        script_lines.append("# Motion Blur Settings")
        script_lines.extend(lines)


def _apply_frame_settings(prefs, is_animation, frame_start, frame_end, frame_step, script_lines):
    """Apply frame start, end, and step settings."""
    lines = []
    if is_animation:
        lines.extend(
            [
                f"bpy.context.scene.frame_start = {frame_start}",
                f"bpy.context.scene.frame_end = {frame_end}",
                f"bpy.context.scene.frame_step = {frame_step}",
                "",
            ]
        )
    else:
        lines.append(f"bpy.context.scene.frame_set({frame_start})")
        lines.append("")

    if prefs.launch_mode != MODE_LIST:
        script_lines.append("# Frame Settings")
        script_lines.extend(lines)


def _apply_camera_settings(settings, script_lines):
    """Apply camera overrides."""
    if not settings.override_settings.cameras_override:
        return

    lines = []

    # Depth of Field Settings
    if settings.override_settings.override_dof:
        lines.extend(
            [
                "for obj in bpy.data.objects:",
                "    if obj.type == 'CAMERA':",
                f"        obj.data.dof.use_dof = {bool(settings.override_settings.use_dof == 'ENABLED')}",
                "",
            ]
        )

    # Lens Shift
    set_camera_shift = (
        settings.override_settings.camera_shift_x != 0.0 or settings.override_settings.camera_shift_y != 0.0
    )
    if set_camera_shift:
        lines.extend(
            [
                "for obj in bpy.data.objects:",
                "    if obj.type == 'CAMERA':",
                f"        obj.data.shift_x += {settings.override_settings.camera_shift_x}",
                f"        obj.data.shift_y += {settings.override_settings.camera_shift_y}",
                "",
            ]
        )

    if lines:
        script_lines.append("# Camera Settings")
        script_lines.extend(_wrap_in_try(lines, "Camera Settings", True))


def _apply_resolution_settings(context, settings, script_lines):
    """Apply overrides: resolution, scale, camera shift, and overscan settings."""
    if not settings.override_settings.format_override:
        return

    try:
        script_lines.append("# Format Settings")
        lines = []

        if settings.override_settings.resolution_override:
            resolution_mode = settings.override_settings.resolution_mode
            if resolution_mode == "SET_WIDTH":
                base_x = settings.override_settings.resolution_x
                try:
                    base_y = calculate_auto_height(context)
                except Exception as e:
                    log.warning("Failed to calculate auto height: %s", e)
                    base_y = settings.override_settings.resolution_y
            elif resolution_mode == "SET_HEIGHT":
                base_y = settings.override_settings.resolution_y
                try:
                    base_x = calculate_auto_width(context)
                except Exception as e:
                    log.warning("Failed to calculate auto width: %s", e)
                    base_x = settings.override_settings.resolution_x
            else:
                base_x = settings.override_settings.resolution_x
                base_y = settings.override_settings.resolution_y

            # Prevent zero scaling crash
            scale = max(1.0, float(settings.override_settings.custom_render_scale)) / 100.0

            scaled_x = int(round(base_x * scale / 2) * 2)
            scaled_y = int(round(base_y * scale / 2) * 2)
            lines.extend(
                [
                    f"bpy.context.scene.render.resolution_x = {scaled_x}",
                    f"bpy.context.scene.render.resolution_y = {scaled_y}",
                    "bpy.context.scene.render.resolution_percentage = 100",
                    "",
                ]
            )
        else:
            # Apply scale settings safely
            scale = max(1.0, float(settings.override_settings.custom_render_scale))
            lines.extend(
                [
                    f"scale_factor = {scale} / 100.0",
                    "base_x = bpy.context.scene.render.resolution_x",
                    "base_y = bpy.context.scene.render.resolution_y",
                    # Calculate new resolution, ensuring even numbers for encoding safety
                    "bpy.context.scene.render.resolution_x = int(round(base_x * scale_factor / 2) * 2)",
                    "bpy.context.scene.render.resolution_y = int(round(base_y * scale_factor / 2) * 2)",
                    "bpy.context.scene.render.resolution_percentage = 100",
                    "",
                ]
            )

        # Apply overscan settings
        if settings.override_settings.use_overscan:
            # Calculate overscan value based on type
            if settings.override_settings.overscan_type == "PERCENTAGE":
                lines.extend(
                    [
                        "base_res_x = bpy.context.scene.render.resolution_x",
                        "base_res_y = bpy.context.scene.render.resolution_y",
                        f"overscan_x = int(base_res_x * {settings.override_settings.overscan_percent} / 100)",
                        f"overscan_y = int(base_res_y * {settings.override_settings.overscan_percent} / 100)",
                    ]
                )
            else:  # PIXELS
                if settings.override_settings.overscan_uniform:
                    lines.append(f"overscan_x = overscan_y = {settings.override_settings.overscan_width}")
                else:
                    lines.extend(
                        [
                            f"overscan_x = {settings.override_settings.overscan_width}",
                            f"overscan_y = {settings.override_settings.overscan_height}",
                        ]
                    )

            lines.extend(
                [
                    "original_resolution = (bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y)",
                    "",
                ]
            )

            # Apply camera shift settings
            set_camera_shift = settings.override_settings.cameras_override and (
                settings.override_settings.camera_shift_x != 0.0 or settings.override_settings.camera_shift_y != 0.0
            )

            if set_camera_shift:
                lines.extend(
                    [
                        "scale_x = original_resolution[0] / max(1, (original_resolution[0] + 2 * overscan_x))",
                        "scale_y = original_resolution[1] / max(1, (original_resolution[1] + 2 * overscan_y))",
                    ]
                )

            # Apply camera shift and lens scaling
            lines.extend(
                [
                    "for obj in bpy.data.objects:",
                    "    if obj.type == 'CAMERA':",
                    "        obj.data.lens = obj.data.lens * (original_resolution[0] / max(1, (original_resolution[0] + 2 * overscan_x)))",
                    "",
                ]
            )

            if set_camera_shift:
                lines.extend(
                    [
                        "        obj.data.shift_x *= scale_x",
                        "        obj.data.shift_y *= scale_y",
                        "",
                    ]
                )

            # Update render resolution
            lines.extend(
                [
                    "bpy.context.scene.render.resolution_x = original_resolution[0] + 2 * overscan_x",
                    "bpy.context.scene.render.resolution_y = original_resolution[1] + 2 * overscan_y",
                    "",
                ]
            )

        script_lines.extend(_wrap_in_try(lines, "Resolution and Format Settings", True))

    except Exception as e:
        log.error("Error applying resolution settings: %s", e, exc_info=True)


def _apply_output_format_settings(settings, script_lines):
    """Apply file format override settings."""
    try:
        if settings.override_settings.file_format_override:
            script_lines.append("# File Format Settings")
            lines = []

            if settings.override_settings.file_format == "OPEN_EXR_MULTILAYER":
                media_type_val = "MULTI_LAYER_IMAGE"
            else:
                media_type_val = "IMAGE"

            # Blender 5.0 - New media_type
            lines.extend(
                [
                    "if bpy.app.version >= (5, 0, 0):",
                    f"    bpy.context.scene.render.image_settings.media_type = '{media_type_val}'",
                ]
            )

            lines.append(
                f"bpy.context.scene.render.image_settings.file_format = '{settings.override_settings.file_format}'"
            )
            if settings.override_settings.file_format in [
                "OPEN_EXR",
                "OPEN_EXR_MULTILAYER",
                "PNG",
                "TIFF",
            ]:
                lines.append(
                    f"bpy.context.scene.render.image_settings.color_depth = '{settings.override_settings.color_depth}'"
                )

            if settings.override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
                lines.append(
                    f"bpy.context.scene.render.image_settings.exr_codec = '{settings.override_settings.codec}'"
                )
            elif settings.override_settings.file_format == "JPEG":
                lines.append(
                    f"bpy.context.scene.render.image_settings.quality = {settings.override_settings.jpeg_quality}"
                )

            script_lines.extend(_wrap_in_try(lines, "Output Format Settings", True))

    except Exception as e:
        log.error("Error applying output format settings: %s", e, exc_info=True)


def _apply_compositing_settings(settings, script_lines):
    """Apply compositing override settings."""
    if settings.override_settings.compositor_override:
        lines = []
        lines.extend(
            [
                "# Compositor Settings",
                f"bpy.context.scene.render.use_compositing = {settings.override_settings.use_compositor}",
                f"bpy.context.scene.render.compositor_device = '{settings.override_settings.compositor_device}'",
                "",
            ]
        )

        if settings.override_settings.compositor_disable_output_files and settings.override_settings.use_compositor:
            lines.extend(
                [
                    "# Disable File Output",
                    'node_tree = getattr(bpy.context.scene, "compositing_node_group", getattr(bpy.context.scene, "node_tree", None))',
                    "if node_tree:",
                    "    for node in node_tree.nodes:",
                    "        if node.type == 'OUTPUT_FILE':",
                    "            node.mute = True",
                    "",
                ]
            )

        script_lines.extend(_wrap_in_try(lines, "Compositor Settings", True))


def _apply_cycles_settings(prefs, settings, selected_ids, script_lines):
    """Apply Cycles-specific rendering settings."""
    try:
        override_settings = settings.override_settings

        if not (
            prefs.manage_cycles_devices
            or override_settings.cycles.device_override
            or override_settings.cycles.sampling_override
            or override_settings.cycles.performance_override
        ):
            return

        script_lines.append("# Cycles Settings")
        lines = []
        lines.append(f"if bpy.context.scene.render.engine == '{RE_CYCLES}':")

        # Apply compute device override
        if override_settings.cycles.device_override:
            lines.append(f"    bpy.context.scene.cycles.device = '{override_settings.cycles.device}'")
            lines.append("")

        _apply_cycles_device_settings(prefs, selected_ids, lines)
        _apply_cycles_sampling_settings(override_settings, lines)
        _apply_cycles_performance_settings(override_settings, lines)

        # Wrap all Cycles code together
        script_lines.extend(_wrap_in_try(lines, "Cycles Overrides", True))

    except Exception as e:
        log.error("Error applying Cycles settings: %s", e, exc_info=True)


def _apply_cycles_sampling_settings(override_settings, lines):
    """Apply Cycles sampling settings."""
    if not override_settings.cycles.sampling_override:
        return

    cycles = override_settings.cycles

    if cycles.sampling_mode == "FACTOR":
        factor = float(cycles.sampling_factor)
        lines.extend(
            [
                "    # Sampling Factor Override",
                f"    quality_factor = {factor}",
                "    bpy.context.scene.cycles.samples = max(1, int(bpy.context.scene.cycles.samples * quality_factor))",
                "    bpy.context.scene.cycles.adaptive_min_samples = int(bpy.context.scene.cycles.adaptive_min_samples * quality_factor)",
                "    # Noise scales by the inverse square root of samples",
                "    bpy.context.scene.cycles.adaptive_threshold = bpy.context.scene.cycles.adaptive_threshold / max(0.0001, (quality_factor ** 0.5))",
                "    bpy.context.scene.cycles.time_limit = bpy.context.scene.cycles.time_limit * quality_factor",
                "",
            ]
        )
    else:
        # CUSTOM MODE
        noise_threshold_value = float(cycles.adaptive_threshold)
        lines.extend(
            [
                f"    bpy.context.scene.cycles.use_adaptive_sampling = {cycles.use_adaptive_sampling}",
                f"    bpy.context.scene.cycles.adaptive_threshold = {noise_threshold_value}",
                f"    bpy.context.scene.cycles.samples = {int(cycles.samples)}",
                f"    bpy.context.scene.cycles.adaptive_min_samples = {cycles.adaptive_min_samples}",
                f"    bpy.context.scene.cycles.time_limit = {cycles.time_limit}",
                "",
            ]
        )

    if cycles.use_denoising:
        lines.extend(
            [
                f"    bpy.context.scene.cycles.use_denoising = {cycles.use_denoising}",
                f"    bpy.context.scene.cycles.denoiser = '{cycles.denoiser}'",
                f"    bpy.context.scene.cycles.denoising_input_passes = '{cycles.denoising_input_passes}'",
                "",
            ]
        )

        if cycles.denoiser == "OPENIMAGEDENOISE":
            lines.extend(
                [
                    f"    bpy.context.scene.cycles.denoising_prefilter = '{cycles.denoising_prefilter}'",
                    f"    bpy.context.scene.cycles.denoising_quality = '{cycles.denoising_quality}'",
                    f"    bpy.context.scene.cycles.denoising_use_gpu = {cycles.denoising_use_gpu}",
                    "",
                ]
            )


def _apply_cycles_performance_settings(override_settings, lines):
    """Apply Cycles performance settings."""
    if not override_settings.cycles.performance_override:
        return

    cycles = override_settings.cycles
    lines.extend(
        [
            f"    bpy.context.scene.cycles.use_auto_tile = {cycles.use_tiling}",
            f"    bpy.context.scene.cycles.tile_size = {cycles.tile_size}",
            f"    bpy.context.scene.render.use_persistent_data = {cycles.persistent_data}",
            "",
        ]
    )


def _apply_cycles_device_settings(prefs, selected_ids, lines):
    """Apply Cycles device settings."""
    if not prefs.manage_cycles_devices:
        return

    if prefs.multiple_backends and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel:
        devices = getattr(prefs, "devices", [])
        # Get the first enabled device matching selected_ids
        match = next((d for d in devices if d.id in selected_ids and d.use), None)
        backend_type = match.type if match else "CPU"  # "CPU" resolves to "NONE" below
    else:
        backend_type = prefs.compute_device_type

    cycles_backend = "NONE" if backend_type == "CPU" else backend_type

    formatted_ids = json.dumps(list(selected_ids), indent=4).replace("\n", "\n            ")

    lines.extend(
        [
            "    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences",
            "    is_gpu = bpy.context.scene.cycles.device == 'GPU'",
            "",
            "    if is_gpu:",
            f"        cycles_prefs.compute_device_type = '{cycles_backend}'",
            f"        selected_ids = {formatted_ids}",
            "        for d in cycles_prefs.devices:",
            "            d.use = d.id in selected_ids",
            "        active_devices = [d for d in cycles_prefs.devices if d.use]",
            "    else:",
            "        active_devices = [d for d in cycles_prefs.devices if d.type == 'CPU']",
            "",
            "    # Print enabled devices",
            "    if active_devices:",
            "        prefix = 'Devices: ' if is_gpu else 'Device: '",
            "        for i, d in enumerate(active_devices):",
            "            indent = prefix if i == 0 else '\\t '",
            "            print(f'{indent}{d.name} ({d.type}) [{d.id}]')",
            "    elif not is_gpu:",
            "        print('Device: CPU')",
            "",
        ]
    )


def _apply_eevee_settings(settings, script_lines):
    """Add EEVEE override settings."""
    override_settings = settings.override_settings
    if not override_settings.eevee_override:
        return

    script_lines.append("# EEVEE Settings")
    eevee = override_settings.eevee

    lines = [
        f"if bpy.context.scene.render.engine in {{'{RE_EEVEE_NEXT}', '{RE_EEVEE}'}}:",
        f"    bpy.context.scene.eevee.taa_render_samples = {eevee.samples}",
        "",
    ]

    script_lines.extend(lines)


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


def _resolve_script_base_name(blend_name: str, settings, prefs) -> str:
    """Resolve the base filename for generated scripts based on preferences."""
    parts = []
    LAUNCH_MODE_MAP = {
        MODE_SINGLE: "Still",
        MODE_SEQ: "Animation",
        MODE_LIST: "List",
    }

    if prefs.use_blend_name_in_script:
        parts.append(blend_name)
    if prefs.use_render_type_in_script:
        render_type = LAUNCH_MODE_MAP.get(prefs.launch_mode)
        parts.append(render_type)
    if prefs.use_export_date_in_script:
        parts.append(datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    parts.append(settings.render_id)

    return "_".join(parts)


def _create_process_files(self, prefs, settings, blend_file, script_lines, process_id, target_dir) -> Path | None:
    """Creates the .py script and the OS-specific shell/batch script."""
    blend_name = Path(blend_file).stem
    sanitized_blend_name = bpy.path.clean_name(blend_name)
    base_name = _resolve_script_base_name(sanitized_blend_name, settings, prefs)

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

    # OS-specific helpers
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

    # Platform-specific header construction
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

    # Shared variable assignments
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
        shell_content.append(set_env("OCIO", bpy.path.abspath(prefs.ocio_path), export=True))

    # Additional Scripts
    def add_script_vars(order: str):
        idx = 1
        for entry in prefs.additional_scripts:
            if entry.order == order and entry.script_path:
                abs_path = Path(bpy.path.abspath(entry.script_path)).resolve()
                if abs_path.is_file():
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

    # Render Commander Script
    cmd_parts.append(f"--python {ref_env('RC_SCRIPT')}")

    for i in range(1, post_c + 1):
        cmd_parts.append(f"--python {ref_env(f'RC_POST_SCRIPT_{i}')}")

    # Handle Custom Arguments
    if prefs.add_command_line_args and prefs.custom_command_line_args.strip():
        cmd_parts.append(prefs.custom_command_line_args.strip())

    # Blender Render Debugging
    if prefs.cmd_debug:
        cmd_parts.append("--debug")

        if prefs.debug_value != 0:
            cmd_parts.append(f"--debug-value {prefs.debug_value}")

        if prefs.verbose_level != "2":
            cmd_parts.append(f"--verbose {prefs.verbose_level}")

        if prefs.debug_cycles and get_render_engine(bpy.context) == RE_CYCLES:
            cmd_parts.append("--debug-cycles")

    # Log Redirection
    if prefs.log_to_file:
        log_file_path = str(_get_log_file_path(prefs, blend_file, log_filename, target_dir))
        shell_content.append(set_env("RC_LOG", log_file_path))
        cmd_parts.append(f"--log-file {ref_env('RC_LOG')}")

    # Format the command string across multiple lines for readability
    line_continue = " ^" if _IS_WINDOWS else " \\"
    cmd_str = f"{line_continue}\n    ".join(cmd_parts)

    shell_content.extend(["", f'echo "Executing Render: {blend_name} ({settings.render_id} - worker{process_id})"'])
    if prefs.log_to_file:
        shell_content.append(f"echo Log written to: {ref_env('RC_LOG')}")

    shell_content.extend(["", cmd_str, ""])

    # Pause/Cleanup logic
    if prefs.keep_terminal_open:
        shell_content.append("pause" if _IS_WINDOWS else 'read -p "Press enter to exit..."')

    shell_content.append("exit")

    # Write File
    exec_path = target_dir / exec_filename
    try:
        exec_path.write_text("\n".join(shell_content), encoding="utf-8")
        if not _IS_WINDOWS:
            current_mode = exec_path.stat().st_mode
            exec_path.chmod(current_mode | stat.S_IEXEC)
    except (OSError, IOError) as exc:
        self.report({"ERROR"}, f"Failed to save execution file: {exc}")
        return None

    # Open scripts folder
    if prefs.auto_open_exported_folder and not settings.folder_opened:
        settings.folder_opened = True
        open_folder(target_dir)

    return exec_path
