"""
GPU Stats Reporter – Per-Frame Handler

Run with Blender's -P option:
    blender.exe -b scene.blend -P nvidia_gpu_stats.py [other options]

This script registers a handler that prints NVIDIA GPU usage 
automatically after every single frame is rendered.
"""

import sys
import subprocess
import bpy

# Global flag to stop trying if nvidia-smi is missing, preventing log spam.
NVIDIA_SMI_AVAILABLE = True


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

    frame = scene.frame_current

    for gpu in rows:
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
