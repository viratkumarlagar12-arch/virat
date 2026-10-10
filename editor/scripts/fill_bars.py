"""Fix black bars inside an already-edited video (common in CapCut exports: a clip or photo that doesn't fill
the 9:16 frame). Keeps timing and audio exactly; only the barred stretches change:
  - small bars (<= 18% of the height): zoom in just enough to push them out of frame
  - big bars (a photo in a strip): blurred-fill background + the strip enlarged in the middle

usage: python fill_bars.py in.mp4 out.mp4 [--keep-from 44.4]   (--keep-from: leave the end card untouched)
"""
import argparse
import subprocess

import numpy as np


def scan(src, w, h, thresh=12):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
    runs, prev, k = [], None, 0
    while True:
        b = p.stdout.read(w * h)
        if len(b) < w * h:
            break
        dark = np.frombuffer(b, np.uint8).reshape(h, w).mean(1) < thresh
        top = int(np.argmin(dark)) if not dark.all() else h
        bot = int(np.argmin(dark[::-1])) if not dark.all() else h
        sig = (top, bot)
        if sig != prev:
            runs.append([k, k, top, bot])
            prev = sig
        else:
            runs[-1][1] = k
        k += 1
    p.wait()
    return [r for r in runs if (r[2] > 4 or r[3] > 4) and r[2] + r[3] < h]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--keep-from", type=float, default=None, help="seconds; don't touch frames after this")
    ap.add_argument("--fps", type=float, default=30)
    a = ap.parse_args()
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height", "-of", "csv=p=0", a.src],
                                   capture_output=True, text=True).stdout.strip().split(","))
    runs = scan(a.src, w, h)
    if a.keep_from is not None:
        runs = [r for r in runs if r[0] / a.fps < a.keep_from]
    if not runs:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-c", "copy", a.out], check=True)
        print("no bars found")
        return
    parts = [f"[0:v]split={len(runs) + 1}[base]" + "".join(f"[s{i}]" for i in range(len(runs)))]
    chain, last = [], "base"
    for i, (f0, f1, top, bot) in enumerate(runs):
        ch = h - top - bot
        if (top + bot) / h <= 0.18:  # zoom past the bars, keep the centre
            z = h / ch
            cw = int(w / z) // 2 * 2
            parts.append(f"[s{i}]crop={cw}:{ch}:{(w - cw) // 2}:{top},scale={w}:{h}:flags=lanczos,setsar=1[f{i}]")
            kind = f"zoom x{z:.2f}"
        else:  # blurred fill + enlarged strip
            fg_w = int(w * 1.3) // 2 * 2
            fg_h = int(ch * 1.3) // 2 * 2
            parts.append(f"[s{i}]crop={w}:{ch}:0:{top},split[a{i}][b{i}]")
            parts.append(f"[a{i}]scale=-2:{h},crop={w}:{h},boxblur=24:2,eq=brightness=-0.14:saturation=1.1[bg{i}]")
            parts.append(f"[b{i}]scale={fg_w}:{fg_h}:flags=lanczos,crop={w}:{fg_h}[fg{i}]")
            parts.append(f"[bg{i}][fg{i}]overlay=0:{(h - fg_h) // 2},setsar=1[f{i}]")
            kind = "blur-fill"
        nxt = f"o{i}"
        chain.append(f"[{last}][f{i}]overlay=0:0:enable='between(n,{f0},{f1})'[{nxt}]")
        last = nxt
        print(f"  {f0 / a.fps:6.2f}-{(f1 + 1) / a.fps:6.2f}s  bars top={top} bottom={bot}px -> {kind}")
    graph = ";".join(parts + chain)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.src, "-filter_complex", graph, "-map", f"[{last}]",
                    "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
                    "-c:a", "copy", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
