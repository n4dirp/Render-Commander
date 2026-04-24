"""
This module contains the primary operators and workload management 
logic for Render Commander. Serves as the high-level controller that 
coordinates user input, calculates render distribution, and triggers 
the script generation engine to produce final exportable assets.
"""

import json
import logging
import re
import time
import string
import random
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List, Union, Tuple

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

from ..preferences import get_addon_preferences
from ..utils.constants import (
    MODE_SINGLE,
    MODE_SEQ,
    MODE_LIST,
    RE_CYCLES,
    RE_EEVEE_NEXT,
    RE_EEVEE,
    RE_WORKBENCH,
    RENDER_HISTORY_LIMIT,
)
from ..utils.helpers import (
    get_addon_temp_dir,
    is_blend_or_backup_file,
    replace_variables,
    calculate_auto_width,
    calculate_auto_height,
    format_to_title_case,
    get_render_engine,
)
from ..cycles_devices import get_devices_for_display
from .generate_scripts import _generate_base_script, _create_process_files, _resolve_script_base_name


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


def parse_frame_string(frame_str: str) -> List[int]:
    """Parse a frame range string into a sorted list of integers."""
    frames = set()
    tokens = re.findall(r"\d+(?:-\d+)?", frame_str)
    for token in tokens:
        if "-" in token:
            start, end = sorted(map(int, token.split("-")))
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

    ranges.append((start, end))

    formatted_ranges = []
    for r in ranges:
        if r[0] == r[1]:
            formatted_ranges.append(f"{r[0]}")
        else:
            formatted_ranges.append(f"{r[0]}-{r[1]}")

    return f"[{', '.join(formatted_ranges)}]"


def get_scene_info(settings):
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


def validate_render_settings(operator, context) -> bool:
    """Shared validation logic."""
    settings = context.window_manager.recom_render_settings
    prefs = get_addon_preferences(context)
    scene = context.scene

    ext_info = {}
    if settings.use_external_blend:
        ext_info = get_scene_info(settings) or {}

    # Blend File
    if settings.use_external_blend:
        if not is_blend_or_backup_file(settings.external_blend_file_path):
            msg = "Invalid Blender file"
            operator.report({"WARNING"}, msg)
            log.error("%s", msg)
            return False

        if not settings.external_scene_info or settings.external_scene_info == "{}":
            msg = "Scene metadata not loaded. Use 'Read Scene'."
            operator.report({"WARNING"}, msg)
            log.error("%s", msg)
            return False

        if ext_info.get("blend_filepath", "") != settings.external_blend_file_path:
            msg = "Mismatch between scene data and file. Reload scene data."
            operator.report({"WARNING"}, msg)
            log.error("%s", msg)
            return False

    elif not bpy.data.filepath:
        msg = "Save the blend file before exporting scripts"
        operator.report({"WARNING"}, msg)
        log.error("%s", msg)
        return False

    # Save Blend
    if not settings.use_external_blend and prefs.auto_save_before_render and bpy.data.is_dirty:
        try:
            bpy.ops.wm.save_mainfile()
            log.info("Auto-saved")
        except Exception as e:
            log.error("Failed to auto-save blend file: %s", e)
            return False

    # FFMPEG File Format
    if not settings.override_settings.file_format_override:
        is_mov = settings.use_external_blend and ext_info.get("is_movie_format", False)
        if prefs.launch_mode != MODE_SEQ and (scene.render.is_movie_format or is_mov):
            msg = "Current mode does not support FFMPEG animation output"
            operator.report({"WARNING"}, msg)
            log.error("%s", msg)
            return False

    # Empty Frame List
    if prefs.launch_mode == MODE_LIST and not settings.frame_list:
        msg = "Frame list required"
        operator.report({"WARNING"}, msg)
        log.error("%s", msg)
        return False

    if not settings.use_external_blend and scene.camera is None:
        msg = "No active camera"
        operator.report({"WARNING"}, msg)
        log.error("%s", msg)
        return False

    # Animation: Prevent identical start/end frames
    if prefs.launch_mode == MODE_SEQ:
        if settings.override_settings.frame_range_override:
            start, end = settings.override_settings.frame_start, settings.override_settings.frame_end
        elif settings.use_external_blend:
            start = ext_info.get("frame_start", 1)
            end = ext_info.get("frame_end", 250)
        else:
            start = scene.frame_start
            end = scene.frame_end

        if start == end:
            msg = "Frame start must be less than end for animation"
            operator.report({"WARNING"}, msg)
            log.error("%s", msg)
            prefs.launch_mode = MODE_SINGLE
            return False

    return True


