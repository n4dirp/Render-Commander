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

    bl_label = "Render Commander"
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
        layout.emboss = "PULLDOWN_MENU"

        layout.popover(panel="RECOM_PT_render_option_popup", text="", icon="OPTIONS")

    def draw(self, context):
        layout = self.layout

        wm = context.window_manager
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # RC Launcher
        col = layout.column(align=False)

        # Render button
        render_op_active = _is_render_operator_active(context)
        render_row = col.row(align=False)

        if settings.disable_render_button:
            render_row.enabled = False
            render_row.operator("recom.loading_button", text="Launching", icon="TIME")
        else:
            col.active = render_op_active
            render_row.enabled = True
            render_row.active = render_op_active

            op_render = render_row.operator("recom.background_render", text=f"Render{CENTER_TEXT}", icon="CONSOLE")
            op_render.action_type = "RENDER"

        col.separator(factor=0.15)

        export_row = col.row(align=False)
        export_row.operator("recom.export_render_script", text=f"Export{CENTER_TEXT}", icon="EXPORT")

        # Render Mode
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False

        col.prop(prefs, "launch_mode", text="Mode", expand=True)

        if prefs.launch_mode == MODE_LIST:
            col.prop(settings, "frame_list", text="Frames", placeholder="1, 2, 5-8")


class RECOM_PT_RenderOptionsPopup(Panel):
    bl_label = "Render/Export Options"
    bl_idname = "RECOM_PT_render_option_popup"
    bl_options = {"INSTANCED"}
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column(heading="Launch Options")
        col.prop(prefs, "auto_open_output_folder", text="Open Output Path")
        col.prop(prefs, "exit_active_session")

        col.separator()

        col = layout.column(heading="Export Options")
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Path")
        col.prop(prefs, "export_master_script", text="Export Master Script")

        col = layout.column(heading="Scripts Directory")
        col.prop(prefs, "export_output_target", text="")

        if prefs.export_output_target == "CUSTOM_PATH":
            col.prop(prefs, "custom_export_path", text="", placeholder="")

        col = layout.column(heading="Folder")
        col.prop(prefs, "export_scripts_folder_name", text="", placeholder="")


class RECOM_MT_RenderCommanderMenu(bpy.types.Menu):
    bl_label = "Render Commander"
    bl_idname = "RECOM_MT_render_commander_menu"

    def draw(self, context):
        layout = self.layout

        col = self.layout.column()
        col.enabled = _is_render_operator_active(context)

        col.operator("recom.render_image", text="Render Image", icon="CONSOLE")
        col.operator("recom.render_animation", text="Render Animation")
        col.separator()
        col.operator("recom.export_image", text="Export Image Render", icon="EXPORT")
        col.operator("recom.export_animation", text="Export Animation Render")


def menu_render_commander_submenu(self, context):
    self.layout.separator()
    row = self.layout.row()
    row.active = _is_render_operator_active(context)
    row.menu("RECOM_MT_render_commander_menu", text="Render Commander")


classes = (
    RECOM_PT_MainPanel,
    RECOM_PT_RenderOptionsPopup,
    RECOM_MT_RenderCommanderMenu,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_render.append(menu_render_commander_submenu)


def unregister():
    bpy.types.TOPBAR_MT_render.remove(menu_render_commander_submenu)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
