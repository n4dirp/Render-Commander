import json
import logging
from pathlib import Path

import bpy

from bpy.types import Panel, UIList

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import get_render_engine, format_to_title_case

log = logging.getLogger(__name__)

# Consolidated format mapping (removed trailing spaces)
FORMAT_NAME_MAPPING = {
    "OPEN_EXR": "OpenEXR",
    "OPEN_EXR_MULTILAYER": "OpenEXR MultiLayer",
    "PNG": "PNG",
    "JPEG": "JPEG",
    "TIFF": "TIFF",
}


def format_small_time(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}m {s:.2f}s"
    else:
        h = int(seconds // 3600)
        rem = seconds % 3600
        m = int(rem // 60)
        return f"{h}h {m}m"


def get_scene_info(settings):
    """Single source of truth for scene info parsing"""
    if not settings.external_scene_info or not settings.is_scene_info_loaded:
        return None

    try:
        info = json.loads(settings.external_scene_info)
        if info.get("blend_filepath", "") == "No Data":
            return None
        return info
    except json.JSONDecodeError as e:
        log.error("Failed to decode JSON: %s", e)
        return None


class RECOM_PT_scene_file_panel(Panel):
    bl_label = "Blend File"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (
            prefs.initial_setup_complete if render_engine == RE_CYCLES else True
        ) and prefs.visible_panels.external_scene

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
        blend_path_row.prop(
            settings, "external_blend_file_path", text="", placeholder="Blend Path"
        )  # , icon="FILE_BLEND")
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

        if not settings.is_scene_info_loaded:
            sub.enabled = False
            sub.operator("recom.loading_button", text="Processing", icon="PREVIEW_LOADING")
        else:
            sub.operator("recom.extract_external_scene_data", text=button_text, icon=icon)


class RECOM_PT_scene_info(Panel):
    bl_label = "Blend Info"
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
        layout.menu("RECOM_MT_external_blend_options", text="", icon="COLLAPSEMENU")
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
        separator = " | "
        blend_filename = Path(info.get("blend_filepath", "Unknown File")).name
        blender_version = info.get("blender_version", "N/A")
        modified_date_short = info.get("modified_date_short", "N/A")
        file_size = info.get("file_size", "N/A")

        col = layout.column(align=True)
        header_row = col.row(align=True)
        header_text_col = header_row.column(align=True)
        header_text_col.label(text=f"{blend_filename}", icon="FILE_BLEND")
        header_text_line2 = col.column(align=True)
        # header_text_line2.active = False
        # header_text_line2.label(text=f"Blender {blender_version}", icon="BLANK1")
        # header_text_line2.separator()
        header_text_line2.label(text=f"{modified_date_short} | v{blender_version} | {file_size} ", icon="BLANK1")
        # header_text_line2.label(text=f"Size: {file_size}", icon="BLANK1")

        return col  # Return for further layout operations

    def _draw_scene_info(self, layout, info):
        """Compact display mode"""
        col = self._draw_scene_info_header(layout, info)
        col.separator(type="AUTO")
        labels_col = col.column(align=False)

        separator = " | "

        scene_name = info.get("scene_name", "")
        viewlayer_names = info.get("viewlayer_names", "")
        labels_col.label(text=f"{scene_name} | {viewlayer_names}", icon="SCENE_DATA")

        # Common rendering properties
        render_engine = info.get("render_engine", RE_CYCLES)
        render_engine_display = RENDER_ENGINE_MAPPING.get(render_engine, render_engine).replace("_", " ")

        # Sampling info
        if render_engine == RE_CYCLES:
            samples = info.get("samples", "0")
            adaptive = info.get("use_adaptive_sampling", False)
            threshold_text = f" ({round(info.get('adaptive_threshold', 0), 4)})" if adaptive else ""
            denoising_text = " | Denoised" if info.get("use_denoising", False) else ""
            labels_col.label(
                text=f"{render_engine_display} | Samples: {samples}{threshold_text}{denoising_text}", icon="SCENE"
            )

        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            eevee_samples = info.get("eevee_samples", "0")
            raytracing_text = " | Raytracing" if info.get("eevee_use_raytracing", False) else ""
            labels_col.label(text=f"{render_engine_display} | Samples: {eevee_samples}{raytracing_text}", icon="SCENE")

        compositing_text = "Compositing" if info.get("use_compositor", False) else ""
        if compositing_text:
            labels_col.label(text=f"{compositing_text}", icon="NODE_COMPOSITING")

        camera_count = info.get("camera_render_count", 0)
        if camera_count > 1:
            labels_col.label(text=f"Render Cameras: {camera_count}", icon="CAMERA_DATA")

        labels_col.separator()

        # Frame/time info
        frame_current = info.get("frame_current", 0)
        frame_start = info.get("frame_start", 0)
        frame_end = info.get("frame_end", 0)
        fps = info.get("fps", 24)
        fps_base = info.get("fps_base", 1)
        fps_real = round(fps / fps_base, 2)
        total_frames = frame_end - frame_start + 1
        total_seconds = total_frames / fps_real
        total_time_text = format_small_time(total_seconds)

        motion_text = " | Motion Enabled" if info.get("use_motion_blur", False) else ""
        labels_col.label(
            text=f"Frame {frame_current} ({frame_start}-{frame_end}) | {fps_real} fps ({total_time_text}){motion_text}",
            icon="PREVIEW_RANGE",
        )

        # Output format/resolution
        file_format = info.get("file_format", "No Data")
        file_format_text = FORMAT_NAME_MAPPING.get(file_format, file_format)
        color_depth_val = info.get("color_depth", "")
        color_depth_text = f" ({color_depth_val}-bit)" if color_depth_val else ""
        resolution_x = info.get("resolution_x", 0)
        resolution_y = info.get("resolution_y", 0)
        render_scale = info.get("render_scale", 100)
        render_scale_text = f" ({render_scale}%)" if render_scale != 100 else ""
        labels_col.label(
            text=f"{resolution_x} x {resolution_y} px{render_scale_text} | {file_format_text}{color_depth_text}",
            icon="IMAGE_DATA",
        )

        # Output path
        output_path = info.get("filepath", "N/A")
        labels_col.label(text=f"{output_path}", icon="FILE_FOLDER")

    def _draw_scene_info_ui_list(self, context, layout, info):
        """Non-compact display mode using UIList"""
        col = self._draw_scene_info_header(layout, info)
        col.separator()

        wm = context.window_manager
        items = wm.recom_external_scene_info_items
        items.clear()

        # Exclude metadata fields shown in header
        excluded_keys = {"blend_filepath", "blender_version", "modified_date", "modified_date_short", "file_size"}

        for k, v in info.items():
            if k not in excluded_keys:
                item = items.add()
                item.key = k  # format_to_title_case(k)
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


class RECOM_UL_external_blend_info_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # layout.active = False
        layout.label(text=f"{item.key}: {item.value}")

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
