"""Offline text-to-speech for a new voiceover (free sherpa-onnx voices in editor/models/tts, see setup.sh).
The script is spoken sentence by sentence (split at । ? ! . and line breaks); each sentence's own leading/trailing
silence is trimmed and a set pause goes between sentences, so every sentence's start/end time is known.

usage: python tts.py <voice> <script.txt | -> <out.wav> [--speed 1.0] [--pauses 0.25 | '[0.3, 0.6, ...]']
                     [--json out.json] [--sid N] [--lang hi]
voices: piper:rohan  piper:pratham  piper:priyamvada                  (Hindi Piper/VITS, 22 kHz)
        kokoro:hm_omega  kokoro:hm_psi  kokoro:hf_alpha  kokoro:hf_beta  (Hindi Kokoro v1.0, 24 kHz; any v1.0 name
        works, e.g. kokoro:af_heart --lang en-us)
--pauses: seconds after each sentence; a JSON list sets them one by one (missing ones are 0.25).
writes 48 kHz mono 24-bit WAV (peak -1 dBFS); --json: each sentence's text, start, end and raw model peak.
"""
import argparse
import json
import re
import sys
import unicodedata
from math import gcd
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf
from scipy.signal import resample_poly

TTS = Path(__file__).resolve().parent.parent / "models" / "tts"
KOKORO = TTS / "kokoro-multi-lang-v1_0"  # fp32: the int8 build adds a steady 4.8/9.6 kHz whine and runs 3x slower
KOKORO_NAMES = """af_alloy af_aoede af_bella af_heart af_jessica af_kore af_nicole af_nova af_river af_sarah af_sky
am_adam am_echo am_eric am_fenrir am_liam am_michael am_onyx am_puck am_santa bf_alice bf_emma bf_isabella bf_lily
bm_daniel bm_fable bm_george bm_lewis ef_dora em_alex ff_siwis hf_alpha hf_beta hm_omega hm_psi if_sara im_nicola
jf_alpha jf_gongitsune jf_nezumi jf_tebukuro jm_kumo pf_dora pm_alex pm_santa zf_xiaobei zf_xiaoni zf_xiaoxiao
zf_xiaoyi zm_yunjian zm_yunxi zm_yunxia zm_yunyang em_santa""".split()  # = Kokoro v1.0 speaker ids 0..53
SR = 48000
PAUSE = 0.25
EDGE = 0.03  # silence kept around each trimmed sentence (s)


def kokoro_respell(s: str) -> str:
    # Kokoro has no breathy ɽʱ: "बढ़ने" comes out as "बर हने"; plain ढ is heard as बढ़ने (ASR round trip)
    return s.replace("\u0922\u093c", "\u0922").replace("\u095d", "\u0922")  # ढ़ (2 forms) -> ढ


def load_voice(voice: str, lang: str = "hi", threads: int = 4):
    """'piper:rohan' / 'kokoro:hm_omega' -> (OfflineTts, speaker id, text fix applied before synthesis)"""
    kind, _, name = voice.partition(":")
    if kind == "piper":
        d = next(TTS.glob(f"vits-piper-*-{name}-*"), None)
        if d is None:
            sys.exit(f"no Piper voice '{name}' in {TTS} (run editor/setup.sh)")
        model = sherpa_onnx.OfflineTtsModelConfig(vits=sherpa_onnx.OfflineTtsVitsModelConfig(
            model=str(next(d.glob("*.onnx"))), tokens=str(d / "tokens.txt"), data_dir=str(d / "espeak-ng-data")),
            num_threads=threads)
        sid, fix = 0, str
    elif kind == "kokoro":
        if name not in KOKORO_NAMES and not name.isdigit():
            sys.exit(f"unknown Kokoro voice '{name}'; Hindi ones: hf_alpha hf_beta hm_omega hm_psi")
        # lang -> espeak-ng voice for everything that is not Chinese: Hindi reads "21" as "ikkis", CO2 as "si o do"
        model = sherpa_onnx.OfflineTtsModelConfig(kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=str(KOKORO / "model.onnx"), voices=str(KOKORO / "voices.bin"), tokens=str(KOKORO / "tokens.txt"),
            data_dir=str(KOKORO / "espeak-ng-data"), lang=lang), num_threads=threads)
        sid = int(name) if name.isdigit() else KOKORO_NAMES.index(name)
        fix = kokoro_respell if lang == "hi" else str
    else:
        sys.exit(f"voice must look like piper:rohan or kokoro:hm_omega, got '{voice}'")
    return sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(model=model)), sid, fix


