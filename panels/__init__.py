# ./panels/__init__.py

import logging

import bpy
from . import (
    cycles_setup_panel,
    main_panel,
    external_scene_panel,
    override_settings_panel,
    override_cycles_panel,
    override_eevee_panel,
    preferences_panel,
    history_panel,
)

log = logging.getLogger(__name__)

ui_modules = [
    cycles_setup_panel,
    main_panel,
    external_scene_panel,
    override_settings_panel,
    override_cycles_panel,
    override_eevee_panel,
    preferences_panel,
    history_panel,
]


def register():
    for mdl in ui_modules:
        try:
            mdl.register()
        except Exception as e:
            log.error(f"Failed to register module {mdl.__name__}", exc_info=True)


def unregister():
    for mdl in reversed(ui_modules):
        try:
            mdl.unregister()
        except Exception as e:
            log.error(f"Failed to unregister module {mdl.__name__}", exc_info=True)
