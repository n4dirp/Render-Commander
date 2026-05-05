"""Programmatic construction of Python render script content."""

import json
import logging
import sys
from pathlib import Path

from ...utils.constants import (
    ADDON_VERSION_STR,
    BLENDER_VERSION_STR,
    MODE_LIST,
    MODE_SEQ,
    MODE_SINGLE,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
)
from ...utils.cycles_devices import get_cycles_prefs
from ...utils.helpers import (
    calculate_auto_height,
    calculate_auto_width,
    get_override_settings,
    get_render_engine,
)

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
ADDON_INFO = f"Render Commander v{ADDON_VERSION_STR} - Blender v{BLENDER_VERSION_STR}"
_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _load_template_script(template_name: str) -> list[str]:
    """Load a template script from the templates directory."""
    template_path = _TEMPLATE_DIR / template_name

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read().splitlines()
    except FileNotFoundError:
        log.error("Template not found: %s", template_path)
        return []


def _wrap_in_try(lines: list[str], section_name: str, abort_on_fail: bool = False) -> list[str]:
    """Wraps a list of generated script lines in a try/except block."""
    if not lines:
        return []

    wrapped = ["try:"]
    for line in lines:
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
                f"    log.error(f'Render Commander: Failed to apply {section_name} -> {{e}}')",
                "",
            ]
        )
    return wrapped


def _add_logging_formatter(script_lines: list[str]) -> None:
    generated_lines = _load_template_script("logging_formatter.py")
    if generated_lines:
        script_lines.extend(generated_lines)
        script_lines.append("")


def _add_render_time_tracking(prefs, script_lines: list[str]) -> None:
    """Add script lines for tracking render time for animation and frame list."""
    if not prefs.track_render_time:
        return

    if prefs.launch_mode == MODE_SEQ:
        generated_lines = _load_template_script("render_time.py")
        if generated_lines:
            script_lines.extend(_wrap_in_try(generated_lines, "Render Time Tracking"))
            script_lines.append("")
    elif prefs.launch_mode == MODE_LIST:
        script_lines.extend(
            [
                "start_time = time.time()",
                "",
            ]
        )


def _apply_motion_blur_settings(override_settings, script_lines: list[str]) -> None:
    """Apply motion blur override settings."""
    if not override_settings.motion_blur_override:
        return

    script_lines.append("# Motion Blur Settings")
    script_lines.append('log.info("Applying Motion Blur override")')
    lines = [
        f"bpy.context.scene.render.use_motion_blur = {override_settings.use_motion_blur}",
        f"bpy.context.scene.render.motion_blur_position = '{override_settings.motion_blur_position}'",
        f"bpy.context.scene.render.motion_blur_shutter = {override_settings.motion_blur_shutter}",
        "",
    ]
    script_lines.extend(lines)


def _apply_frame_settings(
    prefs, override_settings, is_animation, frame_start, frame_end, frame_step, script_lines: list[str]
) -> None:
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
        if override_settings.frame_range_override:
            script_lines.append('log.info(f"Applying Frame Range override")')
        script_lines.extend(lines)


def _apply_fps_converter_settings(override_settings, script_lines: list[str]) -> None:
    """Apply FPS converter / Time Remapping override settings."""
    if not override_settings.use_fps_converter:
        return

    script_lines.append("# FPS Converter / Time Remapping")
    script_lines.append('log.info("Applying FPS Converter override")')

    lines = [
        "original_fps = bpy.context.scene.render.fps",
    ]

    if override_settings.target_fps == "CUSTOM":
        lines.append(f"target_fps = {override_settings.custom_fps}")
    else:
        lines.append(f"target_fps = {override_settings.target_fps}")

    lines.extend(
        [
            "multiplier = target_fps / original_fps",
            "bpy.context.scene.render.frame_map_old = int(original_fps)",
            "bpy.context.scene.render.frame_map_new = int(target_fps)",
            "bpy.context.scene.render.fps = int(target_fps)",
            "bpy.context.scene.frame_start = int(bpy.context.scene.frame_start * multiplier)",
            "bpy.context.scene.frame_end = int(bpy.context.scene.frame_end * multiplier)",
            "",
        ]
    )

    if override_settings.preserve_motion_blur:
        lines.extend(
            [
                "# Preserve Motion Blur Absolute Time",
                "if bpy.context.scene.render.use_motion_blur:",
                "    old_shutter = bpy.context.scene.render.motion_blur_shutter",
                "    bpy.context.scene.render.motion_blur_shutter = old_shutter * multiplier",
                '    log.info(f"Motion blur shutter adjusted: {old_shutter:.3f} -> {bpy.context.scene.render.motion_blur_shutter:.3f}")',
            ]
        )

    script_lines.extend(_wrap_in_try(lines, "FPS Converter", True))


