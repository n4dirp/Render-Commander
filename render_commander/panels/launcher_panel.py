# ./panels/launcher_panel.py

import bpy
from bpy.types import Panel

from ..utils.constants import MODE_LIST, RCBasePanel
from ..utils.helpers import get_addon_preferences, get_addon_settings
from ..utils.render_summary import build_render_summary, build_render_summary_warnings


def _blend_filepath(context):
    settings = get_addon_settings(context)
    if settings.use_external_blend:
        return bool(settings.external_blend_file_path)

    return bool(bpy.data.filepath)


class RECOM_PT_main_panel(RCBasePanel, Panel):
    """Main panel for background rendering controls"""

    bl_label = "Render Commander"
    # bl_icon = 'CONSOLE'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = get_addon_settings(context)
        prefs = get_addon_preferences(context)

        # Launcher
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.active = _blend_filepath(context)
        text = "Export Render Scripts"
        if prefs.export_output_target == "SELECT_DIR":
            text += "..."
        sub.operator("recom.export_render_script", text=text, icon="EXPORT")
        sub.prop(prefs, "show_export_summary", text="", toggle=False, icon="HIDE_OFF")

        # Render Summary
        if prefs.show_export_summary:
            self._draw_summary(layout, context)

        col = layout.column()
        col.prop(prefs, "launch_mode", text="Render Mode", expand=True)

        # Frame List
        if prefs.launch_mode == MODE_LIST:
            row = col.row()
            row.use_property_split = True
            row.use_property_decorate = False
            row.prop(settings, "frame_list", text="Frames")

    def _draw_summary(self, layout, context):
        warnings = build_render_summary_warnings(context)

        box = layout.box().column(align=True)
        box.label(text="Render Details")
        box.separator(type="LINE")
        rows = build_render_summary(context)
        for label, value in rows:
            split = box.split(factor=0.4)
            split.label(text=label)
            split.label(text=value)

        if warnings:
            box.separator(factor=0.3)
            for text in warnings:
                row = box.row()
                row.alert = True
                row.label(text=text)

        layout.separator(factor=0.5)


classes = (RECOM_PT_main_panel,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
