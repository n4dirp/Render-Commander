# ./panels/override_eevee_panel.py

import bpy
from bpy.types import Panel, Menu
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


# -------------------------------------------------------------------
#  PRESETS
# -------------------------------------------------------------------


class RECOM_PT_eevee_settings_presets(PresetPanel, Panel):
    bl_label = "EEVEE Settings Presets"
    preset_subdir = f"{ADDON_NAME}/eevee"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.eevee_preset_add"


# -------------------------------------------------------------------
#  MAIN EEVEE PANEL
# -------------------------------------------------------------------


class RECOM_PT_eevee_settings(Panel):
    bl_label = "EEVEE"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        settings = context.window_manager.recom_render_settings.override_settings
        return (render_engine in {RE_EEVEE_NEXT, RE_EEVEE}) and settings.eevee_override

    def draw_header(self, context):
        pass

    def draw_header_preset(self, context):
        layout = self.layout

        RECOM_PT_eevee_settings_presets.draw_panel_header(self.layout)

        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "eevee_all"

        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        # Draw Sampling directly here (formerly in a separate HIDE_HEADER panel)
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(settings.override_settings.eevee, "samples", text="Samples")
        row.menu("RECOM_MT_eevee_samples", text="", icon=ICON_OPTION)


# -------------------------------------------------------------------
#  SUB PANELS
# -------------------------------------------------------------------


class RECOM_PT_eevee_shadows_settings(Panel):
    bl_label = "Shadows"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings.eevee, "use_shadows", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee.use_shadows

        col = layout.column()
        col.prop(settings.override_settings.eevee, "shadow_ray_count", text="Rays")
        col.prop(settings.override_settings.eevee, "shadow_step_count", text="Steps")


class RECOM_PT_eevee_raytracing_settings(Panel):
    bl_label = "Raytracing"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings.eevee, "use_raytracing", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee.use_raytracing

        col = layout.column()
        col.prop(settings.override_settings.eevee, "ray_tracing_method", text="Method")
        col.prop(settings.override_settings.eevee, "ray_tracing_resolution", text="Resolution")


class RECOM_PT_eevee_denoise_settings(Panel):
    bl_label = "Denoising"
    bl_parent_id = "RECOM_PT_eevee_raytracing_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee.use_raytracing
        layout.prop(settings.override_settings.eevee, "ray_tracing_denoise", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee.ray_tracing_denoise and settings.override_settings.eevee.use_raytracing
        )

        col = layout.column()
        col.prop(settings.override_settings.eevee, "ray_tracing_denoise_temporal")


class RECOM_PT_eevee_fast_gi_settings(Panel):
    bl_label = "Fast GI Approximation"
    bl_parent_id = "RECOM_PT_eevee_raytracing_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee.use_raytracing
        layout.prop(settings.override_settings.eevee, "fast_gi", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee.fast_gi and settings.override_settings.eevee.use_raytracing

        col = layout.column()
        col.prop(settings.override_settings.eevee, "trace_max_roughness", text="Threshold", slider=True)
        col.prop(settings.override_settings.eevee, "fast_gi_resolution", text="Resolution")
        col.prop(settings.override_settings.eevee, "fast_gi_step_count", text="Steps")
        col.prop(settings.override_settings.eevee, "fast_gi_distance", text="Distance")


class RECOM_PT_eevee_volumes_settings(Panel):
    bl_label = "Volumes"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column(align=True)
        col.prop(settings.override_settings.eevee, "volumetric_tile_size", text="Resolution")
        col.prop(settings.override_settings.eevee, "volume_samples", text="Steps")


classes = (
    RECOM_PT_eevee_settings_presets,
    RECOM_PT_eevee_settings,
    RECOM_PT_eevee_shadows_settings,
    RECOM_PT_eevee_raytracing_settings,
    RECOM_PT_eevee_denoise_settings,
    RECOM_PT_eevee_fast_gi_settings,
    RECOM_PT_eevee_volumes_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
