"""Quality review of a rendered Short (masterclass step 4: "after editing, review the frames and make
sure no graphic, B-roll or animation covers my face").

- contact sheets of the final video (frames I look at one by one)
- face check: frames where the face was visible in the cut base video but is not found in the final
  (outside planned full-screen cutaways) are listed as "face covered?"
- loudness / true-peak of the final mix, and duration / resolution / fps

usage: python review.py projects/<name> [video.mp4] [--step 0.5]
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


def frames(path, fps, w=360):
    h = int(w * 16 / 9)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    k = 0
    while True:
        buf = p.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        yield k / fps, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
        k += 1
    p.wait()


def face_flags(path, fps):
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (360, 640), score_threshold=0.55)
    out = {}
    for t, f in frames(path, fps):
        _, faces = det.detect(f)
        out[round(t, 2)] = faces is not None and len(faces) > 0
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--step", type=float, default=0.5)
    a = ap.parse_args()
    proj = Path(a.project)
    vid = Path(a.video) if a.video else max((proj / "out").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    rev = proj / "work" / "review"
    rev.mkdir(parents=True, exist_ok=True)
    for old in rev.glob("*.jpg"):
        old.unlink()

    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format",
                                   str(vid)], capture_output=True, text=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    print(f"{vid.name}: {v['width']}x{v['height']} @ {v['r_frame_rate']} fps, {float(j['format']['duration']):.2f}s, "
          f"{float(j['format']['size']) / 1e6:.1f} MB")
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(vid), "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    summ = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summ)
    pk = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summ)
    print(f"loudness {i.group(1) if i else '?'} LUFS (target -14), true peak {pk.group(1) if pk else '?'} dBTP (max -1)")

    font = str(FONT).replace(":", r"\:")
    vf = (f"fps=1/{a.step},scale=216:384,drawtext=fontfile='{font}':text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:"
          f"fontcolor=white:box=1:boxcolor=black@0.6,tile=6x3:padding=4:color=0x111111")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-vf", vf, "-q:v", "3", str(rev / "final_%02d.jpg")],
                   check=True)
    print("contact sheets:", sorted(p.name for p in rev.glob("final_*.jpg")))

    base = proj / "work" / "base.mp4"
    plan_file = proj / "plan.json"
    faceless = plan_file.exists() and json.loads(plan_file.read_text()).get("layout", {}).get("face") == "none"
    if faceless:
        print("face check: skipped (plan says this video has no face)")
    elif base.exists() and YUNET.exists():
        fb, ff = face_flags(base, 4), face_flags(vid, 4)
        hf = (proj / "hf" / "index.html").read_text()
        m = re.search(r"window\.EDIT = (\{.*?\});</script>", hf, re.S)
        cut = []
        if m:
            ed = json.loads(m.group(1))
            cut = [(o["t"], o["t"] + o["dur"]) for o in ed["overlays"]
                   if o.get("mode") == "full" or o["type"] in ("text_slam", "countdown")]
        bad = [t for t, ok in ff.items() if fb.get(t) and not ok and not any(s - 0.1 <= t <= e + 0.1 for s, e in cut)]
        print(f"face visible in {sum(ff.values())}/{len(ff)} sampled frames; planned cutaways {[(round(s,1), round(e,1)) for s, e in cut]}")
        if bad:
            spans, s0, prev = [], bad[0], bad[0]
            for t in bad[1:] + [None]:
                if t is None or t - prev > 0.3:
                    spans.append((s0, prev))
                    s0 = t
                prev = t if t is not None else prev
            print("FACE COVERED? at:", ", ".join(f"{s:.2f}-{e:.2f}s" for s, e in spans))
        else:
            print("face check: OK — nothing covers the face outside planned cutaways")


if __name__ == "__main__":
    main()
