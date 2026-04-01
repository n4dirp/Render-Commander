# ./panels/history_panel.py

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import logical_width, get_render_engine


class RECOM_PT_render_history_panel(Panel):
    bl_label = "History"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (prefs.initial_setup_complete if render_engine == RE_CYCLES else True) and prefs.visible_panels.history

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
        render_history = prefs.render_history

        row = layout.row()

        list_row = row.row(align=True)
        list_row.template_list(
            "RECOM_UL_render_history",
            "",
            prefs,
            "render_history",
            prefs,
            "active_render_history_index",
            rows=4,
            item_dyntip_propname="tooltip_display",
        )

        menu_column = row.column(align=True)
        menu_column.enabled = len(prefs.render_history) > 0
        # menu_column.operator("recom.clean_render_history", text="", icon="TRASH")
        menu_column.menu("RECOM_MT_render_history", text="", icon="COLLAPSEMENU")

        menu_column.separator()
        menu_column.menu("RECOM_MT_render_history_item", text="", icon="DOWNARROW_HLT")


def draw_kv(layout, label, value, operator=""):
    if label and value:
        row = layout.row(align=True)
        split = row.split(factor=0.4)
        row1 = split.row(align=True)
        row1.alignment = "RIGHT"
        row2 = split.row()
        row1.label(text=label)
        if operator:
            row2.alignment = "LEFT"
            op_folder = row2.operator(operator, text=f"{value}", icon="FILE_FOLDER")
            op_folder.folder_path = value
        else:
            row2.label(text=str(value))


class RECOM_PT_render_details_panel(Panel):
    bl_label = "Render Details"
    bl_parent_id = "RECOM_PT_render_history_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    # bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.render_history and len(prefs.render_history) > 0

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        if prefs.render_history and len(prefs.render_history) > 0:
            active_item = prefs.render_history[prefs.active_render_history_index]

            col = layout.column(align=True)

            draw_kv(col, "Blend File", active_item.blend_file_name)
            draw_kv(col, "Blend Directory", active_item.blend_dir, "recom.open_output_folder")
            col.separator(type="AUTO")
            draw_kv(col, "Render ID", active_item.render_id)
            draw_kv(col, "Render Date", active_item.date)
            col.separator(type="AUTO")
            draw_kv(col, "Engine", RENDER_ENGINE_MAPPING.get(active_item.render_engine, active_item.render_engine))
            draw_kv(col, "Samples", active_item.samples)
            col.separator(type="AUTO")
            draw_kv(col, "Resolution", f"{active_item.resolution_x} x {active_item.resolution_y} px")
            draw_kv(col, "Frame", active_item.frames.replace(" - ", "-"))
            draw_kv(col, "Format", active_item.file_format)
            draw_kv(col, "Output", active_item.output_folder, "recom.open_output_folder")
            draw_kv(col, "Filename", active_item.output_filename)


class RECOM_UL_render_history(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.6)
        col1 = split.column()
        col2 = split.column()

        row = col1.row(align=True)
        row.label(text=item.blend_file_name)

        sub_row = col2.row(align=True)
        sub_row.active = False
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
    RECOM_PT_render_history_panel,
    RECOM_UL_render_history,
    RECOM_PT_render_details_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
