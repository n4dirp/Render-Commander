# ./panels/override_eevee_panel.py

import bpy
from bpy.types import Panel
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


class RECOM_PT_EEVEESettingsPresets(PresetPanel, Panel):
    bl_label = "EEVEE Settings Presets"
    preset_subdir = f"{ADDON_NAME}/eevee"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_eevee_preset"


class RECOM_PT_EEVEESettings(Panel):
    bl_label = "EEVEE"
    bl_idname = "RECOM_PT_eevee_settings"
    bl_parent_id = "RECOM_PT_render_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine in {"BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"}

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings, "eevee_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee_override

        row = layout.row(align=True)
        RECOM_PT_EEVEESettingsPresets.draw_panel_header(row)
        row.operator("recom.import_eevee_settings", text="", icon=ICON_SYNC, emboss=False)
        row.separator()

    def draw(self, context):
        pass


class RECOM_PT_EEVEESamplingSettings(Panel):
    bl_label = "Sampling"
    bl_idname = "RECOM_PT_eevee_sampling_settings"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee_override

        row = layout.row(align=True)
        row.prop(settings.override_settings.eevee, "samples", text="Samples")
        row.separator(factor=0.5)
        row.menu("RECOM_MT_eevee_samples", text="", icon=ICON_OPTION)


class RECOM_PT_EEVEEShadowsSettings(Panel):
    bl_label = "Shadows"
    bl_idname = "RECOM_PT_eevee_shadows_settings"
    bl_parent_id = "RECOM_PT_eevee_sampling_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee_override

        layout.prop(settings.override_settings.eevee, "use_shadows", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_shadows
        )

        col = layout.column()
        col.prop(settings.override_settings.eevee, "shadow_ray_count", text="Rays")
        col.prop(settings.override_settings.eevee, "shadow_step_count", text="Steps")


class RECOM_PT_EEVEERaytracingSettings(Panel):
    bl_label = "Raytracing"
    bl_idname = "RECOM_PT_eevee_raytracing_settings"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee_override

        layout.prop(settings.override_settings.eevee, "use_raytracing", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_raytracing
        )

        col = layout.column()

        rt_col = col.column()
        rt_col.active = settings.override_settings.eevee.use_raytracing
        rt_col.prop(settings.override_settings.eevee, "ray_tracing_method", text="Method")
        rt_col.prop(settings.override_settings.eevee, "ray_tracing_resolution", text="Resolution")


class RECOM_PT_EEVEEDenoiseSettings(Panel):
    bl_label = "Denoising"
    bl_idname = "RECOM_PT_eevee_denoise_settings"
    bl_parent_id = "RECOM_PT_eevee_raytracing_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_raytracing
        )

        layout.prop(settings.override_settings.eevee, "ray_tracing_denoise", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_raytracing
            and settings.override_settings.eevee.ray_tracing_denoise
        )

        col = layout.column()
        col.prop(settings.override_settings.eevee, "ray_tracing_denoise_temporal")


class RECOM_PT_EEVEEFastGISettings(Panel):
    bl_label = "Fast GI Approximation"
    bl_idname = "RECOM_PT_eevee_fast_gi_settings"
    bl_parent_id = "RECOM_PT_eevee_raytracing_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_raytracing
        )
        layout.prop(settings.override_settings.eevee, "fast_gi", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.eevee_override
            and settings.override_settings.eevee.use_raytracing
            and settings.override_settings.eevee.fast_gi
        )

        col = layout.column()

        gi_col = col.column()
        gi_col.active = settings.override_settings.eevee.fast_gi
        gi_col.prop(
            settings.override_settings.eevee, "trace_max_roughness", text="Threshold", slider=True
        )
        gi_col.prop(settings.override_settings.eevee, "fast_gi_resolution", text="Resolution")
        gi_col.prop(settings.override_settings.eevee, "fast_gi_step_count", text="Steps")
        gi_col.prop(settings.override_settings.eevee, "fast_gi_distance", text="Distance")


class RECOM_PT_EEVEEVolumesSettings(Panel):
    bl_label = "Volumes"
    bl_idname = "RECOM_PT_eevee_volumes_settings"
    bl_parent_id = "RECOM_PT_eevee_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.eevee_override

        col = layout.column()
        col.prop(settings.override_settings.eevee, "volumetric_tile_size", text="Resolution")
        col.prop(settings.override_settings.eevee, "volume_samples", text="Steps")


classes = (
    RECOM_PT_EEVEESettingsPresets,
    RECOM_PT_EEVEESettings,
    RECOM_PT_EEVEESamplingSettings,
    RECOM_PT_EEVEEShadowsSettings,
    RECOM_PT_EEVEERaytracingSettings,
    RECOM_PT_EEVEEDenoiseSettings,
    RECOM_PT_EEVEEFastGISettings,
    RECOM_PT_EEVEEVolumesSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
