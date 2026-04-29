import bpy

settings = bpy.context.window_manager.recom_render_settings

use_templates = bpy.app.version >= (5, 0)

if use_templates:
    settings.override_settings.output_directory = "{blend_dir}"
    settings.override_settings.output_filename = "{blend_name}"
else:
    settings.override_settings.output_directory = "//"
    settings.override_settings.output_filename = "render"
