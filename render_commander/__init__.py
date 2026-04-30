# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
import time

import bpy

from . import menus, operators, panels, preferences, properties

ADDON_DIR = os.path.dirname(__file__)

log = logging.getLogger(__package__)
log.propagate = False


class AddonLogFormatter(logging.Formatter):
    """Custom formatter to provide timestamped and addon-prefixed logs."""

    def __init__(self, with_level=False):
        super().__init__()
        self.start_time = time.time()
        self.with_level = with_level

    def format(self, record):
        """Formats the log record with relative timestamps."""
        rel_time = record.created - self.start_time
        minutes, seconds = divmod(rel_time, 60)
        timestamp = f"{int(minutes):02d}:{seconds:06.3f}"
        short_name = __package__.rsplit(".", maxsplit=1)[-1]

        if self.with_level:
            return f"{timestamp}  {short_name} | {record.levelname.title()}: {record.getMessage()}"

        return f"{timestamp}  {short_name} | {record.getMessage()}"


def update_logger_from_prefs():
    """Configures the logger based on user preferences (Opt-in logging)."""
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    enable_logging = False
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        enable_logging = getattr(prefs, "debug_mode", False)
    except (KeyError, AttributeError):
        pass

    if not enable_logging:
        log.addHandler(logging.NullHandler())
        return

    handler = logging.StreamHandler()
    handler.setFormatter(AddonLogFormatter(with_level=True))

    log.addHandler(handler)
    log.setLevel(logging.DEBUG if enable_logging else logging.INFO)


addon_modules = [
    properties,
    preferences,
    operators,
    menus,
    panels,
]


def register():
    log.addHandler(logging.NullHandler())

    for mdl in addon_modules:
        try:
            mdl.register()
        except Exception as err:
            print(f"[{__package__}] Failed to register module {mdl.__name__}: {err}")

    update_logger_from_prefs()

    bpy.utils.register_preset_path(ADDON_DIR)


def unregister():
    bpy.utils.unregister_preset_path(ADDON_DIR)

    for mdl in reversed(addon_modules):
        try:
            mdl.unregister()
        except Exception as err:
            log.error(
                "[%s] Failed to unreg module %s: %s", __package__, mdl.__name__, err
            )


if __name__ == "__main__":
    register()
