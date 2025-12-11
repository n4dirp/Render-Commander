import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.max_bounces = 12
settings.override_settings.cycles.diffuse_bounces = 3
settings.override_settings.cycles.glossy_bounces = 4
settings.override_settings.cycles.transmission_bounces = 12
settings.override_settings.cycles.volume_bounces = 1
settings.override_settings.cycles.transparent_bounces = 8
settings.override_settings.cycles.sample_clamp_direct = 16.0
settings.override_settings.cycles.sample_clamp_indirect = 8.0
settings.override_settings.cycles.caustics_reflective = True
settings.override_settings.cycles.caustics_refractive = True
settings.override_settings.cycles.blur_glossy = 1.0
