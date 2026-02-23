# ./panels/main_panel.py

import logging
from pathlib import Path

import bpy
from bpy.types import Panel, Menu

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


class RECOM_PT_main_panel(Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return prefs.initial_setup_complete if render_engine == RE_CYCLES else True

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Mode
        col = layout.column()
        mode_row = col.row()
        mode_row.prop(prefs, "launch_mode", text="Mode", expand=True)

        # Frame List
        if prefs.launch_mode == MODE_LIST:
            list_col = layout.row()
            list_col.use_property_split = True
            list_col.use_property_decorate = False
            list_col.prop(settings, "frame_list", text="Frame List", placeholder="")

        # Launcher
        launcher_row = layout.row(align=True)
        render_row = launcher_row.row(align=True)
        render_op_active = _is_render_operator_active(context)

        if settings.disable_render_button:
            render_row.enabled = False
            render_row.operator("recom.loading_button", text="Launching", icon="TIME")
        else:
            launcher_row.active = render_op_active
            render_row.enabled = True
            render_row.active = render_op_active

            op_render = render_row.operator("recom.background_render", text="Render", icon="CONSOLE")
            op_render.action_type = "RENDER"

        export_row = launcher_row.row(align=True)
        export_row.operator("recom.export_render_script", text="", icon="EXPORT")


class RECOM_MT_render_commander_menu(Menu):
    bl_label = "Render Commander"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.enabled = _is_render_operator_active(context)

        col.operator("recom.render_image", text="Render Image", icon="CONSOLE")
        col.operator("recom.render_animation", text="Render Animation")
        col.separator()
        col.operator("recom.export_image", text="Export Image Render", icon="EXPORT")
        col.operator("recom.export_animation", text="Export Animation Render")


def menu_render_commander_submenu(self, context):
    layout = self.layout
    layout.separator()
    row = layout.row()
    row.enabled = _is_render_operator_active(context)
    row.menu("RECOM_MT_render_commander_menu", text="Render Commander")


classes = (
    RECOM_PT_main_panel,
    RECOM_MT_render_commander_menu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_render.append(menu_render_commander_submenu)


def unregister():
    bpy.types.TOPBAR_MT_render.remove(menu_render_commander_submenu)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
