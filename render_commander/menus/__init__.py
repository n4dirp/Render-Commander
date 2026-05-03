import logging

from . import menus, override_menus

log = logging.getLogger(__name__)

menu_modules = [
    menus,
    override_menus,
]


def register():
    for mdl in menu_modules:
        try:
            mdl.register()
        except Exception:
            log.error("Failed to register module %s", mdl.__name__, exc_info=True)


def unregister():
    for mdl in reversed(menu_modules):
        try:
            mdl.unregister()
        except Exception:
            log.error("Failed to unregister module %s", mdl.__name__, exc_info=True)
