"""Turn the Sketchfab "Burger Realistic (Free)" GLB into models/burger-raw.glb with named layers.

Source: https://sketchfab.com/3d-models/burger-realistic-free-18e59d7dbd2243c69f469e0f056f44c4
        by erebus3d, CC-BY-4.0 (credit required).

Run:  blender --background --python tools/prepare_burger_model.py -- models/incoming/burger_realistic_free.glb models/burger-raw.glb

The source mesh joins several ingredients, so it is split into loose pieces and each piece is
sorted into a layer by material, height and width, then each layer is joined into one object
named like the "node" values in dishes.json. The result is scaled to a real 12 cm burger with
its bottom at z = 0, centred on x/y.
"""
import os
import sys
import bpy
import mathutils

src, dst = (os.path.abspath(p) for p in sys.argv[sys.argv.index("--") + 1:][:2])
REAL_WIDTH_M = 0.12
ORDER = ["bun_bottom", "lettuce", "patty", "cheese", "pickles", "tomato", "bun_top"]

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)

meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")


def bounds(o):
    ws = [o.matrix_world @ v.co for v in o.data.vertices]
    return [min(p[i] for p in ws) for i in range(3)], [max(p[i] for p in ws) for i in range(3)]


def layer_of(o):
    mn, mx = bounds(o)
    mat = o.active_material.name if o.active_material else ""
    width = mx[0] - mn[0]
    if mat.startswith("lettuce"):
        return "lettuce"
    if mat.startswith("vegies"):
        return "tomato" if width > 2 else "pickles"
    # everything below shares the bun texture atlas
    if mx[2] < 0.6:
        return "bun_bottom"
    if mn[2] > 1.3:
        return "bun_top"
    if 0.5 < mn[2] < 0.6 or mn[2] > 0.9:
        return "patty"      # side ring (0.53-0.95) and top disc (0.95)
    return "cheese"         # draped slice (0.63-1.16)


layers = {name: [] for name in ORDER}
for o in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
    layers[layer_of(o)].append(o)

# bake transforms so every part lives directly in world space
for objs in layers.values():
    for o in objs:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

joined = {}
for name, objs in layers.items():
    if not objs:
        raise SystemExit("no parts found for layer " + name)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    joined[name] = ob

# remove the now-empty Sketchfab hierarchy
for o in [o for o in bpy.context.scene.objects if o.type == "EMPTY"]:
    bpy.data.objects.remove(o, do_unlink=True)

# real size: scale about the bottom centre so the burger is REAL_WIDTH_M wide, bottom at z = 0
pts = [o.matrix_world @ v.co for o in joined.values() for v in o.data.vertices]
mn = mathutils.Vector([min(p[i] for p in pts) for i in range(3)])
mx = mathutils.Vector([max(p[i] for p in pts) for i in range(3)])
s = REAL_WIDTH_M / max(mx.x - mn.x, mx.y - mn.y)
offset = mathutils.Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
for ob in joined.values():
    for v in ob.data.vertices:
        v.co = (v.co - offset) * s
    # origin at each layer's own bottom centre (keeps explode motion clean)
    lv = [v.co for v in ob.data.vertices]
    lmn = mathutils.Vector([min(p[i] for p in lv) for i in range(3)])
    lmx = mathutils.Vector([max(p[i] for p in lv) for i in range(3)])
    origin = mathutils.Vector(((lmn.x + lmx.x) / 2, (lmn.y + lmx.y) / 2, lmn.z))
    for v in ob.data.vertices:
        v.co -= origin
    ob.location = origin
    print(f"LAYER {ob.name:10s} parts {len(layers[ob.name]):3d}  z {lmn.z*100:5.2f}-{lmx.z*100:5.2f} cm  verts {len(ob.data.vertices)}")

bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB", export_yup=True, use_selection=True)
print("wrote", dst)
