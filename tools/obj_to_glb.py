"""Convert an OpenMVS textured OBJ into one self-contained GLB (texture embedded).

Run:  blender --background --python tools/obj_to_glb.py -- in.obj out.glb
Used by scan.ps1. Fixes OpenMVS's "Tr 1" (read as fully transparent) and makes
the surface matte, since a scan's texture already holds the real lighting.
"""
import os
import sys
import bpy

src, dst = (os.path.abspath(p) for p in sys.argv[sys.argv.index("--") + 1:][:2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=src)

for mat in bpy.data.materials:
    if not mat.use_nodes:
        continue
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        continue
    for link in list(bsdf.inputs["Alpha"].links):
        mat.node_tree.links.remove(link)
    # make sure the scan texture drives the colour
    tex = next((n for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and n.image), None)
    if tex is not None:
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Alpha"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    if hasattr(mat, "blend_method"):
        mat.blend_method = "OPAQUE"

for ob in bpy.context.scene.objects:
    if ob.type == "MESH":
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()

bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_yup=True)
print("wrote", dst)
