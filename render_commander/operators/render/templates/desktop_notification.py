# Notification Logic

import subprocess
import atexit
import sys
import ctypes
from pathlib import Path


_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")

# Variables
NOTIFICATION_DETAIL_LEVEL = "DETAILED"
NOTIFICATION_TIMEOUT = 10


def show_windows_alert(title, message):
    """Open a pop-up alert box with a timeout"""
    print(f"Sending notification via Windows MessageBox (timeout: {NOTIFICATION_TIMEOUT}s)...")
    timeout_ms = NOTIFICATION_TIMEOUT * 1000

    try:
        # MessageBoxTimeoutW arguments: hWnd, lpText, lpCaption, uType, wLanguageId, dwMilliseconds
        ctypes.windll.user32.MessageBoxTimeoutW(0, str(message), str(title), 0x40, 0, timeout_ms)
    except AttributeError:
        print("MessageBoxTimeoutW not available. Falling back to blocking MessageBoxW...")
        try:
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title), 0x40)
        except Exception as e:
            print(f"Windows MessageBox fallback failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Windows Notification Error: {e}", file=sys.stderr)


def send_macos_notification(title, message):
    """Sends a notification on macOS using osascript."""
    try:
        print("Sending notification via osascript...")
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
            check=True,
            timeout=NOTIFICATION_TIMEOUT,
        )
    except Exception as e:
        print(f"macOS Notification Error: {e}")


def send_linux_notification(title, message):
    """Sends a notification on Linux using notify-send."""

    try:
        # Blender executable path
        blender_exe = bpy.app.binary_path
        blender_dir = Path(blender_exe).parent

        # Try common icon names
        icon_candidates = ["blender.svg", "blender.png", "blender.ico"]
        icon_path = None
        for candidate in icon_candidates:
            candidate_path = blender_dir / candidate
            if candidate_path.exists():
                icon_path = str(candidate_path)
                break

        # Fallback if not found
        if not icon_path:
            icon_path = "dialog-information"

        print("Sending notification via notify-send...")
        subprocess.run(
            ["notify-send", "-i", icon_path, "-a", "Blender", title, message],
            check=True,
            timeout=NOTIFICATION_TIMEOUT,
        )
    except Exception as e:
        print(f"Linux Notification Error: {e}")


def send_desktop_notification(title, message, output_path, preview_image_path=None):
    """
    Sends a desktop notification by choosing the best available method for the current OS.
    """
    output_dir_path = Path(output_path) if output_path else None

    if _IS_WINDOWS:
        show_windows_alert(title, message)
    elif _IS_MACOS:
        send_macos_notification(title, message)
    elif _IS_LINUX:
        send_linux_notification(title, message)
    else:
        print(f"Desktop notifications not supported on this platform: {sys.platform}")


output_path = Path(bpy.path.abspath(bpy.context.scene.render.filepath))
folder_path = output_path if output_path.is_dir() else output_path.parent


def _build_notification_message(max_len: int = 50) -> str:
    """Return a string with key render details."""

    # Simple Level
    if NOTIFICATION_DETAIL_LEVEL == "SIMPLE":
        return "Render finished successfully."

    def truncate_middle(s: str, max_length: int) -> str:
        if len(s) <= max_length:
            return s
        # Ensure we leave room for '...'
        if max_length < 4:
            return s[:max_length]  # fallback for tiny limits
        half = (max_length - 3) // 2
        return s[:half] + "..." + s[-(max_length - half - 3) :]

    blend_name = Path(bpy.data.filepath).name
    scene = bpy.context.scene
    render = scene.render

    # Compute final resolution considering resolution percentage
    pct = render.resolution_percentage / 100.0
    final_x = int(render.resolution_x * pct)
    final_y = int(render.resolution_y * pct)
    resolution_info = f"{final_x} x {final_y} px"

    #  Detailed Level
    file_format = scene.render.image_settings.file_format
    line1 = truncate_middle(f"Blend: {blend_name}", max_len)
    line2 = truncate_middle(f"Format: {file_format} | {resolution_info}", max_len)
    line3 = truncate_middle(f"Output: {output_path}", max_len)

    return f"{line1}\n{line2}\n{line3}"


notification_title = "Blender" if NOTIFICATION_DETAIL_LEVEL == "SIMPLE" else "Blender - Render Finished"
notification_message = _build_notification_message()

# Register the notification function to be called on exit.
atexit.register(
    send_desktop_notification,
    notification_title,
    notification_message,
    folder_path,
)
