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
    # High Performance plan GUID
    HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    # Or Ultimate Performance:
    # HIGH_PERF_GUID = "e9a42b02-d5df-448d-aa00-03f14749eb61"

    set_power_plan(HIGH_PERF_GUID)
