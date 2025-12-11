import bpy

settings = bpy.context.window_manager.recom_render_settings

settings.override_settings.resolution_override = True
settings.override_settings.resolution_mode = "CUSTOM"
settings.override_settings.resolution_x = 4096
settings.override_settings.resolution_y = 2160
settings.override_settings.render_scale = "1.00"
settings.override_settings.custom_render_scale = 100
