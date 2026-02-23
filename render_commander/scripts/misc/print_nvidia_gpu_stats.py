"""
GPU Stats Reporter – Per-Frame Handler

Run with Blender's -P option:
    blender.exe -b scene.blend -P nvidia_gpu_stats.py [other options]

This script registers a handler that prints NVIDIA GPU usage 
automatically after every single frame is rendered.

Updates:
- Filters output to only show devices enabled in Cycles preferences (CUDA/OPTIX).
- Matches devices using PCI Bus ID.
"""

import sys
import subprocess
import bpy
import re

# Global flag to stop trying if nvidia-smi is missing, preventing log spam.
NVIDIA_SMI_AVAILABLE = True


def _get_cycles_enabled_pci_ids():
    """
    Returns a set of normalized PCI bus IDs (e.g., '0000:0a:00')
    for devices enabled in Cycles preferences.
    Returns None if not filtering (e.g. engine is not Cycles).
    """
    # Only filter if we are using Cycles
    if bpy.context.scene.render.engine != "CYCLES":
        return None

    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
    except (KeyError, AttributeError):
        return None

    enabled_ids = set()

    # We only care about hardware devices (CUDA/OPTIX)
    # The device.id format is typically: "CUDA_DeviceName_0000:0a:00_OptiX"
    # We need to extract the "0000:0a:00" segment to match nvidia-smi.
    pci_pattern = re.compile(r"([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})")

    for device in preferences.devices:
        if device.use and device.type in {"CUDA", "OPTIX"}:
            match = pci_pattern.search(device.id)
            if match:
                # Store as lowercase for consistent comparison
                enabled_ids.add(match.group(1).lower())

    return enabled_ids


def _query_gpu_stats():
    """
    Execute `nvidia-smi` and return a list of dicts.
    Returns None if nvidia-smi fails or is unavailable.
    """
    global NVIDIA_SMI_AVAILABLE
    if not NVIDIA_SMI_AVAILABLE:
        return []

    # Query specific fields for compact logging
    query = (
        "index,pci.bus_id,name,"
        "utilization.gpu,utilization.memory,"
        "memory.total,memory.used,"
        "temperature.gpu,power.draw,power.limit"
    )

    cmd = [
        "nvidia-smi",
        f"--query-gpu={query}",
        "--format=csv,noheader,nounits",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("[GPU Stats] Error: 'nvidia-smi' not found or failed. Disabling stats.", file=sys.stderr)
        NVIDIA_SMI_AVAILABLE = False
        return []

    rows = []
    for line in result.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]

        if len(parts) != 10:
            continue

        (idx, pci_bus_id, name, gpu_util, mem_util, mem_total, mem_used, temp, p_draw, p_limit) = parts

        rows.append(
            {
                "index": idx,
                "pci_bus_id": pci_bus_id,
                "name": name,
                "gpu_util": gpu_util,  # %
                "mem_util": mem_util,  # %
                "mem_total": mem_total,  # MiB
                "mem_used": mem_used,  # MiB
                "temperature": temp,  # C
                "p_draw": p_draw,  # W
                "p_limit": p_limit,  # W
            }
        )
    return rows


def _log_frame_stats(scene):
    """
    Callback function that runs after a frame finishes.
    """
    rows = _query_gpu_stats()
    if not rows:
        return

    # Get list of allowed PCI IDs if in Cycles
    allowed_pci_ids = _get_cycles_enabled_pci_ids()

    frame = scene.frame_current

    for gpu in rows:
        # Filter Logic
        if allowed_pci_ids is not None:
            # Nvidia-smi format: "00000000:0A:00.0"
            # Blender format: "0000:0a:00"

            # Normalize Nvidia ID to match Blender format
            # 1. Lowercase
            # 2. Remove '0000' prefix from domain (00000000 -> 0000)
            # 3. Remove '.0' suffix
            raw_id = gpu["pci_bus_id"].lower()
            normalized_id = raw_id.replace("00000000:", "0000:", 1).split(".")[0]

            if normalized_id not in allowed_pci_ids:
                continue

        try:
            # Calculate memory percentage for display
            mem_used_int = int(gpu["mem_used"])
            mem_total_int = int(gpu["mem_total"])
            mem_pct = (mem_used_int / mem_total_int) * 100 if mem_total_int > 0 else 0
        except ValueError:
            mem_pct = 0

        log_line = (
            f"[GPU {gpu['index']}] {gpu['name']} | "
            f"Bus-Id: {gpu['pci_bus_id']} | "
            f"Util: {gpu['gpu_util']}% | "
            f"Mem: {gpu['mem_used']}/{gpu['mem_total']} MiB ({int(mem_pct)}%) | "
            f"Temp: {gpu['temperature']}°C | "
            f"Pwr: {float(gpu['p_draw']):.1f}W"
        )

        print(log_line, flush=True)


def register():
    """Register the handler."""
    if _log_frame_stats in bpy.app.handlers.render_post:
        bpy.app.handlers.render_post.remove(_log_frame_stats)

    bpy.app.handlers.render_post.append(_log_frame_stats)
    print("[GPU Stats] Handler registered for per-frame reporting.")


def unregister():
    """Unregister the handler."""
    if _log_frame_stats in bpy.app.handlers.render_post:
        bpy.app.handlers.render_post.remove(_log_frame_stats)


if __name__ == "__main__":
    register()
