# ./utils/cycles_devices.py

import logging
import unicodedata
from typing import List, NamedTuple, Optional

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup

from .constants import MODE_SINGLE
from .helpers import redraw_ui

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log.setLevel(logging.WARNING)


# -----------------------------------------------------------
# Normalized device abstraction
# -----------------------------------------------------------


class DeviceEntry(NamedTuple):
    """Normalized device representation from either addon prefs or Cycles prefs."""

    id: str
    name: str
    use: bool
    type: str


def _normalize_device(dev) -> DeviceEntry:
    """Convert any device-like object (PG_DeviceSettings or Cycles device) to DeviceEntry."""
    return DeviceEntry(
        id=getattr(dev, "id", ""),
        name=getattr(dev, "name", ""),
        use=bool(getattr(dev, "use", False)),
        type=getattr(dev, "type", ""),
    )


# -----------------------------------------------------------
# Cycles preference access
# -----------------------------------------------------------


def get_cycles_prefs(context=None):
    """Return Blender's Cycles add-on preferences safely, or None if unavailable."""
    if not getattr(bpy.app.build_options, "cycles", False):
        return None

    context = context or bpy.context
    prefs = getattr(context, "preferences", None)
    if prefs is None:
        return None

    addon = prefs.addons.get("cycles")
    if addon is None:
        return None

    return addon.preferences


_CYCLES_AVAILABLE = get_cycles_prefs()
_DEVICE_ITEMS_CACHE = None


class RECOM_PG_DeviceSettings(PropertyGroup):
    """Local mirror of a Cycles device entry."""

    id: StringProperty(name="ID", description="Unique identifier of the device")
    name: StringProperty(name="Name", description="Name of the device")
    use: BoolProperty(name="Use", description="Use device for rendering", default=True)
    type: StringProperty(name="Type", description="Backend type (e.g., CUDA, OPTIX, CPU)")


# -----------------------------------------------------------
# Enum & Update Callbacks
# -----------------------------------------------------------


def get_device_types_items(self, context):
    """Build dynamic enum items from the currently available Cycles device entries."""
    global _DEVICE_ITEMS_CACHE

    if _DEVICE_ITEMS_CACHE is not None:
        return _DEVICE_ITEMS_CACHE

    cycles_prefs = get_cycles_prefs(context)
    items = [("NONE", "None", "Don't use compute device")]

    if not cycles_prefs:
        _DEVICE_ITEMS_CACHE = items
        return items

    seen = set()
    friendly_names = {
        "CUDA": "CUDA",
        "OPTIX": "OptiX",
        "HIP": "HIP",
        "METAL": "Metal",
        "ONEAPI": "oneAPI",
    }

    for dev in getattr(cycles_prefs, "devices", []):
        dev_type = getattr(dev, "type", "")
        if not dev_type or dev_type in seen or dev_type == "CPU":
            continue

        seen.add(dev_type)
        name = friendly_names.get(dev_type, dev_type)
        items.append((dev_type, name, f"Use {name} for GPU acceleration"))

    _DEVICE_ITEMS_CACHE = items
    return _DEVICE_ITEMS_CACHE


# -----------------------------------------------------------
# Unified device source resolution
# -----------------------------------------------------------


def _get_device_source(prefs, context=None):
    """Return (source_prefs, is_local) tuple.

    When prefs.manage_cycles_devices is True, uses the addon's local device list.
    Otherwise reads directly from Cycles preferences.
    """
    if getattr(prefs, "manage_cycles_devices", False):
        return prefs, True
    return get_cycles_prefs(context), False


def get_compute_device_type(prefs, context=None) -> str:
    """Get the active compute device type from the appropriate source."""
    source, is_local = _get_device_source(prefs, context)
    if source is None:
        return "NONE"
    return getattr(source, "compute_device_type", "NONE")


# -----------------------------------------------------------
# Unified device list retrieval
# -----------------------------------------------------------


def get_devices_for_display(prefs, context=None) -> List[DeviceEntry]:
    """Get list of devices sorted for UI/display, from the appropriate source.

    Returns normalized DeviceEntry objects regardless of source.
    When manage_cycles_devices is True, reads from addon's local prefs.devices.
    Otherwise reads directly from Cycles preferences.
    """
    source, is_local = _get_device_source(prefs, context)

    if source is None:
        return []

    if is_local:
        raw_devices = list(getattr(source, "devices", []))
    else:
        raw_devices = list(getattr(source, "devices", []))

    devices = [_normalize_device(d) for d in raw_devices]
    selected = get_compute_device_type(prefs, context)

    if prefs.multiple_backends and prefs.device_parallel and prefs.launch_mode != MODE_SINGLE:
        # Multi-backend: show all devices, CPU first
        result = [d for d in devices if d.type == "CPU"]
        result.extend([d for d in devices if d.type != "CPU"])
    else:
        # Filter by active type
        result = [d for d in devices if d.type == selected and d.type != "CPU"]

        if selected != "CPU":
            existing_ids = {d.id for d in result}
            result.extend([d for d in devices if d.type == "CPU" and d.id not in existing_ids])
        else:
            result = [d for d in devices if d.type == "CPU"]

    return result


