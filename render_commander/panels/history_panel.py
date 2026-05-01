# ./panels/history_panel.py

import bpy
from bpy.types import Panel, UIList

from ..utils.constants import (
    ICON_OPTION,
    RCBasePanel,
    RCSubPanel,
)
from ..utils.helpers import get_addon_preferences


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
            rows=4,
            item_dyntip_propname="tooltip_display",
        )

        col = row.column(align=True)  # Changed from 'menu_column'
        col.enabled = len(prefs.render_history) > 0
        col.operator("recom.clean_render_history", text="", icon="TRASH")
        col.separator()
        col.menu("RECOM_MT_render_history_item", text="", icon=ICON_OPTION)


class RECOM_UL_render_history(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        layout.label(text=item.script_filename)

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


class RECOM_PT_active_item_properties_panel(RCBasePanel, Panel):
    bl_label = "Script Details"
    bl_parent_id = "RECOM_PT_render_history_panel"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.render_history and prefs.active_render_history_index >= 0 and len(prefs.active_item_properties) > 0

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        # layout.active = False
        layout.template_list(
            "RECOM_UL_active_item_properties",
            "",
            prefs,
            "active_item_properties",
            prefs,
            "item_properties_index",  # dummy, not used for this list
            rows=4,
            item_dyntip_propname="tooltip",
        )


classes = (
    RECOM_PT_render_history_panel,
    RECOM_UL_render_history,
    RECOM_UL_active_item_properties,
    RECOM_PT_active_item_properties_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
