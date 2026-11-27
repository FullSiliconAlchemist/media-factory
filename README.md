# Media Factory

A prompt, a project-specific JSON plan, and a reviewed Blender Python generator produce an editable scene and a PNG. Codex translates the prompt and authors the project. Scene construction runs locally without downloads or API keys.

## Reproduce NoSun

Use Python 3.9+ and Blender 4.5 LTS. From the repository root run:

```sh
python3 -m factory build projects/nosun
```

The CLI prints the new run directory under `outputs/nosun/`. A successful build contains `scene.blend`, `preview.png`, and `generation.log`. Each attempt gets a separate directory, including failures. The log records the invocation, Blender messages and exit status. The CLI searches PATH and the standard macOS Blender app location. Use `--blender /path/to/executable` or set `BLENDER_BIN` for another installation. Eevee requires working graphics access even in background mode.

Open the blend in Blender and select vessels by serial number in the Outliner. Shells, crop rosettes, console displays, pipes, lights, and camera are scene objects. Repeated components share mesh data. Use Object → Relations → Make Single User before editing the mesh of just one repeated part. Transforms are already independent. For changes to the procedural layout, edit `projects/nosun/scene.json` and build again. The project script contains the detailed asset construction.

To render the most recent completed build, or a specific manually edited file:

```sh
python3 -m factory render projects/nosun
python3 -m factory render projects/nosun --scene /path/to/edited.blend
```

Render opens the saved scene, applies the project's render settings and writes a PNG and log in a fresh run directory. Engine, width, height, and sample count come from the JSON render block. Use `BLENDER_EEVEE_NEXT` for Eevee or `CYCLES` for Cycles.

## Create another environment

1. Save the brief in `prompts/`. Ask Codex to translate it into a project-specific plan covering dimensions, assets, palette, lighting, atmosphere and camera.
2. Create `projects/<name>/scene.json` and `build.py`. Keep the render block from NoSun. The rest of the plan belongs to the individual project.
3. Implement `build(plan)` in the local script. Create mesh objects, named collections, at least one powered light and an active camera. Work in metres and seed procedural variation.
4. Review the code, run `python3 -m factory build projects/<name>`, inspect the preview and refine. Project scripts execute as local Python with Blender's permissions. Use only code you trust. The CLI accepts project directories directly under this repository's projects folder.

## NoSun reference build

The [inspected preview](outputs/nosun/20261126-215152-497923-6ad9ac/preview.png) and its [editable scene](outputs/nosun/20261126-215152-497923-6ad9ac/scene.blend) were built on Apple Silicon with Blender 4.5.0 and Eevee at 960 × 540. The 17 × 36 m hall contains four columns of six vessels. The lowered camera looks down the raised service aisle toward process control, with a suspended bay marker in the foreground.

Three builds are preserved. The first exposed a shadow-buffer limit and weak separation between grow lights and overhead lights. The second adjusted the light pools, increased the shadow buffer and added service details. The final build refined the crop meshes and connected the inner vessels to the nutrient mains. The crops remain stylized and the desert setting is conveyed by the depth signage inside the facility.
