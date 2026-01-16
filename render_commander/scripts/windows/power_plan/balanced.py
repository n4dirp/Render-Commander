import subprocess
import sys


def set_power_plan(guid):
    """Set Windows power plan by GUID."""
    if sys.platform != "win32":
        print("This script only works on Windows.")
        return False

    try:
        subprocess.run(["powercfg", "/setactive", guid], check=True, shell=True)
        print(f"Power plan set to GUID: {guid}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to change power plan: {e}")
        return False


if __name__ == "__main__":
    # Balanced plan GUID
    BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"

    set_power_plan(BALANCED_GUID)
