# ./panels/override_cycles_panel.py

import bpy
from bpy.types import Panel, Menu
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import *
from ..utils.helpers import get_render_engine


# -------------------------------------------------------------------
#  PRESETS
# -------------------------------------------------------------------


class RECOM_PT_samples_presets(PresetPanel, Panel):
    bl_label = "Samples Presets"
    preset_subdir = f"{ADDON_NAME}/samples"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.samples_preset_add"


class RECOM_PT_light_paths_presets(PresetPanel, Panel):
    bl_label = "Light Paths Presets"
    preset_subdir = f"{ADDON_NAME}/light_paths"
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.light_paths_preset_add"


# -------------------------------------------------------------------
#  CONTAINER PANEL
# -------------------------------------------------------------------


class RECOM_PT_cycles_overrides(Panel):
    """
    Invisible container that ensures these panels only show
    when the render engine is Cycles.
    """

    bl_label = "Cycles"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"HIDE_HEADER"}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        return render_engine == RE_CYCLES

    def draw(self, context):
        pass


# -------------------------------------------------------------------
#  INDIVIDUAL PANELS
# -------------------------------------------------------------------


class RECOM_PT_compute_device(Panel):
    bl_label = "Compute Device"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.cycles.device_override

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_device"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        row = layout.row()
        row.prop(settings.override_settings.cycles, "device", text="Type", expand=True)


class RECOM_PT_samples_settings(Panel):
    bl_label = "Sampling"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.cycles.sampling_override

    def draw_header_preset(self, context):
        layout = self.layout

        RECOM_PT_samples_presets.draw_panel_header(layout)

        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_sampling"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        row = layout.row(heading="Noise Threshold")
        row.prop(settings.override_settings.cycles, "use_adaptive_sampling", text="")
        sub = row.row()

        use_adaptive_sampling = settings.override_settings.cycles.use_adaptive_sampling

        sub.active = use_adaptive_sampling
        sub_row = sub.row(align=True)
        sub_row.prop(settings.override_settings.cycles, "adaptive_threshold", text="")
        sub_row.menu("RECOM_MT_adaptive_threshold", text="", icon=ICON_OPTION)

        samples_col = layout.column(align=True)
        row_samples = samples_col.row(align=True)
        row_samples.prop(
            settings.override_settings.cycles, "samples", text="Max Samples" if use_adaptive_sampling else "Samples"
        )
        row_samples.menu("RECOM_MT_samples", text="", icon=ICON_OPTION)

        if use_adaptive_sampling:
            row_samples = samples_col.row(align=True)
            row_samples.prop(settings.override_settings.cycles, "adaptive_min_samples", text="Min Samples")
            row_samples.menu("RECOM_MT_adaptive_min_samples", text="", icon=ICON_OPTION)

        row_samples = samples_col.row(align=True)
        row_samples.prop(settings.override_settings.cycles, "time_limit")
        row_samples.menu("RECOM_MT_time_limit", text="", icon=ICON_OPTION)


class RECOM_PT_denoise_settings(Panel):
    bl_label = "Denoise"
    bl_parent_id = "RECOM_PT_samples_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings
        layout.prop(settings.override_settings.cycles, "use_denoising", text="")

    def draw(self, context):
        layout = self.layout

        settings = context.window_manager.recom_render_settings
        layout.active = settings.override_settings.cycles.use_denoising

        row = layout.row()
        row.prop(settings.override_settings.cycles, "denoiser", expand=True)

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(settings.override_settings.cycles, "denoising_input_passes")

        if settings.override_settings.cycles.denoiser == "OPENIMAGEDENOISE":
            col.prop(settings.override_settings.cycles, "denoising_prefilter")
            col.prop(settings.override_settings.cycles, "denoising_quality")
            col.prop(settings.override_settings.cycles, "denoising_use_gpu")

        layer_row = layout.row(heading="View Layer")
        layer_row.use_property_split = True
        layer_row.use_property_decorate = False
        layer_row.prop(settings.override_settings.cycles, "denoising_store_passes", text="Denoising Data")


class RECOM_PT_light_path_settings(Panel):
    bl_label = "Light Paths"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.cycles.light_path_override

    def draw_header(self, context):
        pass

    def draw_header_preset(self, context):
        layout = self.layout

        RECOM_PT_light_paths_presets.draw_panel_header(self.layout)

        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_light_paths"
        layout.separator(factor=0.25)

    def draw(self, context):
        pass


class RECOM_PT_max_bounces_settings(Panel):
    bl_label = "Max Bounces"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column()
        col.prop(settings.override_settings.cycles, "max_bounces", text="Total")

        col = layout.column(align=True)
        col.prop(settings.override_settings.cycles, "diffuse_bounces", text="Diffuse")
        col.prop(settings.override_settings.cycles, "glossy_bounces", text="Glossy")
        col.prop(settings.override_settings.cycles, "transmission_bounces", text="Transmission")
        col.prop(settings.override_settings.cycles, "volume_bounces", text="Volume")
        col = layout.column()
        col.prop(settings.override_settings.cycles, "transparent_bounces", text="Transparent")


class RECOM_PT_clamping_settings(Panel):
    bl_label = "Clamping"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings

        col = layout.column(align=True)
        col.prop(settings.override_settings.cycles, "sample_clamp_direct", text="Direct Light")
        col.prop(settings.override_settings.cycles, "sample_clamp_indirect", text="Indirect Light")


class RECOM_PT_caustics_settings(Panel):
    bl_label = "Caustics"
    bl_parent_id = "RECOM_PT_light_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        settings = context.window_manager.recom_render_settings

        col = layout.column()
        col.prop(settings.override_settings.cycles, "blur_glossy")
        col = layout.column(heading="Caustics", align=True)
        col.prop(settings.override_settings.cycles, "caustics_reflective", text="Reflective")
        col.prop(settings.override_settings.cycles, "caustics_refractive", text="Refractive")


class RECOM_PT_performance_settings(Panel):
    bl_label = "Performance"
    bl_parent_id = "RECOM_PT_cycles_overrides"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.cycles.performance_override

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_performance"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column(heading="")
        col.prop(settings.override_settings.cycles, "use_tiling")
        row_sub = col.row()
        row_sub.active = settings.override_settings.cycles.use_tiling
        row_sub.prop(settings.override_settings.cycles, "tile_size")
        row_sub.menu("RECOM_MT_tile_size", text="", icon=ICON_OPTION)

        col = layout.column(heading="Animation")
        col.prop(settings.override_settings.cycles, "persistent_data")


classes = (
    RECOM_PT_cycles_overrides,
    RECOM_PT_compute_device,
    RECOM_PT_samples_presets,
    RECOM_PT_samples_settings,
    RECOM_PT_denoise_settings,
    RECOM_PT_light_paths_presets,
    RECOM_PT_light_path_settings,
    RECOM_PT_max_bounces_settings,
    RECOM_PT_clamping_settings,
    RECOM_PT_caustics_settings,
    RECOM_PT_performance_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
