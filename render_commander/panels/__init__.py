import logging

import bpy
from bl_ui.utils import PresetPanel

from ..utils.constants import PANEL_LOCATION_VIEWPORT, RCBasePanel, apply_panel_location
from ..utils.helpers import get_addon_preferences
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


def _get_panel_location():
    try:
        prefs = get_addon_preferences(bpy.context)
        return prefs.panel_location
    except AttributeError:
        return PANEL_LOCATION_VIEWPORT


def _iter_panel_classes():
    """Yield the panels that belong to the movable panel tree.

    Popover panels (plain ``Panel`` classes invoked via ``layout.popover()``) and
    preset panels keep their own layout attributes and are never relocated.
    """
    for mdl in ui_modules:
        for cls in getattr(mdl, "classes", ()):
            if not issubclass(cls, bpy.types.Panel) or issubclass(cls, PresetPanel):
                continue
            if issubclass(cls, RCBasePanel) or getattr(cls, "bl_parent_id", None):
                yield cls


def register():
    location = _get_panel_location()
    for cls in _iter_panel_classes():
        apply_panel_location(cls, location)

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


def reload_panels():
    unregister()
    register()


_reload_scheduled = False


def schedule_reload():
    """Re-apply the panel location preference and re-register on the next frame."""
    global _reload_scheduled
    if _reload_scheduled:
        return
    _reload_scheduled = True
    bpy.app.timers.register(_reload_timer)


def _reload_timer():
    global _reload_scheduled
    _reload_scheduled = False
    reload_panels()
    return None
