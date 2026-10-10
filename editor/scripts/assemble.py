"""Cut a new picture track to a voiceover (option B: new VO + existing footage + generated shots).

Each shot is a slice of a source clip (trim, constant speed change, cover-fit to 1080x1920, optional blur/darken).
Shots are frame-exact, concatenated, and muxed with the voiceover. Zooms, graphics and captions are added later by
build.py on top of this "assembled" video, so keep shots clean here.

edl.json:
{ "audio": "tight/voice48k.wav", "fps": 30,
  "shots": [ {"src": "../short1/fixed.mp4", "in": 42.6, "dur": 1.0, "speed": 1.0, "blur": 0, "dim": 0, "note": "hook"} ] }
usage: python assemble.py <project_dir>/edl.json <out.mp4>
"""
import json
import re
import subprocess
import sys
from pathlib import Path

W, H = 1080, 1920


_cuts = {}


def scene_cuts(src, thresh=0.18):
    """cut/dissolve times in a source (cached); some hits are just fast camera moves"""
    if src not in _cuts:
        err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-vf",
                              f"scale=320:-2,select='gt(scene,{thresh})',showinfo", "-an", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
        _cuts[src] = [float(x) for x in re.findall(r"pts_time:([\d.]+)", err)]
    return _cuts[src]


def check_cuts(shots, base, fps=30):
    """warn when a shot's source range runs across a scene cut (a stray frame of the neighbouring shot).
    Frame rounding can pull in one extra frame at either end, so the window is padded by ~1.5 frames."""
    for i, s in enumerate(shots):
        if s.get("blur"):
            continue
        src = (base / s["src"]).resolve()
        a = s.get("in", 0)
        b = a + s["dur"] * s.get("speed", 1.0)
        hits = [c for c in scene_cuts(src) if a - 0.5 / fps < c < b + 1.5 / fps]
        if hits:
            print(f"  WARNING shot {i} ({s.get('note', '')}): {Path(s['src']).name} {a:.2f}-{b:.2f} crosses "
                  f"possible cut(s) at {', '.join(f'{c:.2f}' for c in hits)}")


def main():
    edl_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    edl = json.loads(edl_path.read_text())
    base = edl_path.parent
    check_cuts(edl["shots"], base, edl.get("fps", 30))
    fps = edl.get("fps", 30)
    audio = (base / edl["audio"]).resolve()
    inputs, chains, t = [], [], 0.0
    for i, s in enumerate(edl["shots"]):
        src = (base / s["src"]).resolve()
        speed = s.get("speed", 1.0)
        frames = round((t + s["dur"]) * fps) - round(t * fps)  # round against the running total: no drift
        span = s["dur"] * speed + 0.5  # read a little extra; trimmed to exact frames below
        inputs += ["-ss", f"{s.get('in', 0):.3f}", "-t", f"{span:.3f}", "-i", str(src)]
        f = [f"setpts=(PTS-STARTPTS)/{speed}", f"fps={fps}",
             f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}", "setsar=1",
             f"tpad=stop_mode=clone:stop_duration={s['dur'] + 1:.2f}", f"trim=end_frame={frames}", "setpts=PTS-STARTPTS"]
        if s.get("blur"):
            f.append(f"boxblur={int(s['blur'])}:2")
        if s.get("dim"):
            f.append(f"eq=brightness={-abs(s['dim']):.2f}:saturation=0.9")
        chains.append(f"[{i}:v]" + ",".join(f) + f"[v{i}]")
        print(f"  {t:6.2f}-{t + s['dur']:6.2f}  {Path(s['src']).name}@{s.get('in', 0):.2f} x{speed}  {s.get('note', '')}")
        t += s["dur"]
    n = len(edl["shots"])
    graph = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    # silence under shots after the voice ends (e.g. a channel end card); output cut to the exact picture length
    # (-shortest trims the last frame or two)
    total = round(t * fps) / fps
    graph += f";[{n}:a]apad=whole_dur={total:.4f}[a]"
    (out.parent / "assemble_graph.txt").write_text(graph)
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-i", str(audio), "-filter_complex_script",
           str(out.parent / "assemble_graph.txt"), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
           "-crf", "14", "-g", str(fps), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-t", f"{total:.4f}", str(out)]
    subprocess.run(cmd, check=True)
    print(f"wrote {out} ({t:.2f}s of picture)")


if __name__ == "__main__":
    main()
