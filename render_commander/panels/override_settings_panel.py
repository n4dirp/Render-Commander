# ./panels/override_settings_panel.py

from pathlib import Path

import bpy
from bpy.types import Panel, UIList, Menu, Operator
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import (
    get_default_resolution,
    calculate_auto_width,
    calculate_auto_height,
    get_render_engine,
    redraw_ui,
)

# -------------------------------------------------------------------
#  CONSTANTS & MAPPING
# -------------------------------------------------------------------

# Map: Group -> ID -> (Label, Property Name, Icon)
OVERRIDE_MAP = {
    "Render": {
        "cycles_device": ("Cycles - Compute Device", "cycles.device_override", "BLANK1"),
        "cycles_sampling": ("Cycles - Sampling", "cycles.sampling_override", "BLANK1"),
        "cycles_light_paths": ("Cycles - Light Paths", "cycles.light_path_override", "BLANK1"),
        "cycles_performance": ("Cycles - Performance", "cycles.performance_override", "BLANK1"),
        "eevee_all": ("EEVEE", "eevee_override", "BLANK1"),
        "motion_blur": ("Motion Blur", "motion_blur_override", "BLANK1"),
    },
    "Output": {
        "resolution": ("Resolution", "format_override", "BLANK1"),
        "frame_range": ("Frame Range", "frame_range_override", "BLANK1"),
        "output_path": ("Output Path", "output_path_override", "BLANK1"),
        "file_format": ("File Format", "file_format_override", "BLANK1"),
    },
    "Data": {
        "camera_settings": ("Camera", "cameras_override", "BLANK1"),
        "compositor": ("Compositing", "compositor_override", "BLANK1"),
        "custom_api": ("Advanced Properties", "use_custom_api_overrides", "BLANK1"),
    },
}

# Data for Path Variables Menu
PATH_VARIABLES_DATA = {
    "data": [
        ("{scene_name}", "Scene Name", "SCENE_DATA"),
        ("{view_name}", "View Layer Name", "RENDERLAYERS"),
        ("", "", None),
        ("{engine}", "Render Engine", "SCENE"),
        ("", "", None),
        ("{thresh}", "Cycles Noise Threshold", "BLANK1"),
        ("{samples}", "Cycles Samples", "BLANK1"),
        ("", "", None),
        ("{view_transform}", "View Transform", "BLANK1"),
        ("{look}", "Color Look", "BLANK1"),
        ("", "", None),
        ("{camera_name}", "Camera Name", "CAMERA_DATA"),
        ("{camera_lens}", "Camera Focal Length", "BLANK1"),
        ("{camera_sensor}", "Camera Sensor Width", "BLANK1"),
        ("", "", None),
        ("{blend_dir}", "Blend Directory", "FILE_BLEND"),
        ("{blend_name}", "Blend Name", "BLANK1"),
        ("", "", None),
        ("{bl_ver}", "Blender Version (Render)", "BLANK1"),
    ],
    "output": [
        ("{frame_start}", "Frame Start", "PREVIEW_RANGE"),
        ("{frame_end}", "Frame End", "BLANK1"),
        ("{frame_step}", "Frame Step", "BLANK1"),
        ("{fps}", "Frame Rate", "BLANK1"),
        ("", "", None),
        ("{resolution}", "Resolution (WxH)", "IMAGE_DATA"),
        ("{resolution_width}", "Resolution Width", "BLANK1"),
        ("{resolution_height}", "Resolution Height", "BLANK1"),
        ("{resolution_scale}", "Resolution Percentage", "BLANK1"),
        ("{aspect}", "Aspect Ratio", "BLANK1"),
        ("", "", None),
        ("{file_format}", "File Format", "FILE_IMAGE"),
    ],
    "system": [
        ("{user}", "User Name", "BLANK1"),
        ("{host}", "Hostname", "BLANK1"),
        ("{os}", "Operating System", "BLANK1"),
        ("", "", None),
        ("{date}", "Date (Y-M-D)", "BLANK1"),
        ("{time}", "Time (H-M-S)", "BLANK1"),
        ("{year}", "Year", "BLANK1"),
        ("{month}", "Month", "BLANK1"),
        ("{day}", "Day", "BLANK1"),
    ],
}


