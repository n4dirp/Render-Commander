import bpy

settings = bpy.context.window_manager.recom_render_settings
settings.override_settings.cycles.sampling_override = False
settings.override_settings.cycles.device_override = False
settings.override_settings.cycles.performance_override = False
settings.override_settings.eevee_override = False
settings.override_settings.frame_range_override = False
settings.override_settings.output_path_override = False
settings.override_settings.file_format_override = False
settings.override_settings.format_override = False
settings.override_settings.use_overscan = False
settings.override_settings.motion_blur_override = False
settings.override_settings.compositor_override = False
settings.override_settings.cameras_override = False
settings.override_settings.use_custom_api_overrides = True

# Custom API Overrides Collection
settings.override_settings.custom_api_overrides.clear()

item = settings.override_settings.custom_api_overrides.add()
item.name = "Enable Simplify"
item.data_path = "bpy.context.scene.render.use_simplify"
item.prop_type = "BOOL"
item.value_bool = True
item = settings.override_settings.custom_api_overrides.add()
item.name = "Max Render Subdiv"
item.data_path = "bpy.context.scene.render.simplify_subdivision_render"
item.prop_type = "INT"
item.value_int = 2

settings.override_settings.active_custom_api_index = 0
