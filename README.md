# Real Menu

AR smart menu for restaurants. A QR code on each dish opens a page that shows the dish in 3D:
rotate it 360°, explode it into ingredient layers, see it through the phone camera, or place it
on the real table with WebXR (Android Chrome).

- `index.html` – the viewer. Opens `?dish=<id>` from `dishes.json`, falls back to a built-in burger.
- `dishes.json` – menu: id, English/Arabic name, model path, real size, layer names.
- `models/` – compressed GLB files (≤ 5 MB each).
- `PIPELINE.md` – how to turn one real dish into a model.
- `tools/` – scan (COLMAP + OpenMVS), Blender helpers, QR code generator.

## Credits

- Burger model: ["Burger Realistic (Free)"](https://sketchfab.com/3d-models/burger-realistic-free-18e59d7dbd2243c69f469e0f056f44c4)
  by erebus3d, licensed [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/). Split into named layers, rescaled and compressed.
- [three.js](https://threejs.org) r128 (MIT).
