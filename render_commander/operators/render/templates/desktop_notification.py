# Desktop Notification
import subprocess
import atexit
import sys
import os
import threading
from pathlib import Path
import importlib.util


_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")
_WIN11TOAST_AVAILABLE = _IS_WINDOWS and importlib.util.find_spec("win11toast") is not None


def _send_win11toast_notification(title, message, output_dir_path, preview_path):
    """Sends a rich notification on Windows using the win11toast library."""
    try:
        from contextlib import contextmanager
        from win11toast import toast

        @contextmanager
        def suppress_stdout_stderr():
            """Redirect stdout/stderr to devnull to prevent toast console output."""
            with open(os.devnull, "w") as fnull:
                old_stdout, old_stderr = sys.stdout, sys.stderr
                sys.stdout, sys.stderr = fnull, fnull
                try:
                    yield
                finally:
                    sys.stdout, sys.stderr = old_stdout, old_stderr

        buttons = []
        if preview_path and preview_path.is_file():
            buttons.append(
                {
                    "activationType": "protocol",
                    "arguments": str(preview_path.resolve()),
                    "content": "Open Image",
                }
            )
        else:
            print(f"Toast: No valid preview image at: {preview_path}")

        if output_dir_path and output_dir_path.is_dir():
            buttons.append(
                {
                    "activationType": "protocol",
                    "arguments": str(output_dir_path.resolve()),
                    "content": "Open Folder",
                }
            )
        else:
            print(f"Toast: No valid output folder at: {output_dir_path}")

        def run_toast():
            try:
                print("Toast: Showing Windows toast notification...")
                image_arg = (
                    str(preview_path.resolve()) if preview_path and preview_path.is_file() else None
                )
                with suppress_stdout_stderr():
                    toast(
                        title,
                        message,
                        image=image_arg,
                        buttons=buttons if buttons else None,
                    )
            except Exception as e:
                print(f"Toast: An error occurred inside the notification thread: {e}")

        # Launch toast in a thread with a timeout to prevent blocking.
        t = threading.Thread(target=run_toast, daemon=True)
        t.start()
        t.join(timeout=15)
        if t.is_alive():
            print("Toast: Toast did not close within 15s, terminating thread reference.")

    except Exception as e:
        print(f"Failed to initialize or send win11toast notification: {e}")


def _send_powershell_notification(title, message):
    """Sends a fallback notification on Windows using PowerShell."""
    try:

        def sanitize_for_powershell(text):
            return text.replace("`", "``").replace('"', '`"').replace("$", "`$").replace("\n", "`n")

        ps_title = sanitize_for_powershell(title)
        ps_message = sanitize_for_powershell(message)

        ps_command = f"""
        [void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');
        $notifyIcon = New-Object System.Windows.Forms.NotifyIcon;
        $notifyIcon.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -Id $pid).Path);
        $notifyIcon.BalloonTipTitle = "{ps_title}";
        $notifyIcon.BalloonTipText = "{ps_message}";
        $notifyIcon.Visible = $true;
        $notifyIcon.ShowBalloonTip(10000);
        Start-Sleep -Seconds 15;
        $notifyIcon.Dispose();
        """
        # The 0x08000000 creation flag (CREATE_NO_WINDOW) prevents a PowerShell window from appearing.
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            check=True,
            capture_output=True,
            text=True,
            creationflags=0x08000000,
            timeout=20,  # Safety timeout
        )
    except subprocess.CalledProcessError as e:
        print(f"PowerShell - Command failed: {e.args}")
        print(f"PowerShell - Stdout: {e.stdout}")
        print(f"PowerShell - Stderr: {e.stderr}")
    except subprocess.TimeoutExpired:
        print("PowerShell - Notification process exceeded timeout (20s).")
    except Exception as e:
        print(f"An unexpected error occurred while sending PowerShell notification: {e}")


def _send_macos_notification(title, message):
    """Sends a notification on macOS using osascript."""
    try:
        print("Sending macOS notification via osascript...")
        subprocess.run(
            ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
            check=True,
            timeout=10,
        )
    except Exception as e:
        print(f"macOS Notification Error: {e}")


def _send_linux_notification(title, message):
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

        print("Sending Linux notification via notify-send...")
        subprocess.run(
            ["notify-send", "-i", icon_path, "-a", "Blender", title, message],
            check=True,
            timeout=10,
        )
    except Exception as e:
        print(f"Linux Notification Error: {e}")


def send_desktop_notification(title, message, output_path, preview_image_path=None):
    """
    Sends a desktop notification by choosing the best available method for the current OS.
    """
    preview_path = Path(preview_image_path) if preview_image_path else None
    output_dir_path = Path(output_path) if output_path else None

    if _IS_WINDOWS:
        if _WIN11TOAST_AVAILABLE:
            _send_win11toast_notification(title, message, output_dir_path, preview_path)
        else:
            print("win11toast not found. Falling back to PowerShell notification.")
            _send_powershell_notification(title, message)
    elif _IS_MACOS:
        _send_macos_notification(title, message)
    elif _IS_LINUX:
        _send_linux_notification(title, message)
    else:
        print(f"Desktop notifications not supported on this platform: {sys.platform}")


output_path = Path(bpy.path.abspath(bpy.context.scene.render.filepath))
folder_path = output_path if output_path.is_dir() else output_path.parent


def _build_notification_message(max_len: int = 50) -> str:
    """Return a string with key render details."""

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

    file_format = scene.render.image_settings.file_format

    # Build the 3 lines
    line1 = truncate_middle(f"Blend: {blend_name}", max_len)
    line2 = truncate_middle(f"Format: {file_format} | {resolution_info}", max_len)
    line3 = truncate_middle(f"Output: {output_path}", max_len)

    return f"{line1}\n{line2}\n{line3}"


def _get_output_image_path() -> Path:
    output_format = bpy.context.scene.render.image_settings.file_format
    EXTENSIONS = {
        "PNG": ".png",
        "OPEN_EXR": ".exr",
        "OPEN_EXR_MULTILAYER": ".exr",
        "JPEG": ".jpg",
        "BMP": ".bmp",
        "TGA": ".tga",
        "TIFF": ".tif",
        "HDR": ".hdr",
    }
    extension = EXTENSIONS.get(output_format, ".png")

    image_path: Path
    frame_length_digits = 4
    hash_string = "#" * frame_length_digits

    # Check if the path is a template for an animation frame sequence
    if str(output_path).endswith(hash_string):
        # Construct the specific path for the current frame
        base_path_str = str(output_path).removesuffix(hash_string)
        frame_number_str = str(bpy.context.scene.frame_current).zfill(frame_length_digits)
        image_path = Path(f"{base_path_str}{frame_number_str}{extension}")
    else:
        # This is a single image render; check if an extension is missing
        image_path = output_path
        known_extensions = set(EXTENSIONS.values())

        if image_path.suffix.lower() not in known_extensions:
            # Append the correct extension if it's not already part of the path
            image_path = Path(f"{str(image_path)}{extension}")

    return image_path


notification_title = f"Blender - Render Complete"
notification_message = _build_notification_message()
preview_image_path = _get_output_image_path()

# Register the notification function to be called on exit.
atexit.register(
    send_desktop_notification,
    notification_title,
    notification_message,
    folder_path,
    preview_image_path,
)
