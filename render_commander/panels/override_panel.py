# ./panels/override_settings_panel.py


import logging

import bpy
from bl_ui.utils import PresetPanel
from bpy.types import Menu, Operator, Panel, UIList

from ..operators.presets import PRESET_REGISTRY
from ..utils.constants import (
    MODE_LIST,
    MODE_SEQ,
    MODE_SINGLE,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RCBasePanel,
    RCSubPanel,
)
from ..utils.helpers import (
    draw_label_value_box,
    get_addon_preferences,
    get_default_resolution,
    get_override_settings,
    get_render_engine,
    redraw_ui,
)

log = logging.getLogger(__name__)

# Map: Group -> ID -> (Label, Property Name, Icon)
OVERRIDE_MAP = {
    "Render": {
        "cycles_device": ("Cycles Device", "cycles.device_override", "BLANK1"),
        "cycles_sampling": ("Cycles Sampling", "cycles.sampling_override", "BLANK1"),
        "cycles_denoising": ("Cycles Denoising", "cycles.denoising_override", "BLANK1"),
        "cycles_performance": ("Cycles Performance", "cycles.performance_override", "BLANK1"),
        "eevee_all": ("EEVEE Sampling", "eevee_override", "BLANK1"),
        "motion_blur": ("Motion Blur", "motion_blur_override", "BLANK1"),
    },
    "Output": {
        "resolution": ("Resolution", "format_override", "IMAGE_BACKGROUND"),
        "frame_range": ("Frame Range", "frame_range_override", "PREVIEW_RANGE"),
        "file_format": ("File Format", "file_format_override", "FILE_IMAGE"),
        "output_path": ("Output Path", "output_path_override", "FILE_FOLDER"),
    },
    "Data": {
        "camera_settings": ("Camera", "cameras_override", "OUTLINER_DATA_CAMERA"),
        "compositor": ("Compositing", "compositor_override", "NODE_COMPOSITING"),
        "custom_api": ("Custom Properties", "use_data_path_overrides", "PROPERTIES"),
        "fps_converter": ("FPS Converter", "use_fps_converter", "FILE_REFRESH"),
        "overscan": ("Overscan", "use_overscan", "FULLSCREEN_ENTER"),
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
    bl_options = {"UNDO", "INTERNAL"}

    action: bpy.props.EnumProperty(items=[("ADD", "Add", ""), ("REMOVE", "Remove", "")], default="ADD")
    override_id: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        """Return the description for the override identified by override_id."""
        if properties.action == "REMOVE":
            data = get_override_tuple(properties.override_id)
            if data:
                return f"Remove {data[0]}"
            return "Remove override"
        override_settings = get_override_settings(context)
        data = get_override_tuple(properties.override_id)
        if not data:
            return ""
        prop_path = data[1]
        target, attr = resolve_override_prop(override_settings, prop_path)
        if target is None:
            return data[0]
        rna_type = getattr(type(target), "bl_rna", None)
        if rna_type is None:
            return data[0]
        rna_prop = rna_type.properties.get(attr)
        if rna_prop and rna_prop.description:
            return rna_prop.description
        return data[0]

    def execute(self, context):
        override_settings = get_override_settings(context)

        # Helper lookup
        data = get_override_tuple(self.override_id)
        if not data:
            return {"CANCELLED"}

        prop_path = data[1]

        # Toggle property via helper
        is_active = self.action == "ADD"
        set_override_state(override_settings, prop_path, is_active)

        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_remove_all_overrides(Operator):
    """Remove and reset all enabled overrides"""

    bl_idname = "recom.remove_all_overrides"
    bl_label = "Remove All Overrides"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    def execute(self, context):
        override_settings = get_override_settings(context)

        # Iterate flat list via helper
        for oid, label, prop_path, icon in iterate_all_overrides():
            if is_override_active(override_settings, prop_path):
                set_override_state(override_settings, prop_path, False)

        bpy.ops.recom.reset_overrides()
        redraw_ui()
        return {"FINISHED"}


class RECOM_OT_reset_overrides(Operator):
    """Reset all override settings to their default values"""

    bl_idname = "recom.reset_overrides"
    bl_label = "Reset to Defaults"
    bl_options = {"UNDO", "INTERNAL"}

    def execute(self, context):
        override_settings = get_override_settings(context)

        IGNORE_PATHS = {
            "active_data_path_index",
            "cached_auto_width",
            "cached_auto_height",
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

        reset_pg(override_settings, current_path="")

        redraw_ui()

        log.debug("Override settings reset to defaults")
        return {"FINISHED"}


class RECOM_MT_add_override_menu(Menu):
    bl_label = "Add Override"
    bl_description = "Add non-destructive overrides to the render script"

    def draw(self, context):
        layout = self.layout
        override_settings = get_override_settings(context)
        render_engine = get_render_engine(context)

        items_drawn_total = 0
        first_render_item_processed = False

        for group_name, items in OVERRIDE_MAP.items():
            group_items_to_draw = []

            for oid, (label, prop_path, icon) in items.items():
                if not self.is_engine_supported(oid, render_engine):
                    continue

                if not is_override_active(override_settings, prop_path):
                    # Apply SCENE icon only to first item in Render group
                    if group_name == "Render" and not first_render_item_processed:
                        icon = "SCENE"
                        first_render_item_processed = True

                    group_items_to_draw.append((oid, label, icon))

            if group_items_to_draw:
                if items_drawn_total > 0:
                    layout.separator(factor=1.5)

                for oid, label, icon in group_items_to_draw:
                    op = layout.operator("recom.manage_override", text=label, icon=icon)
                    op.action = "ADD"
                    op.override_id = oid
                    # description is set via the operator's classmethod description()

                items_drawn_total += len(group_items_to_draw)

        if items_drawn_total == 0:
            layout.label(text="All overrides active")

    def is_engine_supported(self, override_id, engine):
        if "cycles" in override_id:
            return engine == RE_CYCLES
        if "eevee" in override_id:
            return engine in {RE_EEVEE_NEXT, RE_EEVEE}
        if override_id == "motion_blur":
            return engine in {RE_CYCLES, RE_EEVEE_NEXT, RE_EEVEE}
        return True  # Defaults to visible for non-engine-specific overrides


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


class RECOM_PT_override_advanced_property_presets(PresetPanel, Panel):
    bl_label = "Advanced Property Override Presets"
    preset_subdir = PRESET_REGISTRY["advanced_props"]
    preset_operator = "script.execute_preset"
    preset_add_operator = "recom.override_advanced_properties_preset_add"


#  Panels
#################################################


class RECOM_PT_scene_override_settings(RCSubPanel, Panel):
    """Main scene overrides panel"""

    bl_label = "Overrides"
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
        row.menu("RECOM_MT_add_override_menu", text="Add Override", icon="ADD")
        row.popover(panel="RECOM_PT_import_overrides_popup", text="", icon="IMPORT")

        override_settings = get_override_settings(context)
        has_active_overrides = any(
            is_override_active(override_settings, prop_path) for _, _, prop_path, _ in iterate_all_overrides()
        )

        sub = row.row(align=True)
        sub.enabled = has_active_overrides
        sub.operator("recom.remove_all_overrides", text="", icon="TRASH")


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
            col.prop(
                prefs.override_import_settings,
                "import_compute_device",
                text="Cycles Device",
            )
            col.prop(
                prefs.override_import_settings,
                "import_sampling",
                text="Cycles Sampling",
            )
            col.prop(
                prefs.override_import_settings,
                "import_performance",
                text="Cycles Performance",
            )
        elif render_engine in {RE_EEVEE_NEXT, RE_EEVEE}:
            col.prop(
                prefs.override_import_settings,
                "import_eevee_settings",
                text="EEVEE Sampling",
            )
        col.prop(prefs.override_import_settings, "import_motion_blur", text="Motion Blur")

        col.separator(factor=0.5)
        col.prop(prefs.override_import_settings, "import_resolution", text="Resolution")
        col.prop(prefs.override_import_settings, "import_frame_range", text="Frame Range")
        col.prop(prefs.override_import_settings, "import_output_path", text="Output Path")
        col.prop(prefs.override_import_settings, "import_output_format", text="File Format")

        col.separator(factor=0.5)
        col.prop(prefs.override_import_settings, "import_compositor", text="Compositing")

        col.separator(factor=0.5)
        layout.operator("recom.import_all_settings", text="Import", icon="IMPORT")


class RECOM_PT_cycles_overrides(RCBasePanel, Panel):
    bl_label = "Cycles"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_options = {"HIDE_HEADER"}
    bl_order = 0

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        return render_engine == RE_CYCLES

    def draw(self, context):
        pass


class RECOM_PT_compute_device(RCBasePanel, Panel):
    bl_label = "Cycles Device"
    bl_parent_id = "RECOM_PT_cycles_overrides"

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.cycles.device_override

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

        override_settings = get_override_settings(context)

        row = layout.row()
        row.prop(override_settings.cycles, "device", text="Type", expand=True)


class RECOM_PT_samples_settings(RCBasePanel, Panel):
    bl_label = "Cycles Sampling"
    bl_parent_id = "RECOM_PT_cycles_overrides"

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.cycles.sampling_override

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

        override_settings = get_override_settings(context)

        # Mode
        layout.row().prop(override_settings.cycles, "sampling_mode", expand=True)

        if override_settings.cycles.sampling_mode == "FACTOR":
            row = layout.row(align=True)
            row.prop(override_settings.cycles, "sampling_factor", text="Samples %", slider=True)
            row.menu("RECOM_MT_sampling_factor", text="", icon="DOWNARROW_HLT")
        else:
            row = layout.row(heading="Noise Threshold")
            row.prop(override_settings.cycles, "use_adaptive_sampling", text="")

            use_adaptive_sampling = override_settings.cycles.use_adaptive_sampling

            sub = row.row(align=True)
            sub.active = use_adaptive_sampling
            sub.prop(override_settings.cycles, "adaptive_threshold", text="")
            sub.menu("RECOM_MT_adaptive_threshold", text="", icon="DOWNARROW_HLT")

            col = layout.column(align=True)
            row = col.row(align=True)
            row.prop(override_settings.cycles, "samples", text="Max Samples" if use_adaptive_sampling else "Samples")
            row.menu("RECOM_MT_samples", text="", icon="DOWNARROW_HLT")

            if use_adaptive_sampling:
                row = col.row(align=True)
                row.prop(override_settings.cycles, "adaptive_min_samples", text="Min Samples")
                row.menu("RECOM_MT_adaptive_min_samples", text="", icon="DOWNARROW_HLT")

            row = col.row(align=True)
            row.prop(override_settings.cycles, "time_limit")
            row.menu("RECOM_MT_time_limit", text="", icon="DOWNARROW_HLT")


class RECOM_PT_denoise_settings(RCBasePanel, Panel):
    bl_label = "Cycles Denoising"
    bl_parent_id = "RECOM_PT_cycles_overrides"

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.cycles.denoising_override

    def draw_header(self, context):
        override_settings = get_override_settings(context)
        self.layout.prop(override_settings.cycles, "use_denoising", text="")

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="X", emboss=False)
        op.action = "REMOVE"
        op.override_id = "cycles_denoising"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout

        override_settings = get_override_settings(context)
        layout.active = override_settings.cycles.use_denoising

        row = layout.row()
        row.prop(override_settings.cycles, "denoiser", expand=True)

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        col.prop(override_settings.cycles, "denoising_input_passes")

        if override_settings.cycles.denoiser == "OPENIMAGEDENOISE":
            col.prop(override_settings.cycles, "denoising_prefilter")
            col.prop(override_settings.cycles, "denoising_quality")
            col.prop(override_settings.cycles, "denoising_use_gpu")


class RECOM_PT_performance_settings(RCBasePanel, Panel):
    bl_label = "Cycles Performance"
    bl_parent_id = "RECOM_PT_cycles_overrides"

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.cycles.performance_override

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

        override_settings = get_override_settings(context)

        col = layout.column(heading="")
        col.prop(override_settings.cycles, "use_tiling", text="Tiling")
        row = col.row()
        row.active = override_settings.cycles.use_tiling
        row.prop(override_settings.cycles, "tile_size")
        row.menu("RECOM_MT_tile_size", text="", icon="DOWNARROW_HLT")

        col = layout.column(heading="Animation")
        col.prop(override_settings.cycles, "persistent_data")


class RECOM_PT_eevee_settings(RCBasePanel, Panel):
    bl_label = "EEVEE Sampling"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        render_engine = get_render_engine(context)
        override_settings = get_override_settings(context)
        return (render_engine in {RE_EEVEE_NEXT, RE_EEVEE}) and override_settings.eevee_override

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

        override_settings = get_override_settings(context)

        col = layout.column(align=True)
        col.prop(override_settings.eevee, "samples", text="Samples")


class RECOM_PT_motion_blur_settings(RCBasePanel, Panel):
    bl_label = "Motion Blur"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.motion_blur_override

    def draw_header(self, context):
        override_settings = get_override_settings(context)
        self.layout.prop(override_settings, "use_motion_blur", text="")

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

        override_settings = get_override_settings(context)

        col = layout.column()
        col.active = override_settings.use_motion_blur
        col.prop(override_settings, "motion_blur_position", text="Position")
        col.prop(override_settings, "motion_blur_shutter", text="Shutter", slider=True)


class RECOM_PT_frame_range_settings(RCBasePanel, Panel):
    bl_label = "Frame Range"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 2

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        prefs = get_addon_preferences(context)
        return override_settings.frame_range_override and prefs.launch_mode != MODE_LIST

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

        override_settings = get_override_settings(context)
        prefs = get_addon_preferences(context)

        if prefs.launch_mode == MODE_SINGLE:
            row = layout.row(align=True)
            row.prop(override_settings, "frame_current", text="Current Frame")

        if prefs.launch_mode == MODE_SEQ:
            col = layout.column(align=True)
            col.prop(override_settings, "frame_start", text="Frame Start")
            col.prop(override_settings, "frame_end", text="End")
            col.prop(override_settings, "frame_step", text="Step")


class RECOM_PT_fps_converter_settings(RCBasePanel, Panel):
    bl_label = "FPS Converter"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.use_fps_converter

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "fps_converter"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        override_settings = get_override_settings(context)
        layout.active = override_settings.use_fps_converter

        col = layout.column()
        col.prop(override_settings, "target_fps", text="Target")
        if override_settings.target_fps == "CUSTOM":
            col.prop(override_settings, "custom_fps", text="Value")
        col.prop(override_settings, "preserve_motion_blur", text="Preserve Motion Blur")


class RECOM_PT_resolution_settings(RCBasePanel, Panel):
    bl_label = "Resolution"
    bl_description = "Resolution"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 1

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.format_override

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

        override_settings = get_override_settings(context)

        col = layout.column()

        row = col.row(heading="Mode")
        row.prop(override_settings, "resolution_override", text="")
        sub = row.row()
        sub.active = override_settings.resolution_override
        sub_row = sub.row(align=True)
        sub_row.prop(override_settings, "resolution_mode", text="")

        if override_settings.resolution_override:
            # Conditional UI Based on Mode
            col = col.column(align=True)
            col.active = override_settings.resolution_override

            if override_settings.resolution_mode == "SET_WIDTH":
                row = col.row(align=True)
                row.prop(override_settings, "resolution_x", text="X")
                row.menu("RECOM_MT_resolution_x", text="", icon="DOWNARROW_HLT")

                auto_height = override_settings.cached_auto_height
                override_settings.resolution_preview = auto_height

                row = col.row(align=True)
                row.enabled = False
                row.prop(override_settings, "resolution_preview", text="Auto-Y")
                row.menu("RECOM_MT_resolution_y", text="", icon="DOWNARROW_HLT")
            elif override_settings.resolution_mode == "SET_HEIGHT":
                auto_width = override_settings.cached_auto_width
                override_settings.resolution_preview = auto_width

                row = col.row(align=True)
                row.enabled = False
                row.prop(override_settings, "resolution_preview", text="Auto-X")
                row.menu("RECOM_MT_resolution_x", text="", icon="DOWNARROW_HLT")

                row = col.row(align=True)
                row.prop(override_settings, "resolution_y", text="Y")
                row.menu("RECOM_MT_resolution_y", text="", icon="DOWNARROW_HLT")
            else:
                row = col.row(align=True)
                row.prop(override_settings, "resolution_x", text="X")
                row.menu("RECOM_MT_resolution_x", text="", icon="DOWNARROW_HLT")

                row = col.row(align=True)
                row.prop(override_settings, "resolution_y", text="Y")
                row.menu("RECOM_MT_resolution_y", text="", icon="DOWNARROW_HLT")

        # Scale resolution menu
        col = layout.column()

        row = col.row(align=True)
        row.prop(override_settings, "custom_render_scale", text="%", slider=True)
        row.menu("RECOM_MT_custom_render_scale", text="", icon="DOWNARROW_HLT")

        # Scaled result
        show_scale = override_settings.custom_render_scale != 100

        if show_scale:
            # Calculate Scale
            scale_factor = override_settings.custom_render_scale / 100

            if override_settings.resolution_override:
                if override_settings.resolution_mode == "SET_HEIGHT":
                    height = override_settings.resolution_y
                    width = auto_width
                elif override_settings.resolution_mode == "SET_WIDTH":
                    width = override_settings.resolution_x
                    height = auto_height
                else:
                    width = override_settings.resolution_x
                    height = override_settings.resolution_y
            else:
                resolution = get_default_resolution(context)
                width = resolution[0]
                height = resolution[1]

            scaled_width = int(round(width * scale_factor / 2) * 2)
            scaled_height = int(round(height * scale_factor / 2) * 2)

            # Draw Preview
            draw_label_value_box(layout, "Scaled", f"{scaled_width} x {scaled_height} px")


class RECOM_PT_overscan_settings(RCBasePanel, Panel):
    bl_label = "Overscan"
    bl_parent_id = "RECOM_PT_scene_override_settings"

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.use_overscan

    def draw_header_preset(self, context):
        layout = self.layout
        op = layout.operator("recom.manage_override", text="", icon="PANEL_CLOSE", emboss=False)
        op.action = "REMOVE"
        op.override_id = "overscan"
        layout.separator(factor=0.25)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        override_settings = get_override_settings(context)
        layout.active = override_settings.use_overscan

        col = layout.column()
        col.use_property_split = True
        col.use_property_decorate = False
        row = col.row()
        row.prop(override_settings, "overscan_type", text="Type", expand=True)

        if override_settings.overscan_type == "PIXELS":
            col = col.column()
            col.prop(override_settings, "overscan_uniform", text="Uniform")
            if override_settings.overscan_uniform:
                col.prop(override_settings, "overscan_width", text="Pixels")
            else:
                col = col.column(align=True)
                col.prop(override_settings, "overscan_width", text="X")
                col.prop(override_settings, "overscan_height", text="Y")
        else:  # PERCENTAGE
            col = col.column()
            col.prop(override_settings, "overscan_uniform", text="Uniform")
            if override_settings.overscan_uniform:
                col.prop(override_settings, "overscan_percent", text="%", slider=True)
            else:
                col = col.column(align=True)
                col.prop(override_settings, "overscan_percent_width", text="X", slider=True)
                col.prop(override_settings, "overscan_percent_height", text="Y", slider=True)


class RECOM_PT_output_path_settings(RCBasePanel, Panel):
    bl_label = "Output Path"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 4

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.output_path_override

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
        layout.use_property_split = True
        layout.use_property_decorate = False
        override_settings = get_override_settings(context)

        col = layout.column(align=True)
        col.prop(override_settings, "output_directory", text="", placeholder="Directory")
        row = col.row(align=True)
        row.prop(override_settings, "output_filename", text="", placeholder="Filename")
        row.popover(panel="RECOM_PT_path_variables", text="", icon="TAG")


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


class RECOM_PT_path_variables(Panel):
    bl_label = "Path Variables"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 12

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        override_settings = get_override_settings(context)
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
            self.draw_section(context, flow.column(), "Path Templates", PATH_VARIABLES_DATA["data"])

        # Draw Custom Variables section
        if has_custom:
            col = flow.column(align=True)
            col.label(text="Custom")
            for var in prefs.custom_variables:
                op = col.operator("recom.insert_variable", text=var.name)
                op.variable = f"{{{var.token}}}"

        layout.separator(factor=0.5)
        col = layout.column()
        col.label(text="Target")
        col.row().prop(override_settings, "variable_insert_target", expand=True)
        col.prop(prefs, "use_underscore_separator", text="Add Underscore")

        return

    def draw_section(self, context, layout, title, variables):
        col = layout.column(align=True)
        col.label(text=title)
        # col.separator()

        for token, label in variables:
            if not token:
                # col.separator()
                continue

            op = col.operator("recom.insert_variable", text=label)
            op.variable = token

        layout = self.layout
        prefs = get_addon_preferences(context)

        show_templates = bpy.app.version >= (5, 0)
        has_custom = bool(prefs.custom_variables)

        if not show_templates and not has_custom:
            layout.label(text="No variables available", icon="INFO")
            return


class RECOM_PT_output_format_settings(RCBasePanel, Panel):
    bl_label = "File Format"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 3

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.file_format_override

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

        override_settings = get_override_settings(context)

        col = layout.column()
        col.prop(override_settings, "file_format", text="File Format")

        if override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER", "PNG", "TIFF"]:
            row = col.row(align=True)
            row.prop(override_settings, "color_depth", text="Color Depth", expand=True)

        if override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
            col.prop(override_settings, "codec", text="Codec")
            col.prop(override_settings, "use_preview", text="Preview")

        if override_settings.file_format == "JPEG":
            col.prop(override_settings, "jpeg_quality", text="Quality", slider=True)


class RECOM_PT_camera_settings(RCBasePanel, Panel):
    bl_label = "Camera"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.cameras_override

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

        override_settings = get_override_settings(context)

        row = layout.row(heading="Depth of Field")
        row.prop(override_settings, "override_dof", text="")
        sub = row.row(align=True)
        sub.active = override_settings.override_dof
        sub.prop(override_settings, "use_dof", text="", expand=False)

        col = layout.column(align=True)
        col.prop(override_settings, "camera_shift_x", text="Shift X", slider=True)
        col.prop(override_settings, "camera_shift_y", text="Y", slider=True)


class RECOM_PT_compositor_settings(RCBasePanel, Panel):
    bl_label = "Compositing"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 5

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.compositor_override

    def draw_header(self, context):
        override_settings = get_override_settings(context)
        self.layout.prop(override_settings, "use_compositor", text="")

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
        override_settings = get_override_settings(context)
        layout.active = override_settings.use_compositor

        layout.prop(override_settings, "compositor_disable_output_files", text="Bypass File Outputs")
        layout.prop(override_settings, "compositor_device", text="Device", expand=True)


class RECOM_UL_data_path_overrides(UIList):
    def draw_item(
        self,
        context,
        layout,
        data,
        item,
        icon,
        active_data,
        active_propname,
        index,
        flt_flag,
    ):
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


class RECOM_PT_data_path_settings(RCBasePanel, Panel):
    bl_label = "Custom Properties"
    bl_parent_id = "RECOM_PT_scene_override_settings"
    bl_order = 6

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.use_data_path_overrides

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
        override_settings = get_override_settings(context)

        row = layout.row()
        row.prop(
            override_settings,
            "property_path_input",
            text="",
            icon="VIEWZOOM",
            placeholder="Data Path",
        )

        col = layout.column()
        row = col.row()

        # Variable list
        list_col = row.column(align=True)
        list_col.template_list(
            "RECOM_UL_data_path_overrides",
            "",
            override_settings,
            "data_path_overrides",
            override_settings,
            "active_data_path_index",
            rows=3,
        )

        # Controls
        col = row.column()
        add_remove_col = col.column(align=True)
        add_remove_col.operator("recom.add_advanced_property_override", text="", icon="ADD")
        add_remove_col.operator("recom.remove_advanced_property_override", text="", icon="REMOVE")


class RECOM_PT_data_path_properties(RCBasePanel, Panel):
    bl_label = "Property Details"
    bl_parent_id = "RECOM_PT_data_path_settings"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        override_settings = get_override_settings(context)
        return override_settings.active_data_path_index >= 0 and override_settings.data_path_overrides

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        override_settings = get_override_settings(context)
        item = override_settings.data_path_overrides[override_settings.active_data_path_index]

        layout.enabled = False

        col = layout.column(align=True)
        col.prop(item, "data_path", text="")

        col = layout.column(align=True)
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
    RECOM_PT_fps_converter_settings,
    RECOM_PT_resolution_presets,
    RECOM_PT_resolution_settings,
    RECOM_PT_overscan_settings,
    RECOM_PT_output_presets,
    RECOM_PT_output_path_settings,
    RECOM_PT_path_variables,
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
