import bpy

override_settings = bpy.context.window_manager.recom_render_settings.override_settings

override_settings.resolution_override = True
override_settings.resolution_mode = "CUSTOM"
override_settings.resolution_x = 1280
override_settings.resolution_y = 720
override_settings.custom_render_scale = 100
