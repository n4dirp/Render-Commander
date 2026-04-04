import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.output_directory = "{blend_dir}/render/"
settings.override_settings.output_filename = "{blend_name}"
