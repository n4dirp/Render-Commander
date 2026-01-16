# ./operators/operators.py

import logging

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, BoolProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
)


log = logging.getLogger(__name__)


class RECOM_OT_ContinueSetup(Operator):
    """Mark initial setup as complete after configuring devices"""

    bl_idname = "recom.continue_setup"
    bl_label = "Continue"
    bl_description = "Proceed to the main interface after completing device configuration."

    def execute(self, context):
        prefs = get_addon_preferences(context)
        prefs.initial_setup_complete = True
        return {"FINISHED"}


class RECOM_OT_ReinitializeDevices(Operator):
    """Reinitialize all Cycles render devices (clean and rescan)"""

    bl_idname = "recom.reinitialize_devices"
    bl_label = "Refresh Device List"
    bl_description = "Clean and rescan all device backends"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        prefs.rescan_all_devices()
        redraw_ui()

        self.report({"INFO"}, "Device list refreshed successfully")
        return {"FINISHED"}


class RECOM_OT_OpenPreferences(Operator):
    bl_idname = "recom.open_pref"
    bl_label = "Open Preferences"
    bl_description = "Open the Render Commander preferences panel"

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
    """Change the directory for additional scripts"""

    bl_idname = "recom.change_scripts_directory"
    bl_label = "Select Scripts Directory"
    bl_description = "Select a new directory containing Python scripts"

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


classes = (
    RECOM_OT_ContinueSetup,
    RECOM_OT_ReinitializeDevices,
    RECOM_OT_OpenPreferences,
    RECOM_OT_ChangeScriptsDirectory,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
