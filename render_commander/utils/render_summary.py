# ./utils/render_summary.py

"""Read-only summary of the current render/export configuration.

Used by the launcher panel to display the most important settings before
exporting render scripts. Mirrors the values recorded in the render history
without producing any side effects.
"""

import logging
import re
from pathlib import Path

import bpy

from ..operators.chunk_calculators import format_frame_range, parse_frame_string
from ..utils.constants import (
    MODE_LIST,
    MODE_SEQ,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RE_WORKBENCH,
    RENDER_ENGINE_MAPPING,
    RENDER_TEMPLATE_PATTERN,
)
from ..utils.cycles_devices import get_devices_for_display
from ..utils.helpers import (
    calculate_auto_height,
    calculate_auto_width,
    format_to_title_case,
    get_addon_preferences,
    get_addon_settings,
    get_render_engine,
    get_scene_info,
    replace_variables,
)

log = logging.getLogger(__name__)


def build_render_summary(context) -> list:
    """Return ``(label, value)`` rows describing the current render/export setup."""
    prefs = get_addon_preferences(context)
    settings = get_addon_settings(context)
    if prefs is None:
        return []

    engine = get_render_engine(context)
    ext_info = get_scene_info(settings) or {} if settings.use_external_blend else {}
    override_settings = settings.override_settings

    rows = []
    rows.append(("Blend File", _blend_name(settings)))
    rows.append(("Engine", RENDER_ENGINE_MAPPING.get(engine, engine)))
    rows.append(("Mode", format_to_title_case(prefs.launch_mode)))
    rows.append(("Frames", _frames_text(context, prefs, settings, ext_info, override_settings)))
    rows.append(("Resolution", _resolution_text(context, settings, ext_info, override_settings)))
    rows.append(("Samples", _samples_text(context, settings, ext_info, engine, override_settings)))
    rows.append(("Output Format", _format_text(context, settings, ext_info, override_settings)))
    rows.append(("Output Path", _output_path_text(context, prefs, settings, ext_info)))
    rows.append(("Scripts", str(_worker_count(context, prefs, settings, engine, ext_info))))
    rows.append(("Export To", _export_target_text(prefs, settings)))

    if engine == RE_CYCLES:
        devices_text = _devices_text(prefs, context)
        if devices_text:
            rows.append(("Devices", devices_text))

    return rows


def build_render_summary_warnings(context) -> list:
    """Return pre-export warnings that would block or hinder the export."""
    prefs = get_addon_preferences(context)
    settings = get_addon_settings(context)
    if prefs is None:
        return []

    warnings = []

    if settings.use_external_blend:
        if not settings.external_blend_file_path:
            warnings.append("No external blend file selected")
        elif not settings.external_scene_info or settings.external_scene_info == "{}":
            warnings.append("Scene metadata not loaded")
    else:
        if not bpy.data.filepath:
            warnings.append("Blend file is not saved")
        if context.scene.camera is None:
            warnings.append("No active camera")

    if prefs.launch_mode == MODE_LIST and not settings.frame_list:
        warnings.append("Frame list is empty")

    return warnings


def _blend_name(settings) -> str:
    if settings.use_external_blend and settings.external_blend_file_path:
        return Path(settings.external_blend_file_path).name
    if bpy.data.filepath:
        return Path(bpy.data.filepath).name
    return "Untitled"


def _frames_text(context, prefs, settings, ext_info, override_settings) -> str:
    if prefs.launch_mode == MODE_LIST and settings.frame_list:
        return format_frame_range(parse_frame_string(settings.frame_list))

    if prefs.launch_mode == MODE_SEQ:
        if override_settings.enabled and override_settings.frame_range_override:
            return f"{override_settings.frame_start}-{override_settings.frame_end}"
        if settings.use_external_blend:
            return f"{ext_info.get('frame_start', 0)}-{ext_info.get('frame_end', 0)}"
        scene = context.scene
        return f"{scene.frame_start}-{scene.frame_end}"

    if override_settings.enabled and override_settings.frame_range_override:
        return str(override_settings.frame_current)
    if settings.use_external_blend:
        return str(ext_info.get("frame_current", 0))
    return str(context.scene.frame_current)


def _resolution_text(context, settings, ext_info, override_settings) -> str:
    if override_settings.enabled and override_settings.format_override:
        res_mode = override_settings.resolution_mode
        if res_mode == "SET_WIDTH":
            width, height = override_settings.resolution_x, calculate_auto_height(context)
        elif res_mode == "SET_HEIGHT":
            width, height = calculate_auto_width(context), override_settings.resolution_y
        else:
            width, height = override_settings.resolution_x, override_settings.resolution_y
        scale = override_settings.custom_render_scale
    elif settings.use_external_blend:
        width = ext_info.get("resolution_x", 0)
        height = ext_info.get("resolution_y", 0)
        scale = ext_info.get("render_scale", 100)
    else:
        scene = context.scene
        width, height = scene.render.resolution_x, scene.render.resolution_y
        scale = scene.render.resolution_percentage

    text = f"{width} x {height} px"
    if scale != 100:
        text += f" ({int(scale)}%)"
    return text


