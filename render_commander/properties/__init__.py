import logging

from . import override_settings, properties

log = logging.getLogger(__name__)

property_modules = [
    override_settings,
    properties,
]


def register():
    for mdl in property_modules:
        try:
            mdl.register()
        except Exception:
            log.error("Failed to register module %s", mdl.__name__, exc_info=True)


def unregister():
    for mdl in reversed(property_modules):
        try:
            mdl.unregister()
        except Exception:
            log.error("Failed to unregister module %s", mdl.__name__, exc_info=True)
