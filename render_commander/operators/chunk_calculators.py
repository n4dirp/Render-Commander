"""Chunk calculation logic for distributing render work across processes/devices."""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Union

from ..utils.constants import MODE_LIST, MODE_SEQ, MODE_SINGLE
from ..utils.cycles_devices import get_cpu_device

log = logging.getLogger(__name__)

MAX_FRAME_RANGE = 100000


def parse_frame_string(frame_str: str) -> List[int]:
    """Parse a frame range string into a sorted list of integers."""
    import re

    frames = set()
    tokens = re.findall(r"\d+(?:-\d+)?", frame_str)
    for token in tokens:
        if "-" in token:
            start, end = sorted(map(int, token.split("-")))
            if end - start > MAX_FRAME_RANGE:
                log.warning("Frame range %s-%s exceeds limit, capping at %s", start, end, MAX_FRAME_RANGE)
                end = start + MAX_FRAME_RANGE
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


@dataclass
class RenderJobChunk:
    """Helper data structure to define a single render process."""

    process_index: int
    device_ids: List[str]
    frames: Union[Tuple[int, int, int], List[int]]
    is_animation_call: bool
    description: str


def calculate_chunks_single_process(prefs, settings, scene, selected_ids, ext_info) -> List[RenderJobChunk]:
    """Create a single job chunk for standard execution."""
    if prefs.launch_mode == MODE_LIST:
        frames = parse_frame_string(settings.frame_list)
        is_animation = False
        desc_frames = format_frame_range(frames)
    else:
        is_not_still = prefs.launch_mode != MODE_SINGLE

        frame_start, frame_end, frame_step = _get_frame_settings(prefs, settings, scene, is_not_still, ext_info)

        frames = (frame_start, frame_end, frame_step)
        is_animation = prefs.launch_mode == MODE_SEQ
        desc_frames = f"{frame_start}" if frame_start == frame_end else f"{frame_start}-{frame_end}"

    return [
        RenderJobChunk(
            process_index=0,
            device_ids=selected_ids,
            frames=frames,
            is_animation_call=is_animation,
            description=f"Mode: {prefs.launch_mode} | Frame: {desc_frames}",
        )
    ]


def calculate_chunks_sequence_parallel(prefs, settings, scene, selected_devices, ext_info) -> List[RenderJobChunk]:
    """Split a frame sequence across available devices."""
    frame_start, frame_end, frame_step = _get_frame_settings(prefs, settings, scene, True, ext_info)
    total_frames = (frame_end - frame_start) // frame_step + 1
    num_devices = min(len(selected_devices), total_frames)

    if num_devices <= 0:
        log.error("No valid frames to render")
        return []

    chunks = []
    current_start = frame_start

    frames_per_device = total_frames // num_devices
    remainder = total_frames % num_devices

    if prefs.frame_allocation != "FRAME_SPLIT":
        frames_per_device = 0

    for i in range(num_devices):
        device = selected_devices[i]
        device_ids = _get_combined_device_ids(prefs, device)

        if prefs.frame_allocation == "FRAME_SPLIT":
            count = frames_per_device + (1 if i < remainder else 0)
            current_end = current_start + (count - 1) * frame_step
            chunk_frames = (current_start, current_end, frame_step)
            desc = f"Worker[#{i}] | Split: [{current_start}-{current_end}]"
            current_start = current_end + frame_step
        else:
            chunk_frames = (frame_start, frame_end, frame_step)
            desc = f"Worker[#{i}] | FullRange: [{frame_start}-{frame_end}]"

        chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

    return chunks


def calculate_chunks_list_parallel(prefs, settings, selected_devices) -> List[RenderJobChunk]:
    """Split a list of frames across available devices."""
    frames = parse_frame_string(settings.frame_list)
    if not frames:
        log.error("No valid frames specified.")
        return []

    total_frames = len(frames)
    num_devices = min(len(selected_devices), total_frames)

    chunks = []
    frames_per_device = total_frames // num_devices
    remainder = total_frames % num_devices
    current_idx = 0

    for i in range(num_devices):
        device = selected_devices[i]
        device_ids = _get_combined_device_ids(prefs, device)

        end_idx = current_idx + frames_per_device + (1 if i < remainder else 0)
        subset = frames[current_idx:end_idx]
        current_idx = end_idx

        if subset:
            desc = f"Worker[#{i}] | Frame: {format_frame_range(subset)}"
            chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

    return chunks


def calculate_chunks_iterations_parallel(
    prefs, settings, scene, process_count: int, ext_info: dict
) -> List[RenderJobChunk]:
    """Split a frame sequence across multiple Blender instances without assigning specific hardware device IDs."""
    frame_start, frame_end, frame_step = _get_frame_settings(prefs, settings, scene, True, ext_info)
    total_frames = (frame_end - frame_start) // frame_step + 1
    actual_process_count = min(process_count, total_frames)

    if actual_process_count <= 0:
        log.error("No valid frames to render")
        return []

    chunks = []
    current_start = frame_start
    frames_per_process = total_frames // actual_process_count
    remainder = total_frames % actual_process_count

    if prefs.frame_allocation != "FRAME_SPLIT":
        frames_per_process = 0

    for i in range(actual_process_count):
        device_ids = []

        if prefs.frame_allocation == "FRAME_SPLIT":
            count = frames_per_process + (1 if i < remainder else 0)
            current_end = current_start + (count - 1) * frame_step
            chunk_frames = (current_start, current_end, frame_step)
            desc = f"Worker[#{i}] | Split:[{current_start}-{current_end}]"
            chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))
            current_start = current_end + frame_step
        else:
            chunk_frames = (frame_start, frame_end, frame_step)
            desc = f"Worker[#{i}] | FullRange:[{frame_start}-{frame_end}]"
            chunks.append(RenderJobChunk(i, device_ids, chunk_frames, True, desc))

    return chunks


def calculate_chunks_list_iterations(settings, process_count: int) -> List[RenderJobChunk]:
    """Split a frame list across multiple processes (Iterations)."""
    frames = parse_frame_string(settings.frame_list)
    if not frames:
        log.error("No valid frames specified.")
        return []

    total_frames = len(frames)
    actual_process_count = min(process_count, total_frames)

    if actual_process_count < 1:
        return []

    chunks = []
    frames_per_process = total_frames // actual_process_count
    remainder = total_frames % actual_process_count
    current_idx = 0

    for i in range(actual_process_count):
        device_ids = []
        count = frames_per_process + (1 if i < remainder else 0)
        end_idx = current_idx + count
        subset = frames[current_idx:end_idx]
        current_idx = end_idx

        if subset:
            desc = f"Worker[#{i}] | Frame: {format_frame_range(subset)}"
            chunks.append(RenderJobChunk(i, device_ids, subset, False, desc))

    return chunks


def _get_frame_settings(prefs, settings, scene, is_animation, ext_info):
    """Retrieve valid frame range parameters based on launch mode and scene data."""

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


def _get_combined_device_ids(prefs, primary_device):
    """Combine CPU with GPU if preference is set."""
    if prefs.combine_cpu_with_gpus:
        cpu_device = get_cpu_device(prefs)
        if cpu_device:
            return [primary_device.id, cpu_device.id]
    return [primary_device.id]
