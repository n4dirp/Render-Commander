# ./panels/launcher_panel.py

import bpy
from bpy.types import Panel

from ..utils.constants import MODE_LIST, RCBasePanel
from ..utils.helpers import get_addon_preferences, get_addon_settings


def _blend_filepath(context):
    settings = get_addon_settings(context)
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)

    return bool(bpy.data.filepath)


class RECOM_PT_main_panel(RCBasePanel, Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"

    def draw(self, context):
        layout = self.layout
        settings = get_addon_settings(context)
        prefs = get_addon_preferences(context)

        # Launcher
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.active = _blend_filepath(context)
        text = "Export"
        if prefs.export_output_target == "SELECT_DIR":
            text += "..."
        sub.operator("recom.export_render_script", text=text, icon="EXPORT")
        row.popover(panel="RECOM_PT_panel_visibility_popup", text="", icon="DOWNARROW_HLT")

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
    bl_ui_units_x = 11

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

        if prefs.export_output_target != "SELECT_DIR":
            col.separator()
            col = layout.column()
            col.label(text="Add Subfolder")
            folder_row = col.row(heading="", align=True)
            folder_row.prop(prefs, "export_scripts_subfolder", text="")
            sub_folder_row = folder_row.row()
            sub_folder_row.active = prefs.export_scripts_subfolder
            sub_folder_row.prop(prefs, "export_scripts_folder_name", text="", placeholder="Folder Name")

            col.separator()
            col = layout.column(align=True)
            col.label(text="Script Naming")

            row = col.row(align=True)
            row.prop(prefs, "use_export_date_in_script", text="Export Date")
            row.prop(prefs, "use_blend_name_in_script", text="Blend Name")
            row = col.row(align=True)
            row.prop(prefs, "use_render_type_in_script", text="Render Mode")
            row.prop(prefs, "use_frame_range_in_script", text="Frame Range")

            tag_row = col.row(align=True)
            tag_row.prop(prefs, "custom_script_tag", text="")
            tag_input = tag_row.row(align=True)
            tag_input.enabled = prefs.custom_script_tag
            tag_input.prop(prefs, "custom_script_text", text="", placeholder="Custom Tag")

            col.separator()
            col = layout.column(heading="Actions", align=True)
            col.prop(prefs, "auto_open_exported_folder", text="Open in File Explorer")

        col.separator()
        col = layout.column()
        col.label(text="Visible Panels")
        row = col.row(align=True)
        col1 = row.column(align=True)
        col1.label(text="Blend File", icon="FILE_BLEND")
        col1.label(text="Overrides", icon="MODIFIER_DATA")
        col1.label(text="Settings", icon="SETTINGS")
        col1.label(text="History", icon="EXPORT")

        col2 = row.column(align=True)
        col2.prop(prefs.visible_panels, "external_scene", text="")
        col2.prop(prefs.visible_panels, "override_settings", text="")
        col2.prop(prefs.visible_panels, "preferences", text="")
        col2.prop(prefs.visible_panels, "history", text="")

        col.separator()
        layout.operator("recom.open_pref", text="Preferences", icon="PREFERENCES")


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
