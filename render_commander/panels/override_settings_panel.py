# ./panels/override_settings_panel.py

import bpy
from bpy.types import Panel
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import (
    get_default_resolution,
    calculate_auto_width,
    calculate_auto_height,
    get_render_engine,
    logical_width,
)


class RECOM_PT_OverridesPresets(PresetPanel, Panel):
    bl_label = "Override Settings Presets"
    preset_subdir = f"{ADDON_NAME}/override_settings"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_overrides_preset"


class RECOM_PT_RenderOverrides(Panel):
    bl_label = "Override Settings"
    bl_idname = "RECOM_PT_render_overrides"
    # bl_parent_id = "RECOM_PT_main_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return (
            prefs.initial_setup_complete if render_engine == "CYCLES" else True
        ) and prefs.visible_panels.override_settings

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        # layout.prop(settings, "use_override_settings", text="")

    def draw_header_preset(self, context):
        RECOM_PT_OverridesPresets.draw_panel_header(self.layout)

    def draw(self, context):
        pass


class RECOM_PT_RenderSettings(Panel):
    bl_label = "Render Properties"
    bl_idname = "RECOM_PT_render_settings"
    bl_parent_id = "RECOM_PT_render_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        pass


class RECOM_PT_MotionBlurSettings(Panel):
    bl_label = "Motion Blur"
    bl_idname = "RECOM_PT_motion_blur_settings"
    bl_parent_id = "RECOM_PT_render_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.motion_blur

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings, "motion_blur_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.motion_blur_override

        row = layout.row(align=True)
        row.operator("recom.import_motion_blur", text="", icon=ICON_SYNC, emboss=False)
        row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.motion_blur_override

        col = layout.column()
        col.prop(settings.override_settings, "use_motion_blur", text="Use Motion Blur")

        sub = layout.column()
        sub.active = settings.override_settings.motion_blur_override and settings.override_settings.use_motion_blur
        sub.prop(settings.override_settings, "motion_blur_position", text="Position")
        sub.prop(settings.override_settings, "motion_blur_shutter", text="Shutter", slider=True)


class RECOM_PT_CompositorSettings(Panel):
    bl_label = "Compositing"
    bl_idname = "RECOM_PT_compositor_settings"
    bl_parent_id = "RECOM_PT_render_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.compositor

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings, "compositor_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.compositor_override
        row = layout.row(align=True)
        row.operator("recom.import_compositor", text="", icon=ICON_SYNC, emboss=False)
        row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings

        layout.active = settings.override_settings.compositor_override

        col = layout.column()

        col.prop(settings.override_settings, "use_compositor", text="Use Compositor")
        sub = col.column()
        sub.active = settings.override_settings.use_compositor
        sub.prop(
            settings.override_settings,
            "compositor_disable_output_files",
            text="Bypass File Outputs",
        )
        sub.separator(factor=0.25)
        device_row = sub.row()
        device_row.prop(settings.override_settings, "compositor_device", text="Device", expand=True)


class RECOM_PT_OutputSettings(Panel):
    bl_label = "Output Properties"
    bl_idname = "RECOM_PT_output_settings"
    bl_parent_id = "RECOM_PT_render_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"HIDE_HEADER"}

    def draw(self, context):
        pass


