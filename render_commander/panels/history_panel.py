# ./panels/history_panel.py

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import (
    RECOM_PT_BasePanel,
    RECOM_PT_SubPanel,
    ICON_OPTION,
    RENDER_ENGINE_MAPPING,
)
from ..preferences import get_addon_preferences


class RECOM_PT_render_history_panel(RECOM_PT_SubPanel, Panel):
    bl_label = "Export History"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.history

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
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

        col = row.column(align=True)  # Changed from 'menu_column'
        col.enabled = len(prefs.render_history) > 0
        col.operator("recom.clean_render_history", text="", icon="TRASH")
        col.separator()
        col.menu("RECOM_MT_render_history_item", text="", icon=ICON_OPTION)


class RECOM_PT_render_details_panel(RECOM_PT_BasePanel, Panel):
    bl_label = "Script Details"
    bl_parent_id = "RECOM_PT_render_history_panel"
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
            self.draw_kv(col, "Render ID", active_item.render_id)
            self.draw_kv(col, "Export Date", active_item.date)
            if active_item.worker_count > 1:
                self.draw_kv(col, "Workers", active_item.worker_count)
            self.draw_kv(col, "Script Name", active_item.script_filename)
            self.draw_kv(col, "Path", active_item.export_path, "recom.open_output_folder")

            col.separator(type="LINE", factor=2.0)
            self.draw_kv(col, "Blend Name", active_item.blend_file_name)
            self.draw_kv(col, "Path", active_item.blend_dir, "recom.open_output_folder")

            col.separator(type="LINE", factor=2.0)
            self.draw_kv(col, "Engine", RENDER_ENGINE_MAPPING.get(active_item.render_engine, active_item.render_engine))
            self.draw_kv(col, "Samples", active_item.samples)
            col = layout.column(align=True)
            self.draw_kv(col, "Resolution", f"{active_item.resolution_x} x {active_item.resolution_y} px")
            self.draw_kv(col, "Frame", active_item.frames.replace(" - ", "-"))
            self.draw_kv(col, "Format", active_item.file_format)
            self.draw_kv(col, "Output Path", active_item.output_path)

    def draw_kv(self, layout, label, value, operator=""):
        if not (label and value):
            return

        row = layout.row(align=True)
        split = row.split(factor=0.4)

        # Label column
        col = split.column(align=True)
        col.alignment = "RIGHT"
        col.label(text=label)

        # Value column
        col = split.column(align=True)
        col.alignment = "LEFT"

        if operator:
            op = col.operator(operator, text=str(value))
            op.folder_path = value
        else:
            col.label(text=str(value))


class RECOM_UL_render_history(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.6)
        split.label(text=item.blend_file_name)
        row = split.row(align=True)
        row.active = False
        row.label(text=item.render_id)

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
