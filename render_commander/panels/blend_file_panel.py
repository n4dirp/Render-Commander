import logging
from pathlib import Path

import bpy
from bpy.types import Panel, UIList

from ..operators.blend_file import _extraction_state
from ..utils.constants import (
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RENDER_ENGINE_MAPPING,
    RCSubPanel,
)
from ..utils.helpers import get_addon_preferences, get_addon_settings, get_scene_info

log = logging.getLogger(__name__)

FORMAT_NAME_MAPPING = {
    "OPEN_EXR": "OpenEXR",
    "OPEN_EXR_MULTILAYER": "OpenEXR MultiLayer",
    "PNG": "PNG",
    "JPEG": "JPEG",
    "TIFF": "TIFF",
}


def format_timecode(frame_start: int, frame_end: int, fps_real: float, show_hours=False) -> str:
    """Convert a frame range to a formatted timecode string."""
    # Calculate total duration
    total_frames = max(0, frame_end - frame_start + 1)
    total_seconds = total_frames / fps_real if fps_real > 0 else 0

    # Break down into time components
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    # Calculate remaining frames from fractional seconds
    frames = int(round((total_seconds - int(total_seconds)) * fps_real))

    # Handle frame overflow (can happen due to rounding)
    if frames >= fps_real:
        frames = 0
        seconds += 1
        if seconds >= 60:
            seconds = 0
            minutes += 1
            if minutes >= 60:
                minutes = 0
                hours += 1

    # Format output
    if show_hours is True or (show_hours is None and hours > 0):
        return f"{hours:02}:{minutes:02}:{seconds:02}+{frames:02}"

    return f"{minutes:02}:{seconds:02}+{frames:02}"


