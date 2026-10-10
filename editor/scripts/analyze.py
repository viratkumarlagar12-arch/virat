"""Step 0 — "go through the video, understand it": probe, audio, loudness, pauses, face position,
scene changes and contact sheets (frame grids I look at to see the video).

usage: python analyze.py <video> <project_dir> [--step 1.0]
writes <project_dir>/analysis.json, audio16k.wav, voice48k.wav, sheets/sheet_XX.jpg
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np

ED = Path(__file__).resolve().parent.parent
FONT = ED / "assets" / "fonts" / "Inter-700.ttf"
YUNET = ED / "models" / "face_detection_yunet_2023mar.onnx"


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)]).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int(v.get("tags", {}).get("rotate", rot))
    if abs(rot) % 180 == 90:
        w, h = h, w  # ffmpeg autorotates, so report display size
    num, den = map(int, v.get("avg_frame_rate", "30/1").split("/"))
    return {
        "width": w, "height": h, "rotation": rot,
        "fps": round(num / den, 3) if den else 30.0,
        "duration": float(j["format"]["duration"]),
        "vcodec": v["codec_name"], "pix_fmt": v.get("pix_fmt"),
        "has_audio": a is not None,
        "acodec": a["codec_name"] if a else None,
        "aspect": "9:16" if h > w else ("16:9" if w > h else "1:1"),
    }


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                          "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", summ)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    return {"integrated_lufs": float(i.group(1)) if i else None,
            "lra": float(lra.group(1)) if lra else None,
            "true_peak_db": float(pk.group(1)) if pk else None}


def silences(path, noise_db, min_d):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                          "-af", f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", err)]
    return [[round(max(0, s), 3), round(e, 3)] for s, e in zip(starts, ends)]


def scene_cuts(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf",
                          "scale=320:-2,select='gt(scene,0.32)',showinfo", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return [round(float(x), 3) for x in re.findall(r"pts_time:([\d.]+)", err)]


def face_track(path, info, fps=5.0):
    """Largest face per sampled frame, normalized [x, y, w, h] in display coordinates."""
    w = 480
    h = int(round(info["height"] * w / info["width"] / 2) * 2)
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), score_threshold=0.6)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    track, k, size = [], 0, w * h * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        _, faces = det.detect(frame)
        t = round(k / fps, 3)
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])
            track.append({"t": t, "box": [round(float(f[0]) / w, 4), round(float(f[1]) / h, 4),
                                          round(float(f[2]) / w, 4), round(float(f[3]) / h, 4)],
                          "score": round(float(f[14]), 3)})
        else:
            track.append({"t": t, "box": None})
        k += 1
    p.wait()
    boxes = np.array([r["box"] for r in track if r["box"]])
    summary = None
    if len(boxes):
        x0, y0 = np.percentile(boxes[:, 0], 5), np.percentile(boxes[:, 1], 5)
        x1 = np.percentile(boxes[:, 0] + boxes[:, 2], 95)
        y1 = np.percentile(boxes[:, 1] + boxes[:, 3], 95)
        med = np.median(boxes, axis=0)
        summary = {
            "coverage": round(len(boxes) / max(1, len(track)), 3),
            "median_box": [round(float(v), 4) for v in med],
            # region the face moves within (5th–95th percentile) — never put graphics here
            "face_zone": [round(float(x0), 4), round(float(y0), 4), round(float(x1 - x0), 4), round(float(y1 - y0), 4)],
            "chin_y": round(float(y1), 4),
            "center_x": round(float(med[0] + med[2] / 2), 4),
        }
    return track, summary


def contact_sheets(path, out_dir, duration, step, info):
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("sheet_*.jpg"):
        old.unlink()
    portrait = info["height"] >= info["width"]
    tw = 216 if portrait else 384
    cols, rows = (5, 3) if portrait else (4, 4)
    font = str(FONT).replace(":", r"\:")
    vf = (f"fps=1/{step},scale={tw}:-2,"
          f"drawtext=fontfile='{font}':text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
          f"tile={cols}x{rows}:padding=4:color=0x111111")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", vf, "-q:v", "3", str(out_dir / "sheet_%02d.jpg")])
    return sorted(str(p.name) for p in out_dir.glob("sheet_*.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("project")
    ap.add_argument("--step", type=float, default=1.0, help="seconds between contact-sheet frames")
    ap.add_argument("--silence-db", type=float, default=-35)
    ap.add_argument("--silence-min", type=float, default=0.3)
    args = ap.parse_args()
    src, proj = Path(args.video).resolve(), Path(args.project)
    proj.mkdir(parents=True, exist_ok=True)

    info = probe(src)
    print("probe:", info)
    if info["has_audio"]:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(proj / "audio16k.wav")])
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s24le",
             str(proj / "voice48k.wav")])
    data = {"source": str(src), "info": info}
    if info["has_audio"]:
        data["loudness"] = loudness(src)
        data["silences"] = silences(src, args.silence_db, args.silence_min)
        print("loudness:", data["loudness"], f"| {len(data['silences'])} pauses")
    data["scene_cuts"] = scene_cuts(src)
    track, summary = face_track(src, info)
    data["face"] = summary
    data["face_track"] = track
    print("face:", summary)
    data["sheets"] = contact_sheets(src, proj / "sheets", info["duration"], args.step, info)
    print("sheets:", data["sheets"])
    (proj / "analysis.json").write_text(json.dumps(data, indent=1))
    print(f"wrote {proj/'analysis.json'}")


if __name__ == "__main__":
    main()
