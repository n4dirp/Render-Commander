# ./preferences.py

import os
import sys
import platform
import logging
import subprocess
import shutil
import unicodedata
import re
from pathlib import Path

import bpy
import _cycles

from bpy.types import AddonPreferences, PropertyGroup, Panel, UIList
from bpy.props import (
    StringProperty,
    BoolProperty,
    CollectionProperty,
    IntProperty,
    PointerProperty,
    EnumProperty,
    FloatProperty,
)

from .utils.constants import *
from .utils.helpers import redraw_ui, sanitize_filename


log = logging.getLogger(__name__)


os.environ["TBB_MALLOC_DISABLE_REPLACEMENT"] = "1"

_IS_WINDOWS = sys.platform == "win32"
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")

PACKAGE = __package__

enum_device_type = (
    ("CPU", "CPU", "CPU", 0),
    ("CUDA", "CUDA", "CUDA", 1),
    ("OPTIX", "OptiX", "OptiX", 3),
    ("HIP", "HIP", "HIP", 4),
    ("METAL", "Metal", "Metal", 5),
    ("ONEAPI", "oneAPI", "oneAPI", 6),
)


class RECOM_PG_DeviceSettings(PropertyGroup):
    id: StringProperty(name="ID")
    name: StringProperty(name="Name")
    use: BoolProperty(name="Use", default=False)
    type: EnumProperty(name="Type", items=enum_device_type, default="CPU")


class RECOM_PG_RecentFile(PropertyGroup):
    path: StringProperty(name="Blend File Path")


class RECOM_PG_ScriptEntry(PropertyGroup):
    script_path: StringProperty(
        name="Script Path",
        description="Path to a Python script to append during rendering.",
        default="",
        subtype="FILE_PATH",
        update=lambda self, context: redraw_ui(),
    )
    order: EnumProperty(
        name="Execution Order",
        items=[
            ("PRE", "Pre-Render", "Run before render"),
            ("POST", "Post-Render", "Run after render"),
        ],
        default="PRE",
        update=lambda self, context: redraw_ui(),
    )


class RECOM_PG_CustomVariable(PropertyGroup):
    name: StringProperty(
        name="Name",
        description="Custom Variable Name.",
        update=lambda self, context: redraw_ui(),
    )
    token: StringProperty(
        name="Token",
        description="Placeholder that will be inserted into paths (e.g. CUSTOM_VAR).",
        update=lambda self, context: redraw_ui(),
    )
    value: StringProperty(
        name="Value",
        description="The string that replaces the token when rendering.",
        update=lambda self, context: redraw_ui(),
    )


class RECOM_PG_RenderHistoryItem(PropertyGroup):
    blend_path: StringProperty(name="Blend Path", default="")
    blend_dir: StringProperty(name="Blend Path", default="")
    blend_file_name: StringProperty(name="Blend Name", default="")
    render_id: StringProperty(name="Render ID", default="")
    date: StringProperty(name="Date", default="")
    render_engine: StringProperty(name="Engine", default="")
    launch_mode: StringProperty(name="Mode", default="")
    device_configuration: StringProperty(name="Devices Used", default="")
    frames: StringProperty(name="Frames", default="")
    resolution_x: IntProperty(name="Width", default=0)
    resolution_y: IntProperty(name="Height", default=0)
    samples: IntProperty(name="Samples", default=0)
    output_folder: StringProperty(name="Output Folder", default="")
    output_filename: StringProperty(name="Output Filename", default="")
    file_format: StringProperty(name="File Format", default="")


class RECOM_PG_VisiblePanels(PropertyGroup):
    external_scene: BoolProperty(
        name="Show External Scene",
        default=True,
        update=lambda self, context: redraw_ui(),
    )
    external_scene_details: BoolProperty(default=True, name="External Scene")

    override_settings: BoolProperty(
        name="Show Override Settings",
        default=True,
        update=lambda self, context: redraw_ui(),
    )
    frame_range: BoolProperty(default=True, name="Frame Range")
    resolution: BoolProperty(default=True, name="Resolution")
    overscan: BoolProperty(default=True, name="Overscan")
    camera_shift: BoolProperty(default=True, name="Camera Shift")
    motion_blur: BoolProperty(default=True, name="Motion Blur")
    output_path: BoolProperty(default=True, name="Output Path")
    file_format: BoolProperty(default=True, name="Output Format")
    compositor: BoolProperty(default=True, name="Compositor")
    compute_device: BoolProperty(default=True, name="Compute Device")
    samples: BoolProperty(default=True, name="Sampling")
    light_paths: BoolProperty(default=True, name="Light Paths")
    performance: BoolProperty(default=True, name="Performance")

    preferences: BoolProperty(
        name="Show Render Preferences",
        default=True,
        update=lambda self, context: redraw_ui(),
    )
    cycles_device_ids: BoolProperty(default=False, name="Device IDs")
    system_power: BoolProperty(default=True, name="System Power")
    ocio: BoolProperty(default=False, name="OCIO Environment")
    blender_executable: BoolProperty(default=True, name="Blender Executable")
    command_line_arguments: BoolProperty(default=False, name="Command Line Arguments")
    append_scripts: BoolProperty(default=True, name="Append Scripts")

    history: BoolProperty(
        name="Show Render History",
        default=True,
        update=lambda self, context: redraw_ui(),
    )
    render_details: BoolProperty(default=True, name="History Entry Info")


