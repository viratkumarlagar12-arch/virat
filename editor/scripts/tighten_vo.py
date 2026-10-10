"""Tighten a voiceover: shorten every pause between phrases (Shorts pacing), trim leading/trailing silence.
Joins use 8 ms fades so nothing clicks. Pauses marked as intentional ("keep") stay as recorded.

usage: python tighten_vo.py <work_dir_with_transcript_and_voice48k> <out.wav> [--max-pause 0.18] [--keep 0.72]
  --keep: source times (s) of pauses to keep as they are, e.g. a dramatic beat after "Kehte hain..."
"""
import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--max-pause", type=float, default=0.18, help="longest silence left between phrases (s)")
    ap.add_argument("--pre", type=float, default=0.07)
    ap.add_argument("--post", type=float, default=0.16)
    ap.add_argument("--keep", type=float, nargs="*", default=[], help="pauses (any time inside them) to keep")
    a = ap.parse_args()
    work = Path(a.work)
    words = json.loads((work / "transcript.json").read_text())["words"]
    audio, sr = sf.read(work / "voice48k.wav", dtype="float32")
    dur = len(audio) / sr

    spans = [[max(0.0, w["start"] - a.pre), min(dur, w["end"] + a.post)] for w in words]
    spans.sort()
    keep = []
    for s, e in spans:
        if keep:
            gap = s - keep[-1][1]
            if gap <= a.max_pause or any(keep[-1][1] - 0.05 <= k <= s + 0.05 for k in a.keep):
                keep[-1][1] = max(keep[-1][1], e)
                continue
        keep.append([s, e])

    fade = int(0.008 * sr)
    gap = np.zeros(int(a.max_pause * sr), dtype=np.float32)
    parts = []
    for i, (s, e) in enumerate(keep):
        seg = audio[int(s * sr) : int(e * sr)].copy()
        if len(seg) > 2 * fade:
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
        parts.append(seg)
        if i + 1 < len(keep):
            parts.append(gap)
    out = np.concatenate(parts)
    sf.write(a.out, out, sr, subtype="PCM_24")
    print(f"{dur:.2f}s -> {len(out) / sr:.2f}s ({len(keep)} phrases)")


if __name__ == "__main__":
    main()
