import logging
from pathlib import Path

import bpy

from bpy.types import Panel, UIList

from ..utils.constants import (
    ICON_MENU,
    RE_CYCLES,
    RE_EEVEE_NEXT,
    RE_EEVEE,
    RENDER_ENGINE_MAPPING,
)
from ..preferences import get_addon_preferences
from ..operators.blend_file import _extraction_state
from ..utils.menus import get_scene_info

log = logging.getLogger(__name__)

FORMAT_NAME_MAPPING = {
    "OPEN_EXR": "OpenEXR",
    "OPEN_EXR_MULTILAYER": "OpenEXR MultiLayer",
    "PNG": "PNG",
    "JPEG": "JPEG",
    "TIFF": "TIFF",
}


class RECOM_PT_scene_file_panel(Panel):
    bl_label = "Blend File"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.external_scene

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings, "use_external_blend", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        layout.emboss = "PULLDOWN_MENU"
        layout.active = bool(prefs.recent_blend_files)
        layout.menu("RECOM_MT_recent_blend_files", text="", icon="RECOVER_LAST")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.use_external_blend

        col = layout.column()
        blend_path_row = col.row(align=True)
        blend_path_row.prop(settings, "external_blend_file_path", text="", icon="FILE_BLEND", placeholder="Blend Path")
        blend_path_row.operator("recom.select_external_blend_file", text="", icon="FILE_FOLDER")

        # Extract Scene Operator
        sub = col.row(align=True)
        sub.enabled = bool(settings.external_blend_file_path)

        button_text = "Read Scene"
        icon = "ZOOM_ALL"
        info = get_scene_info(settings) if settings.external_blend_file_path else {}
        if info and settings.external_blend_file_path == info.get("blend_filepath", ""):
            button_text = "Refresh"
            icon = "FILE_REFRESH"

        sub_extract = sub.row(align=True)

        if not settings.is_scene_info_loaded:
            sub_extract.enabled = False
            button_text = "Processing"
            icon = "SORTTIME"

        # Extract
        sub_extract.operator("recom.extract_external_scene_data", text=button_text, icon=icon)

        # Cancel
        if _extraction_state["is_running"]:
            sub.operator("recom.cancel_extraction", text="", icon="CANCEL")


def format_timecode(frame_start: int, frame_end: int, fps_real: float, show_hours: bool = None) -> str:
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


