# ./menus/override_menus.py

import logging

import bpy
from bpy.types import Menu

from ..preferences import get_addon_preferences

log = logging.getLogger(__name__)


class RECOM_MT_sampling_factor(Menu):
    bl_label = "Sampling Factor Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_value = f"{settings.override_settings.cycles.sampling_factor:.1f}"

        layout.label(text="Sampling Factor")
        layout.separator()

        scale_options = [
            ("25", "25%", "0.25x Samples"),
            ("50", "50%", "0.5x Samples"),
            ("100", "100%", "Original Scene Values"),
            ("150", "150%", "1.5x Samples"),
            ("200", "200%", "2x Samples"),
            ("400", "400%", "4x Samples"),
        ]

        for value, label, description in scale_options:
            icon = "DOT" if f"{float(value):.1f}" == current_value else "BLANK1"

            op = layout.operator("recom.set_sampling_factor", text=label, icon=icon)
            op.value = float(value)


class RECOM_MT_resolution_x(Menu):
    bl_label = "X Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_x = settings.override_settings.resolution_x

        if settings.override_settings.resolution_mode == "SET_HEIGHT":
            layout.enabled = False

        layout.label(text="Resolution X")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text="Swap X and Y", icon="UV_SYNC_SELECT")
        layout.separator()

        sections = {
            "Landscape": [7680, 5120, 3840, 2560, 1280, 854, 640],
            "Portait": [2160, 1920, 720, 480, 360],
            "Square": [8192, 4096, 2048, 1080, 1024, 800, 512, 256],
        }
        section_count = len(sections)

        for i, (label, values) in enumerate(sections.items()):
            for val in values:
                icon = "DOT" if val == current_x else "BLANK1"

                op = layout.operator("recom.set_resolution", text=f"{val} px", icon=icon)
                op.dimension = "X"
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_resolution_y(Menu):
    bl_label = "Y Resolution Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_y = settings.override_settings.resolution_y

        if settings.override_settings.resolution_mode == "SET_WIDTH":
            layout.enabled = False

        layout.label(text="Resolution Y")
        layout.separator()

        swap_row = layout.row()
        swap_row.active = settings.override_settings.resolution_override
        swap_row.operator("recom.swap_resolution", text="Swap X and Y", icon="UV_SYNC_SELECT")
        layout.separator()

        sections = {
            "Landscape": [4320, 2880, 2160, 1440, 720, 480],
            "Portait": [3840, 2560, 1920, 1350, 1280, 960, 640],
            "Square": [8192, 4096, 2048, 1080, 1024, 800, 512, 256],
        }
        section_count = len(sections)

        for i, (label, values) in enumerate(sections.items()):
            for val in values:
                icon = "DOT" if val == current_y else "BLANK1"

                op = layout.operator("recom.set_resolution", text=f"{val} px", icon=icon)
                op.dimension = "Y"
                op.value = val

            if i < section_count - 1:
                layout.separator()


class RECOM_MT_custom_render_scale(Menu):
    bl_label = "Resolution Scale Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current_value = f"{settings.override_settings.custom_render_scale:.2f}"

        layout.label(text="Resolution Scale")
        layout.separator()

        scale_options = [
            ("400", "400%", "4x resolution multiplier"),
            ("300", "300%", "3x resolution multiplier"),
            ("200", "200%", "2x resolution multiplier"),
            ("150", "150%", "1.5x resolution multiplier"),
            ("100", "100%", "Native resolution"),
            ("66.67", "66.7% (2/3)", "2/3 resolution"),
            ("50", "50%", "Half resolution"),
            ("33.33", "33.3% (1/3)", "1/3 resolution"),
            ("25", "25%", "Quarter resolution"),
        ]

        for value, label, description in scale_options:
            icon = "DOT" if f"{float(value):.2f}" == current_value else "BLANK1"

            op = layout.operator("recom.set_custom_render_scale", text=label, icon=icon)
            op.value = float(value)  # Convert to float for setting the property


class RECOM_MT_adaptive_threshold(Menu):
    bl_label = "Adaptive Threshold Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = f"{settings.override_settings.cycles.adaptive_threshold:.4f}"

        layout.label(text="Adaptive Threshold")
        layout.separator()

        thresholds = [0.0050, 0.0100, 0.0150, 0.0250, 0.0500, 0.1000]
        for val in thresholds:
            icon = "DOT" if f"{val:.4f}" == current else "BLANK1"
            op = layout.operator("recom.set_adaptive_threshold", text=f"{val:.4f}", icon=icon)
            op.value = val


