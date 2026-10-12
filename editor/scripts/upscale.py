"""4x AI upscale of a low-res clip (e.g. a 360x640 AI-generated or phone clip) with Real-ESRGAN General x4v3
(small SRVGG net, ONNX, CPU; ~1 s per 360x640 frame on 4 cores). Audio is copied unchanged. Feed the result to
assemble.py, which scales it to 1080x1920 (downscaling a 4x result looks much sharper than a 3x lanczos blow-up).

usage: python upscale.py in.mp4 out.mp4 [--scale-to 1440x2560]
model: editor/models/realesrgan/ (setup.sh downloads it)
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as ort

MODEL = (Path(__file__).resolve().parent.parent / "models" / "realesrgan" / "real_esrgan_general_x4v3-onnx-float"
         / "real_esrgan_general_x4v3.onnx")
TILE, OV, S = 128, 16, 4  # model input tile, overlap between tiles (input px), upscale factor


def probe(src):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height,r_frame_rate", "-of", "json", str(src)],
                                  capture_output=True, text=True).stdout)["streams"][0]
    return j["width"], j["height"], j["r_frame_rate"]


def starts(n):
    """tile origins covering 0..n with overlap; the last tile is flush with the edge"""
    if n <= TILE:
        return [0]
    xs = list(range(0, n - TILE, TILE - OV))
    return xs + [n - TILE]


def ramp(n_out, lo_edge, hi_edge):
    """1D blend weight across a tile: ramps over the overlap except at the image border"""
    w = np.ones(n_out, np.float32)
    r = OV * S
    up = np.linspace(0.02, 1, r, dtype=np.float32)
    if not lo_edge:
        w[:r] = up
    if not hi_edge:
        w[-r:] = up[::-1]
    return w


def upscale_frame(sess, img):
    h, w, _ = img.shape
    pad_h, pad_w = max(0, TILE - h), max(0, TILE - w)
    x = np.pad(img, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect") if (pad_h or pad_w) else img
    H, W = x.shape[:2]
    acc = np.zeros((H * S, W * S, 3), np.float32)
    wsum = np.zeros((H * S, W * S, 1), np.float32)
    ys, xs = starts(H), starts(W)
    for y0 in ys:
        for x0 in xs:
            t = x[y0:y0 + TILE, x0:x0 + TILE].astype(np.float32).transpose(2, 0, 1)[None] / 255.0
            o = sess.run(None, {"image": t})[0][0].transpose(1, 2, 0)
            wy = ramp(TILE * S, y0 == 0, y0 + TILE >= H)
            wx = ramp(TILE * S, x0 == 0, x0 + TILE >= W)
            wt = (wy[:, None] * wx[None, :])[..., None]
            acc[y0 * S:(y0 + TILE) * S, x0 * S:(x0 + TILE) * S] += o * wt
            wsum[y0 * S:(y0 + TILE) * S, x0 * S:(x0 + TILE) * S] += wt
    out = acc / np.maximum(wsum, 1e-6)
    return (np.clip(out[:h * S, :w * S], 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--scale-to", help="WxH of the written video (default: 4x the source)")
    a = ap.parse_args()
    w, h, fps = probe(a.src)
    so = ort.SessionOptions()
    so.intra_op_num_threads = 0
    sess = ort.InferenceSession(str(MODEL), so, providers=["CPUExecutionProvider"])
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", a.src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    vf = ["-vf", f"scale={a.scale_to.replace('x', ':')}:flags=lanczos"] if a.scale_to else []
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w * S}x{h * S}",
                            "-r", fps, "-i", "-", "-i", a.src, "-map", "0:v", "-map", "1:a?", *vf, "-c:v", "libx264",
                            "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", a.out],
                           stdin=subprocess.PIPE)
    n = 0
    while True:
        b = dec.stdout.read(w * h * 3)
        if len(b) < w * h * 3:
            break
        enc.stdin.write(upscale_frame(sess, np.frombuffer(b, np.uint8).reshape(h, w, 3)).tobytes())
        n += 1
        if n % 24 == 0:
            print(f"  {n} frames", flush=True)
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"wrote {a.out} ({n} frames, {w}x{h} -> {a.scale_to or f'{w * S}x{h * S}'})")


if __name__ == "__main__":
    main()
