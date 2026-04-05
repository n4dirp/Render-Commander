# ./preferences.py

import os
import sys
import platform
import logging
import subprocess
import shutil
import re
from pathlib import Path

import bpy
import _cycles

from bpy.types import AddonPreferences, PropertyGroup, Panel
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
from .utils.helpers import redraw_ui

_IS_WINDOWS = sys.platform.startswith("win")
_IS_MACOS = sys.platform == "darwin"
_IS_LINUX = sys.platform.startswith("linux")

log = logging.getLogger(__name__)

os.environ["TBB_MALLOC_DISABLE_REPLACEMENT"] = "1"

PACKAGE = __package__

enum_device_type = (
    ("CPU", "CPU", "CPU", 0),
    ("CUDA", "CUDA", "CUDA", 1),
    ("OPTIX", "OptiX", "OptiX", 3),
    ("HIP", "HIP", "HIP", 4),
    ("METAL", "Metal", "Metal", 5),
    ("ONEAPI", "oneAPI", "oneAPI", 6),
)


# Helper functions
def get_addon_preferences(context):
    return context.preferences.addons[__package__].preferences


# Device settings
class RECOM_PG_DeviceSettings(PropertyGroup):
    id: StringProperty(name="ID", description="Unique identifier of the device")
    name: StringProperty(name="Name", description="Name of the device")
    use: BoolProperty(name="Use", description="Use device for rendering", default=True)
    type: EnumProperty(name="Type", items=enum_device_type, default="OPTIX")


