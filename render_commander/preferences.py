# ./preferences.py

import logging

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import AddonPreferences, PropertyGroup

from .utils.constants import (
    MODE_LIST,
    MODE_SEQ,
    MODE_SINGLE,
)
from .utils.cycles_devices import (
    RECOM_PG_DeviceSettings,
    get_device_types_items,
    refresh_cycles_devices,
)
from .utils.helpers import redraw_ui

log = logging.getLogger(__name__)


def on_logging_pref_changed(self, context):
    """Triggered whenever the user checks/unchecks the setting in the UI"""
    from . import update_logger_from_prefs

    update_logger_from_prefs()


class RECOM_PG_ScriptEntry(PropertyGroup):
    """Scripts entries for appending during rendering"""

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


class RECOM_PG_CustomVariable(PropertyGroup):
    """Custom path variables for output paths"""

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


class RECOM_PG_RenderHistoryItem(PropertyGroup):
    """Render history properties"""

    blend_path: StringProperty(name="Blend Path", default="")
    blend_dir: StringProperty(name="Blend Directory", default="")
    blend_file_name: StringProperty(name="Blend Name", default="")
    render_id: StringProperty(name="Render ID", default="")
    worker_count: IntProperty(name="Workers", default=0)
    date: StringProperty(name="Date", default="")
    export_path: StringProperty(name="Export Path", default="")
    script_filename: StringProperty(name="Script Filename", default="")
    render_engine: StringProperty(name="Render Engine", default="")
    launch_mode: StringProperty(name="Render Mode", default="")
    frames: StringProperty(name="Frames", default="")
    resolution_x: IntProperty(name="Width", default=0)
    resolution_y: IntProperty(name="Height", default=0)
    samples: StringProperty(name="Samples", default="")
    output_path: StringProperty(name="Output Path", default="")
    file_format: StringProperty(name="File Format", default="")


class RECOM_PG_PropertyItem(PropertyGroup):
    """Single property row for active item display"""

    name: StringProperty(name="Property Name", default="")
    value: StringProperty(name="Property Value", default="")
    tooltip: StringProperty(name="Tooltip", default="Script Details")


def update_active_render_history_properties(self, context):
    """Update the active item properties collection when selection changes"""
    # Validate index bounds
    if self.active_render_history_index < 0 or not self.render_history:
        return

    # Check if index is within valid range
    if self.active_render_history_index >= len(self.render_history):
        # Reset to valid index or -1 if collection is empty
        self.active_render_history_index = len(self.render_history) - 1 if self.render_history else -1
        return

    active_item = self.render_history[self.active_render_history_index]

    # Clear existing properties
    self.active_item_properties.clear()

    # Define which properties to display
    properties_to_show = [
        ("Blend Name", active_item.blend_file_name),
        ("Blend Directory", active_item.blend_dir),
        ("Render ID", active_item.render_id),
        ("Date", active_item.date),
        ("Workers", str(active_item.worker_count)),
        ("Engine", active_item.render_engine),
        # ("Render Mode", active_item.launch_mode),
        ("Frames", active_item.frames),
        ("Resolution", f"{active_item.resolution_x} x {active_item.resolution_y}"),
        ("Samples", active_item.samples),
        ("File Format", active_item.file_format),
        ("Output Path", active_item.output_path),
        ("Script Name", active_item.script_filename),
        ("Script Directory", active_item.export_path),
    ]

    # Populate the collection
    for name, value in properties_to_show:
        if value:  # Only add non-empty values
            prop_item = self.active_item_properties.add()
            prop_item.name = name
            prop_item.value = value
            prop_item.tooltip = f"{name}: {value}"


class RECOM_PG_RecentBlendFile(PropertyGroup):
    path: StringProperty(name="Blend File Path")


class RECOM_PG_VisiblePanels(PropertyGroup):
    """Visibility settings for addon panels"""

    external_scene: BoolProperty(name="Blend File", default=True, update=lambda self, context: redraw_ui())
    override_settings: BoolProperty(name="Override Settings", default=True, update=lambda self, context: redraw_ui())
    preferences: BoolProperty(
        name="Render Preferences",
        default=True,
        update=lambda self, context: redraw_ui(),
    )
    ocio: BoolProperty(name="OCIO Environment", default=False)
    history: BoolProperty(name="Export History", default=True, update=lambda self, context: redraw_ui())


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
#################################################


