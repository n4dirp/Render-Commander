import bpy


def apply_metadata_settings():
    """
    Enables 'Burn Into Image' and configures metadata stamping.
    """
    scene = bpy.context.scene
    r = scene.render

    # --- CONFIGURATION ---
    # Set these to True/False to choose what gets burned into the image
    SHOW_DATE = True
    SHOW_TIME = True
    SHOW_RENDER_TIME = True
    SHOW_FRAME = True
    SHOW_MEMORY = True
    SHOW_CAMERA = True
    SHOW_LENS = False
    SHOW_SCENE = False
    SHOW_FILENAME = True
    SHOW_LABELS = True

    # Appearance
    FONT_SIZE = 12
    FONT_COLOR = (1.0, 1.0, 1.0, 1.0)
    BG_COLOR = (0.0, 0.0, 0.0, 0.5)

    # Custom Note (Optional)
    CUSTOM_NOTE = ""
    # ---------------------

    print(f"[:] Enabling Metadata Burn-in on scene: {scene.name}")

    r.use_stamp = True

    settings_map = {
        "use_stamp_date": SHOW_DATE,
        "use_stamp_time": SHOW_TIME,
        "use_stamp_render_time": SHOW_RENDER_TIME,
        "use_stamp_frame": SHOW_FRAME,
        "use_stamp_memory": SHOW_MEMORY,
        "use_stamp_camera": SHOW_CAMERA,
        "use_stamp_lens": SHOW_LENS,
        "use_stamp_scene": SHOW_SCENE,
        "use_stamp_filename": SHOW_FILENAME,
        "use_stamp_labels": SHOW_LABELS,
    }

    for prop, value in settings_map.items():
        if hasattr(r, prop):
            setattr(r, prop, value)
        else:
            print(f"[:] Warning: Property '{prop}' not found (Skipped).")

    try:
        r.stamp_font_size = FONT_SIZE
        r.stamp_foreground = FONT_COLOR
        r.stamp_background = BG_COLOR
        print(f"[:] Stamp Visuals applied (Size: {FONT_SIZE})")
    except AttributeError:
        print("[:] Warning: Could not set stamp visual properties.")

    if CUSTOM_NOTE:
        if hasattr(r, "use_stamp_note"):
            r.use_stamp_note = True
            r.stamp_note_text = CUSTOM_NOTE
            print("[:] Custom note attached.")


if __name__ == "__main__":
    apply_metadata_settings()
