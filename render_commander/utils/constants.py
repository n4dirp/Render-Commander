# ./utils/constants.py

from pathlib import Path

import bpy
import tomllib


def get_extension_version() -> str:
    """Get extension version as a string from blender_manifest.toml"""
    manifest_path = Path(__file__).parent.parent / "blender_manifest.toml"
    if manifest_path.exists():
        try:
            with open(manifest_path, "rb") as f:
                manifest_data = tomllib.load(f)
                return manifest_data.get("version", "0.0.0")
        except Exception as e:
            print(f"Failed to read extension version: {e}")
    return "0.0.0"


# General
BLENDER_VERSION_STR = bpy.app.version_string
ADDON_VERSION_STR = get_extension_version()
EXTERNAL_BLEND_FILE_HISTORY_LIMIT = 30
RENDER_HISTORY_LIMIT = 30

# Render Engines
RE_CYCLES = "CYCLES"
RE_EEVEE = "BLENDER_EEVEE"
RE_EEVEE_NEXT = "BLENDER_EEVEE_NEXT"
RE_WORKBENCH = "BLENDER_WORKBENCH"

RENDER_ENGINE_MAPPING = {
    RE_CYCLES: "Cycles",
    RE_EEVEE: "EEVEE",
    RE_EEVEE_NEXT: "EEVEE",
    RE_WORKBENCH: "Workbench",
}

# Render Modes
MODE_SINGLE = "SINGLE_FRAME"
MODE_SEQ = "SEQUENCE"
MODE_LIST = "FRAME_LIST"

# Panel Location
PANEL_LOCATION_VIEWPORT = "VIEWPORT"
PANEL_LOCATION_RENDER = "RENDER_PROPERTIES"
PANEL_LOCATION_OUTPUT = "OUTPUT_PROPERTIES"
PANEL_CATEGORY = "Render Commander"
PANEL_ROOT_ID = "RECOM_PT_main_panel"
RENDER_TAB_CONTEXT = "render"
OUTPUT_TAB_CONTEXT = "output"

# Path Templates
RESERVED_TOKENS = {
    "blend_dir",
    "blend_name",
    "blend_name_lib",
    "blend_dir_lib",
    "fps",
    "resolution_x",
    "resolution_y",
    "scene_name",
    "camera_name",
}

# Regex patterns for template processing
RENDER_TEMPLATE_PATTERN = r"\{[^}]*\}"


class RCBasePanel:
    """Mix-in to standardize layout metadata across all Render Commander panels"""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Render Commander"


class RCSubPanel(RCBasePanel):
    """Mix-in for sub-panels to standardize layout metadata and allow dynamic parent assignment"""

    bl_parent_id = "RECOM_PT_main_panel"


def _drop_attr(cls, name):
    """Delete a class attribute that was injected by a previous location."""
    if name in cls.__dict__:
        delattr(cls, name)


def apply_panel_location(cls, location):
    """Set the panel class layout attributes for the requested location.

    Blender reads ``bl_space_type``/``bl_region_type``/``bl_parent_id``/``bl_context``/
    ``bl_category`` at registration time, so this is called right before ``register_class``
    and again whenever the user changes the ``panel_location`` preference.

    Both the Render and Output Properties tabs are entered through a ``bl_context`` root
    panel (the native Blender 5.x pattern, e.g. ``RenderButtonsPanel``), which keeps the
    root panel header visible. Parenting to a built-in context panel would inherit its
    ``HIDE_HEADER`` state.
    """
    if location == PANEL_LOCATION_VIEWPORT:
        cls.bl_space_type = "VIEW_3D"
        cls.bl_region_type = "UI"
        cls.bl_category = PANEL_CATEGORY
        _drop_attr(cls, "bl_context")
        if cls.__name__ == PANEL_ROOT_ID:
            _drop_attr(cls, "bl_parent_id")
        return

    cls.bl_space_type = "PROPERTIES"
    cls.bl_region_type = "WINDOW"
    _drop_attr(cls, "bl_category")
    if cls.__name__ != PANEL_ROOT_ID:
        return

    if location == PANEL_LOCATION_RENDER:
        cls.bl_context = RENDER_TAB_CONTEXT
    elif location == PANEL_LOCATION_OUTPUT:
        cls.bl_context = OUTPUT_TAB_CONTEXT
    _drop_attr(cls, "bl_parent_id")
