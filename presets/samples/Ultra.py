import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.use_adaptive_sampling = True
settings.override_settings.cycles.adaptive_threshold = 0.01
settings.override_settings.cycles.samples = 4096
settings.override_settings.cycles.adaptive_min_samples = 64
settings.override_settings.cycles.time_limit = 0.0
settings.override_settings.cycles.use_denoising = False
