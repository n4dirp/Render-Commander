"""Properties used by the 'Overrides' system"""

import logging

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

from ..utils.helpers import (
    calculate_auto_height,
    calculate_auto_width,
    redraw_ui,
    resolve_blender_path,
)

log = logging.getLogger(__name__)


def data_path_search_callback(self, context, edit_text):
    """Provides autocomplete suggestions for Blender data paths."""
    text = edit_text.strip()
    if not text:
        return [
            "bpy.context.scene",
            "bpy.context.scene.render",
            "bpy.context.scene.cycles",
            "bpy.context.scene.eevee",
            "bpy.context.view_layer",
        ]

    try:
        normalized, _ = resolve_blender_path(text)
    except Exception:
        normalized = text  # Keep user input as fallback

    items = []
    if "." in normalized:
        base_path, prefix = normalized.rsplit(".", 1)
        try:
            _, base_obj = resolve_blender_path(base_path)
            if base_obj is not None:
                props = (
                    [p.identifier for p in base_obj.bl_rna.properties]
                    if hasattr(base_obj, "bl_rna")
                    else [p for p in dir(base_obj) if not p.startswith("_")]
                )
                items = [f"{base_path}.{p}" for p in props if p.startswith(prefix)]
        except Exception:
            pass

    return items[:30] if items else [text]


class RECOM_PG_DataPathOverride(PropertyGroup):
    """Stores arbitrary data path overrides entered by the user"""

    name: StringProperty(name="Name", default="Data Path Override")
    data_path: StringProperty(
        name="Data Path",
        description="The Python path to the blender property",
        update=lambda self, context: redraw_ui(),
    )
    prop_type: EnumProperty(
        name="Type",
        items=[
            ("BOOL", "Boolean", ""),
            ("INT", "Integer", ""),
            ("FLOAT", "Float", ""),
            ("STRING", "String", ""),
            ("VECTOR_3", "Vector (3D)", ""),
            ("COLOR_4", "Color (RGBA)", ""),
        ],
        default="FLOAT",
    )
    value_bool: BoolProperty(name="Value")
    value_int: IntProperty(name="Value")
    value_float: FloatProperty(name="Value")
    value_string: StringProperty(name="Value")
    value_vector_3: FloatVectorProperty(name="Value", size=3)
    value_color_4: FloatVectorProperty(name="Value", size=4, subtype="COLOR", min=0.0, max=1.0)