# -------------------------------------------------------------------
#  HELPERS
# -------------------------------------------------------------------


def get_override_tuple(override_id):
    """Finds the configuration tuple for a given ID in the nested map."""
    for group_items in OVERRIDE_MAP.values():
        if override_id in group_items:
            return group_items[override_id]
    return None


def resolve_override_prop(settings, prop_path):
    """
    Resolves 'cycles.device_override' to (parent_obj, 'device_override').
    Returns (target_object, attribute_name).
    """
    if "." in prop_path:
        base, sub = prop_path.split(".", 1)
        target = getattr(settings, base)
        return target, sub
    return settings, prop_path


def is_override_active(settings, prop_path):
    """Checks if a specific override property is currently True."""
    target, attr = resolve_override_prop(settings, prop_path)
    return getattr(target, attr)


def set_override_state(settings, prop_path, state):
    """Sets an override property to True/False."""
    target, attr = resolve_override_prop(settings, prop_path)
    setattr(target, attr, state)


def iterate_all_overrides():
    """Generator that yields (id, label, prop_path, icon) for every item."""
    for group_name, items in OVERRIDE_MAP.items():
        for oid, data in items.items():
            yield oid, data[0], data[1], data[2]


# -------------------------------------------------------------------
#  OPERATORS & MENUS
# -------------------------------------------------------------------


class RECOM_OT_manage_override(Operator):
    """Add or Remove a scene override"""

    bl_idname = "recom.manage_override"
    bl_label = "Manage Override"
    bl_options = {"UNDO"}

    action: bpy.props.EnumProperty(items=[("ADD", "Add", ""), ("REMOVE", "Remove", "")], default="ADD")
    override_id: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings

        # Helper lookup
        data = get_override_tuple(self.override_id)
        if not data:
            return {"CANCELLED"}

        prop_path = data[1]

        # Toggle property via helper
        is_active = self.action == "ADD"
        set_override_state(settings, prop_path, is_active)

        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_remove_all_overrides(Operator):
    """Remove all active scene overrides"""

    bl_idname = "recom.remove_all_overrides"
    bl_label = "Remove All Overrides"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings

        # Iterate flat list via helper
        for oid, label, prop_path, icon in iterate_all_overrides():
            if is_override_active(settings, prop_path):
                set_override_state(settings, prop_path, False)

        bpy.ops.recom.reset_overrides()
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_reset_overrides(Operator):
    """Reset all override settings to their default values"""

    bl_idname = "recom.reset_overrides"
    bl_label = "Reset to Defaults"
    bl_options = {"UNDO"}

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings

        # Add the exact paths or property names you DO NOT want to reset.
        # Format: "property_name" (for root level) OR "group_name.property_name" (for nested)
        IGNORE_PATHS = {
            "active_custom_api_index",
            "cached_auto_width",
            "cached_auto_height",
            "resolved_directory",
            "resolved_filename",
            "resolved_path",
        }

        # 2. Dynamically add all the master toggle properties from OVERRIDE_MAP
        for group_items in OVERRIDE_MAP.values():
            for data in group_items.values():
                prop_path = data[1]  # e.g., "cycles.device_override" or "format_override"
                IGNORE_PATHS.add(prop_path)

        # Recursive helper function to unset properties, tracking the path
        def reset_pg(pg, current_path=""):
            for prop in pg.bl_rna.properties:
                pid = prop.identifier

                # Build the full path (e.g., "cycles.device_override")
                full_path = f"{current_path}.{pid}" if current_path else pid

                # Skip internal Blender RNA properties AND our generated ignore list
                if pid in {"rna_type", "name"} or full_path in IGNORE_PATHS or pid in IGNORE_PATHS:
                    continue

                # 1. Clear Collections (e.g., custom_api_overrides)
                if prop.type == "COLLECTION":
                    getattr(pg, pid).clear()

                # 2. Recurse into PointerProperties (like .cycles and .eevee)
                elif prop.type == "POINTER":
                    sub_pg = getattr(pg, pid)
                    if sub_pg:
                        reset_pg(sub_pg, current_path=full_path)

                # 3. Unset standard properties (Bool, Int, Enum, Float, String)
                else:
                    if not prop.is_readonly:
                        pg.property_unset(pid)

        # Trigger the recursive reset starting at the root ("")
        reset_pg(settings, current_path="")

        from ..utils.helpers import redraw_ui

        redraw_ui()

        self.report({"INFO"}, "Override settings reset to defaults")
        return {"FINISHED"}


