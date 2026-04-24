# ./utils/constants.py

import tomllib
from pathlib import Path

import bpy

from .. import __package__ as base_package


def get_addon_name() -> str:
    """Get the name of the addon."""
    return base_package


def get_extension_version() -> str:
    """
    Reads the blender_manifest.toml located one level above this helper file
    to get the extension version as a string.
    """

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
ADDON_NAME = get_addon_name()
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

# UI
ICON_OPTION = "DOWNARROW_HLT"
ICON_MENU = "COLLAPSEMENU"
ICON_SYNC = "IMPORT"


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
