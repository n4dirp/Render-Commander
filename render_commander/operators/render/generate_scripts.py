# ./operators/render/generate_scripts.py

import json
import logging
from pathlib import Path

from ...utils.constants import *
from ...utils.helpers import (
    get_render_engine,
    calculate_auto_width,
    calculate_auto_height,
)

log = logging.getLogger(__name__)


def _generate_base_script(
    context,
    prefs,
    selected_ids,
    is_animation,
    frame_start,
    frame_end,
    frame_step,
    start_msg: str = "",
):
    """Generate common script parts for both single and parallel rendering."""

    settings = context.window_manager.recom_render_settings
    script_lines = []

    # Start Script
    script_lines.extend(
        [
            f"# Render Commander - Render ID: {settings.render_id}",
            "",
            "import bpy",
            "",
        ]
    )

    if start_msg:
        msg_lines = start_msg.splitlines()
        script_lines.append(f'print("{start_msg}")')

    # Add render time tracking
    _add_render_time_tracking(prefs, script_lines)

    # Apply motion blur settings
    _apply_motion_blur_settings(settings, script_lines)

    # Apply frame settings
    _apply_frame_settings(is_animation, frame_start, frame_end, frame_step, script_lines)

    # Apply resolution and scale settings
    _apply_resolution_settings(context, settings, script_lines)

    # Apply output format settings
    _apply_output_format_settings(settings, script_lines)

    # Apply compositing settings
    _apply_compositing_settings(settings, script_lines)

    # Apply render engine specific settings
    render_engine = get_render_engine(context)
    if render_engine == RE_CYCLES:
        _apply_cycles_settings(context, prefs, settings, selected_ids, script_lines)
    elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
        _apply_eevee_settings(settings, script_lines)

    return script_lines


def _add_render_time_tracking(prefs, script_lines):
    """Add script lines for tracking render time."""
    if prefs.launch_mode == MODE_SEQ:
        script_lines.extend(_load_template_script("render_time.py"))
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
    """Apply motion blur settings."""
    if settings.override_settings.motion_blur_override:
        script_lines.extend(
            [
                f"bpy.context.scene.render.use_motion_blur = {settings.override_settings.use_motion_blur}",
                f"bpy.context.scene.render.motion_blur_position = '{settings.override_settings.motion_blur_position}'",
                f"bpy.context.scene.render.motion_blur_shutter = {settings.override_settings.motion_blur_shutter}",
                "",
            ]
        )


def _apply_frame_settings(is_animation, frame_start, frame_end, frame_step, script_lines):
    """Apply frame start, end, and step settings."""
    if is_animation:
        script_lines.extend(
            [
                f"bpy.context.scene.frame_start = {frame_start}",
                f"bpy.context.scene.frame_end = {frame_end}",
                f"bpy.context.scene.frame_step = {frame_step}",
                "",
            ]
        )
    else:
        script_lines.append(f"bpy.context.scene.frame_set({frame_start})")
        script_lines.append("")


