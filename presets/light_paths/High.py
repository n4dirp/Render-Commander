import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.max_bounces = 16
settings.override_settings.cycles.diffuse_bounces = 4
settings.override_settings.cycles.glossy_bounces = 6
settings.override_settings.cycles.transmission_bounces = 16
settings.override_settings.cycles.volume_bounces = 2
settings.override_settings.cycles.transparent_bounces = 12
settings.override_settings.cycles.sample_clamp_direct = 32.0
settings.override_settings.cycles.sample_clamp_indirect = 16.0
settings.override_settings.cycles.caustics_reflective = True
settings.override_settings.cycles.caustics_refractive = True
settings.override_settings.cycles.blur_glossy = 0.5
