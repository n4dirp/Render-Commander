# ./__init__.py

bl_info = {
    "name": "Render Commander",
    "author": "Nadir Perazzo",
    "description": "Background render launcher for Cycles & EEVEE",
    "version": (0, 9, 9),
    "blender": (4, 2, 0),
    "doc_url": "https://github.com/n4dirp/Render-Commander",
    "tracker_url": "https://github.com/n4dirp/Render-Commander",
    "category": "Render",
}

import logging
import json
import shutil
import time
from pathlib import Path

import bpy

from .utils.constants import *
from . import properties
from . import preferences
from . import utils
from . import operators
from . import panels

ADDON_NAME = __package__
logger = logging.getLogger(ADDON_NAME)


class TitleCaseFormatter(logging.Formatter):
    def format(self, record):
        record.levelname = record.levelname.title()
        return super().format(record)


class ModernBlenderFormatter(logging.Formatter):
    def __init__(self, with_level=False):
        super().__init__()
        self.start_time = time.time()
        self.with_level = with_level

    def format(self, record):
        rel_time = record.created - self.start_time
        minutes, seconds = divmod(rel_time, 60)
        timestamp = f"{int(minutes):02d}:{seconds:06.3f}"
        name = f"{record.name:<14}"

        if self.with_level:
            return f"{timestamp}  {name} | {record.levelname.title()}: {record.getMessage()}"
        else:
            return f"{timestamp}  {name} | {record.getMessage()}"


def setup_logging():
    """Sets up the addon's logger. Call this from register()."""
    # Remove any existing handlers to prevent duplicates during re-registration
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler()
    if bpy.app.version >= (5, 0, 0):
        handler.setFormatter(ModernBlenderFormatter(with_level=True))
    else:
        handler.setFormatter(TitleCaseFormatter("%(levelname)s: %(message)s"))

    logger.addHandler(handler)

    # Set a default level. This will be updated from prefs later.
    logger.setLevel(logging.INFO)


def update_logger_from_prefs():
    """Updates the logger's level based on addon preferences."""
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        level = logging.DEBUG if prefs.debug_mode else logging.INFO

        # Set the level on our specific logger, not the root logger
        logger.setLevel(level)
        # Use our logger to report the change
        # logger.debug(f"Logging level set to {logging.getLevelName(level)}")
    except (KeyError, AttributeError):
        # This can happen during initial registration before prefs are available
        # The default level set in setup_logging() will be used.
        pass


addon_modules = [
    properties,
    preferences,
    utils,
    operators,
    panels,
]


def install_default_presets():
    addon_dir = Path(__file__).parent
    source_dir = addon_dir / "presets"

    dest_base = Path(bpy.utils.user_resource("SCRIPTS")) / "presets" / __package__
    dest_base.mkdir(parents=True, exist_ok=True)

    if source_dir.exists():
        for source_path in source_dir.rglob("*.py"):
            # Calculate relative path from source_dir
            rel_path = source_path.relative_to(source_dir)
            dest_path = dest_base / rel_path

            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy if not exist or outdated
            if not dest_path.exists():
                shutil.copy2(source_path, dest_path)
            else:
                src_mtime = source_path.stat().st_mtime
                dst_mtime = dest_path.stat().st_mtime
                if src_mtime > dst_mtime:
                    shutil.copy2(source_path, dest_path)


def register():
    setup_logging()
    # logger.info("Registering Render Commander addon.")

    for mdl in addon_modules:
        try:
            mdl.register()
        except Exception as e:
            logger.error(f"Failed to register module {mdl.__name__}", exc_info=True)

    prefs = bpy.context.preferences.addons[__package__].preferences
    try:
        if not prefs.preset_installed:
            install_default_presets()
            prefs.preset_installed = True
    except Exception:
        logger.error("Failed to check or set preset_installed flag", exc_info=True)

    update_logger_from_prefs()
    # logger.info("Registration finished.")


def unregister():
    # logger.info("Unregistering Render Commander addon.")
    for mdl in reversed(addon_modules):
        try:
            mdl.unregister()
        except Exception:
            logger.error(f"Failed to unregister module {mdl.__name__}", exc_info=True)


if __name__ == "__main__":
    register()
