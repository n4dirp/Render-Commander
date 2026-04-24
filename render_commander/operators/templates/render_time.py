"""Render Time Logic for Sequence Renders"""

import time
from bpy.app.handlers import persistent


def format_duration(seconds):
    """Convert seconds into a human-readable time string (e.g., 2h 15m 30s)."""
    seconds = round(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes}m {remaining_seconds}s"
    if minutes:
        return f"{minutes}m {remaining_seconds}s"
    return f"{remaining_seconds}s"


@persistent
def on_render_init(scene):
    """Initialize render tracking variables when a render starts."""
    scene["recom_render_start_time"] = time.time()
    scene["recom_render_frames_completed"] = 0


@persistent
def on_render_post(scene):
    """Update and display progress after each frame is rendered."""
    frames_completed = scene.get("recom_render_frames_completed", 0) + 1
    scene["recom_render_frames_completed"] = frames_completed

    render_start_time = scene.get("recom_render_start_time")
    try:
        frame_step = scene.frame_step or 1
        total_frames = int((scene.frame_end - scene.frame_start) / frame_step) + 1
        progress_percentage = min(frames_completed / total_frames, 1.0) if total_frames else 0

        progress_indicator = "#" * int(32 * progress_percentage) + "-" * (32 - int(32 * progress_percentage))
        estimated_time_remaining = None

        if render_start_time and 0 < frames_completed < total_frames:
            estimated_time_remaining = format_duration(
                (time.time() - render_start_time) / frames_completed * (total_frames - frames_completed)
            )

        status_message = f"Progress: [{progress_indicator}] {int(progress_percentage*100)}% | Frame {frames_completed}/{total_frames}"
        if estimated_time_remaining:
            status_message += f" | ETA: {estimated_time_remaining}"

        print(status_message)
    except Exception as e:
        print(f"Progress bar calculation error: {e}")


@persistent
def on_render_complete(scene):
    """Log total render time and clean up tracking variables when the render finishes."""
    render_start_time = scene.get("recom_render_start_time")
    frames_completed = scene.get("recom_render_frames_completed", 0)

    if render_start_time is not None:
        total_elapsed_time = time.time() - render_start_time
        print(f"Total Render Time: {format_duration(total_elapsed_time)} ({total_elapsed_time:.2f}s)")

        if frames_completed > 0:
            print(f"Frames: {frames_completed} | Avg: {total_elapsed_time/frames_completed:.2f}s")

        # Clean up scene properties
        scene.pop("recom_render_start_time", None)
        scene.pop("recom_render_frames_completed", None)


# Register handlers
bpy.app.handlers.render_init.append(on_render_init)
bpy.app.handlers.render_post.append(on_render_post)
bpy.app.handlers.render_complete.append(on_render_complete)