class RECOM_MT_samples(Menu):
    bl_label = "Samples Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.samples

        layout.label(text="Samples")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 6144, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_adaptive_min_samples(Menu):
    bl_label = "Adaptive Min Samples Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.adaptive_min_samples

        layout.label(text="Adaptive Min Samples")
        layout.separator()

        values = [0, 16, 32, 64, 128, 256, 512, 1024]
        for val in values:
            icon = "DOT" if val == current else "BLANK1"

            op = layout.operator("recom.set_adaptive_min_samples", text=str(val), icon=icon)
            op.value = val


class RECOM_MT_time_limit(Menu):
    bl_label = "Time Limit Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.time_limit

        layout.label(text="Time Limit")
        layout.separator()

        time_presets = [
            ("0 s", 0.0),
            ("15 s", 15.0),
            ("30 s", 30.0),
            ("1 min", 60.0),
            ("3 min", 180.0),
            ("5 min", 300.0),
            ("10 min", 600.0),
            ("15 min", 900.0),
            ("20 min", 1200.0),
            ("30 min", 1800.0),
            ("1 hr", 3600.0),
            ("3 hr", 10800.0),
            ("6 hr", 21600.0),
        ]
        for label, seconds in time_presets:
            icon = "DOT" if seconds == current else "BLANK1"

            op = layout.operator("recom.set_time_limit", text=label, icon=icon)
            op.value = seconds


class RECOM_MT_tile_size(Menu):
    bl_label = "Tile Size Menu"

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        current = settings.override_settings.cycles.tile_size

        layout.label(text="Tile Size")
        layout.separator()

        values = [64, 128, 256, 512, 1024, 2048, 4096, 8192]
        values.sort(reverse=True)

        for val in values:
            icon = "DOT" if val == current else "BLANK1"
            op = layout.operator("recom.set_tile_size", text=str(val), icon=icon)
            op.value = val


# Data for Path Variables Menu
PATH_VARIABLES_DATA = {
    "data": [
        ("{blend_dir}", "Blend Directory"),
        ("{blend_name}", "Blend Name"),
        ("", ""),
        ("{fps}", "Frame Rate"),
        ("{resolution_x}", "Resolution X"),
        ("{resolution_y}", "Resolution Y"),
        ("", ""),
        ("{scene_name}", "Scene Name"),
        ("{camera_name}", "Camera Name"),
    ],
}


class RECOM_MT_insert_variable_root(Menu):
    bl_label = "Add Variable Menu"
    bl_description = "Add a variable to the output file path"

    def draw_section(self, layout, title, variables):
        col = layout.column(align=True)
        col.label(text=title)
        col.separator()

        for token, label in variables:
            if not token:
                col.separator()
                continue

            op = col.operator("recom.insert_variable", text=label)
            op.variable = token

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)

        show_templates = bpy.app.version >= (5, 0)
        has_custom = bool(prefs.custom_variables)

        if not show_templates and not has_custom:
            layout.label(text="No variables available", icon="INFO")
            return

        # Calculate columns based on visible sections only
        num_sections = 1 if show_templates else 0
        extra_column = 1 if has_custom else 0
        columns = num_sections + extra_column

        flow = layout.grid_flow(columns=columns, even_columns=True, even_rows=False, align=True)

        # Draw Path Templates section (Blender 5.0+)
        if show_templates:
            self.draw_section(flow.column(), "Path Templates", PATH_VARIABLES_DATA["data"])

        # Draw Custom Variables section
        if has_custom:
            col = flow.column(align=True)
            col.label(text="Custom")
            col.separator()

            for var in prefs.custom_variables:
                op = col.operator("recom.insert_variable", text=var.name)
                op.variable = f"{{{var.token}}}"


classes = (
    RECOM_MT_sampling_factor,
    RECOM_MT_resolution_x,
    RECOM_MT_resolution_y,
    RECOM_MT_custom_render_scale,
    RECOM_MT_adaptive_threshold,
    RECOM_MT_samples,
    RECOM_MT_adaptive_min_samples,
    RECOM_MT_time_limit,
    RECOM_MT_tile_size,
    RECOM_MT_insert_variable_root,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
