# Prevent System Sleep
import subprocess
import atexit
import sys
import os

sleep_blocker_process = None


def prevent_sleep():
    global sleep_blocker_process

    # Windows sleep prevention
    if sys.platform == "win32":
        import ctypes

        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        flags = (
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            if prevent_monitor_off
            else ES_CONTINUOUS | ES_SYSTEM_REQUIRED
        )
        ctypes.windll.kernel32.SetThreadExecutionState(flags)
        print("Windows sleep/hibernation disabled.")

    # macOS sleep prevention
    elif sys.platform == "darwin":
        sleep_blocker_process = subprocess.Popen(["caffeinate"])
        print("macOS caffeinate process started.")

    # Linux sleep prevention
    elif sys.platform.startswith("linux"):
        try:
            sleep_blocker_process = subprocess.Popen(
                [
                    "systemd-inhibit",
                    "--why=Blender Render",
                    "bash",
                    "-c",
                    "while true; do sleep 3600; done",
                ]
            )
            print("Linux sleep inhibited via systemd-inhibit.")
        except FileNotFoundError:
            print("Systemd-inhibit not found. No sleep prevention.")


def restore_sleep():
    global sleep_blocker_process
    if sys.platform == "win32":
        import ctypes

        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        print("Windows sleep/hibernation restored.")
    else:
        if sleep_blocker_process is not None:
            sleep_blocker_process.terminate()
            print(f"Sleep prevention process terminated.")


atexit.register(restore_sleep)
prevent_sleep()