def split_sentences(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text)
    parts = re.split(r"(?<=[।॥?!])(?![।॥?!])\s*|(?<=\.)\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip(" \t।॥?!.,")]


def trim(x: np.ndarray, sr: int) -> np.ndarray:
    """cut the model's own silence at both ends (below -40 dB of the peak), keep EDGE, 5 ms fades"""
    loud = np.flatnonzero(np.abs(x) > max(np.abs(x).max() * 0.01, 1e-4))
    if not len(loud):
        return x[:0]
    x = x[max(0, loud[0] - int(EDGE * sr)) : loud[-1] + int(EDGE * sr)].copy()
    f = min(int(0.005 * sr), len(x) // 2)
    x[:f] *= np.linspace(0, 1, f)
    x[len(x) - f :] *= np.linspace(1, 0, f)
    return x


def speak(tts, sid: int, sentences: list[str], speed: float = 1.0, pauses=PAUSE, fix=str):
    """-> (48 kHz float audio, [{i, text, start, end, peak}])"""
    pauses = pauses if isinstance(pauses, list) else [pauses] * len(sentences)
    parts, segs, t = [], [], 0.0
    for i, s in enumerate(sentences):
        g = tts.generate(fix(s), sid=sid, speed=speed)
        x = np.asarray(g.samples, dtype=np.float32)
        k = gcd(SR, g.sample_rate)
        x = resample_poly(trim(x, g.sample_rate), SR // k, g.sample_rate // k).astype(np.float32)
        segs.append({"i": i, "text": s, "start": round(t, 3), "end": round(t + len(x) / SR, 3),
                     "peak": round(float(np.abs(g.samples).max()), 3)})
        gap = float(pauses[i]) if i < len(pauses) else PAUSE
        parts += [x, np.zeros(int(gap * SR) if i + 1 < len(sentences) else int(EDGE * SR), np.float32)]
        t += (len(x) + len(parts[-1])) / SR
    audio = np.concatenate(parts)
    return audio * (0.891 / max(np.abs(audio).max(), 1e-6)), segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("voice", help="piper:rohan | piper:pratham | piper:priyamvada | kokoro:hm_omega | ...")
    ap.add_argument("text", help="script file (UTF-8) or - for stdin")
    ap.add_argument("out")
    ap.add_argument("--speed", type=float, default=1.0, help="1.1 = 10%% faster")
    ap.add_argument("--pauses", default=str(PAUSE), help="seconds after each sentence: 0.3 or JSON list [0.3, 0.6]")
    ap.add_argument("--sid", type=int, help="speaker id override (multi-speaker models)")
    ap.add_argument("--lang", default="hi", help="Kokoro only: espeak-ng language for non-Chinese text")
    ap.add_argument("--json", help="write sentence timings here")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    text = sys.stdin.read() if a.text == "-" else Path(a.text).read_text(encoding="utf-8")
    sents = split_sentences(text)
    if not sents:
        sys.exit("no text to speak")
    tts, sid, fix = load_voice(a.voice, a.lang, a.threads)
    audio, segs = speak(tts, sid if a.sid is None else a.sid, sents, a.speed, json.loads(a.pauses), fix)
    sf.write(a.out, audio, SR, subtype="PCM_24")
    for s in segs:
        print(f"[{s['start']:6.2f}-{s['end']:6.2f}] {s['text']}" + ("  (model output clipped)" if s["peak"] >= 1 else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"voice": a.voice, "speed": a.speed, "duration": round(len(audio) / SR, 3),
                                            "sentences": segs}, ensure_ascii=False, indent=1))
    print(f"wrote {a.out} ({len(audio) / SR:.2f}s, {len(segs)} sentences)")


if __name__ == "__main__":
    main()
