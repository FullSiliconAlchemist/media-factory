"""Blender-side entry point. Only reviewed project Python belongs here."""
import json
import runpy
import sys
from pathlib import Path

import bpy

action, folder, destination = sys.argv[sys.argv.index("--") + 1:]
project, out = Path(folder), Path(destination)
plan = json.loads((project / "scene.json").read_text())
if action == "build":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    runpy.run_path(str(project / "build.py"))["build"](plan)
scene = bpy.context.scene
if not scene.camera or not any(obj.type == "MESH" for obj in scene.objects):
    raise ValueError("A renderable scene requires a camera and mesh geometry")
if not any(obj.type == "LIGHT" and obj.data.energy > 0 for obj in scene.objects):
    raise ValueError("Expected a powered scene light")
options = plan["render"]
width, height = options["resolution"]
if min(width, height, options["samples"]) < 1:
    raise ValueError("Resolution and sample count must be positive")
scene.render.engine = options["engine"]
scene.render.resolution_x, scene.render.resolution_y = width, height
scene.render.resolution_percentage = 100
scene.eevee.taa_render_samples = options["samples"]
scene.cycles.samples = options["samples"]
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = "//preview.png"
if action == "build":
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "scene.blend"), compress=True)
scene.render.filepath = str(out / "preview.png")
print(f"Validated {len(scene.objects)} objects, camera {scene.camera.name}", flush=True)
bpy.ops.render.render(write_still=True)