def _apply_resolution_settings(context, settings, script_lines):
    """Apply resolution, scale, camera shift, and overscan settings."""
    if settings.override_settings.format_override:
        if settings.override_settings.resolution_override:
            resolution_mode = settings.override_settings.resolution_mode
            if resolution_mode == "SET_WIDTH":
                base_x = settings.override_settings.resolution_x
                base_y = calculate_auto_height(context)
            elif resolution_mode == "SET_HEIGHT":
                base_y = settings.override_settings.resolution_y
                base_x = calculate_auto_width(context)
            else:
                base_x = settings.override_settings.resolution_x
                base_y = settings.override_settings.resolution_y

            if settings.override_settings.render_scale != "CUSTOM":
                scale = float(settings.override_settings.render_scale)
            else:
                scale = settings.override_settings.custom_render_scale / 100

            scaled_x = int(round(base_x * scale / 2) * 2)
            scaled_y = int(round(base_y * scale / 2) * 2)
            script_lines.extend(
                [
                    f"bpy.context.scene.render.resolution_x = {scaled_x}",
                    f"bpy.context.scene.render.resolution_y = {scaled_y}",
                    "bpy.context.scene.render.resolution_percentage = 100",
                    "",
                ]
            )
        else:
            # Apply scale settings
            if settings.override_settings.render_scale != "CUSTOM":
                scale = int(float(settings.override_settings.render_scale) * 100)
            else:
                scale = settings.override_settings.custom_render_scale
            script_lines.append(f"bpy.context.scene.render.resolution_percentage = {scale}")
            script_lines.append("")

        # Apply camera shift settings
        set_camera_shift = settings.override_settings.camera_shift_override and (
            settings.override_settings.camera_shift_x != 0.0 or settings.override_settings.camera_shift_y != 0.0
        )
        if set_camera_shift:
            script_lines.extend(
                [
                    "for obj in bpy.data.objects:",
                    "    if obj.type == 'CAMERA':",
                    f"        obj.data.shift_x += {settings.override_settings.camera_shift_x}",
                    f"        obj.data.shift_y += {settings.override_settings.camera_shift_y}",
                    "",
                ]
            )

        # Apply overscan settings
        if settings.override_settings.use_overscan:
            # Calculate overscan value based on type
            if settings.override_settings.overscan_type == "PERCENTAGE":
                script_lines.extend(
                    [
                        "base_res_x = bpy.context.scene.render.resolution_x",
                        "base_res_y = bpy.context.scene.render.resolution_y",
                        f"overscan_x = int(base_res_x * {settings.override_settings.overscan_percent} / 100)",
                        f"overscan_y = int(base_res_y * {settings.override_settings.overscan_percent} / 100)",
                    ]
                )

            else:  # PIXELS
                if settings.override_settings.overscan_uniform:
                    script_lines.append(f"overscan_x = overscan_y = {settings.override_settings.overscan_width}")
                else:
                    script_lines.extend(
                        [
                            f"overscan_x = {settings.override_settings.overscan_width}",
                            f"overscan_y = {settings.override_settings.overscan_height}",
                        ]
                    )

            script_lines.extend(
                [
                    "original_resolution = (bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y)",
                    "",
                ]
            )

            if set_camera_shift:
                script_lines.extend(
                    [
                        "scale_x = original_resolution[0] / (original_resolution[0] + 2 * overscan_x)",
                        "scale_y = original_resolution[1] / (original_resolution[1] + 2 * overscan_y)",
                    ]
                )

            # Apply camera shift and lens scaling
            script_lines.extend(
                [
                    "for obj in bpy.data.objects:",
                    "    if obj.type == 'CAMERA':",
                    "        obj.data.lens = obj.data.lens * (original_resolution[0] / (original_resolution[0] + 2 * overscan_x))",
                    "",
                ]
            )

            if set_camera_shift:
                script_lines.extend(
                    [
                        "        obj.data.shift_x *= scale_x",
                        "        obj.data.shift_y *= scale_y",
                        "",
                    ]
                )

            # Update render resolution
            script_lines.extend(
                [
                    "bpy.context.scene.render.resolution_x = original_resolution[0] + 2 * overscan_x",
                    "bpy.context.scene.render.resolution_y = original_resolution[1] + 2 * overscan_y",
                    "",
                ]
            )


def _apply_output_format_settings(settings, script_lines):
    """Apply output format settings."""
    if settings.override_settings.file_format_override:
        if settings.override_settings.file_format == "OPEN_EXR_MULTILAYER":
            media_type_val = "MULTI_LAYER_IMAGE"
        else:
            media_type_val = "IMAGE"

        # Blender 5.0 - New media_type
        script_lines.extend(
            [
                "if bpy.app.version > (5, 0, 0):",
                f"    bpy.context.scene.render.image_settings.media_type = '{media_type_val}'",
            ]
        )

        script_lines.append(
            f"bpy.context.scene.render.image_settings.file_format = '{settings.override_settings.file_format}'"
        )
        if settings.override_settings.file_format in [
            "OPEN_EXR",
            "OPEN_EXR_MULTILAYER",
            "PNG",
            "TIFF",
        ]:
            script_lines.append(
                f"bpy.context.scene.render.image_settings.color_depth = '{settings.override_settings.color_depth}'"
            )

        if settings.override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
            script_lines.append(
                f"bpy.context.scene.render.image_settings.exr_codec = '{settings.override_settings.codec}'"
            )
        elif settings.override_settings.file_format == "JPEG":
            script_lines.append(
                f"bpy.context.scene.render.image_settings.quality = {settings.override_settings.jpeg_quality}"
            )
        script_lines.append("")


