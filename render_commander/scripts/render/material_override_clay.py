import bpy

# Name for the override material
override_mat_name = "Default_Diffuse_Override"

# Check if material already exists, otherwise create it
if override_mat_name in bpy.data.materials:
    override_mat = bpy.data.materials[override_mat_name]
else:
    override_mat = bpy.data.materials.new(name=override_mat_name)
    override_mat.use_nodes = True
    nodes = override_mat.node_tree.nodes
    links = override_mat.node_tree.links

    # Clear existing nodes
    nodes.clear()

    # Add Diffuse BSDF and Output node
    diffuse = nodes.new(type="ShaderNodeBsdfDiffuse")
    output = nodes.new(type="ShaderNodeOutputMaterial")

    # Position nodes for readability
    diffuse.location = (-200, 0)
    output.location = (0, 0)

    # Connect Diffuse to Output
    links.new(diffuse.outputs["BSDF"], output.inputs["Surface"])

    # Optional: set diffuse color (light gray)
    diffuse.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1.0)

# Apply override material to active view layer
view_layer = bpy.context.view_layer
view_layer.material_override = override_mat

print(f"Applied '{override_mat_name}' as material override to view layer '{view_layer.name}'.")
