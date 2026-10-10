"""Build a finished Short from an edit plan.

  projects/<name>/plan.json  (written by me after watching the video + reading the transcript)
  + work/analysis.json, work/transcript.json  (from analyze.py / transcribe.py)
  -> jump-cuts, 9:16 face-centred reframe, colour grade        (ffmpeg)
  -> captions, cards, charts, b-roll, zooms, hook, CTA          (HyperFrames HTML -> Chrome render)
  -> voice clean-up, music bed with ducking, SFX, -14 LUFS      (mix.py)
  -> projects/<name>/out/<name>_vN.mp4

usage: python build.py projects/<name> [--draft] [--no-render] [--version N]
Times in plan.json are SOURCE seconds (as in transcript.txt) unless the key is t_out.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mix as mixmod  # noqa: E402
import music as musicmod  # noqa: E402

ED = Path(__file__).resolve().parent.parent
FONTS = ED / "assets" / "fonts"
SFXDIR = ED / "assets" / "sfx"
HF_BIN = ED / "node_modules" / ".bin" / "hyperframes"
W, H, FPS = 1080, 1920, 30
UI_TOP, UI_BOTTOM = 150, 1580  # keep text out of the Shorts UI (search bar / title + buttons)

THEMES = {
    # dark cards, heavy type, yellow keywords — Hormozi / Warikoo-energy explainer
    "bold": {
        "fonts": {"Montserrat": [800, 900], "Poppins": [600, 700, 800]},
        "active": "#FFD60A",
        "vars": {"--ui-font": '"Poppins"', "--head-font": '"Montserrat"', "--head-weight": "900",
                 "--cap-font": '"Montserrat"', "--cap-weight": "900", "--cap-color": "#FFFFFF",
                 "--cap-stroke": "13px", "--cap-stroke-color": "#000000", "--accent": "#FFD60A",
                 "--accent-strong": "#FFD60A", "--card-bg": "rgba(16,16,20,0.94)", "--card-fg": "#FFFFFF",
                 "--card-muted": "#A1A1AA", "--good": "#16A34A", "--hot": "#FF453A", "--vignette": "0.35"},
    },
    # Apple-style: white cards, Inter, blue accent, clean captions
    "clean": {
        "fonts": {"Inter": [500, 600, 700, 800, 900]},
        "active": "#FFD60A",
        "vars": {"--ui-font": '"Inter"', "--head-font": '"Inter"', "--head-weight": "800",
                 "--cap-font": '"Inter"', "--cap-weight": "800", "--cap-color": "#FFFFFF",
                 "--cap-stroke": "9px", "--cap-stroke-color": "rgba(0,0,0,0.85)", "--accent": "#FFD60A",
                 "--accent-strong": "#0A84FF", "--card-bg": "rgba(255,255,255,0.96)", "--card-fg": "#1D1D1F",
                 "--card-muted": "#6E6E73", "--good": "#34C759", "--hot": "#FF3B30", "--vignette": "0.25"},
    },
    # Hinglish explainer: Poppins captions, white cards, red/yellow accents
    "desi": {
        "fonts": {"Poppins": [600, 700, 800, 900], "Mukta": [700, 800]},
        "active": "#FFD60A",
        "vars": {"--ui-font": '"Poppins"', "--head-font": '"Poppins"', "--head-weight": "900",
                 "--cap-font": '"Poppins"', "--cap-weight": "800", "--cap-color": "#FFFFFF",
                 "--cap-stroke": "12px", "--cap-stroke-color": "#000000", "--accent": "#FFD60A",
                 "--accent-strong": "#E5162B", "--card-bg": "rgba(255,255,255,0.97)", "--card-fg": "#111111",
                 "--card-muted": "#5B5B66", "--good": "#16A34A", "--hot": "#E5162B", "--vignette": "0.3"},
    },
}

GRADES = {
    "none": "",
    "natural": "eq=contrast=1.03:saturation=1.08,unsharp=5:5:0.35",
    # low-res sources (480p/720p) blown up to 1080x1920: a little more contrast and detail
    "upscale": "eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.75:3:3:0.3",
    "punchy": "eq=contrast=1.08:saturation=1.16:gamma=0.98,unsharp=5:5:0.5",
    "warm": "colorbalance=rs=0.04:bs=-0.04:rm=0.02:bm=-0.03,eq=contrast=1.05:saturation=1.1,unsharp=5:5:0.35",
    "cinematic": "colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.03,eq=contrast=1.08:saturation=1.04:gamma=0.97,unsharp=5:5:0.4",
}

DEFAULT_SFX = {"hook": "impact", "card": "whoosh", "stat": "whoosh", "bars": "whoosh", "list": "swoosh",
               "compare": "whoosh", "emoji": "bubble", "image": "whoosh", "video": "whoosh",
               "lower_third": "swoosh", "countdown": None, "cta": "pop", "text_slam": "impact", "flash": "camera",
               "sundial": "whoosh", "ring": "pop", "stamp": "impact", "hand": None, "flare": None, "note10": None,
               "fade": None}
OVERLAY_ONLY = {"emoji", "flash", "hand", "ring", "flare", "note10", "fade"}  # drawn on the footage; don't take a layout zone


# ----------------------------------------------------------------------------- helpers
def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"command failed: {cmd[0]} {cmd[1] if len(cmd) > 1 else ''}")
    return r


def snap(t):
    return round(t * FPS) / FPS


class TimeMap:
    """source time <-> output time across the jump cuts"""

    def __init__(self, keep):
        self.segs, o = [], 0.0
        for s, e in keep:
            self.segs.append((s, e, o))
            o += e - s
        self.duration = o

    def out(self, t):
        for s, e, o in self.segs:
            if t < s:
                return o  # inside a removed gap -> the cut point
            if t <= e:
                return o + (t - s)
        return self.duration

    def inside(self, t):
        return any(s <= t <= e for s, e, _ in self.segs)

    def cut_points(self):
        return [o for _, _, o in self.segs[1:]]


def merge(ranges, gap=0.0):
    out = []
    for s, e in sorted(ranges):
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def subtract(ranges, cuts):
    out = []
    for s, e in ranges:
        pieces = [[s, e]]
        for cs, ce in cuts:
            nxt = []
            for a, b in pieces:
                if ce <= a or cs >= b:
                    nxt.append([a, b])
                else:
                    if cs > a:
                        nxt.append([a, cs])
                    if ce < b:
                        nxt.append([ce, b])
            pieces = nxt
        out += pieces
    return out


# ----------------------------------------------------------------------------- words & cuts
def load_words(proj, plan):
    tr = json.loads((proj / "work" / "transcript.json").read_text())
    words = [dict(w) for w in tr["words"]]
    fix = {int(k): v for k, v in plan.get("word_text", {}).items()}
    for w in words:
        w["text"] = fix.get(w["i"], w["w"])
    return words


def keep_ranges(words, plan, duration):
    c = plan.get("cuts", {})
    drop = set(c.get("remove_words", []))
    if c.get("auto", True):
        pre, post, gap = c.get("pre", 0.08), c.get("post", 0.14), c.get("max_pause", 0.22)
        spans = [[max(0, w["start"] - pre), min(duration, w["end"] + post)] for w in words if w["i"] not in drop]
        keep = merge(spans, gap)
    else:
        keep = [[0, duration]]
    removed = [list(r) for r in c.get("remove", [])]
    removed += [[words[i]["start"] - 0.02, words[i]["end"] + 0.02] for i in drop if i < len(words)]
    keep = subtract(keep, removed)
    if "trim" in c:
        a, b = c["trim"]
        keep = [[max(s, a), min(e, b)] for s, e in keep if e > a and s < b]
    keep = [[snap(s), snap(e)] for s, e in keep]
    return [(s, e) for s, e in keep if e - s >= 0.15]


# ----------------------------------------------------------------------------- reframe + base render
def crop_plan(info, analysis, keep, plan):
    sw, sh = info["width"], info["height"]
    zoom = plan.get("reframe", {}).get("zoom", 1.0)
    if sw / sh > 9 / 16:  # wider than 9:16 -> crop width, follow the face per segment
        ch = sh / zoom
        cw = ch * 9 / 16
    else:
        cw = sw / zoom
        ch = cw * 16 / 9
    cw, ch = int(cw) // 2 * 2, int(ch) // 2 * 2
    track = [r for r in analysis.get("face_track", []) if r["box"]]
    face = analysis.get("face") or {}
    gcx = face.get("center_x", 0.5) * sw
    gcy = (face.get("median_box", [0, 0.3, 0, 0.2])[1] + face.get("median_box", [0, 0.3, 0, 0.2])[3] / 2) * sh
    crops = []
    for s, e in keep:
        pts = [r["box"] for r in track if s - 0.2 <= r["t"] <= e + 0.2]
        cx = np.median([(b[0] + b[2] / 2) * sw for b in pts]) if pts else gcx
        cy = np.median([(b[1] + b[3] / 2) * sh for b in pts]) if pts else gcy
        x = int(np.clip(cx - cw / 2, 0, sw - cw))
        # keep the face in the upper-middle third when we are cropping vertically too
        y = int(np.clip(cy - ch * 0.38, 0, sh - ch)) if ch < sh else 0
        crops.append((x, y))
    return cw, ch, crops


def render_base(src, info, keep, cw, ch, crops, grade, work):
    # crop x/y follow the face per kept segment (evaluated on source time t before frame selection)
    def piecewise(vals):
        expr = str(vals[-1])
        for (s, e), v in reversed(list(zip(keep[:-1], vals[:-1]))):
            expr = f"if(lt(t,{e + 0.05:.3f}),{v},{expr})"
        return expr

    xs, ys = [c[0] for c in crops], [c[1] for c in crops]
    sel = "+".join(f"between(n,{int(round(s * FPS))},{int(round(e * FPS)) - 1})" for s, e in keep)
    vf = [f"fps={FPS}", f"crop={cw}:{ch}:'{piecewise(xs)}':'{piecewise(ys)}'",
          f"scale={W}:{H}:flags=lanczos", "setsar=1"]
    if GRADES.get(grade):
        vf.append(GRADES[grade])
    vf += [f"select='{sel}'", f"setpts=N/{FPS}/TB", "format=yuv420p"]
    (work / "base_vf.txt").write_text(",".join(vf))
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_script:v", work / "base_vf.txt", "-an",
         "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", str(FPS), "-r", str(FPS), work / "base.mp4"])
    # voice: same cuts, 6 ms fades at every joint so cuts never click
    a, sr = sf.read(work / "voice48k.wav", dtype="float32")
    fade = int(0.006 * sr)
    parts = []
    for s, e in keep:
        seg = a[int(round(s * sr)) : int(round(e * sr))].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        parts.append(seg)
    sf.write(work / "voice_cut.wav", np.concatenate(parts), sr, subtype="PCM_24")


# ----------------------------------------------------------------------------- layout
def face_out_box(info, analysis, cw, ch, crops):
    """protected face region in output pixels (union over segments, with hair/chin margins)"""
    f = analysis.get("face")
    if not f:
        return [W * 0.3, H * 0.22, W * 0.7, H * 0.48]
    sw, sh = info["width"], info["height"]
    zx, zy, zw, zh = f["face_zone"]
    boxes = []
    for x, y in crops:
        x0 = (zx * sw - x) * W / cw
        x1 = ((zx + zw) * sw - x) * W / cw
        y0 = (zy * sh - y) * H / ch
        y1 = ((zy + zh) * sh - y) * H / ch
        boxes.append([x0, y0, x1, y1])
    b = np.array(boxes)
    x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
    fh = y1 - y0
    return [max(0, x0 - 0.12 * fh), max(0, y0 - 0.22 * fh), min(W, x1 + 0.12 * fh), min(H, y1 + 0.12 * fh)]


def zoomed(box, origin, s):
    ox, oy = origin
    return [ox + (box[0] - ox) * s, oy + (box[1] - oy) * s, ox + (box[2] - ox) * s, oy + (box[3] - oy) * s]


def make_layout(face, origin, max_zoom, cap_size, plan):
    fz = zoomed(face, origin, max_zoom)
    half = cap_size * 1.35  # two caption lines
    cy = plan.get("captions", {}).get("y")
    if cy is None:
        cy = max(1330, fz[3] + half + 30)
        if cy + half > UI_BOTTOM:  # face too low: captions go above the head
            cy = max(UI_TOP + half, fz[1] - half - 30)
    low_cy = max(cy, UI_BOTTOM - half)  # where captions drop to while a big graphic uses the body zone
    top = [UI_TOP, max(UI_TOP, fz[1] - 30)]
    if cy > fz[3]:
        lower = [fz[3] + 30, cy - half - 24]
        body = [fz[3] + 30, low_cy - half - 24]
    else:
        lower = body = [cy + half + 24, UI_BOTTOM]
    return {"face": [round(v) for v in fz], "caption_y": round(cy), "caption_y_low": round(low_cy), "zones": {
        "top": [round(v) for v in top], "lower": [round(v) for v in lower], "body": [round(v) for v in body],
        "center": [UI_TOP, UI_BOTTOM], "full": [0, H]}}


# natural height (px) each graphic needs to render without shrinking
NEED = {"bars": 420, "list": 360, "compare": 220, "image": 420, "video": 420, "card": 210, "stat": 300,
        "sundial": 540, "stamp": 280,
        "hook": 240, "cta": 230, "countdown": 400, "lower_third": 140, "text_slam": 300}


def pick_zone(o, layout):
    z = o.get("zone", "auto")
    if isinstance(z, list):
        return "custom", z
    if z == "auto" and o["type"] == "text_slam":
        z = "center"
    if z != "auto":
        return z, layout["zones"][z]
    zs = layout["zones"]
    need = NEED.get(o["type"], 240)
    h = {k: v[1] - v[0] for k, v in zs.items()}
    if h["top"] >= need:
        return "top", zs["top"]
    if h["lower"] >= need:
        return "lower", zs["lower"]
    best = max(("top", "lower", "body"), key=lambda k: h[k])
    return best, zs[best]


# ----------------------------------------------------------------------------- captions
NUM_RE = re.compile(r"[\d₹$%]|lakh|lac|crore|cr\b|k\b|million|billion", re.I)


def caption_chunks(words, tm, plan, layout, overlays_c):
    cc = plan.get("captions", {})
    if cc.get("off"):
        return []
    hide = set(cc.get("hide_words", [])) | set(plan.get("cuts", {}).get("remove_words", []))
    hl = set(cc.get("highlight", []))
    kw = [k.lower() for k in cc.get("keywords", [])]
    breaks = set(cc.get("breaks", []))
    emoji = {int(k): v for k, v in cc.get("emoji", {}).items()}
    max_w, max_c = cc.get("max_words", 3), cc.get("max_chars", 18)
    strip = re.compile(r"^[\"'“”‘’(\[]+|[\"'“”‘’)\],.;:।]+$")
    seq = []
    for w in words:
        if w["i"] in hide or not tm.inside((w["start"] + w["end"]) / 2):
            continue
        txt = strip.sub("", w["text"]).strip()
        if not txt:
            continue
        t0, t1 = tm.out(w["start"]), tm.out(w["end"])
        is_hl = w["i"] in hl or bool(NUM_RE.search(txt)) or txt.lower().strip("?!") in kw
        seq.append({"i": w["i"], "text": txt, "t0": t0, "t1": max(t1, t0 + 0.08), "hl": is_hl,
                    "end_punct": bool(re.search(r"[.?!।,]$", w["text"]))})
        if w["i"] in emoji:
            seq.append({"i": w["i"], "text": emoji[w["i"]], "t0": t0 + 0.05, "t1": t1, "hl": False, "end_punct": False,
                        "emoji": True})
    chunks, cur = [], []
    for k, w in enumerate(seq):
        if cur:
            chars = sum(len(x["text"]) + 1 for x in cur) + len(w["text"])
            gap = w["t0"] - cur[-1]["t1"]
            if (len(cur) >= max_w and not w.get("emoji")) or chars > max_c + (3 if w.get("emoji") else 0) \
                    or gap > 0.35 or cur[-1]["end_punct"] or w["i"] in breaks:
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    body = [(o["t"], o["t"] + o["dur"]) for o in overlays_c if o.get("zone_name") == "body"]
    stop = tm.out(cc["until"]) if "until" in cc else tm.duration  # e.g. no captions on a channel end card
    out = []
    for k, ch in enumerate(chunks):
        t0 = ch[0]["t0"]
        if t0 >= stop:
            break
        nxt = chunks[k + 1][0]["t0"] if k + 1 < len(chunks) else tm.duration
        t1 = min(nxt, ch[-1]["t1"] + 0.45, stop)
        low = any(t0 < b1 and t1 > b0 for b0, b1 in body)
        out.append({"t0": round(t0, 3), "t1": round(max(t1, t0 + 0.25), 3),
                    "y": layout["caption_y_low"] if low else layout["caption_y"],
                    "words": [{"text": w["text"], "t0": round(w["t0"], 3), "t1": round(w["t1"], 3), "hl": w["hl"]}
                              for w in ch]})
    return out


# ----------------------------------------------------------------------------- time anchors
def anchor(o, words, tm, key="t", wkey="w"):
    if f"{key}_out" in o:
        return float(o[f"{key}_out"])
    if wkey in o:
        w = words[int(o[wkey])]
        return tm.out(w["start"]) + o.get("dt", 0.0)
    if key in o:
        return tm.out(float(o[key])) + o.get("dt", 0.0)
    raise SystemExit(f"overlay needs t, t_out or w: {o}")


def end_of(o, start, words, tm):
    if "until_w" in o:
        return tm.out(words[int(o["until_w"])]["end"]) + 0.35
    if "until" in o:
        return tm.out(float(o["until"]))
    return start + float(o.get("dur", 2.5))


# ----------------------------------------------------------------------------- camera
def camera_events(tm, plan, words, overlays_c):
    cam = plan.get("camera", {})
    cut_zoom = cam.get("cut_zoom", 1.08)
    punch = cam.get("punch", 1.12)
    events, scale = [], 1.0
    windows = []  # (t0, t1) of punches
    for p in cam.get("punches", []):
        t0 = anchor(p, words, tm)
        hold = p.get("hold", 1.2)
        windows.append((t0, t0 + hold + 0.35, p))
    full = [(o["t"], o["t"] + o["dur"]) for o in overlays_c if o.get("mode") == "full" or o["type"] == "text_slam"]

    seg_bounds = [0.0] + tm.cut_points() + [tm.duration]
    for k in range(len(seg_bounds) - 1):
        a, b = seg_bounds[k], seg_bounds[k + 1]
        if k > 0 and cam.get("alternate", True) and not any(w0 <= a <= w1 for w0, w1, _ in windows):
            scale = cut_zoom if scale == 1.0 else 1.0
            events.append({"t": round(a, 3), "scale": scale, "dur": 0})
        # slow push on long takes so the frame never sits still
        if b - a > 3.0 and cam.get("drift", True):
            inside = [w for w in windows if a <= w[0] < b]
            end = min([w[0] for w in inside] + [b]) - 0.02
            if end - a > 2.0:
                events.append({"t": round(a + 0.02, 3), "scale": round(scale * 1.035, 4), "dur": round(end - a - 0.04, 3),
                               "ease": "none"})
                scale = round(scale * 1.035, 4)
    for t0, t1, p in windows:
        base = next((e["scale"] for e in reversed(events) if e["t"] <= t0), 1.0)
        target = min(1.32, base * p.get("scale", punch))
        events.append({"t": round(t0, 3), "scale": round(target, 4), "dur": p.get("in", 0.16), "ease": "power3.out"})
        events.append({"t": round(t1 - 0.35, 3), "scale": round(base, 4), "dur": 0.35, "ease": "power2.inOut"})
    # explicit per-shot moves for assembled montages: {"t_out": 1.0, "from": 1.0, "scale": 1.12, "dur": 1.9,
    # "ease": "none", "origin": [x, y]} — origin changes only on a cut (scale is reset with "from")
    for kf in cam.get("keyframes", []):
        t0 = anchor(kf, words, tm)
        if "from" in kf or "origin" in kf:
            ev = {"t": round(t0, 3), "scale": kf.get("from", kf.get("scale", 1.0)), "dur": 0}
            if "origin" in kf:
                ev["origin"] = kf["origin"]
            events.append(ev)
        if kf.get("dur"):
            events.append({"t": round(t0 + 0.001, 3), "scale": kf["scale"], "dur": kf["dur"], "ease": kf.get("ease", "none")})
    for s in cam.get("shakes", []):
        t0 = anchor(s, words, tm)
        events.append({"t": round(t0, 3), "type": "shake", "dur": s.get("dur", 0.35), "amp": s.get("amp", 14)})
        events.append({"t": round(t0 - 0.001, 3), "scale": 1.1, "dur": 0})  # zoomed so shake shows no edges
    events.sort(key=lambda e: e["t"])
    max_zoom = max([1.0] + [e.get("scale", 1.0) for e in events])
    return events, max_zoom


# ----------------------------------------------------------------------------- overlays
def compile_overlays(plan, words, tm, layout, media_dir, verbose=False):
    out, sfx, media_html = [], [], []
    for n, o in enumerate(plan.get("overlays", [])):
        o = dict(o)
        typ = o["type"]
        t0 = anchor(o, words, tm)
        t1 = end_of(o, t0, words, tm)
        if typ == "countdown":
            t1 = t0 + o.get("n", 3) + 0.3
        if typ == "flash":
            t1 = t0 + 0.35
        if typ == "fade":
            t1 = t0 + o.get("in", 0.3) + o.get("hold", 0) + o.get("out", 0.3)
        o["t"], o["dur"] = round(t0, 3), round(max(0.4, t1 - t0), 3)
        if typ in ("image", "video"):
            o["mode"] = o.get("mode", "pip")
        if o.get("mode") == "full" or typ in OVERLAY_ONLY - {"emoji"}:
            o["zone_name"], o["zone"] = "full", layout["zones"]["full"]
        else:
            o["zone_name"], o["zone"] = pick_zone(o, layout)
        # named moments inside an overlay, e.g. "times": {"shadow": {"w": 55}} -> o["t_shadow"]
        for key, at in o.pop("times", {}).items():
            o[f"t_{key}"] = round(anchor(at, words, tm), 3)
        # sub-item timing
        if typ == "bars":
            for k, it in enumerate(o["items"]):
                it["t"] = round(anchor(it, words, tm) if ("w" in it or "t_out" in it) else t0 + 0.35 + 0.22 * k, 3)
                sfx.append({"t": it["t"], "name": "bubble"})
        if typ == "list":
            for k, it in enumerate(o["items"]):
                it["t"] = round(anchor(it, words, tm) if ("w" in it or "t_out" in it) else t0 + 0.4 + 0.35 * k, 3)
                sfx.append({"t": it["t"], "name": "pop"})
        if typ == "compare" and "b" in o and ("w" in o["b"] or "t" in o["b"]):
            o["t_b"] = round(anchor(o["b"], words, tm), 3)
            sfx.append({"t": o["t_b"], "name": "whoosh"})
        if typ == "stat":
            sfx.append({"t": o["t"] + 0.1 + o.get("count_dur", 1.0), "name": o.get("end_sfx", "cash")})
        if typ == "countdown":
            for k in range(o.get("n", 3)):
                sfx.append({"t": o["t"] + k, "name": "tick"})
            sfx.append({"t": o["t"] + o.get("n", 3), "name": "ding"})
        if typ == "hand" and o.get("style", "glow") == "glow" and o.get("tick_sfx", True):
            steps = o.get("steps") or max(1, round(o["dur"] / 0.5))
            for k in range(steps):
                sfx.append({"t": round(o["t"] + k * (o["dur"] - 0.2) / steps, 3), "name": "tick", "gain_db": -3})
        if typ == "note10":
            for key, name, g in (("t_wheel", "whoosh", 0), ("t_card", "pop", 0), ("t_label", "cash", -2),
                                 ("t_flip", "swoosh", 0), ("t_zoom", "whoosh", -1)):
                if key in o:
                    sfx.append({"t": o[key], "name": name, "gain_db": g})
        if typ == "cta":
            sfx.append({"t": o["t"] + 1.0, "name": "click"})
            sfx.append({"t": o["t"] + 1.1, "name": "success", "gain_db": -3})
        if typ == "hook":
            o["words"], acc = [], False
            for tok in o["text"].split():
                start = tok.startswith("*")
                acc = acc or start
                o["words"].append({"w": tok.strip("*"), "acc": acc})
                if tok.endswith("*") and (len(tok) > 1 or not start):
                    acc = False
        if typ == "emoji":
            fz = layout["face"]
            side = o.get("side", "right")
            o.setdefault("x", min(W - 150, fz[2] + 110) if side == "right" else max(150, fz[0] - 110))
            o.setdefault("y", max(UI_TOP + 120, fz[1] + 60))
        if typ in ("image", "video"):
            src = Path(o["src"]).expanduser()
            if not src.is_absolute():
                src = (Path(plan["_proj"]) / src).resolve()
            dst = media_dir / f"m{n}{src.suffix.lower()}"
            shutil.copy(src, dst)
            o["src"] = f"assets/media/{dst.name}"
            o["el_id"] = f"ov{n}"
            cls = "full" if o["mode"] == "full" else "pip"
            if typ == "video":
                inner = (f'<video id="bv{n}" class="clip" src="{o["src"]}" muted playsinline data-start="{o["t"]}" '
                         f'data-duration="{o["dur"]}" data-media-start="{o.get("media_start", 0)}" data-track-index="{3 + n % 3}"></video>')
            else:
                inner = f'<img src="{o["src"]}" alt="" />'
            capd = f'<div class="cap">{o["caption"]}</div>' if o.get("caption") and cls == "pip" else ""
            layer = "broll" if cls == "full" else "overlays"
            media_html.append((layer, f'<div class="{cls}" id="ov{n}"><div class="kb" style="position:absolute;inset:0">{inner}</div>{capd}</div>'))
        snd = o.get("sfx", DEFAULT_SFX.get(typ))
        if typ in ("image", "video") and o.get("mode") == "full":
            snd = o.get("sfx", "swoosh")
        if snd and snd != "none":
            sfx.append({"t": o["t"], "name": snd})
            if typ == "hook":
                sfx.append({"t": o["t"] + 0.02, "name": "whoosh", "gain_db": -4})
        out.append(o)
    # one graphic per zone at a time: an earlier one leaves just as the next one arrives
    solo = [o for o in out if o["type"] not in OVERLAY_ONLY and o.get("mode") != "full"]
    solo.sort(key=lambda o: o["t"])
    for a, b in zip(solo, solo[1:]):
        za, zb = a["zone"], b["zone"]
        if za[0] < zb[1] and zb[0] < za[1] and b["t"] < a["t"] + a["dur"]:
            new = round(max(0.6, b["t"] - a["t"]), 3)
            if verbose:
                print(f"  note: {a['type']}@{a['t']:.2f} shortened {a['dur']:.2f}->{new:.2f}s (next: {b['type']}@{b['t']:.2f})")
            a["dur"] = new
    for o in out:  # nothing runs past the end of the video
        if o["t"] + o["dur"] > tm.duration:
            o["dur"] = round(max(0.6, tm.duration - o["t"]), 3)
    return out, sfx, media_html


# ----------------------------------------------------------------------------- HyperFrames project
def font_faces(theme):
    css, loads = [], []
    for fam, weights in THEMES[theme]["fonts"].items():
        for wgt in weights:
            f = FONTS / f"{fam}-{wgt}.ttf"
            if f.exists():
                css.append(f'@font-face {{ font-family: "{fam}"; src: url("assets/fonts/{f.name}") format("truetype"); '
                           f'font-weight: {wgt}; font-display: block; }}')
                loads.append(f'{wgt} 40px "{fam}"')
    css.append('@font-face { font-family: "Noto Color Emoji"; src: url("assets/fonts/NotoColorEmoji.ttf"); }')
    loads.append('40px "Noto Color Emoji"')
    return "\n".join(css), loads


def write_hf(hfdir, edit, theme, media_html):
    assets = hfdir / "assets"
    (assets / "fonts").mkdir(parents=True, exist_ok=True)
    for fam, weights in THEMES[theme]["fonts"].items():
        for wgt in weights:
            f = FONTS / f"{fam}-{wgt}.ttf"
            if f.exists():
                shutil.copy(f, assets / "fonts" / f.name)
    emoji = Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf")
    if emoji.exists():
        shutil.copy(emoji, assets / "fonts" / emoji.name)
    shutil.copy(ED / "node_modules" / "gsap" / "dist" / "gsap.min.js", assets / "gsap.min.js")
    shutil.copy(ED / "templates" / "runtime.js", assets / "runtime.js")
    faces, loads = font_faces(theme)
    edit["fonts"] = loads
    css = (ED / "templates" / "style.css").read_text()
    layers = {"broll": "", "overlays": ""}
    for layer, html in media_html:
        layers[layer] += "\n    " + html
    d = edit["duration"]
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<title>{edit['name']}</title>
<script src="assets/gsap.min.js"></script>
<style>
{faces}
{css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{d:.3f}" data-width="{W}" data-height="{H}">
  <div id="cam"><video id="aroll" class="clip" src="assets/base.mp4" muted playsinline data-start="0" data-duration="{d:.3f}" data-track-index="0"></video></div>
  <div id="grade"></div>
  <div id="broll">{layers['broll']}
  </div>
  <div id="overlays">{layers['overlays']}
  </div>
  <div id="captions"></div>
  <div id="fx"></div>
</div>
<script>window.EDIT = {json.dumps(edit, ensure_ascii=False)};</script>
<script src="assets/runtime.js"></script>
<script>
  // measure text only after fonts load; register the timeline once it is fully built
  Promise.all(window.EDIT.fonts.map((f) => document.fonts.load(f))).then(() => {{
    window.__timelines["main"] = window.__buildEdit();
  }});
</script>
</body>
</html>
"""
    (hfdir / "index.html").write_text(html)
    (hfdir / "hyperframes.json").write_text(json.dumps({"paths": {"assets": "assets"}, "media": {"autoProxy": True}}, indent=2))