class RECOM_OT_add_advanced_property_override(Operator):
    bl_idname = "recom.add_advanced_property_override"
    bl_label = "Add Property Override"
    bl_description = "Add a property override by entering a Blender Python data path"
    bl_options = {"UNDO"}

    data_path: bpy.props.StringProperty(
        name="Data Path", description="Paste full Python property path (e.g. bpy.context.scene.render.use_simplify)"
    )

    def invoke(self, context, event):
        # Pre-fill from clipboard if it looks like a python path
        cb = context.window_manager.clipboard
        if cb and ("bpy." in cb or "scene." in cb or "render." in cb):
            self.data_path = cb
        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        import bpy
        import mathutils

        settings = context.window_manager.recom_render_settings.override_settings
        path = self.data_path.strip()

        # Try to resolve shorthand paths
        if path.startswith("scene."):
            eval_path = "bpy.context." + path
        elif path.startswith("view_layer."):
            eval_path = "bpy.context." + path
        elif not path.startswith("bpy."):
            eval_path = "bpy.context.scene." + path
        else:
            eval_path = path

        try:
            val = eval(eval_path)

            item = settings.custom_api_overrides.add()
            item.name = path.split(".")[-1].replace("_", " ").title()
            item.data_path = eval_path

            # Detect data type automatically based on the current value in the scene
            if isinstance(val, bool):
                item.prop_type = "BOOL"
                item.value_bool = val
            elif isinstance(val, int):
                item.prop_type = "INT"
                item.value_int = val
            elif isinstance(val, float):
                item.prop_type = "FLOAT"
                item.value_float = val
            elif isinstance(val, str):
                item.prop_type = "STRING"
                item.value_string = val
            elif isinstance(val, mathutils.Vector):
                item.prop_type = "VECTOR_3"
                for i in range(min(3, len(val))):
                    item.value_vector_3[i] = float(val[i])
            elif isinstance(val, mathutils.Color):
                item.prop_type = "COLOR_4"
                for i in range(min(3, len(val))):
                    item.value_color_4[i] = float(val[i])
                item.value_color_4[3] = 1.0  # Default alpha
            else:
                # Handle Array/Tuples
                if hasattr(val, "__len__"):
                    if len(val) == 3:
                        item.prop_type = "VECTOR_3"
                        for i in range(3):
                            item.value_vector_3[i] = float(val[i])
                    elif len(val) == 4:
                        item.prop_type = "COLOR_4"
                        for i in range(4):
                            item.value_color_4[i] = float(val[i])
                    else:
                        item.prop_type = "STRING"
                        item.value_string = str(val)
                else:
                    item.prop_type = "STRING"
                    item.value_string = str(val)

            settings.active_custom_api_index = len(settings.custom_api_overrides) - 1
            redraw_ui()
        except Exception as e:
            self.report({"ERROR"}, f"Failed to evaluate path: {str(e)}")
            return {"CANCELLED"}

        return {"FINISHED"}


class RECOM_OT_remove_advanced_property_override(Operator):
    bl_idname = "recom.remove_advanced_property_override"
    bl_label = "Remove Property Override"
    bl_description = "Remove the currently selected property override from the list."
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return len(settings.custom_api_overrides) > 0

    def execute(self, context):
        settings = context.window_manager.recom_render_settings.override_settings
        idx = settings.active_custom_api_index
        settings.custom_api_overrides.remove(idx)
        settings.active_custom_api_index = max(0, idx - 1)
        return {"FINISHED"}


