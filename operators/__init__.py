# ./operators/__init__.py

import logging

import bpy

from .render import background_render
from . import (
    external_scene,
    operators,
    import_settings,
    override_output_path,
    override_settings,
    presets_settings,
    custom_path_variables,
    blender_executable,
    append_scripts,
    render_history,
)

log = logging.getLogger(__name__)

operator_modules = [
    background_render,
    external_scene,
    operators,
    import_settings,
    override_output_path,
    override_settings,
    presets_settings,
    custom_path_variables,
    blender_executable,
    append_scripts,
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
