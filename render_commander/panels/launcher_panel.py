# ./panels/launcher_panel.py

import bpy
from bpy.types import Panel

from ..utils.constants import RECOM_PT_BasePanel, MODE_LIST
from ..preferences import get_addon_preferences


def _blend_filepath(context):
    settings = context.window_manager.recom_render_settings
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)

    return bool(bpy.data.filepath)


class RECOM_PT_main_panel(RECOM_PT_BasePanel, Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Launcher
        row = layout.row()
        row.active = _blend_filepath(context)
        row.operator("recom.export_render_script", text="Generate Scripts", icon="EXPORT")

        # Mode
        col = layout.column()
        row = col.row()
        row.prop(prefs, "launch_mode", text="Mode", expand=True)
        row.popover(panel="RECOM_PT_panel_visibility_popup", text="", icon="DOWNARROW_HLT")

        # Frame List
        if prefs.launch_mode == MODE_LIST:
            row = layout.row()
            row.use_property_split = True
            row.use_property_decorate = False
            row.prop(settings, "frame_list", text="", placeholder="Frame List")


class RECOM_PT_panel_visibility_popup(Panel):
    """Popup panel to control visibility of addon panels"""

    bl_label = "Panel Visibility"
    bl_description = "Toggle visibility of addon panels"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        layout.label(text="Visible Panels")

        col = layout.column(align=True)
        col.prop(prefs.visible_panels, "external_scene", text="Blend File")
        col.prop(prefs.visible_panels, "override_settings", text="Override Settings")
        col.prop(prefs.visible_panels, "preferences", text="Render Preferences")
        col.prop(prefs.visible_panels, "history", text="Export History")


classes = (
    RECOM_PT_panel_visibility_popup,
    RECOM_PT_main_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