class RECOM_MT_add_override_menu(Menu):
    bl_label = "Add Override"
    bl_description = "Add Settings Override Menu"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings.override_settings
        render_engine = get_render_engine(context)

        items_drawn_total = 0

        # Iterate through the groups (Render, Output)
        for group_name, items in OVERRIDE_MAP.items():
            # Collect valid items for this group first
            group_items_to_draw = []

            for oid, (label, prop_path, icon) in items.items():
                # Filter by Render Engine
                if "cycles" in oid and render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                    continue
                if "eevee" in oid and render_engine == RE_CYCLES:
                    continue

                # Check if already active
                if not is_override_active(settings, prop_path):
                    group_items_to_draw.append((oid, label, icon))

            # Draw the group
            if group_items_to_draw:
                if items_drawn_total > 0:
                    layout.separator()

                # layout.label(text=group_name)

                for oid, label, icon in group_items_to_draw:
                    op = layout.operator("recom.manage_override", text=label, icon=icon)
                    op.action = "ADD"
                    op.override_id = oid

                items_drawn_total += len(group_items_to_draw)

        if items_drawn_total == 0:
            layout.label(text="All overrides active")


# --- VARIABLE MENU ---


class RECOM_MT_insert_variable_root(Menu):
    bl_label = "Add Variable Menu"

    def draw_section(self, layout, title, variables):
        col = layout.column(align=True)
        col.label(text=title, icon="BLANK1")
        col.separator()

        for token, label, icon in variables:
            if not token:
                col.separator()
                continue

            icon = icon if icon is not None else "BLANK1"
            op = col.operator("recom.insert_variable", text=label, icon=icon)
            op.variable = token

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        num_sections = len(PATH_VARIABLES_DATA)
        extra_column = 1 if prefs.custom_variables else 0
        columns = num_sections + extra_column

        flow = layout.grid_flow(columns=columns, even_columns=True, even_rows=False, align=True)

        # --- Custom Variables ---
        if prefs.custom_variables:
            col = flow.column()
            col.label(text="Custom", icon="BLANK1")
            col.separator()

            for var in prefs.custom_variables:
                op = col.operator("recom.insert_variable", text=var.name)
                op.variable = f"{{{var.token}}}"

        # --- Built-in Sections ---
        self.draw_section(flow.column(), "Render/Data", PATH_VARIABLES_DATA["data"])
        self.draw_section(flow.column(), "Output", PATH_VARIABLES_DATA["output"])
        self.draw_section(flow.column(), "System", PATH_VARIABLES_DATA["system"])


# -------------------------------------------------------------------
#  POPUPS & UTILS
# -------------------------------------------------------------------


class RECOM_PT_import_overrides_popup(Panel):
    bl_label = "Import Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)

        col = layout.column()
        col.label(text="Import Settings")

        if render_engine == RE_CYCLES:
            col.prop(prefs.override_settings, "import_compute_device", text="Device")
            col.prop(prefs.override_settings, "import_sampling", text="Sampling")
            col.prop(prefs.override_settings, "import_light_paths", text="Light Paths")
            col.prop(prefs.override_settings, "import_performance", text="Performance")
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            col.prop(prefs.override_settings, "import_eevee_settings", text="EEVEE")
        col.prop(prefs.override_settings, "import_motion_blur", text="Motion Blur")

        col.separator(factor=0.5)
        col.prop(prefs.override_settings, "import_resolution", text="Resolution")
        col.prop(prefs.override_settings, "import_frame_range", text="Frame Range")
        col.prop(prefs.override_settings, "import_output_path", text="Output Path")
        col.prop(prefs.override_settings, "import_output_format", text="File Format")

        col.separator(factor=0.5)
        col.prop(prefs.override_settings, "import_compositor", text="Compositing")

        col.separator(factor=0.5)
        col.operator("recom.import_all_settings", text="Import", icon=ICON_SYNC)


# -------------------------------------------------------------------
#  PRESETS
# -------------------------------------------------------------------


class RECOM_PT_overrides_presets(PresetPanel, Panel):
    bl_label = "Override Presets"
    preset_subdir = Path(ADDON_NAME) / "override_settings"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.overrides_preset_add"


class RECOM_PT_resolution_presets(PresetPanel, Panel):
    bl_label = "Resolution Presets"
    preset_subdir = Path(ADDON_NAME) / "resolution"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.resolution_preset_add"


