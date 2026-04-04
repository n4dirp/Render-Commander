import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.sampling_override = True
settings.override_settings.cycles.samples = 4096
settings.override_settings.cycles.adaptive_min_samples = 64
settings.override_settings.cycles.time_limit = 0.0
settings.override_settings.cycles.use_adaptive_sampling = True
settings.override_settings.cycles.adaptive_threshold = 0.005
settings.override_settings.cycles.use_denoising = False
settings.override_settings.output_path_override = True
settings.override_settings.output_directory = "{blend_dir}/render/"
settings.override_settings.output_filename = "{blend_name}_Ultra"
settings.override_settings.file_format_override = True
settings.override_settings.file_format = "OPEN_EXR_MULTILAYER"
settings.override_settings.color_depth = "32"
settings.override_settings.codec = "DWAA"
settings.override_settings.jpeg_quality = 90
settings.override_settings.format_override = False
settings.override_settings.resolution_override = False
settings.override_settings.resolution_mode = "SET_WIDTH"
settings.override_settings.resolution_x = 4096
settings.override_settings.resolution_y = 2160
settings.override_settings.custom_render_scale = 100
settings.override_settings.use_custom_api_overrides = True
