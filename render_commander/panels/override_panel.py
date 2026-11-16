# ./panels/override_panel.py


import logging

import bpy
from bl_ui.utils import PresetPanel
from bpy.types import Menu, Operator, Panel, UIList

from ..operators.presets import PRESET_REGISTRY
from ..preferences import RECOM_PT_custom_variables_presets
from ..utils.constants import (
    MODE_LIST,
    MODE_SEQ,
    MODE_SINGLE,
    RE_CYCLES,
    RE_EEVEE,
    RE_EEVEE_NEXT,
    RCSubPanel,
)
from ..utils.helpers import (
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
        "overscan": ("Resolution Overscan", "use_overscan", "FULLSCREEN_ENTER"),
        "frame_range": ("Frame Range", "frame_range_override", "PREVIEW_RANGE"),
        "file_format": ("File Format", "file_format_override", "FILE_IMAGE"),
        "output_path": ("Output Path", "output_path_override", "FILE_FOLDER"),
    },
    "Data": {
        "camera_settings": ("Camera", "cameras_override", "OUTLINER_DATA_CAMERA"),
        "compositor": ("Compositing", "compositor_override", "NODE_COMPOSITING"),
        "fps_converter": ("FPS Converter", "use_fps_converter", "FILE_REFRESH"),
        "custom_api": ("Advanced", "use_data_path_overrides", "PROPERTIES"),
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


def count_active_overrides(settings):
    """Returns the number of overrides that are currently active."""
    return sum(1 for _, _, prop_path, _ in iterate_all_overrides() if is_override_active(settings, prop_path))


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

        if is_active:
            override_settings.enabled = True

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
            "enabled",
            "box_state",
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


#  Override Boxes
#################################################


def _header_denoising_toggle(header, context):
    override_settings = get_override_settings(context)
    toggle = header.row(align=True)
    toggle.active = override_settings.enabled
    toggle.prop(override_settings.cycles, "use_denoising", text="")


def _header_motion_blur_toggle(header, context):
    override_settings = get_override_settings(context)
    toggle = header.row(align=True)
    toggle.active = override_settings.enabled
    toggle.prop(override_settings, "use_motion_blur", text="")


def _header_compositor_toggle(header, context):
    override_settings = get_override_settings(context)
    toggle = header.row(align=True)
    toggle.active = override_settings.enabled
    toggle.prop(override_settings, "use_compositor", text="")


def _draw_cycles_device(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled
    row = layout.row()
    row.prop(override_settings.cycles, "device", text="Type", expand=True)


def _draw_cycles_sampling(layout, context):
    override_settings = get_override_settings(context)

    render_engine = get_render_engine(context)
    layout.active = override_settings.enabled and render_engine == RE_CYCLES

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


def _draw_cycles_denoising(layout, context):
    override_settings = get_override_settings(context)

    render_engine = get_render_engine(context)
    layout.active = override_settings.enabled and override_settings.cycles.use_denoising and render_engine == RE_CYCLES

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


def _draw_cycles_performance(layout, context):
    render_engine = get_render_engine(context)
    override_settings = get_override_settings(context)
    layout.active = override_settings.enabled and render_engine == RE_CYCLES

    col = layout.column(heading="")
    col.prop(override_settings.cycles, "use_tiling", text="Tiling")
    row = col.row()
    row.active = override_settings.cycles.use_tiling
    row.prop(override_settings.cycles, "tile_size")
    row.menu("RECOM_MT_tile_size", text="", icon="DOWNARROW_HLT")

    col = layout.column(heading="Animation")
    col.prop(override_settings.cycles, "persistent_data")


def _draw_eevee(layout, context):
    render_engine = get_render_engine(context)
    override_settings = get_override_settings(context)
    layout.active = override_settings.enabled and render_engine in {RE_EEVEE_NEXT, RE_EEVEE}

    col = layout.column(align=True)
    col.prop(override_settings.eevee, "samples", text="Samples")


def _draw_motion_blur(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

    col = layout.column()
    col.active = override_settings.use_motion_blur
    col.prop(override_settings, "motion_blur_position", text="Position")
    col.prop(override_settings, "motion_blur_shutter", text="Shutter", slider=True)


def _draw_render_resolution(layout, context, override_settings, auto_width, auto_height):
    """Draw calculated render resolution"""
    show_scale = override_settings.custom_render_scale != 100
    if not show_scale:
        return

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
    layout.label(text=f"Render Resolution: {scaled_width} x {scaled_height} px")


def _draw_resolution(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

    col = layout.column()

    row = col.row(heading="Mode")
    row.prop(override_settings, "resolution_override", text="")
    sub = row.row()
    sub.active = override_settings.resolution_override
    sub_row = sub.row(align=True)
    sub_row.prop(override_settings, "resolution_mode", text="")
    if override_settings.resolution_mode == "CUSTOM":
        sub_row.operator("recom.swap_resolution", text="", icon="ARROW_LEFTRIGHT")

    auto_width, auto_height = 0, 0

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

    _draw_render_resolution(layout, context, override_settings, auto_width, auto_height)


def _draw_overscan(layout, context):
    override_settings = get_override_settings(context)
    layout.active = override_settings.enabled and override_settings.use_overscan

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


def _draw_frame_range(layout, context):
    override_settings = get_override_settings(context)
    prefs = get_addon_preferences(context)

    layout.active = override_settings.enabled and prefs.launch_mode != MODE_LIST

    if prefs.launch_mode != MODE_SEQ:
        row = layout.row(align=True)
        row.prop(override_settings, "frame_current", text="Current Frame")

    if prefs.launch_mode != MODE_SINGLE:
        col = layout.column(align=True)
        col.prop(override_settings, "frame_start", text="Frame Start")
        col.prop(override_settings, "frame_end", text="End")
        col.prop(override_settings, "frame_step", text="Step")


def _draw_fps_converter(layout, context):
    override_settings = get_override_settings(context)
    layout.active = override_settings.enabled and override_settings.use_fps_converter

    col = layout.column()
    col.prop(override_settings, "target_fps", text="Target")
    if override_settings.target_fps == "CUSTOM":
        col.prop(override_settings, "custom_fps", text="Value")
    col.prop(override_settings, "preserve_motion_blur", text="Preserve Motion Blur")


def _draw_output_path(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

    col = layout.column(align=False)
    col.prop(override_settings, "output_directory", text="Directory", placeholder="Directory")
    row = col.row(align=False)
    row.prop(override_settings, "output_filename", text="Filename", placeholder="Filename")
    row.popover(panel="RECOM_PT_path_variables", text="", icon="TAG")


def _draw_output_format(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

    col = layout.column()
    col.prop(override_settings, "file_format", text="File Format")

    if override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER", "PNG", "TIFF"]:
        row = col.row(align=True)
        row.prop(override_settings, "color_depth", text="Color Depth", expand=True)

    if override_settings.file_format in ["OPEN_EXR", "OPEN_EXR_MULTILAYER"]:
        col.prop(override_settings, "codec", text="Codec")
        col.prop(override_settings, "use_preview", text="Preview")

    if override_settings.file_format in ["JPEG", "WEBP"]:
        col.prop(override_settings, "quality", text="Quality", slider=True)


def _draw_camera(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

    row = layout.row(heading="Depth of Field")
    row.prop(override_settings, "override_dof", text="")
    sub = row.row(align=True)
    sub.active = override_settings.override_dof
    sub.prop(override_settings, "use_dof", text="", expand=False)

    col = layout.column(align=True)
    col.prop(override_settings, "camera_shift_x", text="Shift X", slider=True)
    col.prop(override_settings, "camera_shift_y", text="Y", slider=True)


def _draw_compositor(layout, context):
    override_settings = get_override_settings(context)
    layout.active = override_settings.enabled and override_settings.use_compositor

    layout.prop(override_settings, "compositor_disable_output_files", text="Bypass File Outputs")
    layout.prop(override_settings, "compositor_device", text="Device", expand=True)


def _draw_data_path_properties(layout, override_settings):
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


def _draw_data_path(layout, context):
    override_settings = get_override_settings(context)

    layout.active = override_settings.enabled

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

    active_index = override_settings.active_data_path_index
    if override_settings.data_path_overrides and 0 <= active_index < len(override_settings.data_path_overrides):
        box_state = override_settings.box_state
        details_open = box_state.custom_api_details

        toggle = layout.row(align=True)
        toggle.prop(
            box_state,
            "custom_api_details",
            text="Property Details",
            icon="DOWNARROW_HLT" if details_open else "RIGHTARROW",
            emboss=False,
        )

        if details_open:
            sub_body = layout.column()
            sub_body.use_property_split = True
            sub_body.use_property_decorate = False
            _draw_data_path_properties(sub_body, override_settings)


# Override ID -> body drawer
OVERRIDE_BODY_DRAWERS = {
    "cycles_device": _draw_cycles_device,
    "cycles_sampling": _draw_cycles_sampling,
    "cycles_denoising": _draw_cycles_denoising,
    "cycles_performance": _draw_cycles_performance,
    "eevee_all": _draw_eevee,
    "motion_blur": _draw_motion_blur,
    "resolution": _draw_resolution,
    "overscan": _draw_overscan,
    "frame_range": _draw_frame_range,
    "file_format": _draw_output_format,
    "output_path": _draw_output_path,
    "camera_settings": _draw_camera,
    "compositor": _draw_compositor,
    "fps_converter": _draw_fps_converter,
    "custom_api": _draw_data_path,
}

# Override ID -> extra header controls (drawn between the collapse arrow and the label)
OVERRIDE_HEADER_EXTRAS = {
    "cycles_denoising": _header_denoising_toggle,
    "motion_blur": _header_motion_blur_toggle,
    "compositor": _header_compositor_toggle,
}

# Override ID -> preset panel shown in the box header
OVERRIDE_PRESETS = {
    "cycles_sampling": RECOM_PT_samples_presets,
    "resolution": RECOM_PT_resolution_presets,
    "output_path": RECOM_PT_output_presets,
    "custom_api": RECOM_PT_override_advanced_property_presets,
}


def draw_override_box(layout, context, override_id, label, icon):
    """Draw a single override as a collapsible, modifier-style box."""
    override_settings = get_override_settings(context)
    box_state = override_settings.box_state
    expanded = getattr(box_state, override_id)

    box = layout.box()

    # Header. Split with a fixed factor so the title and the right hand buttons
    # always stay inside the box, however narrow the region is.
    header = box.row(align=True)
    split = header.split(factor=0.68, align=True)

    left = split.row(align=True)
    left.prop(
        box_state,
        override_id,
        text="",
        icon="DOWNARROW_HLT" if expanded else "RIGHTARROW",
        emboss=False,
    )

    header_extra = OVERRIDE_HEADER_EXTRAS.get(override_id)
    if header_extra:
        header_extra(left, context)

    if icon and icon != "BLANK1":
        left.label(text=label, icon=icon)
    else:
        left.label(text=label)

    right = split.row(align=True)
    right.alignment = "RIGHT"
    right.emboss = "NONE"

    preset_panel = OVERRIDE_PRESETS.get(override_id)
    if preset_panel:
        preset_panel.draw_panel_header(right)
        # draw_panel_header() mutates the emboss state, keep it flat for the X button.
        right.emboss = "NONE"

    op = right.operator("recom.manage_override", text="", icon="X", emboss=False)
    op.action = "REMOVE"
    op.override_id = override_id

    if not expanded:
        return

    body = box.column()
    body.use_property_split = True
    body.use_property_decorate = False

    OVERRIDE_BODY_DRAWERS[override_id](body, context)


#  Panels
#################################################


class RECOM_PT_scene_override_settings(RCSubPanel, Panel):
    """Main scene overrides panel"""

    bl_label = ""
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        prefs = get_addon_preferences(context)
        return prefs.visible_panels.override_settings

    def draw_header(self, context):
        layout = self.layout
        override_settings = get_override_settings(context)
        override_count = count_active_overrides(override_settings)
        text = f"Overrides ({override_count})" if override_count > 0 else "Overrides"

        layout.prop(override_settings, "enabled", text=text)

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = "PULLDOWN_MENU"
        row = layout.row(align=True)
        RECOM_PT_overrides_presets.draw_panel_header(row)

    def draw(self, context):
        layout = self.layout
        override_settings = get_override_settings(context)

        row = layout.row(align=True)
        row.active = override_settings.enabled
        row.menu("RECOM_MT_add_override_menu", text="Add Override", icon="ADD")
        row.popover(panel="RECOM_PT_import_overrides_popup", text="", icon="IMPORT")

        has_active_overrides = count_active_overrides(override_settings) > 0
        if has_active_overrides:
            row.operator("recom.remove_all_overrides", text="", icon="TRASH")

        col = layout.column()
        col.active = override_settings.enabled
        for override_id, label, prop_path, icon in iterate_all_overrides():
            if not is_override_active(override_settings, prop_path):
                continue
            draw_override_box(col, context, override_id, label, icon)


class RECOM_PT_import_overrides_popup(Panel):
    bl_label = "Import from Scene"
    bl_description = "Add overrides and populate with scene values"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        render_engine = get_render_engine(context)

        layout.label(text="Import from Scene")

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
        layout.operator("recom.import_all_settings", text="Import Settings", icon="IMPORT")


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


# Popup Panel
class RECOM_PT_path_variables(Panel):
    bl_label = "Path Variables"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 13

    def draw(self, context):
        layout = self.layout
        prefs = get_addon_preferences(context)
        override_settings = get_override_settings(context)
        show_templates = bpy.app.version >= (5, 0)
        has_custom = bool(prefs.custom_variables)

        col = layout.column()
        col.label(text="Target")
        col.row().prop(override_settings, "variable_insert_target", expand=True)
        col.prop(prefs, "use_underscore_separator", text="Add Underscore")
        layout.separator(factor=0.5)

        if not show_templates and not has_custom:
            layout.label(text="No variables available", icon="INFO")
        else:
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

        header, sub_body = layout.panel("RECOM_PT_custom_variables", default_closed=True)
        header.label(text="Custom Variables")
        RECOM_PT_custom_variables_presets.draw_panel_header(header)
        if sub_body:
            col = sub_body.column()
            row = col.row()
            show_op = len(prefs.custom_variables)

            # Variable list
            list_col = row.column()
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
            col = row.column()
            add_remove_col = col.column(align=True)
            add_remove_col.operator("recom.add_custom_variable", text="", icon="ADD")
            has_selection = bool(
                prefs.custom_variables and prefs.active_custom_variable_index < len(prefs.custom_variables)
            )
            remove_col = add_remove_col.column(align=True)
            remove_col.active = has_selection
            remove_col.operator("recom.remove_custom_variable", text="", icon="REMOVE")
            col.separator(factor=0.5)

            if show_op:
                # Move buttons
                move_col = col.column(align=True)
                move_col.active = has_selection and len(prefs.custom_variables) > 1
                move_col.operator("recom.move_custom_variable", text="", icon="TRIA_UP").direction = "UP"
                move_col.operator("recom.move_custom_variable", text="", icon="TRIA_DOWN").direction = "DOWN"

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


classes = (
    RECOM_OT_manage_override,
    RECOM_OT_remove_all_overrides,
    RECOM_OT_reset_overrides,
    RECOM_MT_add_override_menu,
    RECOM_PT_import_overrides_popup,
    RECOM_PT_overrides_presets,
    RECOM_PT_scene_override_settings,
    RECOM_PT_samples_presets,
    RECOM_PT_resolution_presets,
    RECOM_PT_output_presets,
    RECOM_PT_override_advanced_property_presets,
    RECOM_PT_path_variables,
    RECOM_UL_data_path_overrides,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
