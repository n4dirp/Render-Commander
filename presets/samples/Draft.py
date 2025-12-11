import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.use_adaptive_sampling = True
settings.override_settings.cycles.adaptive_threshold = 0.1
settings.override_settings.cycles.samples = 64
settings.override_settings.cycles.adaptive_min_samples = 0
settings.override_settings.cycles.time_limit = 0.0
settings.override_settings.cycles.use_denoising = False
