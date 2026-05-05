import bpy

cycles_settings = bpy.context.window_manager.recom_render_settings.override_settings.cycles

cycles_settings.sampling_mode = "CUSTOM"
cycles_settings.use_adaptive_sampling = True
cycles_settings.adaptive_threshold = 0.05
cycles_settings.samples = 512
cycles_settings.adaptive_min_samples = 16
cycles_settings.time_limit = 0.0
cycles_settings.use_denoising = True
