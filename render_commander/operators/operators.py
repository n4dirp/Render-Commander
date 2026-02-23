# ./operators/operators.py

import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ..utils.constants import *
from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
)


log = logging.getLogger(__name__)


class RECOM_OT_LoadingButton(Operator):
    bl_idname = "recom.loading_button"
    bl_label = ""
    bl_description = ""

    def execute(self, context):
        return {"FINISHED"}


class RECOM_OT_ContinueSetup(Operator):
    bl_idname = "recom.continue_setup"
    bl_label = "Continue"
    bl_description = "Proceed to the main interface after completing Cycles device configuration."

    def execute(self, context):
        prefs = get_addon_preferences(context)
        prefs.initial_setup_complete = True
        return {"FINISHED"}


class RECOM_OT_ReinitializeDevices(Operator):
    bl_idname = "recom.reinitialize_devices"
    bl_label = "Refresh Device List"
    bl_description = "Reinitialize all Cycles render devices"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        prefs.rescan_all_devices()
        redraw_ui()

        self.report({"INFO"}, "Device list refreshed successfully")
        return {"FINISHED"}


class RECOM_OT_OpenPreferences(Operator):
    bl_idname = "recom.open_pref"
    bl_label = "Open Preferences"
    bl_description = "Open the add-on preferences panel"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        bpy.ops.screen.userpref_show()
        bpy.context.preferences.active_section = "ADDONS"

        wm = context.window_manager
        wm.addon_search = "Render Commander"

        try:
            bpy.ops.preferences.addon_expand(module="render_commander")
        except RuntimeError as e:
            self.report({"WARNING"}, f"Could not expand addon: {e}")

        return {"FINISHED"}


class RECOM_OT_ChangeScriptsDirectory(Operator):
    bl_idname = "recom.change_scripts_directory"
    bl_label = "Select Scripts Directory"
    bl_description = "Change the directory for additional Python scripts"

    directory: StringProperty(
        name="Export Directory",
        description="Directory to read python files",
        subtype="DIR_PATH",
    )

    filter_folder: BoolProperty(
        default=True,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    def execute(self, context):
        prefs = get_addon_preferences(context)
        # The actual path will be handled in invoke
        prefs.scripts_directory = self.directory
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class RECOM_OT_DeviceID(Operator):
    bl_idname = "recom.cycles_device_ids"
    bl_label = "Device ID"
    bl_description = "Displays the unique identifier of the compute devices"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        blender_path = bpy.path.abspath(prefs.custom_executable_path)

        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        layout = self.layout

        prefs = get_addon_preferences(context)

        layout.label(text="Device ID")

        label_col = layout.box().column(align=True)

        prev_type = None
        for device in prefs.get_devices_for_display():
            if prev_type is not None and device.type != prev_type:
                label_col.separator(type="AUTO")

            row = label_col.row(align=True)
            # row.active = False
            icon = "CHECKBOX_HLT" if device.use else "CHECKBOX_DEHLT"
            row.label(text=device.id, icon=icon)

            prev_type = device.type


classes = (
    RECOM_OT_LoadingButton,
    RECOM_OT_ContinueSetup,
    RECOM_OT_ReinitializeDevices,
    RECOM_OT_OpenPreferences,
    RECOM_OT_ChangeScriptsDirectory,
    RECOM_OT_DeviceID,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
