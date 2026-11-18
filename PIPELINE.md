# One dish, start to finish

Target: one `models/<id>.glb`, **≤ 5 MB**, real size in metres, one named node per ingredient layer.

## 0. Plan the layers first

A scan only captures surfaces the camera can see, so the patty inside a closed burger is never captured.
For a dish that explodes into layers:

- **Scan each layer on its own** (bottom bun, patty, cheese…) on the same plate, then stack them in Blender. This gives the best result.
- Or scan the whole dish closed, and add the hidden layers by scanning them separately or modelling them in Blender.

Write the layer list (bottom to top) before shooting. These names become the node names, e.g. `bun_bottom, patty, cheese, tomato, lettuce, bun_top`.

## 1. Capture

- Use soft, even light with no hard shadows: a cloudy window or two lamps with diffusers. Food is shiny, so avoid direct sun and flash.
- Put the item on a **textured, non-shiny** surface. A newspaper or patterned cloth helps tracking. Don't use a white plate on a white table.
- Keep a ruler or a known-size object in a few shots so you can set the real scale later.
- **Photos:** take 70–150 sharp photos in 3 rings (low, middle, high), stepping about 10° between shots, with 60–80 % overlap. Lock exposure and focus, and don't zoom.
- **Video option:** do 2–3 slow orbits in 4K. Extract frames with `ffmpeg -i dish.mp4 -vf fps=3 -q:v 2 frames/%04d.jpg`.
- Shoot fast. Food dries and wilts within minutes.

## 2a. Reconstruct with KIRI Engine (easiest)

Phone app or kiriengine.app → **Photo Scan** → upload → wait → **Export GLB or OBJ** with textures.
Skip to step 3.

## 2b. Reconstruct with COLMAP + OpenMVS (local, free, uses your RTX 4070)

Installed in `C:\tools\colmap` and `C:\tools\openmvs_cuda`. One command does everything:

```powershell
.\tools\scan.ps1 -Photos D:\shoot\patty -Name patty
```

- **Video instead of photos:** `-Video D:\shoot\patty.mp4` (frames are extracted at 3 per second).
- **Quality:** `-Quality fast | normal | high`. Normal is the default. High adds mesh refining and is slower.
- **Easier:** drag a photo folder onto `tools\scan.bat` and type the layer name.
- **Result:** `scans\<name>\<name>.glb`, a textured GLB with the texture embedded. 72 photos take about 2 minutes on the RTX 4070.
- **Scale:** the scan's size and orientation are arbitrary. You fix both in Blender in step 3.
- **If it fails at "Solve camera positions":** reshoot with more overlap, sharper focus or more surface texture.

## 2c. Reconstruct with ComfyUI image-to-3D (when you only have 1–4 photos)

Use this when a scan isn't possible. The shape is invented by AI, so it looks less realistic than a scan.

1. ComfyUI → **Templates → 3D → Hunyuan3D 2.1** (needs the model, ~8 GB, not installed yet).
2. Load a clean front photo with the background removed, then run it. The output is a GLB in `ComfyUI/output/`.
3. The built-in nodes make the **shape only**. Texture it in Blender (step 3, project the photo) or use a scan for the final dish.

## 3. Blender cleanup and layer separation

1. **File → Import** the OBJ or GLB.
2. **Scale and orient:** Set the real size using the ruler: `S` and type the factor. A burger is about 0.12 m wide. Put the bottom at Z = 0 and centre it on X/Y. Then use `Ctrl+A` → **All Transforms**.
3. **Clean:** In Edit Mode, delete the table and background around the dish (`L` to select islands, `X`). Use `Mesh → Clean Up → Merge by Distance`, then fill holes (`Alt+F` on a selected boundary).
4. **Separate layers:** For a single scan, select each ingredient's faces and press `P` → **Selection**. For per-layer scans, import each one and stack them.
5. **Name each object** exactly as in `dishes.json` → `layers[].node` (e.g. `patty`). Names are case-sensitive.
6. **Origin:** For each layer, use `Object → Set Origin → Origin to Geometry`. Order doesn't matter in the file, because the viewer follows `dishes.json`.
7. **Reduce polygons:** Add a Decimate modifier and aim for **≤ 100k triangles for the whole dish** (20–50k is ideal). Apply it.
8. **Textures:** Use 2048 px max per layer, or 1024 for small layers. If the scan has a huge texture, bake it down: `Render → Bake` with Cycles, Diffuse colour.
9. Optional: you can leave the plate in as its own node (not listed in `layers`). Then it stays still while the food explodes.

**Export:** `File → Export → glTF 2.0`:
- Format **glTF Binary (.glb)**
- Include: **Selected Objects** (or Visible), +Y Up ✔
- Mesh: Apply Modifiers ✔, UVs ✔, Normals ✔
- Compression: off (step 4 handles it)

Save it as `models/<id>-raw.glb`.

## 4. Compress to ≤ 5 MB

```powershell
npx @gltf-transform/cli optimize models/burger-raw.glb models/burger.glb --compress draco --texture-compress webp --texture-size 2048 --join false --flatten false
```

Check the result:

```powershell
npx @gltf-transform/cli inspect models/burger.glb
```

- Still over 5 MB? Rerun with `--texture-size 1024`, or decimate more in Blender.
- `--join false --flatten false` stops it merging layers that share a material. Check that every layer name still appears in `inspect`.
- The viewer supports Draco, Meshopt and WebP.

## 5. Add to the menu

Add an entry to `dishes.json`:

```json
{
  "id": "burger",
  "name": { "en": "Classic Burger", "ar": "برغر كلاسيك" },
  "model": "models/burger.glb",
  "size_m": 0.12,
  "layers": [
    { "node": "bun_bottom", "en": "Bottom bun", "ar": "الخبز السفلي" },
    { "node": "patty",      "en": "Beef patty", "ar": "لحم البرغر" }
  ]
}
```

- `id`: lowercase, no spaces. It's the `?dish=` value and the QR file name.
- `size_m`: real width in metres, used for AR placement on the table.
- `layers`: bottom to top. Nodes not listed don't move.

## 6. Test and make the QR

1. Run `python -m http.server 8080` in this folder, then open `http://localhost:8080/?dish=burger`. Drag, explode, and check that the labels line up.
2. Run `python tools/make_qr.py https://<your-site>/` to create `qr/burger.png`.
3. Scan the QR with a phone on the HTTPS site and test Camera and AR mode.