# Scripts entries for appending during rendering
class RECOM_PG_ScriptEntry(PropertyGroup):
    script_path: StringProperty(
        name="Script Path",
        description="Python script to run before or after render",
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

    def _get_tooltip(self):
        return f"Script Path: {self.script_path}"

    def _set_tooltip(self, value):
        # The preset system will try to write a string here – we just ignore it.
        pass

    tooltip_display: StringProperty(
        get=_get_tooltip,
        set=_set_tooltip,
        description="Tooltip shown on hover (Path: <full script path>)",
    )


# Custom path variables for output paths
class RECOM_PG_CustomVariable(PropertyGroup):
    name: StringProperty(
        name="Variable Name",
        description="Custom variable name (e.g. 'scene')",
        update=lambda self, context: redraw_ui(),
    )
    token: StringProperty(
        name="Placeholder Token",
        description="Token used in paths (e.g. '{variable}')",
        update=lambda self, context: redraw_ui(),
    )
    value: StringProperty(
        name="Replacement Value",
        description="Value to replace the placeholder token",
        update=lambda self, context: redraw_ui(),
    )


# Render History
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
    samples: StringProperty(name="Samples", default="")
    output_folder: StringProperty(name="Output Folder", default="")
    output_filename: StringProperty(name="Output Filename", default="")
    file_format: StringProperty(name="File Format", default="")


class RECOM_PG_RecentBlendFile(PropertyGroup):
    path: StringProperty(name="Blend File Path")


# Visibility settings for addon panels
class RECOM_PG_VisiblePanels(PropertyGroup):
    external_scene: BoolProperty(name="Blend File", default=True, update=lambda self, context: redraw_ui())
    override_settings: BoolProperty(name="Override Settings", default=True, update=lambda self, context: redraw_ui())
    preferences: BoolProperty(name="Preferences", default=True, update=lambda self, context: redraw_ui())
    ocio: BoolProperty(name="OCIO Configuration", default=False)
    history: BoolProperty(name="History", default=True, update=lambda self, context: redraw_ui())


class RECOM_PG_OverrideImportSettings(PropertyGroup):
    """Import‑group toggles"""

    import_compute_device: BoolProperty(name="Compute Device", default=False)
    import_frame_range: BoolProperty(name="Frame Range", default=True)
    import_resolution: BoolProperty(name="Resolution", default=True)
    import_sampling: BoolProperty(name="Sampling", default=False)
    import_eevee_settings: BoolProperty(name="EEVEE", default=False)
    import_motion_blur: BoolProperty(name="Motion Blur", default=False)
    import_output_path: BoolProperty(name="Output Path", default=True)
    import_output_format: BoolProperty(name="File Format", default=False)
    import_performance: BoolProperty(name="Performance", default=False)
    import_compositor: BoolProperty(name="Compositor", default=False)


# Main addon preferences class
class RECOM_Preferences(AddonPreferences):
    """Preferences for the addon settings"""

    bl_idname = __package__

    # -------------------------------------------------------------------
    # Addon Cycles Devices Configuration
    # -------------------------------------------------------------------

    _device_types_cache = None

    @classmethod
    def get_device_types_cache(cls):
        if cls._device_types_cache is None:
            cls._device_types_cache = _cycles.get_device_types()
        return cls._device_types_cache

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
            items.append(("CUDA", "CUDA", "Use NVIDIA CUDA for GPU acceleration", 1))
        if has_optix:
            items.append(("OPTIX", "OptiX", "Use NVIDIA OptiX for GPU acceleration", 3))
        if has_hip:
            items.append(("HIP", "HIP", "Use AMD HIP for GPU acceleration", 4))
        if has_metal:
            items.append(("METAL", "Metal", "Use Apple Metal for GPU acceleration", 5))
        if has_oneapi:
            items.append(("ONEAPI", "oneAPI", "Use Intel oneAPI for GPU acceleration", 6))
        return items

    def _update_compute_device_type(self, context):
        if self.compute_device_type != "NONE":
            self.get_device_list(self.compute_device_type)
        else:
            self.get_device_list("NONE")

    compute_device_type: EnumProperty(
        name="Compute Device Type",
        description="Device to use for computation (rendering with Cycles)",
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
            if device_entry.id == device_info_tuple[2] and device_entry.type == device_info_tuple[1]:
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
            # Show all devices, but order with CPU first
            cpu_devices = []
            non_cpu_devices = []

            for dev_entry in self.devices:
                if dev_entry.type == "CPU":
                    cpu_devices.append(dev_entry)
                else:
                    non_cpu_devices.append(dev_entry)

            devices_to_display = cpu_devices + non_cpu_devices
        else:
            # Original logic: filter based on compute_device_type
            for dev_entry in self.devices:
                if dev_entry.type == selected_compute_type and dev_entry.type != "CPU":
                    devices_to_display.append(dev_entry)
            if selected_compute_type != "CPU":
                for dev_entry in self.devices:
                    if dev_entry.type == "CPU" and not any(d.id == dev_entry.id for d in devices_to_display):
                        devices_to_display.append(dev_entry)
            else:
                for dev_entry in self.devices:
                    if dev_entry.type == "CPU":
                        devices_to_display.append(dev_entry)
        return devices_to_display

    @staticmethod
    def _format_device_name(name):
        import unicodedata

        return (
            name.replace("(TM)", unicodedata.lookup("TRADE MARK SIGN"))
            .replace("(tm)", unicodedata.lookup("TRADE MARK SIGN"))
            .replace("(R)", unicodedata.lookup("REGISTERED SIGN"))
            .replace("(C)", unicodedata.lookup("COPYRIGHT SIGN"))
        )

    def _draw_devices(self, layout, devices_to_draw):
        selected_compute_type = self.compute_device_type

        # Quick‑check for “no compatible devices” when we’re not in multi‑backend mode.
        has_primary_devices = any(d.type == selected_compute_type and d.type != "CPU" for d in devices_to_draw)
        if not (self.multiple_backends and self.device_parallel):
            if not devices_to_draw or (
                selected_compute_type != "CPU" and selected_compute_type != "NONE" and not has_primary_devices
            ):
                col = layout.column(align=True)
                col.active = False
                col.label(text=f"No compatible GPUs found for Cycles")

                return

        # Draw each device
        prev_type = None
        for device in devices_to_draw:
            if (
                prev_type is not None
                and device.type != prev_type
                and not (self.multiple_backends and self.device_parallel and self.launch_mode != "SINGLE_FRAME")
            ):
                layout.separator(type="AUTO", factor=0.5)

            device_name = self._format_device_name(device.name)

            if device.type != prev_type:
                if self.launch_mode != "SINGLE_FRAME" and self.multiple_backends and self.device_parallel:
                    type_col = layout.column(align=True)

                    type_row = type_col.row()
                    type_row.active = False
                    type_row.label(text=device.type)

                else:
                    type_col = layout.column(align=True)

            type_col.prop(device, "use", text=device_name, translate=False)

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

    # -------------------------------------------------------------------
    # Render Options And Behavior Properties
    # -------------------------------------------------------------------

    # Device parallel
    device_parallel: BoolProperty(
        name="Parallel Rendering",
        description="Launch separate render process for each device",
        default=True,
    )
    parallel_delay: FloatProperty(
        name="Multi-Process Start Delay",
        description="Delay before starting each additional render process to avoid resource conflicts",
        min=0.0,
        default=1.0,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )
    frame_allocation: EnumProperty(
        name="Frame Mode",
        items=[
            (
                "SEQUENTIAL",
                "Sequential",
                "Each device renders the full frame range.\n"
                "Automatically disables overwriting and enables placeholders.",
            ),
            ("FRAME_SPLIT", "Split", "Divide frame range among devices"),
        ],
        default="FRAME_SPLIT",
        description="How frames are distributed across rendering devices",
    )
    multiple_backends: BoolProperty(
        name="Multi-Backend",
        description="Render using enabled devices from different backends",
        default=False,
    )
    combine_cpu_with_gpus: BoolProperty(
        name="CPU & GPU Rendering",
        default=True,
        description="Create a dedicated CPU-only render job and exclude the CPU from all other render jobs",
    )
    cpu_threads_limit: IntProperty(
        name="Thread Limit",
        default=0,
        min=0,
        description="Maximum threads for rendering jobs",
    )

    iterations_per_device: IntProperty(
        name="Iterations per Device",
        default=1,
        min=1,
        soft_max=8,
        description="Number of render iterations per device",
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

            elif _IS_MACOS:
                potential_exe = path / "Contents" / "MacOS" / "Blender"
                if potential_exe.is_file():
                    found_exe = potential_exe
                else:
                    potential_exe_in_app = path / "Blender.app" / "Contents" / "MacOS" / "Blender"
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
        version_str = self._get_blender_version_info(str(executable_path))
        if version_str:
            self.custom_executable_version = version_str
        else:
            log.error(f"Could not determine Blender version from: {executable_path}")

    def _get_blender_version_info(self, blender_path):
        """Returns the version string of the external Blender executable."""
        try:
            result = subprocess.run(
                [blender_path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            for line in result.stdout.splitlines():
                if line.startswith("Blender "):
                    return line[len("Blender ") :].strip()

            return None
        except Exception as e:
            log.error(f"Failed to fetch Blender version: {e}")
            return None

    blender_executable_source: EnumProperty(
        name="Blender Executable",
        description="Source of Blender executable",
        items=[
            ("CURRENT", "Current", "Use the executable of the currently running Blender"),
            ("SYSTEM", "System", "Use the Blender executable available in the system environment PATH"),
            ("CUSTOM", "Custom", "Use a manually specified Blender executable path"),
        ],
        default="CURRENT",
    )
    custom_executable_path: StringProperty(
        name="Executable Path",
        description="Custom Blender executable path",
        default="",
        subtype="FILE_PATH",
        update=_validate_custom_blender_path,
        options={"SKIP_SAVE"},
    )
    custom_executable_version: StringProperty(
        name="External Blender --version",
        description="",
        default="",
    )

    # External Terminal
    keep_terminal_open: BoolProperty(
        name="Keep Terminal Open",
        description="Keep the terminal window open after the render finishes",
        default=True,
    )
    exit_active_session: BoolProperty(
        name="Close Blender",
        description="Automatically exit current Blender instance before rendering",
        default=False,
    )
    use_windows_terminal_tabs: BoolProperty(
        name="Use Windows Terminal Tabs",
        description=(
            "Open all render processes as tabs within one terminal window.\n"
            "Requires Windows Terminal ('wt') to be installed and available in PATH."
        ),
        default=True,
    )

    # Render logging
    log_to_file: BoolProperty(
        name="Log to File",
        default=False,
        description="Save render logs to a file.\n" "Add: --log-file <filepath>",
    )
    log_to_file_location: EnumProperty(
        name="Log Directory",
        items=[
            ("EXECUTION_FILES", "Scripts Path", "Save logs files in render scripts directory"),
            ("BLEND_PATH", "Blend File Path", "Save logs files next to blend file"),
            ("CUSTOM_PATH", "Custom Path", "Specify custom log folder location"),
        ],
        default="EXECUTION_FILES",
    )
    save_to_log_folder: BoolProperty(
        name="Save to Logs Folder",
        default=True,
        description="Save logs in a dedicated 'logs' folder within the blend file's directory",
    )
    log_custom_path: StringProperty(
        name="Save Logs Path",
        subtype="DIR_PATH",
        description="Directory to save log files when using custom location",
    )
    logs_folder_name: StringProperty(
        name="Logs Subfolder",
        description="Folder name for render log files",
        default=RENDER_LOGS_FOLDER_NAME,
    )

    recent_blend_files: CollectionProperty(type=RECOM_PG_RecentBlendFile)

    # Render Options

    default_render_filename: StringProperty(
        name="Filename",
        description="Default filename for render output files, used if the filename is empty.",
        default="render",
    )

    auto_save_before_render: BoolProperty(
        name="Auto‑Save Before Render",
        description="Auto-save the current blend file before rendering",
        default=False,
    )
    auto_open_output_folder: BoolProperty(
        name="Auto-Open Output Folder",
        default=False,
        description="Open the output folder automatically when the render starts",
    )
    write_still: BoolProperty(
        name="Write Still",
        default=True,
        description="Write Image, Save the rendered image to the output path",
    )

    # Notification
    send_desktop_notifications: BoolProperty(
        name="Send Desktop Notification",
        description="Show a desktop notification when the render finishes",
        default=False,
    )
    show_notification_all_workers: BoolProperty(
        name="Show for All Workers",
        description="Display desktop notification for all rendering workers (not just first)",
        default=False,
    )
    notification_detail_level: EnumProperty(
        name="Notification Content",
        items=[
            ("SIMPLE", "Simple", "Minimal info: Just status"),
            ("DETAILED", "Detailed", "Full info: Filename, Format, Resolution, Output Path"),
        ],
        default="DETAILED",
        description="How much detail to show in desktop notifications",
    )

    # Filename
    frame_length_digits: IntProperty(
        name="Frame Number Padding",
        default=4,
        min=1,
        soft_min=3,
        soft_max=6,
        description="Number of digits used to pad frame numbers in filenames",
    )
    filename_separator: EnumProperty(
        name="File Separator",
        description="Separator between filename and frame numbers",
        items=[
            ("DOT", "Dot (.)", "Filename.####"),
            ("UNDERSCORE", "Underscore (_)", "Filename_####"),
        ],
        default="DOT",
    )

    # Append Scripts
    append_python_scripts: BoolProperty(
        name="Append Python Scripts",
        description="Add additional python scripts to run during rendering.\n" "Add: --python <filepath>",
        default=False,
    )
    additional_scripts: CollectionProperty(
        type=RECOM_PG_ScriptEntry,
        name="Additional Python Scripts",
        description="List of additional Python scripts to append during render",
    )
    active_script_index: IntProperty(
        name="Active Script Index",
        default=0,
    )

    # Command line arguments
    add_command_line_args: BoolProperty(
        name="Use Command Line Arguments",
        description="Add additional command line arguments for render",
        default=True,
    )
    custom_command_line_args: StringProperty(
        name="Command Line Arguments",
        description="Additional command line arguments to pass to Blender during render",
        default="-noaudio --log render",
        update=lambda self, context: redraw_ui(),
    )

    # OCIO config
    set_ocio: BoolProperty(
        name="OCIO Config",
        description="Use a custom color management configuration",
        default=False,
    )
    ocio_path: StringProperty(
        name="OCIO Config File",
        description="Path to the OCIO configuration file (.ocio)",
        subtype="FILE_PATH",
        update=lambda self, context: redraw_ui(),
    )

    # Linux specific default applications
    linux_terminal_config: StringProperty(
        name="Terminal Emulator Command",
        description=(
            "Enter the command and execution flag for your preferred terminal.\n"
            "Example: 'konsole -e'.\n"
            "Leave empty to auto-detect a standard installed terminal."
        ),
        default="",
    )
    linux_explorer_config: StringProperty(
        name="File Explorer Command",
        description=(
            "Enter the command and any flags for your preferred file manager.\n"
            "Example: 'dolphin --select'.\n"
            "Leave empty to use system defaults or auto-detect."
        ),
        default="",
    )

    # System power management
    shutdown_after_render: BoolProperty(
        name="Shutdown After Render",
        default=False,
        description="Shutdown the computer after all render jobs are completed",
    )
    shutdown_type: EnumProperty(
        name="",
        items=[
            ("SLEEP", "Sleep", "Put the computer to sleep after rendering"),
            ("POWER_OFF", "Shutdown", "Power off the computer after rendering"),
        ],
        default="SLEEP",
        description="Shutdown action after rendering",
    )
    shutdown_delay: FloatProperty(
        name="Shutdown Delay",
        description="Time to wait before executing the selected shutdown action after rendering finishes",
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
        description=("Show external blend scene info in a compact box"),
    )
    preset_installed: BoolProperty(
        default=False,
        description="Indicates if default presets have been installed",
    )
    cycles_setup_complete: BoolProperty(
        name="Cycles Render Devices Setup Complete",
        description="Indicates if the initial device configuration has been completed",
        default=False,
    )
    launch_mode: EnumProperty(
        items=[
            (MODE_SINGLE, "Image", "Render a single frame"),
            (MODE_SEQ, "Animation", "Render a full frame range"),
            (
                MODE_LIST,
                "List",
                "Render non-continuous frame ranges",
            ),
        ],
        default=MODE_SEQ,
        description="Render Mode",
        update=lambda self, context: redraw_ui(),
    )

    # Custom path variables
    custom_variables: CollectionProperty(type=RECOM_PG_CustomVariable)
    active_custom_variable_index: IntProperty(default=-1, name="Active Custom Variable Index")

    # Temporary files
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
        description="Specify a custom folder for the addon's temporary files",
        default="",
        subtype="DIR_PATH",
        update=_validate_custom_temp_folder,
    )
    use_custom_temp: BoolProperty(
        name="Custom Temp Folder",
        description="Use a custom folder for the addon's temporary files instead of the default one",
        default=False,
    )
    auto_clean_enabled: BoolProperty(
        name="Enable Auto Clean",
        description="Enable automatic cleanup of old temporary files on startup",
        default=True,
    )
    auto_clean_older_than_days: FloatProperty(
        name="Auto-Clean Older Than",
        description="Automatically clean temporary files older than this time",
        default=7 * 24 * 60 * 60,
        min=60.0,
        soft_min=24 * 60 * 60,
        soft_max=365.0 * 24 * 60 * 60,
        step=100.0 * 60 * 60 * 24,
        unit="TIME_ABSOLUTE",
    )
    debug_mode: BoolProperty(
        name="Enable Debug Mode",
        description="Enable detailed logging for debugging purposes",
        default=False,
    )

    # Render History
    render_history: CollectionProperty(type=RECOM_PG_RenderHistoryItem)
    active_render_history_index: IntProperty(default=-1, name="Active Render History Index")

    # Export options properties
    auto_open_exported_folder: BoolProperty(
        name="Open Exported Folder",
        description="Open the folder that contains the exported script/files after export",
        default=False,
    )
    export_output_target: EnumProperty(
        name="Export Folder Target",
        description="Where the exported files will be saved",
        items=[
            ("SELECT_DIR", "Select Directory", "Folder chosen in the export dialog"),
            ("BLEND_DIR", "Blend File Path", "Folder next to the .blend file"),
            ("CUSTOM_PATH", "Custom Path", "User‑defined folder"),
        ],
        default="SELECT_DIR",
    )
    custom_export_path: StringProperty(
        name="Custom Export Path",
        description="Manually set the folder to open after export",
        subtype="DIR_PATH",
        default="",
        update=lambda self, context: redraw_ui(),
    )
    export_master_script: BoolProperty(
        name="Export Master Script",
        description="For parallel rendering, exports an additional master script to launch multiple workers",
        default=True,
    )

    # Scripts directory properties
    scripts_directory: StringProperty(
        name="Scripts Directory",
        description="Directory containing additional Python scripts",
        default="",
        subtype="DIR_PATH",
    )
    export_scripts_subfolder: BoolProperty(
        name="Scripts Subfolder",
        description="Save the script files into a subfolder",
        default=False,
    )
    export_scripts_folder_name: StringProperty(
        name="Export Scripts Folder",
        description="Folder name for export render scripts",
        default=EXPORT_SCRIPTS_FOLDER_NAME,
    )

    # Import override settings
    override_import_settings: PointerProperty(type=RECOM_PG_OverrideImportSettings)

    # EEVEE & Workbench
    multi_instance: BoolProperty(
        name="Multi-Process",
        default=False,
        description="Run multiple render processes simultaneously",
    )
    render_iterations: IntProperty(
        name="Render Iterations",
        description="Number of render iterations to run simultaneously",
        default=2,
        min=2,
        soft_max=4,
    )

    # Panel visibility settings
    visible_panels: PointerProperty(type=RECOM_PG_VisiblePanels)

    # Command Line Debug
    debug_mode: BoolProperty(
        name="Basic Debug Mode",
        description="Turn debugging on.\n" "Add: --debug",
        default=False,
    )
    debug_value: IntProperty(
        name="Debug Value",
        default=0,
        min=0,
        max=3,
        description="Set specific debug value for debugging purposes (0-3).\n" "Add: --debug-value <value>",
    )
    verbose_level: EnumProperty(
        name="Verbosity Level",
        items=[
            ("0", "None", "No verbosity"),
            ("1", "Low", "Low verbosity"),
            ("2", "Medium", "Medium verbosity - default"),
            ("3", "High", "High verbosity"),
        ],
        default="2",
        description="Set the verbosity level for debug messages.\n" "Add: --verbose <verbose>",
    )
    debug_cycles: BoolProperty(
        name="Debug Cycles",
        description="Enable debug messages from Cycles renderer.\n" "Add: --debug-cycles",
        default=False,
    )

    def draw_default_applications(self, context, layout):
        layout.label(text="Default Applications")
        root_col = layout.column()
        root_col.prop(self, "linux_terminal_config", text="Terminal Emulator")
        root_col.prop(self, "linux_explorer_config", text="File Explorer")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text="Visible Panels")
        root_col = layout.column()

        # Main panels
        main_panels_col = root_col.column(align=True)
        main_panels_col.prop(self.visible_panels, "external_scene")
        main_panels_col.prop(self.visible_panels, "override_settings")
        main_panels_col.prop(self.visible_panels, "preferences")
        main_panels_col.prop(self.visible_panels, "history")

        preferences_col = root_col.column(heading="Render Preferences")
        preferences_col.prop(self.visible_panels, "ocio")

        root_col.separator()
        root_col = layout.column()

        # Temporary Files
        temp_box = root_col
        temp_box.label(text="Temporary Files")

        # Temp folder
        temp_row = temp_box.row(heading="Custom Path")
        temp_row.prop(self, "use_custom_temp", text="")
        temp_path_row = temp_row.row()
        temp_path_row.active = self.use_custom_temp
        temp_path_row.prop(self, "custom_temp_path", text="", placeholder="")

        # Temp cleanup
        temp_tools_col = temp_box.column()
        auto_clean_row = temp_tools_col.row(align=True, heading="Auto-Clean")
        auto_clean_row.prop(self, "auto_clean_enabled", text="")

        age_row = auto_clean_row.row(align=True)
        age_row.active = self.auto_clean_enabled
        age_row.prop(self, "auto_clean_older_than_days", text="")

        actions_row = auto_clean_row.row(align=True)
        actions_row.operator("recom.clean_temp_files", text="", icon="TRASH")
        actions_row.operator("recom.open_temp_dir", text="", icon="FILE_FOLDER")

        # Linux Defaults
        if _IS_LINUX:
            root_col.separator()
            self.draw_default_applications(context, root_col)

        # Debugging
        root_col.separator()
        root_col.label(text="Debug")
        root_col.prop(self, "debug_mode", text="Developer Mode")

        if self.debug_mode:
            debug_col = root_col.column(heading="")
            debug_col.prop(self, "cycles_setup_complete", text="Cycles Setup Completed")


classes = (
    RECOM_PG_OverrideImportSettings,
    RECOM_PG_DeviceSettings,
    RECOM_PG_RecentBlendFile,
    RECOM_PG_RenderHistoryItem,
    RECOM_PG_ScriptEntry,
    RECOM_PG_CustomVariable,
    RECOM_PG_VisiblePanels,
    RECOM_Preferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