class RECOM_PT_output_presets(PresetPanel, Panel):
    bl_label = "Output Path Presets"
    preset_subdir = Path(ADDON_NAME) / "output_path"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.output_preset_add"


class RECOM_PT_custom_variables_presets(PresetPanel, Panel):
    bl_label = "Custom Variables Presets"
    preset_subdir = Path(ADDON_NAME) / "custom_variables"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.custom_variables_preset_add"


class RECOM_PT_override_advanced_property_presets(PresetPanel, Panel):
    bl_label = "Advanced Property Override Presets"
    preset_subdir = Path(ADDON_NAME) / "advanced_properties"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.override_advanced_properties_preset_add"


# -------------------------------------------------------------------
#  MAIN PANEL
# -------------------------------------------------------------------


class RECOM_PT_scene_override_settings(Panel):
    """Main scene overrides panel"""

    bl_label = "Override Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (
            prefs.initial_setup_complete if render_engine == RE_CYCLES else True
        ) and prefs.visible_panels.override_settings

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = "PULLDOWN_MENU"
        row = layout.row(align=True)
        RECOM_PT_overrides_presets.draw_panel_header(row)

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        add_op = row.row(align=True)
        add_op.menu("RECOM_MT_add_override_menu", text="Add Override", icon="ADD")

        row.popover(panel="RECOM_PT_import_overrides_popup", text="", icon="IMPORT")
        settings = context.window_manager.recom_render_settings.override_settings
        has_active_overrides = False

        # Check nested map via helper
        for oid, label, prop_path, icon in iterate_all_overrides():
            if is_override_active(settings, prop_path):
                has_active_overrides = True
                break

        # Only show the remove button when there are active overrides
        remove_row = row.row(align=True)
        remove_row.enabled = has_active_overrides
        # remove_row.operator("recom.reset_overrides", text="", icon="LOOP_BACK")
        remove_row.operator("recom.remove_all_overrides", text="", icon="PANEL_CLOSE")


# -------------------------------------------------------------------
#  INDIVIDUAL OVERRIDE PANELS
# -------------------------------------------------------------------


class RECOM_PT_motion_blur_settings(Panel):
    bl_label = "Motion Blur"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.motion_blur_override

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings, "use_motion_blur", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "motion_blur"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column()
        col.active = settings.override_settings.use_motion_blur
        col.prop(settings.override_settings, "motion_blur_position", text="Position")
        col.prop(settings.override_settings, "motion_blur_shutter", text="Shutter", slider=True)


class RECOM_PT_frame_range_settings(Panel):
    bl_label = "Frame Range"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        prefs = get_addon_preferences(context)
        return settings.frame_range_override  # and not prefs.launch_mode == MODE_LIST

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "frame_range"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        row = layout.row(align=True)
        row.active = prefs.launch_mode == MODE_SINGLE
        row.prop(settings.override_settings, "frame_current", text="Current Frame")

        col = layout.column(align=True)
        col.active = prefs.launch_mode == MODE_SEQ
        col.prop(settings.override_settings, "frame_start", text="Frame Start")
        col.prop(settings.override_settings, "frame_end", text="End")
        col.prop(settings.override_settings, "frame_step", text="Step")


