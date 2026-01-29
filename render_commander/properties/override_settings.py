# ./properties/properties.py

import logging
import os
from pathlib import Path

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    PointerProperty,
    IntProperty,
    EnumProperty,
    FloatProperty,
)
from bpy.types import PropertyGroup

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    replace_variables,
    redraw_ui,
    calculate_auto_width,
    calculate_auto_height,
    get_default_render_output_path,
)

log = logging.getLogger(__name__)


class RECOM_PG_CyclesRenderOverrides(PropertyGroup):
    """Stores Cycles render override settings"""

    device_override: BoolProperty(
        name="Override Compute Device",
        default=False,
    )
    device: EnumProperty(
        name="",
        items=[
            (
                "CPU",
                "CPU",
                "Use CPU for rendering",
            ),
            (
                "GPU",
                "GPU",
                "Use GPU compute devices for rendering",
            ),
        ],
        default="GPU",
        description="Device to use for rendering",
    )

    # Sampling
    sampling_override: BoolProperty(
        name="Override Sampling",
        default=False,
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
        description="Noise level step to stop sampling at, lower values reduce noise at the cost of render time.\nZero for automatic setting based on number of AA samples.",
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
        description="Minimum AA samples for adaptive sampling, to discover noisy features before stopping sampling.\nZero for automatic setting based on noise threshold.",
        min=0,
        max=4096,
        default=0,
    )
    time_limit: FloatProperty(
        name="Time Limit",
        description="Limit the render time (excluding synchronization time). " "Zero disables the limit.",
        min=0.0,
        default=0.0,
        step=100.0,
        unit="TIME_ABSOLUTE",
    )

    # Denoise
    use_denoising: BoolProperty(
        name="Use Denoising",
        default=False,
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
    denoising_store_passes: BoolProperty(
        name="Enable Denoising Data",
        default=False,
        description="Store the denoising feature passes and noisy image.\nThe passes adapt to the denoiser selected for rendering.",
    )

    # Light Paths
    light_path_override: BoolProperty(name="Override Light Paths", default=False)
    max_bounces: IntProperty(
        name="Max Bounces",
        description="Maximum number of light bounces",
        default=12,
        min=0,
        max=1024,
        update=lambda self, context: redraw_ui(),
    )
    diffuse_bounces: IntProperty(
        name="Diffuse",
        description="Maximum number of diffuse light bounces. Affects how light scatters off matte surfaces.",
        default=3,
        min=0,
        max=1024,
    )
    glossy_bounces: IntProperty(
        name="Glossy",
        description="Maximum number of glossy light bounces. Influences reflections on shiny surfaces.",
        default=4,
        min=0,
        max=1024,
    )
    transmission_bounces: IntProperty(
        name="Transmission",
        description="Maximum number of transmission bounces for transparent and refractive surfaces like glass",
        default=12,
        min=0,
        max=1024,
    )
    volume_bounces: IntProperty(
        name="Volume",
        description="Maximum number of light bounces inside volumetric objects (e.g., smoke, fog)",
        default=0,
        min=0,
        max=1024,
    )
    transparent_bounces: IntProperty(
        name="Transparent",
        description="Maximum number of transparent bounces (used for materials like glass or alpha-mapped textures)",
        default=8,
        min=0,
        max=1024,
    )
    sample_clamp_direct: FloatProperty(
        name="Clamp Direct",
        description="Clamp the brightness of directly-lit samples to reduce fireflies (noise). Lower values give more clamping.",
        default=32.0,
        min=0.0,
        max=1024.0,
    )
    sample_clamp_indirect: FloatProperty(
        name="Clamp Indirect",
        description="Clamp the brightness of indirectly-lit samples to reduce fireflies. Especially useful in complex lighting scenarios.",
        default=10.0,
        min=0.0,
        max=1024.0,
    )
    caustics_reflective: BoolProperty(
        name="Reflective Caustics",
        description="Use reflective caustics, resulting in a brighter image (more noise but added realism)",
        default=True,
    )
    caustics_refractive: BoolProperty(
        name="Refractive Caustics",
        description="Use refractive caustics, resulting in a brighter image (more noise but added realism)",
        default=True,
    )
    blur_glossy: FloatProperty(
        name="Filter Glossy",
        description="Adaptively blur glossy shaders after blurry bounces, " "to reduce noise at the cost of accuracy",
        min=0.0,
        max=10.0,
        default=1.0,
    )

    # Performance
    performance_override: BoolProperty(
        name="Override Performance",
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
    use_shadows: BoolProperty(
        name="Shadows",
        default=True,
        description="Enable Shadows for EEVEE",
    )
    shadow_ray_count: IntProperty(
        name="Shadow Ray Count",
        default=1,
        min=1,
        max=4,
        description="Number of rays for shadow calculations",
    )
    shadow_step_count: IntProperty(
        name="Shadow Step Count",
        default=12,
        min=1,
        max=16,
        description="Steps for shadow sampling",
    )
    use_raytracing: BoolProperty(
        name="Use Raytracing",
        default=True,
        description="Enable Raytracing for EEVEE",
    )
    ray_tracing_method: EnumProperty(
        name="Raytracing Method",
        items=[
            ("SCREEN", "Screen-Trace", ""),
            ("PROBE", "Light Probe", ""),
        ],
        default="SCREEN",
        description="Raytracing method for EEVEE",
    )
    ray_tracing_resolution: EnumProperty(
        name="Raytracing Resolution",
        items=[
            ("1", "1:1", ""),
            ("2", "1:2", ""),
            ("4", "1:4", ""),
            ("8", "1:8", ""),
            ("16", "1:16", ""),
        ],
        default="2",
        description="Resolution scale for raytracing",
    )
    ray_tracing_denoise: BoolProperty(
        name="Denoise",
        default=True,
        description="Enable denoising for raytraced effects",
    )
    ray_tracing_denoise_temporal: BoolProperty(
        name="Temporal Accumulation",
        default=False,
        description="Accumulate samples by reprojecting last tracing results",
    )
    fast_gi: BoolProperty(
        name="Fast GI Approximation",
        default=True,
        description="Use fast GI approximation for faster rendering",
    )
    trace_max_roughness: FloatProperty(
        name="Threshold",
        default=0.5,
        min=0.0,
        max=1.0,
        description="Raytrace Max Roughness",
    )
    fast_gi_resolution: EnumProperty(
        name="Fast GI Resolution",
        items=[
            ("1", "1:1", ""),
            ("2", "1:2", ""),
            ("4", "1:4", ""),
            ("8", "1:8", ""),
            ("16", "1:16", ""),
        ],
        default="2",
        description="Resolution scale for GI",
    )
    fast_gi_step_count: IntProperty(
        name="Fast GI Step Count",
        default=8,
        min=1,
        max=16,
        description="Steps for GI sampling",
    )
    fast_gi_distance: FloatProperty(
        name="Fast GI Distance",
        default=0.0,
        min=0.0,
        description="",
        unit="LENGTH",
    )
    volumetric_tile_size: EnumProperty(
        name="Volume Resolution",
        items=[
            ("1", "1:1", ""),
            ("2", "1:2", ""),
            ("4", "1:4", ""),
            ("8", "1:8", ""),
            ("16", "1:16", ""),
        ],
        default="8",
        description="Control volume quality",
    )
    volume_samples: IntProperty(
        name="Volume Steps",
        default=64,
        min=1,
        max=256,
        description="Number of steps for volumetric effects",
    )


class RECOM_PG_OverrideSettings(PropertyGroup):
    """Stores override settings"""

    # Cycles Render
    cycles_override: BoolProperty(name="Override Cycles Render", default=True)
    cycles: PointerProperty(type=RECOM_PG_CyclesRenderOverrides)

    # EEVEE Render
    eevee_override: BoolProperty(
        name="Override EEVEE Render",
        default=False,
    )
    eevee: PointerProperty(type=RECOM_PG_EEVEERenderOverrides)

    # Frame Range
    frame_range_override: BoolProperty(
        name="Override Frame Range",
        default=False,
    )
    frame_current: IntProperty(
        name="",
        description="Specify the exact frame number to render (e.g., for still images)",
        default=1,
        min=0,
    )
    frame_start: IntProperty(
        name="",
        description="Define the start frame for animation rendering",
        default=1,
        min=0,
    )
    frame_end: IntProperty(
        name="",
        description="Define the end frame for animation rendering",
        default=250,
        min=0,
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
        default=False,
    )
    resolution_override: BoolProperty(
        name="Set Resolution",
        default=True,
    )

    def _update_auto_cache(self, context):
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
                "Set Width",
                "Specify the width; height will be calculated automatically to maintain the scene's aspect ratio.",
            ),
            (
                "SET_HEIGHT",
                "Set Height",
                "Specify the height; width will be calculated automatically to maintain the scene's aspect ratio.",
            ),
        ],
        default="CUSTOM",
        description="Choose how resolution is configured",
        update=_update_auto_cache,
    )
    resolution_preview: IntProperty(
        name="Auto Calculate Resolution",
        default=1000,
        min=1,
        description="Auto set the resolution maintaining aspect ratio from scene",
        subtype="PIXEL",
    )
    resolution_x: IntProperty(
        name="Width",
        default=1920,
        min=1,
        description="Horizontal resolution in pixels",
        subtype="PIXEL",
        update=_update_auto_cache,
    )
    resolution_y: IntProperty(
        name="Height",
        default=1080,
        min=1,
        description="Vertical resolution in pixels",
        subtype="PIXEL",
        update=_update_auto_cache,
    )
    cached_auto_width: IntProperty(
        name="Cached Auto Width",
        default=0,
        description="Cached width that keeps the aspect ratio when SET_HEIGHT is active",
        subtype="PIXEL",
    )
    cached_auto_height: IntProperty(
        name="Cached Auto Height",
        default=0,
        description="Cached height that keeps the aspect ratio when SET_WIDTH is active",
        subtype="PIXEL",
    )
    render_scale: EnumProperty(
        name="Render Scale",
        items=[
            ("CUSTOM", "Custom", "Custom Scale"),
            ("4.00", "400%", "4x resolution multiplier"),
            ("3.00", "300%", "3x resolution multiplier"),
            ("2.00", "200%", "2x resolution multiplier"),
            ("1.50", "150%", "1.5x resolution multiplier"),
            ("1.00", "100%", "Native resolution"),
            ("0.6667", "66.7% (2/3)", "2/3 resolution"),
            ("0.50", "50%", "Half resolution"),
            ("0.3333", "33.3% (1/3)", "1/3 resolution"),
            ("0.25", "25%", "Quarter resolution"),
        ],
        default="1.00",
        description=(
            "Resolution scaling factor.\n" ">100% for supersampling (sharper results).\n" "<100% for faster previews."
        ),
    )
    custom_render_scale: IntProperty(
        name="Custom Render Scale",
        default=100,
        min=1,
        soft_max=200,
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
        name="",
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
        default=False,
    )
    file_format: EnumProperty(
        name="Format",
        items=[
            ("OPEN_EXR", "OpenEXR (.exr)", "Output image in OpenEXR format"),
            (
                "OPEN_EXR_MULTILAYER",
                "OpenEXR MultiLayer (.exr)",
                "Output image in OpenEXR MultiLayer format",
            ),
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
        else:
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

    # Output Path
    def on_output_path_changed(self, context):
        prefs = get_addon_preferences(context)

        if prefs.path_preview:
            try:
                dir_path_str = self.output_directory or ""
                file_name_str = self.output_filename or ""

                # Resolve directory path with variables
                resolved_dir_str = replace_variables(dir_path_str)
                if resolved_dir_str:
                    folder_path_display = resolved_dir_str
                else:
                    folder_path_display = str(get_default_render_output_path())

                # Ensure trailing slash for display
                # if folder_path_display and not folder_path_display.endswith(("/", "\\")):
                #    folder_path_display += "/"

                if folder_path_display and not folder_path_display.endswith(os.sep):
                    folder_path_display += os.sep

                self.resolved_directory = folder_path_display

                # Resolve filename with variables
                resolved_filename = replace_variables(file_name_str)
                self.resolved_filename = resolved_filename or ""

                self.resolved_path = (
                    str(Path(self.resolved_directory) / self.resolved_filename)
                    if resolved_filename
                    else folder_path_display
                )
            except Exception as e:
                log.error(f"Failed to resolve output path: {str(e)}")

    output_path_override: BoolProperty(
        name="Override Output Path",
        default=False,
        update=on_output_path_changed,
    )
    output_directory: StringProperty(
        name="Output Directory",
        # subtype="DIR_PATH",
        options={"OUTPUT_PATH"},
        default="{blend_dir}/render/",
        description="Specify the directory where rendered files will be saved",
        update=on_output_path_changed,
    )
    output_filename: StringProperty(
        name="Output Filename",
        default="{blend_name}",
        subtype="FILE_NAME",
        description="Specify the filename pattern for rendered files",
        update=on_output_path_changed,
    )
    variable_insert_target: EnumProperty(
        name="Insert Into",
        items=[
            ("DIRECTORY", "Directory", "Insert variable into the output directory path string"),
            ("FILENAME", "Filename", "Insert variable into the output filename string"),
        ],
        default="FILENAME",
    )
    resolved_directory: StringProperty(
        name="Resolved Directory",
        description="Cached version of the resolved directory path",
        default="",
    )
    resolved_filename: StringProperty(
        name="Resolved Filename",
        description="Cached version of the resolved file name path",
        default="",
    )
    resolved_path: StringProperty(
        name="Resolved Output Path",
        description="Cached version of the resolved output path",
        default="",
    )

    # Motion Blur
    motion_blur_override: BoolProperty(
        name="Override Motion Blur",
        default=False,
    )
    use_motion_blur: BoolProperty(
        name="Enable Motion Blur",
        default=True,
        description="Enable motion blur",
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
    motion_blur_shutter: FloatProperty(name="Shutter Length", default=0.5, min=0.0, max=1.0)

    # Compositor
    compositor_override: BoolProperty(
        name="Override Compositor Settings",
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


classes = (
    RECOM_PG_CyclesRenderOverrides,
    RECOM_PG_EEVEERenderOverrides,
    RECOM_PG_OverrideSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
