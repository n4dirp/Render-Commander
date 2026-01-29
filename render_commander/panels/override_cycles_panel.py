# ./panels/override_cycles_panel.py

import bpy
from bpy.types import Panel
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


class RECOM_PT_CyclesSetting(Panel):
    bl_label = "Cycles"
    bl_idname = "RECOM_PT_cycles_overrides"
    bl_parent_id = "RECOM_PT_render_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"HIDE_HEADER"}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES"

    def draw(self, context):
        pass


class RECOM_PT_ComputeDevice(Panel):
    bl_label = "Device"
    bl_idname = "RECOM_PT_compute_device"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES" and prefs.visible_panels.compute_device

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings.cycles, "device_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.device_override
        row = layout.row(align=True)
        # row.operator("recom.import_compute_device", text="", icon=ICON_SYNC, emboss=False)
        # row.separator(factor=1)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.device_override

        row = layout.row()
        row.prop(settings.override_settings.cycles, "device", text="Type", expand=True)


class RECOM_PT_SamplesPresets(PresetPanel, Panel):
    bl_label = "Samples Presets"
    preset_subdir = f"{ADDON_NAME}/samples"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_samples_preset"


class RECOM_PT_SamplesSettings(Panel):
    bl_label = "Sampling"
    bl_idname = "RECOM_PT_samples_settings"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES" and prefs.visible_panels.samples

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings.cycles, "sampling_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.sampling_override

        row = layout.row(align=True)
        RECOM_PT_SamplesPresets.draw_panel_header(row)
        # row.operator("recom.import_sampling", text="", icon=ICON_SYNC, emboss=False)
        # row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.sampling_override

        row = layout.row(heading="Noise Threshold")
        row.prop(settings.override_settings.cycles, "use_adaptive_sampling", text="")
        sub = row.row()
        sub.active = settings.override_settings.cycles.use_adaptive_sampling
        sub_row = sub.row(align=True)
        sub_row.prop(settings.override_settings.cycles, "adaptive_threshold", text="")
        sub_row.menu("RECOM_MT_adaptive_threshold", text="", icon=ICON_OPTION)

        samples_col = layout.column(align=True)
        row_samples = samples_col.row(align=True)
        row_samples.prop(settings.override_settings.cycles, "samples", text="Max Samples")
        row_samples.menu("RECOM_MT_samples", text="", icon=ICON_OPTION)

        row_samples = samples_col.row(align=True)
        row_samples.prop(settings.override_settings.cycles, "adaptive_min_samples", text="Min Samples")
        row_samples.menu("RECOM_MT_adaptive_min_samples", text="", icon=ICON_OPTION)

        row_samples = layout.row(align=True)
        row_samples.prop(settings.override_settings.cycles, "time_limit")
        row_samples.menu("RECOM_MT_time_limit", text="", icon=ICON_OPTION)


class RECOM_PT_DenoiseSettings(Panel):
    bl_label = "Denoise"
    bl_idname = "RECOM_PT_denoise_settings"
    bl_parent_id = "RECOM_PT_samples_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.sampling_override
        layout.prop(settings.override_settings.cycles, "use_denoising", text="")

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings
        layout.active = (
            settings.override_settings.cycles.sampling_override and settings.override_settings.cycles.use_denoising
        )

        col = layout.column()
        row = col.row()
        row.prop(settings.override_settings.cycles, "denoiser", expand=True)
        col.prop(settings.override_settings.cycles, "denoising_input_passes")

        if settings.override_settings.cycles.denoiser == "OPENIMAGEDENOISE":
            col.prop(settings.override_settings.cycles, "denoising_prefilter")
            col.prop(settings.override_settings.cycles, "denoising_quality")
            col.prop(settings.override_settings.cycles, "denoising_use_gpu")

        row = layout.row(heading="View Layer")
        row.prop(settings.override_settings.cycles, "denoising_store_passes", text="Denoising Data")


