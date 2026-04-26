"""Render Time Logic for Sequence Renders"""

from bpy.app.handlers import persistent


def format_duration(seconds):
    """Convert seconds into a human-readable time string."""
    seconds = round(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)

    if hours:
        return "%dh %dm %ds" % (hours, minutes, remaining_seconds)
    if minutes:
        return "%dm %ds" % (minutes, remaining_seconds)
    return "%ds" % remaining_seconds


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

    frame_step = scene.frame_step if scene.frame_step else 1
    total_frames = int((scene.frame_end - scene.frame_start) / frame_step) + 1

    if total_frames <= 0:
        return

    progress_percentage = min(frames_completed / total_frames, 1.0)
    bar_size = 32
    filled_len = int(bar_size * progress_percentage)
    progress_indicator = "#" * filled_len + "-" * (bar_size - filled_len)

    estimated_time_remaining = None
    if render_start_time and 0 < frames_completed < total_frames:
        elapsed = time.time() - render_start_time
        eta_seconds = (elapsed / frames_completed) * (total_frames - frames_completed)
        estimated_time_remaining = format_duration(eta_seconds)

    status_message = "Progress: [%s] %d%% | Frame %d/%d" % (
        progress_indicator,
        int(progress_percentage * 100),
        frames_completed,
        total_frames,
    )

    if estimated_time_remaining:
        status_message += " | ETA: %s" % estimated_time_remaining

    log.info("%s", status_message)


@persistent
def on_render_complete(scene):
    """Log total render time and clean up tracking variables."""
    render_start_time = scene.get("recom_render_start_time")
    frames_completed = scene.get("recom_render_frames_completed", 0)

    if render_start_time is not None:
        total_elapsed_time = time.time() - render_start_time
        hours, remainder = divmod(total_elapsed_time, 3600)
        minutes, seconds = divmod(remainder, 60)

        log.info("Render completed in %02d:%02d:%05.2f", int(hours), int(minutes), seconds)

        if frames_completed > 0:
            log.info("Frames: %d | Avg: %.2fs", frames_completed, total_elapsed_time / frames_completed)

        # Clean up scene properties
        scene.pop("recom_render_start_time", None)
        scene.pop("recom_render_frames_completed", None)


# Register handlers
bpy.app.handlers.render_init.append(on_render_init)
bpy.app.handlers.render_post.append(on_render_post)
bpy.app.handlers.render_complete.append(on_render_complete)