class RECOM_PG_CyclesRenderOverrides(PropertyGroup):
    """Stores Cycles render override settings"""

    device_override: BoolProperty(
        name="Override Compute Device",
        description="Override the compute device used for Cycles rendering",
        default=False,
    )
    device: EnumProperty(
        name="",
        items=[
            ("CPU", "CPU", "Use CPU for rendering"),
            ("GPU", "GPU", "Use GPU compute devices for rendering"),
        ],
        default="GPU",
        description="Device to use for rendering",
    )

    # Sampling
    sampling_override: BoolProperty(
        name="Override Sampling",
        description="Override Cycles sampling settings",
        default=False,
    )
    sampling_mode: EnumProperty(
        name="Mode",
        items=[
            (
                "FACTOR",
                "Factor",
                "Multiply the scene's current sampling settings by a factor",
            ),
            ("CUSTOM", "Custom", "Set absolute sampling values manually"),
        ],
        default="FACTOR",
        description="Choose how to override sampling values",
        update=lambda self, context: redraw_ui(),
    )
    sampling_factor: FloatProperty(
        name="Quality Factor",
        default=100.0,
        min=1.0,
        soft_max=200.0,
        precision=0,
        step=10,
        subtype="PERCENTAGE",
        description="Multiplier for the scene's sampling settings as a percentage",
    )
    use_adaptive_sampling: BoolProperty(
        name="Use Adaptive Sampling",
        description="Automatically reduce the number of samples per pixel based on estimated noise level",
        default=True,
    )
    adaptive_threshold: FloatProperty(
        name="Adaptive Sampling Threshold",
        min=0.0,
        max=1.0,
        soft_min=0.001,
        default=0.015,
        precision=4,
        description=(
            "Noise level step to stop sampling at, lower values reduce noise at the cost of render time.\n"
            "Zero for automatic setting based on number of AA samples."
        ),
    )
    samples: IntProperty(
        name="Samples",
        default=2048,
        min=1,
        max=32768,
        description="Number of samples to render for each pixel",
        update=lambda self, context: redraw_ui(),
    )
    adaptive_min_samples: IntProperty(
        name="Adaptive Min Samples",
        description=(
            "Minimum AA samples for adaptive sampling, to discover noisy features before stopping sampling.\n"
            "Zero for automatic setting based on noise threshold."
        ),
        min=0,
        max=4096,
        default=0,
    )
    time_limit: FloatProperty(
        name="Time Limit",
        description="Limit the render time (excluding synchronization time).Zero disables the limit.",
        min=0.0,
        default=0.0,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )

    # Denoise
    denoising_override: BoolProperty(
        name="Override Denoising",
        description="Override Cycles denoising settings",
        default=False,
    )
    use_denoising: BoolProperty(
        name="Use Denoising",
        default=True,
        description="Toggle denoising during rendering",
    )
    denoiser: EnumProperty(
        name="Denoiser",
        description="Denoiser to use",
        items=[
            ("OPTIX", "OptiX", "Use OptiX AI denoiser"),
            ("OPENIMAGEDENOISE", "OIDN", "Use Intel Open Image Denoise"),
        ],
        default="OPENIMAGEDENOISE",
    )
    denoising_input_passes: EnumProperty(
        name="Passes",
        description="Input passes used by the denoiser",
        items=[
            ("RGB", "None", "Use only the color pass"),
            ("RGB_ALBEDO", "Albedo", "Use color and albedo passes"),
            ("RGB_ALBEDO_NORMAL", "Albedo and Normal", "Use all passes"),
        ],
        default="RGB_ALBEDO_NORMAL",
    )
    denoising_prefilter: EnumProperty(
        name="Prefilter",
        description="Prefilter for auxiliary passes",
        items=[
            ("NONE", "None", "No prefiltering"),
            ("FAST", "Fast", "Fast prefiltering (less accurate)"),
            ("ACCURATE", "Accurate", "Better quality prefiltering"),
        ],
        default="ACCURATE",
    )
    denoising_quality: EnumProperty(
        name="Quality",
        description="Overall denoise quality",
        items=[
            ("HIGH", "High", "High Quality"),
            ("BALANCED", "Balanced", "Balanced between performance and quality"),
            ("FAST", "Fast", "High performance"),
        ],
        default="HIGH",
    )
    denoising_use_gpu: BoolProperty(
        name="Use GPU",
        default=True,
        description="Enable GPU acceleration for denoising",
    )

    # Performance
    performance_override: BoolProperty(
        name="Override Performance",
        description="Override Cycles performance settings",
        default=False,
    )
    use_tiling: BoolProperty(
        name="Use Tiling",
        default=True,
        description="Enable tiling for memory optimization",
    )
    tile_size: IntProperty(
        name="Tile Size",
        default=2048,
        min=8,
        description="Set the tile size for rendering (in pixels)",
    )
    use_spatial_splits: BoolProperty(
        name="Use Spatial Splits",
        default=True,
        description="Enable spatial splits for BVH optimization",
    )
    use_compact_bvh: BoolProperty(
        name="Use Compact BVH",
        default=False,
        description="Enable compact BVH for memory efficiency",
    )
    persistent_data: BoolProperty(
        name="Persistent Data",
        default=True,
        description="Enable persistent data for faster re-rendering",
    )


class RECOM_PG_EEVEERenderOverrides(PropertyGroup):
    """Stores EEVEE render override settings"""

    samples: IntProperty(
        name="Samples",
        default=256,
        min=1,
        description="EEVEE TAA render samples",
        update=lambda self, context: redraw_ui(),
    )


