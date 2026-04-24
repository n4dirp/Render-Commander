# ./panels/override_settings_panel.py


import logging

import bpy
from bpy.types import Panel, UIList, Menu, Operator
from bl_ui.utils import PresetPanel

from ..preferences import get_addon_preferences
from ..utils.constants import (
    RE_EEVEE_NEXT,
    RE_EEVEE,
    RE_CYCLES,
    MODE_SINGLE,
    MODE_SEQ,
    MODE_LIST,
    ICON_OPTION,
    ICON_SYNC,
    RESERVED_TOKENS,
)
from ..utils.helpers import (
    get_default_resolution,
    get_render_engine,
    redraw_ui,
)
from ..operators.presets import PRESET_REGISTRY


log = logging.getLogger(__name__)

# Map: Group -> ID -> (Label, Property Name, Icon)
OVERRIDE_MAP = {
    "Render": {
        "cycles_device": ("Cycles Device", "cycles.device_override", "BLANK1"),
        "cycles_sampling": ("Cycles Sampling", "cycles.sampling_override", "BLANK1"),
        "cycles_performance": ("Cycles Performance", "cycles.performance_override", "BLANK1"),
        "eevee_all": ("EEVEE Sampling", "eevee_override", "BLANK1"),
        "motion_blur": ("Motion Blur", "motion_blur_override", "BLANK1"),
    },
    "Output": {
        "resolution": ("Resolution", "format_override", "IMAGE_BACKGROUND"),
        "frame_range": ("Frame Range", "frame_range_override", "PREVIEW_RANGE"),
        "output_path": ("Output Path", "output_path_override", "FILE_FOLDER"),
        "file_format": ("File Format", "file_format_override", "FILE_IMAGE"),
    },
    "Data": {
        "camera_settings": ("Camera", "cameras_override", "OUTLINER_DATA_CAMERA"),
        "compositor": ("Compositing", "compositor_override", "NODE_COMPOSITING"),
        "custom_api": ("Advanced", "use_data_path_overrides", "SYSTEM"),
    },
}


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
    """Remove and reset all enabled overrides"""

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

        IGNORE_PATHS = {
            "active_data_path_index",
            "cached_auto_width",
            "cached_auto_height",
            "resolved_directory",
            "resolved_filename",
            "resolved_path",
        }

        for group_items in OVERRIDE_MAP.values():
            for data in group_items.values():
                prop_path = data[1]
                IGNORE_PATHS.add(prop_path)

        def reset_pg(pg, current_path=""):
            for prop in pg.bl_rna.properties:
                pid = prop.identifier

                full_path = f"{current_path}.{pid}" if current_path else pid

                if pid in {"rna_type", "name"} or full_path in IGNORE_PATHS or pid in IGNORE_PATHS:
                    continue

                if prop.type == "COLLECTION":
                    getattr(pg, pid).clear()

                elif prop.type == "POINTER":
                    sub_pg = getattr(pg, pid)
                    if sub_pg:
                        reset_pg(sub_pg, current_path=full_path)
                else:
                    if not prop.is_readonly:
                        pg.property_unset(pid)

        reset_pg(settings, current_path="")

        redraw_ui()

        log.debug("Override settings reset to defaults")
        return {"FINISHED"}


class RECOM_MT_add_override_menu(Menu):
    bl_label = "Add Override"
    bl_description = "Add non-destructive overrides to the render script"

    def draw(self, context):
        layout = self.layout
        settings = context.window_manager.recom_render_settings.override_settings
        render_engine = get_render_engine(context)

        items_drawn_total = 0
        first_render_item_processed = False

        for group_name, items in OVERRIDE_MAP.items():
            group_items_to_draw = []

            for oid, (label, prop_path, icon) in items.items():
                if "cycles" in oid and render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
                    continue
                if "eevee" in oid and render_engine == RE_CYCLES:
                    continue

                if not is_override_active(settings, prop_path):
                    # Apply SCENE icon only to first item in Render group
                    if group_name == "Render" and not first_render_item_processed:
                        icon = "SCENE"
                        first_render_item_processed = True

                    group_items_to_draw.append((oid, label, icon))

            if group_items_to_draw:
                if items_drawn_total > 0:
                    layout.separator()

                for oid, label, icon in group_items_to_draw:
                    op = layout.operator("recom.manage_override", text=label, icon=icon)
                    op.action = "ADD"
                    op.override_id = oid

                items_drawn_total += len(group_items_to_draw)

        if items_drawn_total == 0:
            layout.label(text="All overrides active")