class RECOM_PT_FrameRangeSettings(Panel):
    bl_label = "Frame Range"
    bl_idname = "RECOM_PT_frame_range_settings"
    bl_parent_id = "RECOM_PT_output_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.frame_range

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)
        layout.active = prefs.launch_mode != MODE_LIST
        layout.prop(settings.override_settings, "frame_range_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)
        layout.active = settings.override_settings.frame_range_override and not prefs.launch_mode == MODE_LIST
        row = layout.row(align=True)
        row.operator("recom.import_frame_range", text="", icon=ICON_SYNC, emboss=False)
        row.separator(factor=1)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.frame_range_override and not prefs.launch_mode == MODE_LIST

        row = layout.row(align=True)
        row.active = prefs.launch_mode == MODE_SINGLE
        row.prop(settings.override_settings, "frame_current", text="Current Frame")

        col = layout.column(align=True)
        col.active = prefs.launch_mode == MODE_SEQ
        col.prop(settings.override_settings, "frame_start", text="Frame Start")
        col.prop(settings.override_settings, "frame_end", text="End")
        col.prop(settings.override_settings, "frame_step", text="Step")


class RECOM_PT_ResolutionPresets(PresetPanel, Panel):
    bl_label = "Resolution Presets"
    preset_subdir = f"{ADDON_NAME}/resolution"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_resolution_preset"


class RECOM_PT_ResolutionSettings(Panel):
    bl_label = "Format"
    bl_idname = "RECOM_PT_resolution_settings"
    bl_parent_id = "RECOM_PT_output_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.resolution

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings, "format_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override

        row = layout.row(align=True)
        RECOM_PT_ResolutionPresets.draw_panel_header(row)
        row.operator("recom.import_manual_resolution", text="", icon=ICON_SYNC, emboss=False)
        row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override

        col = layout.column()

        row = col.row(heading="Resolution")
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
            # row_x.separator(factor=0.5)
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            auto_height = settings.override_settings.cached_auto_height
            settings.override_settings.resolution_preview = auto_height

            row_y = col_res.row(align=True)
            row_y.active = False
            row_y.prop(settings.override_settings, "resolution_preview", text="Auto-Height")
            # row_y.separator(factor=0.5)
            row_y.menu("RECOM_MT_resolution_y", text="", icon="DECORATE_LOCKED")
        elif settings.override_settings.resolution_mode == "SET_HEIGHT":
            auto_width = settings.override_settings.cached_auto_width
            settings.override_settings.resolution_preview = auto_width

            row_x = col_res.row(align=True)
            row_x.active = False
            row_x.prop(settings.override_settings, "resolution_preview", text="Auto-Width")
            # row_x.separator(factor=0.5)
            row_x.menu("RECOM_MT_resolution_x", text="", icon="DECORATE_LOCKED")

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Height")
            # row_y.separator(factor=0.5)
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)
        else:
            row_x = col_res.row(align=True)
            row_x.prop(settings.override_settings, "resolution_x", text="Width")
            # row_x.separator(factor=0.5)
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Height")
            # row_y.separator(factor=0.5)
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)

        # Scale resolution menu
        scale_col = layout.column()
        scale_col.prop(settings.override_settings, "render_scale", text="Scale")
        if settings.override_settings.render_scale == "CUSTOM":
            scale_col.prop(settings.override_settings, "custom_render_scale", text="%", slider=True)

        # Scaled result
        show_scale = settings.override_settings.render_scale != "1.00" and (
            settings.override_settings.render_scale != "CUSTOM" or settings.override_settings.custom_render_scale != 100
        )
        if show_scale:
            scale_factor = (
                float(settings.override_settings.render_scale)
                if settings.override_settings.render_scale != "CUSTOM"
                else settings.override_settings.custom_render_scale / 100
            )
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

            scaled_width = int(width * scale_factor)
            scaled_height = int(height * scale_factor)

            scaled_label_box = scale_col.box()
            scaled_label_row = scaled_label_box.row(align=True)
            scaled_label_row.separator(factor=0.5)
            scaled_label_row.active = False
            scaled_label_row.label(text=f"Output: {scaled_width} x {scaled_height} px")