def _apply_camera_settings(override_settings, script_lines: list[str]) -> None:
    """Apply camera overrides."""
    if not override_settings.cameras_override:
        return

    lines = []

    if override_settings.override_dof:
        lines.extend(
            [
                "for obj in bpy.data.objects:",
                "    if obj.type == 'CAMERA':",
                f"        obj.data.dof.use_dof = {bool(override_settings.use_dof == 'ENABLED')}",
                "",
            ]
        )

    set_camera_shift = override_settings.camera_shift_x != 0.0 or override_settings.camera_shift_y != 0.0
    if set_camera_shift:
        lines.extend(
            [
                "for obj in bpy.data.objects:",
                "    if obj.type == 'CAMERA':",
                f"        obj.data.shift_x += {override_settings.camera_shift_x}",
                f"        obj.data.shift_y += {override_settings.camera_shift_y}",
                "",
            ]
        )

    if lines:
        script_lines.append("# Camera Settings")
        script_lines.append('log.info("Applying Camera override")')
        script_lines.extend(_wrap_in_try(lines, "Camera Settings", True))


def _apply_resolution_settings(context, override_settings, script_lines: list[str]) -> None:
    """Apply overrides: resolution, scale, camera shift, and overscan settings."""
    if not override_settings.format_override:
        return

    try:
        script_lines.append("# Format Settings")
        script_lines.append('log.info("Applying Resolution/Format override")')
        lines = []

        if override_settings.resolution_override:
            resolution_mode = override_settings.resolution_mode
            if resolution_mode == "SET_WIDTH":
                base_x = override_settings.resolution_x
                try:
                    base_y = calculate_auto_height(context)
                except Exception as e:
                    log.warning("Failed to calculate auto height: %s", e)
                    base_y = override_settings.resolution_y
            elif resolution_mode == "SET_HEIGHT":
                base_y = override_settings.resolution_y
                try:
                    base_x = calculate_auto_width(context)
                except Exception as e:
                    log.warning("Failed to calculate auto width: %s", e)
                    base_x = override_settings.resolution_x
            else:
                base_x = override_settings.resolution_x
                base_y = override_settings.resolution_y

            scale = max(1.0, float(override_settings.custom_render_scale)) / 100.0

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
            scale = max(1.0, float(override_settings.custom_render_scale))
            lines.extend(
                [
                    f"scale_factor = {scale} / 100.0",
                    "base_x = bpy.context.scene.render.resolution_x",
                    "base_y = bpy.context.scene.render.resolution_y",
                    "bpy.context.scene.render.resolution_x = int(round(base_x * scale_factor / 2) * 2)",
                    "bpy.context.scene.render.resolution_y = int(round(base_y * scale_factor / 2) * 2)",
                    "bpy.context.scene.render.resolution_percentage = 100",
                    "",
                ]
            )

        script_lines.extend(_wrap_in_try(lines, "Resolution and Format Settings", True))

    except Exception as e:
        log.error("Error applying resolution settings: %s", e, exc_info=True)


def _apply_overscan_settings(context, override_settings, script_lines: list[str]) -> None:
    if not override_settings.use_overscan:
        return

    script_lines.append("# Overscan Settings")
    script_lines.append('log.info("Applying Overscan setting")')
    lines = []

    if override_settings.overscan_type == "PERCENTAGE":
        if override_settings.overscan_uniform:
            lines.extend(
                [
                    "base_res_x = bpy.context.scene.render.resolution_x",
                    "base_res_y = bpy.context.scene.render.resolution_y",
                    f"overscan_x = int(base_res_x * {override_settings.overscan_percent} / 100)",
                    f"overscan_y = int(base_res_y * {override_settings.overscan_percent} / 100)",
                ]
            )
        else:
            lines.extend(
                [
                    "base_res_x = bpy.context.scene.render.resolution_x",
                    "base_res_y = bpy.context.scene.render.resolution_y",
                    f"overscan_x = int(base_res_x * {override_settings.overscan_percent_width} / 100)",
                    f"overscan_y = int(base_res_y * {override_settings.overscan_percent_height} / 100)",
                ]
            )
    else:
        if override_settings.overscan_uniform:
            lines.append(f"overscan_x = overscan_y = {override_settings.overscan_width}")
        else:
            lines.extend(
                [
                    f"overscan_x = {override_settings.overscan_width}",
                    f"overscan_y = {override_settings.overscan_height}",
                ]
            )

    lines.extend(
        [
            "original_resolution = (bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y)",
            "",
        ]
    )

    set_camera_shift = override_settings.cameras_override and (
        override_settings.camera_shift_x != 0.0 or override_settings.camera_shift_y != 0.0
    )

    if set_camera_shift:
        lines.extend(
            [
                "scale_x = original_resolution[0] / max(1, (original_resolution[0] + 2 * overscan_x))",
                "scale_y = original_resolution[1] / max(1, (original_resolution[1] + 2 * overscan_y))",
            ]
        )

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

    lines.extend(
        [
            "bpy.context.scene.render.resolution_x = original_resolution[0] + 2 * overscan_x",
            "bpy.context.scene.render.resolution_y = original_resolution[1] + 2 * overscan_y",
            "",
        ]
    )

    script_lines.extend(lines)


