import bpy
from bpy.types import Operator
from bpy.props import IntProperty, FloatProperty

from ..preferences import get_addon_preferences


class RECOM_OT_SetResolutionX(Operator):
    bl_idname = "recom.set_resolution_x"
    bl_label = "Set Resolution Width"
    bl_description = "Set Resolution Width"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.resolution_x = self.value
        return {"FINISHED"}


class RECOM_OT_SetResolutionY(Operator):
    bl_idname = "recom.set_resolution_y"
    bl_label = "Set Resolution Height"
    bl_description = "Set Resolution Height"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.resolution_y = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveThreshold(Operator):
    bl_idname = "recom.set_adaptive_threshold"
    bl_label = "Set Adaptive Threshold"
    bl_description = "Set Adaptive Threshold"

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_threshold = self.value
        return {"FINISHED"}


class RECOM_OT_SetSamples(Operator):
    bl_idname = "recom.set_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetAdaptiveMinSamples(Operator):
    bl_idname = "recom.set_adaptive_min_samples"
    bl_label = "Set Adaptive Min Samples"
    bl_description = "Set Adaptive Min Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.adaptive_min_samples = self.value
        return {"FINISHED"}


class RECOM_OT_SetTimeLimit(Operator):
    bl_idname = "recom.set_time_limit"
    bl_label = "Set Time Limit"
    bl_description = "Set Time Limit"

    value: FloatProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.time_limit = self.value
        return {"FINISHED"}


class RECOM_OT_SetTileSize(Operator):
    bl_idname = "recom.set_tile_size"
    bl_label = "Set Tile Size"
    bl_description = "Set Tile Size"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.cycles.tile_size = self.value
        return {"FINISHED"}


class RECOM_OT_SetEEVEESamples(Operator):
    bl_idname = "recom.set_eevee_samples"
    bl_label = "Set Samples"
    bl_description = "Set Samples"

    value: IntProperty()

    def execute(self, context):
        settings = context.window_manager.recom_render_settings
        settings.override_settings.eevee.samples = self.value
        return {"FINISHED"}


classes = (
    RECOM_OT_SetResolutionX,
    RECOM_OT_SetResolutionY,
    RECOM_OT_SetAdaptiveThreshold,
    RECOM_OT_SetSamples,
    RECOM_OT_SetAdaptiveMinSamples,
    RECOM_OT_SetTimeLimit,
    RECOM_OT_SetTileSize,
    RECOM_OT_SetEEVEESamples,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
