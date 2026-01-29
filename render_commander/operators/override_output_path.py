import time
import os
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy.props import FloatProperty, StringProperty

from ..preferences import get_addon_preferences
from ..utils.helpers import (
    open_folder,
    logical_width,
    get_nearest_existing_path,
    replace_variables,
)


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
            return context.window_manager.invoke_props_dialog(self, width=logical_width(350))
        else:
            return self.execute(context)

    def draw(self, context):
        layout = self.layout
        folder_path = self.folder_to_create if hasattr(self, "folder_to_create") else "N/A"
        col = layout.column(align=True)

        row = col.row()
        row.alignment = "CENTER"

        # col.label(text=f"Folder does not exist:")
        # col.separator()
        row.label(text="Create folder?")
        row = col.row()
        row.alignment = "CENTER"
        row.label(text=f"'{folder_path}'")

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


class RECOM_OT_ShowTooltip(Operator):
    """Update and display the resolved output path"""

    bl_idname = "recom.show_tooltip"
    bl_label = "Show Full Path"
    bl_description = "Resolved Oputput Path"

    _last_click_time = 0.0
    _double_click_delay = 0.3  # seconds

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        now = time.time()

        if now - RECOM_OT_ShowTooltip._last_click_time < self._double_click_delay:
            # Double click: Show popup
            folder = settings.override_settings.resolved_directory
            filename = settings.override_settings.resolved_filename
            text_to_show = str(Path(folder) / filename)

            if not filename:
                # Build the folder path first
                text_to_show = str(Path(folder))
                sep = os.sep  # '\\' on Windows, '/' elsewhere
                # Add a single trailing separator only when missing
                if not text_to_show.endswith(sep):
                    text_to_show += sep

            context.window_manager.popup_menu(
                lambda self, context: self.layout.label(text=f"{text_to_show}", icon="FILEBROWSER"),
                title="Resolved Output Path",
            )
        else:
            # Single click: Refresh only
            settings.override_settings.on_output_path_changed(context)

        # Update last click time
        RECOM_OT_ShowTooltip._last_click_time = now

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


classes = (
    RECOM_OT_SelectOutputDirectory,
    RECOM_OT_OpenFolder,
    RECOM_OT_InsertVariable,
    RECOM_OT_ShowTooltip,
    RECOM_OT_RefreshResolvedPath,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
