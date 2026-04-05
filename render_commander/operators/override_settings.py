# ./operators/override_settings.py

import time
import os
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty, StringProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    redraw_ui,
)


class RECOM_OT_SetResolutionX(Operator):
    bl_idname = "recom.set_resolution_x"
    bl_label = "Set Resolution Width"
    bl_description = "Set Resolution Width"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.resolution_x = self.value
        return {"FINISHED"}


class RECOM_OT_SetResolutionY(Operator):
    bl_idname = "recom.set_resolution_y"
    bl_label = "Set Resolution Height"
    bl_description = "Set Resolution Height"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.resolution_y = self.value
        return {"FINISHED"}


class RECOM_OT_SwapResolution(Operator):
    """Swap the values of resolution_x and resolution_y."""

    bl_idname = "recom.swap_resolution"
    bl_label = "Swap Width / Height"
    bl_description = "Exchange the current width and height values"

    def execute(self, context):
        rs = context.window_manager.recom_render_settings.override_settings

        x = rs.resolution_x
        y = rs.resolution_y

        rs.resolution_x = y
        rs.resolution_y = x

        return {"FINISHED"}


class RECOM_OT_set_custom_render_scale(Operator):
    """Set Custom Render Scale"""

    bl_idname = "recom.set_custom_render_scale"
    bl_label = "Set Custom Render Scale"

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.custom_render_scale = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveThreshold(Operator):
    bl_idname = "recom.set_adaptive_threshold"
    bl_label = "Set Adaptive Threshold"
    bl_description = "Set Adaptive Threshold"

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_threshold = self.value
        return {"FINISHED"}


class RECOM_OT_SetSamples(Operator):
    bl_idname = "recom.set_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveMinSamples(Operator):
    bl_idname = "recom.set_adaptive_min_samples"
    bl_label = "Set Adaptive Min Samples"
    bl_description = "Set Adaptive Min Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_min_samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetTimeLimit(Operator):
    bl_idname = "recom.set_time_limit"
    bl_label = "Set Time Limit"
    bl_description = "Set Time Limit"

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.time_limit = self.value
        return {"FINISHED"}


class RECOM_OT_SetTileSize(Operator):
    bl_idname = "recom.set_tile_size"
    bl_label = "Set Tile Size"
    bl_description = "Set Tile Size"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.tile_size = self.value
        return {"FINISHED"}


class RECOM_OT_SetEEVEESamples(Operator):
    bl_idname = "recom.set_eevee_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.eevee.samples = self.value
        return {"FINISHED"}


class RECOM_OT_SelectOutputDirectory(Operator):
    bl_idname = "recom.select_output_directory"
    bl_description = "Open a file explorer"
    bl_label = "Output Directory"

    directory: StringProperty(subtype="DIR_PATH")

    def execute(self, context):
        """Called after the user picks a file."""
        settings = context.window_manager.recom_render_settings
        abs_path = Path(bpy.path.abspath(self.directory))
        settings.override_settings.output_directory = str(abs_path)

        self.report({"INFO"}, f"Output directory set to: {abs_path}")
        return {"FINISHED"}

    def invoke(self, context, event):
        """Open the file browser when the operator is invoked"""
        wm = context.window_manager
        settings = context.window_manager.recom_render_settings

        try:
            # Resolve the current output directory (may contain variables)
            resolved_dir_str = replace_variables(settings.override_settings.output_directory)
            path_obj = Path(resolved_dir_str)
        except AttributeError:
            path_obj = Path()

        # Check if path exists and is a directory
        if path_obj.exists() and path_obj.is_dir():
            start_path = path_obj
        else:
            nearest_path = get_nearest_existing_path(resolved_dir_str)
            if nearest_path:
                start_path = nearest_path
            else:
                start_path = Path.home()

        abs_start_path = Path(bpy.path.abspath(str(start_path))).resolve()
        self.directory = str(abs_start_path)

        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


class RECOM_OT_OpenFolder(Operator):
    """Open or create output folder directory"""

    bl_idname = "recom.open_folder"
    bl_label = "Open Output Path"
    bl_description = "Open the resolved output directory"

    folder_to_create: StringProperty()

    def invoke(self, context, event):
        settings = context.window_manager.recom_render_settings
        # Resolve the output path
        settings.override_settings.on_output_path_changed(context)

        full_path = settings.override_settings.resolved_directory

        if not full_path or full_path in ["Unknown", "Preview disabled"] or full_path.startswith("Error"):
            self.report({"WARNING"}, "Path is invalid.")
            return {"CANCELLED"}

        folder_path = Path(full_path)
        self.folder_to_create = str(folder_path)

        # Check if the directory exists
        if not folder_path.exists():
            return context.window_manager.invoke_props_dialog(self, width=400)
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        folder_path = self.folder_to_create if hasattr(self, "folder_to_create") else "N/A"

        col = layout.column(align=True)

        row = col.row()
        row.alignment = "CENTER"
        row.label(text="Create folder?")
        col.separator(factor=0.5)
        row = col.box().row(align=True)
        tooltip_row = row.row(align=True)

        tooltip_row.operator("recom.show_tooltip", text=self.folder_to_create, emboss=False)

    def execute(self, context):
        open_folder(self.folder_to_create)

        return {"FINISHED"}


