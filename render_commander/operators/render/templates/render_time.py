"""Track Blender animation render time with progress bar."""

import time
import datetime
from bpy.app.handlers import persistent


@persistent
def on_render_init(scene):
    """Initialize render timer at start of rendering."""
    scene["_recom_render_start_time"] = time.time()
    scene["_recom_render_timer_frame_count"] = 0


@persistent
def on_render_post(scene):
    """Update progress bar during rendering."""
    current_count = scene.get("_recom_render_timer_frame_count", 0) + 1
    scene["_recom_render_timer_frame_count"] = current_count

    try:
        start = scene.frame_start
        end = scene.frame_end
        step = scene.frame_step
        if step == 0:
            step = 1

        total_frames = int((end - start) / step) + 1
        percent = current_count / total_frames if total_frames > 0 else 0
        percent = min(1.0, percent)

        bar_length = 60
        filled_length = int(bar_length * percent)
        bar = "=" * filled_length + "-" * (bar_length - filled_length)

        print(f"Progress: [{bar}] {percent*100:.1f}% | Frame {current_count}/{total_frames}")
    except Exception as exc:
        print(f"Progress bar error: {exc}")


@persistent
def on_render_complete(scene):
    """Finalize render time tracking and output stats."""
    start_time = bpy.context.scene.get("_recom_render_start_time")
    frame_count = scene.get("_recom_render_timer_frame_count")
    if start_time is not None:
        elapsed_seconds = time.time() - start_time
        total_seconds = round(elapsed_seconds)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        formatted_total_time = (
            f"{hours}h {minutes}m {seconds}s"
            if hours > 0
            else f"{minutes}m {seconds}s"
            if minutes > 0
            else f"{seconds}s"
        )

        print(f"Total Render Time: {formatted_total_time} ({elapsed_seconds:.2f} seconds)")
        if frame_count is not None and frame_count > 0:
            avg_time_per_frame = elapsed_seconds / frame_count
            print(f"Frames Rendered: {frame_count}")
            print(f"Average Time per Frame: {avg_time_per_frame:.2f} seconds")

        del scene["_recom_render_start_time"]
        del scene["_recom_render_timer_frame_count"]


bpy.app.handlers.render_init.append(on_render_init)
bpy.app.handlers.render_post.append(on_render_post)
bpy.app.handlers.render_complete.append(on_render_complete)