def _apply_compositing_settings(settings, script_lines):
    """Apply compositing settings."""
    if settings.override_settings.compositor_override:
        script_lines.extend(
            [
                "if bpy.app.version < (5, 0, 0):",
                f"    bpy.context.scene.use_nodes = {settings.override_settings.use_compositor}",
                "elif not settings.use_compositor:",
                f"    bpy.context.scene.compositing_node_group = None",
                f"bpy.context.scene.render.compositor_device = '{settings.override_settings.compositor_device}'",
                "",
            ]
        )
        if settings.override_settings.compositor_disable_output_files and settings.override_settings.use_compositor:
            script_lines.extend(
                [
                    "for node in bpy.context.scene.node_tree.nodes:",
                    "    if node.type == 'OUTPUT_FILE':",
                    "        node.mute = True",
                    "",
                ]
            )


def _apply_cycles_settings(context, prefs, settings, selected_ids, script_lines):
    """Apply Cycles-specific rendering settings."""
    override_settings = settings.override_settings
    cycles_backend = "NONE" if prefs.compute_device_type == "CPU" else prefs.compute_device_type
    formatted_ids = json.dumps(selected_ids, indent=4).replace("\n", "\n    ")

    script_lines.extend(
        [
            f"if bpy.context.scene.render.engine == '{RE_CYCLES}':",
            "    preferences = bpy.context.preferences.addons['cycles'].preferences",
            f"    preferences.compute_device_type = '{cycles_backend}'",
            f"    selected_ids = {formatted_ids}",
            "    for device in preferences.devices:",
            "        device.use = device.id in selected_ids",
            "",
        ]
    )
    script_lines.extend(
        [
            "    enabled_devices = [d for d in preferences.devices if d.use]",
            "    if enabled_devices:",
            "        print('Devices:' + enabled_devices[0].name + ' (' + enabled_devices[0].type + ') [' + enabled_devices[0].id + ']')",
            "        for d in enabled_devices[1:]:",
            "            print('\\t' + d.name + ' (' + d.type + ') [' + d.id + ']')",
            "",
        ]
    )

    if override_settings.cycles.device_override:
        script_lines.append(f"    bpy.context.scene.cycles.device = '{override_settings.cycles.device}'")
        script_lines.append("")

    _apply_cycles_sampling_settings(override_settings, script_lines)
    _apply_cycles_light_paths_settings(override_settings, script_lines)
    _apply_cycles_performance_settings(override_settings, script_lines)