class RECOM_PT_resolution_settings(Panel):
    bl_label = "Resolution"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.format_override

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        RECOM_PT_resolution_presets.draw_panel_header(row)
        op = row.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "resolution"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column()

        row = col.row(heading="Mode")
        row.prop(settings.override_settings, "resolution_override", text="")
        sub = row.row()
        sub.active = settings.override_settings.resolution_override
        sub_row = sub.row(align=True)
        sub_row.prop(settings.override_settings, "resolution_mode", text="")

        # Conditional UI Based on Mode
        col_res = col.column(align=True)
        col_res.active = settings.override_settings.resolution_override

        if settings.override_settings.resolution_mode == "SET_WIDTH":
            row_x = col_res.row(align=True)
            row_x.prop(settings.override_settings, "resolution_x", text="Width")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            auto_height = settings.override_settings.cached_auto_height
            settings.override_settings.resolution_preview = auto_height

            row_y = col_res.row(align=True)
            row_y.enabled = False
            row_y.prop(settings.override_settings, "resolution_preview", text="Auto-Height")
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)
        elif settings.override_settings.resolution_mode == "SET_HEIGHT":
            auto_width = settings.override_settings.cached_auto_width
            settings.override_settings.resolution_preview = auto_width

            row_x = col_res.row(align=True)
            row_x.enabled = False
            row_x.prop(settings.override_settings, "resolution_preview", text="Auto-Width")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Height")
            # row_y.separator(factor=0.5)
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)
        else:
            row_x = col_res.row(align=True)
            row_x.prop(settings.override_settings, "resolution_x", text="Width")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Height")
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)

        # Scale resolution menu
        scale_col = layout.column()

        scale_row = scale_col.row(align=True)
        scale_row.prop(settings.override_settings, "custom_render_scale", text="Scale", slider=True)
        scale_row.menu("RECOM_MT_custom_render_scale", text="", icon=ICON_OPTION)

        # Scaled result
        show_scale = settings.override_settings.custom_render_scale != 100

        if show_scale:
            # Calculate Scale
            scale_factor = settings.override_settings.custom_render_scale / 100

            if settings.override_settings.resolution_override:
                if settings.override_settings.resolution_mode == "SET_HEIGHT":
                    height = settings.override_settings.resolution_y
                    width = auto_width
                elif settings.override_settings.resolution_mode == "SET_WIDTH":
                    width = settings.override_settings.resolution_x
                    height = auto_height
                else:
                    width = settings.override_settings.resolution_x
                    height = settings.override_settings.resolution_y
            else:
                resolution = get_default_resolution(context)
                width = resolution[0]
                height = resolution[1]

            scaled_width = int(round(width * scale_factor / 2) * 2)
            scaled_height = int(round(height * scale_factor / 2) * 2)

            # Draw Preview
            scaled_label_row = scale_col.row(align=True)
            scaled_label_row.label(text=f"Scaled: {scaled_width} x {scaled_height} px")


class RECOM_PT_overscan_settings(Panel):
    bl_label = "Overscan"
    bl_parent_id = "RECOM_PT_resolution_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.format_override

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings, "use_overscan", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.use_overscan

        overscan_col = layout.column()
        overscan_row = overscan_col.row()
        overscan_row.prop(settings.override_settings, "overscan_type", text="Type", expand=True)

        if settings.override_settings.overscan_type == "PIXELS":
            col = overscan_col.column()
            col.prop(settings.override_settings, "overscan_uniform", text="Uniform")
            if settings.override_settings.overscan_uniform:
                col.prop(settings.override_settings, "overscan_width", text="Pixels")
            else:
                subcol = col.column(align=True)
                subcol.prop(settings.override_settings, "overscan_width", text="Width")
                subcol.prop(settings.override_settings, "overscan_height", text="Height")
        else:
            overscan_col.prop(settings.override_settings, "overscan_percent", text="%", slider=True)


class RECOM_PT_output_path_settings(Panel):
    bl_label = "Output Path"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.output_path_override

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row(align=True)
        RECOM_PT_output_presets.draw_panel_header(row)
        op = row.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "output_path"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings

        col = layout.column(align=True)
        dir_row = col.row(align=True)
        dir_row.prop(
            settings.override_settings, "output_directory", text="", icon="FILE_FOLDER", placeholder="Directory"
        )
        dir_row.operator("recom.select_output_directory", text="", icon="FILE_FOLDER")
        col.prop(settings.override_settings, "output_filename", text="", icon="FILE", placeholder="Filename")


class RECOM_PT_resolved_path(Panel):
    bl_label = "Resolved Path"
    bl_parent_id = "RECOM_PT_insert_variables"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings

        directory = settings.override_settings.resolved_directory
        filename = settings.override_settings.resolved_filename

        active = bool(directory or filename)
        resolved_col = layout.column(align=True)
        main_row = resolved_col.row(align=True)

        if active:
            directory_row = main_row.row(align=True)
            directory_row.prop(settings.override_settings, "resolved_directory", text="", expand=True)

            filename_row = resolved_col.row(align=True)
            filename_row.prop(settings.override_settings, "resolved_filename", text="", expand=True)
            filename_row.operator("recom.show_tooltip", text="", icon="FILE_REFRESH")

        open_row = main_row.row(align=True)
        open_row.enabled = active
        open_row.operator("recom.open_folder", text="", icon="FOLDER_REDIRECT")


