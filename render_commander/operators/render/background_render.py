# ./operators/render/background_render.py

import json
import logging
import os
import re
import subprocess
import sys
import time
import stat
import shlex
import shutil
import string
import random

from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Union, Tuple

import bpy
import bpy.app.timers
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ... import __package__ as base_package
from ...preferences import get_addon_preferences
from ...utils.constants import *
from ...utils.helpers import (
    get_addon_temp_dir,
    is_blend_or_backup_file,
    replace_variables,
    open_folder,
    calculate_auto_width,
    calculate_auto_height,
    format_to_title_case,
    get_render_engine,
    redraw_ui,
)
from .generate_scripts import (
    _generate_base_script,
    _add_notification_script,
)

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")


log = logging.getLogger(__name__)


@dataclass
class RenderJobChunk:
    """Helper data structure to define a single render process."""

    process_index: int
    device_ids: List[str]
    # Frames can be a range tuple (start, end, step) OR a list of integers
    frames: Union[Tuple[int, int, int], List[int]]
    is_animation_call: bool  # True uses render(animation=True), False uses render(write_still=...)
    description: str


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
    ranges.append((start, end))

    formatted_ranges = []
    for r in ranges:
        if r[0] == r[1]:
            formatted_ranges.append(f"{r[0]}")
        else:
            formatted_ranges.append(f"{r[0]}-{r[1]}")

    return f"[{', '.join(formatted_ranges)}]"


def reset_button_state() -> None:
    """Reset the render button state and redraw UI."""
    try:
        wm = bpy.context.window_manager
        if wm is not None and hasattr(wm, "recom_render_settings"):
            wm.recom_render_settings.disable_render_button = False
            redraw_ui()
    except Exception:
        pass
    return None


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_default_render_output_path() -> Path:
    """Get the default temporary directory path for renders."""
    return Path(tempfile.gettempdir())


def validate_render_settings(operator, context) -> bool:
    """Shared validation logic."""
    settings = context.window_manager.recom_render_settings
    prefs = get_addon_preferences(context)
    scene = context.scene

    # Blend File
    if settings.use_external_blend:
        if not is_blend_or_backup_file(settings.external_blend_file_path):
            msg = "Invalid Blender file"
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False
        if not settings.external_scene_info or settings.external_scene_info == "{}":
            msg = "Scene metadata not loaded. Use 'Read Scene'."
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False
        try:
            if json.loads(settings.external_scene_info).get("blend_filepath", "") != settings.external_blend_file_path:
                msg = "Mismatch between scene data and file. Reload scene data."
                operator.report({"INFO"}, msg)
                log.error(msg)
                return False
        except:
            return False
    elif not bpy.data.filepath:
        if operator.action_type == "RENDER":
            msg = "Save the blend file before rendering"
        else:  # EXPORT
            msg = "Save the blend file before exporting scripts"
        operator.report({"INFO"}, msg)
        log.error(msg)
        return False

    # Save Blend
    if not settings.use_external_blend and prefs.auto_save_before_render and bpy.data.is_dirty:
        try:
            bpy.ops.wm.save_mainfile()
            log.info("Auto-saved")
        except:
            return False

    # FFMPEG File Format
    if not settings.override_settings.file_format_override:
        is_mov = settings.use_external_blend and json.loads(settings.external_scene_info).get("is_movie_format", False)
        if prefs.launch_mode != MODE_SEQ and (scene.render.is_movie_format or is_mov):
            msg = "Current mode does not support FFMPEG animation output"
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False

    # Empty Frame List
    if prefs.launch_mode == MODE_LIST and not settings.frame_list:
        msg = "Frame list required"
        operator.report({"INFO"}, msg)
        log.error(msg)
        return False

    if not settings.use_external_blend and scene.camera is None:
        msg = "No active camera"
        operator.report({"INFO"}, msg)
        log.error(msg)
        return False

    # Executable
    if prefs.blender_executable_source == "CUSTOM":
        raw_path = prefs.custom_executable_path.strip()

        if not raw_path:
            msg = "No Blender executable path is set"
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False

        blender_exec = Path(bpy.path.abspath(raw_path))

        if not blender_exec.exists():
            msg = f"Blender executable path does not exist:\n{blender_exec}"
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False

        if not blender_exec.is_file():
            msg = f"Path is not a file:\n{blender_exec}"
            operator.report({"INFO"}, msg)
            log.error(msg)
            return False

    return True


