"""Masterclass step 2.1 — index your own b-roll library once, reuse it in every edit.

1) scan:   python broll_index.py scan <folder> [--me my_photo.jpg]
   -> <folder>/_index/clip_list.csv  (one row per clip: duration, orientation, faces, "is it me?")
   -> <folder>/_index/sheet_XX.jpg   (3 frames per clip, numbered — I look at these and fill in
                                       category / description / tags in the CSV)
2) organize: python broll_index.py organize <folder>
   -> copies clips into numbered category folders ("01 Talking to Camera", "02 Walking", ...)
      following the category column. Originals are never moved or deleted.
"""
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ED = Path(__file__).resolve().parent.parent
YUNET = ED / "models" / "face_detection_yunet_2023mar.onnx"
SFACE = ED / "models" / "face_recognition_sface_2021dec.onnx"
FONT = ED / "assets" / "fonts" / "Inter-700.ttf"
VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".3gp"}
IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
FIELDS = ["id", "file", "kind", "duration", "width", "height", "orientation", "faces", "is_me", "me_score",
          "category", "description", "tags"]
CATEGORIES = ["Talking to Camera", "Walking", "Dancing", "With Friends", "Couple", "Family and Home", "Travel",
              "Snow", "Work and Desk", "Food", "Gym and Sports", "City and Street", "Nature", "Events", "Selfies",
              "Screen Recordings", "Other"]


def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                                   str(p)], capture_output=True, text=True).stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        return None
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    rot = 0
    for sd in v.get("side_data_list", []):
        rot = int(sd.get("rotation", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w
    return {"duration": float(j.get("format", {}).get("duration", 0) or 0), "width": w, "height": h}


def grab(p, t, kind):
    if kind == "image":
        im = cv2.imread(str(p))
        return im
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1", "-vf",
                        "scale=480:-2", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if not r.stdout:
        return None
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)


class Faces:
    def __init__(self, me_photo=None):
        self.det = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), score_threshold=0.7)
        self.rec = cv2.FaceRecognizerSF.create(str(SFACE), "") if SFACE.exists() else None
        self.me = None
        if me_photo and self.rec:
            img = cv2.imread(str(me_photo))
            f = self.detect(img)
            if f is None:
                raise SystemExit(f"no face found in {me_photo}")
            self.me = self.embed(img, f)

    def detect(self, img):
        h, w = img.shape[:2]
        s = 640 / max(h, w)
        small = cv2.resize(img, (int(w * s), int(h * s))) if s < 1 else img
        self.det.setInputSize((small.shape[1], small.shape[0]))
        _, faces = self.det.detect(small)
        if faces is None or not len(faces):
            return None
        f = max(faces, key=lambda r: r[2] * r[3]).copy()
        if s < 1:
            f[:14] /= s
        return f

    def count(self, img):
        h, w = img.shape[:2]
        self.det.setInputSize((w, h))
        _, faces = self.det.detect(img)
        return 0 if faces is None else len(faces)

    def embed(self, img, f):
        return self.rec.feature(self.rec.alignCrop(img, f))

    def me_score(self, img):
        if self.me is None:
            return None
        f = self.detect(img)
        if f is None:
            return 0.0
        return float(self.rec.match(self.me, self.embed(img, f), cv2.FaceRecognizerSF_FR_COSINE))


