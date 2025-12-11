# Track Render Time
import time
import datetime
from bpy.app.handlers import persistent


@persistent
def on_render_init(scene):
    scene["_recom_render_start_time"] = time.time()
    scene["_recom_render_timer_frame_count"] = 0


@persistent
def on_render_post(scene):
    scene["_recom_render_timer_frame_count"] = scene.get("_recom_render_timer_frame_count", 0) + 1


@persistent
def on_render_complete(scene):
    start_time = bpy.context.scene.get("_recom_render_start_time")
    frame_count = scene.get("_recom_render_timer_frame_count")
    if start_time is not None:
        elapsed_seconds = time.time() - start_time
        total_seconds = round(elapsed_seconds)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            formatted_total_time = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            formatted_total_time = f"{minutes}m {seconds}s"
        else:
            formatted_total_time = f"{seconds}s"

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
