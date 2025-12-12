# ./operators/background_render.py

import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

import bpy
import bpy.app.timers
from bpy.types import Operator


from ... import __package__ as base_package
from ...preferences import get_addon_preferences
from ...utils.constants import *
from ...utils.helpers import (
    is_blender_blend_file,
    parse_frame_string,
    format_frame_range,
    replace_variables,
    sanitize_filename,
    reset_button_state,
    generate_job_id,
    open_folder,
    get_default_resolution,
    calculate_auto_width,
    calculate_auto_height,
    run_in_terminal,
    shell_quote,
    format_to_title_case,
    get_render_engine,
    get_default_render_output_path,
)
from .generate_scripts import (
    _generate_base_script,
    _add_notification_script,
    _add_prevent_sleep_commands,
)

log = logging.getLogger(__name__)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


class RECOM_OT_BackgroundRender(Operator):
    """Main operator for background rendering."""

    bl_idname = "recom.background_render"
    bl_label = "Background Render"
    bl_description = "Run a background render"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Main execution method that handles single and parallel rendering."""

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)
        scene = context.scene

        # Validation
        if not self._validate_settings(context, settings, prefs, scene):
            return {"CANCELLED"}

        blend_file = (
            bpy.path.abspath(settings.external_blend_file_path)
            if settings.use_external_blend and settings.external_blend_file_path
            else bpy.data.filepath
        )
        settings.disable_render_button = True
        bpy.app.timers.register(reset_button_state, first_interval=0.75)

        settings.render_id = generate_job_id()
        settings.folder_opened = False
        render_engine = get_render_engine(context)

        self._add_to_history(context, prefs, settings, scene, render_engine)

        if render_engine == RE_CYCLES:
            self._execute_cycles_render(context, prefs, settings, render_engine, blend_file, scene)
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}:
            self._execute_single_process_render(
                context,
                prefs,
                settings,
                render_engine,
                [],
                [],
                blend_file,
                scene,
            )
        else:
            self.report({"ERROR"}, f"Unsupported render engine: {render_engine}")
            return {"CANCELLED"}

        self.report({"INFO"}, f"Background render launched")
        return {"FINISHED"}

    def _validate_settings(self, context, settings, prefs, scene) -> bool:
        """Return True if validation passed, otherwise report and return False."""
        use_external = settings.use_external_blend

        # External‑blend sanity checks
        if use_external:
            if not is_blender_blend_file(settings.external_blend_file_path):
                self.report(
                    {"ERROR"}, f"Invalid or non‑Blender file: {settings.external_blend_file_path}"
                )
                return False

            if (
                not settings.external_scene_info
                or settings.external_scene_info.isspace()
                or settings.external_scene_info == "{}"
            ):
                self.report(
                    {"ERROR"},
                    "Missing external scene data.\nClick 'Read Scene' before rendering.",
                )
                return False

            try:
                scene_info = json.loads(settings.external_scene_info)
                if scene_info.get("blend_filepath", "") != settings.external_blend_file_path:
                    self.report(
                        {"ERROR"},
                        "Mismatch in scene data.\nClick 'Read Scene' before rendering.",
                    )
                    return False
            except json.JSONDecodeError:
                self.report(
                    {"ERROR"},
                    "Invalid scene data format.\nClick 'Read Scene' again.",
                )
                return False

        elif not bpy.data.filepath:
            self.report({"ERROR"}, "Please save the .blend file first.")
            return False

        # Auto‑save if requested
        if not use_external and prefs.auto_save_before_render and bpy.data.is_dirty:
            # Only touch disk if we actually have something new
            try:
                bpy.ops.wm.save_mainfile()
                log.info("Auto‑saved .blend file before render.")
            except Exception as e:
                log.warning(f"Failed to auto‑save before render: {e}")
                return False

        # Movie format checks
        if not settings.override_settings.file_format_override:
            is_movie_format = (
                settings.use_external_blend
                and settings.external_scene_info
                and json.loads(settings.external_scene_info).get("is_movie_format", False)
            )
            if prefs.launch_mode != MODE_SEQ and (scene.render.is_movie_format or is_movie_format):
                self.report(
                    {"ERROR"},
                    f"Cannot render {prefs.launch_mode} with animation output (FFMPEG).",
                )
                return False

            if prefs.launch_mode == MODE_SEQ and (scene.render.is_movie_format or is_movie_format):
                log.warning("FFMPEG Video output not supported - defaulting to PNG sequence")

        # Frame list non‑empty check
        if prefs.launch_mode == MODE_LIST and not settings.frame_list:
            self.report({"ERROR"}, "Frame List is empty.\nPlease specify frames to render.")
            return False

        # Check camera
        if not use_external:
            if scene.camera is None:
                self.report(
                    {"ERROR"},
                    "No active camera found.",
                )
                return False
        else:
            try:
                scene_info = json.loads(settings.external_scene_info)
                if scene_info.get("camera_lens", "0") == 0:
                    self.report(
                        {"ERROR"},
                        "External blend file has no camera.",
                    )
                    return False
            except Exception as exc:
                # Loading the external file failed – fall back to a generic error.
                log.warning(f"Failed to inspect external blend for cameras: {exc}")

        return True

    def _add_to_history(self, context, prefs, settings, scene, render_engine):
        history_item = prefs.render_history.add()

        # Set properties
        if settings.use_external_blend and settings.external_blend_file_path:
            blend_path = bpy.path.abspath(settings.external_blend_file_path)

            try:
                info = json.loads(settings.external_scene_info)
                if render_engine == RE_CYCLES:
                    history_item.samples = info.get("samples", "0")
                elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                    history_item.samples = info.get("eevee_samples", "0")

                if not settings.override_settings.format_override:
                    history_item.resolution_x = info.get("resolution_x", "0")
                    history_item.resolution_y = info.get("resolution_y", "0")
            except:
                pass
        else:
            blend_path = bpy.data.filepath

            if render_engine == RE_CYCLES:
                history_item.samples = context.scene.cycles.samples
            elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                history_item.samples = context.scene.eevee.taa_render_samples

            if not settings.override_settings.format_override:
                history_item.resolution_x = context.scene.render.resolution_x
                history_item.resolution_y = context.scene.render.resolution_y

        if settings.override_settings.format_override:
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
            history_item.resolution_x = base_x
            history_item.resolution_y = base_y

        if blend_path:
            path_obj = Path(blend_path)

            history_item.blend_path = str(path_obj)
            history_item.blend_dir = str(path_obj.parent)
            history_item.blend_file_name = path_obj.name
        else:
            history_item.blend_path = "Unknown"
            history_item.blend_dir = "Unknown"
            history_item.blend_file_name = "untitled"

        history_item.render_engine = render_engine
        history_item.render_id = settings.render_id
        history_item.launch_mode = format_to_title_case(prefs.launch_mode)

        # Format frames string based on render type
        if prefs.launch_mode == MODE_LIST and settings.frame_list:
            frames = format_frame_range(parse_frame_string(settings.frame_list))
        elif prefs.launch_mode == MODE_SEQ:
            if settings.use_external_blend:
                try:
                    info = json.loads(settings.external_scene_info)
                    frames = f"{info.get('frame_start', '1')} - {info.get('frame_end', '250')}"
                except:
                    frames = "N/A"
            else:
                frames = f"{scene.frame_start} - {scene.frame_end}"
        else:  # Single frame
            if settings.use_external_blend:
                try:
                    info = json.loads(settings.external_scene_info)
                    frames = str(info.get("frame_current", "1"))
                except:
                    frames = "N/A"
            else:
                frames = str(scene.frame_current)

        history_item.frames = frames

        # Set File Format
        if settings.override_settings.file_format_override:
            file_format = settings.override_settings.file_format
        else:
            if settings.use_external_blend:
                try:
                    info = json.loads(settings.external_scene_info)
                    file_format = info.get("file_format", "")
                except:
                    file_format = "N/A"
            else:
                file_format = bpy.context.scene.render.image_settings.file_format
        history_item.file_format = file_format

        # Set date
        now = datetime.now()
        history_item.date = now.strftime("%Y-%m-%d %H:%M:%S")

        # Add the new entry to the top of the list (instead of appending at end)
        item_index = len(prefs.render_history) - 1
        prefs.render_history.move(item_index, 0)

        # Ensure we don't exceed max history size (20 items)
        if len(prefs.render_history) > RENDER_HISTORY_LIMIT:
            prefs.render_history.remove(RENDER_HISTORY_LIMIT)

    def _execute_cycles_render(self, context, prefs, settings, render_engine, blend_file, scene):
        """Execute rendering for Cycles engine."""
        # Determine device configuration
        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]

        current_backend = prefs.compute_device_type

        # Handle CPU/GPU combination
        if (prefs.launch_mode == MODE_SEQ and prefs.device_parallel) or (
            prefs.launch_mode == MODE_LIST and prefs.device_parallel
        ):
            selected_devices = [
                d
                for d in devices_to_display
                if d.use and (not prefs.combine_cpu_with_gpus or d.type != "CPU")
            ]

        # Handle fallback to CPU
        if current_backend == "NONE":
            self._handle_cpu_fallback(prefs, devices_to_display, selected_devices)
            devices_to_display = prefs.get_devices_for_display()
            selected_devices = [d for d in devices_to_display if d.use]

        # Handle no devices selected
        elif not selected_devices:
            self._handle_no_devices_selected(prefs, devices_to_display, selected_devices)

        selected_ids = [d.id for d in selected_devices]

        # Get Cycles Device
        if settings.override_settings.cycles.device_override:
            cycles_device = settings.override_settings.cycles.device
        else:
            if settings.use_external_blend:
                try:
                    info = json.loads(settings.external_scene_info)
                    cycles_device = str(info.get("device", "CPU"))
                except:
                    cycles_device = "CPU"
            else:
                cycles_device = str(scene.cycles.device)

        # Disable Parallel for Cycles CPU
        if cycles_device == "GPU":
            # Execute based on launch mode
            if prefs.launch_mode == MODE_SINGLE:
                return self._execute_single_process_render(
                    context,
                    prefs,
                    settings,
                    render_engine,
                    selected_devices,
                    selected_ids,
                    blend_file,
                    scene,
                )

            elif (
                prefs.launch_mode == MODE_SEQ
                and prefs.device_parallel
                and len(selected_devices) > 1
            ):
                return self._execute_sequence_parallel_render(
                    context,
                    prefs,
                    settings,
                    selected_devices,
                    selected_ids,
                    blend_file,
                    scene,
                )

            elif (
                prefs.launch_mode == MODE_LIST
                and prefs.device_parallel
                and len(selected_devices) > 1
            ):
                return self._execute_frame_list_parallel_render(
                    context,
                    prefs,
                    settings,
                    selected_devices,
                    selected_ids,
                    blend_file,
                    scene,
                )

        # Fallback to single process
        return self._execute_single_process_render(
            context,
            prefs,
            settings,
            render_engine,
            selected_devices,
            selected_ids,
            blend_file,
            scene,
        )

    def _handle_cpu_fallback(self, prefs, devices_to_display, selected_devices):
        """Handle fallback to CPU when no GPU devices are available."""
        for device in prefs.devices:
            if device.type == "CPU":
                device.use = True
        prefs.compute_device_type = "NONE"
        current_backend = "NONE"

        # Update devices for display
        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]

    def _handle_no_devices_selected(self, prefs, devices_to_display, selected_devices):
        """Handle case when no devices are selected."""
        prefs.compute_device_type = "NONE"
        current_backend = "NONE"
        for device in prefs.devices:
            if device.type == "CPU":
                device.use = True
        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]
        self.report({"WARNING"}, "No devices selected. Fallback to CPU.")

    def _get_temp_script_path(self, context, settings, prefs, blend_file, process_id):
        blend_name = sanitize_filename(Path(blend_file).stem)
        timestamp = get_timestamp()
        filename = f"{blend_name}_{process_id}_{timestamp}.py"
        script_path = get_addon_temp_dir(prefs) / filename
        return script_path

    def _execute_single_process_render(
        self,
        context,
        prefs,
        settings,
        render_engine,
        selected_devices,
        selected_ids,
        blend_file,
        scene,
    ):
        """Execute single process render for still, secuence and frame list."""

        wm = context.window_manager

        is_not_still = prefs.launch_mode != MODE_SINGLE
        frame_start, frame_end, frame_step = self._get_frame_settings(
            context, prefs, scene, is_not_still
        )

        if prefs.launch_mode == MODE_LIST:
            frames = parse_frame_string(settings.frame_list)
            frames_str = format_frame_range(frames)
        else:
            frames_str = (
                f"{frame_start}" if frame_start == frame_end else f"{frame_start}-{frame_end}"
            )

        if render_engine in {RE_CYCLES, RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}:
            mode_str = format_to_title_case(prefs.launch_mode)
            blend_name = Path(blend_file).name
            log_mode = f"{mode_str} (Single Process)" if render_engine == RE_CYCLES else mode_str

            log.debug(
                f"Render ID:{settings.render_id} | "
                f"Blend:'{blend_name}' | "
                f"Engine:{render_engine} | "
                f"Mode:{log_mode} | "
                f"Frame:{frames_str}"
            )

            # Print Cycles Devices
            devices_str = ""
            if render_engine == RE_CYCLES:
                device_details = [f"{d.name} ({d.type}) [{d.id}]" for d in selected_devices]
                log.debug(f"Process[#0] | Devices:{device_details} | Assigned_Frames:{frames_str}")
                if device_details:
                    indent = " " * 8
                    devices_str = ("\\n" + indent).join(device_details)

            print_msg = (
                f"Render ID:{settings.render_id} | "
                f"Engine:{render_engine} | "
                f"Mode:{format_to_title_case(prefs.launch_mode)} | "
                f"Frame:{frames_str}\\n"
            )
            if devices_str:
                print_msg += f"Devices:{devices_str}\\n"

        is_animation = prefs.launch_mode == MODE_SEQ
        script_lines = _generate_base_script(
            context,
            prefs,
            selected_ids,
            is_animation,
            frame_start,
            frame_end,
            frame_step,
            print_msg,
        )

        # System Sleep
        if prefs.set_system_power and (prefs.prevent_sleep or prefs.prevent_monitor_off):
            _add_prevent_sleep_commands(context, prefs, script_lines)

        # Set output Path
        if prefs.launch_mode == MODE_SINGLE:
            if prefs.write_still:
                script_lines.append(
                    self._get_output_path_command(context, prefs, scene, frame_start, blend_file)
                )
                script_lines.append("bpy.ops.render.render(animation=False, write_still=True)")

            else:
                if settings.override_settings.output_path_override:
                    output_path = self.resolve_custom_output_path(
                        context, prefs, scene, frame_start
                    )
                    settings.render_output_folder_path = str(Path(output_path).parent)
                    settings.render_output_filename = Path(output_path).name

                    script_lines.append(f"bpy.context.scene.render.filepath = r'{output_path}'")
                    script_lines.append("bpy.ops.render.render(animation=False, write_still=True)")
                else:
                    output_path = Path(
                        self.get_default_output_path(context, prefs, scene, 1, blend_file)
                    )
                    settings.render_output_folder_path = str(output_path.parent)
                    settings.render_output_filename = output_path.name

                    script_lines.append("bpy.ops.render.render(animation=False, write_still=False)")

        elif prefs.launch_mode == MODE_SEQ:
            script_lines.append(
                self._get_output_path_command(context, prefs, scene, frame_start, blend_file)
            )

            script_lines.append("bpy.ops.render.render(animation=True)")

        elif prefs.launch_mode == MODE_LIST:
            for frame in frames:
                script_lines.extend(
                    [
                        f"bpy.context.scene.frame_set({frame})",
                        self._get_output_path_command(context, prefs, scene, frame, blend_file),
                    ]
                )

                if prefs.write_still:
                    script_lines.append("bpy.ops.render.render(animation=False, write_still=True)")
                else:
                    script_lines.append("bpy.ops.render.render(animation=False, write_still=False)")

        # Set render history output_path
        history_item = prefs.render_history[0]
        history_item.output_folder = settings.render_output_folder_path
        history_item.output_filename = settings.render_output_filename

        # Desktop Notification
        _add_notification_script(context, prefs, script_lines)

        # System Power
        if prefs.set_system_power and prefs.shutdown_after_render:
            self._add_sys_shutdown_execute(context, prefs, script_lines)

        process_id = f"{settings.render_id}_0"
        script_path = self._get_temp_script_path(context, settings, prefs, blend_file, process_id)

        self._add_remove_temp_script(script_lines, script_path)

        temp_script_path = self.create_temp_script(script_path, script_lines)
        terminal_title = self._get_terminal_title(context, prefs, blend_file, process_id)
        log_file_path = self._get_log_file_path(prefs, blend_file, process_id)

        try:
            self._launch_render_process(
                context,
                prefs,
                blend_file,
                temp_script_path,
                terminal_title,
                log_file_path,
                process_id,
            )
        except Exception as e:
            self.report({"ERROR"}, f"Failed to start render: {str(e)}")
            temp_script_path.unlink(missing_ok=True)
            return {"CANCELLED"}

        if prefs.external_terminal and prefs.exit_active_session:
            bpy.app.timers.register(
                lambda: bpy.ops.wm.quit_blender(), first_interval=OPEN_FOLDER_DELAY + 0.1
            )

        return {"FINISHED"}

    def _execute_sequence_parallel_render(
        self,
        context,
        prefs,
        settings,
        selected_devices,
        selected_ids,
        blend_file,
        scene,
    ):
        """Execute parallel rendering for frame secuences."""

        wm = context.window_manager

        try:
            # Attempt to get frame settings
            frame_start, frame_end, frame_step = self._get_frame_settings(
                context, prefs, scene, True
            )
        except ValueError as e:
            # Handle invalid frame range (start >= end for animation)
            log.error(f"Invalid frame range: {str(e)}")
            return {"CANCELLED"}

        blend_name = Path(blend_file).name
        log.debug(
            f"Render ID:{settings.render_id} | "
            f"Blend:'{blend_name}' | "
            f"Engine:CYCLES | "
            f"Mode:{format_to_title_case(prefs.launch_mode)} (Parallel Process) | "
            f"Frames:[{frame_start}-{frame_end}]"
        )

        total_frames = (frame_end - frame_start) // frame_step + 1

        # Only use as many devices as we have frames for
        num_devices = min(len(selected_devices), total_frames)

        # Split frames between devices - FIX: Handle cases where there are fewer frames than devices
        if prefs.frame_allocation == "FRAME_SPLIT":
            if num_devices <= 0:
                self.report({"ERROR"}, "No valid frames to render")
                return {"CANCELLED"}

            frames_per_device = total_frames // num_devices
            remainder = total_frames % num_devices

            device_ranges = []
            current_start = frame_start
            for i in range(num_devices):
                # Calculate end frame based on how many frames each device gets
                current_end = current_start + (frames_per_device - 1) * frame_step

                # Add extra frame to first 'remainder' devices
                if i < remainder:
                    current_end += frame_step

                device_ranges.append((current_start, current_end))
                current_start = current_end + frame_step

        i = 0

        # Parallel Render
        def process_next_device():
            nonlocal i
            if i >= num_devices:
                return

            device = selected_devices[i]
            # dev_frames = device_ranges[i]
            # formatted_frames = format_frame_range(dev_frames)

            # Combine CPU + GPU
            if prefs.combine_cpu_with_gpus:
                devices_to_display = prefs.get_devices_for_display()
                cpu_device = next(
                    (d for d in devices_to_display if d.use and d.type == "CPU"), None
                )
                if cpu_device:
                    device_ids = [device.id, cpu_device.id]
                    log_devices = f"{device.name} ({device.type}) [{device.id}], {cpu_device.name} [{cpu_device.id}]"
                else:
                    device_ids = [device.id]
                    log_devices = f"{device.name} ({device.type}) [{device.id}]"
            else:
                device_ids = [device.id]
                log_devices = f"{device.name} ({device.type}) [{device.id}]"

            # Frame split mode
            if prefs.frame_allocation == "FRAME_SPLIT":
                dev_frame_start, dev_frame_end = device_ranges[i]
                dev_range = device_ranges[i]

                if dev_range[0] == dev_range[1]:
                    log_dev_range = f"{dev_range[0]}"
                else:
                    log_dev_range = f"{dev_range[0]}-{dev_range[1]}"

                print_msg = (
                    f"Render ID:{settings.render_id} | "
                    "Engine:CYCLES | "
                    f"Process[#{i}] | "
                    f"Assigned Frames:[{log_dev_range}]\\n"
                    f"Devices:{log_devices}"
                )
                log.debug(print_msg)

                print_msg = f"{print_msg}\\n"
                script_lines = _generate_base_script(
                    context,
                    prefs,
                    device_ids,
                    True,
                    dev_frame_start,
                    dev_frame_end,
                    frame_step,
                    print_msg,
                )

                script_lines.extend(
                    [
                        "bpy.context.scene.render.use_overwrite = True",
                        "bpy.context.scene.render.use_placeholder = False",
                        "",
                    ]
                )

                dev_frame_start = device_ranges[i][0]
                if settings.override_settings.output_path_override:
                    output_path = self.resolve_custom_output_path(
                        context, prefs, scene, dev_frame_start
                    )
                else:
                    output_path = self.get_default_output_path(
                        context, prefs, scene, dev_frame_start, blend_file
                    )
                script_lines.append(f"bpy.context.scene.render.filepath = r'{output_path}'")

                settings.render_output_folder_path = str(Path(output_path).parent)
                settings.render_output_filename = Path(output_path).name

            # Sequential Mode
            else:
                print_msg = (
                    f"Render ID:{settings.render_id} | "
                    "Engine:CYCLES | "
                    f"Process[#{i}] | "
                    f"Assigned Frames:[{frame_start}-{frame_end}]\\n"
                    f"Devices:{log_devices}"
                )
                log.debug(print_msg)

                print_msg = f"{print_msg}\\n"
                script_lines = _generate_base_script(
                    context, prefs, device_ids, True, frame_start, frame_end, frame_step, print_msg
                )

                script_lines.extend(
                    [
                        "bpy.context.scene.render.use_overwrite = False",
                        "bpy.context.scene.render.use_placeholder = True",
                        "",
                    ]
                )

                if settings.override_settings.output_path_override:
                    output_path = self.resolve_custom_output_path(
                        context, prefs, scene, frame_start
                    )
                else:
                    output_path = self.get_default_output_path(
                        context, prefs, scene, frame_start, blend_file
                    )
                script_lines.append(f"bpy.context.scene.render.filepath = r'{output_path}'")

                settings.render_output_folder_path = str(Path(output_path).parent)
                settings.render_output_filename = Path(output_path).name

            # Set render history output_path
            if i == 0:
                history_item = prefs.render_history[0]
                history_item.output_folder = settings.render_output_folder_path
                history_item.output_filename = settings.render_output_filename

            # Limit CPU Threads
            if (any(d.type == "CPU" and d.use for d in prefs.devices)) and (
                prefs.cpu_threads_limit != 0
            ):
                script_lines.append(f"bpy.context.scene.cycles.threads = {prefs.cpu_threads_limit}")

            # System Sleep
            if (
                i == 0
                and prefs.set_system_power
                and (prefs.prevent_sleep or prefs.prevent_monitor_off)
            ):
                _add_prevent_sleep_commands(context, prefs, script_lines)

            # Add Execute Render Command
            script_lines.append("bpy.ops.render.render(animation=True)")

            # Desktop Notification
            if i == 0:
                _add_notification_script(context, prefs, script_lines)

            if (
                prefs.set_system_power
                and (
                    (prefs.prevent_sleep or prefs.prevent_monitor_off)
                    or prefs.shutdown_after_render
                )
            ) or prefs.send_desktop_notifications:
                # Add temp file creation for all processes
                self._add_create_temp_files_script(
                    context, prefs, script_lines, settings.render_id, i
                )

                # Add shutdown code for the first process
                if i == 0:
                    self._add_wait_for_all_processes(
                        context, prefs, script_lines, settings.render_id, num_devices
                    )

                    # Add System Shutdown
                    if prefs.set_system_power and prefs.shutdown_after_render:
                        self._add_sys_shutdown_execute(context, prefs, script_lines)

            process_id = f"{settings.render_id}_{i}"
            script_path = self._get_temp_script_path(
                context, settings, prefs, blend_file, process_id
            )

            self._add_remove_temp_script(script_lines, script_path)

            temp_script_path = self.create_temp_script(script_path, script_lines)
            terminal_title = self._get_terminal_title(context, prefs, blend_file, process_id)
            log_file_path = self._get_log_file_path(prefs, blend_file, process_id)

            try:
                # for iter_num in range(prefs.iterations_per_device):
                self._launch_render_process(
                    context,
                    prefs,
                    blend_file,
                    temp_script_path,
                    terminal_title,
                    log_file_path,
                    process_id,
                )
            except Exception as e:
                self.report({"ERROR"}, f"Failed to start render for {device.name}: {str(e)}")
                temp_script_path.unlink(missing_ok=True)
                return {"CANCELLED"}

            # Schedule next device if there's a delay and not the last one
            if i < len(selected_devices) - 1:
                bpy.app.timers.register(process_next_device, first_interval=prefs.parallel_delay)
            else:
                # Exit active session
                if prefs.external_terminal and prefs.exit_active_session:
                    bpy.app.timers.register(
                        lambda: bpy.ops.wm.quit_blender(), first_interval=OPEN_FOLDER_DELAY + 0.1
                    )

            i += 1

        process_next_device()

        return {"FINISHED"}

    def _execute_frame_list_parallel_render(
        self,
        context,
        prefs,
        settings,
        selected_devices,
        selected_ids,
        blend_file,
        scene,
    ):
        """Execute parallel render for frame lists."""

        wm = context.window_manager

        frames = parse_frame_string(settings.frame_list)
        if not frames:
            self.report({"WARNING"}, "No valid frames specified.")
            return {"CANCELLED"}

        formatted_frames = format_frame_range(frames)

        blend_name = Path(blend_file).name
        log.debug(
            f"Render ID:{settings.render_id} | "
            f"Blend:'{blend_name}' | "
            f"Engine:CYCLES | "
            f"Mode:{format_to_title_case(prefs.launch_mode)} (Parallel_Process) | "
            f"Frames:{formatted_frames}"
        )

        if not selected_ids:
            self.report({"ERROR"}, "No devices selected")
            return {"CANCELLED"}

        # Split frames among devices
        total_frames = len(frames)

        # Only use as many devices as we have frames for
        num_devices = min(len(selected_devices), total_frames)

        # Handle single device (still render) or parallel devices
        if prefs.device_parallel:
            if num_devices <= 0:
                self.report({"ERROR"}, "No valid frames to render")
                return {"CANCELLED"}

            frames_per_device = total_frames // num_devices
            remainder = total_frames % num_devices

            device_ranges = []
            current_start = 0
            for i in range(num_devices):
                # Calculate the slice of frames for this device
                current_end = current_start + frames_per_device

                if i < remainder:
                    current_end += 1

                device_ranges.append(frames[current_start:current_end])
                current_start = current_end
        else:
            # Single device: process all frames
            device_ranges = [frames]

        # Parallel Render
        def process_next_device():
            nonlocal i  # Access the loop index from the outer scope
            if i >= len(selected_devices):
                return  # All devices processed

            device = selected_devices[i]
            dev_frames = device_ranges[i]
            formatted_frames = format_frame_range(dev_frames)

            # Combine CPU + GPU
            if prefs.combine_cpu_with_gpus:
                devices_to_display = prefs.get_devices_for_display()
                cpu_device = next(
                    (d for d in devices_to_display if d.use and d.type == "CPU"), None
                )
                if cpu_device:
                    device_ids = [device.id, cpu_device.id]
                    log_devices = f"{device.name} ({device.type}) [{device.id}], {cpu_device.name} [{cpu_device.id}]"
                else:
                    device_ids = [device.id]
                    log_devices = f"{device.name} ({device.type}) [{device.id}]"
            else:
                device_ids = [device.id]
                log_devices = f"{device.name} ({device.type}) [{device.id}]"

            msg = (
                f"Render ID:{settings.render_id} | "
                "Engine:CYCLES | "
                f"Process[#{i}] | "
                f"Assigned Frames:{formatted_frames}\\n"
                f"Devices:{log_devices}\\n"
            )

            if not dev_frames:
                log.warning(f"Device {device.name} has no frames to render. Skipping.")
                i += 1
                return

            log.debug(msg)

            # Get frame settings based on current configuration
            frame_start, frame_end, frame_step = self._get_frame_settings(
                context, prefs, scene, False
            )

            # Generate script for this device
            script_lines = _generate_base_script(
                context, prefs, device_ids, False, dev_frames[0], dev_frames[-1], 1, msg
            )

            # Limit CPU Threads
            if (any(d.type == "CPU" and d.use for d in prefs.devices)) and (
                prefs.cpu_threads_limit != 0
            ):
                script_lines.append(f"bpy.context.scene.cycles.threads = {prefs.cpu_threads_limit}")

            # System Sleep
            if (
                i == 0
                and prefs.set_system_power
                and (prefs.prevent_sleep or prefs.prevent_monitor_off)
            ):
                _add_prevent_sleep_commands(context, prefs, script_lines)

            # Add frame-specific commands
            for frame in dev_frames:
                # Set frame and output path
                script_lines.append(f"bpy.context.scene.frame_set({frame})")

                # Set output path
                if settings.override_settings.output_path_override:
                    output_path = self.resolve_custom_output_path(context, prefs, scene, frame)

                else:
                    output_path = self.get_default_output_path(
                        context, prefs, scene, frame, blend_file
                    )

                script_lines.append(f"bpy.context.scene.render.filepath = r'{output_path}'")

                settings.render_output_folder_path = str(Path(output_path).parent)
                settings.render_output_filename = Path(output_path).name

                # Save render file
                if prefs.write_still:
                    script_lines.append("bpy.ops.render.render(animation=False, write_still=True)")
                else:
                    script_lines.append("bpy.ops.render.render(animation=False, write_still=False)")

            if i == 0:
                # Set render history output_path
                history_item = prefs.render_history[0]
                history_item.output_folder = settings.render_output_folder_path
                history_item.output_filename = settings.render_output_filename

            # Desktop Notification
            if i == 0:
                _add_notification_script(context, prefs, script_lines)

            # Print total render time
            script_lines.extend(
                [
                    "",
                    "end_time = time.time()",
                    "total_seconds = end_time - start_time",
                    "hours, remainder = divmod(total_seconds, 3600)",
                    "minutes, seconds = divmod(remainder, 60)",
                    "",
                    "if hours > 0:",
                    '    formatted_total_time = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"',
                    "elif minutes > 0:",
                    '    formatted_total_time = f"{int(minutes)}m {int(seconds)}s"',
                    "else:",
                    '    formatted_total_time = f"{int(seconds)}s"',
                    "",
                    'print(f"Total Render Time: {formatted_total_time} ({total_seconds:.2f} seconds)")',
                    "",
                ]
            )

            if (
                prefs.set_system_power
                and (
                    (prefs.prevent_sleep or prefs.prevent_monitor_off)
                    or prefs.shutdown_after_render
                )
            ) or prefs.send_desktop_notifications:
                # Add temp file creation for all processes
                self._add_create_temp_files_script(
                    context, prefs, script_lines, settings.render_id, i
                )

                # Add shutdown code for the first process
                if i == 0:
                    self._add_wait_for_all_processes(
                        context, prefs, script_lines, settings.render_id, num_devices
                    )

                    # Add System Shutdown
                    if prefs.set_system_power and prefs.shutdown_after_render:
                        self._add_sys_shutdown_execute(context, prefs, script_lines)

            process_id = f"{settings.render_id}_{i}"
            script_path = self._get_temp_script_path(
                context, settings, prefs, blend_file, process_id
            )

            self._add_remove_temp_script(script_lines, script_path)

            temp_script_path = self.create_temp_script(script_path, script_lines)
            terminal_title = self._get_terminal_title(context, prefs, blend_file, process_id)
            log_file_path = self._get_log_file_path(prefs, blend_file, process_id)

            try:
                self._launch_render_process(
                    context,
                    prefs,
                    blend_file,
                    temp_script_path,
                    terminal_title,
                    log_file_path,
                    process_id,
                )
            except Exception as e:
                self.report({"ERROR"}, f"Failed to start render: {str(e)}")
                temp_script_path.unlink(missing_ok=True)
                return {"CANCELLED"}

            # Schedule next device after delay
            if i < len(selected_devices) - 1:
                bpy.app.timers.register(process_next_device, first_interval=prefs.parallel_delay)
            else:
                # Exit active session
                if prefs.external_terminal and prefs.exit_active_session:
                    bpy.app.timers.register(
                        lambda: bpy.ops.wm.quit_blender(), first_interval=OPEN_FOLDER_DELAY + 0.1
                    )

            i += 1

        i = 0
        process_next_device()

        return {"FINISHED"}

    def _get_frame_settings(self, context, prefs, scene, is_animation):
        """Retrieve frame settings for rendering."""

        settings = context.window_manager.recom_render_settings
        try:

            def validate_frame_range(start, end, step):
                if start >= end:
                    if start == end:
                        self.report({"ERROR"}, "Frame Start must be less than Frame End.")
                        prefs.launch_mode = MODE_SINGLE
                        return None
                    raise ValueError("Frame start must be less than frame end for animation.")
                if step <= 0:
                    raise ValueError("Frame step must be a positive integer.")
                return (start, end, step)

            if settings.override_settings.frame_range_override:
                if is_animation:
                    return validate_frame_range(
                        settings.override_settings.frame_start,
                        settings.override_settings.frame_end,
                        settings.override_settings.frame_step,
                    ) or {"CANCELLED"}
                else:
                    frame = settings.override_settings.frame_current
                    if frame < 1:
                        raise ValueError("Still frame must be a positive integer.")
                    return (frame, frame, 1)

            elif settings.use_external_blend:
                info = json.loads(settings.external_scene_info)
                if is_animation:
                    return validate_frame_range(
                        info.get("frame_start", 1),
                        info.get("frame_end", 250),
                        info.get("frame_step", 1),
                    )
                else:
                    frame = info.get("frame_current", 1)
                    return (frame, frame, 1)

            else:
                if is_animation:
                    return validate_frame_range(
                        scene.frame_start, scene.frame_end, scene.frame_step
                    ) or {"CANCELLED"}
                else:
                    frame = scene.frame_current
                    return (frame, frame, 1)

        except Exception as e:
            log.error(f"Invalid frame settings: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid frame range configuration. Error: {str(e)}")

    def _add_create_temp_files_script(self, context, prefs, script_lines, render_id, process_num):
        script_lines.extend(
            [
                "",
                "# Create temp files",
                "import time",
                "import sys",
                "import tempfile",
                "from pathlib import Path",
                "",
                f"render_id = '{render_id}'",
                f"temp_dir = Path(r'{get_addon_temp_dir(prefs)}')",
                "",
                "temp_dir.mkdir(exist_ok=True)",
                "",
                f"temp_file = temp_dir / f'{render_id}_process_{process_num}'",
                "",
                "with open(temp_file, 'w') as f:",
                "    pass",
                "",
            ]
        )

    def _add_wait_for_all_processes(self, context, prefs, script_lines, render_id, num_processes):
        script_lines.extend(
            [
                "# Wait for all processes",
                f"num_processes = {num_processes}",
                f"temp_dir = Path(r'{get_addon_temp_dir(prefs)}')",
                "",
                "temp_dir.mkdir(exist_ok=True)",
                "",
                'print(f"\\nWaiting for other processes to complete...")',
                "",
                "while True:",
                "    all_done = True",
                "    for i in range(num_processes):",
                "        temp_file = temp_dir / f'{render_id}_process_{i}'",
                "        if not temp_file.exists():",
                "            all_done = False",
                "            break",
                "    if all_done:",
                "        break",
                "    time.sleep(2)",
                "",
                'print(f"All processes completed.\\n")',
                "",
                "for i in range(num_processes):",
                "    temp_file = temp_dir / f'{render_id}_process_{i}'",
                "    if temp_file.exists():",
                "        temp_file.unlink()",
                "",
            ]
        )

    def _add_sys_shutdown_execute(self, context, prefs, script_lines):
        """Execute shutdown command with optional delay."""

        delay = prefs.shutdown_delay
        type = prefs.shutdown_type

        script_lines.append("import os")

        if delay > 0:
            script_lines.extend(
                [
                    "import time",
                    f"print('System {type.lower()} scheduled in {delay:.0f} seconds.')",
                    f"time.sleep({delay})",
                ]
            )

        if _IS_WINDOWS:
            # Windows: power off / sleep
            cmd = (
                "shutdown /s /t 0"  # power off immediately
                if type == "POWER_OFF"
                else "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"  # sleep
            )

        elif _IS_MACOS:
            # macOS: use osascript to sleep or shutdown
            cmd = (
                "osascript -e 'tell application \"Finder\" to sleep'"
                if type == "SLEEP"
                else "osascript -e 'tell application \"System Events\" to shut down computer'"
            )

        elif _IS_LINUX:
            # Linux / Unix: systemd or shutdown
            cmd = "systemctl poweroff" if type == "POWER_OFF" else "systemctl suspend"

        script_lines.append(f"print(r'{cmd}')")
        script_lines.append(f"os.system(r'{cmd}')")

    def _add_remove_temp_script(self, script_lines, script_path):
        script_lines.extend(
            [
                "",
                "# Temp script cleanup on Blender exit",
                "import atexit",
                "from pathlib import Path",
                "",
                "def _cleanup_temp_script():",
                f"    temp_path = Path(r'{Path(script_path)}')",
                "    try:",
                "        if temp_path.exists():",
                "            temp_path.unlink()",
                "    except Exception as e:",
                '        print(f"Failed to remove temp file: {e}")',
                "",
                "atexit.register(_cleanup_temp_script)",
                "",
            ]
        )

    def resolve_custom_output_path(self, context, prefs, scene, frame):
        """Resolve the custom output path for rendering."""

        try:
            settings = context.window_manager.recom_render_settings

            # Ensure paths are not None before joining
            if settings.override_settings.output_directory:
                dir_path = Path(settings.override_settings.output_directory)
            else:
                dir_path = get_default_render_output_path()

            file_name = (
                settings.override_settings.output_filename
                if settings.override_settings.output_filename
                else prefs.default_render_filename or "render"
            )

            sep = "." if prefs.filename_separator == "DOT" else "_"

            if prefs.launch_mode == MODE_SEQ:
                hash_string = "#" * prefs.frame_length_digits
                file_name_f = f"{file_name}{sep}{hash_string}"
            else:
                file_name_f = f"{file_name}{sep}{str(frame).zfill(prefs.frame_length_digits)}"

            combined_path = dir_path / file_name_f
            # log.debug(f"Output Path: {combined_path}")

            custom_path = replace_variables(str(combined_path))
            log.debug(f"Output Path Resolved: {custom_path}")

            return custom_path
        except Exception as e:
            log.error(f"Failed to resolve custom output path: {str(e)}")

    def _get_output_path_command(self, context, prefs, scene, frame, blend_file):
        """Get the output path command based on settings."""

        settings = context.window_manager.recom_render_settings

        if settings.override_settings.output_path_override:
            output_path = self.resolve_custom_output_path(context, prefs, scene, frame)
        else:
            output_path = self.get_default_output_path(context, prefs, scene, frame, blend_file)

        settings.render_output_folder_path = str(Path(output_path).parent)
        settings.render_output_filename = Path(output_path).name

        return f"bpy.context.scene.render.filepath = r'{output_path}'"

    def get_default_output_path(self, context, prefs, scene, frame, blend_file):
        """Get the default output path for still or animation."""

        settings = context.window_manager.recom_render_settings

        # Base Path
        if settings.use_external_blend:
            try:
                info = json.loads(settings.external_scene_info)
                base_path_from_source = info.get("filepath", "")
            except json.JSONDecodeError:
                base_path_from_source = "//"
        else:
            base_path_from_source = scene.render.filepath

        if base_path_from_source:
            raw_path = bpy.path.abspath(base_path_from_source)
        else:
            raw_path = get_default_render_output_path()

        # Absolute Path
        full_path = Path(raw_path).resolve()

        is_dir = base_path_from_source.endswith(("/", "\\")) or full_path.is_dir()

        if is_dir:
            base_dir = full_path
            base_name = prefs.default_render_filename or "render"
        else:
            base_dir = full_path.parent
            base_name = full_path.stem

        if settings.override_settings.file_format_override:
            file_format = settings.override_settings.file_format
        else:
            if settings.use_external_blend:
                try:
                    info = json.loads(settings.external_scene_info)
                    file_format = info.get("file_format", "PNG")
                except json.JSONDecodeError:
                    file_format = "PNG"
            else:
                file_format = scene.render.image_settings.file_format

        extensions = {
            "PNG": ".png",
            "OPEN_EXR": ".exr",
            "OPEN_EXR_MULTILAYER": ".exr",
            "JPEG": ".jpg",
            "BMP": ".bmp",
            "TGA": ".tga",
            "TIFF": ".tif",
            "HDR": ".hdr",
        }
        ext = extensions.get(file_format.upper(), ".png")

        frame_str = str(frame).zfill(prefs.frame_length_digits)
        sep = "." if prefs.filename_separator == "DOT" else "_"

        if prefs.launch_mode == MODE_SEQ:
            hash_string = "#" * prefs.frame_length_digits
            filename = f"{base_name}{sep}{hash_string}"
        else:
            filename = f"{base_name}{sep}{frame_str}{ext}"

        final_path = base_dir / filename
        # final_path = final_path.as_posix()  # .replace("\\", "/")

        return str(final_path)

    def create_temp_script(self, script_file_path, script_lines):
        """Creates a temp script in a dedicated addon temp folder."""

        try:
            script_file_path.write_text("\n".join(script_lines), encoding="utf-8")
            return script_file_path
        except Exception as e:
            log.error("Failed to create temporary script", exc_info=True)
            raise RuntimeError("Could not generate render script.") from e

    def _get_terminal_title(self, context, prefs, blend_file, process):
        """Generates a terminal title string."""

        blend_name = Path(blend_file).stem

        return f"Render {process} - {blend_name}"

    def _get_log_file_path(self, prefs, blend_file, process_id):
        """Helper method to generate log file path."""

        if not prefs.log_to_file:
            return ""

        log_folder = Path()

        if prefs.log_to_file_location == "BLEND_PATH":
            log_folder = Path(blend_file).parent
            log.debug(f"Log folder set to BLEND_PATH: {log_folder}")

            if prefs.save_to_log_folder:
                base_dir = Path(blend_file).parent
                log_folder = base_dir / "logs"
                log_folder.mkdir(exist_ok=True)
                log.debug(f"Using 'logs' subfolder: {log_folder}")

        elif prefs.log_to_file_location == "CUSTOM_PATH":
            log_folder = Path(bpy.path.abspath(prefs.log_custom_path)) or Path(
                get_addon_temp_dir(prefs)
            )
            log.debug(f"Log folder set to CUSTOM_PATH: {log_folder}")

        blend_name = Path(blend_file).stem
        log_filename = self._get_log_filename(blend_name, process_id)

        return str(log_folder / log_filename)

    def _get_log_filename(self, blend_name, process_id):
        sanitized_name = sanitize_filename(blend_name)
        timestamp = get_timestamp()

        return f"{sanitized_name}_{process_id}_{timestamp}.log"

    def _launch_render_process(
        self,
        context,
        prefs,
        blend_file,
        temp_script_path,
        terminal_title,
        log_file_path,
        process_id,
    ):
        """Handle cross-platform process launching for rendering"""

        # Get Blender Exec
        blender_exec = Path(
            bpy.path.abspath(prefs.custom_executable_path)
            if prefs.custom_executable
            else bpy.app.binary_path
        )
        if not blender_exec.is_file():
            log.error(f"Blender executable not found at: {blender_exec}")
            raise FileNotFoundError(f"Blender executable not found at: {blender_exec}")

        # Log script content
        if prefs.log_to_file and temp_script_path.exists():
            script_content = temp_script_path.read_text(encoding="utf-8")
            if log_file_path:
                with open(log_file_path, "a") as log_file:
                    log_file.write("\n# Append script\n")
                    log_file.write(script_content)
                    log_file.write("\n")
                    log_file.write("\n# Render log\n")

        # Base cmd
        cmd_list = [
            str(blender_exec),
            "-b",
            str(blend_file),
            "-noaudio",
            "--log",
            "render",
        ]

        # PRE scripts
        if prefs.append_python_scripts and prefs.additional_scripts:
            for entry in prefs.additional_scripts:
                if entry.order == "PRE" and entry.script_path:
                    abs_script_path = Path(bpy.path.abspath(entry.script_path))
                    if abs_script_path.is_file():
                        cmd_list.extend(["-P", str(abs_script_path)])
                    else:
                        log.warning(f"Script not found: {abs_script_path}")

        # Main script
        cmd_list.extend(
            [
                "-P",
                str(temp_script_path),
            ]
        )

        # POST scripts
        if prefs.append_python_scripts and prefs.additional_scripts:
            for entry in prefs.additional_scripts:
                if entry.order == "POST" and entry.script_path:
                    abs_script_path = Path(bpy.path.abspath(entry.script_path))
                    if abs_script_path.is_file():
                        cmd_list.extend(["-P", str(abs_script_path)])
                    else:
                        log.warning(f"Script not found: {abs_script_path}")

        # Set OCIO environment variable
        env = os.environ.copy()
        if prefs.set_ocio and prefs.ocio_path:
            env["OCIO"] = prefs.ocio_path

        if prefs.add_command_line_args and prefs.custom_command_line_args.strip():
            # Split into individual arguments and add them to cmd_list
            for arg in prefs.custom_command_line_args.split():
                cmd_list.append(arg)

        # Logging redirection
        stdout = None
        stderr = None
        if prefs.log_to_file:
            log_file_name = self._get_log_filename(Path(blend_file).stem, process_id)
            log_path = log_file_path or Path(tempfile.gettempdir()) / log_file_name

            stdout = log_path.open("a")
            stderr = subprocess.STDOUT
            log.info(f"Render log redirected to {log_path}")

        # Open Render Folder Delay
        settings = context.window_manager.recom_render_settings
        if (
            prefs.auto_open_output_folder
            and settings.render_output_folder_path
            and not settings.folder_opened
        ):
            folder_path = settings.render_output_folder_path
            settings.folder_opened = True

            def delayed_open():
                print(f"open folder: {folder_path}")
                open_folder(folder_path)

            bpy.app.timers.register(delayed_open, first_interval=OPEN_FOLDER_DELAY)

        # Run process
        if prefs.external_terminal:
            # Convert cmd_list to single line str
            cmd_str = " ".join([shell_quote(arg) for arg in cmd_list])

            # Set OCIO environment for external terminal
            if prefs.set_ocio and prefs.ocio_path:
                quoted_ocio_var = shell_quote(f"OCIO={prefs.ocio_path}")
                # ocio_var = f"OCIO={prefs.ocio_path}"
                if _IS_WINDOWS:
                    cmd_str = f"set {quoted_ocio_var} && {cmd_str}"
                else:
                    cmd_str = f"export {quoted_ocio_var} && {cmd_str}"

            # Add logging to file
            if prefs.log_to_file and log_file_path:
                quoted_log_file_path = shell_quote(log_file_path)

                cmd_str += f" >> {quoted_log_file_path} 2>&1"

                # Add message to console before running the command
                if _IS_WINDOWS:
                    # Use multiple echo statements, each adds its own line
                    cmd_str = (
                        f"echo Rendering in progress... && "
                        f"echo Log written to: {log_file_path} && "
                        f"{cmd_str} && "
                        f"echo Render complete."
                    )
                elif _IS_MACOS:
                    # Show a native macOS dialog, then run command
                    cmd_str = (
                        f'osascript -e \'tell application "System Events" '
                        f'to display dialog "Rendering in progress...\\nLog written to: {log_file_path}"\' '
                        f"&& {cmd_str} && echo Render complete."
                    )
                elif _IS_LINUX:
                    # Use echo -e so that \n is interpreted
                    cmd_str = (
                        f'echo -e "Rendering in progress...\\nLog written to: {log_file_path}" && '
                        f"{cmd_str} && "
                        f"echo Render complete."
                    )

            if _IS_WINDOWS:
                if prefs.keep_terminal_open:
                    win_cmd = f'start "{terminal_title}" cmd /k "{cmd_str}"'
                else:
                    win_cmd = f'start "{terminal_title}" {cmd_str}'

                log.debug(f"Launch Command: {win_cmd}")
                subprocess.Popen(win_cmd, shell=True)

            elif _IS_MACOS:
                if prefs.keep_terminal_open:
                    macos_cmd = f'osascript -e \'tell application "Terminal" to do script "{cmd_str}; read"\''
                else:
                    macos_cmd = (
                        f'osascript -e \'tell application "Terminal" to do script "{cmd_str}"\''
                    )

                log.debug(f"Launch Command: {macos_cmd}")
                os.system(macos_cmd)

            elif _IS_LINUX:
                run_in_terminal(prefs, cmd_str, prefs.keep_terminal_open)

            else:
                self.report({"ERROR"}, f"Unsupported platform: {sys.platform}")
        else:
            log.debug(f"Launch Command: {' '.join(cmd_list)}")
            subprocess.Popen(cmd_list, stdout=stdout, stderr=stderr)


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_version_from_string(version_str):
    """Extracts major and minor version from a string like 'Version: 4.0.1'"""
    if not version_str:
        return None

    # Extract just the "Version" line (ignoring Date/Hash)
    for line in version_str.splitlines():
        if line.startswith("Version:"):
            parts = line.split()
            if len(parts) >= 2 and "." in parts[1]:
                ver_str = parts[1]
                try:
                    major, minor = map(int, ver_str.split(".", 1))  # Only split once
                    return (major, minor)
                except ValueError:
                    pass
    return None


def get_addon_temp_dir(prefs: object) -> Path:
    """Get the addon's temporary directory with version checks."""

    # Determine if we should use user extension path based on Blender version
    use_user_extension = True

    # Check current Blender executable version (bpy.app.version)
    if bpy.app.version < (4, 2):
        log.debug(
            f"Current Blender version {bpy.app.version} is less than 4.2, skipping user extension path"
        )
        use_user_extension = False

    # First try custom temp path if specified and valid
    if prefs.use_custom_temp and prefs.custom_temp_path:
        try:
            custom_path = Path(bpy.path.abspath(prefs.custom_temp_path)).resolve()
            if custom_path.exists() and custom_path.is_dir():
                addon_temp = custom_path / ADDON_NAME
                addon_temp.mkdir(parents=True, exist_ok=True)
                return addon_temp
            else:
                log.warning(f"Custom temp path does not exist or is not a directory: {custom_path}")
        except Exception as e:
            log.error(f"Error using custom temp path: {e}")

    # Fallback: Use user-specific extension path if available and version condition met
    if use_user_extension:
        try:
            user_extension_path = Path(bpy.utils.extension_path_user(base_package, create=True))
            if user_extension_path.exists() and user_extension_path.is_dir():
                return user_extension_path
            else:
                log.warning(
                    f"User extension path does not exist or is not a directory: {user_extension_path}"
                )
        except Exception as e:
            log.error(f"Error using user extension path: {e}")

    # Fallback: Blender temp dir's parent or system temp
    try:
        blender_temp = Path(bpy.app.tempdir).resolve()
        parent_blend_temp = blender_temp.parent

        if parent_blend_temp.exists() and parent_blend_temp.is_dir():
            usable_temp = parent_blend_temp
        else:
            usable_temp = Path(tempfile.gettempdir()).resolve()
            if not usable_temp.exists():
                usable_temp.mkdir(parents=True, exist_ok=True)

        addon_temp = usable_temp / ADDON_NAME
        addon_temp.mkdir(parents=True, exist_ok=True)
        return addon_temp

    except Exception as e:
        raise RuntimeError(f"Failed to create addon temp directory: {e}") from e


classes = (RECOM_OT_BackgroundRender,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