def _apply_output_format_settings(override_settings, script_lines: list[str]) -> None:
    """Apply file format override settings."""
    try:
        if not override_settings.file_format_override:
            return

        script_lines.append("# File Format Settings")
        script_lines.append('log.info(f"Applying File Format override")')
        lines = []

        if override_settings.file_format == "OPEN_EXR_MULTILAYER":
            media_type_val = "MULTI_LAYER_IMAGE"
        else:
            media_type_val = "IMAGE"

        lines.extend(
            [
                "if bpy.app.version >= (5, 0, 0):",
                f"    bpy.context.scene.render.image_settings.media_type = '{media_type_val}'",
            ]
        )

        lines.append(f"bpy.context.scene.render.image_settings.file_format = '{override_settings.file_format}'")
        if override_settings.file_format in [
            "OPEN_EXR",
            "OPEN_EXR_MULTILAYER",
            "PNG",
            "TIFF",
        ]:
            lines.append(f"bpy.context.scene.render.image_settings.color_depth = '{override_settings.color_depth}'")

        if override_settings.file_format in [
            "OPEN_EXR",
            "OPEN_EXR_MULTILAYER",
        ]:
            lines.extend(
                [
                    f"bpy.context.scene.render.image_settings.exr_codec = '{override_settings.codec}'",
                    f"bpy.context.scene.render.image_settings.use_preview = {override_settings.use_preview}",
                ]
            )

        if override_settings.file_format in ["JPEG", "WEBP"]:
            lines.append(f"bpy.context.scene.render.image_settings.quality = {override_settings.quality}")

        script_lines.extend(_wrap_in_try(lines, "Output Format Settings", True))

    except Exception as e:
        log.error("Error applying output format settings: %s", e, exc_info=True)


def _apply_compositing_settings(override_settings, script_lines: list[str]) -> None:
    """Apply compositing override settings."""
    if not override_settings.compositor_override:
        return

    script_lines.append("# Compositing Settings")
    script_lines.append('log.info(f"Applying Compositor override")')
    lines = []
    lines.extend(
        [
            f"bpy.context.scene.render.use_compositing = {override_settings.use_compositor}",
            f"bpy.context.scene.render.compositor_device = '{override_settings.compositor_device}'",
            "",
        ]
    )

    if override_settings.compositor_disable_output_files and override_settings.use_compositor:
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


def _apply_cycles_settings(context, prefs, override_settings, selected_ids, script_lines: list[str]) -> None:
    """Apply Cycles-specific rendering settings."""
    try:
        if not (
            prefs.manage_cycles_devices
            or prefs.device_parallel
            or override_settings.cycles.device_override
            or override_settings.cycles.sampling_override
            or override_settings.cycles.denoising_override
            or override_settings.cycles.performance_override
        ):
            return

        script_lines.append("# Cycles Settings")
        script_lines.append('log.info("Applying Cycles overrides")')
        lines = []
        lines.append(f"if bpy.context.scene.render.engine == '{RE_CYCLES}':")

        if override_settings.cycles.device_override:
            lines.append(f"    bpy.context.scene.cycles.device = '{override_settings.cycles.device}'")
            lines.append("")

        _apply_cycles_device_settings(context, prefs, selected_ids, lines)
        _apply_cycles_sampling_settings(override_settings, lines)
        _apply_cycles_denoising_settings(override_settings, lines)
        _apply_cycles_performance_settings(override_settings, lines)

        script_lines.extend(_wrap_in_try(lines, "Cycles Overrides", True))

    except Exception as e:
        log.error("Error applying cycles settings: %s", e, exc_info=True)


def _apply_cycles_sampling_settings(override_settings, lines: list[str]) -> None:
    """Apply Cycles sampling settings."""
    if not override_settings.cycles.sampling_override:
        return

    cycles = override_settings.cycles

    if cycles.sampling_mode == "FACTOR":
        factor = float(cycles.sampling_factor) / 100.0
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


def _apply_cycles_denoising_settings(override_settings, lines: list[str]) -> None:
    """Apply Cycles denoising settings."""
    if not override_settings.cycles.denoising_override:
        return

    cycles = override_settings.cycles
    if not cycles.denoising_override:
        return

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


def _apply_cycles_performance_settings(override_settings, lines: list[str]) -> None:
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