class RECOM_OT_InsertVariable(Operator):
    """Insert variables into output paths"""

    bl_idname = "recom.insert_variable"
    bl_label = "Insert Variable"
    bl_description = "Insert selected variable into output path"

    variable: StringProperty(
        name="Variable",
        description="The variable to insert (e.g., {SCENE})",
    )

    @classmethod
    def description(cls, context, properties):
        # 'properties' contains operator properties like my_value
        return f"Add '{properties.variable}' to the output path"

    def execute(self, context):
        """Inserts selected variable into the specified path component"""

        settings = context.window_manager.recom_render_settings

        if settings.override_settings.variable_insert_target == "DIRECTORY":
            current_dir = settings.override_settings.output_directory
            # Add separator only if the current path is not empty and does not end with '/'
            if current_dir and not current_dir.endswith(("/", "//", "\\")) and current_dir != "":
                settings.override_settings.output_directory = f"{current_dir}_{self.variable}"
            else:
                settings.override_settings.output_directory = f"{current_dir}{self.variable}"

        else:
            current_file = settings.override_settings.output_filename
            # Add separator only if the current path is not empty and does not end with '/'
            if current_file and not current_file.endswith(("/", "//", "\\")) and current_file != "":
                settings.override_settings.output_filename = f"{current_file}_{self.variable}"
            else:
                settings.override_settings.output_filename = f"{current_file}{self.variable}"

        # Trigger path update after inserting
        settings.override_settings.on_output_path_changed(context)
        return {"FINISHED"}


class RECOM_OT_RefreshResolvedPath(Operator):
    """Force update of resolved output path"""

    bl_idname = "recom.refresh_resolved_path"
    bl_label = "Refresh Resolved Path"
    bl_description = "Update the resolved output path"

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        # Reset cached values
        settings.override_settings.resolved_directory = ""
        settings.override_settings.resolved_filename = ""
        settings.override_settings.on_output_path_changed(context)
        resolved_path = (
            Path(settings.override_settings.resolved_directory) / settings.override_settings.resolved_filename
        )

        if settings.override_settings.resolved_directory:
            self.report({"INFO"}, f"Resolved Path Updated '{resolved_path}'")
        return {"FINISHED"}


# Custom Variables


class RECOM_OT_AddCustomVariable(Operator):
    bl_idname = "recom.add_custom_variable"
    bl_label = "Add Custom Variable"
    bl_description = "Create a simple custom variable"

    def execute(self, context):
        prefs = get_addon_preferences(context)

        existing = prefs.custom_variables

        base_name = "name"
        base_token = "token"
        base_value = "value"

        idx = 1
        while (
            any(item.name == f"{base_name}_{idx}" for item in existing)
            or any(item.token == f"{base_token}_{idx}" for item in existing)
            or any(item.value == f"{base_value}_{idx}" for item in existing)
        ):
            idx += 1

        new_item = prefs.custom_variables.add()
        new_item.name = f"{base_name}_{idx}"
        new_item.token = f"{base_token}_{idx}"
        new_item.value = f"{base_value}_{idx}"

        prefs.active_custom_variable_index = len(prefs.custom_variables) - 1
        return {"FINISHED"}


class RECOM_OT_RemoveCustomVariable(Operator):
    bl_idname = "recom.remove_custom_variable"
    bl_label = "Remove Custom Variable"
    bl_description = "Remove active item from list"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index
        if idx >= 0:
            prefs.custom_variables.remove(idx)
            # Check if the collection is now empty
            if len(prefs.custom_variables) == 0:
                prefs.active_custom_variable_index = -1
            else:
                # Update the active index
                prefs.active_custom_variable_index = max(0, idx - 1)
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_MoveCustomVariableUp(Operator):
    bl_idname = "recom.move_custom_variable_up"
    bl_label = "Move Up"
    bl_description = "Move the selected custom variable up in the list"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index

        if idx > 0:
            # Swap with the previous item
            prefs.custom_variables.move(idx, idx - 1)
            prefs.active_custom_variable_index -= 1

        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_MoveCustomVariableDown(Operator):
    bl_idname = "recom.move_custom_variable_down"
    bl_label = "Move Down"
    bl_description = "Move the selected custom variable down in the list"

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index

        if idx < len(prefs.custom_variables) - 1:
            # Swap with the next item
            prefs.custom_variables.move(idx, idx + 1)
            prefs.active_custom_variable_index += 1

        redraw_ui()
        return {"FINISHED"}


classes = (
    RECOM_OT_SetResolutionX,
    RECOM_OT_SetResolutionY,
    RECOM_OT_SwapResolution,
    RECOM_OT_set_custom_render_scale,
    RECOM_OT_SetAdaptiveThreshold,
    RECOM_OT_SetSamples,
    RECOM_OT_SetAdaptiveMinSamples,
    RECOM_OT_SetTimeLimit,
    RECOM_OT_SetTileSize,
    RECOM_OT_SetEEVEESamples,
    RECOM_OT_SelectOutputDirectory,
    RECOM_OT_OpenFolder,
    RECOM_OT_InsertVariable,
    RECOM_OT_RefreshResolvedPath,
    RECOM_OT_AddCustomVariable,
    RECOM_OT_RemoveCustomVariable,
    RECOM_OT_MoveCustomVariableUp,
    RECOM_OT_MoveCustomVariableDown,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
