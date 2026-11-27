"""Run a reviewed local Blender project and preserve every attempt."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "render"])
    parser.add_argument("project", type=Path)
    parser.add_argument("--blender", default=os.getenv("BLENDER_BIN"))
    parser.add_argument("--scene", type=Path, help="edited .blend to render")
    args = parser.parse_args()
    project = args.project.resolve()
    if project.parent != ROOT / "projects":
        parser.error("choose a reviewed local directory directly under projects/")
    binary = args.blender or shutil.which("blender") or "/Applications/Blender.app/Contents/MacOS/Blender"
    if not shutil.which(binary):
        parser.error("set BLENDER_BIN or pass --blender")
    config = project / "scene.json"
    script = project / "build.py"
    if not config.is_file() or not script.is_file() or config.is_symlink() or script.is_symlink():
        parser.error("project requires local scene.json and build.py files")
    runs = ROOT / "outputs" / project.name
    command = [binary, "-b", "--factory-startup", "--disable-autoexec", "-t", "4"]
    if args.action == "render":
        scenes = sorted(runs.glob("*/scene.blend"), reverse=True)
        source = args.scene or next((s for s in scenes if (s.parent / "preview.png").exists()), None)
        if source is None or not source.is_file():
            parser.error("build the project first or supply --scene")
        command.append(str(source.resolve()))
    elif args.scene:
        parser.error("--scene is for render")
    run = runs / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:6])
    run.mkdir(parents=True)
    command += ["--python-exit-code", "1", "-P", str(ROOT / "factory" / "blender_job.py"),
                "--", args.action, str(project), str(run)]
    print(run, flush=True)
    with (run / "generation.log").open("w") as log:
        print(json.dumps(command), file=log, flush=True)
        code = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT).returncode
        print(f"Blender exit code {code}", file=log)
    if code or not (run / "preview.png").is_file() or (args.action == "build" and not (run / "scene.blend").is_file()):
        sys.exit(f"Blender job failed. See {run / 'generation.log'}")


if __name__ == "__main__":
    main()