class RECOM_PT_scene_file_panel(RCSubPanel, Panel):
    bl_label = "Blend File"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.external_scene

    def draw_header(self, context):
        settings = get_addon_settings(context)
        self.layout.prop(settings, "use_external_blend", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        layout.emboss = "PULLDOWN_MENU"
        layout.active = bool(prefs.recent_blend_files)
        layout.menu("RECOM_MT_recent_blend_files", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = get_addon_settings(context)
        layout.active = settings.use_external_blend

        col = layout.column()
        row = col.row(align=True)
        sub = row.row(align=True)
        sub.prop(settings, "external_blend_file_path", text="", placeholder="Blend Path")
        sub.operator("recom.select_external_blend_file", text="", icon="FILE_FOLDER")

        # Extract Scene Operator
        sub = row.row(align=True)
        sub.enabled = bool(settings.external_blend_file_path)

        icon = "ZOOM_ALL"
        info = get_scene_info(settings) if settings.external_blend_file_path else {}
        if info and settings.external_blend_file_path == info.get("blend_filepath", ""):
            icon = "FILE_REFRESH"

        sub_extract = sub.row(align=True)

        if not settings.is_scene_info_loaded:
            sub_extract.enabled = False
        else:
            # Extract
            sub_extract.operator("recom.extract_external_scene_data", text="", icon=icon)

        # Cancel
        if _extraction_state["is_running"]:
            row.operator("recom.cancel_extraction", text="", icon="CANCEL")

            box = layout.box()
            box.active = False
            box.label(text="Reading scene data…", icon="SORTTIME")

        if not settings.external_blend_file_path and get_scene_info(settings):
            return

        info = get_scene_info(settings) if settings.external_blend_file_path else {}

        # Check for error in scene info extraction first
        if isinstance(info, dict) and "error" in info:
            layout.label(text=f"Error: {info['error']}", icon="ERROR")
            return

        # Display Scene Info
        if info:
            prefs = get_addon_preferences(context)

            if not prefs.show_scene_info_list:
                self._draw_scene_info(layout.box(), info)
            else:
                self._draw_scene_info_ui_list(context, layout.box(), info)

        elif settings.external_blend_file_path and settings.is_scene_info_loaded:
            layout.label(text="Failed to load valid scene information", icon="ERROR")

    def _draw_scene_info_header(self, layout, info):
        """Shared header drawing for both display modes"""
        blend_filename = Path(info.get("blend_filepath", "Unknown File")).name
        version_file = info.get("version_file", "N/A")
        modified_date_short = info.get("modified_date_short", "N/A")
        file_size = info.get("file_size", "N/A")

        col = layout.column(align=True)
        row = col.row(align=True)
        row.label(text=f"{blend_filename}", icon="FILE_BLEND")
        row.menu("RECOM_MT_external_blend_options", text="", icon="DOWNARROW_HLT")
        col.label(text=f"Blender {version_file}", icon="BLANK1")
        col.label(text=f"{modified_date_short} | {file_size}", icon="BLANK1")

        return col

    def _draw_scene_info(self, layout, info):
        """Compact display mode"""
        col = self._draw_scene_info_header(layout, info)
        col.separator(factor=2.0, type="LINE")

        separator_factor = 1.0

        # Scene
        scene_name = info.get("scene_name", "")
        viewlayer_names = info.get("viewlayer_names", "")

        col = col.column(align=True)
        col.label(text=f"{scene_name}", icon="SCENE_DATA")

        layer_list = [name.strip() for name in viewlayer_names.split(", ") if name.strip()]
        if layer_list:
            layer_col = col.column(align=True)

            if len(layer_list) == 1:
                # Single layer: combine label and layer name on same line
                layer_col.label(text=f"{layer_list[0]}", icon="RENDERLAYERS")
            else:
                # Multiple layers: label on first line, layers below
                layer_col.label(text="Render Layers: ", icon="RENDERLAYERS")
                for name in layer_list:
                    layer_col.label(text=name, icon="BLANK1")
                layer_col.scale_y = 0.9

        # Engine
        render_engine = info.get("render_engine", RE_CYCLES)
        render_engine_display = RENDER_ENGINE_MAPPING.get(render_engine, render_engine).replace("_", " ")

        # Sampling info
        if render_engine == RE_CYCLES:
            samples = info.get("samples", "0")
            adaptive = info.get("use_adaptive_sampling", False)
            threshold_text = f" ({round(info.get('adaptive_threshold', 0), 4)})" if adaptive else ""
            denoising_text = "Denoising" if info.get("use_denoising", False) else ""
            compute_device = info.get("device", "N/A")

            col.separator(factor=separator_factor)
            col.label(
                text=f"{render_engine_display} ({compute_device})",
                icon="SCENE",
            )
            col.label(text=f"Samples: {samples}{threshold_text}", icon="BLANK1")
            if denoising_text:
                col.label(text=f"{denoising_text}", icon="BLANK1")
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            eevee_samples = info.get("eevee_samples", "0")
            raytracing_text = " | Raytracing" if info.get("eevee_use_raytracing", False) else ""

            col.separator(factor=separator_factor)
            col.label(text=f"{render_engine_display}", icon="SCENE")
            col.label(text=f"Samples: {eevee_samples}{raytracing_text}", icon="BLANK1")

        # Compositing
        compositing_text = "Compositing" if info.get("use_compositor", False) else ""
        if compositing_text:
            col.separator(factor=separator_factor)
            col.label(text=f"{compositing_text}", icon="NODE_COMPOSITING")

        # Camera
        camera_count = info.get("camera_render_count", 0)
        if camera_count > 1:
            col.separator(factor=separator_factor)
            col.label(text=f"Render Cameras: {camera_count}", icon="CAMERA_DATA")

        # Frame/time info
        frame_current = info.get("frame_current", 0)
        frame_start = info.get("frame_start", 0)
        frame_end = info.get("frame_end", 0)
        fps = info.get("fps", 24)
        fps_base = info.get("fps_base", 1)
        fps_real = round(fps / fps_base, 2)
        timecode = format_timecode(frame_start, frame_end, fps_real)
        motion_text = "Motion Blur" if info.get("use_motion_blur", False) else ""

        def format_float(value):
            if value == int(value):
                return str(int(value))
            else:
                return str(value)

        col.separator(factor=separator_factor)
        col.label(text=f"Frame {frame_start}/{frame_end} ({frame_current})", icon="PREVIEW_RANGE")
        col.label(text=f"{format_float(fps_real)} fps | {timecode}", icon="BLANK1")
        if motion_text:
            col.label(text=f"{motion_text}", icon="BLANK1")

        # Output format/resolution
        file_format = info.get("file_format", "No Data")
        file_format_text = FORMAT_NAME_MAPPING.get(file_format, file_format)
        color_depth_val = info.get("color_depth", "")
        color_depth_text = f" ({color_depth_val}-bit)" if color_depth_val else ""
        resolution_x = info.get("resolution_x", 0)
        resolution_y = info.get("resolution_y", 0)
        render_scale = info.get("render_scale", 100)
        render_scale_text = f" ({render_scale}%)" if render_scale != 100 else ""

        col.separator(factor=separator_factor)
        col.label(text=f"{resolution_x} x {resolution_y} px{render_scale_text}", icon="IMAGE_DATA")
        col.label(text=f"{file_format_text}{color_depth_text}", icon="BLANK1")

        # Output path
        output_path = info.get("filepath", "")
        frame_path = info.get("frame_path", "")
        if output_path and frame_path:
            col.separator(factor=separator_factor)
            op_folder_row = col.row(align=True)
            op_folder_row.alignment = "LEFT"
            op_folder_row.operator(
                "recom.open_blend_output_path",
                text=f"{output_path}",
                icon="FILE_FOLDER",
            ).file_path = frame_path

    def _draw_scene_info_ui_list(self, context, layout, info):
        """Non-compact display mode using UIList"""
        col = self._draw_scene_info_header(layout, info)
        col.separator()

        wm = context.window_manager
        items = wm.recom_external_scene_info_items
        items.clear()

        # Exclude metadata fields shown in header
        excluded_keys = {
            "blend_filepath",
            "version_file",
            "modified_date",
            "modified_date_short",
            "file_size",
            "view_layer",
            "view_layer_count",
        }

        for k, v in info.items():
            if k not in excluded_keys:
                item = items.add()
                item.key = k
                item.value = str(v)

        col.template_list(
            "RECOM_UL_external_blend_info_list",
            "",
            wm,
            "recom_external_scene_info_items",
            wm,
            "recom_external_scene_info_active",
            rows=4,
            item_dyntip_propname="tooltip_display",
        )


# Add this near the top of the file, after FORMAT_NAME_MAPPING
EXTERNAL_BLEND_INFO_KEY_MAP = {
    "scene_name": "Scene Name",
    "view_layer": "View Layer",
    "view_layer_count": "View Layer Count",
    "viewlayer_names": "View Layer Names",
    "render_engine": "Render Engine",
    "view_transform": "View Transform",
    "look": "Look",
    "frame_current": "Current Frame",
    "frame_start": "Start Frame",
    "frame_end": "End Frame",
    "frame_step": "Frame Step",
    "fps": "FPS",
    "fps_base": "FPS Base",
    "resolution_x": "Resolution X",
    "resolution_y": "Resolution Y",
    "render_scale": "Render Scale",
    "filepath": "Output Path",
    "frame_path": "Frame Path",
    "is_movie_format": "Movie Format",
    "file_format": "File Format",
    "color_depth": "Color Depth",
    "exr_codec": "EXR Codec",
    "jpeg_quality": "JPEG Quality",
    "use_motion_blur": "Motion Blur",
    "motion_blur_position": "Motion Blur Position",
    "motion_blur_shutter": "Motion Blur Shutter",
    "camera_name": "Camera Name",
    "camera_lens": "Camera Lens",
    "camera_sensor": "Camera Sensor",
    "use_compositor": "Compositing",
    "compositor_device": "Compositor Device",
    "camera_render_count": "Render Cameras",
    "device": "Device",
    "use_adaptive_sampling": "Adaptive Sampling",
    "adaptive_threshold": "Adaptive Threshold",
    "samples": "Samples",
    "adaptive_min_samples": "Min Adaptive Samples",
    "time_limit": "Time Limit",
    "use_denoising": "Denoising",
    "denoiser": "Denoiser",
    "denoising_input_passes": "Denoising Input Passes",
    "denoising_prefilter": "Denoising Prefilter",
    "denoising_quality": "Denoising Quality",
    "use_denoise_gpu": "Denoise GPU",
    "use_tiling": "Auto Tiling",
    "tile_size": "Tile Size",
    "use_spatial_splits": "Spatial Splits",
    "use_compact_bvh": "Compact BVH",
    "persistent_data": "Persistent Data",
    "eevee_samples": "EEVEE Samples",
    "eevee_use_raytracing": "EEVEE Raytracing",
}


class RECOM_UL_external_blend_info_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        display_key = EXTERNAL_BLEND_INFO_KEY_MAP.get(item.key, item.key.replace("_", " ").title())

        split = layout.split(factor=0.45)
        split.label(text=display_key)
        split.label(text=item.value)

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = []
        filter_text = self.filter_name.lower().strip() if self.filter_name else ""

        for item in items:
            # Filter by both the original key and the display name
            display_name = EXTERNAL_BLEND_INFO_KEY_MAP.get(item.key, item.key).lower()
            if filter_text in item.key.lower() or filter_text in display_name:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, []


classes = (
    RECOM_PT_scene_file_panel,
    RECOM_UL_external_blend_info_list,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