class RECOM_PT_insert_variables(Panel):
    bl_label = "Path Variables"
    bl_parent_id = "RECOM_PT_output_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        row = layout.row(align=False)
        row.prop(settings.override_settings, "variable_insert_target", text="Target", expand=True)

        layout.menu("RECOM_MT_insert_variable_root", text="Add Variable", icon="ADD")


class RECOM_PT_custom_variables(Panel):
    bl_label = "Custom Variables"
    bl_parent_id = "RECOM_PT_insert_variables"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 2

    def draw_header_preset(self, context):
        RECOM_PT_custom_variables_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        root_col = layout.column()
        content_row = root_col.row()

        # Variable list
        list_col = content_row.column()
        list_col.template_list(
            "RECOM_UL_custom_variables",
            "",
            prefs,
            "custom_variables",
            prefs,
            "active_custom_variable_index",
            rows=4,
        )

        # Controls
        controls_col = content_row.column()
        add_remove_col = controls_col.column(align=True)
        add_remove_col.operator("recom.add_custom_variable", text="", icon="ADD")

        has_selection = bool(
            prefs.custom_variables and prefs.active_custom_variable_index < len(prefs.custom_variables)
        )

        remove_col = add_remove_col.column(align=True)
        remove_col.active = has_selection
        remove_col.operator("recom.remove_custom_variable", text="", icon="REMOVE")
        controls_col.separator(factor=0.5)

        menu_row = controls_col.row()
        menu_row.active = has_selection and len(prefs.custom_variables) > 1
        menu_row.menu("RECOM_MT_custom_variables", text="", icon="DOWNARROW_HLT")

        # Variable details
        if prefs.active_custom_variable_index >= 0 and has_selection:
            list_col.separator(factor=0.5)
            active_var = prefs.custom_variables[prefs.active_custom_variable_index]
            details_col = root_col.column(align=True)
            details_col.use_property_split = True
            details_col.use_property_decorate = False
            details_col.prop(active_var, "name", text="Name")
            details_col.prop(active_var, "token", text="Token")
            details_col.prop(active_var, "value", text="Value")


