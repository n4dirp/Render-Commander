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
        # layout.popover(panel="RECOM_PT_layout_popup", text="", icon="DOWNARROW_HLT")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout

        wm = context.window_manager
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Launching
        col = layout.column(align=False)

        if settings.disable_render_button:
            box = col.box()
            disable_row = box.row(align=True)
            disable_row.active = False
            disable_row.scale_y = 0.5
            row1 = disable_row.row(align=True)
            row1.alignment = "CENTER"
            row1.label(text=f"Launching...")

        else:
            col.active = _is_render_operator_active(context)

            # Render button
            render_row = col.row(align=True)
            op_render = render_row.operator(
                "recom.background_render",
                text=f"Render",
                icon="CONSOLE",
            )
            op_render.action_type = "RENDER"
            render_row.popover(panel="RECOM_PT_render_option_popup", text="", icon="DOWNARROW_HLT")

        col.separator(factor=0.15)
        export_row = col.row(align=True)
        export_row.operator(
            "recom.export_render_script",
            text=f"Export",
            icon="EXPORT",
        )
        export_row.popover(panel="RECOM_PT_export_option_popup", text="", icon="DOWNARROW_HLT")

        # Render Mode
        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False

        col.prop(prefs, "launch_mode", text="Mode", expand=True)

        if prefs.launch_mode == MODE_LIST:
            col.prop(settings, "frame_list", text="Frames", placeholder="1, 2, 5-8")


class RECOM_PT_RenderOptionsPopup(Panel):
    bl_label = "Render Options"
    bl_idname = "RECOM_PT_render_option_popup"
    bl_options = {"INSTANCED"}
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column(heading="Launch Options")
        col.prop(prefs, "auto_open_output_folder", text="Open Output Folder")
        col.prop(prefs, "exit_active_session", text="Exit Blender Session")


class RECOM_PT_ExportOptionsPopup(Panel):
    bl_label = "Export Options"
    bl_idname = "RECOM_PT_export_option_popup"
    bl_options = {"INSTANCED"}
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column(heading="Export Options")
        col.prop(prefs, "auto_open_exported_folder", text="Open Scripts Folder")
        col.prop(prefs, "export_master_script", text="Export Master Script")

        col = layout.column(heading="Save location")
        col.prop(prefs, "export_output_target", text="")

        if prefs.export_output_target == "CUSTOM_PATH":
            col.prop(prefs, "custom_export_path", text="", placeholder="Custom Path")


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

    render_image = row.operator(
        "recom.background_render",
        text=f"Render Commander: Render {mode_name}",
        icon="CONSOLE",
    )
    render_image.action_type = "RENDER"


class RECOM_MT_RenderCommanderMenu(bpy.types.Menu):
    bl_label = "Render Commander"
    bl_idname = "RECOM_MT_render_commander_menu"

    def draw(self, context):
        layout = self.layout

        layout.operator("recom.render_image", text="Render Image", icon="RENDER_STILL")
        layout.operator("recom.render_animation", text="Render Animation", icon="RENDER_ANIMATION")
        layout.separator()
        layout.operator("recom.export_image", text="Export Image Render", icon="EXPORT")
        layout.operator("recom.export_animation", text="Export Animation Render")


def menu_render_commander_submenu(self, context):
    self.layout.separator()
    self.layout.menu("RECOM_MT_render_commander_menu", text="Render Commander", icon="CONSOLE")


classes = (
    RECOM_PT_MainPanel,
    RECOM_PT_RenderOptionsPopup,
    RECOM_PT_ExportOptionsPopup,
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