class RECOM_OT_BackgroundRender(Operator):
    """Main operator for background rendering execution."""

    """
    1. **Validation**: Checks scene integrity, camera, and file status.
    2. **Chunking**: Splits workload based on Engine (Cycles = Devices, Eevee = Iterations) and Mode (Seq/List).
    3. **Generation**: Creates Python logic and Shell/Batch scripts for each process chunk.
    4. **Execution**: Launches a Master Script to run processes in parallel or exports them.
    """

    bl_idname = "recom.background_render"
    bl_label = "Background Render"
    bl_description = "Run a background render"
    bl_options = {"REGISTER", "UNDO"}

    action_type: EnumProperty(
        name="Action Type",
        items=[
            ("RENDER", "Render", "Execute render immediately"),
            ("EXPORT", "Export Script", "Export batch file and script to folder"),
        ],
        default="RENDER",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    directory: StringProperty(
        name="Export Directory",
        description="Directory to save the export files (passed from Export Operator)",
        subtype="DIR_PATH",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def execute(self, context):
        """Main execution method that handles single and parallel rendering."""

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)
        scene = context.scene

        # Validation
        if self.action_type == "RENDER":
            if not validate_render_settings(self, context):
                return {"CANCELLED"}

        blend_file = (
            bpy.path.abspath(settings.external_blend_file_path)
            if settings.use_external_blend and settings.external_blend_file_path
            else bpy.data.filepath
        )

        if self.action_type == "RENDER":
            settings.disable_render_button = True
            bpy.app.timers.register(reset_button_state, first_interval=0.75)

        settings.render_id = generate_job_id()
        settings.folder_opened = False
        render_engine = get_render_engine(context)

        self._add_to_history(context, prefs, settings, scene, render_engine)

        # Dispatch based on Engine and Parallelism logic
        if render_engine == RE_CYCLES:
            return self._execute_cycles_render(context, prefs, settings, render_engine, blend_file, scene)

        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}:
            render_iterations = prefs.render_iterations
            is_multi_instance = prefs.multi_instance

            # Logic Router
            if is_multi_instance and prefs.launch_mode == MODE_LIST:
                chunks = self._calculate_chunks_list_iterations(prefs, settings, render_iterations)

            elif is_multi_instance and prefs.launch_mode == MODE_SEQ:
                chunks = self._calculate_chunks_iterations_parallel(prefs, settings, scene, render_iterations)

            else:
                # Single Process (Single frame, or List/Seq with multi_instance=False)
                chunks = self._calculate_chunks_single_process(prefs, settings, scene, [])

            total_processes = len(chunks)
            if not chunks:
                return {"CANCELLED"}

            return self._process_render_chunks(context, prefs, settings, blend_file, chunks, total_processes)
        else:
            self.report({"ERROR"}, f"Unsupported render engine: {render_engine}")
            return {"CANCELLED"}

    def _add_to_history(self, context, prefs, settings, scene, render_engine):
        history_item = prefs.render_history.add()

        # Populate resolution
        if settings.use_external_blend and settings.external_blend_file_path:
            blend_path = bpy.path.abspath(settings.external_blend_file_path)
            try:
                info = json.loads(settings.external_scene_info)
                if render_engine == RE_CYCLES:
                    history_item.samples = str(info.get("samples", 0))
                elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                    history_item.samples = str(info.get("eevee_samples", 0))
                if not settings.override_settings.format_override:
                    history_item.resolution_x = info.get("resolution_x", 0)
                    history_item.resolution_y = info.get("resolution_y", 0)
            except:
                pass
        else:
            blend_path = bpy.data.filepath
            if render_engine == RE_CYCLES:
                history_item.samples = str(context.scene.cycles.samples)
            elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                history_item.samples = str(context.scene.eevee.taa_render_samples)
            if not settings.override_settings.format_override:
                history_item.resolution_x = context.scene.render.resolution_x
                history_item.resolution_y = context.scene.render.resolution_y

        if render_engine == RE_CYCLES and settings.override_settings.cycles.sampling_override:
            if settings.override_settings.cycles.sampling_mode == "FACTOR":
                history_item.samples = f"{settings.override_settings.cycles.sampling_factor}x"
            else:
                history_item.samples = str(settings.override_settings.cycles.samples)
        elif (render_engine in {RE_EEVEE_NEXT, RE_EEVEE}) and settings.override_settings.eevee_override:
            history_item.samples = str(settings.override_settings.eevee.samples)

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

        # Format frames string
        if prefs.launch_mode == MODE_LIST and settings.frame_list:
            frames = format_frame_range(parse_frame_string(settings.frame_list))
        elif prefs.launch_mode == MODE_SEQ:
            if settings.override_settings.frame_range_override:
                frames = f"{settings.override_settings.frame_start}-{settings.override_settings.frame_end}"
            else:
                if settings.use_external_blend:
                    try:
                        info = json.loads(settings.external_scene_info)
                        frames = f"{info.get('frame_start', '0')}-{info.get('frame_end', '0')}"
                    except:
                        frames = "N/A"
                else:
                    frames = f"{scene.frame_start}-{scene.frame_end}"

        else:  # Single frame
            if settings.override_settings.frame_range_override:
                frames = str(settings.override_settings.frame_current)
            else:
                if settings.use_external_blend:
                    try:
                        info = json.loads(settings.external_scene_info)
                        frames = str(info.get("frame_current", "0"))
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

        item_index = len(prefs.render_history) - 1
        prefs.render_history.move(item_index, 0)

        if len(prefs.render_history) > RENDER_HISTORY_LIMIT:
            prefs.render_history.remove(RENDER_HISTORY_LIMIT)

    def _execute_cycles_render(self, context, prefs, settings, render_engine, blend_file, scene):
        """Execute rendering for Cycles engine, handling device selection and splitting."""
        devices_to_display = prefs.get_devices_for_display()
        selected_devices = [d for d in devices_to_display if d.use]
        current_backend = prefs.compute_device_type

        # Handle CPU/GPU combination logic
        if (prefs.launch_mode == MODE_SEQ and prefs.device_parallel) or (
            prefs.launch_mode == MODE_LIST and prefs.device_parallel
        ):
            selected_devices = [
                d for d in devices_to_display if d.use and (not prefs.combine_cpu_with_gpus or d.type != "CPU")
            ]

        # Handle fallback to CPU if no backend/devices
        if current_backend == "NONE":
            self._handle_cpu_fallback(prefs)
            devices_to_display = prefs.get_devices_for_display()
            selected_devices = [d for d in devices_to_display if d.use]
        elif not selected_devices:
            self._handle_no_devices_selected(prefs)

        # Cycles Device Type (CPU vs GPU) for Scene settings
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

        # Determine Workload Strategy
        chunks = []

        # Condition: GPU Parallel (Sequence or List)
        if cycles_device == "GPU" and len(selected_devices) > 1 and prefs.device_parallel:
            if prefs.launch_mode == MODE_SEQ:
                chunks = self._calculate_chunks_sequence_parallel(context, prefs, settings, scene, selected_devices)
            elif prefs.launch_mode == MODE_LIST:
                chunks = self._calculate_chunks_list_parallel(prefs, settings, selected_devices)
            else:  # MODE_SINGLE, falling back to single process logic
                selected_ids = [d.id for d in selected_devices]
                chunks = self._calculate_chunks_single_process(prefs, settings, scene, selected_ids)
        else:
            # CPU or Single GPU or Single Process Mode
            selected_ids = [d.id for d in selected_devices]
            chunks = self._calculate_chunks_single_process(prefs, settings, scene, selected_ids)

        if not chunks:
            return {"CANCELLED"}

        # Execute Unified
        total_parallel_processes = len(chunks) if prefs.device_parallel else 1
        return self._process_render_chunks(context, prefs, settings, blend_file, chunks, total_parallel_processes)

    # Workload Calculators

    def _calculate_chunks_iterations_parallel(self, prefs, settings, scene, process_count: int) -> List[RenderJobChunk]:
        """
        Split a frame sequence across multiple Blender instances (Iterations)
        without assigning specific hardware device IDs.
        """

        try:
            frame_start, frame_end, frame_step = self._get_frame_settings(prefs, settings, scene, True)
        except ValueError as e:
            self.report({"INFO"}, str(e))
            log.error(str(e))
            return []

        total_frames = (frame_end - frame_start) // frame_step + 1

        # Ensure we don't spawn more processes than frames
        actual_process_count = min(process_count, total_frames)

        if actual_process_count <= 0:
            error_msg = "No valid frames to render"
            self.report({"INFO"}, error_msg)
            log.error(error_msg)
            return []

        chunks = []
        current_start = frame_start

        # Calculate Splits
        frames_per_process = total_frames // actual_process_count
        remainder = total_frames % actual_process_count

        if prefs.frame_allocation != "FRAME_SPLIT":
            # If not split (Placeholder/Sequential), every instance attempts full range
            frames_per_process = 0

        for i in range(actual_process_count):
            # For Eevee/Workbench pass an empty list for device_ids.
            device_ids = []

            if prefs.frame_allocation == "FRAME_SPLIT":
                count = frames_per_process + (1 if i < remainder else 0)
                # Calculate end based on count
                current_end = current_start + (count - 1) * frame_step

                chunk_frames = (current_start, current_end, frame_step)
                desc = f"Process[#{i}] | Split:[{current_start}-{current_end}]"

                chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

                current_start = current_end + frame_step
            else:
                # Sequential / Placeholder logic - All get full range
                chunk_frames = (frame_start, frame_end, frame_step)
                desc = f"Process[#{i}] | FullRange:[{frame_start}-{frame_end}]"
                chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

        return chunks

    def _calculate_chunks_list_iterations(self, prefs, settings, process_count: int) -> List[RenderJobChunk]:
        """Split a frame list across multiple processes (Iterations)."""
        frames = parse_frame_string(settings.frame_list)
        if not frames:
            self.report({"WARNING"}, "No valid frames specified.")
            return []

        total_frames = len(frames)
        # Ensure we don't spawn more processes than we have frames
        actual_process_count = min(process_count, total_frames)

        if actual_process_count < 1:
            return []

        chunks = []

        # Calculate Splits
        frames_per_process = total_frames // actual_process_count
        remainder = total_frames % actual_process_count
        current_idx = 0

        for i in range(actual_process_count):
            # Empty device list for Eevee/Workbench
            device_ids = []

            # Determine how many frames this process gets
            count = frames_per_process + (1 if i < remainder else 0)

            end_idx = current_idx + count
            subset = frames[current_idx:end_idx]
            current_idx = end_idx

            if subset:
                desc = f"Process[#{i}] | Frames: {format_frame_range(subset)}"
                # is_animation_call is False for List mode
                chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

        return chunks

    def _calculate_chunks_single_process(self, prefs, settings, scene, selected_ids) -> List[RenderJobChunk]:
        """Create a single job chunk for standard execution."""

        if prefs.launch_mode == MODE_LIST:
            frames = parse_frame_string(settings.frame_list)
            is_animation = False  # List mode processes frames individually in the script
            desc_frames = format_frame_range(frames)
        else:
            is_not_still = prefs.launch_mode != MODE_SINGLE

            try:
                frame_start, frame_end, frame_step = self._get_frame_settings(prefs, settings, scene, is_not_still)
            except ValueError as e:
                self.report({"INFO"}, str(e))
                log.error(str(e))
                return []

            frames = (frame_start, frame_end, frame_step)
            is_animation = prefs.launch_mode == MODE_SEQ
            desc_frames = f"{frame_start}" if frame_start == frame_end else f"{frame_start}-{frame_end}"

        return [
            RenderJobChunk(
                process_index=0,
                device_ids=selected_ids,
                frames=frames,
                is_animation_call=is_animation,
                description=f"Mode: {format_to_title_case(prefs.launch_mode)} | Frames: {desc_frames}",
            )
        ]

    def _calculate_chunks_sequence_parallel(
        self, context, prefs, settings, scene, selected_devices
    ) -> List[RenderJobChunk]:
        """Split a frame sequence across available devices."""

        try:
            frame_start, frame_end, frame_step = self._get_frame_settings(prefs, settings, scene, True)
        except ValueError as e:
            self.report({"INFO"}, str(e))
            log.error(str(e))
            return []

        total_frames = (frame_end - frame_start) // frame_step + 1
        num_devices = min(len(selected_devices), total_frames)

        if num_devices <= 0:
            error_msg = "No valid frames to render"
            self.report({"INFO"}, error_msg)
            log.error(error_msg)
            return []

        chunks = []
        current_start = frame_start

        # Calculate Splits
        frames_per_device = total_frames // num_devices
        remainder = total_frames % num_devices

        if prefs.frame_allocation != "FRAME_SPLIT":
            # If not split, every device gets full range
            frames_per_device = 0  # Signal to use full range loop below logic

        for i in range(num_devices):
            device = selected_devices[i]
            device_ids = self._get_combined_device_ids(prefs, device)

            if prefs.frame_allocation == "FRAME_SPLIT":
                count = frames_per_device + (1 if i < remainder else 0)
                # Calculate end based on count
                current_end = current_start + (count - 1) * frame_step

                chunk_frames = (current_start, current_end, frame_step)
                desc = f"Process[#{i}] | Split: [{current_start}-{current_end}]"

                chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

                current_start = current_end + frame_step
            else:
                # Sequential / Placeholder logic - All get full range
                chunk_frames = (frame_start, frame_end, frame_step)
                desc = f"Process[#{i}] | FullRange: [{frame_start}-{frame_end}]"
                chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

        return chunks

    def _calculate_chunks_list_parallel(self, prefs, settings, selected_devices) -> List[RenderJobChunk]:
        """Split a list of frames across available devices."""
        frames = parse_frame_string(settings.frame_list)
        if not frames:
            self.report({"WARNING"}, "No valid frames specified.")
            return []

        total_frames = len(frames)
        num_devices = min(len(selected_devices), total_frames)

        chunks = []

        # Split logic
        frames_per_device = total_frames // num_devices
        remainder = total_frames % num_devices
        current_idx = 0

        for i in range(num_devices):
            device = selected_devices[i]
            device_ids = self._get_combined_device_ids(prefs, device)

            end_idx = current_idx + frames_per_device + (1 if i < remainder else 0)
            subset = frames[current_idx:end_idx]
            current_idx = end_idx

            if subset:
                desc = f"Process[#{i}] | Frames: {format_frame_range(subset)}"
                chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

        return chunks

    def _get_combined_device_ids(self, prefs, primary_device):
        """Helper to combine CPU with GPU if preference is set."""
        if prefs.combine_cpu_with_gpus:
            devices_to_display = prefs.get_devices_for_display()
            cpu_device = next((d for d in devices_to_display if d.use and d.type == "CPU"), None)
            if cpu_device:
                return [primary_device.id, cpu_device.id]
        return [primary_device.id]

    def _handle_cpu_fallback(self, prefs):
        for device in prefs.devices:
            if device.type == "CPU":
                device.use = True
        prefs.compute_device_type = "NONE"

    def _handle_no_devices_selected(self, prefs):
        prefs.compute_device_type = "NONE"
        for device in prefs.devices:
            if device.type == "CPU":
                device.use = True
        self.report({"WARNING"}, "No devices selected. Fallback to CPU.")

    # Unified Execution

    def _process_render_chunks(
        self, context, prefs, settings, blend_file, chunks: List[RenderJobChunk], total_processes: int
    ):
        """Unified method to generate scripts for all chunks and execute them."""

        if self.action_type == "EXPORT":
            folder_name = prefs.export_scripts_folder_name if prefs.export_scripts_subfolder else ""
            target_dir = Path(self.directory) / folder_name
        else:
            target_dir = get_addon_temp_dir(prefs)

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        generated_script_paths = []
        for chunk in chunks:
            # Generate the Python Content
            script_lines = self._generate_chunk_python_script(
                context,
                prefs,
                settings,
                scene=context.scene,
                chunk=chunk,
                blend_file=blend_file,
                target_dir=target_dir,
                total_processes=total_processes,
            )

            # Identifiers
            process_id = chunk.process_index

            # Generate Files (.py and .bat/.sh)
            shell_script_path = self._create_process_files(
                prefs, settings, blend_file, script_lines, process_id, target_dir
            )

            if shell_script_path:
                generated_script_paths.append(shell_script_path)

        if not generated_script_paths:
            return {"CANCELLED"}

        master_script_path = None
        if self.action_type == "RENDER":
            master_script_path = self._create_master_script(
                prefs, settings, blend_file, target_dir, generated_script_paths
            )
        elif self.action_type == "EXPORT" and prefs.export_master_script and len(chunks) > 1:
            master_script_path = self._create_master_script(
                prefs, settings, blend_file, target_dir, generated_script_paths
            )

        if self.action_type == "RENDER":
            script_to_run = master_script_path or generated_script_paths[0]
            try:
                self._execute_script_file(prefs, settings, script_to_run)
            except Exception as exc:
                self.report({"ERROR"}, f"Failed to start render: {exc}")
                return {"CANCELLED"}

        if prefs.exit_active_session:
            bpy.app.timers.register(lambda: bpy.ops.wm.quit_blender(), first_interval=OPEN_FOLDER_DELAY + 0.1)

        return {"FINISHED"}

    def _generate_chunk_python_script(
        self, context, prefs, settings, scene, chunk: RenderJobChunk, blend_file, target_dir, total_processes
    ):
        """Generates the full Python script content for a specific chunk."""

        # Determine Frame Bounds for Base Script (start, end, step)
        if isinstance(chunk.frames, tuple):
            f_start, f_end, f_step = chunk.frames
        else:  # List
            f_start = chunk.frames[0]
            f_end = chunk.frames[-1]
            f_step = 1

        print_msg = f"Render ID: {settings.render_id} | {chunk.description}"
        log.debug(print_msg)

        script_lines = _generate_base_script(
            context, prefs, chunk.device_ids, chunk.is_animation_call, f_start, f_end, f_step, print_msg
        )

        # Parallelism specific flags (Placeholder/Overwrite)
        if prefs.device_parallel and prefs.launch_mode == MODE_SEQ:
            script_lines.append("# Parallel Render Settings")
            if prefs.frame_allocation == "FRAME_SPLIT":
                script_lines.extend(
                    [
                        "bpy.context.scene.render.use_overwrite = True",
                        "bpy.context.scene.render.use_placeholder = False",
                        "",
                    ]
                )
            else:
                script_lines.extend(
                    [
                        "bpy.context.scene.render.use_overwrite = False",
                        "bpy.context.scene.render.use_placeholder = True",
                        "",
                    ]
                )

        # CPU Threads limit
        if (any(d.type == "CPU" and d.use for d in prefs.devices)) and (prefs.cpu_threads_limit != 0):
            script_lines.append(f"bpy.context.scene.cycles.threads = {prefs.cpu_threads_limit}")

        # Output Path & Render Call Logic

        # Helper to set path and add render call
        def add_render_cmd(frame, is_anim, write_still):
            out_path = self._resolve_output_path(prefs, settings, scene, frame, blend_file)

            script_lines.extend(
                [
                    "# Output Settings",
                    f"bpy.context.scene.render.filepath = r'{out_path}'",
                    "",
                ]
            )

            # Add notification
            if chunk.process_index == 0:
                _add_notification_script(prefs, script_lines)

            script_lines.extend(
                [
                    "# Start Render",
                    "bpy.ops.render.render(animation=True)"
                    if is_anim
                    else f"bpy.ops.render.render(animation=False, write_still={write_still})",
                    "",
                ]
            )

        if chunk.is_animation_call:
            # Mode: Sequence
            add_render_cmd(f_start, True, False)
        elif isinstance(chunk.frames, tuple):
            # Mode: Single Frame (tuple used in single process fallback)
            write_s = prefs.write_still or settings.override_settings.output_path_override
            add_render_cmd(f_start, False, write_s)
        else:
            # Mode: List (list of frames)
            for frame in chunk.frames:
                script_lines.append("# Set Frame List")
                script_lines.append(f"bpy.context.scene.frame_set({frame})")

                add_render_cmd(frame, False, prefs.write_still)

            # Add timing for list mode
            script_lines.extend(
                [
                    "",
                    "end_time = time.time()",
                    "total_seconds = end_time - start_time",
                    'print(f"Total Render Time: {total_seconds:.2f} seconds")',
                    "",
                ]
            )

        # Post-Processing / Coordination (Notification, Shutdown, Wait)
        # Only process 0 manages shared resources/shutdown usually
        if chunk.process_index == 0:
            # Update history entry with actual output path from the first chunk
            if prefs.render_history:
                hist = prefs.render_history[0]
                hist.output_folder = settings.render_output_folder_path
                hist.output_filename = settings.render_output_filename

            # _add_notification_script(context, prefs, script_lines)

        # Parallel Sync Logic
        requires_sync = prefs.send_desktop_notifications

        if total_processes > 1 and requires_sync:
            self._add_create_temp_files_script(context, prefs, script_lines, settings.render_id, chunk.process_index)
            if chunk.process_index == 0:
                self._add_wait_for_all_processes(context, prefs, script_lines, settings.render_id, total_processes)
                if prefs.shutdown_after_render:
                    self._add_sys_shutdown_execute(context, prefs, script_lines)
        elif chunk.process_index == 0 and prefs.shutdown_after_render:
            # Single process shutdown
            self._add_sys_shutdown_execute(context, prefs, script_lines)

        # Cleanup Temp Script (if RENDER mode)
        if self.action_type == "RENDER":
            process_id = f"{settings.render_id}_script{chunk.process_index}"
            script_name = f"{bpy.path.clean_name(Path(blend_file).stem)}_{process_id}.py"
            self._add_remove_temp_script(script_lines, target_dir / script_name)

        return script_lines

    def _resolve_output_path(self, prefs, settings, scene, frame, blend_file):
        """Helper to resolve output path and side-effect update settings/history variables."""
        if settings.override_settings.output_path_override:
            output_path = self._resolve_custom_output_path(prefs, settings, scene, frame)
        else:
            output_path = self._get_default_output_path(prefs, settings, scene, frame, blend_file)

        # Side effects required for history and open folder logic
        settings.render_output_folder_path = str(Path(output_path).parent)
        settings.render_output_filename = Path(output_path).name
        return str(output_path)

    # UNIFIED FILE GENERATION METHODS

    def _create_process_files(self, prefs, settings, blend_file, script_lines, process_id, target_dir):
        """Creates the .py script and the OS-specific shell/batch script."""

        blend_name = Path(blend_file).stem
        sanitized_blend_name = bpy.path.clean_name(blend_name)
        timestamp = get_timestamp()
        render_id = settings.render_id

        py_filename = f"{sanitized_blend_name}_{render_id}_script{process_id}.py"
        py_path = target_dir / py_filename

        try:
            py_path.write_text("\n".join(script_lines), encoding="utf-8")
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to save python script: {exc}")
            return None

        # Determine Shell/Batch Script Content
        if prefs.blender_executable_source == "SYSTEM":
            blender_exec = "blender"
        elif prefs.blender_executable_source == "CUSTOM":
            blender_exec = bpy.path.abspath(prefs.custom_executable_path)
        else:
            blender_exec = bpy.app.binary_path

        shell_content = []
        exec_extension = ".bat" if _IS_WINDOWS else ".sh"

        def quote_win_arg(arg):
            return subprocess.list2cmdline([arg])

        # Platform-specific header construction
        if _IS_WINDOWS:
            shell_content = [
                "@echo off",
                'cd /d "%~dp0"',
                "",
                f'set "RC_BLENDER={str(blender_exec)}"',
                f'set "RC_BLEND={str(blend_file)}"',
                f'set "RC_SCRIPT=%~dp0{py_filename}"',
            ]
            if prefs.set_ocio and prefs.ocio_path:
                shell_content.append(f'set "OCIO={prefs.ocio_path}"')
        else:
            shell_content = [
                "#!/bin/bash",
                'cd "$(dirname "$0")"',
                "",
                f"RC_BLENDER={shlex.quote(str(blender_exec))}",
                f"RC_BLEND={shlex.quote(str(blend_file))}",
                f'RC_SCRIPT="$(pwd)/{py_filename}"',
            ]
            if prefs.set_ocio and prefs.ocio_path:
                shell_content.append(f"export OCIO={shlex.quote(prefs.ocio_path)}")

        # Additional Scripts
        def add_script_vars(order: str):
            idx = 1
            for entry in prefs.additional_scripts:
                if entry.order == order and entry.script_path:
                    abs_path = Path(bpy.path.abspath(entry.script_path)).resolve()
                    if abs_path.is_file():
                        var = f"RC_{order}_SCRIPT_{idx}"
                        if _IS_WINDOWS:
                            shell_content.append(f'set "{var}={str(abs_path)}"')
                        else:
                            shell_content.append(f"{var}={shlex.quote(str(abs_path))}")
                        idx += 1
            return idx - 1

        pre_c = add_script_vars("PRE") if prefs.append_python_scripts else 0
        post_c = add_script_vars("POST") if prefs.append_python_scripts else 0

        def env_ref(var: str) -> str:
            if _IS_WINDOWS:
                return f'"%{var}%"'
            return f"${var}"

        cmd_parts = [
            env_ref("RC_BLENDER"),
            "--background",
            env_ref("RC_BLEND"),
        ]

        for i in range(1, pre_c + 1):
            cmd_parts.extend(["--python", env_ref(f"RC_PRE_SCRIPT_{i}")])

        # Render Commander Script
        cmd_parts.extend(["--python", env_ref("RC_SCRIPT")])

        for i in range(1, post_c + 1):
            cmd_parts.extend(["--python", env_ref(f"RC_POST_SCRIPT_{i}")])

        # Handle Custom Arguments
        if prefs.add_command_line_args and prefs.custom_command_line_args.strip():
            cmd_parts.extend([prefs.custom_command_line_args])

        # Debug Mode
        if prefs.debug_mode:
            cmd_parts.append("-d")

            if prefs.debug_value != 0:
                cmd_parts.extend(["--debug-value", str(prefs.debug_value)])

            if prefs.verbose_level != "2":  # Default is medium
                cmd_parts.extend(["--verbose", prefs.verbose_level])

            if prefs.debug_cycles and get_render_engine(bpy.context) == RE_CYCLES:
                cmd_parts.append("--debug-cycles")

        # Log Redirection
        if prefs.log_to_file:
            log_file_path = self._get_log_file_path(prefs, settings, blend_file, process_id, target_dir)
            if _IS_WINDOWS:
                RC_LOG = str(log_file_path)
                shell_content.append(f'set "RC_LOG={RC_LOG}"')
            else:
                RC_LOG = shlex.quote(str(log_file_path))
                shell_content.append(f"RC_LOG={RC_LOG}")

            cmd_parts.append(f"--log-file {env_ref('RC_LOG')}")

        cmd_str = " ".join(cmd_parts)

        shell_content.extend(["", f'echo "Executing Render: {blend_name} ({render_id} - worker{process_id})"'])
        if prefs.log_to_file:
            shell_content.append(f"echo Log written to: {env_ref(RC_LOG)}")
        shell_content.append("")
        shell_content.append(cmd_str)

        # Pause/Cleanup logic
        if prefs.keep_terminal_open:
            shell_content.append("pause" if _IS_WINDOWS else 'read -p "Press enter to exit..."')

        if self.action_type == "RENDER":
            # Delete script
            shell_content.append("")
            shell_content.append('(goto) 2>nul & del "%~f0" && exit' if _IS_WINDOWS else 'rm -- "$0"')
        else:
            shell_content.append("exit")

        # Write File
        exec_path = target_dir / f"{sanitized_blend_name}_{render_id}_worker{process_id}{exec_extension}"
        try:
            exec_path.write_text("\n".join(shell_content), encoding="utf-8")
            if not _IS_WINDOWS:
                current_mode = exec_path.stat().st_mode
                exec_path.chmod(current_mode | stat.S_IEXEC)
        except Exception as exc:
            self.report({"ERROR"}, f"Failed to save execution file: {exc}")
            return None

        # Auto open export
        if self.action_type == "EXPORT" and prefs.auto_open_exported_folder and not settings.folder_opened:
            settings.folder_opened = True

            def delayed_open():
                open_folder(target_dir)

            bpy.app.timers.register(delayed_open, first_interval=OPEN_FOLDER_DELAY)

        return exec_path

    def _create_master_script(self, prefs, settings, blend_file, target_dir, script_paths):
        """Creates a master script that launches multiple process scripts."""
        if not script_paths:
            return None

        render_id = settings.render_id
        sanitized_blend_name = bpy.path.clean_name(Path(blend_file).stem)

        if _IS_WINDOWS:
            master_name = f"{sanitized_blend_name}_{render_id}_master.bat"
            use_wt = prefs.use_windows_terminal_tabs and shutil.which("wt") is not None

            content = [
                "@echo off",
                'cd /d "%~dp0"',
                f"echo Launching {len(script_paths)} processes for ID: {render_id}",
                "echo.",
                "setlocal enabledelayedexpansion",
                "",
            ]

            if use_wt:
                content.append("echo Opening render terminals in Windows Terminal tabs...")
                delay_seconds = int(prefs.parallel_delay)
                abs_paths = [str(Path(p).resolve()) for p in script_paths]

                if delay_seconds <= 0:
                    term_cmd = f"wt -w {render_id}"
                    for i, abs_path in enumerate(abs_paths):
                        if i == 0:
                            term_cmd += f' cmd /k "{abs_path}"'
                        else:
                            term_cmd += f' ; wt -w {render_id} new-tab cmd /k "{abs_path}"'
                    content.append(term_cmd)
                else:
                    content.append(f'wt -w {render_id} --title "{render_id} worker0" cmd /k "{abs_paths[0]}"')
                    for i, p in enumerate(abs_paths[1:], start=1):
                        content.extend(
                            [
                                f"echo Waiting {delay_seconds}s before next tab...",
                                f"timeout /t {delay_seconds} /nobreak >nul",
                                f'wt -w {render_id} new-tab --title "{render_id} worker{i}" cmd /k "{p}"',
                            ]
                        )
            else:
                for i, path in enumerate(script_paths):
                    if i > 0 and prefs.parallel_delay > 0:
                        content.extend(
                            [
                                f"echo Waiting {int(prefs.parallel_delay)}s...",
                                f"timeout /t {int(prefs.parallel_delay)} /nobreak >nul",
                            ]
                        )
                    content.append(f'start "" "{path.name}"')

            content.extend(["", "echo All processes launched."])
            if self.action_type == "RENDER":
                content.append('(goto) 2>nul & del "%~f0"')
            content.append("exit")
        else:
            master_name = f"{sanitized_blend_name}_{render_id}_master.sh"
            content = [
                "#!/bin/bash",
                'cd "$(dirname "$0")"',
                f'echo "Launching {len(script_paths)} processes for ID: {render_id}"',
                "",
            ]

            if _IS_MACOS:
                term_cmd = "open -a Terminal"
            else:
                term_cmd = self._get_linux_terminal_command(prefs)

            for i, path in enumerate(script_paths):
                if i > 0 and prefs.parallel_delay > 0:
                    content.extend(
                        [f'echo "Waiting {int(prefs.parallel_delay)}s..."', f"sleep {int(prefs.parallel_delay)}"]
                    )

                if _IS_MACOS:
                    content.append(f'open -a Terminal "{path}"')
                else:
                    content.append(f'{term_cmd} "./{path.name}" &' if term_cmd else f"./{path.name} &")

            content.extend(["", 'echo "All processes launched."'])
            if self.action_type == "RENDER":
                content.append('rm -- "$0"')
            content.append("exit")

        # Write File
        master_path = target_dir / master_name
        try:
            master_path.write_text("\n".join(content), encoding="utf-8")
            if not _IS_WINDOWS:
                current_mode = master_path.stat().st_mode
                master_path.chmod(current_mode | stat.S_IEXEC)
            return master_path
        except Exception as e:
            log.error(f"Failed to write master script: {e}")
            return None

    def _execute_script_file(self, prefs, settings, script_path):
        """Execute the generated shell/batch script."""

        script_path = Path(script_path).resolve()

        # Auto open output folder
        if prefs.auto_open_output_folder and settings.render_output_folder_path and not settings.folder_opened:
            settings.folder_opened = True

            def delayed_open():
                open_folder(settings.render_output_folder_path)
                return None

            bpy.app.timers.register(delayed_open, first_interval=OPEN_FOLDER_DELAY)

        # Execute Script
        try:
            log.info(f'Executing script: "{script_path}"')

            if _IS_WINDOWS:
                try:
                    os.startfile(script_path)
                except OSError:
                    subprocess.Popen(["start", "", script_path], shell=True)

            elif _IS_MACOS:
                subprocess.Popen([script_path])

            elif _IS_LINUX:
                try:
                    subprocess.Popen([script_path], shell=True)
                except PermissionError:
                    subprocess.Popen(["xdg-open", script_path])

        except Exception as e:
            msg = f"Failed to launch script: {e}"
            log.error(msg)
            self.report({"ERROR"}, msg)

    def _get_linux_terminal_command(self, prefs):
        # Helper to check if the binary exists (safely ignoring flags like '--' or '-e')
        def is_installed(cmd_str: str) -> bool:
            if not cmd_str:
                return False
            try:
                # Safely split "alacritty -e" -> "alacritty"
                binary = shlex.split(cmd_str)[0]
                return shutil.which(binary) is not None
            except ValueError:
                return False

        custom_cmd = getattr(prefs, "linux_terminal_config", "").strip()
        if custom_cmd:
            if is_installed(custom_cmd):
                return custom_cmd
            else:
                log.warning(f"Custom terminal configuration '{custom_cmd}' not found. Falling back to auto-detect.")

        fallback_terminals = [
            "gnome-terminal --",
            "xfce4-terminal -x",
            "konsole -e",
            "terminator -x",
            "xterm -e",
        ]

        for term in fallback_terminals:
            if is_installed(term):
                return term

        if shutil.which("x-terminal-emulator"):
            return "x-terminal-emulator -e"

        log.warning("No standard terminal emulator found on system. Defaulting to 'xterm -e'.")
        return "xterm -e"

    # SHARED HELPERS (Frame parsing, etc)

    def _get_frame_settings(self, prefs, settings, scene, is_animation):
        try:

            def check(prefs, start, end, step):
                if start >= end and is_animation:
                    prefs.launch_mode = MODE_SINGLE
                    raise ValueError("Frame start must be less than frame end.")

                return (start, end, step)

            if settings.override_settings.frame_range_override:
                if is_animation:
                    return check(
                        prefs,
                        settings.override_settings.frame_start,
                        settings.override_settings.frame_end,
                        settings.override_settings.frame_step,
                    )
                return (settings.override_settings.frame_current,) * 2 + (1,)

            elif settings.use_external_blend:
                info = json.loads(settings.external_scene_info)
                if is_animation:
                    return check(
                        prefs, info.get("frame_start", 1), info.get("frame_end", 250), info.get("frame_step", 1)
                    )
                val = info.get("frame_current", 1)
                return (val, val, 1)

            else:
                if is_animation:
                    return check(prefs, scene.frame_start, scene.frame_end, scene.frame_step)
                return (scene.frame_current,) * 2 + (1,)

        except Exception as exc:
            raise ValueError(f"Invalid frame range: {exc}")

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
                "temp_dir.mkdir(exist_ok=True)",
                "",
                f"temp_file = temp_dir / f'{render_id}_process_{process_num}.tmp'",
                "with open(temp_file, 'w') as f: pass",
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
                'print(f"\\nWaiting for other processes to complete...")',
                "",
                "while True:",
                "    all_done = True",
                "    for i in range(num_processes):",
                "        if not (temp_dir / f'{render_id}_process_{i}.tmp').exists():",
                "            all_done = False",
                "            break",
                "    if all_done: break",
                "    time.sleep(2)",
                "",
                'print(f"All processes completed.\\n")',
                "",
                "for i in range(num_processes):",
                "    f = temp_dir / f'{render_id}_process_{i}.tmp'",
                "    if f.exists(): f.unlink()",
                "",
            ]
        )

    def _add_sys_shutdown_execute(self, context, prefs, script_lines):
        delay, type_ = prefs.shutdown_delay, prefs.shutdown_type
        script_lines.append("import os")
        if delay > 0:
            script_lines.extend(
                [
                    "import time",
                    f"print('System {type_.lower()} scheduled in {delay:.0f} seconds.')",
                    f"time.sleep({delay})",
                ]
            )

        cmd = ""
        if _IS_WINDOWS:
            cmd = "shutdown /s /t 0" if type_ == "POWER_OFF" else "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"
        elif _IS_MACOS:
            cmd = (
                "osascript -e 'tell application \"System Events\" to shut down computer'"
                if type_ != "SLEEP"
                else "osascript -e 'tell application \"Finder\" to sleep'"
            )
        elif _IS_LINUX:
            cmd = "systemctl poweroff" if type_ == "POWER_OFF" else "systemctl suspend"

        script_lines.extend([f"print(r'{cmd}')", f"os.system(r'{cmd}')"])

    def _add_remove_temp_script(self, script_lines, script_path):
        script_lines.extend(
            [
                "",
                "# Temp script cleanup",
                "import atexit",
                "from pathlib import Path",
                "",
                "def _cleanup_temp_script():",
                f"    try: Path(r'{Path(script_path)}').unlink(missing_ok=True)",
                "    except: pass",
                "atexit.register(_cleanup_temp_script)",
                "",
            ]
        )

    def _resolve_custom_output_path(self, prefs, settings, scene, frame):
        try:
            dir_path = (
                Path(settings.override_settings.output_directory)
                if settings.override_settings.output_directory
                else get_default_render_output_path()
            )
            file_name = settings.override_settings.output_filename or prefs.default_render_filename or "render"
            sep = "." if prefs.filename_separator == "DOT" else "_"

            if prefs.launch_mode == MODE_SEQ:
                file_name_f = f"{file_name}{sep}{'#' * prefs.frame_length_digits}"
            else:
                file_name_f = f"{file_name}{sep}{str(frame).zfill(prefs.frame_length_digits)}"

            return replace_variables(str(dir_path / file_name_f))
        except Exception as exc:
            log.error(f"Failed to resolve custom output path: {exc}")

    def _get_default_output_path(self, prefs, settings, scene, frame, blend_file):
        if settings.use_external_blend:
            try:
                base_path = json.loads(settings.external_scene_info).get("filepath", "//")
            except:
                base_path = "//"
        else:
            base_path = scene.render.filepath

        full_path = Path(bpy.path.abspath(base_path) if base_path else get_default_render_output_path()).resolve()
        is_dir = base_path.endswith(("/", "\\")) or full_path.is_dir()
        base_dir, base_name = (
            (full_path, prefs.default_render_filename or "render") if is_dir else (full_path.parent, full_path.stem)
        )

        # File format ext
        if settings.override_settings.file_format_override:
            ff = settings.override_settings.file_format
        elif settings.use_external_blend:
            try:
                ff = json.loads(settings.external_scene_info).get("file_format", "PNG")
            except:
                ff = "PNG"
        else:
            ff = scene.render.image_settings.file_format

        ext = {
            "PNG": ".png",
            "OPEN_EXR": ".exr",
            "OPEN_EXR_MULTILAYER": ".exr",
            "JPEG": ".jpg",
            "BMP": ".bmp",
            "TGA": ".tga",
            "TIFF": ".tif",
        }.get(ff.upper(), ".png")

        sep = "." if prefs.filename_separator == "DOT" else "_"
        if prefs.launch_mode == MODE_SEQ:
            filename = f"{base_name}{sep}{'#' * prefs.frame_length_digits}"
        else:
            filename = f"{base_name}{sep}{str(frame).zfill(prefs.frame_length_digits)}{ext}"

        return str(base_dir / filename)

    def _get_log_folder(self, prefs, blend_file, target_dir=None):
        """Determine the log folder based on preferences and context."""
        if not prefs.log_to_file:
            return None

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
            custom_path = Path(bpy.path.abspath(prefs.log_custom_path)) or Path(get_addon_temp_dir(prefs))
            if not custom_path:
                custom_path = Path(get_addon_temp_dir(prefs))
            log_folder = _ensure_dir(custom_path / logs_folder_name_str)

        return log_folder

    def _get_log_file_path(self, prefs, settings, blend_file, process_id, target_dir=None):
        """Get the full path for a log file."""
        if not prefs.log_to_file:
            return ""

        log_folder = self._get_log_folder(prefs, blend_file, target_dir)
        if not log_folder:
            return ""

        return str(
            log_folder / f"{bpy.path.clean_name(Path(blend_file).stem)}_{settings.render_id}_worker{process_id}.log"
        )