class RECOM_PT_LightPathsPresets(PresetPanel, Panel):
    bl_label = "Light Paths Presets"
    preset_subdir = f"{ADDON_NAME}/light_paths"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.add_light_paths_preset"


class RECOM_PT_LightPathSettings(Panel):
    bl_label = "Light Paths"
    bl_idname = "RECOM_PT_light_path_settings"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES" and prefs.visible_panels.light_paths

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings.cycles, "light_path_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.light_path_override

        row = layout.row(align=True)
        RECOM_PT_LightPathsPresets.draw_panel_header(row)
        # row.operator("recom.import_light_paths", text="", icon=ICON_SYNC, emboss=False)
        # row.separator()

    def draw(self, context):
        pass


class RECOM_PT_MaxBouncesSettings(Panel):
    bl_label = "Max Bounces"
    bl_idname = "RECOM_PT_max_bounces_settings"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.cycles.light_path_override

        col = layout.column()
        col.prop(settings.override_settings.cycles, "max_bounces", text="Total")

        col = layout.column(align=True)
        col.prop(settings.override_settings.cycles, "diffuse_bounces", text="Diffuse")
        col.prop(settings.override_settings.cycles, "glossy_bounces", text="Glossy")
        col.prop(settings.override_settings.cycles, "transmission_bounces", text="Transmission")
        col.prop(settings.override_settings.cycles, "volume_bounces", text="Volume")
        col = layout.column()
        col.prop(settings.override_settings.cycles, "transparent_bounces", text="Transparent")


class RECOM_PT_ClampingSettings(Panel):
    bl_label = "Clamping"
    bl_idname = "RECOM_PT_clamping_settings"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.cycles.light_path_override

        col = layout.column(align=True)
        col.prop(settings.override_settings.cycles, "sample_clamp_direct", text="Direct Light")
        col.prop(settings.override_settings.cycles, "sample_clamp_indirect", text="Indirect Light")


class RECOM_PT_CausticsSettings(Panel):
    bl_label = "Caustics"
    bl_idname = "RECOM_PT_caustics_settings"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        layout.active = settings.override_settings.cycles.light_path_override

        col = layout.column()
        col.prop(settings.override_settings.cycles, "blur_glossy")
        col = layout.column(heading="Caustics", align=True)
        col.prop(settings.override_settings.cycles, "caustics_reflective", text="Reflective")
        col.prop(settings.override_settings.cycles, "caustics_refractive", text="Refractive")


class RECOM_PT_PerformanceSettings(Panel):
    bl_label = "Performance"
    bl_idname = "RECOM_PT_performance_settings"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)
        return render_engine == "CYCLES" and prefs.visible_panels.performance

    def draw_header(self, context):
        settings = context.window_manager.recom_render_settings
        self.layout.prop(settings.override_settings.cycles, "performance_override", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.performance_override

        row = layout.row(align=True)
        # row.operator("recom.import_performance", text="", icon=ICON_SYNC, emboss=False)
        # row.separator()

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.performance_override

        col = layout.column(heading="")
        col.prop(settings.override_settings.cycles, "use_tiling")
        row_sub = col.row()
        row_sub.active = settings.override_settings.cycles.use_tiling
        row_sub.prop(settings.override_settings.cycles, "tile_size")
        # row_sub.separator(factor=0.5)
        row_sub.menu("RECOM_MT_tile_size", text="", icon=ICON_OPTION)

        col = layout.column(heading="Animation")
        col.prop(settings.override_settings.cycles, "persistent_data")


classes = (
    RECOM_PT_CyclesSetting,
    RECOM_PT_ComputeDevice,
    RECOM_PT_SamplesPresets,
    RECOM_PT_SamplesSettings,
    RECOM_PT_DenoiseSettings,
    RECOM_PT_LightPathsPresets,
    RECOM_PT_LightPathSettings,
    RECOM_PT_MaxBouncesSettings,
    RECOM_PT_ClampingSettings,
    RECOM_PT_CausticsSettings,
    RECOM_PT_PerformanceSettings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
