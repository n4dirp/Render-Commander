import logging

from . import (
    background_render,
    presets,
    blend_file,
    operators,
    override_settings,
    override_import_settings,
    render_history,
)

log = logging.getLogger(__name__)

operator_modules = [
    presets,
    background_render,
    blend_file,
    operators,
    override_settings,
    override_import_settings,
    render_history,
]


def register():
    for mdl in operator_modules:
        try:
            mdl.register()
        except Exception:
            log.error("Failed to register module %s", mdl.__name__, exc_info=True)


def unregister():
    for mdl in reversed(operator_modules):
        try:
            mdl.unregister()
        except Exception:
            log.error("Failed to unregister module %s", mdl.__name__, exc_info=True)