class RECOM_UL_custom_variables(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            row = layout.row(align=True)
            row.prop(item, "name", text="", emboss=False, placeholder="Name")


class RECOM_PT_output_format_settings(Panel):
    bl_label = "File Format"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 4

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.file_format_override

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "file_format"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column()
        col.prop(settings.override_settings, "file_format", text="File Format", icon="FILE_IMAGE")

        if settings.override_settings.file_format in [
            "OPEN_EXR",
            "OPEN_EXR_MULTILAYER",
            "PNG",
            "TIFF",
        ]:
            row = col.row(align=True)
            row.prop(settings.override_settings, "color_depth", text="Color Depth", expand=True)

        if settings.override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
            col.prop(settings.override_settings, "codec", text="Codec")

        if settings.override_settings.file_format == "JPEG":
            col.prop(settings.override_settings, "jpeg_quality", text="Quality", slider=True)


class RECOM_PT_camera_settings(Panel):
    bl_label = "Camera"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.cameras_override

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "camera_settings"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings

        col = layout.column(align=True)
        col.prop(settings.override_settings, "camera_shift_x", text="Shift X", slider=True)
        col.prop(settings.override_settings, "camera_shift_y", text="Y", slider=True)

        row = layout.row(heading="Depth of Field")
        row.prop(settings.override_settings, "override_dof", text="")
        sub_row = row.row(align=True)
        sub_row.active = settings.override_settings.override_dof
        sub_row.prop(settings.override_settings, "use_dof", text="", expand=False)


class RECOM_PT_compositor_settings(Panel):
    bl_label = "Compositing"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.compositor_override

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings, "use_compositor", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "compositor"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings

        col = layout.column()
        col.active = settings.override_settings.use_compositor
        col.prop(
            settings.override_settings,
            "compositor_disable_output_files",
            text="Bypass File Outputs",
        )
        col.separator(factor=0.25)
        device_row = col.row()
        device_row.prop(settings.override_settings, "compositor_device", text="Device", expand=True)


class RECOM_UL_custom_api_overrides(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            label_row = layout.row(align=True)
            label_row.prop(item, "name", text="", emboss=False, placeholder="Data Path")

            row = layout.row(align=True)
            # row.alignment = "RIGHT"
            if item.prop_type == "BOOL":
                row.prop(item, "value_bool", text="")
            elif item.prop_type == "INT":
                row.prop(item, "value_int", text="")
            elif item.prop_type == "FLOAT":
                row.prop(item, "value_float", text="")
            elif item.prop_type == "STRING":
                row.prop(item, "value_string", text="")
            elif item.prop_type == "VECTOR_3":
                row.prop(item, "value_vector_3", text="")
            elif item.prop_type == "COLOR_4":
                row.prop(item, "value_color_4", text="")


class RECOM_PT_custom_api_settings(Panel):
    bl_label = "Advanced Properties"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 6

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.use_custom_api_overrides

    def draw_header_preset(self, context):
        layout = self.layout

        row = layout.row(align=True)
        RECOM_PT_override_advanced_property_presets.draw_panel_header(row)

        op = row.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "custom_api"

        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings.override_settings

        root_col = layout.column()
        content_row = root_col.row()

        # Variable list
        list_col = content_row.column(align=True)
        list_col.template_list(
            "RECOM_UL_custom_api_overrides",
            "",
            settings,
            "custom_api_overrides",
            settings,
            "active_custom_api_index",
            rows=4,
        )

        # Controls
        controls_col = content_row.column()
        add_remove_col = controls_col.column(align=True)
        add_remove_col.operator("recom.add_advanced_property_override", text="", icon="ADD")
        add_remove_col.operator("recom.remove_advanced_property_override", text="", icon="REMOVE")

        if settings.active_custom_api_index >= 0 and settings.custom_api_overrides:
            item = settings.custom_api_overrides[settings.active_custom_api_index]

            details_col = layout.column()
            col = details_col.column(align=True)
            col.label(text="Data Path:")
            col.prop(item, "data_path", text="")

            col = details_col.column()
            col_sub = col.column()
            # col_sub.active = False
            col_sub.prop(item, "name")
            col_sub.prop(item, "prop_type", text="Type")

            if item.prop_type == "BOOL":
                col.prop(item, "value_bool")
            elif item.prop_type == "INT":
                col.prop(item, "value_int")
            elif item.prop_type == "FLOAT":
                col.prop(item, "value_float")
            elif item.prop_type == "STRING":
                col.prop(item, "value_string")
            elif item.prop_type == "VECTOR_3":
                col.prop(item, "value_vector_3")
            elif item.prop_type == "COLOR_4":
                col.prop(item, "value_color_4")


# -------------------------------------------------------------------
#  REGISTRATION
# -------------------------------------------------------------------

classes = (
    RECOM_OT_manage_override,
    RECOM_OT_remove_all_overrides,
    RECOM_OT_reset_overrides,
    RECOM_OT_add_advanced_property_override,
    RECOM_OT_remove_advanced_property_override,
    RECOM_MT_add_override_menu,
    RECOM_MT_insert_variable_root,
    RECOM_PT_import_overrides_popup,
    RECOM_PT_overrides_presets,
    RECOM_PT_scene_override_settings,
    # Render
    RECOM_PT_motion_blur_settings,
    # Output
    RECOM_PT_frame_range_settings,
    RECOM_PT_resolution_presets,
    RECOM_PT_resolution_settings,
    RECOM_PT_overscan_settings,
    RECOM_PT_output_presets,
    RECOM_PT_custom_variables_presets,
    RECOM_PT_output_path_settings,
    RECOM_UL_custom_variables,
    RECOM_PT_insert_variables,
    RECOM_PT_custom_variables,
    RECOM_PT_resolved_path,
    RECOM_PT_output_format_settings,
    # Data
    RECOM_PT_camera_settings,
    RECOM_PT_compositor_settings,
    RECOM_PT_override_advanced_property_presets,
    RECOM_UL_custom_api_overrides,
    RECOM_PT_custom_api_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