def scan(folder, me_photo):
    idx = folder / "_index"
    idx.mkdir(exist_ok=True)
    faces = Faces(me_photo)
    files = sorted(p for p in folder.rglob("*") if p.suffix.lower() in VIDEO | IMAGE and "_index" not in p.parts
                   and not p.name.startswith("."))
    old = {}
    if (idx / "clip_list.csv").exists():  # keep descriptions already written
        with open(idx / "clip_list.csv") as f:
            old = {r["file"]: r for r in csv.DictReader(f)}
    rows, strips = [], []
    font = ImageFont.truetype(str(FONT), 22)
    for n, p in enumerate(files, 1):
        kind = "video" if p.suffix.lower() in VIDEO else "image"
        info = probe(p) if kind == "video" else None
        if kind == "video" and not info:
            continue
        if kind == "image":
            im = cv2.imread(str(p))
            if im is None:
                continue
            info = {"duration": 0, "width": im.shape[1], "height": im.shape[0]}
        d = info["duration"]
        times = [0] if kind == "image" else [d * 0.12, d * 0.5, d * 0.88]
        frames = [f for f in (grab(p, t, kind) for t in times) if f is not None]
        if not frames:
            continue
        nfaces = max(faces.count(cv2.resize(f, (480, int(480 * f.shape[0] / f.shape[1])))) for f in frames)
        scores = [s for s in (faces.me_score(f) for f in frames) if s is not None]
        me = max(scores) if scores else None
        rel = str(p.relative_to(folder))
        prev = old.get(rel, {})
        rows.append({"id": n, "file": rel, "kind": kind, "duration": round(d, 2), "width": info["width"],
                     "height": info["height"],
                     "orientation": "portrait" if info["height"] > info["width"] else "landscape",
                     "faces": nfaces, "is_me": "" if me is None else ("yes" if me >= 0.363 else "no"),
                     "me_score": "" if me is None else round(me, 3), "category": prev.get("category", ""),
                     "description": prev.get("description", ""), "tags": prev.get("tags", "")})
        tiles = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).resize((200, int(200 * f.shape[0] / f.shape[1])))
                 for f in frames]
        th = max(t.height for t in tiles)
        strip = Image.new("RGB", (620, min(th, 360) + 36), (17, 17, 17))
        for k, t in enumerate(tiles):
            strip.paste(t.crop((0, 0, 200, min(th, 360))), (4 + k * 205, 34))
        ImageDraw.Draw(strip).text((6, 4), f"#{n}  {rel[:40]}  {d:.1f}s  faces:{nfaces}"
                                   + (f"  me:{rows[-1]['is_me']}" if me is not None else ""), font=font, fill="white")
        strips.append(strip)
        print(f"  #{n} {rel} {d:.1f}s faces={nfaces} me={rows[-1]['is_me']}")
    with open(idx / "clip_list.csv", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        w.writerows(rows)
    for old_sheet in idx.glob("sheet_*.jpg"):
        old_sheet.unlink()
    for s in range(0, len(strips), 6):  # 6 clips per sheet, 2 columns
        group = strips[s : s + 6]
        hmax = max(g.height for g in group)
        sheet = Image.new("RGB", (1250, hmax * 3 + 10), (0, 0, 0))
        for k, g in enumerate(group):
            sheet.paste(g, ((k % 2) * 628, (k // 2) * (hmax + 4)))
        sheet.save(idx / f"sheet_{s // 6 + 1:02d}.jpg", quality=85)
    print(f"wrote {idx/'clip_list.csv'} ({len(rows)} clips) and {-(-len(strips) // 6)} contact sheets")
    print("categories to use:", ", ".join(CATEGORIES))


def organize(folder):
    idx = folder / "_index"
    with open(idx / "clip_list.csv") as f:
        rows = list(csv.DictReader(f))
    used = [c for c in CATEGORIES if any(r["category"] == c for r in rows)]
    used += sorted({r["category"] for r in rows if r["category"] and r["category"] not in CATEGORIES})
    names = {c: f"{i + 1:02d} {c}" for i, c in enumerate(used)}
    out = folder / "_organized"
    for r in rows:
        if not r["category"]:
            continue
        src = folder / r["file"]
        dst_dir = out / names[r["category"]]
        dst_dir.mkdir(parents=True, exist_ok=True)
        stem = "_".join(r["description"].lower().split()[:6]) or Path(r["file"]).stem
        dst = dst_dir / f"{int(r['id']):03d}_{stem}{src.suffix.lower()}"
        if not dst.exists():
            shutil.copy2(src, dst)
        r["organized_path"] = str(dst.relative_to(folder))
    with open(idx / "clip_list.csv", "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS + ["organized_path"])
        w.writeheader()
        w.writerows(rows)
    print(f"copied into {out} -> {', '.join(names.values())}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "organize"])
    ap.add_argument("folder")
    ap.add_argument("--me", help="a clear photo of your face, to tag clips you appear in")
    a = ap.parse_args()
    folder = Path(a.folder).expanduser().resolve()
    scan(folder, a.me) if a.cmd == "scan" else organize(folder)


if __name__ == "__main__":
    main()
