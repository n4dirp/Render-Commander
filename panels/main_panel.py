# ./panels/main_panel.py

import logging
from pathlib import Path

import bpy
from bpy.types import Panel

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import get_render_engine, logical_width

log = logging.getLogger(__name__)


def _is_render_operator_active(context):
    settings = context.window_manager.recom_render_settings
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)
    else:
        return bool(bpy.data.filepath)


class RECOM_PT_MainPanel(Panel):
    """Main panel for background rendering controls"""

    bl_label = "Launcher"
    bl_idname = "RECOM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return prefs.initial_setup_complete if render_engine == "CYCLES" else True

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        # layout.popover(panel="RECOM_PT_layout_popup", text="", icon="DOWNARROW_HLT")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        main_col = layout.column()

        wm = context.window_manager
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Launching box
        if settings.disable_render_button:
            box = main_col.box()
            row = box.row(align=True)
            row.active = False
            row.scale_y = 0.5
            row = row.row(align=True)
            row.alignment = "CENTER"
            row.label(text=f"Launching...")

        else:
            # Render button
            row = main_col.row(align=True)
            row.active = _is_render_operator_active(context)
            row.operator(
                "recom.background_render",
                text=f"Render{CENTER_TEXT}",
                icon="CONSOLE",
            )

        # Render Mode
        main_col.separator(factor=0.5)
        col = main_col.column()
        col.use_property_split = True
        col.use_property_decorate = False

        col.prop(prefs, "launch_mode", text="Mode", expand=True)

        if prefs.launch_mode == MODE_LIST:
            col.prop(settings, "frame_list", text="Frames", placeholder="1, 2, 5-8")


def menu_render_button(self, context):
    layout = self.layout
    layout.separator()

    prefs = get_addon_preferences(context)

    row = layout.row()
    row.active = _is_render_operator_active(context)

    mode_name = "Image"
    enum_id = prefs.launch_mode
    for item in type(prefs).bl_rna.properties["launch_mode"].enum_items:
        if item.identifier == enum_id:
            mode_name = item.name
            break

    text = f"Render {mode_name}"

    row.operator(
        "recom.background_render",
        text=text,
        icon="CONSOLE",
    )


classes = (RECOM_PT_MainPanel,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_render.append(menu_render_button)


def unregister():
    bpy.types.TOPBAR_MT_render.remove(menu_render_button)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
