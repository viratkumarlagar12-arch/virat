"""Render a 3D HyperFrames scene (Three.js) to an MP4 clip you can drop into a plan as full-screen b-roll.

usage: python render3d.py <template.html> <out.mp4> [--title "..."] [--sub "..."] [--duration 6] [--draft]
                          [--config '{"mode":"spokes"}']
templates live in editor/templates/3d/

--config merges a JSON object over the template's one-line defaults `window.CFG = {...};` (using --config on a
template without that line is an error). A "duration" key also sets the root data-duration; --duration wins
over both and is written into CFG too.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ED = Path(__file__).resolve().parent.parent
CFG_RE = re.compile(r"^([ \t]*window\.CFG\s*=\s*)(\{.*\})(\s*;)[ \t]*$", re.M)


def parse_js_object(src):
    """Parse a one-line JS object literal like `{ a: 1, mode: "x" }` (JSON with bare keys). None if it can't."""
    try:
        return json.loads(src)
    except ValueError:
        pass
    q = re.sub(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', r'\1"\2":', src)
    q = re.sub(r",\s*([}\]])", r"\1", q)
    try:
        v = json.loads(q)
    except ValueError:
        return None
    return v if isinstance(v, dict) else None


def js_literal(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def apply_config(page, config, duration=None):
    """Merge `config` (dict) over the template's window.CFG defaults. Returns (page, effective duration or None)."""
    m = CFG_RE.search(page)
    if not m:
        raise SystemExit("--config: template has no `window.CFG = {...};` line")
    over = dict(config)
    if duration:
        over["duration"] = duration
    base = parse_js_object(m.group(2))
    if base is None:  # unusual literal: let the browser merge it
        lit = f"Object.assign({m.group(2)}, {js_literal(over)})"
    else:
        lit = js_literal({**base, **over})
    page = page[:m.start(2)] + lit + page[m.end(2):]
    return page, over.get("duration")


def stage(template, title=None, sub=None, duration=None, config=None):
    """Copy the template + gsap/three/fonts into a temp HyperFrames project dir; returns its path."""
    page = Path(template).read_text()
    if title:
        t = re.sub(r"\*([^*]+)\*", r'<span class="acc">\1</span>', html.escape(title))
        page = re.sub(r'(<div id="title">).*?(</div>)', lambda m: m.group(1) + t + m.group(2), page, count=1)
    if sub:
        page = re.sub(r'(<div id="sub">).*?(</div>)', lambda m: m.group(1) + html.escape(sub) + m.group(2), page, count=1)
    if config is not None or (duration and CFG_RE.search(page)):
        page, duration = apply_config(page, config or {}, duration)
    if duration:
        page = re.sub(r'data-duration="[\d.]+"', f'data-duration="{float(duration):g}"', page, count=1)
    tmp = Path(tempfile.mkdtemp(prefix="hf3d_"))
    assets = tmp / "assets"
    (assets / "fonts").mkdir(parents=True)
    shutil.copy(ED / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets)
    shutil.copy(ED / "node_modules" / "three" / "build" / "three.module.js", assets)
    shutil.copy(ED / "node_modules" / "three" / "build" / "three.core.js", assets)
    for f in (ED / "assets" / "fonts").glob("*.ttf"):
        shutil.copy(f, assets / "fonts")
    (tmp / "index.html").write_text(page)
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("out")
    ap.add_argument("--title", help='title HTML; wrap the accent word as *word*')
    ap.add_argument("--sub")
    ap.add_argument("--duration", type=float)
    ap.add_argument("--config", help="JSON object merged over the template's `window.CFG = {...};` defaults")
    ap.add_argument("--draft", action="store_true")
    a = ap.parse_args()
    config = None
    if a.config:
        try:
            config = json.loads(a.config)
        except ValueError as e:
            raise SystemExit(f"--config is not valid JSON: {e}")
        if not isinstance(config, dict):
            raise SystemExit("--config must be a JSON object")
    tmp = stage(a.template, a.title, a.sub, a.duration, config)
    try:
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
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
