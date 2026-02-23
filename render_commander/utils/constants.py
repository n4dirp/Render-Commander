# ./utils/constants.py

from .. import __package__ as base_package


def get_addon_name() -> str:
    """Get the name of the addon."""
    return base_package


# General
ADDON_NAME = get_addon_name()
CENTER_TEXT = ""  # "      "
OPEN_FOLDER_DELAY = 0.3
EXTERNAL_BLEND_FILE_HISTORY_LIMIT = 30
RENDER_HISTORY_LIMIT = 30

# Paths
EXPORT_SCRIPTS_FOLDER_NAME = "render_scripts"
RENDER_LOGS_FOLDER_NAME = "logs"

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
ICON_COLLAPSED = "DISCLOSURE_TRI_DOWN"
ICON_EXPANDED = "DISCLOSURE_TRI_RIGHT"
ICON_OPTION = "DOWNARROW_HLT"
ICON_SYNC = "IMPORT"