#  Presets
#################################################


class RECOM_PT_overrides_presets(PresetPanel, Panel):
    bl_label = "Override Presets"
    preset_subdir = PRESET_REGISTRY["overrides_main"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.overrides_preset_add"


class RECOM_PT_samples_presets(PresetPanel, Panel):
    bl_label = "Samples Presets"
    preset_subdir = PRESET_REGISTRY["cycles_samples"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.samples_preset_add"


class RECOM_PT_resolution_presets(PresetPanel, Panel):
    bl_label = "Resolution Presets"
    preset_subdir = PRESET_REGISTRY["resolution"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.resolution_preset_add"


class RECOM_PT_output_presets(PresetPanel, Panel):
    bl_label = "Output Path Presets"
    preset_subdir = PRESET_REGISTRY["output_path"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.output_preset_add"


class RECOM_PT_custom_variables_presets(PresetPanel, Panel):
    bl_label = "Custom Variables Presets"
    preset_subdir = PRESET_REGISTRY["custom_variables"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.custom_variables_preset_add"


class RECOM_PT_override_advanced_property_presets(PresetPanel, Panel):
    bl_label = "Advanced Property Override Presets"
    preset_subdir = PRESET_REGISTRY["advanced_props"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.override_advanced_properties_preset_add"


#  Panels
#################################################


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
        return prefs.visible_panels.override_settings

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
        remove_row.operator("recom.remove_all_overrides", text="", icon="PANEL_CLOSE")


class RECOM_PT_import_overrides_popup(Panel):
    bl_label = "Import Settings"
    bl_description = "Add overrides and populate with scene values"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)

        layout.label(text="Import Settings")

        col = layout.column(align=True)

        if render_engine == RE_CYCLES:
            col.prop(prefs.override_import_settings, "import_compute_device", text="Cycles Device")
            col.prop(prefs.override_import_settings, "import_sampling", text="Cycles Sampling")
            col.prop(prefs.override_import_settings, "import_performance", text="Cycles Performance")
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            col.prop(prefs.override_import_settings, "import_eevee_settings", text="EEVEE Sampling")
        col.prop(prefs.override_import_settings, "import_motion_blur", text="Motion Blur")

        col.separator(factor=0.5)
        col.prop(prefs.override_import_settings, "import_resolution", text="Resolution")
        col.prop(prefs.override_import_settings, "import_frame_range", text="Frame Range")
        col.prop(prefs.override_import_settings, "import_output_path", text="Output Path")
        col.prop(prefs.override_import_settings, "import_output_format", text="File Format")

        col.separator(factor=0.5)
        col.prop(prefs.override_import_settings, "import_compositor", text="Compositing")

        col.separator(factor=0.5)
        layout.operator("recom.import_all_settings", text="Import", icon=ICON_SYNC)


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


class RECOM_PT_compute_device(Panel):
    bl_label = "Cycles Device"
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
    bl_label = "Cycles Sampling"
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
        row = layout.row(align=True)
        RECOM_PT_samples_presets.draw_panel_header(row)
        op = row.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_sampling"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        # Mode
        layout.row().prop(settings.override_settings.cycles, "sampling_mode", expand=True)

        if settings.override_settings.cycles.sampling_mode == "FACTOR":
            layout.prop(settings.override_settings.cycles, "sampling_factor")
        else:
            row = layout.row(heading="Noise Threshold")
            row.prop(settings.override_settings.cycles, "use_adaptive_sampling", text="")

            use_adaptive_sampling = settings.override_settings.cycles.use_adaptive_sampling

            sub = row.row()
            sub.active = use_adaptive_sampling
            sub_row = sub.row(align=True)
            sub_row.prop(settings.override_settings.cycles, "adaptive_threshold", text="")
            sub_row.menu("RECOM_MT_adaptive_threshold", text="", icon=ICON_OPTION)

            samples_col = layout.column(align=True)
            row_samples = samples_col.row(align=True)
            row_samples.prop(
                settings.override_settings.cycles,
                "samples",
                text="Max Samples" if use_adaptive_sampling else "Samples",
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


class RECOM_PT_performance_settings(Panel):
    bl_label = "Cycles Performance"
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


class RECOM_PT_eevee_settings(Panel):
    bl_label = "EEVEE Sampling"
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
        row = layout.row(align=True)

        op = row.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "eevee_all"

        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings

        col = layout.column(align=True)
        col.prop(settings.override_settings.eevee, "samples", text="Samples")


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
        return settings.frame_range_override

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

        if prefs.launch_mode == MODE_SINGLE:
            row = layout.row(align=True)
            row.prop(settings.override_settings, "frame_current", text="Current Frame")

        if prefs.launch_mode == MODE_SEQ:
            col = layout.column(align=True)
            col.prop(settings.override_settings, "frame_start", text="Frame Start")
            col.prop(settings.override_settings, "frame_end", text="End")
            col.prop(settings.override_settings, "frame_step", text="Step")

        if prefs.launch_mode == MODE_LIST:
            layout.label(text="No supported in current render mode")


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
            row_x.prop(settings.override_settings, "resolution_x", text="X")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            auto_height = settings.override_settings.cached_auto_height
            settings.override_settings.resolution_preview = auto_height

            row_y = col_res.row(align=True)
            row_y.enabled = False
            row_y.prop(settings.override_settings, "resolution_preview", text="Auto-Y")
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)
        elif settings.override_settings.resolution_mode == "SET_HEIGHT":
            auto_width = settings.override_settings.cached_auto_width
            settings.override_settings.resolution_preview = auto_width

            row_x = col_res.row(align=True)
            row_x.enabled = False
            row_x.prop(settings.override_settings, "resolution_preview", text="Auto-X")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Y")
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)
        else:
            row_x = col_res.row(align=True)
            row_x.prop(settings.override_settings, "resolution_x", text="X")
            row_x.menu("RECOM_MT_resolution_x", text="", icon=ICON_OPTION)

            row_y = col_res.row(align=True)
            row_y.prop(settings.override_settings, "resolution_y", text="Y")
            row_y.menu("RECOM_MT_resolution_y", text="", icon=ICON_OPTION)

        # Scale resolution menu
        scale_col = layout.column()

        scale_row = scale_col.row(align=True)
        scale_row.prop(settings.override_settings, "custom_render_scale", text="%", slider=True)
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
            settings.override_settings,
            "output_directory",
            text="",
            icon="FILE_FOLDER",
            placeholder="Directory",
        )
        col.prop(
            settings.override_settings,
            "output_filename",
            text="",
            icon="FILE",
            placeholder="Filename",
        )


class RECOM_PT_insert_variables(Panel):
    bl_label = "Path Variables"
    bl_parent_id = "RECOM_PT_output_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings
        prefs = get_addon_preferences(context)

        col = layout.column()
        col.menu("RECOM_MT_insert_variable_root", text="Add Variable", icon="ADD")

        col = layout.column()
        row = col.row(align=False)
        row.prop(settings.override_settings, "variable_insert_target", text="Target", expand=True)
        col.prop(prefs, "use_underscore_separator", text="Add Underscore")


class RECOM_PT_custom_variables(Panel):
    bl_label = "Custom Variables"
    bl_parent_id = "RECOM_PT_insert_variables"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        RECOM_PT_custom_variables_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        prefs = get_addon_preferences(context)

        root_col = layout.column()
        content_row = root_col.row()
        show_op = len(prefs.custom_variables)

        # Variable list
        list_col = content_row.column()
        rows = 4 if show_op else 3
        list_col.template_list(
            "RECOM_UL_custom_variables",
            "",
            prefs,
            "custom_variables",
            prefs,
            "active_custom_variable_index",
            rows=rows,
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

        if not show_op:
            return

        # Move buttons
        move_col = controls_col.column(align=True)
        move_col.active = has_selection and len(prefs.custom_variables) > 1
        move_col.operator("recom.move_custom_variable_up", text="", icon="TRIA_UP")
        move_col.operator("recom.move_custom_variable_down", text="", icon="TRIA_DOWN")

        # Variable details
        if prefs.active_custom_variable_index >= 0 and has_selection:
            active_var = prefs.custom_variables[prefs.active_custom_variable_index]
            root_col.separator(factor=0.5)
            details_col = root_col.column(align=True)
            details_col.prop(active_var, "name", text="Variable Name")
            token_row = details_col.row(align=True)
            if active_var.token in RESERVED_TOKENS:
                token_row.alert = True
            token_row.prop(active_var, "token", text="Token")
            details_col.prop(active_var, "value", text="Value")


class RECOM_UL_custom_variables(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        split = layout.split(factor=0.6)
        split.prop(item, "name", text="", emboss=False, placeholder="Name", icon="TAG")
        row_sub = split.row(align=True)
        row_sub.active = False
        row_sub.prop(item, "token", text="", emboss=False)


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
        col.prop(settings.override_settings, "file_format", text="File Format")

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


class RECOM_UL_data_path_overrides(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index, flt_flag):
        layout.prop(item, "name", text="", emboss=False, placeholder="Data Path")
        row = layout.row(align=True)
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


class RECOM_PT_data_path_settings(Panel):
    bl_label = "Advanced"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_order = 6

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.use_data_path_overrides

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

        search_row = layout.row()
        search_row.prop(settings, "property_path_input", text="", icon="VIEWZOOM", placeholder="Data Path")

        root_col = layout.column()
        content_row = root_col.row()

        # Variable list
        list_col = content_row.column(align=True)
        list_col.template_list(
            "RECOM_UL_data_path_overrides",
            "",
            settings,
            "data_path_overrides",
            settings,
            "active_data_path_index",
            rows=3,
        )

        # Controls
        controls_col = content_row.column()
        add_remove_col = controls_col.column(align=True)
        add_remove_col.operator("recom.add_advanced_property_override", text="", icon="ADD")
        add_remove_col.operator("recom.remove_advanced_property_override", text="", icon="REMOVE")


class RECOM_PT_data_path_properties(Panel):
    bl_label = "Property Details"
    bl_parent_id = "RECOM_PT_data_path_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        settings = context.window_manager.recom_render_settings.override_settings
        return settings.active_data_path_index >= 0 and settings.data_path_overrides

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        settings = context.window_manager.recom_render_settings.override_settings
        item = settings.data_path_overrides[settings.active_data_path_index]

        details_col = layout.column()

        col = details_col.column(align=True)
        # col.label(text="Data Path:")
        col.prop(item, "data_path", text="")

        col = details_col.column(align=True)
        col.prop(item, "name")
        col.prop(item, "prop_type", text="Type")

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


classes = (
    RECOM_OT_manage_override,
    RECOM_OT_remove_all_overrides,
    RECOM_OT_reset_overrides,
    RECOM_MT_add_override_menu,
    RECOM_PT_import_overrides_popup,
    RECOM_PT_overrides_presets,
    RECOM_PT_scene_override_settings,
    # Render
    RECOM_PT_cycles_overrides,
    RECOM_PT_compute_device,
    RECOM_PT_samples_presets,
    RECOM_PT_samples_settings,
    RECOM_PT_denoise_settings,
    RECOM_PT_performance_settings,
    RECOM_PT_eevee_settings,
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
    RECOM_PT_output_format_settings,
    # Data
    RECOM_PT_camera_settings,
    RECOM_PT_compositor_settings,
    RECOM_PT_override_advanced_property_presets,
    RECOM_UL_data_path_overrides,
    RECOM_PT_data_path_settings,
    RECOM_PT_data_path_properties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