class RECOM_PT_scene_info(Panel):
    bl_label = "File Details"
    bl_parent_id = "RECOM_PT_scene_file_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings
        return settings.external_blend_file_path and get_scene_info(settings)

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = "PULLDOWN_MENU"
        layout.menu("RECOM_MT_external_blend_options", text="", icon=ICON_MENU)
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.use_external_blend

        info = get_scene_info(settings) if settings.external_blend_file_path else {}

        # Check for error in scene info extraction first
        if isinstance(info, dict) and "error" in info:
            layout.label(text=f"Error: {info['error']}", icon="ERROR")
            return

        # Display Scene Info
        if info:
            prefs = get_addon_preferences(context)
            if prefs.compact_external_info:
                self._draw_scene_info(layout, info)
            else:
                self._draw_scene_info_ui_list(context, layout, info)

        elif settings.external_blend_file_path and settings.is_scene_info_loaded:
            layout.label(text="Failed to load valid scene information", icon="ERROR")

    def _draw_scene_info_header(self, layout, info):
        """Shared header drawing for both display modes"""
        blend_filename = Path(info.get("blend_filepath", "Unknown File")).name
        version_file = info.get("version_file", "N/A")
        modified_date_short = info.get("modified_date_short", "N/A")
        file_size = info.get("file_size", "N/A")

        col = layout.column(align=True)
        header_row = col.row(align=True)
        header_text_col = header_row.column(align=True)
        header_text_col.label(text=f"{blend_filename}", icon="FILE_BLEND")
        header_text_line2 = col.column(align=True)
        header_text_line2.label(text=f"{modified_date_short} | {version_file} | {file_size}", icon="BLANK1")

        return col

    def _draw_scene_info(self, layout, info):
        """Compact display mode"""
        col = self._draw_scene_info_header(layout, info)
        col.separator(factor=2.0, type="LINE")

        # Scene
        scene_name = info.get("scene_name", "")
        viewlayer_names = info.get("viewlayer_names", "")

        labels_col = col.column(align=True)
        labels_col.label(text=f"{scene_name} | {viewlayer_names}", icon="SCENE_DATA")

        # Engine
        render_engine = info.get("render_engine", RE_CYCLES)
        render_engine_display = RENDER_ENGINE_MAPPING.get(render_engine, render_engine).replace("_", " ")

        # Sampling info
        if render_engine == RE_CYCLES:
            samples = info.get("samples", "0")
            adaptive = info.get("use_adaptive_sampling", False)
            threshold_text = f" ({round(info.get('adaptive_threshold', 0), 4)})" if adaptive else ""
            denoising_text = " | Denoised" if info.get("use_denoising", False) else ""
            compute_device = info.get("device", "")
            if compute_device == "GPU":
                compute_device = "GPU Compute"

            labels_col.separator(factor=0.5)
            labels_col.label(text=f"{render_engine_display} | {compute_device}", icon="SCENE")
            labels_col.label(text=f"Samples: {samples}{threshold_text}{denoising_text}", icon="BLANK1")

        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            eevee_samples = info.get("eevee_samples", "0")
            raytracing_text = " | Raytracing" if info.get("eevee_use_raytracing", False) else ""

            labels_col.separator(factor=0.5)
            labels_col.label(
                text=f"{render_engine_display} | Samples: {eevee_samples}{raytracing_text}",
                icon="SCENE",
            )

        # Compositing
        compositing_text = "Compositing" if info.get("use_compositor", False) else ""
        if compositing_text:
            labels_col.separator(factor=0.5)
            labels_col.label(text=f"{compositing_text}", icon="NODE_COMPOSITING")

        # Camera
        camera_count = info.get("camera_render_count", 0)
        if camera_count > 1:
            labels_col.separator(factor=0.5)
            labels_col.label(text=f"Render Cameras: {camera_count}", icon="CAMERA_DATA")

        # Frame/time info
        frame_current = info.get("frame_current", 0)
        frame_start = info.get("frame_start", 0)
        frame_end = info.get("frame_end", 0)
        fps = info.get("fps", 24)
        fps_base = info.get("fps_base", 1)
        fps_real = round(fps / fps_base, 2)
        timecode = format_timecode(frame_start, frame_end, fps_real)
        motion_text = " | Motion Enabled" if info.get("use_motion_blur", False) else ""

        labels_col.separator(factor=0.5)
        labels_col.label(
            text=f"Frame {frame_current} ({frame_start}-{frame_end}) | {fps_real} fps",
            icon="PREVIEW_RANGE",
        )
        labels_col.label(text=f"{timecode}{motion_text}", icon="BLANK1")

        # Output format/resolution
        file_format = info.get("file_format", "No Data")
        file_format_text = FORMAT_NAME_MAPPING.get(file_format, file_format)
        color_depth_val = info.get("color_depth", "")
        color_depth_text = f" ({color_depth_val}-bit)" if color_depth_val else ""
        resolution_x = info.get("resolution_x", 0)
        resolution_y = info.get("resolution_y", 0)
        render_scale = info.get("render_scale", 100)
        render_scale_text = f" ({render_scale}%)" if render_scale != 100 else ""

        labels_col.separator(factor=0.5)
        labels_col.label(
            text=f"{resolution_x} x {resolution_y} px{render_scale_text} | {file_format_text}{color_depth_text}",
            icon="IMAGE_DATA",
        )

        # Output path
        output_path = info.get("filepath", "")
        frame_path = info.get("frame_path", "")
        if output_path and frame_path:
            labels_col.separator(factor=0.5)
            op_folder_row = labels_col.row(align=True)
            op_folder_row.alignment = "LEFT"
            op_folder = op_folder_row.operator(
                "recom.open_blend_output_path", text=f"{output_path}", icon="FILE_FOLDER"
            )
            op_folder.file_path = frame_path

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
            rows=6,
            item_dyntip_propname="tooltip_display",
        )


class RECOM_UL_external_blend_info_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.5)
        split.label(text=f"{item.key}")
        split.label(text=f"{item.value}")

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = []
        filter_text = self.filter_name.lower().strip() if self.filter_name else ""

        for item in items:
            flt_flags.append(self.bitflag_filter_item if filter_text in item.key.lower() else 0)

        return flt_flags, []


classes = (
    RECOM_PT_scene_file_panel,
    RECOM_PT_scene_info,
    RECOM_UL_external_blend_info_list,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
