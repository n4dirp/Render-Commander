"""
Contains operators designed to specifically modify the active render overrides.
"""

from typing import Any

import bpy
import mathutils
from bpy.props import (
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Operator

from ..utils.helpers import get_addon_preferences, redraw_ui, resolve_blender_path


class RECOM_OT_SetResolution(Operator):
    bl_idname = "recom.set_resolution"
    bl_label = "Set Resolution"
    bl_description = "Set the resolution width or height"
    bl_options = {"INTERNAL"}

    dimension: EnumProperty(
        items=[
            ("X", "Width", "Set the resolution width (X)"),
            ("Y", "Height", "Set the resolution height (Y)"),
        ],
        name="Dimension",
        description="Which resolution dimension to set",
        default="X",
    )

    value: IntProperty(
        name="Value",
        description="The resolution value to set",
    )

    def execute(self, context):
        settings = context.window_manager.recom_render_settings

        # Map dimension to property name
        property_map = {
            "X": "resolution_x",
            "Y": "resolution_y",
        }

        prop_name = property_map.get(self.dimension)
        if prop_name:
            setattr(settings.override_settings, prop_name, self.value)

        return {"FINISHED"}


class RECOM_OT_SwapResolution(Operator):
    """Swap the values of resolution_x and resolution_y."""

    bl_idname = "recom.swap_resolution"
    bl_label = "Swap Width / Height"
    bl_description = "Exchange the current width and height values"
    bl_options = {"INTERNAL"}

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
    bl_options = {"INTERNAL"}

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.custom_render_scale = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveThreshold(Operator):
    bl_idname = "recom.set_adaptive_threshold"
    bl_label = "Set Adaptive Threshold"
    bl_description = "Set Adaptive Threshold"
    bl_options = {"INTERNAL"}

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_threshold = self.value
        return {"FINISHED"}


class RECOM_OT_set_sampling_factor(Operator):
    bl_idname = "recom.set_sampling_factor"
    bl_label = "Set Sampling Factor"
    bl_options = {"UNDO", "INTERNAL"}

    value: FloatProperty()

    def execute(self, context):
        context.window_manager.recom_render_settings.override_settings.cycles.sampling_factor = self.value
        return {"FINISHED"}


class RECOM_OT_SetSamples(Operator):
    bl_idname = "recom.set_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"
    bl_options = {"INTERNAL"}

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveMinSamples(Operator):
    bl_idname = "recom.set_adaptive_min_samples"
    bl_label = "Set Adaptive Min Samples"
    bl_description = "Set Adaptive Min Samples"
    bl_options = {"INTERNAL"}

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_min_samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetTimeLimit(Operator):
    bl_idname = "recom.set_time_limit"
    bl_label = "Set Time Limit"
    bl_description = "Set Time Limit"
    bl_options = {"INTERNAL"}

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.time_limit = self.value
        return {"FINISHED"}


class RECOM_OT_SetTileSize(Operator):
    bl_idname = "recom.set_tile_size"
    bl_label = "Set Tile Size"
    bl_description = "Set Tile Size"
    bl_options = {"INTERNAL"}

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.tile_size = self.value
        return {"FINISHED"}


class RECOM_OT_SetEEVEESamples(Operator):
    bl_idname = "recom.set_eevee_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"
    bl_options = {"INTERNAL"}

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.eevee.samples = self.value
        return {"FINISHED"}


class RECOM_OT_InsertVariable(Operator):
    bl_idname = "recom.insert_variable"
    bl_label = "Insert Variable"
    bl_description = "Insert selected variable into output path"
    bl_options = {"INTERNAL"}

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
        prefs = get_addon_preferences(context)
        separator = "_" if prefs.use_underscore_separator else ""

        if settings.override_settings.variable_insert_target == "DIRECTORY":
            current_dir = settings.override_settings.output_directory
            # Add separator only if the current path is not empty and does not end with '/'
            if current_dir and not current_dir.endswith(("/", "//", "\\")) and current_dir != "":
                settings.override_settings.output_directory = f"{current_dir}{separator}{self.variable}"
            else:
                settings.override_settings.output_directory = f"{current_dir}{self.variable}"

        else:
            current_file = settings.override_settings.output_filename
            # Add separator only if the current path is not empty and does not end with '/'
            if current_file and not current_file.endswith(("/", "//", "\\", ".")) and current_file != "":
                settings.override_settings.output_filename = f"{current_file}{separator}{self.variable}"
            else:
                settings.override_settings.output_filename = f"{current_file}{self.variable}"

        return {"FINISHED"}


# Custom Variables


class RECOM_OT_AddCustomVariable(Operator):
    bl_idname = "recom.add_custom_variable"
    bl_label = "Add Custom Variable"
    bl_description = "Create a simple custom variable"
    bl_options = {"INTERNAL"}

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
    bl_options = {"INTERNAL"}

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


class RECOM_OT_MoveCustomVariable(Operator):
    bl_idname = "recom.move_custom_variable"
    bl_label = "Move Custom Variable"
    bl_description = "Move the selected custom variable up or down in the list"
    bl_options = {"INTERNAL"}

    direction: EnumProperty(
        items=[
            ("UP", "Up", "Move the selected item up"),
            ("DOWN", "Down", "Move the selected item down"),
        ],
        name="Direction",
        description="Direction to move the custom variable",
        default="UP",
    )

    def execute(self, context):
        prefs = get_addon_preferences(context)
        idx = prefs.active_custom_variable_index
        total = len(prefs.custom_variables)

        if self.direction == "UP" and idx > 0:
            prefs.custom_variables.move(idx, idx - 1)
            prefs.active_custom_variable_index -= 1
        elif self.direction == "DOWN" and idx < total - 1:
            prefs.custom_variables.move(idx, idx + 1)
            prefs.active_custom_variable_index += 1

        redraw_ui()
        return {"FINISHED"}


def get_prop_config(val: Any) -> tuple[str, dict]:
    """Returns (prop_type, {attr: value}) for an override item."""
    if isinstance(val, bool):
        return "BOOL", {"value_bool": val}
    if isinstance(val, int):
        return "INT", {"value_int": val}
    if isinstance(val, float):
        return "FLOAT", {"value_float": val}
    if isinstance(val, str):
        return "STRING", {"value_string": val}
    if isinstance(val, mathutils.Vector):
        return "VECTOR_3", {"value_vector_3": [float(v) for v in val[:3]]}
    if isinstance(val, mathutils.Color):
        return "COLOR_4", {"value_color_4": [float(v) for v in val[:3]] + [1.0]}
    if isinstance(val, (list, tuple)):
        if len(val) == 3:
            return "VECTOR_3", {"value_vector_3": [float(v) for v in val]}
        if len(val) == 4:
            return "COLOR_4", {"value_color_4": [float(v) for v in val]}
    return "STRING", {"value_string": str(val)}


class RECOM_OT_add_advanced_property_override(Operator):
    bl_idname = "recom.add_advanced_property_override"
    bl_label = "Add Property Override"
    bl_description = (
        "Creates a new property override. \nIf the input is empty, "
        "it will automatically attempt to use a path from your clipboard."
    )
    bl_options = {"UNDO", "INTERNAL"}

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings
        path = settings.property_path_input.strip()

        if not path:
            cb = context.window_manager.clipboard
            if cb:
                cb_str = cb.strip()
                valid_prefixes = (
                    "bpy.",
                    "scene.",
                    "render.",
                    "view_layer.",
                    "view_layers[",
                    "eevee.",
                    "cycles.",
                    "world.",
                )
                if any(cb_str.startswith(p) for p in valid_prefixes):
                    path = cb_str

        if not path:
            self.report({"WARNING"}, "Please enter a valid data path or copy one to clipboard.")
            return {"CANCELLED"}

        try:
            normalized_path, val = resolve_blender_path(path)
        except Exception as e:
            self.report({"ERROR"}, f"Failed to evaluate path: {e}")
            return {"CANCELLED"}

        item = settings.data_path_overrides.add()
        item.name = normalized_path.rsplit(".", 1)[-1].replace("_", " ").title()
        item.data_path = normalized_path

        prop_type, values = get_prop_config(val)
        item.prop_type = prop_type

        for attr, value in values.items():
            target = getattr(item, attr)
            # Handle RNA array/vector assignment safely
            if hasattr(target, "__setitem__") and not isinstance(value, str):
                for i, v in enumerate(value):
                    target[i] = v
            else:
                setattr(item, attr, value)

        settings.active_data_path_index = len(settings.data_path_overrides) - 1
        settings.property_path_input = ""

        return {"FINISHED"}


class RECOM_OT_remove_advanced_property_override(Operator):
    bl_idname = "recom.remove_advanced_property_override"
    bl_label = "Remove Property Override"
    bl_description = "Remove the currently selected property override from the list."
    bl_options = {"UNDO", "INTERNAL"}

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return len(settings.data_path_overrides) > 0

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings
        idx = settings.active_data_path_index
        settings.data_path_overrides.remove(idx)
        settings.active_data_path_index = max(0, idx - 1)
        return {"FINISHED"}


classes = (
    RECOM_OT_SetResolution,
    RECOM_OT_SwapResolution,
    RECOM_OT_set_custom_render_scale,
    RECOM_OT_set_sampling_factor,
    RECOM_OT_SetAdaptiveThreshold,
    RECOM_OT_SetSamples,
    RECOM_OT_SetAdaptiveMinSamples,
    RECOM_OT_SetTimeLimit,
    RECOM_OT_SetTileSize,
    RECOM_OT_SetEEVEESamples,
    RECOM_OT_InsertVariable,
    RECOM_OT_AddCustomVariable,
    RECOM_OT_RemoveCustomVariable,
    RECOM_OT_MoveCustomVariable,
    RECOM_OT_add_advanced_property_override,
    RECOM_OT_remove_advanced_property_override,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
