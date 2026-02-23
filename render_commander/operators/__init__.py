# ./operators/__init__.py

import logging

import bpy

from .render import background_render
from . import (
    presets,
    blend_file,
    operators,
    scene_overrides,
    override_output_path,
    override_import_settings,
    blender_executable,
    python_scripts,
    render_history,
)

log = logging.getLogger(__name__)

operator_modules = [
    presets,
    background_render,
    blend_file,
    operators,
    scene_overrides,
    override_output_path,
    override_import_settings,
    blender_executable,
    python_scripts,
    render_history,
]


def register():
    for mdl in operator_modules:
        try:
            mdl.register()
        except Exception as e:
            log.error(f"Failed to register module {mdl.__name__}", exc_info=True)


def unregister():
    for mdl in reversed(operator_modules):
        try:
            mdl.unregister()
        except Exception as e:
            log.error(f"Failed to unregister module {mdl.__name__}", exc_info=True)
