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
from ..utils.helpers import format_timecode, get_addon_preferences, get_addon_settings, get_scene_info

log = logging.getLogger(__name__)

FORMAT_NAME_MAPPING = {
    "OPEN_EXR": "OpenEXR",
    "OPEN_EXR_MULTILAYER": "Multi-Layer EXR",
    "PNG": "PNG",
    "JPEG": "JPEG",
    "TIFF": "TIFF",
}


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
        layout.menu("RECOM_MT_recent_blend_files", text="", icon="RECOVER_LAST")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
        settings = get_addon_settings(context)
        layout.active = settings.use_external_blend

        col = layout.column()
        row = col.row(align=True)
        sub = row.row(align=True)
        sub.prop(settings, "external_blend_file_path", text="", placeholder="Blend Path")
        sub.operator("recom.select_external_blend_file", text="", icon="FILE_FOLDER")

        # Extract Scene Operator
        sub = layout.row(align=True)
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
            button_text = "Reading scene data…"
            icon = "SORTTIME"

        # Extract
        sub_extract.operator("recom.extract_external_scene_data", text=button_text, icon=icon)

        # Cancel
        if _extraction_state["is_running"]:
            sub.operator("recom.cancel_extraction", text="", icon="CANCEL")
        else:
            sub.menu("RECOM_MT_external_blend_options", text="", icon="DOWNARROW_HLT")

        if not settings.external_blend_file_path and get_scene_info(settings):
            return

        info = get_scene_info(settings) if settings.external_blend_file_path else {}

        # Check for error in scene info extraction first
        if isinstance(info, dict) and "error" in info:
            layout.label(text=f"Error: {info['error']}", icon="ERROR")
            return

        # Display Scene Info
        if info:
            col = layout.column()
            if not prefs.show_scene_info_list:
                self._draw_scene_info(col, info)
            else:
                self._draw_scene_info_ui_list(context, col, info)

        elif settings.external_blend_file_path and settings.is_scene_info_loaded:
            layout.label(text="Failed to load valid scene information", icon="ERROR")

    def _draw_scene_info_row(self, layout, key='', value='', icon="NONE"):
        """Draw a two-column key-value row."""
        split = layout.split(factor=0.4)
        split.label(text=key, icon=icon)
        split.label(text=str(value))

    def _draw_scene_info(self, layout, info):
        """Compact display mode with two-column key-value layout"""

        col = layout.box().column(align=True)
        col.separator(factor=0.2)

        # blend_filename = Path(info.get("blend_filepath", "Unknown File")).name
        version_file = info.get("version_file", "N/A")
        modified_date_short = info.get("modified_date_short", "N/A")
        file_size = info.get("file_size", "N/A")
        self._draw_scene_info_row(col, "Blender", version_file)
        self._draw_scene_info_row(col, "Modified", modified_date_short)
        self._draw_scene_info_row(col, "File Size", file_size)

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

            self._draw_scene_info_row(col, "Engine", f"{render_engine_display} ({compute_device})")
            self._draw_scene_info_row(col, "Samples", f"{samples}{threshold_text}")
            if denoising_text:
                self._draw_scene_info_row(col, "Denoising", "Enabled")
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            eevee_samples = info.get("eevee_samples", "0")
            raytracing_text = " | Raytracing" if info.get("eevee_use_raytracing", False) else ""

            self._draw_scene_info_row(col, "Engine", render_engine_display)
            self._draw_scene_info_row(col, "Samples", f"{eevee_samples}{raytracing_text}")

        # Compositing
        compositing_text = "Compositing" if info.get("use_compositor", False) else ""
        if compositing_text:
            self._draw_scene_info_row(col, "Compositing", "Enabled")

        # Camera
        camera_count = info.get("camera_render_count", 0)
        if camera_count > 1:
            self._draw_scene_info_row(col, "Render Cameras", str(camera_count))

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

        self._draw_scene_info_row(col, "Duration", f"{timecode} ({format_float(fps_real)} fps)")
        self._draw_scene_info_row(col, "Frame Range", f"{frame_start}-{frame_end}")
        self._draw_scene_info_row(col, "Current Frame", frame_current)
        if motion_text:
            self._draw_scene_info_row(col, "Motion Blur", "Enabled")

        # Resolution
        resolution_x = info.get("resolution_x", 0)
        resolution_y = info.get("resolution_y", 0)
        render_scale = info.get("render_scale", 100)
        render_scale_text = f" ({render_scale}%)" if render_scale != 100 else ""
        self._draw_scene_info_row(col, "Resolution", f"{resolution_x} x {resolution_y} px{render_scale_text}")

        # Output format
        file_format = info.get("file_format", "No Data")
        file_format_text = FORMAT_NAME_MAPPING.get(file_format, file_format)
        color_depth_val = info.get("color_depth", "")
        color_depth_text = f" ({color_depth_val}-bit)" if color_depth_val else ""
        self._draw_scene_info_row(col, "Format", f"{file_format_text}{color_depth_text}")

        # Color Management
        view_transform = info.get("view_transform", "")
        look = info.get("look", "")
        if view_transform or look:
            cm_text = ""
            if view_transform and look:
                cm_text = f"{view_transform} | {look}"
            elif view_transform:
                cm_text = view_transform
            else:
                cm_text = look
            self._draw_scene_info_row(col, "Color Management", cm_text)

        # Output Path
        output_path = info.get("filepath", "")
        self._draw_scene_info_row(col, "Output Path", output_path)

    def _draw_scene_info_ui_list(self, context, layout, info):
        """Non-compact display mode using UIList"""
        # self._draw_scene_info_header(layout, info)

        col = layout.column(align=True)

        wm = context.window_manager
        items = wm.recom_external_scene_info_items
        items.clear()

        # Exclude metadata fields shown in header
        excluded_keys = {
            "blend_filepath",
            "modified_date",
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
    "modified_date_short": "Modified",
    "scene_name": "Scene Name",
    "view_layer": "View Layer",
    "view_layer_count": "View Layer Count",
    "viewlayer_names": "View Layer",
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
    "quality": "Quality",
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