class RECOM_OT_ExportRenderScript(Operator):
    bl_idname = "recom.export_render_script"
    bl_label = "Export Render Scripts"
    bl_description = "Export script render files"
    bl_options = {"REGISTER", "INTERNAL"}

    directory: StringProperty(
        name="Export Directory",
        description="Directory to save the export files",
        subtype="DIR_PATH",
    )
    filter_folder: BoolProperty(
        default=True,
        options={"HIDDEN", "SKIP_SAVE"},
    )
    action_type: EnumProperty(
        name="Action Type",
        items=[
            ("RENDER", "Render", "Execute render immediately"),
            ("EXPORT", "Export Script", "Export batch file and script to folder"),
        ],
        default="EXPORT",
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def _get_export_directory(self, context, prefs) -> Path:
        """Determine export directory based on preferences."""
        settings = context.window_manager.recom_render_settings

        if prefs.export_output_target == "BLEND_DIR":
            if settings.use_external_blend and settings.external_blend_file_path:
                blend_dir = settings.external_blend_file_path
            else:
                blend_dir = bpy.data.filepath
            return Path(blend_dir).parent.as_posix()

        elif prefs.export_output_target == "CUSTOM_PATH" and prefs.custom_export_path:
            custom_path = Path(prefs.custom_export_path).resolve()
            if not custom_path.exists():
                log.warning(f"Custom export path does not exist: '{custom_path}'. Using temp directory instead.")
            else:
                return custom_path

        # Fallback to temporary directory
        temp_dir = get_addon_temp_dir(prefs).as_posix()
        log.debug(f"Using temporary directory for export: {temp_dir}")

        return temp_dir

    def invoke(self, context, event):
        prefs = get_addon_preferences(context)

        if not validate_render_settings(self, context):
            return {"CANCELLED"}

        if prefs.export_output_target != "SELECT_DIR":
            self.directory = str(self._get_export_directory(context, prefs))
            return self.execute(context)

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            prefs = get_addon_preferences(context)
            settings = context.window_manager.recom_render_settings

            bpy.ops.recom.background_render(action_type="EXPORT", directory=self.directory)

            folder_name = prefs.export_scripts_folder_name if prefs.export_scripts_subfolder else ""
            target_dir = Path(self.directory) / folder_name

            self.report({"INFO"}, f"Render scripts exported ({settings.render_id})")
            log.info(f'Render scripts exported to: "{str(target_dir)}"')

        except Exception as exc:
            self.report({"ERROR"}, f"Failed to export; check the console for details")
            log.error(f"Failed to export the render scripts to '{self.directory}': {exc}")
            return {"CANCELLED"}

        return {"FINISHED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        col = layout.column()

        folder_row = col.row(heading="Sub-Folder")
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(prefs, "export_scripts_folder_name", text="")

        render_engine = get_render_engine(context)
        is_parallel = prefs.launch_mode in {MODE_SEQ, MODE_LIST} and (
            prefs.device_parallel if render_engine == RE_CYCLES else prefs.multi_instance
        )
        if is_parallel:
            col.prop(prefs, "export_master_script", text="Create Master Script")
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Folder")


class RECOM_OT_RenderImage(Operator):
    bl_idname = "recom.render_image"
    bl_label = "Render Image"
    bl_description = "Render a single frame"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        old_launch_mode = prefs.launch_mode
        prefs.launch_mode = MODE_SINGLE

        try:
            bpy.ops.recom.background_render(action_type="RENDER")
        except Exception as e:
            prefs.launch_mode = old_launch_mode
            self.report({"ERROR"}, f"{e}")
            return {"CANCELLED"}

        return {"FINISHED"}


class RECOM_OT_RenderAnimation(Operator):
    bl_idname = "recom.render_animation"
    bl_label = "Render Animation"
    bl_description = "Render a full frame range"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        old_launch_mode = prefs.launch_mode
        prefs.launch_mode = MODE_SEQ

        try:
            bpy.ops.recom.background_render(action_type="RENDER")
        except Exception as e:
            prefs.launch_mode = old_launch_mode
            self.report({"ERROR"}, f"{e}")
            return {"CANCELLED"}

        return {"FINISHED"}


class RECOM_OT_ExportImage(Operator):
    bl_idname = "recom.export_image"
    bl_label = "Export Render Image Script"
    bl_description = "Export a render script for a single frame"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        old_launch_mode = prefs.launch_mode
        prefs.launch_mode = MODE_SINGLE

        try:
            bpy.ops.recom.export_render_script("INVOKE_DEFAULT")
            prefs.launch_mode = old_launch_mode
        except Exception as e:
            prefs.launch_mode = old_launch_mode
            self.report({"ERROR"}, f"{e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class RECOM_OT_ExportAnimation(Operator):
    bl_idname = "recom.export_animation"
    bl_label = "Export Render Animation Script"
    bl_description = "Export a render script for an animation"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        old_launch_mode = prefs.launch_mode
        prefs.launch_mode = MODE_SEQ

        try:
            bpy.ops.recom.export_render_script("INVOKE_DEFAULT")
            prefs.launch_mode = old_launch_mode
        except Exception as e:
            prefs.launch_mode = old_launch_mode
            self.report({"ERROR"}, f"{e}")
            return {"CANCELLED"}
        return {"FINISHED"}


classes = (
    RECOM_OT_BackgroundRender,
    RECOM_OT_ExportRenderScript,
    RECOM_OT_RenderImage,
    RECOM_OT_RenderAnimation,
    RECOM_OT_ExportImage,
    RECOM_OT_ExportAnimation,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
