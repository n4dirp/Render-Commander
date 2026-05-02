# ./utils/cycles_devices.py

import logging
import unicodedata

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import PropertyGroup

from .constants import MODE_SINGLE
from .helpers import redraw_ui

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
log.setLevel(logging.WARNING)


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


# Enum & Update Callbacks
#################################################


def get_device_types_items(self, context):
    """Build dynamic enum items from the currently available Cycles device entries."""
    global _DEVICE_ITEMS_CACHE

    # Return the cached items if they exist to prevent UI lag and memory crashes
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

    # Dynamically read what devices are currently registered in Cycles
    for dev in getattr(cycles_prefs, "devices", []):
        dev_type = getattr(dev, "type", "")
        if not dev_type or dev_type in seen or dev_type == "CPU":
            continue

        seen.add(dev_type)
        name = friendly_names.get(dev_type, dev_type)
        items.append((dev_type, name, f"Use {name} for GPU acceleration"))

    _DEVICE_ITEMS_CACHE = items  # Save to cache
    return _DEVICE_ITEMS_CACHE


# Device List Management (Refactored / Merged)
#################################################


def refresh_cycles_devices(prefs, context=None, sync_type=True):
    """Refresh the local device list from Cycles."""
    global _DEVICE_ITEMS_CACHE
    _DEVICE_ITEMS_CACHE = None  # Reset the cache so the Enum updates

    context = context or bpy.context
    cycles_prefs = get_cycles_prefs(context)

    if not cycles_prefs:
        if sync_type:
            prefs.compute_device_type = "NONE"
        prefs.devices.clear()
        return False

    try:
        # Sync active compute device type from Cycles
        if sync_type:
            cycles_type = getattr(cycles_prefs, "compute_device_type", "NONE")
            valid_types = [item[0] for item in get_device_types_items(prefs, context)]

            if cycles_type in valid_types and prefs.compute_device_type != cycles_type:
                prefs.compute_device_type = cycles_type

        # Smart sync devices to avoid UI duplicating items (diffing instead of .clear())
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
                # Update existing entry
                entry = existing_devices[key]
                if entry.name != dev_name:
                    entry.name = dev_name
                entry.use = dev_use
            else:
                # Create new entry
                item = prefs.devices.add()
                item.id = dev_id
                item.name = dev_name
                item.type = dev_type
                item.use = dev_use
                existing_devices[key] = item

        # Remove stale devices that are no longer in Cycles
        for i in range(len(prefs.devices) - 1, -1, -1):
            d = prefs.devices[i]
            if (d.id, d.type) not in fresh_keys:
                prefs.devices.remove(i)

        redraw_ui()
        return True

    except Exception as e:
        log.error("Error refreshing Cycles device settings: %s", e)
        return False


# UI & Formatting Utilities
#################################################


def format_device_name(name):
    """Format trademark symbols for the UI."""
    return (
        name.replace("(TM)", unicodedata.lookup("TRADE MARK SIGN"))
        .replace("(tm)", unicodedata.lookup("TRADE MARK SIGN"))
        .replace("(R)", unicodedata.lookup("REGISTERED SIGN"))
        .replace("(C)", unicodedata.lookup("COPYRIGHT SIGN"))
    )


def get_devices_for_display(prefs):
    """Get list of devices for UI display."""
    selected = prefs.compute_device_type
    devices_to_display = []

    if prefs.multiple_backends and prefs.device_parallel and prefs.launch_mode != MODE_SINGLE:
        devices_to_display.extend([d for d in prefs.devices if d.type == "CPU"])
        devices_to_display.extend([d for d in prefs.devices if d.type != "CPU"])
    else:
        devices_to_display.extend([d for d in prefs.devices if d.type == selected and d.type != "CPU"])

        if selected != "CPU":
            existing_ids = {d.id for d in devices_to_display}
            devices_to_display.extend([d for d in prefs.devices if d.type == "CPU" and d.id not in existing_ids])
        else:
            devices_to_display = [d for d in prefs.devices if d.type == "CPU"]

    return devices_to_display


def draw_devices(layout, prefs):
    """Draw device list in UI."""

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
            # Draw group labels
            if device.type != prev_type:
                row = col.row()
                row.active = False
                row.label(text=device.type)

        if prefs.show_device_id and device.type != "CPU":
            device_name = device.id
        else:
            device_name = format_device_name(device.name)

        col.prop(device, "use", text=device_name, translate=False)

        prev_type = device.type
