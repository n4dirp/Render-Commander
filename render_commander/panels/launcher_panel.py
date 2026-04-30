# ./panels/launcher_panel.py

import bpy
from bpy.types import Panel

from ..operators.background_render import draw_script_filename
from ..preferences import get_addon_preferences
from ..utils.constants import MODE_LIST, RCBasePanel


def _blend_filepath(context):
    settings = context.window_manager.recom_render_settings
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)

    return bool(bpy.data.filepath)


class RECOM_PT_main_panel(RCBasePanel, Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Launcher
        row = layout.row(align=True)
        row.active = _blend_filepath(context)
        text = "Export"  # Generate Scripts
        if prefs.export_output_target == "SELECT_DIR":
            text += "..."
        row.operator("recom.export_render_script", text=text, icon="EXPORT")
        row.popover(
            panel="RECOM_PT_panel_visibility_popup", text="", icon="DOWNARROW_HLT"
        )

        # Mode
        col = layout.column()
        row = col.row()
        row.prop(prefs, "launch_mode", text="Mode", expand=True)

        # Frame List
        if prefs.launch_mode == MODE_LIST:
            row = col.row()
            row.use_property_split = True
            row.use_property_decorate = False
            row.prop(settings, "frame_list", text="", placeholder="Frame List")


class RECOM_PT_panel_visibility_popup(Panel):
    bl_label = "Options"
    bl_description = ""
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        col = layout.column()
        col.label(text="Export Options")

        col = layout.column()
        col.label(text="Target")
        sub = col.row()
        sub.prop(prefs, "export_output_target", expand=True)
        if prefs.export_output_target == "CUSTOM_PATH":
            col.prop(prefs, "custom_export_path", text="", placeholder="Path")

        col = layout.column()
        col.label(text="Add Subfolder")
        folder_row = col.row(heading="", align=True)
        folder_row.prop(prefs, "export_scripts_subfolder", text="")
        sub_folder_row = folder_row.row()
        sub_folder_row.active = prefs.export_scripts_subfolder
        sub_folder_row.prop(
            prefs, "export_scripts_folder_name", text="", placeholder="Folder Name"
        )

        col.separator()
        col = layout.column(align=True)
        col.label(text="Script Naming")
        draw_script_filename(col, prefs)

        col.separator()
        col = layout.column(heading="Actions", align=True)
        col.prop(prefs, "auto_open_exported_folder", text="Open in File Explorer")

        # return

        layout.separator(type="LINE")

        col = layout.column(align=True, heading="Visible Panels")
        col.prop(prefs.visible_panels, "external_scene", text="Blend File")
        col.prop(prefs.visible_panels, "override_settings", text="Override Settings")
        col.prop(prefs.visible_panels, "preferences", text="Render Preferences")
        col.prop(prefs.visible_panels, "history", text="Export History")

        # Debugging
        col = layout.column(heading="Debug")
        col.prop(prefs, "debug_mode", text="Console Logging")


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
