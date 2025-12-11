# ./properties/__init__.py

import logging

import bpy
from . import override_settings
from . import properties

utils_modules = [
    override_settings,
    properties,
]


def register():
    for mdl in utils_modules:
        try:
            mdl.register()
        except Exception as e:
            logging.error(f"Failed to register module {mdl.__name__}", exc_info=True)


def unregister():
    for mdl in reversed(utils_modules):
        try:
            mdl.unregister()
        except Exception as e:
            logging.error(f"Failed to unregister module {mdl.__name__}", exc_info=True)