def hf(args, cwd, timeout=3600):
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}
    return subprocess.run([str(HF_BIN), *args], cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--draft", action="store_true", help="fast low-quality render")
    ap.add_argument("--no-render", action="store_true", help="only build the HyperFrames project")
    ap.add_argument("--remix", action="store_true",
                    help="audio-only change (music/SFX/levels): reuse the last picture render, redo the mix + encode")
    ap.add_argument("--version", type=int)
    args = ap.parse_args()
    proj = Path(args.project).resolve()
    work, out_dir = proj / "work", proj / "out"
    out_dir.mkdir(exist_ok=True)
    plan = json.loads((proj / "plan.json").read_text())
    plan["_proj"] = str(proj)
    analysis = json.loads((work / "analysis.json").read_text())
    info = analysis["info"]
    name = plan.get("name", proj.name)
    theme = plan.get("theme", "bold")

    words = load_words(proj, plan)
    keep = keep_ranges(words, plan, info["duration"])
    tm = TimeMap(keep)
    print(f"cuts: {len(keep)} segments, {info['duration']:.1f}s -> {tm.duration:.1f}s")

    cw, ch, crops = crop_plan(info, analysis, keep, plan)
    if not (args.remix and (work / "base.mp4").exists()):  # the picture is reused as-is on --remix
        render_base(analysis["source"], info, keep, cw, ch, crops, plan.get("grade", "natural"), work)
    lay = plan.get("layout", {})
    if lay.get("face") == "none":  # faceless video (b-roll + voiceover): graphics above centre, zoom from centre
        face, origin = [W / 2, lay.get("graphics_bottom", 760)] * 2, [W // 2, H // 2]
    else:
        face = lay.get("face") or face_out_box(info, analysis, cw, ch, crops)
        origin = [round((face[0] + face[2]) / 2), round(face[1] + (face[3] - face[1]) * 0.55)]
    origin = plan.get("camera", {}).get("origin", origin)

    hfdir = proj / "hf"
    if hfdir.exists():
        shutil.rmtree(hfdir)
    (hfdir / "assets" / "media").mkdir(parents=True)

    # first pass with a provisional layout to know overlay windows, then camera, then final layout
    cap_size = plan.get("captions", {}).get("size", 84)
    layout = make_layout(face, origin, plan.get("camera", {}).get("max_zoom_guess", 1.2), cap_size, plan)
    overlays_c, sfx, media_html = compile_overlays(plan, words, tm, layout, hfdir / "assets" / "media")
    cam_events, max_zoom = camera_events(tm, plan, words, overlays_c)
    layout = make_layout(face, origin, max_zoom, cap_size, plan)
    overlays_c, sfx, media_html = compile_overlays(plan, words, tm, layout, hfdir / "assets" / "media", verbose=True)
    chunks = caption_chunks(words, tm, plan, layout, overlays_c)

    for s in plan.get("sfx", []):
        sfx.append({"t": anchor(s, words, tm), "name": s["name"], "gain_db": s.get("gain_db", 0)})
    if plan.get("camera", {}).get("punch_sfx"):
        for e in cam_events:
            if e.get("dur") and e.get("ease") == "power3.out":
                sfx.append({"t": e["t"], "name": plan["camera"]["punch_sfx"], "gain_db": -4})
    sfx.sort(key=lambda e: e["t"])

    th = THEMES[theme]
    cc = plan.get("captions", {})
    edit = {
        "name": name, "duration": round(tm.duration, 3), "fps": FPS,
        "theme": {"vars": {**th["vars"], **plan.get("theme_vars", {})}, "active": cc.get("active", th["active"])},
        "camera": {"origin": origin, "events": cam_events},
        "captions": {"style": cc.get("style", "pop"), "size": cap_size, "uppercase": cc.get("uppercase", theme == "bold"),
                     "chunks": chunks},
        "overlays": overlays_c,
        "progress": plan.get("progress_bar", True),
        "vignette": th["vars"]["--vignette"],
    }
    shutil.copy(work / "base.mp4", hfdir / "assets" / "base.mp4")
    write_hf(hfdir, edit, theme, media_html)
    (work / "layout.json").write_text(json.dumps({"layout": layout, "face": face, "origin": origin, "keep": keep,
                                                   "max_zoom": max_zoom, "sfx": sfx}, indent=1))
    summary = [f"duration {tm.duration:.2f}s  segments {len(keep)}  max zoom {max_zoom:.2f}",
               f"face(out px) {[round(v) for v in face]}  caption_y {layout['caption_y']}  zones {layout['zones']}"]
    summary += [f"  {o['t']:6.2f}-{o['t'] + o['dur']:6.2f} {o['type']:<11} zone={o['zone_name']} {o['zone']}" for o in overlays_c]
    summary += [f"  cap {c['t0']:6.2f}-{c['t1']:6.2f} " + " ".join(w["text"] for w in c["words"]) for c in chunks]
    (work / "edit_summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary[:2]))

    lint = hf(["lint"], hfdir)
    print(lint.stdout[-1500:])
    if args.no_render:
        return

    # ---- music + mix
    mcfg = plan.get("music", {"mood": "upbeat"})
    music_path = None
    if mcfg and mcfg.get("file"):
        music_path = Path(mcfg["file"]).expanduser()
        if not music_path.is_absolute():
            music_path = proj / music_path
    elif mcfg and mcfg.get("mood"):
        music_path = work / "music.wav"
        bed, bpm = musicmod.compose(mcfg["mood"], tm.duration, mcfg.get("bpm"), mcfg.get("seed", 3))
        sf.write(music_path, bed, musicmod.SR, subtype="PCM_16")
    mixmod.mix(work / "voice_cut.wav", work / "final_audio.wav", music_path, mcfg or {}, sfx, tm.duration, work)

    # ---- render picture
    v = args.version or (1 + max([int(m.group(1)) for p in out_dir.glob(f"{name}_v*.mp4")
                                  if (m := re.search(r"_v(\d+)\.mp4$", p.name))] + [0]))
    silent = work / "render_silent.mp4"
    if args.remix:
        got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    str(silent)], capture_output=True, text=True).stdout or 0) if silent.exists() else 0
        if abs(got - tm.duration) > 1.5 / FPS:
            raise SystemExit(f"--remix needs a picture render of {tm.duration:.2f}s in {silent} (found {got:.2f}s)")
        print("remix: reusing the last picture render")
    else:
        q = "draft" if args.draft else "delivery"
        print(f"rendering ({q}) ...")
        r = hf(["render", "--quality", q, "--output", str(silent)], hfdir)
        tail = (r.stdout + r.stderr)[-2500:]
        if r.returncode or not silent.exists():
            print(tail)
            raise SystemExit("render failed")
        print("\n".join(l for l in tail.splitlines() if "rendered in" in l or "capture ·" in l))
    final = out_dir / f"{name}_v{v}.mp4"
    # final encode at YouTube's recommended 1080p bitrate range (the render itself is near-lossless and huge)
    run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", work / "final_audio.wav", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
         "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-shortest", "-movflags", "+faststart", final])
    print(f"DONE -> {final}")
    if final.stat().st_size > 29 * 2 ** 20:  # chat/file delivery caps at 30 MiB: make a 2-pass copy that fits
        upload = final.with_name(final.stem + "_upload.mp4")
        vbit = int((27.5 * 2 ** 20 * 8 / tm.duration - 192_000) / 1000)
        common = ["-c:v", "libx264", "-preset", "slow", "-b:v", f"{vbit}k", "-maxrate", f"{int(vbit * 1.4)}k",
                  "-bufsize", f"{vbit * 2}k", "-passlogfile", str(work / "x264pass")]
        run(["ffmpeg", "-v", "error", "-y", "-i", final, *common, "-pass", "1", "-an", "-f", "mp4", "/dev/null"])
        run(["ffmpeg", "-v", "error", "-y", "-i", final, *common, "-pass", "2", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", upload])
        print(f"upload copy ({upload.stat().st_size / 2 ** 20:.1f} MiB) -> {upload}")


if __name__ == "__main__":
    main()
