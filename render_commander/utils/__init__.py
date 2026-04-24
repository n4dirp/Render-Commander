import logging

from . import menus

log = logging.getLogger(__name__)

utils_modules = [menus]


def register():
    for mdl in utils_modules:
        try:
            mdl.register()
        except Exception:
            log.error("Failed to register module %s", mdl.__name__, exc_info=True)


def unregister():
    for mdl in reversed(utils_modules):
        try:
            mdl.unregister()
        except Exception:
            log.error("Failed to unregister module %s", mdl.__name__, exc_info=True)
