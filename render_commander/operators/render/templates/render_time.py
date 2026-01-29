# Render Time Logic

import time
import datetime
from bpy.app.handlers import persistent


def format_duration(seconds_input):
    """Helper to format seconds into readable string."""
    total_seconds = round(seconds_input)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


@persistent
def on_render_init(scene):
    """Initialize render timer at start of rendering."""
    scene["_recom_render_start_time"] = time.time()
    scene["_recom_render_timer_frame_count"] = 0


@persistent
def on_render_post(scene):
    """Update progress bar and estimated remaining time during rendering."""
    current_count = scene.get("_recom_render_timer_frame_count", 0) + 1
    scene["_recom_render_timer_frame_count"] = current_count

    start_time = scene.get("_recom_render_start_time")

    try:
        start = scene.frame_start
        end = scene.frame_end
        step = scene.frame_step
        if step == 0:
            step = 1

        total_frames = int((end - start) / step) + 1
        percent = current_count / total_frames if total_frames > 0 else 0
        percent = min(1.0, percent)

        # Progress Bar
        bar_length = 64
        fill_char = "#"
        empty_char = "-"

        filled_length = int(bar_length * percent)
        bar = fill_char * filled_length + empty_char * (bar_length - filled_length)

        # ETA Calculation
        eta_str = "--:--"
        if start_time is not None and current_count > 0:
            elapsed = time.time() - start_time
            avg_per_frame = elapsed / current_count
            remaining_frames = total_frames - current_count
            remaining_seconds = remaining_frames * avg_per_frame
            eta_str = format_duration(remaining_seconds)

        print(f"Progress: [{bar}] {percent*100:.1f}% | Frame {current_count}/{total_frames} | ETA: {eta_str}")

    except Exception as exc:
        print(f"Progress bar error: {exc}")


@persistent
def on_render_complete(scene):
    """Finalize render time tracking and output stats."""
    start_time = scene.get("_recom_render_start_time")
    frame_count = scene.get("_recom_render_timer_frame_count")

    if start_time is not None:
        elapsed_seconds = time.time() - start_time
        formatted_total_time = format_duration(elapsed_seconds)

        print(f"Total Render Time: {formatted_total_time} ({elapsed_seconds:.2f} seconds)")
        if frame_count is not None and frame_count > 0:
            avg_time_per_frame = elapsed_seconds / frame_count
            print(f"Frames Rendered: {frame_count}")
            print(f"Average Time per Frame: {avg_time_per_frame:.2f} seconds")

        # Cleanup keys
        if "_recom_render_start_time" in scene:
            del scene["_recom_render_start_time"]
        if "_recom_render_timer_frame_count" in scene:
            del scene["_recom_render_timer_frame_count"]


# Register Timer Handlers
bpy.app.handlers.render_init.append(on_render_init)
bpy.app.handlers.render_post.append(on_render_post)
bpy.app.handlers.render_complete.append(on_render_complete)
