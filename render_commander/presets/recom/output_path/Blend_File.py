import bpy

override_settings = bpy.context.window_manager.recom_render_settings.override_settings

use_templates = bpy.app.version >= (5, 0)

if use_templates:
    override_settings.output_directory = "{blend_dir}"
    override_settings.output_filename = "{blend_name}"
else:
    override_settings.output_directory = "//"
    override_settings.output_filename = "render"
