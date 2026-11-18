"""Build models/sample.glb: a 3-layer test dish with named nodes (base, middle, top).

Run:  blender --background --python tools/make_sample_glb.py
It shows the naming rule the viewer relies on: one object per layer, named exactly
like the "node" values in dishes.json, sized in metres, origin at the layer's bottom.
"""
import os
import bpy

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "sample.glb")

bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, rgb, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


# (name, radius m, height m, z of bottom m, colour, roughness)
layers = [
    ("base",   0.060, 0.020, 0.000, (0.80, 0.55, 0.25), 0.6),
    ("middle", 0.058, 0.015, 0.020, (0.35, 0.18, 0.08), 0.8),
    ("top",    0.060, 0.035, 0.035, (0.70, 0.38, 0.12), 0.5),
]

for name, r, h, z, rgb, rough in layers:
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r, depth=h, location=(0, 0, z + h / 2))
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    ob.data.materials.append(material(name, rgb, rough))
    bpy.ops.object.shade_smooth()

os.makedirs(os.path.dirname(OUT), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", export_yup=True)
print("wrote", os.path.abspath(OUT))
