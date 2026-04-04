import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.cycles.sampling_override = True
settings.override_settings.cycles.samples = 64
settings.override_settings.cycles.adaptive_min_samples = 16
settings.override_settings.cycles.time_limit = 0.0
settings.override_settings.cycles.use_adaptive_sampling = True
settings.override_settings.cycles.adaptive_threshold = 0.035
settings.override_settings.cycles.use_denoising = False
settings.override_settings.cycles.denoiser = "OPENIMAGEDENOISE"
settings.override_settings.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
settings.override_settings.cycles.denoising_prefilter = "ACCURATE"
settings.override_settings.cycles.denoising_quality = "HIGH"
settings.override_settings.cycles.denoising_use_gpu = True
settings.override_settings.cycles.denoising_store_passes = False
settings.override_settings.output_path_override = True
settings.override_settings.output_directory = "{blend_dir}/render/"
settings.override_settings.output_filename = "{blend_name}_Draft"
settings.override_settings.file_format_override = True
settings.override_settings.file_format = "JPEG"
settings.override_settings.jpeg_quality = 85
settings.override_settings.format_override = True
settings.override_settings.resolution_override = False
settings.override_settings.resolution_mode = "SET_WIDTH"
settings.override_settings.resolution_x = 512
settings.override_settings.resolution_y = 512
settings.override_settings.custom_render_scale = 50
settings.override_settings.use_custom_api_overrides = True
