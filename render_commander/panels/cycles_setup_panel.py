# ./panels/cycles_setup_panel.py

import os

import bpy
from bpy.types import Panel

from ..preferences import get_addon_preferences, RECOM_Preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


class RECOM_PT_CyclesSetup(Panel):
    """Initial Setup Cycles Render Devices"""

    bl_label = "Render Commander"
    bl_idname = "RECOM_PT_bg_render_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES" and not prefs.initial_setup_complete

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        col = layout.column()

        """
        info_box = col.box().column()
        info_box.label(text="Initial Setup")
        col.separator(factor=0.5)
        """

        devices_box = col.box()

        col_box = devices_box.column()

        title_row = col_box.row()
        title_row.label(text="Compute Devices")

        sync_row = title_row.row(align=True)
        sync_row.alignment = "RIGHT"
        sync_row.operator("recom.import_from_cycles_settings", text="", icon=ICON_SYNC, emboss=False)

        row = col_box.row()
        row.prop(prefs, "compute_device_type", expand=True)

        if prefs.compute_device_type != "NONE":
            col_box.separator(factor=0.5)
            devices_to_display_list = prefs.get_devices_for_display()
            col_dev = col_box.box().column()
            prefs._draw_devices(col_dev, devices_to_display_list)

        col.separator(factor=0.5)
        col.operator("recom.continue_setup", text=f"Continue{CENTER_TEXT}", icon="CHECKMARK")


classes = (RECOM_PT_CyclesSetup,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
