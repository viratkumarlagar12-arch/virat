"""Final audio mix: clean voice + ducked music + SFX, mastered to YouTube loudness (-14 LUFS, -1 dBTP).

Voice chain (ffmpeg): high-pass 80 Hz, light denoise, de-mud, presence lift, compressor.
Music: scaled relative to the voice (K-weighted, i.e. as loud as ears hear it), ducked while you talk, scooped in the
voice frequency band. Level: "under_voice_db"/"gap_db", or "volume" like CapCut's music volume (100 = the track's
full level; a normally mastered track at 10 sits about 14 dB under a voiceover).
SFX: placed at event times with per-effect default levels.

usage (normally called from build.py):
  python mix.py voice.wav out.wav [--music bed.wav] [--sfx events.json] [--duration 42.0]
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter, resample_poly, sosfilt

SR = 48000
ED = Path(__file__).resolve().parent.parent
SFX_DIR = ED / "assets" / "sfx"

# level of each effect relative to the voice (dB). Tuned to sit under speech, never over it.
SFX_GAIN_DB = {
    "whoosh": -9, "swoosh": -11, "whoosh_down": -10, "pop": -8, "bubble": -11, "click": -10,
    "tick": -9, "ding": -11, "cash": -9, "success": -10, "riser": -11, "impact": -5,
    "glitch": -12, "typing": -14, "camera": -9,
}
VOICE_CHAIN = (
    "highpass=f=80,highpass=f=80,afftdn=nf=-28:tn=1,"
    "equalizer=f=280:t=q:w=1.2:g=-2.5,equalizer=f=3800:t=q:w=1.0:g=2.5,equalizer=f=11000:t=q:w=0.8:g=1.5,"
    "acompressor=threshold=-20dB:ratio=3:attack=6:release=90:makeup=2"
)


def load(path, sr=SR):
    a, r = sf.read(str(path), dtype="float32", always_2d=True)
    if r != sr:
        a = resample_poly(a, sr, r, axis=0).astype(np.float32)
    if a.shape[1] == 1:
        a = np.repeat(a, 2, 1)
    return a[:, :2]


def kweight(x):
    """ITU-R BS.1770 K-weighting (48 kHz): levels as ears hear them, so a bass-heavy music bed isn't over-counted"""
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585],
                x, axis=0)
    return lfilter([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621], y, axis=0)


def rms_env(x, win=0.05):
    m = x.mean(1)
    n = int(win * SR)
    pad = (-len(m)) % n
    blocks = np.pad(m, (0, pad)).reshape(-1, n)
    r = np.sqrt((blocks ** 2).mean(1) + 1e-12)
    return np.repeat(r, n)[: len(m)]


def smooth(mask, attack=0.06, release=0.45):
    """attack/release follower on a 0/1 speech mask, at a 1 kHz control rate"""
    step = SR // 1000
    ctl = mask[::step]
    o = np.empty_like(ctl)
    y = 0.0
    a, r = np.exp(-1 / (attack * 1000)), np.exp(-1 / (release * 1000))
    for i, v in enumerate(ctl):
        c = a if v > y else r
        y = c * y + (1 - c) * v
        o[i] = y
    out = np.repeat(o, step)[: len(mask)]
    return np.pad(out, (0, len(mask) - len(out)), mode="edge")


def speech_rms(voice):
    env = rms_env(voice)
    thr = np.percentile(env, 95) * 0.15
    sp = env[env > thr]
    return float(np.sqrt((sp ** 2).mean())) if len(sp) else 0.05, env > thr


def loudnorm(src, dst, target=-14.0, tp=-1.5):
    """two-pass EBU R128 normalization"""
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af",
                         f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p1, re.S).group(0))
    af = (f"loudnorm=I={target}:TP={tp}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
          f"alimiter=limit={10 ** (tp / 20):.4f}:level=false:latency=true")  # latency: no 5 ms audio delay
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-ar", str(SR), "-c:a", "pcm_s24le",
                    str(dst)], check=True)


def music_stem(voice, music, music_cfg, n):
    """the music exactly as it goes into the mix: looped/cut to n samples, voice band scooped, levelled and ducked"""
    m = load(music)
    if len(m) < n:  # loop with a short crossfade
        reps = int(np.ceil(n / len(m))) + 1
        m = np.concatenate([m] * reps)
    m = m[:n].copy()
    band = sosfilt(butter(2, [900, 4500], "bandpass", fs=SR, output="sos"), m, axis=0)
    m -= 0.35 * band  # make room for the voice
    # levels as heard (K-weighted); the music's first/last 2 s (fades) don't count
    vk, speaking = speech_rms(kweight(voice))
    core = m[2 * SR : max(2 * SR + SR, n - 2 * SR)]
    mr = float(np.sqrt((kweight(core) ** 2).mean()) + 1e-9)
    if "volume" in music_cfg:  # CapCut-style: track mastered ~-10 LUFS, voiceover ~-16 LUFS
        under = -6 - 20 * np.log10(max(music_cfg["volume"], 0.1) / 100)
        gap = under - 2
    else:
        under = music_cfg.get("under_voice_db", 19)  # how far below the voice while talking
        gap = music_cfg.get("gap_db", 11)  # in pauses / intro / outro
    g_talk, g_gap = vk / mr * 10 ** (-under / 20), vk / mr * 10 ** (-gap / 20)
    duck = smooth(speaking.astype(np.float32))
    gain = g_gap + (g_talk - g_gap) * duck
    fo = int(1.2 * SR)
    gain[-fo:] *= np.linspace(1, 0, fo)
    return m * gain[:, None]


def mix(voice_wav, out_wav, music=None, music_cfg=None, sfx_events=(), duration=None, work=None):
    work = Path(work or Path(out_wav).parent)
    music_cfg = music_cfg or {}
    vproc = work / "voice_processed.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(voice_wav), "-af", VOICE_CHAIN, "-ar", str(SR),
                    "-c:a", "pcm_s24le", str(vproc)], check=True)
    voice = load(vproc)
    n = int((duration or len(voice) / SR) * SR)
    voice = np.pad(voice, ((0, max(0, n - len(voice))), (0, 0)))[:n]
    vr = speech_rms(voice)[0]  # SFX levels are relative to this (plain RMS)
    out = voice.copy()

    if music:
        out += music_stem(voice, music, music_cfg, n)

    for ev in sfx_events:
        name = ev["name"]
        path = Path(ev.get("path") or SFX_DIR / f"{name}.wav")
        if not path.exists():
            print(f"  sfx missing: {path}")
            continue
        s = load(path)
        amp = np.abs(s).max(1)
        active = s[amp > amp.max() * 0.05]  # loudness of the audible part, so short clicks aren't over-boosted
        sr_ = float(np.sqrt((active ** 2).mean()) + 1e-9)
        g = vr * 10 ** ((SFX_GAIN_DB.get(name, -10) + ev.get("gain_db", 0)) / 20) / sr_
        st = int(ev["t"] * SR)
        if st >= n:
            continue
        seg = s[: n - st] * g
        out[st : st + len(seg)] += seg

    tmp = work / "mix_pre.wav"
    sf.write(tmp, out.astype(np.float32), SR, subtype="FLOAT")
    loudnorm(tmp, out_wav)
    return out_wav


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice")
    ap.add_argument("out")
    ap.add_argument("--music")
    ap.add_argument("--sfx", help="json list of {t, name, gain_db?}")
    ap.add_argument("--duration", type=float)
    a = ap.parse_args()
    ev = json.loads(Path(a.sfx).read_text()) if a.sfx else []
    mix(a.voice, a.out, a.music, {}, ev, a.duration)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
