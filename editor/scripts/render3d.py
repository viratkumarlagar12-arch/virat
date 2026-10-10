"""Render a 3D HyperFrames scene (Three.js) to an MP4 clip you can drop into a plan as full-screen b-roll.

usage: python render3d.py <template.html> <out.mp4> [--title "..."] [--sub "..."] [--duration 6] [--draft]
templates live in editor/templates/3d/
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ED = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("out")
    ap.add_argument("--title", help='title HTML; wrap the accent word as *word*')
    ap.add_argument("--sub")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="hf3d_"))
    assets = tmp / "assets"
    (assets / "fonts").mkdir(parents=True)
    shutil.copy(ED / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets)
    shutil.copy(ED / "node_modules" / "three" / "build" / "three.module.js", assets)
    shutil.copy(ED / "node_modules" / "three" / "build" / "three.core.js", assets)
    for f in (ED / "assets" / "fonts").glob("*.ttf"):
        shutil.copy(f, assets / "fonts")
    page = Path(a.template).read_text()
    if a.title:
        t = re.sub(r"\*([^*]+)\*", r'<span class="acc">\1</span>', html.escape(a.title))
        page = re.sub(r'(<div id="title">).*?(</div>)', lambda m: m.group(1) + t + m.group(2), page, count=1)
    if a.sub:
        page = re.sub(r'(<div id="sub">).*?(</div>)', lambda m: m.group(1) + html.escape(a.sub) + m.group(2), page, count=1)
    if a.duration:
        page = re.sub(r'data-duration="[\d.]+"', f'data-duration="{a.duration}"', page, count=1)
    (tmp / "index.html").write_text(page)
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}
    out = Path(a.out).resolve()
    r = subprocess.run([str(ED / "node_modules" / ".bin" / "hyperframes"), "render", "--quality",
                        "draft" if a.draft else "delivery", "--output", str(out)], cwd=tmp, capture_output=True,
                       text=True, env=env)
    tail = (r.stdout + r.stderr)[-2000:]
    if r.returncode or not out.exists():
        print(tail)
        raise SystemExit("3D render failed")
    print("\n".join(l for l in tail.splitlines() if "rendered in" in l or "capture ·" in l))
    print("wrote", out)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