class RECOM_PT_OverscanSettings(Panel):
    bl_label = "Overscan"
    bl_idname = "RECOM_PT_overscan_settings"
    bl_parent_id = "RECOM_PT_resolution_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.overscan

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override
        layout.prop(settings.override_settings, "use_overscan", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override and settings.override_settings.use_overscan

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


class RECOM_PT_CameraShiftSettings(Panel):
    bl_label = "Lens Shift"
    bl_idname = "RECOM_PT_camera_shift_settings"
    bl_parent_id = "RECOM_PT_resolution_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.camera_shift

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override
        layout.prop(settings.override_settings, "camera_shift_override", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.format_override and settings.override_settings.camera_shift_override

        col = layout.column(align=True)
        col.prop(settings.override_settings, "camera_shift_x", text="Shift X", slider=True)
        col.prop(settings.override_settings, "camera_shift_y", text="Y", slider=True)


class RECOM_PT_OutputPresets(PresetPanel, Panel):
    bl_label = "Output Path Presets"
    preset_subdir = f"{ADDON_NAME}/output_path"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_output_preset"


class RECOM_PT_OutputPathSettings(Panel):
    bl_label = "Output Path"
    bl_idname = "RECOM_PT_output_path_settings"
    bl_parent_id = "RECOM_PT_output_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.output_path

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings, "output_path_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.output_path_override
        row = layout.row(align=True)
        RECOM_PT_OutputPresets.draw_panel_header(row)
        row.menu("RECOM_MT_resolved_path", text="", icon="COLLAPSEMENU")

        row.separator()

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.output_path_override

        col = layout.column(align=True)
        dir_row = col.row(align=True)
        dir_row.prop(
            settings.override_settings,
            "output_directory",
            text="",
            icon="FILE_FOLDER",
            placeholder="Output Directory",
        )
        dir_row.operator("recom.select_output_directory", text="", icon="FILE_FOLDER")

        col.prop(
            settings.override_settings,
            "output_filename",
            text="",
            icon="FILE",
            placeholder="Output Filename",
        )

        if prefs.path_preview:
            resolved_path = settings.override_settings.resolved_path or f"Resolve"
            row = layout.row(align=True)
            row.active = False
            row.operator(
                "recom.show_tooltip",
                text=resolved_path,
                # icon="FILE_REFRESH",
            )


class RECOM_PT_AddVariablesPanel(Panel):
    bl_label = "Path Variables"
    bl_idname = "RECOM_PT_add_variables_panel"
    bl_parent_id = "RECOM_PT_output_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    MAX_WIDTH = 250
    SECTIONS = [
        (
            "show_custom_variables",
            "Custom",
            [],
        ),
        (
            "show_file_info",
            "Blend File",
            [
                ("{blend_dir}", "Blend Directory"),
                ("{blend_name}", "Blend Name"),
            ],
        ),
        (
            "show_render_info",
            "Render Info",
            [
                ("{scene_name}", "Scene Name"),
                ("{view_name}", "View Layer Name"),
                ("{engine}", "Render Engine"),
                ("{thresh}", "Noise Threshold"),
                ("{samples}", "Max Samples"),
                ("{aspect}", "Aspect Ratio"),
                ("{resolution}", "Resolution (WxH)"),
                ("{file_format}", "File Format"),
                ("{bl_ver}", "Blender Version"),
            ],
        ),
        (
            "show_camera_info",
            "Camera Info",
            [
                ("{camera_name}", "Camera Name"),
                ("{camera_lens}", "Focal Length"),
                ("{camera_sensor}", "Sensor Width"),
            ],
        ),
        (
            "show_frame_range",
            "Frame Info",
            [
                ("{fps}", "Frame Rate"),
                ("{frame_start}", "Start"),
                ("{frame_end}", "End"),
                ("{frame_step}", "Step"),
            ],
        ),
        (
            "show_date_system",
            "Date & System",
            [
                ("{year}", "Year"),
                ("{month}", "Month"),
                ("{day}", "Day"),
                ("{date}", "Date (Y-M-D)"),
                ("{time}", "Time (H-M-S)"),
                ("{user}", "User"),
                ("{host}", "Host"),
            ],
        ),
    ]

    def _draw_variable_section(self, context, layout, rs, show_prop_name, label_text, tokens):
        prefs = get_addon_preferences(context)

        if show_prop_name == "show_custom_variables":
            if not prefs.custom_variables:
                return

        icon = ICON_COLLAPSED if getattr(rs, show_prop_name) else ICON_EXPANDED

        col = layout.column()
        row = col.row(align=True)
        row.alignment = "LEFT"
        row.prop(rs, show_prop_name, text="", icon=icon, emboss=False)
        row.label(text=label_text)

        if getattr(rs, show_prop_name):
            grid_row = col.column(align=True)
            grid_row.scale_y = 1

            if show_prop_name == "show_custom_variables":
                if prefs.custom_variables:
                    for var in prefs.custom_variables:
                        token = f"{{{var.token}}}"
                        label = f"{var.name}"
                        op = grid_row.operator("recom.insert_variable", text=label)
                        op.variable = token
            else:
                for token, label in tokens:
                    op = grid_row.operator("recom.insert_variable", text=label)
                    op.variable = token

    def _get_dual_column(self, layout, region_width):
        width = logical_width(region_width)

        if width > self.MAX_WIDTH:
            split = layout.split(factor=0.5, align=True)
            return split.column(align=True), split.column(align=True)

        return layout.column(align=True), None

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.output_path_override

        insert_row = layout.row()
        insert_row.use_property_split = True
        insert_row.use_property_decorate = False
        insert_row.prop(settings.override_settings, "variable_insert_target", expand=True)

        main_col = layout.column()
        main_col.separator(factor=0.25)

        region_width = context.region.width
        col_left, col_right = self._get_dual_column(main_col, region_width)
        sep_counter = {col_left: 0, col_right: 0}

        for i, (prop, label, tokens) in enumerate(self.SECTIONS):
            target_layout = col_left if col_right is None or i % 2 == 0 else col_right

            is_custom_section = prop == "show_custom_variables"
            if is_custom_section and not prefs.custom_variables:
                pass
            else:
                if sep_counter[target_layout] > 0:
                    target_layout.separator(factor=0.5)
                sep_counter[target_layout] += 1

                self._draw_variable_section(context, target_layout, prefs, prop, label, tokens)


class RECOM_PT_OutputFormatSettings(Panel):
    bl_label = "File Format"
    bl_idname = "RECOM_PT_output_format_settings"
    bl_parent_id = "RECOM_PT_output_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.file_format

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings, "file_format_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.file_format_override
        row = layout.row(align=True)
        row.operator("recom.import_output_format", text="", icon=ICON_SYNC, emboss=False)
        row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.file_format_override

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


classes = (
    RECOM_PT_OverridesPresets,
    RECOM_PT_RenderOverrides,
    RECOM_PT_RenderSettings,
    RECOM_PT_OutputSettings,
    RECOM_PT_ResolutionPresets,
    RECOM_PT_ResolutionSettings,
    RECOM_PT_OverscanSettings,
    RECOM_PT_CameraShiftSettings,
    RECOM_PT_FrameRangeSettings,
    RECOM_PT_MotionBlurSettings,
    RECOM_PT_OutputPresets,
    RECOM_PT_OutputPathSettings,
    RECOM_PT_AddVariablesPanel,
    RECOM_PT_OutputFormatSettings,
    RECOM_PT_CompositorSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
