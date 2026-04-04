# ./panels/cycles_setup_panel.py

import os

import bpy
from bpy.types import Panel

from ..preferences import get_addon_preferences, RECOM_Preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


class RECOM_PT_cycles_setup(Panel):
    """Initial Setup for Cycles Render Devices"""

    bl_label = "Render Commander"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == RE_CYCLES and not prefs.cycles_setup_complete

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        col_box = layout.box().column()

        title_row = col_box.row()
        title_row.label(text="Cycles Compute Devices")

        import_row = title_row.row()
        import_row.alignment = "RIGHT"
        import_row.operator("recom.import_from_cycles_settings", text="", icon=ICON_SYNC)

        row = col_box.row()
        row.prop(prefs, "compute_device_type", expand=True)

        if prefs.compute_device_type != "NONE":
            col_box.separator(factor=0.5)
            devices_to_display_list = prefs.get_devices_for_display()
            col_dev = col_box.box().column()
            prefs._draw_devices(col_dev, devices_to_display_list)

        layout.operator("recom.continue_setup", text="Continue", icon="CHECKMARK")


classes = (RECOM_PT_cycles_setup,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