def _samples_text(context, settings, ext_info, engine, override_settings) -> str:
    if engine == RE_CYCLES:
        if override_settings.enabled and override_settings.cycles.sampling_override:
            if override_settings.cycles.sampling_mode == "FACTOR":
                return f"{int(override_settings.cycles.sampling_factor)}%"
            return str(override_settings.cycles.samples)
        if settings.use_external_blend:
            return str(ext_info.get("samples", 0))
        return str(context.scene.cycles.samples)

    if engine in {RE_EEVEE_NEXT, RE_EEVEE}:
        if override_settings.enabled and override_settings.eevee_override:
            return str(override_settings.eevee.samples)
        if settings.use_external_blend:
            return str(ext_info.get("eevee_samples", 0))
        return str(context.scene.eevee.taa_render_samples)

    return ""


def _format_text(context, settings, ext_info, override_settings) -> str:
    if override_settings.enabled and override_settings.file_format_override:
        fmt_id = override_settings.file_format
    elif settings.use_external_blend:
        fmt_id = ext_info.get("file_format", "")
    else:
        fmt_id = context.scene.render.image_settings.file_format

    if not fmt_id:
        return ""

    prop = context.scene.render.image_settings.bl_rna.properties["file_format"]
    return prop.enum_items[fmt_id].name if fmt_id in prop.enum_items else str(fmt_id)


def _output_path_text(context, prefs, settings, ext_info) -> str:
    scene = context.scene
    override_settings = settings.override_settings
    is_override = override_settings.enabled and override_settings.output_path_override

    try:
        if is_override:
            dir_path = override_settings.output_directory or "/tmp/"
            file_name = override_settings.output_filename
        else:
            base_path = ext_info.get("filepath", "//") if settings.use_external_blend else scene.render.filepath
            last_slash = max(base_path.rfind("/"), base_path.rfind("\\"))
            if last_slash == -1:
                dir_path, file_name = "", base_path
            else:
                dir_path, file_name = base_path[: last_slash + 1], base_path[last_slash + 1 :]

        if dir_path and not dir_path.endswith(("/", "\\")):
            dir_path += "/"

        if not file_name:
            file_name = prefs.default_render_filename or "render"

        sep = "." if prefs.filename_separator == "DOT" else "_"
        file_name_no_templates = re.sub(RENDER_TEMPLATE_PATTERN, "", file_name)

        if "#" not in file_name_no_templates:
            file_name = f"{file_name}{sep}{'#' * prefs.frame_length_digits}"

        output_path = f"{dir_path}{file_name}"

        if is_override:
            output_path = replace_variables(prefs, output_path)

        return output_path

    except Exception as exc:
        log.error("Failed to resolve output path for summary: %s", exc)
        return ""


def _worker_count(context, prefs, settings, engine, ext_info) -> int:
    if engine == RE_CYCLES:
        devices = [d for d in get_devices_for_display(prefs, context) if d.use]
        parallel = prefs.device_parallel and prefs.launch_mode in {MODE_SEQ, MODE_LIST}

        if parallel:
            if prefs.combine_cpu_with_gpus:
                devices = [d for d in devices if d.type != "CPU"]

            if settings.override_settings.enabled and settings.override_settings.cycles.device_override:
                device = settings.override_settings.cycles.device
            elif settings.use_external_blend:
                device = str(ext_info.get("device", "CPU"))
            else:
                device = str(context.scene.cycles.device)

            if device == "GPU":
                return max(1, len(devices))

        return 1

    if engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}:
        if prefs.multi_instance and prefs.launch_mode in {MODE_SEQ, MODE_LIST}:
            return prefs.render_iterations

    return 1


def _export_target_text(prefs, settings) -> str:
    if prefs.export_output_target == "SELECT_DIR":
        target = "Choose folder at export"
    elif prefs.export_output_target == "BLEND_DIR":
        if settings.use_external_blend and settings.external_blend_file_path:
            base = Path(bpy.path.abspath(settings.external_blend_file_path)).parent
        else:
            base = Path(bpy.data.filepath).parent if bpy.data.filepath else Path()
        target = str(base)
    else:  # CUSTOM_PATH
        target = prefs.custom_export_path or "Not set"

    if prefs.export_scripts_subfolder and prefs.export_scripts_folder_name:
        target = f"{target} / {prefs.export_scripts_folder_name}"

    return target


def _devices_text(prefs, context) -> str:
    enabled = [d for d in get_devices_for_display(prefs, context) if d.use]
    if not enabled:
        return ""

    by_type = {}
    for dev in enabled:
        by_type[dev.type] = by_type.get(dev.type, 0) + 1

    return " | ".join(f"{dev_type}: {count}" for dev_type, count in by_type.items())