def get_cpu_device(prefs, context=None) -> Optional[DeviceEntry]:
    """Get the first enabled CPU device from the appropriate source."""
    devices = get_devices_for_display(prefs, context)
    for d in devices:
        if d.use and d.type == "CPU":
            return d
    return None


# -----------------------------------------------------------
# Device List Management (Local only)
# -----------------------------------------------------------


def refresh_local_devices(prefs, context=None, sync_type=True):
    """Refresh the local device list from Cycles. Only used when manage_cycles_devices is True."""
    global _DEVICE_ITEMS_CACHE
    _DEVICE_ITEMS_CACHE = None

    context = context or bpy.context
    cycles_prefs = get_cycles_prefs(context)

    if not cycles_prefs:
        if sync_type:
            prefs.compute_device_type = "NONE"
        prefs.devices.clear()
        return False

    try:
        if sync_type:
            cycles_type = getattr(cycles_prefs, "compute_device_type", "NONE")
            valid_types = [item[0] for item in get_device_types_items(prefs, context)]

            if cycles_type in valid_types and prefs.compute_device_type != cycles_type:
                prefs.compute_device_type = cycles_type

        fresh_keys = set()
        existing_devices = {(d.id, d.type): d for d in prefs.devices}

        for cyc_dev in getattr(cycles_prefs, "devices", []):
            dev_id = getattr(cyc_dev, "id", "")
            dev_type = getattr(cyc_dev, "type", "")
            dev_name = getattr(cyc_dev, "name", "")
            dev_use = bool(getattr(cyc_dev, "use", False))

            if not dev_id or not dev_type:
                continue

            key = (dev_id, dev_type)
            fresh_keys.add(key)

            if key in existing_devices:
                entry = existing_devices[key]
                if entry.name != dev_name:
                    entry.name = dev_name
                entry.use = dev_use
            else:
                item = prefs.devices.add()
                item.id = dev_id
                item.name = dev_name
                item.type = dev_type
                item.use = dev_use
                existing_devices[key] = item

        for i in range(len(prefs.devices) - 1, -1, -1):
            d = prefs.devices[i]
            if (d.id, d.type) not in fresh_keys:
                prefs.devices.remove(i)

        redraw_ui()
        return True

    except Exception as e:
        log.error("Error refreshing Cycles device settings: %s", e)
        return False


# -----------------------------------------------------------
# UI & Formatting Utilities
# -----------------------------------------------------------


def format_device_name(name):
    """Format trademark symbols for the UI."""
    return (
        name.replace("(TM)", unicodedata.lookup("TRADE MARK SIGN"))
        .replace("(tm)", unicodedata.lookup("TRADE MARK SIGN"))
        .replace("(R)", unicodedata.lookup("REGISTERED SIGN"))
        .replace("(C)", unicodedata.lookup("COPYRIGHT SIGN"))
    )


def draw_devices(layout, prefs):
    """Draw device list in UI. Uses local prefs.devices directly."""
    devices_to_draw = get_devices_for_display(prefs)

    if not devices_to_draw:
        col = layout.column(align=True)
        col.active = False
        col.label(text="No compatible devices found")
        return

    prev_type = None
    for device in devices_to_draw:
        if prev_type is not None and device.type != prev_type:
            layout.separator(factor=0.5)

        col = layout.column(align=True)

        if prefs.multiple_backends and prefs.device_parallel and prefs.launch_mode != MODE_SINGLE:
            if device.type != prev_type:
                row = col.row()
                row.active = False
                row.label(text=device.type)

        if prefs.show_device_id and device.type != "CPU":
            device_name = device.id
        else:
            device_name = format_device_name(device.name)

        # Find the actual PG device for prop binding (only works with local prefs)
        pg_device = next((d for d in prefs.devices if d.id == device.id and d.type == device.type), None)
        if pg_device:
            col.prop(pg_device, "use", text=device_name, translate=False)

        prev_type = device.type
