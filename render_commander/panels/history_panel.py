# ./panels/history_panel.py

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import RCBasePanel, RCSubPanel
from ..utils.helpers import get_addon_preferences, get_addon_settings


class RECOM_PT_render_history_panel(RCSubPanel, Panel):
    bl_label = "History"
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
            rows=3,
            item_dyntip_propname="tooltip_display",
        )

        col = row.column(align=True)
        col.active = len(prefs.render_history) > 0
        col.menu("RECOM_MT_render_history_item", text="", icon="DOWNARROW_HLT")
        valid_index = (
            prefs.render_history
            and prefs.active_render_history_index >= 0
            and prefs.active_render_history_index < len(prefs.render_history)
        )
        if valid_index:
            active_item = prefs.render_history[prefs.active_render_history_index]
            col.separator()
            op = col.operator("recom.open_output_folder", text="", icon="FILE_FOLDER")
            op.folder_path = active_item.export_path


class RECOM_PT_render_details_panel(RCBasePanel, Panel):
    bl_label = "Details"
    bl_parent_id = "RECOM_PT_render_history_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return (
            prefs.render_history
            and len(prefs.render_history) > 0
            and prefs.active_render_history_index >= 0
            and prefs.active_render_history_index < len(prefs.render_history)
        )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)
        settings = get_addon_settings(context)

        layout.template_list(
            "RECOM_UL_active_item_properties",
            "",
            prefs,
            "active_item_properties",
            settings,
            "item_properties_index",
            rows=3,
            item_dyntip_propname="tooltip",
        )


class RECOM_UL_render_history(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.label(text=item.blend_file_name)
        sub = row.row(align=True)
        sub.active = False
        sub.alignment = "RIGHT"
        sub.label(text=item.render_id)

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


class RECOM_UL_active_item_properties(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=0.45)
        split.label(text=item.name)
        split.label(text=item.value)


classes = (
    RECOM_PT_render_history_panel,
    RECOM_PT_render_details_panel,
    RECOM_UL_render_history,
    RECOM_UL_active_item_properties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
