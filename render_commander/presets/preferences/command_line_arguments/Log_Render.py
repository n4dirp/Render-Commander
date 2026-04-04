import bpy
settings = bpy.context.preferences.addons['bl_ext.D_Blender_packages.render_commander'].preferences

settings.custom_command_line_args = '-noaudio --log render'
