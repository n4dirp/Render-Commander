# ./panels/main_panel.py

import bpy
from bpy.types import Panel

from ..utils.constants import MODE_LIST
from ..preferences import get_addon_preferences


def _blend_filepath(context):
    settings = context.window_manager.recom_render_settings
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)

    return bool(bpy.data.filepath)


class RECOM_PT_main_panel(Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        # Launcher
        export_row = layout.row(align=True)
        export_row.active = _blend_filepath(context)
        export_row.operator("recom.export_render_script", text="Generate Scripts", icon="EXPORT")

        # Mode
        col = layout.column()
        mode_row = col.row()
        mode_row.prop(prefs, "launch_mode", text="Mode", expand=True)

        # Frame List
        if prefs.launch_mode == MODE_LIST:
            list_col = layout.row()
            list_col.use_property_split = True
            list_col.use_property_decorate = False
            list_col.prop(settings, "frame_list", text="Frame List")


classes = (RECOM_PT_main_panel,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