def get_addon_preferences(context):
    return context.preferences.addons[__package__].preferences


def get_prevent_sleep_description():
    if sys.platform == "win32":
        return (
            "Keep the computer awake while rendering.\n"
            "Uses Windows system flags to disable sleep and hibernation."
        )
    elif sys.platform == "darwin":
        return (
            "Keep the computer awake while rendering.\n"
            "Uses the 'caffeinate' utility to block sleep."
        )
    elif sys.platform.startswith("linux"):
        return (
            "Keep the computer awake while rendering.\n"
            "Uses 'systemd-inhibit' to prevent suspend."
        )
    else:
        return "Keep the computer awake while rendering."


class RECOM_Preferences(AddonPreferences):
    """Preferences for the addon settings"""

    bl_idname = __package__

    _device_types_cache = None

    @classmethod
    def get_device_types_cache(cls):
        if cls._device_types_cache is None:
            cls._device_types_cache = _cycles.get_device_types()
        return cls._device_types_cache

    def _update_compute_device_type(self, context):
        if self.compute_device_type != "NONE":
            self.get_device_list(self.compute_device_type)
        else:
            self.get_device_list("NONE")

    @staticmethod
    def default_device_type_val():
        import platform

        if (platform.system() == "Darwin") and (platform.machine() == "arm64"):
            return 5
        return 0

    def get_device_types_items(self, context):
        (
            has_cuda,
            has_optix,
            has_hip,
            has_metal,
            has_oneapi,
            _,
        ) = self.get_device_types_cache()
        items = [("NONE", "None", "Don't use compute device", 0)]
        if has_cuda:
            items.append(("CUDA", "CUDA", "Use CUDA for GPU acceleration", 1))
        if has_optix:
            items.append(("OPTIX", "OptiX", "Use OptiX for GPU acceleration", 3))
        if has_hip:
            items.append(("HIP", "HIP", "Use HIP for GPU acceleration", 4))
        if has_metal:
            items.append(("METAL", "Metal", "Use Metal for GPU acceleration", 5))
        if has_oneapi:
            items.append(("ONEAPI", "oneAPI", "Use oneAPI for GPU acceleration", 6))
        return items

    compute_device_type: EnumProperty(
        name="Backend",
        description="Device to use for computation",
        default=default_device_type_val(),
        items=get_device_types_items,
        update=_update_compute_device_type,
    )

    devices: CollectionProperty(type=RECOM_PG_DeviceSettings)

    def get_device_list(self, compute_device_type_str_enum_val):
        if compute_device_type_str_enum_val == "NONE":
            device_list = []
        else:
            device_list = _cycles.available_devices(compute_device_type_str_enum_val)

        device_list = []
        if compute_device_type_str_enum_val != "NONE":
            device_list = _cycles.available_devices(compute_device_type_str_enum_val)
            if compute_device_type_str_enum_val != "CPU":
                cpu_devices = _cycles.available_devices("CPU")
                existing_cpu_ids = {dev[2] for dev in device_list if dev[1] == "CPU"}
                for cpu_dev in cpu_devices:
                    if cpu_dev[2] not in existing_cpu_ids:
                        device_list.extend([cpu_dev])
        else:
            device_list = _cycles.available_devices("CPU")

        self.update_device_entries(device_list, compute_device_type_str_enum_val)
        return device_list

    def find_existing_device_entry(self, device_info_tuple):
        for device_entry in self.devices:
            if (
                device_entry.id == device_info_tuple[2]
                and device_entry.type == device_info_tuple[1]
            ):
                return device_entry
        return None

    def update_device_entries(self, device_list, current_compute_type_str):
        """
        Synchronizes the stored device list with the currently available devices.
        This function removes stale entries, adds new ones, and updates existing ones.
        """

        # Identify and remove stale devices
        # Get a set of persistent IDs for all currently available devices for quick lookups.
        # The device_info tuple from _cycles is (name, type, persistent_id, ...)
        fresh_device_ids = {dev[2] for dev in device_list}

        # Find the indices of stored devices that are no longer available.
        stale_device_indices = []
        for i, stored_device in enumerate(self.devices):
            # We only prune devices that belong to the currently selected backend (or CPU, which is always checked).
            # We check if a device of the current type or CPU is no longer in the fresh list.
            if stored_device.type == current_compute_type_str or (
                stored_device.type == "CPU" and current_compute_type_str != "NONE"
            ):
                if stored_device.id not in fresh_device_ids:
                    stale_device_indices.append(i)

        # Remove the stale devices by iterating backwards to avoid messing up indices.
        for i in sorted(stale_device_indices, reverse=True):
            self.devices.remove(i)

        # Add new devices and update existing ones
        for device_info in device_list:
            # device_info format: (name, type, id, has_peer_memory, has_rt, ...)
            # Ensure we only process valid device types.
            if device_info[1] not in {"CUDA", "OPTIX", "CPU", "HIP", "METAL", "ONEAPI"}:
                continue

            entry = self.find_existing_device_entry(device_info)

            # If the device is not in our list, add it.
            if not entry:
                entry = self.devices.add()
                entry.id = device_info[2]
                entry.name = device_info[0]
                entry.type = device_info[1]

                # Default 'use' state for newly added devices.
                # A non-CPU device should be enabled if it matches the selected backend.
                # A CPU device should be enabled if it's the only option or if no backend is selected.
                is_primary_device = entry.type == current_compute_type_str and entry.type != "CPU"
                is_cpu_fallback = entry.type == "CPU" and (
                    current_compute_type_str in {"CPU", "NONE"} or len(device_list) == 1
                )

                entry.use = is_primary_device or is_cpu_fallback

            # If the device exists, ensure its name is up-to-date (e.g., driver update changed it).
            elif entry.name != device_info[0]:
                entry.name = device_info[0]

    def get_devices_for_display(self):
        selected_compute_type = self.compute_device_type
        devices_to_display = []

        if self.multiple_backends and self.device_parallel and self.launch_mode != "SINGLE_FRAME":
            # Show all devices, regardless of backend
            for dev_entry in self.devices:
                devices_to_display.append(dev_entry)
        else:
            # Original logic: filter based on compute_device_type
            for dev_entry in self.devices:
                if dev_entry.type == selected_compute_type and dev_entry.type != "CPU":
                    devices_to_display.append(dev_entry)
            if selected_compute_type != "CPU":
                for dev_entry in self.devices:
                    if dev_entry.type == "CPU" and not any(
                        d.id == dev_entry.id for d in devices_to_display
                    ):
                        devices_to_display.append(dev_entry)
            else:
                for dev_entry in self.devices:
                    if dev_entry.type == "CPU":
                        devices_to_display.append(dev_entry)
        return devices_to_display

    @staticmethod
    def _normalize_device_name(name: str) -> str:
        return name.replace("(TM)", unicodedata.lookup("TRADE MARK SIGN")).replace(
            "(R)", unicodedata.lookup("REGISTERED SIGN")
        )

    def _draw_devices(self, layout, devices_to_draw):
        selected_compute_type = self.compute_device_type

        # Quick‑check for “no compatible devices” when we’re not in multi‑backend mode.
        has_primary_devices = any(
            d.type == selected_compute_type and d.type != "CPU" for d in devices_to_draw
        )
        if not self.multiple_backends:
            if not devices_to_draw or (
                selected_compute_type != "CPU"
                and selected_compute_type != "NONE"
                and not has_primary_devices
            ):
                row = layout.row(align=True)
                row.active = False
                row.label(text=f"No compatible devices found for {selected_compute_type}")
                return

        # Draw each device
        prev_type = None
        for device in devices_to_draw:
            if prev_type is not None and device.type != prev_type:
                layout.separator(type="LINE")

            if (
                self.launch_mode != "SINGLE_FRAME"
                and self.multiple_backends
                and self.device_parallel
            ):
                device_name = f"{self._normalize_device_name(device.name)} ({device.type})"
            else:
                device_name = self._normalize_device_name(device.name)

            row = layout.row()
            row.prop(device, "use", text=device_name, translate=False)

            prev_type = device.type

    def import_cycles_device_settings(self):
        """Import device settings from Cycles Render Devices"""
        try:
            cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
            cycles_devices = cycles_prefs.devices
            has_cuda, has_optix, has_hip, has_metal, has_oneapi, _ = self.get_device_types_cache()

            self.devices.clear()

            if has_cuda:
                self.get_device_list("CUDA")
            if has_optix:
                self.get_device_list("OPTIX")
            if has_hip:
                self.get_device_list("HIP")
            if has_metal:
                self.get_device_list("METAL")
            if has_oneapi:
                self.get_device_list("ONEAPI")

            for device in self.devices:
                is_enabled = False
                for cycles_device in cycles_devices:
                    if cycles_device.id == device.id:
                        is_enabled = cycles_device.use
                        break

                device.use = is_enabled

            self.compute_device_type = cycles_prefs.compute_device_type

            redraw_ui()
            return True
        except Exception as e:
            print(f"Error syncing with Cycles settings: {str(e)}")
            return False

    def rescan_all_devices(self):
        """Rescan all available device types and update the device list."""
        self.devices.clear()
        has_cuda, has_optix, has_hip, has_metal, has_oneapi, _ = self.get_device_types_cache()

        if has_cuda:
            self.get_device_list("CUDA")
        if has_optix:
            self.get_device_list("OPTIX")
        if has_hip:
            self.get_device_list("HIP")
        if has_metal:
            self.get_device_list("METAL")
        if has_oneapi:
            self.get_device_list("ONEAPI")

        self.get_device_list("CPU")

    def get_device_list(self, compute_device_type_str_enum_val):
        """Get device list for a specific device type"""
        device_list = []

        if compute_device_type_str_enum_val == "NONE":
            device_list = []
        else:
            device_list = _cycles.available_devices(compute_device_type_str_enum_val)

            # Add CPU devices if not using CPU as the main device type
            if compute_device_type_str_enum_val != "CPU":
                cpu_devices = _cycles.available_devices("CPU")
                existing_cpu_ids = {dev[2] for dev in device_list if dev[1] == "CPU"}
                for cpu_dev in cpu_devices:
                    if cpu_dev[2] not in existing_cpu_ids:
                        device_list.append(cpu_dev)

        self.update_device_entries(device_list, compute_device_type_str_enum_val)
        return device_list

    # Device parallel
    device_parallel: BoolProperty(
        name="Parallel Device Rendering",
        description="Launch separate render process for each device",
        default=True,
    )
    parallel_delay: FloatProperty(
        name="Multi-Process Start Delay",
        description="Delay before starting each additional render process to avoid resource conflicts.",
        min=0.0,
        default=0.5,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )
    frame_allocation: EnumProperty(
        items=[
            (
                "SEQUENTIAL",
                "Sequential",
                "Each device processes the entire frame range one after another.\n"
                "Use: Overwriting=False, Placeholders=True.",
            ),
            (
                "FRAME_SPLIT",
                "Split",
                "Divide the frame range evenly between devices.\n"
                "Each device renders a unique subset of frames concurrently.",
            ),
        ],
        default="FRAME_SPLIT",
        description="Determine how frames are distributed across rendering devices",
    )
    multiple_backends: BoolProperty(
        name="Multi-Backend",
        description="Render using enabled devices from different backends.",
        default=False,
    )
    combine_cpu_with_gpus: BoolProperty(
        name="Combine CPU with GPUs",
        default=True,
        description="Enable the CPU to be used alongside GPUs devices during parallel rendering.",
    )
    cpu_threads_limit: IntProperty(
        name="CPU Threads Limit",
        default=0,
        min=0,
        description="Limit the number of CPU threads used per render process.",
    )
    iterations_per_device: IntProperty(
        name="Iterations per Device",
        default=1,
        min=1,
        soft_max=8,
        description="Number of render iterations per device.",
    )

    # Blender executable
    def _validate_custom_blender_path(self, context):
        """
        Validate the Blender executable path.
        If a folder is provided, search for the executable within it.
        """
        path_str = self.custom_executable_path.strip()
        if not path_str:
            self.custom_executable_version = ""
            return

        path = Path(bpy.path.abspath(path_str))
        self.custom_executable_version = ""

        if not path.exists():
            log.error(f"Path does not exist: {path}")
            return

        executable_path = path

        if path.is_dir():
            found_exe = None
            if _IS_WINDOWS:
                potential_exe = path / "blender.exe"
                if potential_exe.is_file():
                    found_exe = potential_exe
            elif _IS_MACOS:  # macOS
                potential_exe = path / "Contents" / "MacOS" / "Blender"
                if potential_exe.is_file():
                    found_exe = potential_exe
                else:
                    potential_app_path = path / "Blender.app"
                    potential_exe_in_app = potential_app_path / "Contents" / "MacOS" / "Blender"
                    if potential_exe_in_app.is_file():
                        found_exe = potential_exe_in_app
            elif _IS_LINUX:
                potential_exe = path / "blender"
                if potential_exe.is_file():
                    found_exe = potential_exe

            if found_exe:
                self.custom_executable_path = str(found_exe)
                executable_path = found_exe
            else:
                log.error(f"Could not find a Blender executable in folder: {path}")
                return

        if not executable_path.is_file():
            log.error(f"Path is not a file: {executable_path}")
            return

        if _IS_WINDOWS:
            if executable_path.suffix.lower() != ".exe":
                log.error("On Windows, path must be a .exe file")
                return
        elif _IS_MACOS or _IS_LINUX:
            # Check if file is executable (using stat)
            try:
                if not os.access(str(executable_path), os.X_OK):
                    log.error("File is not executable")
                    return
            except Exception:
                log.error("Unable to check executable permissions")
                return

        # Get and display version info
        version_info = self._get_blender_version_info(str(executable_path))
        if version_info:
            formatted = "\n".join(
                f"{k.capitalize().replace('_', ' ')}: {v}" for k, v in version_info.items()
            )
            self.custom_executable_version = formatted
        else:
            log.error(f"Could not determine Blender version from: {executable_path}")

    def _get_blender_version_info(self, blender_path):
        try:
            result = subprocess.run(
                [blender_path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            lines = result.stdout.splitlines()

            info = {}
            commit_date = None
            commit_time = None

            for line in lines:
                if line.startswith("Blender "):
                    info["version"] = line[len("Blender ") :].strip()
                elif "build commit date:" in line:
                    commit_date = line.split(":", 1)[1].strip()
                elif "build commit time:" in line:
                    commit_time = line.split(":", 1)[1].strip()
                elif "build hash:" in line:
                    info["hash"] = line.split(":", 1)[1].strip()

            # Combine commit date and time into a single "Date" field
            if commit_date and commit_time:
                info["Date"] = f"{commit_date} {commit_time}"

            ordered_info = {
                "version": info.get("version", ""),
                "Date": info.get("Date", ""),
                "hash": info.get("hash", ""),
            }

            # Set custom_executable_version_tuple
            try:
                # Parse version string safely
                version_str = info.get("version", "4.0.0")
                # Remove any suffix after dash (e.g., "4.0.0-alpha" → "4.0.0")
                version_str = version_str.split("-")[0].split("+")[
                    0
                ]  # also handle build metadata like "+git..."
                version_parts = version_str.split(".")

                # Normalize to exactly 3 numeric parts
                normalized = []
                for i in range(3):
                    if i < len(version_parts):
                        part = version_parts[i].strip()
                        # Handle cases like "4a" → just take digits (optional, but defensive)
                        num_str = "".join(filter(str.isdigit, part)) or "0"
                        normalized.append(int(num_str))
                    else:
                        normalized.append(0)

                self.custom_executable_version_tuple = normalized

                # print(list(self.custom_executable_version_tuple))
                # print(type(self.custom_executable_version_tuple))

            except Exception as e:
                log.warning(f"Failed to get custom executable version: {e}")

            if ordered_info["version"]:
                return ordered_info
            else:
                return None

        except Exception:
            return None

    custom_executable_version: StringProperty(
        name="External Blender --version",
        description="",
        default="",
    )
    custom_executable_version_tuple: bpy.props.IntVectorProperty(
        name="Blender Version",
        description="Stored external Blender version",
        size=3,
        subtype="NONE",
        default=(0, 0, 0),
    )
    custom_executable_path: StringProperty(
        name="Blender Executable",
        description="Path to custom Blender executable.",
        default="",
        subtype="FILE_PATH",
        update=_validate_custom_blender_path,
        options={"SKIP_SAVE"},
    )
    custom_executable: BoolProperty(
        name="Custom Blender Executable",
        description="Override default Blender with a custom executable for rendering",
        default=False,
    )

    # External Terminal
    external_terminal: BoolProperty(
        name="Use External Terminal",
        description="Launch the render process in an external terminal.",
        default=True,
    )
    keep_terminal_open: BoolProperty(
        name="Keep Terminal Open",
        description="Keep the external terminal window open after the render finishes.",
        default=True,
    )
    exit_active_session: BoolProperty(
        name="Close Blender Before Render",
        description="Automatically close active blender session after launching a render job.",
        default=False,
    )

    # Render log to file
    log_to_file: BoolProperty(
        name="Log to File",
        default=False,
        description="Save render logs to a file in the project folder",
    )
    log_to_file_location: EnumProperty(
        name="",
        items=[
            (
                "BLEND_PATH",
                "Blend File Path",
                "Save logs in the same directory as the blend file.",
            ),
            ("CUSTOM_PATH", "Custom", "Specify a custom directory for log files."),
        ],
        default="BLEND_PATH",
    )
    save_to_log_folder: BoolProperty(
        name="Save to Logs Folder",
        default=True,
        description="Save logs in a dedicated 'logs' folder within the blend file's directory.",
    )
    log_custom_path: StringProperty(
        name="Save Logs Path",
        subtype="DIR_PATH",
        description="Directory to save log files when using custom location",
    )

    # Compact variables groups in output path variables
    show_file_info: BoolProperty(name="Show Variables", default=False)
    show_camera_info: BoolProperty(name="Show Variables", default=False)
    show_render_info: BoolProperty(name="Show Variables", default=False)
    show_date_system: BoolProperty(name="Show Variables", default=False)
    show_frame_range: BoolProperty(name="Show Variables", default=False)
    show_blender_info: BoolProperty(name="Show Variables", default=False)
    show_custom_blender_info: BoolProperty(name="Show Variables", default=False)
    show_custom_variables: BoolProperty(name="Show Variables", default=False)

    # Render external files
    recent_blend_files: CollectionProperty(type=RECOM_PG_RecentFile)

    def add_recent_blend_file(self, new_path):
        """Add a new blend file path to recent files, removing duplicates and prioritizing."""
        # Remove existing entries with the same path
        for i in reversed(range(len(self.recent_blend_files))):
            if self.recent_blend_files[i].path == new_path:
                self.recent_blend_files.remove(i)

        new_entry = self.recent_blend_files.add()
        new_entry.path = new_path

        while len(self.recent_blend_files) > 20:
            self.recent_blend_files.remove(0)

    def _sanitize_filename(self, context):
        value = self.default_render_filename
        cleaned = "".join(c for c in value if c.isalnum() or c in "_- ")
        if cleaned != value:
            self.default_render_filename = cleaned
            log.debug(f"Sanitized render filename: Original: '{value}', Cleaned: '{cleaned}'")

    default_render_filename: StringProperty(
        name="Default Render Filename",
        description="Set the default filename used when no output filename is specified.",
        default="render",
        update=_sanitize_filename,
    )

    # Render Options
    auto_save_before_render: BoolProperty(
        name="Auto‑Save Before Render",
        description="Save the current .blend file automatically before launching a background render.",
        default=False,
    )
    auto_open_output_folder: BoolProperty(
        name="Auto-Open Output Folder",
        default=False,
        description="Open the output folder automatically when the render starts.",
    )
    write_still: BoolProperty(
        name="Save Still Image",
        default=True,
        description="Save the rendered image to the output path (only for still renders).",
    )
    send_desktop_notifications: BoolProperty(
        name="Send Desktop Notification",
        description="Show a desktop notification when the render finishes.",
        default=False,
    )

    # Filename
    frame_length_digits: IntProperty(
        name="Frame Number Padding",
        default=4,
        min=1,
        soft_min=3,
        soft_max=6,
        description="Number of digits used to pad frame numbers in filenames.",
    )
    filename_separator: EnumProperty(
        name="Frame Number Separator",
        description="Character used to separate the filename and the frame number",
        items=[
            ("DOT", "Dot ( . )", "Filename.####"),
            ("UNDERSCORE", "Underscore ( _ )", "Filename_####"),
        ],
        default="UNDERSCORE",
    )

    # Append Scripts
    append_python_scripts: BoolProperty(
        name="Append Python Scripts",
        description="Add additional python scripts to run during rendering.",
        default=False,
    )
    additional_scripts: CollectionProperty(
        type=RECOM_PG_ScriptEntry,
        name="Additional Python Scripts",
        description="List of additional Python scripts to append during render.",
    )
    active_script_index: IntProperty(
        name="Active Script Index",
        default=0,
    )

    add_command_line_args: BoolProperty(
        name="Add Command Line Arguments",
        description="Add additional command line arguments.",
        default=False,
    )
    custom_command_line_args: StringProperty(
        name="Custom Command Line Arguments",
        description="Additional command line arguments to pass to Blender during render (e.g., --debug --verbose)",
        default="",
    )

    # OCIO
    set_ocio: BoolProperty(
        name="OCIO Environment Variable",
        description="Enable custom OCIO config for renders",
        default=False,
    )
    ocio_path: StringProperty(
        name="OCIO Config File",
        description="Path to the OCIO configuration file (.ocio)",
        subtype="FILE_PATH",
        update=lambda self, context: redraw_ui(),
    )

    # Linux
    linux_terminal: EnumProperty(
        name="",
        items=[
            ("GNOME", "GNOME Terminal", "GNOME Terminal"),
            ("XFCE", "Xfce Terminal", "Xfce Terminal"),
            ("KONSOLE", "KDE Konsole", "KDE Konsole"),
            ("XTERM", "Xterm", "Xterm"),
            ("TERMINATOR", "Terminator", "Terminator"),
        ],
        default="GNOME",
        description="Select the terminal emulator for Linux",
    )
    set_linux_terminal: BoolProperty(
        name="Set Linux Terminal",
        description="Select the terminal emulator.",
        default=False,
    )
    linux_file_explorer: EnumProperty(
        name="Linux File Explorer",
        description="Choose which file‑manager is used when opening folders on Linux",
        items=[
            ("NAUTILUS", "Nautilus", "GNOME Files (nautilus)"),
            ("DOLPHIN", "Dolphin", "KDE Dolphin"),
            ("THUNAR", "Thunar", "XFCE Thunar"),
            ("NEMO", "Nemo", "MATE Nemo"),
            ("XDG_OPEN", "xdg-open", "Fallback – use the system default (xdg‑open)"),
        ],
        default="XDG_OPEN",
    )

    # System Power
    set_system_power: BoolProperty(
        name="System Power",
        description="Enable system power options for rendering.",
        default=False,
    )

    prevent_sleep: BoolProperty(
        name="Prevent Computer Sleep",
        description=get_prevent_sleep_description(),
        default=True,
    )
    prevent_monitor_off: BoolProperty(
        name="Prevent Monitor Turn‑Off",
        description="Keep the display on while rendering.\nExtends the sleep prevention to include display activity.",
        default=False,
    )
    shutdown_after_render: BoolProperty(
        name="Shutdown After Render",
        default=False,
        description="Shutdown the computer after all render jobs are completed.",
    )
    shutdown_type: EnumProperty(
        name="",
        items=[
            ("SLEEP", "Sleep", "Put the computer to sleep after rendering."),
            ("POWER_OFF", "Shutdown", "Power off the computer after rendering."),
        ],
        default="SLEEP",
        description="Shutdown action after rendering",
    )
    shutdown_delay: FloatProperty(
        name="Shutdown Delay",
        description="Time to wait before executing the selected shutdown action after rendering finishes.",
        default=30.0,
        min=0.0,
        soft_min=1.0,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )

    # Misc
    compact_external_info: BoolProperty(
        name="Compact External Info",
        default=True,
        description=("Show external blend scene info in a compact box. "),
    )
    path_preview: BoolProperty(
        name="Show Resolved Path",
        default=False,
        description="Dynamically resolve and display the full output path with variables replaced.",
        # update=on_output_path_changed,
    )
    preset_installed: BoolProperty(
        default=False, description="Indicates if default presets have been installed."
    )
    initial_setup_complete: BoolProperty(
        name="Cycles Render Devices Setup Complete",
        description="Indicates if the initial device configuration has been completed.",
        default=False,
    )
    launch_mode: EnumProperty(
        items=[
            (MODE_SINGLE, "Image", "Render a single frame"),
            (MODE_SEQ, "Animation", "Render a full frame range"),
            (
                MODE_LIST,
                "Frame List",
                "Render non-continuous frame ranges",
            ),
        ],
        default="SINGLE_FRAME",
        description="Render Mode",
        update=lambda self, context: redraw_ui(),
    )

    # Custom path variables
    custom_variables: CollectionProperty(type=RECOM_PG_CustomVariable)
    active_custom_variable_index: IntProperty(default=-1, name="Active Custom Variable Index")

    def _validate_custom_temp_folder(self, context):
        """Validate the custom temp folder path."""
        path_str = self.custom_temp_path.strip()
        if not path_str:
            self.use_custom_temp = False
            return

        path = Path(bpy.path.abspath(path_str))

        # Check if path exists and is a directory
        if not path.exists() or not path.is_dir():
            log.error(f"Custom temp folder does not exist: {path}")
            self.use_custom_temp = False
            return

        # Check if we can write to the folder
        test_file = path / ".test_write"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception:
            log.error(f"Cannot write to custom temp folder: {path}")
            self.use_custom_temp = False
            return

        self.use_custom_temp = True

    custom_temp_path: StringProperty(
        name="Temp Folder Path",
        description="Specify a custom folder for the addon's temporary files.",
        default="",
        subtype="DIR_PATH",
        update=_validate_custom_temp_folder,
    )
    use_custom_temp: BoolProperty(
        name="Custom Temp Folder",
        description="Use a custom folder for the addon's temporary files instead of the default one.",
        default=False,
    )
    debug_mode: BoolProperty(
        name="Enable Debug Mode",
        description="Enable detailed logging for debugging purposes.",
        default=False,
    )

    # Render History
    render_history: CollectionProperty(type=RECOM_PG_RenderHistoryItem)
    active_render_history_index: IntProperty(default=-1, name="Active Render History Index")

    visible_panels: PointerProperty(type=RECOM_PG_VisiblePanels)

    # Preference Groups
    group_box_visible_panels: BoolProperty(name="Display Preferences", default=False)
    group_box_custom_variables: BoolProperty(name="Display Preferences", default=False)
    group_box_default_filename: BoolProperty(name="Display Preferences", default=False)
    group_box_default_applications: BoolProperty(name="Display Preferences", default=False)
    group_box_development: BoolProperty(name="Display Preferences", default=False)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        col = layout.column()

        # Show Panels
        visible_panels_box = col.box().column()
        visible_panels_header_row = visible_panels_box.row(align=True)
        visible_panels_header_row.alignment = "LEFT"
        icon = ICON_COLLAPSED if self.group_box_visible_panels else ICON_EXPANDED
        visible_panels_header_row.prop(
            self, "group_box_visible_panels", text="", icon=icon, emboss=False
        )
        visible_panels_header_row.label(text="Visible Panels")

        if self.group_box_visible_panels:
            # visible_panels_box.prop(self, "show_layout_options", text="Layout Buttons")
            # visible_panels_box.separator()

            visible_panels_box.label(text="General")

            main_panels_col = visible_panels_box.column(heading="")
            main_panels_col.prop(self.visible_panels, "external_scene", text="External Scene")
            main_panels_col.prop(self.visible_panels, "override_settings", text="Override Settings")
            main_panels_col.prop(self.visible_panels, "preferences", text="Preferences")
            main_panels_col.prop(self.visible_panels, "history", text="History")

            visible_panels_box.label(text="Override Settings")
            override_settings_box = visible_panels_box.column(heading="")

            # Cycles
            cycles_settings_box = override_settings_box.column(heading="Cycles Render")
            cycles_settings_box.prop(self.visible_panels, "compute_device", text="Compute Device")
            cycles_settings_box.prop(self.visible_panels, "light_paths", text="Light Paths")
            cycles_settings_box.prop(self.visible_panels, "performance")
            cycles_settings_box.separator()

            override_settings_box.prop(self.visible_panels, "frame_range", text="Frame Range")

            override_settings_box.separator()
            override_settings_box.prop(self.visible_panels, "resolution", text="Format")
            override_settings_box.prop(self.visible_panels, "overscan", text="Overscan")
            override_settings_box.prop(self.visible_panels, "camera_shift", text="Lens Shift")
            override_settings_box.separator()

            override_settings_box.prop(self.visible_panels, "motion_blur", text="Motion Blur")
            override_settings_box.prop(self.visible_panels, "output_path", text="Output Path")
            override_settings_box.prop(self.visible_panels, "file_format", text="File Format")
            override_settings_box.prop(self.visible_panels, "compositor", text="Compositing")

            visible_panels_box.label(text="Preferences")

            preferences_box = visible_panels_box.column(heading="")
            preferences_box.prop(self.visible_panels, "system_power")
            preferences_box.prop(self.visible_panels, "ocio")
            preferences_box.prop(self.visible_panels, "blender_executable")
            preferences_box.prop(self.visible_panels, "command_line_arguments")
            preferences_box.prop(self.visible_panels, "append_scripts")

        col.separator(factor=0.25)

        # Custom Variables
        custom_vars_box = col.box().column()
        custom_vars_header_row = custom_vars_box.row(align=True)
        custom_vars_header_row.alignment = "LEFT"
        icon = ICON_COLLAPSED if self.group_box_custom_variables else ICON_EXPANDED
        custom_vars_header_row.prop(
            self, "group_box_custom_variables", text="", icon=icon, emboss=False
        )
        custom_vars_header_row.label(text="Custom Path Variables")

        if self.group_box_custom_variables:
            custom_vars_row = custom_vars_box.row()
            variables_list_box = custom_vars_row.column()
            listbox = variables_list_box.template_list(
                "RECOM_UL_custom_variables",
                "",
                self,
                "custom_variables",
                self,
                "active_custom_variable_index",
                rows=4,
            )

            if self.active_custom_variable_index >= 0:
                variables_list_box.separator()
                current_variable = self.custom_variables[self.active_custom_variable_index]
                variable_details_box = custom_vars_box.column(align=True)
                variable_details_box.prop(current_variable, "name", text="Variable Name")
                variable_details_box.prop(current_variable, "token", text="Token")
                variable_details_box.prop(current_variable, "value", text="Value")

            variable_controls_box = custom_vars_row.column()
            add_remove_box = variable_controls_box.column(align=True)
            add_remove_box.operator("recom.add_custom_variable", text="", icon="ADD")

            is_variable_selected = len(
                self.custom_variables
            ) > 0 and self.active_custom_variable_index < len(self.custom_variables)

            remove_variable_button = add_remove_box.column(align=True)
            remove_variable_button.active = is_variable_selected
            remove_variable_button.operator(
                "cbl.remove_custom_variable", text="", icon="REMOVE"
            )  # placeholder
            variable_controls_box.separator(factor=0.5)

            variable_menu_row = variable_controls_box.row()
            if not is_variable_selected or len(self.custom_variables) < 2:
                variable_menu_row.active = False
            variable_menu_row.menu("RECOM_MT_custom_variables", text="", icon="DOWNARROW_HLT")

        # Default Filename
        col.separator(factor=0.25)

        default_filename_box = col.box().column()
        default_filename_header_row = default_filename_box.row(align=True)
        default_filename_header_row.alignment = "LEFT"
        icon = ICON_COLLAPSED if self.group_box_default_filename else ICON_EXPANDED
        default_filename_header_row.prop(
            self, "group_box_default_filename", text="", icon=icon, emboss=False
        )
        default_filename_header_row.label(text="Output Filename")

        if self.group_box_default_filename:
            default_filename_box.prop(self, "default_render_filename", text="Default Name")
            default_filename_box.prop(self, "filename_separator", text="Frame Separator")
            default_filename_box.prop(self, "frame_length_digits", text="Padding")

        # Linux - Default Applications
        if _IS_LINUX:
            col.separator(factor=0.25)

            default_apps_box = col.box().column()
            default_apps_header_row = default_apps_box.row(align=True)
            default_apps_header_row.alignment = "LEFT"
            icon = ICON_COLLAPSED if self.group_box_default_applications else ICON_EXPANDED
            default_apps_header_row.prop(
                self, "group_box_default_applications", text="", icon=icon, emboss=False
            )
            default_apps_header_row.label(text="Default Applications")

            if self.group_box_default_applications:
                terminal_row = default_apps_box.row(align=True, heading="Terminal")
                terminal_row.prop(self, "set_linux_terminal", text="")
                terminal_sub_row = terminal_row.row()
                terminal_sub_row.active = self.set_linux_terminal
                terminal_sub_row.prop(self, "linux_terminal", text="")
                default_apps_box.prop(self, "linux_file_explorer", text="File Explorer")

        # Development
        col.separator(factor=0.25)

        development_box = col.box().column()
        development_header_row = development_box.row(align=True)
        development_header_row.alignment = "LEFT"
        icon = ICON_COLLAPSED if self.group_box_development else ICON_EXPANDED
        development_header_row.prop(self, "group_box_development", text="", icon=icon, emboss=False)
        development_header_row.label(text="Developer")

        if self.group_box_development:
            # development_box.separator()

            debug_preferences_box = development_box.column()

            temp_row = debug_preferences_box.row(heading="Temp Folder")
            temp_row.prop(self, "use_custom_temp", text="")
            temp_sub_row = temp_row.row()
            temp_sub_row.active = self.use_custom_temp
            temp_sub_row.prop(self, "custom_temp_path", text="", placeholder="")
            # development_box.separator()

            development_box.prop(self, "debug_mode", text="Debug Mode")

            if self.debug_mode:
                debug_preferences_box = development_box.column(heading="Debug")
                debug_preferences_box.prop(
                    self, "initial_setup_complete", text="Cycles Setup Completed"
                )
                debug_preferences_box.prop(
                    self, "preset_installed", text="Default Presets Installed"
                )


class RECOM_UL_custom_variables(UIList):
    bl_idname = "RECOM_UL_custom_variables"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag
    ):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            # Show name and token side‑by‑side
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, placeholder="Name")
            row.prop(item, "token", text="", placeholder="Token")
            row.prop(item, "value", text="", placeholder="Value")


classes = (
    RECOM_PG_DeviceSettings,
    RECOM_PG_RecentFile,
    RECOM_PG_RenderHistoryItem,
    RECOM_PG_ScriptEntry,
    RECOM_PG_CustomVariable,
    RECOM_PG_VisiblePanels,
    RECOM_UL_custom_variables,
    RECOM_Preferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
