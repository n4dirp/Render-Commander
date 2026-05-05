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