class RECOM_Preferences(AddonPreferences):
    """Preferences for the addon settings"""

    bl_idname = __package__

    # Misc
    #################################

    launch_mode: EnumProperty(
        items=[
            (MODE_SINGLE, "Still", "Render a single frame"),
            (MODE_SEQ, "Sequence", "Render a full frame range"),
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
    debug_mode: BoolProperty(
        name="Enable Console Logging",
        description="Print add-on status and debug messages to the system console",
        default=False,
        update=on_logging_pref_changed,
    )
    visible_panels: PointerProperty(type=RECOM_PG_VisiblePanels)

    command_line_preview: StringProperty(name="Preview", default="")

    # Ext blend file
    recent_blend_files: CollectionProperty(type=RECOM_PG_RecentBlendFile)
    show_scene_info_list: BoolProperty(
        name="Show List",
        default=False,
    )

    # Overrides
    custom_variables: CollectionProperty(type=RECOM_PG_CustomVariable)
    active_custom_variable_index: IntProperty(default=-1, name="Active Custom Variable Index")
    use_underscore_separator: BoolProperty(
        name="Use Underscore Separator",
        description="Automatically inserts an underscore between the base path and the added variable",
        default=True,
    )
    override_import_settings: PointerProperty(type=RECOM_PG_OverrideImportSettings)

    # Render History
    render_history: CollectionProperty(type=RECOM_PG_RenderHistoryItem)
    active_render_history_index: IntProperty(
        default=-1,
        name="Active Render History Index",
        update=update_active_render_history_properties,
    )
    active_item_properties: CollectionProperty(type=RECOM_PG_PropertyItem)
    item_properties_index: IntProperty(default=-1)

    # Cycles Devices
    compute_device_type: EnumProperty(
        name="Compute Device Type",
        description="Device to use for computation (rendering with Cycles)",
        default=0,
        items=lambda self, context: get_device_types_items(self, context),
        update=lambda self, context: redraw_ui(),
    )
    devices: CollectionProperty(type=RECOM_PG_DeviceSettings)
    show_device_id: BoolProperty(
        name="Show Device ID",
        default=False,
        update=lambda self, context: redraw_ui(),
    )
    devices_ini: BoolProperty(
        name="Get Devices from Cycles",
        description="Create a local copy of devices",
        default=False,
        update=lambda self, context: redraw_ui(),
    )

    # Parallel Rendering
    manage_cycles_devices: BoolProperty(
        name="Manage Compute Devices",
        description="Configures Cycles render compute devices, only used for the exported render scripts",
        default=False,
    )
    device_parallel: BoolProperty(
        name="Parallel Rendering",
        description="Launch separate render process for each device",
        default=False,
    )
    frame_allocation: EnumProperty(
        name="Frame Mode",
        items=[
            (
                "SEQUENTIAL",
                "Sequential",
                "Each device renders the full frame range.\n"
                " * Automatically disables overwriting and enables placeholders.",
            ),
            ("FRAME_SPLIT", "Split", "Divide frame range among devices"),
        ],
        default="FRAME_SPLIT",
        description="How frames are distributed across rendering devices",
    )
    parallel_delay: FloatProperty(
        name="Multi-Process Start Delay",
        description="Delay before starting each additional render process to avoid resource conflicts",
        min=0.0,
        default=1.0,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )
    multiple_backends: BoolProperty(
        name="Multi-Backend",
        description="Render using enabled devices from different backends",
        default=False,
    )
    combine_cpu_with_gpus: BoolProperty(
        name="CPU & GPU Rendering",
        default=True,
        description="Enable to assign the CPU to a separate render job and keep it out of GPU tasks",
    )
    cpu_threads_limit: IntProperty(
        name="Thread Limit",
        default=0,
        min=0,
        description="Maximum threads for rendering jobs",
    )
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
        max=32,
        soft_max=8,
    )

    # Render Options
    #################################

    keep_terminal_open: BoolProperty(
        name="Keep Terminal Open",
        description="Prevents the terminal window from closing automatically after the render finishes",
        default=True,
    )
    auto_save_before_render: BoolProperty(
        name="Auto‑Save Before Render",
        description="Save the current blend file before export, if it has unsaved changes",
        default=False,
    )
    write_still: BoolProperty(
        name="Write Still",
        default=True,
        description="Write Image, Save the rendered image to the output path",
    )
    track_render_time: BoolProperty(
        name="Track Render Time",
        description="Show render progress in the console.\n"
        "Displays progress bar, percentage, frame count, and estimated time remaining",
        default=False,
    )

    # Filename
    default_render_filename: StringProperty(
        name="Default Output Filename",
        description="Name used for rendered output files if the filename is empty",
        default="render",
    )
    frame_length_digits: IntProperty(
        name="Frame Number Padding",
        default=4,
        min=1,
        soft_min=3,
        soft_max=6,
        description="Number of digits used to pad frame numbers in output filenames.\n"
        " * Used when the filename does not contain # characters",
    )
    filename_separator: EnumProperty(
        name="File Separator",
        description="Separator between output filename and frame numbers.\n"
        " * Used when the filename does not contain # characters",
        items=[
            ("DOT", "Dot (.)", "Filename.####"),
            ("UNDERSCORE", "Underscore (_)", "Filename_####"),
        ],
        default="DOT",
    )
    # Script Name
    use_blend_name_in_script: BoolProperty(
        name="Include Blend Name",
        description="Append the blend file name to the generated script filenames",
        default=True,
    )
    use_render_type_in_script: BoolProperty(
        name="Include Render Type",
        description="Append the render mode to the generated script filenames",
        default=False,
    )
    use_export_date_in_script: BoolProperty(
        name="Include Export Date",
        description="Append the export date to the generated script filenames",
        default=False,
    )
    use_frame_range_in_script: BoolProperty(
        name="Include Frame Range",
        description="Append the active frame range or list to the generated script filenames",
        default=False,
    )
    custom_script_tag: BoolProperty(
        name="Custom Tag",
        description="Add custom text to script filenames",
        default=False,
    )
    custom_script_text: StringProperty(
        name="Custom Tag Text",
        description="Custom text appended to script filenames",
        default="",
        maxlen=50,
        update=lambda self, context: redraw_ui(),
    )

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
            ("SELECT_DIR", "Select", "Folder chosen in the export dialog"),
            ("BLEND_DIR", "Blend Path", "Folder next to the .blend file"),
            ("CUSTOM_PATH", "Custom", "User‑defined folder"),
        ],
        default="SELECT_DIR",
        update=lambda self, context: redraw_ui(),
    )
    custom_export_path: StringProperty(
        name="Custom Export Path",
        description="Manually set the folder to open after export",
        subtype="DIR_PATH",
        default="",
        update=lambda self, context: redraw_ui(),
    )
    export_scripts_subfolder: BoolProperty(
        name="Scripts Subfolder",
        description="Save the script files into a subfolder",
        default=False,
    )
    export_scripts_folder_name: StringProperty(
        name="Export Scripts Folder",
        description="Folder name for export render scripts",
        default="render_scripts",
    )

    # Render Command line
    #################################

    add_command_line_args: BoolProperty(
        name="Use Command Line Arguments",
        description="Add additional command line arguments for render",
        default=True,
    )
    custom_command_line_args: StringProperty(
        name="Command Line Arguments",
        description="Additional command line arguments to pass to Blender during render",
        default="--log render",
        update=lambda self, context: redraw_ui(),
    )

    # Render logging
    log_to_file: BoolProperty(
        name="Log to File",
        default=False,
        description="Save render logs to a file.\n * Appends: --log-file <filepath>",
    )
    log_to_file_location: EnumProperty(
        name="Log Directory",
        items=[
            (
                "EXECUTION_FILES",
                "Scripts Path",
                "Save logs files in render scripts directory",
            ),
            ("BLEND_PATH", "Blend File Path", "Save logs files next to blend file"),
            ("CUSTOM_PATH", "Custom Path", "Specify custom log folder location"),
        ],
        default="EXECUTION_FILES",
    )
    save_to_log_folder: BoolProperty(
        name="Save to Logs Folder",
        default=False,
        description="Save logs in a dedicated 'logs' folder",
    )
    log_custom_path: StringProperty(
        name="Save Logs Path",
        subtype="DIR_PATH",
        description="Directory to save log files when using custom location",
    )
    logs_folder_name: StringProperty(
        name="Logs Subfolder",
        description="Folder name for render log files",
        default="logs",
    )

    # Append Scripts
    append_python_scripts: BoolProperty(
        name="Append Python Scripts",
        description="Add additional python scripts to run during rendering.\n * Appends: --python <filepath>",
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

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text="Visible Panels")
        col = layout.column(align=True)
        col = col.column(heading="Settings")
        col.prop(self.visible_panels, "ocio")

        layout.label(text="Debug")
        col = layout.column()
        col.prop(self, "debug_mode", text="Console Logging")


classes = (
    RECOM_PG_DeviceSettings,
    RECOM_PG_OverrideImportSettings,
    RECOM_PG_RecentBlendFile,
    RECOM_PG_RenderHistoryItem,
    RECOM_PG_PropertyItem,
    RECOM_PG_ScriptEntry,
    RECOM_PG_CustomVariable,
    RECOM_PG_VisiblePanels,
    RECOM_Preferences,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if prefs and not prefs.devices_ini:
            refresh_cycles_devices(prefs, bpy.context, sync_type=True)
            prefs.devices_ini = True
    except Exception as e:
        log.warning("Could not initialize Cycles devices: %s", e)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
