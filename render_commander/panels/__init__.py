import logging

from . import (
    launcher_panel,
    blend_file_panel,
    override_settings_panel,
    preferences_panel,
    history_panel,
)

log = logging.getLogger(__name__)

ui_modules = [
    launcher_panel,
    blend_file_panel,
    override_settings_panel,
    preferences_panel,
    history_panel,
]


def register():
    for mdl in ui_modules:
        try:
            mdl.register()
        except Exception:
            log.error("Failed to register module %s", mdl.__name__, exc_info=True)


def unregister():
    for mdl in reversed(ui_modules):
        try:
            mdl.unregister()
        except Exception:
            log.error("Failed to unregister module %s", mdl.__name__, exc_info=True)