def _apply_cycles_sampling_settings(override_settings, script_lines):
    """Apply Cycles sampling settings."""
    if not override_settings.cycles.sampling_override:
        return

    cycles = override_settings.cycles
    noise_threshold_value = float(cycles.adaptive_threshold)

    lines = [
        f"    bpy.context.scene.cycles.use_adaptive_sampling = {cycles.use_adaptive_sampling}",
        f"    bpy.context.scene.cycles.adaptive_threshold = {noise_threshold_value}",
        f"    bpy.context.scene.cycles.samples = {int(cycles.samples)}",
        f"    bpy.context.scene.cycles.adaptive_min_samples = {cycles.adaptive_min_samples}",
        f"    bpy.context.scene.cycles.time_limit = {cycles.time_limit}",
        "",
    ]

    if cycles.use_denoising:
        lines.extend(
            [
                f"    bpy.context.scene.cycles.use_denoising = {cycles.use_denoising}",
                f"    bpy.context.scene.cycles.denoiser = '{cycles.denoiser}'",
                f"    bpy.context.scene.cycles.denoising_input_passes = '{cycles.denoising_input_passes}'",  # Fixed typo
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

        if cycles.denoising_store_passes:
            lines.extend(
                [
                    "    for layer in bpy.context.scene.view_layers:",
                    "        layer.cycles.denoising_store_passes = True",
                    "",
                ]
            )

    script_lines.extend(lines)


def _apply_cycles_light_paths_settings(override_settings, script_lines):
    """Apply Cycles light paths settings."""
    if not override_settings.cycles.light_path_override:
        return

    cycles = override_settings.cycles
    lines = [
        f"    bpy.context.scene.cycles.max_bounces = {cycles.max_bounces}",
        f"    bpy.context.scene.cycles.diffuse_bounces = {cycles.diffuse_bounces}",
        f"    bpy.context.scene.cycles.glossy_bounces = {cycles.glossy_bounces}",
        f"    bpy.context.scene.cycles.transmission_bounces = {cycles.transmission_bounces}",
        f"    bpy.context.scene.cycles.volume_bounces = {cycles.volume_bounces}",
        f"    bpy.context.scene.cycles.transparent_max_bounces = {cycles.transparent_bounces}",
        f"    bpy.context.scene.cycles.sample_clamp_direct = {cycles.sample_clamp_direct}",
        f"    bpy.context.scene.cycles.sample_clamp_indirect = {cycles.sample_clamp_indirect}",
        f"    bpy.context.scene.cycles.caustics_reflective = {cycles.caustics_reflective}",
        f"    bpy.context.scene.cycles.caustics_refractive = {cycles.caustics_refractive}",
        f"    bpy.context.scene.cycles.blur_glossy = {cycles.blur_glossy}",
        "",
    ]

    script_lines.extend(lines)


def _apply_cycles_performance_settings(override_settings, script_lines):
    """Apply Cycles performance settings."""
    if not override_settings.cycles.performance_override:
        return

    cycles = override_settings.cycles
    lines = [
        f"    bpy.context.scene.cycles.use_auto_tile = {cycles.use_tiling}",
        f"    bpy.context.scene.cycles.tile_size = {cycles.tile_size}",
        f"    bpy.context.scene.render.use_persistent_data = {cycles.persistent_data}",
        "",
    ]

    script_lines.extend(lines)


def _apply_eevee_settings(settings, script_lines):
    """Apply EEVEE-specific rendering settings."""
    override_settings = settings.override_settings
    if not override_settings.eevee_override:
        return

    eevee = override_settings.eevee
    lines = [
        f"if bpy.context.scene.render.engine in {{'{RE_EEVEE_NEXT}', '{RE_EEVEE}'}}:",
        f"    bpy.context.scene.eevee.taa_render_samples = {eevee.samples}",
        f"    bpy.context.scene.eevee.use_shadows = {eevee.use_shadows}",
        f"    bpy.context.scene.eevee.shadow_ray_count = {eevee.shadow_ray_count}",
        f"    bpy.context.scene.eevee.shadow_step_count = {eevee.shadow_step_count}",
        f"    bpy.context.scene.eevee.use_raytracing = {eevee.use_raytracing}",
        f'    bpy.context.scene.eevee.ray_tracing_method = "{eevee.ray_tracing_method}"',
        f'    bpy.context.scene.eevee.ray_tracing_options.resolution_scale = "{eevee.ray_tracing_resolution}"',
        f"    bpy.context.scene.eevee.ray_tracing_options.use_denoise = {eevee.ray_tracing_denoise}",
        f"    bpy.context.scene.eevee.ray_tracing_options.denoise_temporal = {eevee.ray_tracing_denoise_temporal}",
        f"    bpy.context.scene.eevee.use_fast_gi = {eevee.fast_gi}",
        f"    bpy.context.scene.eevee.ray_tracing_options.trace_max_roughness = {eevee.trace_max_roughness}",
        f'    bpy.context.scene.eevee.fast_gi_resolution = "{eevee.fast_gi_resolution}"',
        f"    bpy.context.scene.eevee.fast_gi_step_count = {eevee.fast_gi_step_count}",
        f"    bpy.context.scene.eevee.fast_gi_distance = {eevee.fast_gi_distance}",
        f'    bpy.context.scene.eevee.volumetric_tile_size = "{eevee.volumetric_tile_size}"',
        f"    bpy.context.scene.eevee.volumetric_samples = {eevee.volume_samples}",
        "",
    ]

    script_lines.extend(lines)


def _load_template_script(template_name):
    """Load a template script from the operators directory."""
    template_path = Path(__file__).parent / "templates" / template_name
    try:
        with open(template_path, "r") as f:
            template_content = f.read()
        return template_content.splitlines()
    except Exception as e:
        log.error(f"Failed to load template {template_name}: {str(e)}")
        return []


def _add_notification_script(context, prefs, script_lines):
    if prefs.send_desktop_notifications:
        notification_content = _load_template_script("desktop_notification.py")

        # Replace the placeholder with the actual value
        notification_content = "\n".join(notification_content).replace(
            "frame_length_digits = 4", f"frame_length_digits = {prefs.frame_length_digits}"
        )

        script_lines.extend(notification_content.splitlines())


def _add_prevent_sleep_commands(context, prefs, script_lines):
    prevent_sleep_content = _load_template_script("prevent_sleep.py")

    # Replace placeholder with actual value
    prevent_sleep_content = "\n".join(prevent_sleep_content).replace(
        "prevent_monitor_off", "True" if prefs.prevent_monitor_off else "False"
    )

    script_lines.extend(prevent_sleep_content.splitlines())