class RECOM_OT_ExportRenderScript(Operator):
    """Main operator for background rendering script generation."""

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

    @classmethod
    def description(cls, context, properties):
        prefs = get_addon_preferences(context)
        target = prefs.export_output_target
        messages = {
            "SELECT_DIR": "Choose a directory for render scripts",
            "BLEND_DIR": "Save render scripts next to the .blend file",
            "CUSTOM_PATH": f"Save render scripts to custom directory:\n'{prefs.custom_export_path}'",
        }

        return messages.get(target, "")

    def invoke(self, context, event):
        prefs = get_addon_preferences(context)

        if not validate_render_settings(self, context):
            return {"CANCELLED"}

        if prefs.export_output_target != "SELECT_DIR":
            self.directory = str(self._get_export_directory(context, prefs))
            return self.execute(context)

        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        prefs = get_addon_preferences(context)

        col = layout.column()

        folder_row = col.row(heading="Subfolder")
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(prefs, "export_scripts_folder_name", text="")
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Folder")

    def execute(self, context):
        """Main execution method that handles single and parallel rendering."""
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)
        scene = context.scene

        ext_info = {}
        if settings.use_external_blend:
            ext_info = get_scene_info(settings) or {}

        blend_file = (
            bpy.path.abspath(settings.external_blend_file_path)
            if settings.use_external_blend and settings.external_blend_file_path
            else bpy.data.filepath
        )

        settings.render_id = generate_job_id()
        settings.folder_opened = False
        render_engine = get_render_engine(context)

        self._add_to_history(context, prefs, settings, scene, render_engine, ext_info)

        # Dispatch based on Engine and Parallelism logic
        if render_engine == RE_CYCLES:
            self._execute_cycles_export(context, prefs, settings, blend_file, scene, ext_info)

        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE, RE_WORKBENCH}:
            render_iterations = prefs.render_iterations
            is_multi_instance = prefs.multi_instance

            # Logic Router
            if is_multi_instance and prefs.launch_mode == MODE_LIST:
                chunks = self._calculate_chunks_list_iterations(settings, render_iterations)

            elif is_multi_instance and prefs.launch_mode == MODE_SEQ:
                chunks = self._calculate_chunks_iterations_parallel(prefs, settings, scene, render_iterations, ext_info)

            else:
                # Single Process (Single frame, or List/Seq with multi_instance=False)
                chunks = self._calculate_chunks_single_process(prefs, settings, scene, [], ext_info)

            if not chunks:
                return {"CANCELLED"}

            # Track workers for logging
            settings.worker_count = len(chunks)

            self._process_render_chunks(context, prefs, settings, blend_file, chunks, ext_info)
        else:
            self.report({"ERROR"}, f"Unsupported render engine: {render_engine}")
            return {"CANCELLED"}

        if settings.first_worker_info:
            self.report({"INFO"}, f"Saved: {settings.first_worker_info} ({settings.worker_count})")

        folder_name = prefs.export_scripts_folder_name if prefs.export_scripts_subfolder else ""
        target_dir = Path(self.directory) / folder_name
        log.info('Render scripts saved to: "%s"', str(target_dir))

        return {"FINISHED"}

    def _get_export_directory(self, context, prefs) -> Path:
        """Determine export directory based on preferences."""
        settings = context.window_manager.recom_render_settings

        if prefs.export_output_target == "BLEND_DIR":
            if settings.use_external_blend and settings.external_blend_file_path:
                blend_dir = settings.external_blend_file_path
            else:
                blend_dir = bpy.data.filepath

            return Path(blend_dir).parent.as_posix()

        if prefs.export_output_target == "CUSTOM_PATH" and prefs.custom_export_path:
            custom_path = Path(prefs.custom_export_path).resolve()
            if not custom_path.exists():
                log.warning("Custom export path does not exist: '%s'. Using temp directory instead.", custom_path)
            else:
                return custom_path

        # Fallback to temporary directory
        temp_dir = get_addon_temp_dir().as_posix()
        log.debug("Using temporary directory for export: %s", temp_dir)

        return temp_dir

    def _add_to_history(self, context, prefs, settings, scene, render_engine, ext_info: dict) -> None:
        """Records the current render task details into the addon's persistent history collection."""

        history_item = prefs.render_history.add()

        override = settings.override_settings
        is_external = settings.use_external_blend
        is_eevee = render_engine in {RE_EEVEE_NEXT, RE_EEVEE}

        if not is_external:
            ext_info = {}

        # File Paths
        blend_path = (
            bpy.path.abspath(settings.external_blend_file_path)
            if (is_external and settings.external_blend_file_path)
            else bpy.data.filepath
        )

        if blend_path:
            path_obj = Path(blend_path)
            history_item.blend_path = str(path_obj)
            history_item.blend_dir = str(path_obj.parent)
            history_item.blend_file_name = path_obj.name
        else:
            history_item.blend_path = "Unknown"
            history_item.blend_dir = "Unknown"
            history_item.blend_file_name = "untitled"

        # Resolution
        if override.format_override:
            res_mode = override.resolution_mode
            history_item.resolution_x = (
                override.resolution_x if res_mode in {"SET_WIDTH", "CUSTOM"} else calculate_auto_width(context)
            )
            history_item.resolution_y = (
                override.resolution_y if res_mode in {"SET_HEIGHT", "CUSTOM"} else calculate_auto_height(context)
            )
        else:
            history_item.resolution_x = ext_info.get("resolution_x", 0) if is_external else scene.render.resolution_x
            history_item.resolution_y = ext_info.get("resolution_y", 0) if is_external else scene.render.resolution_y

        # Samples
        if render_engine == RE_CYCLES:
            if override.cycles.sampling_override:
                history_item.samples = (
                    f"{override.cycles.sampling_factor}x"
                    if override.cycles.sampling_mode == "FACTOR"
                    else str(override.cycles.samples)
                )
            else:
                history_item.samples = str(ext_info.get("samples", 0) if is_external else scene.cycles.samples)

        elif is_eevee:
            if override.eevee_override:
                history_item.samples = str(override.eevee.samples)
            else:
                history_item.samples = str(
                    ext_info.get("eevee_samples", 0) if is_external else scene.eevee.taa_render_samples
                )

        # Frames
        if prefs.launch_mode == MODE_LIST and settings.frame_list:
            frames = format_frame_range(parse_frame_string(settings.frame_list))
        elif prefs.launch_mode == MODE_SEQ:
            if override.frame_range_override:
                frames = f"{override.frame_start}-{override.frame_end}"
            else:
                frames = (
                    f"{ext_info.get('frame_start', 0)}-{ext_info.get('frame_end', 0)}"
                    if is_external
                    else f"{scene.frame_start}-{scene.frame_end}"
                )
        else:  # Single frame
            if override.frame_range_override:
                frames = str(override.frame_current)
            else:
                frames = str(ext_info.get("frame_current", 0)) if is_external else str(scene.frame_current)

        history_item.frames = frames

        # File Format
        if override.file_format_override:
            history_item.file_format = override.file_format
        else:
            history_item.file_format = (
                ext_info.get("file_format", "") if is_external else scene.render.image_settings.file_format
            )

        # Metadata and Export Path
        history_item.render_engine = render_engine
        history_item.render_id = settings.render_id
        history_item.launch_mode = format_to_title_case(prefs.launch_mode)
        history_item.date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        export_path = Path(bpy.path.abspath(self.directory))
        if prefs.export_scripts_subfolder:
            export_path = export_path / prefs.export_scripts_folder_name
        history_item.export_path = str(export_path)

        # Manage History List Limits
        item_index = len(prefs.render_history) - 1
        prefs.render_history.move(item_index, 0)

        if len(prefs.render_history) > RENDER_HISTORY_LIMIT:
            prefs.render_history.remove(RENDER_HISTORY_LIMIT)

    def _execute_cycles_export(self, context, prefs, settings, blend_file, scene, ext_info: dict) -> dict:
        """Generate export scripts for Cycles engine, handling device selection and splitting."""

        if not prefs.manage_cycles_devices:
            chunks = self._calculate_chunks_single_process(prefs, settings, scene, [], ext_info)
            settings.worker_count = len(chunks)
            return self._process_render_chunks(context, prefs, settings, blend_file, chunks, ext_info)

        devices_to_display = get_devices_for_display(prefs)
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
            devices_to_display = get_devices_for_display(prefs)
            selected_devices = [d for d in devices_to_display if d.use]
        elif not selected_devices:
            self._handle_no_devices_selected(prefs)

        # Cycles Device Type (CPU vs GPU) for Scene settings
        if settings.override_settings.cycles.device_override:
            cycles_device = settings.override_settings.cycles.device
        else:
            cycles_device = (
                str(ext_info.get("device", "CPU")) if settings.use_external_blend else str(scene.cycles.device)
            )

        # Determine Workload Strategy
        chunks = []

        # Condition: GPU Parallel (Sequence or List)
        if cycles_device == "GPU" and len(selected_devices) > 1 and prefs.device_parallel:
            if prefs.launch_mode == MODE_SEQ:
                chunks = self._calculate_chunks_sequence_parallel(prefs, settings, scene, selected_devices, ext_info)
            elif prefs.launch_mode == MODE_LIST:
                chunks = self._calculate_chunks_list_parallel(prefs, settings, selected_devices)
            else:  # MODE_SINGLE, falling back to single process logic
                selected_ids = [d.id for d in selected_devices]
                chunks = self._calculate_chunks_single_process(prefs, settings, scene, selected_ids, ext_info)
        else:
            # CPU or Single GPU or Single Process Mode
            selected_ids = [d.id for d in selected_devices]
            chunks = self._calculate_chunks_single_process(prefs, settings, scene, selected_ids, ext_info)

        if not chunks:
            return {"CANCELLED"}

        # Execute Unified
        # Track workers for logging
        settings.worker_count = len(chunks)
        return self._process_render_chunks(context, prefs, settings, blend_file, chunks, ext_info)

    # Workload Calculators

    def _calculate_chunks_iterations_parallel(
        self, prefs, settings, scene, process_count: int, ext_info: dict
    ) -> List[RenderJobChunk]:
        """
        Split a frame sequence across multiple Blender instances (Iterations)
        without assigning specific hardware device IDs.
        """

        try:
            frame_start, frame_end, frame_step = self._get_frame_settings(prefs, settings, scene, True, ext_info)
        except ValueError as e:
            self.report({"WARNING"}, str(e))
            log.error("%s", str(e))
            return []

        total_frames = (frame_end - frame_start) // frame_step + 1

        # Ensure we don't spawn more processes than frames
        actual_process_count = min(process_count, total_frames)

        if actual_process_count <= 0:
            error_msg = "No valid frames to render"
            self.report({"WARNING"}, error_msg)
            log.error("%s", error_msg)
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

    def _calculate_chunks_list_iterations(self, settings, process_count: int) -> List[RenderJobChunk]:
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
                desc = f"Process[#{i}] | Frame: {format_frame_range(subset)}"
                # is_animation_call is False for List mode
                chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

        return chunks

    def _calculate_chunks_single_process(
        self, prefs, settings, scene, selected_ids, ext_info: dict
    ) -> List[RenderJobChunk]:
        """Create a single job chunk for standard execution."""

        if prefs.launch_mode == MODE_LIST:
            frames = parse_frame_string(settings.frame_list)
            is_animation = False  # List mode processes frames individually in the script
            desc_frames = format_frame_range(frames)
        else:
            is_not_still = prefs.launch_mode != MODE_SINGLE

            try:
                frame_start, frame_end, frame_step = self._get_frame_settings(
                    prefs, settings, scene, is_not_still, ext_info
                )
            except ValueError as e:
                self.report({"WARNING"}, str(e))
                log.error("%s", str(e))
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
                description=f"Mode: {format_to_title_case(prefs.launch_mode)} | Frame: {desc_frames}",
            )
        ]

    def _calculate_chunks_sequence_parallel(
        self, prefs, settings, scene, selected_devices, ext_info: dict
    ) -> List[RenderJobChunk]:
        """Split a frame sequence across available devices."""

        try:
            frame_start, frame_end, frame_step = self._get_frame_settings(prefs, settings, scene, True, ext_info)
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
                desc = f"Process[#{i}] | Frame: {format_frame_range(subset)}"
                chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

        return chunks

    def _get_combined_device_ids(self, prefs, primary_device):
        """Helper to combine CPU with GPU if preference is set."""
        if prefs.combine_cpu_with_gpus:
            devices_to_display = get_devices_for_display(prefs)
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
        self, context, prefs, settings, blend_file, chunks: List[RenderJobChunk], ext_info: dict
    ):
        """Generate scripts for all chunks."""

        folder_name = prefs.export_scripts_folder_name if prefs.export_scripts_subfolder else ""
        target_dir = Path(self.directory) / folder_name

        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        settings.first_worker_info = ""

        generated_script_paths = []
        for chunk in chunks:
            # Generate the Python Content
            script_lines = self._generate_chunk_python_script(context, prefs, settings, context.scene, chunk, ext_info)

            # Identifiers
            process_id = chunk.process_index

            # Generate Files (.py and .bat/.sh)
            shell_script_path = _create_process_files(
                self, prefs, settings, blend_file, script_lines, process_id, target_dir
            )

            if shell_script_path:
                generated_script_paths.append(shell_script_path)

            if settings.first_worker_info == "":
                blend_name = Path(blend_file).stem if blend_file else "untitled"
                sanitized_blend_name = bpy.path.clean_name(blend_name)
                settings.first_worker_info = _resolve_script_base_name(sanitized_blend_name, settings, prefs)

        if not generated_script_paths:
            return {"CANCELLED"}

        if prefs.exit_active_session:
            bpy.ops.wm.quit_blender()

        return {"FINISHED"}

    def _generate_chunk_python_script(
        self, context, prefs, settings, scene, chunk: RenderJobChunk, ext_info: dict
    ) -> List[str]:
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
            context,
            prefs,
            chunk.device_ids,
            chunk.is_animation_call,
            f_start,
            f_end,
            f_step,
            print_msg,
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
        def add_render_cmd(frame, is_anim, write_still, ext_info):
            script_lines.append("# Filepath Settings")

            out_path = self._resolve_output_path(prefs, settings, scene, ext_info)
            base_name_no_templates = re.sub(r"\{[^}]*\}", "", out_path)

            if "#" in base_name_no_templates and prefs.launch_mode == MODE_SINGLE:
                script_lines.append(f'bpy.context.scene.render.filepath = r"{out_path}"')
                script_lines.append(
                    f"bpy.context.scene.render.filepath = bpy.context.scene.render.frame_path(frame={frame})"
                )
            else:
                # Add frame to render filename
                script_lines.append(f'bpy.context.scene.render.filepath = r"{out_path}"')

            script_lines.append("")

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
            add_render_cmd(f_start, True, False, ext_info)
        elif isinstance(chunk.frames, tuple):
            # Mode: Single Frame (tuple used in single process fallback)
            write_s = prefs.write_still or settings.override_settings.output_path_override
            add_render_cmd(f_start, False, write_s, ext_info)
        else:
            # Mode: List (list of frames)
            out_path = self._resolve_output_path(prefs, settings, scene, ext_info)

            is_contiguous = len(chunk.frames) > 1 and (chunk.frames[-1] - chunk.frames[0] == len(chunk.frames) - 1)

            if is_contiguous:
                frames_str = f"frames_to_render = range({chunk.frames[0]}, {chunk.frames[-1] + 1})"
            else:
                str_frames = [str(f) for f in chunk.frames]
                line_chunks = [", ".join(str_frames[i : i + 15]) for i in range(0, len(str_frames), 15)]

                wrapped_frames = ",\n    ".join(line_chunks)
                frames_str = f"frames_to_render = [\n    {wrapped_frames}\n]"

            script_lines.extend(
                [
                    "# Set Frame List",
                    f'base_filepath = r"{out_path}"',
                    "",
                    frames_str,
                    "",
                    "for frame in frames_to_render:",
                    "    bpy.context.scene.render.filepath = base_filepath",
                    "    bpy.context.scene.frame_set(frame)",
                    "    bpy.context.scene.render.filepath = bpy.context.scene.render.frame_path(frame=frame)",
                    f"    bpy.ops.render.render(animation=False, write_still={prefs.write_still})",
                    "",
                ]
            )

            # Add timing
            if prefs.track_render_time:
                script_lines.extend(
                    [
                        "end_time = time.time()",
                        "total_seconds = end_time - start_time",
                        'print(f"Total Render Time: {total_seconds:.2f} seconds")',
                        "",
                    ]
                )

        if chunk.process_index == 0:
            # Update history entry with actual output path from the first chunk
            if prefs.render_history:
                hist = prefs.render_history[0]
                hist.output_folder = settings.render_output_folder_path

                if hist.output_folder:
                    abs_path = Path(hist.output_folder).resolve()
                    hist.is_output_path_valid = abs_path.is_dir()
                else:
                    hist.is_output_path_valid = False
        return script_lines

    def _resolve_output_path(self, prefs, settings, scene, ext_info: dict) -> str:
        """Resolves the output path and updates settings/history variables."""
        is_override = settings.override_settings.output_path_override

        try:
            # Determine base directory and filename based on the mode
            if is_override:
                dir_path = settings.override_settings.output_directory or '/tmp/'
                file_name = settings.override_settings.output_filename
            else:
                base_path = ext_info.get("filepath", "//") if settings.use_external_blend else scene.render.filepath
                last_slash = max(base_path.rfind("/"), base_path.rfind("\\"))
                if last_slash == -1:
                    dir_path, file_name = "", base_path
                else:
                    dir_path, file_name = base_path[: last_slash + 1], base_path[last_slash + 1 :]

            # Normalize directory
            if dir_path and not dir_path.endswith(("/", "\\")):
                dir_path += "/"

            if not file_name:
                file_name = prefs.default_render_filename or "render"

            # Apply frame formatting
            sep = "." if prefs.filename_separator == "DOT" else "_"
            file_name_no_templates = re.sub(r"\{[^}]*\}", "", file_name)

            if "#" not in file_name_no_templates:
                file_name = f"{file_name}{sep}{'#' * prefs.frame_length_digits}"

            output_path = f"{dir_path}{file_name}"

            # Replace variables
            if is_override:
                output_path = replace_variables(output_path)

        except Exception as exc:
            log.error("Failed to resolve output path: %s", exc)
            if is_override:
                return ""
            raise

        # Required side-effect for history
        output_path = str(output_path)
        settings.render_output_folder_path = output_path

        return output_path

    def _get_frame_settings(self, prefs, settings, scene, is_animation, ext_info: dict) -> Tuple[int, int, int]:
        """
        Retrieves valid frame range parameters (start, end, step) based on the
        current launch mode and availability of external scene metadata.
        """
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

            if settings.use_external_blend:
                if is_animation:
                    return check(
                        prefs,
                        ext_info.get("frame_start", 1),
                        ext_info.get("frame_end", 250),
                        ext_info.get("frame_step", 1),
                    )
                val = ext_info.get("frame_current", 1)
                return (val, val, 1)

            if is_animation:
                return check(prefs, scene.frame_start, scene.frame_end, scene.frame_step)
            return (scene.frame_current,) * 2 + (1,)

        except Exception as exc:
            raise ValueError(f"Invalid frame range: {exc}") from exc


classes = (RECOM_OT_ExportRenderScript,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
