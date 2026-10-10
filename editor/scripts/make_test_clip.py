"""Make a fake 'raw talking-head' clip for testing the pipeline (real face photo + real speech).

usage: python make_test_clip.py <out.mp4> [--portrait]
"""
import subprocess, sys, tempfile
from pathlib import Path
import numpy as np, soundfile as sf
from skimage import data
from PIL import Image

ED = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1]); portrait = "--portrait" in sys.argv
W, H = (1080, 1920) if portrait else (1920, 1080)
tmp = Path(tempfile.mkdtemp())
Image.fromarray(data.astronaut()).resize((900, 900)).save(tmp / "face.png")
wavs = [ED / "models/sherpa-onnx-whisper-turbo/test_wavs/0.wav",
        ED / "models/sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-v2-int8-2026-02-05/test_wavs/en.wav",
        ED / "models/sherpa-onnx-whisper-turbo/test_wavs/1.wav"]
parts = [np.zeros(int(0.6 * 16000), np.float32)]
for i, w in enumerate(wavs):
    a, sr = sf.read(w, dtype="float32")
    if a.ndim > 1: a = a.mean(1)
    if sr != 16000:
        from scipy.signal import resample_poly
        a = resample_poly(a, 16000, sr).astype(np.float32)
    parts += [a, np.zeros(int((1.6 if i == 0 else 0.7) * 16000), np.float32)]
audio = np.concatenate(parts); sf.write(tmp / "speech.wav", audio, 16000)
dur = len(audio) / 16000
x = (W - 900) // 2 + (0 if portrait else 260); y = (H - 900) // 2 - (200 if portrait else 0)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x2b3440:s={W}x{H}:r=30:d={dur}",
    "-loop", "1", "-i", str(tmp / "face.png"), "-i", str(tmp / "speech.wav"),
    "-filter_complex", f"[1:v]scale=900:900[f];[0:v][f]overlay=x='{x}+30*sin(t/2)':y={y}:shortest=1,format=yuv420p[v]",
    "-map", "[v]", "-map", "2:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
    "-ar", "48000", "-t", str(dur), str(out)], check=True)
print(out, round(dur, 2), "s")
