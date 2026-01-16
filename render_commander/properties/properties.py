# ./properties/properties.py

import logging
import re
from pathlib import Path

import bpy
from bpy.props import (
    StringProperty,
    BoolProperty,
    PointerProperty,
    CollectionProperty,
    IntProperty,
    EnumProperty,
    FloatProperty,
)
from bpy.types import PropertyGroup

from .override_settings import RECOM_PG_OverrideSettings
from ..utils.helpers import (
    redraw_ui,
    is_blender_blend_file,
)

log = logging.getLogger(__name__)


class RECOM_PG_RenderSettings(PropertyGroup):
    """Stores render configuration settings"""

    # Frame List
    def _sanitize_frame_list(self, context):
        """Sanitize the frame_list to allow digits, commas, hyphens, and spaces,
        and normalize spaces into commas with consistent formatting."""

        value = self.frame_list
        cleaned = "".join(c for c in value if c.isdigit() or c in ",- ")
        cleaned = re.sub(r"\s*-\s*", "-", cleaned)
        cleaned = re.sub(r"\s+", ",", cleaned)
        cleaned = re.sub(r",+", ",", cleaned)
        cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
        cleaned = cleaned.strip(", ")

        if cleaned != value:
            self.frame_list = cleaned
            log.debug(f"Sanitized frame list: Original: '{value}', Cleaned: '{cleaned}'")

    frame_list: StringProperty(
        name="Frame List",
        description="Frame numbers or ranges separated by commas.\nExample: 1, 2, 5-8",
        default="",
        update=_sanitize_frame_list,
    )

    def _check_external_blend_file_path(self, context):
        ext_blend_file = self.external_blend_file_path
        if ext_blend_file:
            if not is_blender_blend_file(ext_blend_file):
                log.warning(f"External Blend File - Invalid or non-Blender file: {ext_blend_file}")

    # External Scene
    use_external_blend: BoolProperty(
        name="Use External Blend File",
        default=False,
        description="Render external blend file instead of current scene.",
        update=lambda self, context: redraw_ui(),
    )
    external_blend_file_path: StringProperty(
        name="External Blend File",
        # subtype="FILE_PATH",
        default="",
        description="Path to an external blend file for rendering",
        update=_check_external_blend_file_path,
    )
    external_scene_info: StringProperty(
        name="External Scene Info",
        default="{}",
        description="Stores scene info from external blend file",
    )
    is_scene_info_loaded: BoolProperty(
        name="Scene Info Loaded",
        default=True,
        description="Indicates if external scene info is loaded",
    )

    # Override Settings
    use_override_settings: BoolProperty(
        name="Use Override Settings",
        default=False,
        description="Apply custom render settings overrides.",
    )
    override_settings: PointerProperty(type=RECOM_PG_OverrideSettings)

    # Misc
    render_id: StringProperty(
        name="Render ID",
        default="",
        description="Stores a render id",
    )
    render_output_folder_path: StringProperty(
        name="Render Output Folder",
        default="",
        description="Stores the final render output folder",
    )
    render_output_filename: StringProperty(
        name="Render Output Filename",
        default="",
        description="Stores the final render output filename",
    )
    folder_opened: BoolProperty(
        name="Folder Opened",
        description="Whether the output folder has been opened",
        default=False,
    )
    disable_render_button: BoolProperty(
        name="Disable Render Button",
        description="Internal flag to disable the render button.",
        default=False,
    )


def get_custom_tooltip(self):
    return f"{self.key}: {self.value}"


class RECOM_PG_ExternalSceneInfoItem(PropertyGroup):
    """Container for a single key/value pair extracted from the external scene JSON."""

    key: StringProperty(name="Key")
    value: StringProperty(name="Value")
    tooltip_display: StringProperty(get=get_custom_tooltip)


classes = (
    RECOM_PG_RenderSettings,
    RECOM_PG_ExternalSceneInfoItem,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    try:
        wm = bpy.types.WindowManager
        wm.recom_render_settings = PointerProperty(type=RECOM_PG_RenderSettings)
        wm.recom_external_scene_info_items = CollectionProperty(
            type=RECOM_PG_ExternalSceneInfoItem,
        )
        wm.recom_external_scene_info_active = IntProperty(name="Active Index")

    except Exception as e:
        log.error("Failed to register custom properties", exc_info=True)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    try:
        wm = bpy.types.WindowManager
        del wm.recom_external_scene_info_active
        del wm.recom_external_scene_info_items
        del wm.recom_render_settings

    except Exception as e:
        log.error("Failed to unregister custom properties", exc_info=True)