def _apply_cycles_device_settings(context, prefs, selected_ids, lines: list[str]) -> None:
    """Apply Cycles device settings for the generated worker script."""

    if not (prefs.device_parallel or prefs.manage_cycles_devices):
        return

    if prefs.multiple_backends and prefs.launch_mode != MODE_SINGLE and prefs.device_parallel:
        source = prefs if prefs.manage_cycles_devices else get_cycles_prefs(context)
        devices = getattr(source, "devices", []) if source else []
        match = next((d for d in devices if d.id in selected_ids and getattr(d, "use", False)), None)
        backend_type = getattr(match, "type", "CPU") if match else "CPU"
    else:
        cycles_prefs = prefs if prefs.manage_cycles_devices else get_cycles_prefs(context)
        backend_type = getattr(cycles_prefs, "compute_device_type", "NONE") if cycles_prefs else "NONE"

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
            "    # Log enabled devices",
            "    if active_devices:",
            "        log.info(f'Active Devices: {len(active_devices)}')",
            "        for d in active_devices:",
            "            log.info(f'  - {d.name} ({d.type}) [{d.id}]')",
            "    elif not is_gpu:",
            "        log.info('Device: CPU')",
            "",
        ]
    )


def _apply_eevee_settings(override_settings, script_lines: list[str]) -> None:
    """Add EEVEE override settings."""
    if not override_settings.eevee_override:
        return

    script_lines.append("# EEVEE Settings")
    script_lines.append('log.info(f"Applying EEVEE override")')
    eevee = override_settings.eevee

    lines = [
        f"if bpy.context.scene.render.engine in {{'{RE_EEVEE_NEXT}', '{RE_EEVEE}'}}:",
        f"    bpy.context.scene.eevee.taa_render_samples = {eevee.samples}",
        "",
    ]

    script_lines.extend(lines)


def _apply_data_path_overrides(override_settings, script_lines: list[str]) -> None:
    """Add data paths overrides."""
    try:
        if not override_settings.use_data_path_overrides:
            return

        overrides = override_settings.data_path_overrides
        if not overrides:
            return

        script_lines.append("# Data Path Overrides")
        script_lines.append(f'log.info("Applying {len(overrides)} data path override(s)")')

        for item in overrides:
            path = item.data_path

            if item.prop_type == "BOOL":
                val_str = str(item.value_bool)
            elif item.prop_type == "INT":
                val_str = str(item.value_int)
            elif item.prop_type == "FLOAT":
                val_str = str(item.value_float)
            elif item.prop_type == "STRING":
                val_str = repr(item.value_string)
            elif item.prop_type == "VECTOR_3":
                val_str = str(tuple(item.value_vector_3))
            elif item.prop_type == "COLOR_4":
                val_str = str(tuple(item.value_color_4))
            else:
                log.warning("Unknown property type %s for override %s", item.prop_type, path)
                val_str = "None"

            script_lines.extend(
                [
                    "try:",
                    f"    {path} = {val_str}",
                    "except Exception as e:",
                    f'    log.error("Failed to apply custom override (%s): %s", "{path}", {{e}})',
                ]
            )
        script_lines.append("")
    except Exception as e:
        log.error("Error applying data path overrides: %s", e, exc_info=True)


def _generate_base_script(
    context,
    prefs,
    selected_ids,
    is_animation,
    frame_start,
    frame_end,
    frame_step,
    start_msg,
) -> list[str]:
    """Generate common script parts for both single and parallel rendering."""
    script_lines = []

    override_settings = get_override_settings(context)

    script_lines.extend(
        [
            f'"""{ADDON_INFO}"""',
            "",
            "import bpy",
            "",
        ]
    )

    _add_logging_formatter(script_lines)

    if start_msg:
        script_lines.append(f'log.info("{start_msg}")')
        script_lines.append("")

    _add_render_time_tracking(prefs, script_lines)
    _apply_data_path_overrides(override_settings, script_lines)
    _apply_motion_blur_settings(override_settings, script_lines)
    _apply_frame_settings(prefs, override_settings, is_animation, frame_start, frame_end, frame_step, script_lines)
    _apply_fps_converter_settings(override_settings, script_lines)
    _apply_camera_settings(override_settings, script_lines)
    _apply_resolution_settings(context, override_settings, script_lines)
    _apply_overscan_settings(context, override_settings, script_lines)
    _apply_output_format_settings(override_settings, script_lines)
    _apply_compositing_settings(override_settings, script_lines)

    render_engine = get_render_engine(context)
    if render_engine == RE_CYCLES:
        _apply_cycles_settings(context, prefs, override_settings, selected_ids, script_lines)
    elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
        _apply_eevee_settings(override_settings, script_lines)

    return script_lines
