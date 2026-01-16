# ./panels/history_panel.py

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import logical_width, get_render_engine


class RECOM_PT_RenderHistoryPanel(Panel):
    bl_label = "History"
    bl_idname = "RECOM_PT_render_history_panel"
    # bl_parent_id = "RECOM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (prefs.initial_setup_complete if render_engine == "CYCLES" else True) and prefs.visible_panels.history

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        row = layout.row(align=True)
        row.active = len(prefs.render_history) > 0
        # row.menu("RECOM_MT_render_history", text="", icon="COLLAPSEMENU")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        render_history = prefs.render_history

        row = layout.row()

        list_row = row.row(align=True)
        list_row.template_list(
            "RECOM_UL_RenderHistory",
            "",
            prefs,
            "render_history",
            prefs,
            "active_render_history_index",
            rows=4,
        )

        menu_row = row.column(align=True)
        menu_row.active = len(prefs.render_history) > 0
        menu_row.menu("RECOM_MT_render_history_item", text="", icon="DOWNARROW_HLT")
        menu_row.separator()
        menu_row.menu("RECOM_MT_render_history", text="", icon="COLLAPSEMENU")


class RECOM_PT_RenderDetailsPanel(Panel):
    bl_label = "Details"
    bl_idname = "RECOM_PT_render_details_panel"
    bl_parent_id = "RECOM_PT_render_history_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    # bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.render_history and len(prefs.render_history) > 0 and prefs.visible_panels.render_details

    def draw_header_preset(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        row = layout.row()
        row.active = len(prefs.render_history) > 0
        # row.menu("RECOM_MT_render_history_item", text="", icon="DOWNARROW_HLT")
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        if prefs.render_history and len(prefs.render_history) > 0:
            active_item = prefs.render_history[prefs.active_render_history_index]

            detail_box = layout.box()
            row = detail_box.row(align=True)
            row.separator(factor=0.5)

            col = row.column(align=True)
            col.active = False
            col.label(text=f"Blend File: {active_item.blend_file_name}")
            col.label(text=f"Blend Folder: {active_item.blend_dir}")

            col.label(text=f"Render ID: {active_item.render_id}")
            col.label(text=f"Date: {active_item.date}")
            col.label(text=f"Mode: {active_item.launch_mode}")
            col.label(text=f"Engine: {active_item.render_engine}")
            col.label(text=f"Frame: {active_item.frames.replace(' - ', '-')}")
            col.label(text=f"Resolution: {active_item.resolution_x} x {active_item.resolution_y} px")
            col.label(text=f"Samples: {active_item.samples}")
            col.label(text=f"Format: {active_item.file_format}")
            col.label(text=f"Output Folder: {active_item.output_folder}")
            col.label(text=f"Output Filename: {active_item.output_filename}")


class RECOM_UL_RenderHistory(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.6)
        col1 = split.column()
        col2 = split.column()

        row = col1.row(align=True)
        # row.label(text="", icon="FILE_BLEND")
        row.label(text=item.blend_file_name)

        sub_row = col2.row(align=True)
        sub_row.active = False
        # sub_row.alignment = "RIGHT"
        sub_row.label(text=item.render_id)

    def filter_items(self, context, data, propname):
        search_text = self.filter_name.lower().strip() if self.filter_name else ""
        items = getattr(data, propname)

        flt_flags = [self.bitflag_filter_item] * len(items)
        if not search_text:
            return flt_flags, []

        search_text = search_text.lower()

        for i, item in enumerate(items):
            match = False
            if search_text in item.blend_file_name.lower():
                match = True

            elif search_text in item.frames.replace(" - ", "-").lower():
                match = True
            elif search_text in item.render_id.lower():
                match = True

            flt_flags[i] = self.bitflag_filter_item if match else 0

        return flt_flags, []


classes = (
    RECOM_PT_RenderHistoryPanel,
    RECOM_UL_RenderHistory,
    RECOM_PT_RenderDetailsPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
