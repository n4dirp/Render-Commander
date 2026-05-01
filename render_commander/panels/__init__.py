import logging

from . import (
    blend_file_panel,
    history_panel,
    launcher_panel,
    override_panel,
    settings_panel,
)

log = logging.getLogger(__name__)

ui_modules = [
    launcher_panel,
    blend_file_panel,
    override_panel,
    settings_panel,
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
