# ./panels/external_scene_panel.py

import json
import logging
from pathlib import Path

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import get_render_engine, format_to_title_case

log = logging.getLogger(__name__)

FORMAT_NAME_MAPPING = {
    "OPEN_EXR": "OpenEXR",
    "OPEN_EXR_MULTILAYER": "OpenEXR MultiLayer",
    "PNG": "PNG",
    "JPEG": "JPEG",
    "TIFF": "TIFF",
}


class RECOM_PT_SceneFilePanel(Panel):
    bl_label = "External Blend File"
    bl_idname = "RECOM_PT_scene_file_panel"
    # bl_parent_id = "RECOM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (
            prefs.initial_setup_complete if render_engine == "CYCLES" else True
        ) and prefs.visible_panels.external_scene

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings, "use_external_blend", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        # Recent files menu
        layout.active = True if len(prefs.recent_blend_files) > 0 else False
        layout.menu("RECOM_MT_recent_blend_files", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.use_external_blend

        col = layout.column()
        blend_path_row = col.row(align=True)
        blend_path_row.prop(
            settings,
            "external_blend_file_path",
            text="",
            # icon="FILE_BLEND",
            placeholder="Blend Path",
        )
        blend_path_row.operator("recom.select_external_blend_file", text="", icon="FILE_FOLDER")

        # Extract Scene Operator
        sub = col.row(align=True)
        if settings.is_scene_info_loaded:
            sub.enabled = True if len(settings.external_blend_file_path) > 0 else False

            button_text = f"Read Scene{CENTER_TEXT}"
            icon = "ZOOM_ALL"

            if settings.external_blend_file_path:
                try:
                    info = json.loads(settings.external_scene_info)
                    if info.get("blend_filepath", "") == settings.external_blend_file_path:
                        button_text = f"Refresh{CENTER_TEXT}"
                        icon = "FILE_REFRESH"
                except json.JSONDecodeError as e:
                    log.error("Failed to decode JSON: %s", e)
            sub.operator("recom.extract_external_scene_data", text=button_text, icon=icon)

        else:
            sub.enabled = False
            sub.operator("recom.loading_button", text=f"Processing{CENTER_TEXT}", icon="TIME")

        # Display Scene Info
        try:
            if prefs.compact_external_info:
                info = json.loads(settings.external_scene_info)
                if settings.external_blend_file_path and info and info.get("blend_filepath") != "No Data":
                    self._draw_scene_info_box(layout, info)
            """
            else:
                wm = context.window_manager
                items = wm.recom_external_scene_info_items
                active_index = wm.recom_external_scene_info_active

                try:
                    info_dict = json.loads(settings.external_scene_info)
                    if (
                        settings.external_blend_file_path
                        and info_dict
                        and info_dict.get("blend_filepath") != "No Data"
                    ):
                        items.clear()
                        for k, v in info_dict.items():
                            item = items.add()
                            item.key = format_to_title_case(k)
                            item.value = str(v)

                except (json.JSONDecodeError, TypeError):
                    if settings.external_blend_file_path:
                        layout.label(text="Invalid Scene Info Data", icon="ERROR")
                    return

                row_main = layout.row()
                row_main.template_list(
                    "RECOM_UL_ExternalBlendInfoList",
                    "",
                    wm,
                    "recom_external_scene_info_items",
                    wm,
                    "recom_external_scene_info_active",
                    rows=8,
                )
                row_main.menu("RECOM_MT_external_blend_options", text="", icon="DOWNARROW_HLT")
            """
        except (json.JSONDecodeError, TypeError):
            if settings.external_blend_file_path:
                layout.label(text="Invalid Scene Info Data", icon="ERROR")

    def _draw_scene_info_box(self, layout, info):
        # Variables
        separator = "  |  "
        blend_filename = Path(info.get("blend_filepath", "Unknown File")).name
        blender_version = info.get("blender_version", "N/A")
        modified_date_short = info.get("modified_date_short", "N/A")
        file_size = info.get("file_size", "N/A")
        scene_name = info.get("scene_name", "N/A")
        view_layer = info.get("view_layer", "N/A")
        cam_name = info.get("camera_name", "No Camera")
        frame_current = info.get("frame_current", "0")
        frame_start = info.get("frame_start", "0")
        frame_end = info.get("frame_end", "0")
        fps = info.get("fps", 24)
        fps_base = info.get("fps_base", 1)
        fps_real = round(fps / fps_base, 2)
        resolution_x = info.get("resolution_x", 0)
        resolution_y = info.get("resolution_y", 0)
        render_scale = info.get("render_scale", 100)
        render_scale_text = f" ({render_scale}%)" if render_scale != 100 else ""
        samples = info.get("samples", "0")
        adaptive = info.get("use_adaptive_sampling", False)
        threshold = round(info.get("adaptive_threshold", 0), 4)
        threshold_text = f" (Thr. {threshold})" if adaptive else ""
        use_denoising = info.get("use_denoising", False)
        denoising_text = f"{separator}Denoised" if use_denoising else ""
        use_motion_blur = info.get("use_motion_blur", False)
        motion_text = f"{separator}Motion Enabled" if use_motion_blur else ""
        use_compositor = info.get("use_compositor", False)
        compositing_text = f"{separator}Compositing" if use_compositor else ""
        file_format = info.get("file_format", "No Data")
        color_depth_val = info.get("color_depth", "")
        color_depth_text = f" ({color_depth_val}-bit)" if color_depth_val else ""
        output_path = info.get("filepath", "N/A")
        file_format_text = FORMAT_NAME_MAPPING.get(file_format, file_format)
        render_engine = info.get("render_engine", "CYCLES")
        eevee_samples = info.get("eevee_samples", "0")
        eevee_use_raytracing = info.get("eevee_use_raytracing", False)
        use_raytracing_text = f"{separator}Raytracing" if eevee_use_raytracing else ""

        # Draw
        box = layout.box()
        # row = box.row(align=True)
        # row.separator(factor=0.5)

        col = box.column(align=True)

        header_row = col.row(align=True)
        header_text_col = header_row.column(align=True)
        header_text_col.active = False
        header_text_col.label(text=f"{blend_filename}")
        header_text_line2 = col.column(align=True)
        header_text_line2.active = False
        header_text_line2.label(text=f"Blender {blender_version}{separator}Size: {file_size}")
        header_text_line2.label(text=f"Modified: {modified_date_short}")
        menu_col = header_row.column()
        menu_col.alignment = "RIGHT"
        menu_col.menu("RECOM_MT_external_blend_options", text="", icon="DOWNARROW_HLT")

        col.separator(type="LINE", factor=1.5)

        labels_col = col.column(align=True)
        labels_col.active = False
        if render_engine != "CYCLES":
            labels_col.label(text=f'Render Engine: {render_engine.replace("_", " ")}')
        labels_col.label(text=f"Frame: {frame_current} / {frame_start}-{frame_end} @{fps_real} FPS{motion_text}")

        if render_engine == "CYCLES":
            labels_col.label(text=f"Samples: {samples}{threshold_text}{denoising_text}{compositing_text}")
        elif render_engine in {"BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"}:
            labels_col.label(text=f"Samples: {eevee_samples}{use_raytracing_text}{compositing_text}")

        labels_col.label(
            text=f"Format: {file_format_text}{color_depth_text}{separator}{resolution_x} x {resolution_y} px{render_scale_text}"
        )

        labels_col.label(text=f"Output: {output_path}")


class RECOM_PT_ExternalBlendInfoExpanded(Panel):
    bl_label = "Scene Info"
    bl_idname = "RECOM_PT_external_blend_info_expanded"
    bl_parent_id = "RECOM_PT_scene_file_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        settings = context.window_manager.recom_render_settings
        return settings.external_blend_file_path and settings.is_scene_info_loaded and not prefs.compact_external_info

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.use_external_blend

        layout.menu("RECOM_MT_external_blend_options", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.use_external_blend

        wm = context.window_manager
        items = wm.recom_external_scene_info_items
        active_index = wm.recom_external_scene_info_active

        try:
            info_dict = json.loads(settings.external_scene_info)
            if settings.external_blend_file_path and info_dict and info_dict.get("blend_filepath") != "No Data":
                items.clear()
                for k, v in info_dict.items():
                    item = items.add()
                    item.key = format_to_title_case(k)
                    item.value = str(v)

        except (json.JSONDecodeError, TypeError):
            if settings.external_blend_file_path:
                layout.label(text="Invalid Scene Info Data", icon="ERROR")
            return

        row_main = layout.row()
        row_main.template_list(
            "RECOM_UL_ExternalBlendInfoList",
            "",
            wm,
            "recom_external_scene_info_items",
            wm,
            "recom_external_scene_info_active",
            rows=8,
            item_dyntip_propname="tooltip_display",
        )


class RECOM_UL_ExternalBlendInfoList(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.active = False
        """
        split = layout.split(factor=0.45)
        split.column().label(text=f"{item.key}")
        split.column().label(text=f"{item.value}")
        """
        layout.label(text=f"{item.key}: {item.value}")

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = []
        flt_neworder = []

        filter_text = self.filter_name.lower().strip() if self.filter_name else ""

        for item in items:
            if filter_text in item.key.lower():
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder


classes = (
    RECOM_PT_SceneFilePanel,
    RECOM_UL_ExternalBlendInfoList,
    RECOM_PT_ExternalBlendInfoExpanded,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
