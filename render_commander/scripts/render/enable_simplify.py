import bpy


def apply_low_vram_settings():
    scene = bpy.context.scene

    # --- CONFIGURATION ---
    # Options: 'OFF', '4096', '2048', '1024', '512', '256', '128'
    MAX_TEXTURE_SIZE = "1024"
    MAX_SUBDIVISIONS = 2
    PARTICLE_PERCENT = 0.5
    # ---------------------

    print(f"[:] Applying Low VRAM Optimizations on scene: {scene.name}")

    scene.render.use_simplify = True

    if hasattr(scene.render, "simplify_texture_limit"):
        scene.render.simplify_texture_limit = MAX_TEXTURE_SIZE
        print(f"[:] Texture Limit set to: {MAX_TEXTURE_SIZE}px (Standard)")
    elif scene.render.engine == "CYCLES" and hasattr(scene.cycles, "texture_limit"):
        try:
            scene.cycles.texture_limit = MAX_TEXTURE_SIZE
            print(f"[:] Texture Limit set to: {MAX_TEXTURE_SIZE}px (Cycles)")
        except TypeError:
            print("[:] Could not set Cycles texture limit (API type mismatch).")
    else:
        print("[:] Warning: 'simplify_texture_limit' property not found. Texture limit skipped.")

    if hasattr(scene.render, "simplify_subdivision_render"):
        scene.render.simplify_subdivision_render = MAX_SUBDIVISIONS
        print(f"[:] Max Render Subdivisions set to: {MAX_SUBDIVISIONS}")


if __name__ == "__main__":
    apply_low_vram_settings()
