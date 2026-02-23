import bpy


def apply_low_vram_settings():
    """
    Applies on-the-fly optimizations to the current scene to reduce VRAM usage.
    Safe for Blender 4.0, 5.0, and newer API changes.
    """
    scene = bpy.context.scene

    # --- CONFIGURATION ---
    # Options: 'OFF', '4096', '2048', '1024', '512', '256', '128'
    MAX_TEXTURE_SIZE = "1024"
    MAX_SUBDIVISIONS = 2
    PARTICLE_PERCENT = 0.5
    # ---------------------

    print(f"[:] Applying Low VRAM Optimizations on scene: {scene.name}")

    # 1. Enable Global Simplify
    scene.render.use_simplify = True

    # 2. Limit Texture Size (Robust Check)
    # Tries standard API first, then falls back to engine-specific or alternative paths
    if hasattr(scene.render, "simplify_texture_limit"):
        scene.render.simplify_texture_limit = MAX_TEXTURE_SIZE
        print(f"[:] Texture Limit set to: {MAX_TEXTURE_SIZE}px (Standard)")
    elif scene.render.engine == "CYCLES" and hasattr(scene.cycles, "texture_limit"):
        # Fallback for Cycles if moved in 5.0+
        try:
            scene.cycles.texture_limit = MAX_TEXTURE_SIZE
            print(f"[:] Texture Limit set to: {MAX_TEXTURE_SIZE}px (Cycles)")
        except TypeError:
            # Sometimes Cycles expects an INT index or INT value depending on version
            # If string fails, we try to safely skip or default to a hardcoded int if known
            print("[:] Could not set Cycles texture limit (API type mismatch).")
    else:
        print("[:] Warning: 'simplify_texture_limit' property not found. Texture limit skipped.")

    # 3. Cap Geometry Subdivisions
    if hasattr(scene.render, "simplify_subdivision_render"):
        scene.render.simplify_subdivision_render = MAX_SUBDIVISIONS
        print(f"[:] Max Render Subdivisions set to: {MAX_SUBDIVISIONS}")

    # 4. Reduce Child Particles
    if hasattr(scene.render, "simplify_child_particles_render"):
        scene.render.simplify_child_particles_render = PARTICLE_PERCENT
        print(f"[:] Particles reduced to: {PARTICLE_PERCENT * 100}%")


if __name__ == "__main__":
    apply_low_vram_settings()
