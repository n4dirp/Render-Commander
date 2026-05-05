import bpy
override_settings = bpy.context.window_manager.recom_render_settings.override_settings

override_settings.use_data_path_overrides = True
override_settings.data_path_overrides.clear()
item_sub_1 = override_settings.data_path_overrides.add()
item_sub_1.name = 'Use Simplify'
item_sub_1.data_path = 'bpy.context.scene.render.use_simplify'
item_sub_1.prop_type = 'BOOL'
item_sub_1.value_bool = False
item_sub_1.value_int = 0
item_sub_1.value_float = 0.0
item_sub_1.value_string = ''
item_sub_1.value_vector_3 = (0.0, 0.0, 0.0)
item_sub_1.value_color_4 = (0.0, 0.0, 0.0, 0.0)
item_sub_1 = override_settings.data_path_overrides.add()
item_sub_1.name = 'Simplify Subdivision Render'
item_sub_1.data_path = 'bpy.context.scene.render.simplify_subdivision_render'
item_sub_1.prop_type = 'INT'
item_sub_1.value_bool = False
item_sub_1.value_int = 6
item_sub_1.value_float = 0.0
item_sub_1.value_string = ''
item_sub_1.value_vector_3 = (0.0, 0.0, 0.0)
item_sub_1.value_color_4 = (0.0, 0.0, 0.0, 0.0)

# Custom API Overrides Collection
override_settings.data_path_overrides.clear()
item = override_settings.data_path_overrides.add()
item.name = 'Use Simplify'
item.data_path = 'bpy.context.scene.render.use_simplify'
item.prop_type = 'BOOL'
item.value_bool = False
item = override_settings.data_path_overrides.add()
item.name = 'Simplify Subdivision Render'
item.data_path = 'bpy.context.scene.render.simplify_subdivision_render'
item.prop_type = 'INT'
item.value_int = 6
override_settings.active_data_path_index = 1