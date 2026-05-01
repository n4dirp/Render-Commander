import logging

from . import (
    blend_file,
    export,
    history,
    import_settings,
    override,
    presets,
    utils,
)

log = logging.getLogger(__name__)

operator_modules = [
    presets,
    export,
    blend_file,
    utils,
    override,
    import_settings,
    history,
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