class RECOM_PG_OverrideSettings(PropertyGroup):
    """Stores override settings"""

    # Data Path Overrides
    property_path_input: StringProperty(
        name="Blender Data Path",
        description=("Search for a Blender data path to override.\nExample: bpy.context.scene.render.use_simplify"),
        search=data_path_search_callback,
    )
    use_data_path_overrides: BoolProperty(
        name="Use Data Path Overrides",
        default=False,
        description="Enable data path property overrides",
    )
    data_path_overrides: CollectionProperty(type=RECOM_PG_DataPathOverride)
    active_data_path_index: IntProperty(default=0)

    # Cycles Render
    cycles_override: BoolProperty(name="Override Cycles Render", default=True)
    cycles: PointerProperty(type=RECOM_PG_CyclesRenderOverrides)

    # EEVEE Render
    eevee_override: BoolProperty(
        name="Override EEVEE Render",
        description="Override EEVEE render sampling settings",
        default=False,
    )
    eevee: PointerProperty(type=RECOM_PG_EEVEERenderOverrides)

    # Frame Range
    frame_range_override: BoolProperty(
        name="Override Frame Range",
        description="Override the animation frame range",
        default=False,
    )
    frame_current: IntProperty(
        name="",
        description="Specify the exact frame number to render",
        default=1,
        min=0,
    )

    def _update_frame_range(self, context):
        """Ensure frame_start is always less than or equal to frame_end."""
        if self.frame_start > self.frame_end:
            self.frame_end = self.frame_start

    frame_start: IntProperty(
        name="",
        description="Define the start frame for animation rendering",
        default=1,
        min=0,
        update=_update_frame_range,
    )
    frame_end: IntProperty(
        name="",
        description="Define the end frame for animation rendering",
        default=250,
        min=0,
        update=_update_frame_range,
    )
    frame_step: IntProperty(
        name="",
        description="Define the interval between frames to render",
        default=1,
        min=1,
    )
    fps: IntProperty(
        name="",
        description="Define the interval between frames to render",
        default=30,
        min=1,
    )

    # Resolution
    format_override: BoolProperty(
        name="Override Format",
        description="Override resolution and render scale settings",
        default=False,
    )
    resolution_override: BoolProperty(
        name="Set Resolution",
        default=True,
    )

    def _update_auto_resolution_cache(self, context):
        """Recompute auto‑width/auto‑height when anything that affects them changes."""
        mode_changed = self.resolution_mode != getattr(self, "_cached_res_mode", None)

        # If resolution inputs changed – recompute as well
        res_x_changed = self.resolution_x != getattr(self, "_cached_res_x", None)
        res_y_changed = self.resolution_y != getattr(self, "_cached_res_y", None)

        if mode_changed or res_x_changed or res_y_changed:
            # Store the current values for next comparison
            self._cached_res_mode = self.resolution_mode
            self._cached_res_x = self.resolution_x
            self._cached_res_y = self.resolution_y

            # Recalculate based on the new mode
            if self.resolution_mode == "SET_WIDTH":
                self.cached_auto_height = calculate_auto_height(context)
            elif self.resolution_mode == "SET_HEIGHT":
                self.cached_auto_width = calculate_auto_width(context)
            else:
                # No auto calculation needed for CUSTOM mode
                self.cached_auto_width = self.resolution_x
                self.cached_auto_height = self.resolution_y

    resolution_mode: EnumProperty(
        name="",
        items=[
            ("CUSTOM", "Custom", "Manually set both width and height"),
            (
                "SET_WIDTH",
                "Set X",
                "Specify the width; height will be calculated automatically to maintain the scene's aspect ratio.",
            ),
            (
                "SET_HEIGHT",
                "Set Y",
                "Specify the height; width will be calculated automatically to maintain the scene's aspect ratio.",
            ),
        ],
        default="CUSTOM",
        description="Choose how resolution is configured",
        update=_update_auto_resolution_cache,
    )
    resolution_preview: IntProperty(
        name="Auto Calculate Resolution",
        default=1000,
        min=1,
        description="Auto set the resolution maintaining aspect ratio from scene",
        subtype="PIXEL",
    )
    resolution_x: IntProperty(
        name="Resolution X",
        default=1920,
        min=1,
        description="Horizontal resolution in pixels",
        subtype="PIXEL",
        update=_update_auto_resolution_cache,
    )
    resolution_y: IntProperty(
        name="Resolution Y",
        default=1080,
        min=1,
        description="Vertical resolution in pixels",
        subtype="PIXEL",
        update=_update_auto_resolution_cache,
    )
    cached_auto_width: IntProperty(
        name="Cached Auto X",
        default=0,
        description="Cached width that keeps the aspect ratio when SET_HEIGHT is active",
        subtype="PIXEL",
    )
    cached_auto_height: IntProperty(
        name="Cached Auto Y",
        default=0,
        description="Cached height that keeps the aspect ratio when SET_WIDTH is active",
        subtype="PIXEL",
    )
    custom_render_scale: FloatProperty(
        name="Custom Render Scale",
        default=100.0,
        min=1.0,
        soft_max=200.0,
        precision=1,
        step=10,
        description="Enter a custom scale factor %",
        subtype="PERCENTAGE",
    )

    # Overscan
    use_overscan: BoolProperty(
        name="Use Resolution Overscan",
        description="Add extra pixels or a percentage around the final image",
        default=False,
    )
    overscan_type: EnumProperty(
        name="Overscan Type",
        items=[
            ("PERCENTAGE", "Percentage", "Add percentage of the image size"),
            ("PIXELS", "Pixels", "Add an absolute number of pixels"),
        ],
        description="How the overscan is calculated.",
        default="PERCENTAGE",
    )
    overscan_percent: FloatProperty(
        name="Overscan %",
        description="Percentage to add around the image",
        min=0.0,
        soft_max=30.0,
        default=5.0,
        precision=0,
        subtype="PERCENTAGE",
    )
    overscan_uniform: BoolProperty(
        name="Uniform Overscan",
        description="Apply the same pixel value to both width and height",
        default=True,
    )
    overscan_percent_width: FloatProperty(
        name="Overscan % X",
        description="Percentage to add to the left and right sides",
        min=0.0,
        soft_max=30.0,
        default=5.0,
        precision=0,
        subtype="PERCENTAGE",
    )
    overscan_percent_height: FloatProperty(
        name="Overscan % Y",
        description="Percentage to add to the top and bottom sides",
        min=0.0,
        soft_max=30.0,
        default=5.0,
        precision=0,
        subtype="PERCENTAGE",
    )
    overscan_width: IntProperty(
        name="Width Overscan",
        description="Extra pixels added to the left and right sides",
        min=0,
        default=50,
        subtype="PIXEL",
    )
    overscan_height: IntProperty(
        name="Height Overscan",
        description="Extra pixels added to the top and bottom sides",
        min=0,
        default=50,
        subtype="PIXEL",
    )

    # Camera
    cameras_override: BoolProperty(
        name="Camera Settings",
        description="Enable or disable all camera overrides",
        default=False,
    )
    override_dof: BoolProperty(
        name="Override Depth of Field",
        description="Override depth of field settings on all cameras in the scene",
        default=False,
    )
    use_dof: EnumProperty(
        name="",
        items=[
            (
                "DISABLED",
                "Disabled",
                "Disable depth of field on all cameras in the scene",
            ),
            ("ENABLED", "Enabled", "Use depth of field on all cameras in the scene"),
        ],
        default="DISABLED",
    )
    # Lens Shift
    camera_shift_override: BoolProperty(
        name="Add Lens Shift",
        description="Apply shift settings to all cameras in the scene",
        default=False,
    )
    camera_shift_x: FloatProperty(
        name="Shift X",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
        precision=3,
        description="Camera horizontal shift. \nPositive = Right / Negative = Left.",
    )
    camera_shift_y: FloatProperty(
        name="Shift Y",
        default=0.0,
        soft_min=-1.0,
        soft_max=1.0,
        precision=3,
        description="Camera vertical shift. \nPositive = Up / Negative = Down.",
    )

    # File Format
    file_format_override: BoolProperty(
        name="Override Output File Format",
        description="Override the output image file format",
        default=False,
    )
    file_format: EnumProperty(
        name="Format",
        items=[
            (
                "OPEN_EXR_MULTILAYER",
                "Multi-Layer EXR",
                "Output image in OpenEXR MultiLayer format",
            ),
            ("OPEN_EXR", "OpenEXR (.exr)", "Output image in OpenEXR format"),
            ("PNG", "PNG (.png)", "Output image in PNG format"),
            ("JPEG", "JPEG (.jpg)", "Output image in JPEG format"),
            ("TIFF", "TIFF (.tif)", "Output image in TIFF format"),
        ],
        default="OPEN_EXR_MULTILAYER",
        description="Select the output format for rendered images",
    )
    codec: EnumProperty(
        name="Codec",
        items=[
            ("ZIP", "ZIP", "Lossless compression using DEFLATE"),
            ("PIZ", "PIZ", "Lossless compression using PIZ algorithm"),
            ("DWAA", "DWAA (lossy)", "Deep image format (lossy)"),
            ("DWAB", "DWAB (lossy)", "Deep image format (lossy)"),
            ("PXR24", "Pxr24 (lossy)", "Legacy format for Pixar workflows"),
        ],
        default="DWAA",
        description="Codec for OpenEXR/TIFF output",
    )
    jpeg_quality: IntProperty(
        name="Quality",
        default=85,
        min=1,
        max=100,
        description="Quality for JPEG output (1-100)",
    )

    def _get_color_depth_items(self, context):
        """Get color depth options based on output format."""
        file_format = self.file_format

        if file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
            return [
                ("16", "Float (Half)", "16-bit color channels"),
                ("32", "Float (Full)", "32-bit color channels"),
            ]

        return [
            ("8", "8", "8-bit color channels"),
            ("16", "16", "16-bit color channels"),
        ]

    color_depth: EnumProperty(
        name="Color Depth",
        items=_get_color_depth_items,
        default=0,
        description="Bit depth per channel",
    )
    use_preview: BoolProperty(
        name="",
        description="Save a JPG preview in the same directory",
        default=False,
    )

    # Output Path
    output_path_override: BoolProperty(
        name="Override Output Path",
        description="Override the output directory and filename",
        default=False,
    )
    output_directory: StringProperty(
        name="Output Directory",
        default="/tmp\\",
        subtype="DIR_PATH",
        options={"OUTPUT_PATH", "PATH_SUPPORTS_BLEND_RELATIVE"},
        description="Specify the directory where rendered files will be saved",
        update=lambda self, context: redraw_ui(),
    )
    output_filename: StringProperty(
        name="Output Filename",
        subtype="FILE_NAME",
        description="Specify the filename pattern for rendered files",
        update=lambda self, context: redraw_ui(),
    )
    variable_insert_target: EnumProperty(
        name="Insert Into",
        items=[
            (
                "DIRECTORY",
                "Directory",
                "Insert variable into the output directory path string",
            ),
            ("FILENAME", "Filename", "Insert variable into the output filename string"),
        ],
        default="FILENAME",
    )
    show_path_variables: BoolProperty(
        name="Show Path Variables",
        default=False,
        update=lambda self, context: redraw_ui(),
    )

    # Motion Blur
    motion_blur_override: BoolProperty(
        name="Override Motion Blur",
        description="Override motion blur settings",
        default=False,
    )
    use_motion_blur: BoolProperty(
        name="Enable Motion Blur",
        default=True,
        description="Use multi-sampled 3D scene motion blur",
    )
    motion_blur_position: EnumProperty(
        name="Motion Blur Position",
        items=[
            ("CENTER", "Center of Frame", "Based on the center of the frame"),
            ("START", "Start of Frame", "Based on the start of the frame"),
            ("END", "End of Frame", "Based on the end of the frame"),
        ],
        default="CENTER",
    )
    motion_blur_shutter: FloatProperty(
        name="Shutter Length",
        default=0.5,
        min=0.0,
        max=1.0,
    )

    # Compositor
    compositor_override: BoolProperty(
        name="Override Compositor Settings",
        description="Override compositor settings",
        default=False,
    )
    use_compositor: BoolProperty(
        name="Use Compositor Nodes",
        default=True,
        description="Enable the compositing node tree",
    )
    compositor_device: EnumProperty(
        name="Compositor Device",
        items=[
            ("CPU", "CPU", "Use CPU for compositing"),
            ("GPU", "GPU", "Use GPU for compositing"),
        ],
        default="GPU",
        description="Set the device used for compositing",
    )
    compositor_disable_output_files: BoolProperty(
        name="Bypass File Outputs",
        default=False,
        description="Muted all File Output nodes in the compositor",
    )

    # FPS
    use_fps_converter: BoolProperty(
        name="Enable FPS Converter",
        default=False,
        description="Apply time remapping to convert frame rate",
    )
    target_fps: EnumProperty(
        name="Target",
        items=[
            ("6", "6 fps", ""),
            ("8", "8 fps", ""),
            ("12", "12 fps", ""),
            ("24", "24 fps", ""),
            ("25", "25 fps", ""),
            ("30", "30 fps", ""),
            ("50", "50 fps", ""),
            ("60", "60 fps", ""),
            ("120", "120 fps", ""),
            ("240", "240 fps", ""),
            ("CUSTOM", "Custom", "Enter a custom frame rate"),
        ],
        default="60",
        description="The desired output frame rate",
    )
    custom_fps: IntProperty(
        name="Custom FPS",
        default=60,
        min=1,
        soft_max=240,
        description="Custom frame rate value",
    )
    preserve_motion_blur: BoolProperty(
        name="Preserve Motion Blur Time",
        default=False,
        description="Adjust motion blur shutter speed to match the absolute time of the original framerate",
    )


classes = (
    RECOM_PG_CyclesRenderOverrides,
    RECOM_PG_EEVEERenderOverrides,
    RECOM_PG_DataPathOverride,
    RECOM_PG_OverrideSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
