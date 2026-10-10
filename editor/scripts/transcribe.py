"""Word-level transcription for captions (masterclass step 4: "first transcribe my video so you know
exactly when each animation, text, image or effect should appear").

Text comes from Whisper large-v3-turbo (good with Hindi + English mixed speech). Word timing comes
from Meta's Omnilingual CTC model, which gives a timestamp for every character; the two are aligned
character-by-character. Speech regions are found first with Silero VAD.

usage: python transcribe.py <project_dir> [--lang auto|hi|en|...]
reads  <project_dir>/audio16k.wav   (written by analyze.py)
writes <project_dir>/transcript.json, transcript.txt
"""
import argparse
import difflib
import json
import unicodedata
from pathlib import Path

import numpy as np
import sherpa_onnx
import soundfile as sf

MODELS = Path(__file__).resolve().parent.parent / "models"
WHISPER = MODELS / "sherpa-onnx-whisper-turbo"
CTC = MODELS / "sherpa-onnx-omnilingual-asr-1600-languages-300M-ctc-v2-int8-2026-02-05"
SR = 16000
PAD = 0.15  # seconds of context around each VAD segment


def norm_chars(s: str) -> str:
    s = unicodedata.normalize("NFC", s.lower())
    return "".join(c for c in s if unicodedata.category(c)[0] in "LMN")


def vad_segments(audio: np.ndarray) -> list[tuple[float, float]]:
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = str(MODELS / "silero_vad.onnx")
    cfg.silero_vad.threshold = 0.45
    cfg.silero_vad.min_silence_duration = 0.3
    cfg.silero_vad.min_speech_duration = 0.15
    cfg.silero_vad.max_speech_duration = 18
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=600)
    win = cfg.silero_vad.window_size
    segs = []
    for i in range(0, len(audio), win):
        vad.accept_waveform(audio[i : i + win])
        while not vad.empty():
            f = vad.front
            segs.append((f.start / SR, (f.start + len(f.samples)) / SR))
            vad.pop()
    vad.flush()
    while not vad.empty():
        f = vad.front
        segs.append((f.start / SR, (f.start + len(f.samples)) / SR))
        vad.pop()
    # merge segments separated by tiny gaps so phrases stay whole
    merged = []
    for s, e in segs:
        if merged and s - merged[-1][1] < 0.25 and e - merged[-1][0] < 20:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def decode(rec, audio):
    st = rec.create_stream()
    st.accept_waveform(SR, audio)
    rec.decode_stream(st)
    return st.result


def detect_script(text: str) -> str:
    deva = sum(1 for c in text if "ऀ" <= c <= "ॿ")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    return "hi" if deva > latin else "en"


def align(words: list[str], ctc_tokens: list[str], ctc_times: list[float], seg_end: float):
    """Give each Whisper word a start/end from the CTC character timestamps."""
    cchars, ctimes = [], []
    for tok, t in zip(ctc_tokens, ctc_times):
        for c in norm_chars(tok):
            cchars.append(c)
            ctimes.append(t)
    wchars, owner = [], []
    for i, w in enumerate(words):
        for c in norm_chars(w):
            wchars.append(c)
            owner.append(i)
    hits: dict[int, list[float]] = {}
    sm = difflib.SequenceMatcher(None, "".join(wchars), "".join(cchars), autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            hits.setdefault(owner[a + k], []).append(ctimes[b + k])
    out = []
    for i, w in enumerate(words):
        ts = hits.get(i)
        out.append({"w": w, "start": min(ts) if ts else None, "end": max(ts) + 0.08 if ts else None})
    # interpolate words the CTC model didn't hear the same way (e.g. English word in Hindi speech)
    first_t = ctc_times[0] if ctc_times else 0.0
    i = 0
    while i < len(out):
        if out[i]["start"] is not None:
            i += 1
            continue
        j = i
        while j < len(out) and out[j]["start"] is None:
            j += 1
        lo = out[i - 1]["end"] if i > 0 else first_t
        hi = out[j]["start"] if j < len(out) else seg_end
        lens = [max(1, len(norm_chars(out[k]["w"]))) for k in range(i, j)]
        span = max(hi - lo, 0.05 * len(lens))
        t = lo
        for k, n in zip(range(i, j), lens):
            d = span * n / sum(lens)
            out[k]["start"], out[k]["end"] = t, t + d
            t += d
        i = j
    # monotonic, no overlaps
    for k in range(len(out)):
        if k and out[k]["start"] < out[k - 1]["start"] + 0.02:
            out[k]["start"] = out[k - 1]["start"] + 0.02
        if k + 1 < len(out) and out[k + 1]["start"] is not None:
            out[k]["end"] = min(out[k]["end"], max(out[k + 1]["start"], out[k]["start"] + 0.05))
        out[k]["end"] = max(out[k]["end"], out[k]["start"] + 0.05)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--lang", default="auto", help="auto | hi | en | any Whisper language code")
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    proj = Path(args.project)
    audio, sr = sf.read(proj / "audio16k.wav", dtype="float32")
    assert sr == SR, "audio16k.wav must be 16 kHz mono"

    segs = vad_segments(audio)
    print(f"VAD: {len(segs)} speech segments")
    ctc = sherpa_onnx.OfflineRecognizer.from_omnilingual_asr_ctc(
        model=str(CTC / "model.int8.onnx"), tokens=str(CTC / "tokens.txt"), num_threads=args.threads
    )
    chunks = []
    for s, e in segs:
        a0, a1 = max(0, int((s - PAD) * SR)), min(len(audio), int((e + PAD) * SR))
        r = decode(ctc, audio[a0:a1])
        chunks.append((s, e, a0 / SR, a1, r.text, list(r.tokens), [a0 / SR + t for t in r.timestamps]))

    lang = args.lang
    if lang == "auto":
        lang = detect_script(" ".join(c[4] for c in chunks))
        print(f"language guess from speech script: {lang}")
    whisper = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=str(WHISPER / "turbo-encoder.int8.onnx"),
        decoder=str(WHISPER / "turbo-decoder.int8.onnx"),
        tokens=str(WHISPER / "turbo-tokens.txt"),
        language=lang,
        task="transcribe",
        num_threads=args.threads,
    )

    segments, all_words = [], []
    for s, e, off, a1, ctext, ctoks, ctimes in chunks:
        a0 = int(off * SR)
        wtext = decode(whisper, audio[a0:a1]).text.strip()
        words = wtext.split() if wtext else ctext.split()
        timed = align(words, ctoks, ctimes, e + PAD) if words else []
        for w in timed:
            w["start"], w["end"] = round(w["start"], 3), round(w["end"], 3)
            w["i"] = len(all_words)
            all_words.append(w)
        segments.append({"start": round(s, 3), "end": round(e, 3), "text": wtext, "ctc_text": ctext, "words": timed})
        print(f"[{s:6.2f}-{e:6.2f}] {wtext}")

    data = {"language": lang, "duration": len(audio) / SR, "segments": segments, "words": all_words}
    (proj / "transcript.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    lines = [f"[{sg['start']:6.2f}-{sg['end']:6.2f}] {sg['text']}\n    ctc: {sg['ctc_text']}" for sg in segments]
    (proj / "transcript.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {proj/'transcript.json'} ({len(all_words)} words)")


if __name__ == "__main__":
    main()
