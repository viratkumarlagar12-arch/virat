"""Copyright-free background-music bed, composed and synthesized from scratch.

Moods: upbeat (explainer / motivation), lofi (story / calm), cinematic (big reveal / facts),
tech (AI / coding / fast facts), suspense (puzzle / countdown), documentary (history / science facts; piano +
strings, audible on phone speakers).
If you have a track you prefer (e.g. from YouTube Audio Library), put it in the plan instead.

usage: python music.py <out.wav> --mood upbeat --duration 45 [--bpm 112] [--seed 3]
"""
import argparse

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000

MOODS = {
    #            bpm  root  scale    progression (scale degrees, 0-based)   swing
    "upbeat":    (112, 60, "major", [0, 4, 5, 3], 0.0),
    "lofi":      (82, 57, "minor", [0, 5, 2, 6], 0.18),
    "cinematic": (92, 57, "minor", [0, 5, 2, 6], 0.0),
    "tech":      (122, 57, "minor", [0, 0, 5, 6], 0.0),
    "suspense":  (100, 50, "minor", [0, 0, 1, 0], 0.0),
    # piano ostinato + strings + bell over a soft pulse: most of its energy is in the mids, so it is still heard on
    # phone speakers (the other cinematic bed is mostly sub-bass and disappears on a phone)
    "documentary": (90, 57, "minor", [0, 5, 2, 6], 0.0),
}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10]}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord(root, scale, degree, size=4):
    s = SCALES[scale]
    return [root + s[(degree + 2 * k) % 7] + 12 * ((degree + 2 * k) // 7) for k in range(size)]


def lp(x, f, order=2):
    return sosfilt(butter(order, min(f, SR / 2 - 100), "lowpass", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x, axis=0)


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.1):
    e = np.full(n, s)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    nd = min(nd, n - na)
    e[na : na + nd] = np.linspace(1, s, nd)
    nr = min(nr, n)
    e[n - nr :] *= np.linspace(1, 0, nr)
    return e


def saw(f, n, harmonics=14):
    t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harmonics + 1) if f * k < SR / 2.2)


class Mix:
    def __init__(self, n):
        self.buf = np.zeros((n, 2))

    def add(self, x, start, gain=1.0, pan=0.0):
        s = int(start * SR)
        if s >= len(self.buf):
            return
        x = x[: len(self.buf) - s]
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.buf[s : s + len(x), 0] += x * gain * l * 1.414
        self.buf[s : s + len(x), 1] += x * gain * r * 1.414


def kick(rng):
    t = np.arange(int(0.45 * SR)) / SR
    f = 120 * np.exp(-t * 30) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) + 0.1 * rng.standard_normal(len(t)) * np.exp(-t * 200)


def snare(rng, soft=False):
    t = np.arange(int(0.25 * SR)) / SR
    nz = sosfilt(butter(2, [1200, 7000], "bandpass", fs=SR, output="sos"), rng.standard_normal(len(t)))
    x = nz * np.exp(-t * (22 if soft else 16)) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return x * (0.6 if soft else 1)


def hat(rng, open_=False):
    t = np.arange(int((0.18 if open_ else 0.05) * SR)) / SR
    return hp(rng.standard_normal(len(t)), 7500) * np.exp(-t * (18 if open_ else 90))


def pluck(f, d, rng):
    """Karplus-Strong string"""
    n = int(d * SR)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return lp(out, 5000)


def epiano(f, d):
    n = int(d * SR)
    t = np.arange(n) / SR
    idx = 1.8 * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t))
    x += 0.15 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 12)
    return x * np.exp(-t * 1.2) * adsr(n, 0.004, 0.2, 0.8, 0.15) * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t))


def pad(freqs, d, cutoff=1400, attack=0.35):
    n = int(d * SR)
    x = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):
            x += saw(f * 2 ** (det / 12), n, 10)
    return lp(x / (3 * len(freqs)), cutoff) * adsr(n, attack, 0.3, 0.8, 0.4)


def piano(f, d, vel=1.0):
    """soft 'felt' piano: slightly stretched partials, the higher ones dying faster"""
    n = int(d * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        if fk > SR / 2.2:
            break
        x += np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.4 + 0.8 * k)) / k ** 1.4
    x = lp(x * adsr(n, 0.004, 0.05, 1.0, 0.08), 2600 + 1400 * vel)
    return x / (np.max(np.abs(x)) + 1e-9) * vel


def bell(f, d):
    """mallet / celesta: inharmonic partials, long ring"""
    n = int(d * SR)
    t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * dk)
            for r, a, dk in ((1, 1.0, 1.6), (2.76, 0.35, 3.5), (5.4, 0.15, 7), (8.93, 0.06, 12)) if f * r < SR / 2.2)
    return x * adsr(n, 0.002, 0.05, 1.0, 0.2)


def reverb(x, secs=1.8, mix=0.22, seed=1):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-t * 6.9 / secs)[:, None]
    ir = lp(ir, 6000)
    wet = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return x * (1 - mix) + wet * mix


def compose(mood, duration, bpm=None, seed=3):
    rng = np.random.default_rng(seed)
    bpm0, root, scale, prog, swing = MOODS[mood]
    bpm = bpm or bpm0
    beat = 60 / bpm
    bar = 4 * beat
    nbars = int(np.ceil((duration + 1.5) / bar))
    total = nbars * bar + 2.0
    drums, bass, keys, pads, lead = (Mix(int(total * SR)) for _ in range(5))
    K, S, H = kick(rng), snare(rng, soft=mood == "lofi"), hat(rng)
    side = np.ones(int(total * SR))

    for b in range(nbars):
        t0 = b * bar
        deg = prog[b % len(prog)]
        ch = chord(root, scale, deg, 4)
        intro = b == 0
        # ---- drums
        if mood in ("upbeat", "tech"):
            for q in range(4):
                if not intro or q >= 2:
                    drums.add(K, t0 + q * beat, 0.9)
                    s = int((t0 + q * beat) * SR)
                    L = int(0.25 * SR)
                    side[s : s + L] = np.minimum(side[s : s + L], 1 - 0.45 * np.exp(-np.arange(L) / SR * 14))
            if not intro:
                for q in (1, 3):
                    drums.add(S, t0 + q * beat, 0.45)
            for e in range(8):
                drums.add(H, t0 + e * beat / 2, 0.22 if e % 2 else 0.12, pan=0.3)
        elif mood == "lofi":
            pattern_k = [0, 1.5, 2.25] if b % 2 else [0, 2.5]
            for q in pattern_k:
                drums.add(K, t0 + q * beat, 0.75)
            for q in (1, 3):
                drums.add(S, t0 + q * beat + 0.01, 0.5)
            for e in range(8):
                sw = swing * beat / 2 if e % 2 else 0
                drums.add(H, t0 + e * beat / 2 + sw, 0.12 * rng.uniform(0.6, 1), pan=0.25)
        elif mood == "cinematic":
            drums.add(K, t0, 0.9)
            if b % 2:
                drums.add(K, t0 + 2.5 * beat, 0.6)
            drums.add(S, t0 + 2 * beat, 0.3)
        elif mood == "suspense":
            for q in range(4):
                drums.add(hat(rng), t0 + q * beat, 0.25, pan=-0.2)  # clock tick
            drums.add(K, t0, 0.6)
        elif mood == "documentary" and 2 <= b < nbars - 1:  # heartbeat pulse once the piano has set the mood
            drums.add(K, t0, 0.5)
            drums.add(K, t0 + 2 * beat, 0.25)

        # ---- bass
        bnote = hz(ch[0] - 12)
        if mood == "documentary":
            if b >= 1:
                n = int(bar * SR)
                bass.add(np.sin(2 * np.pi * bnote * np.arange(n) / SR) * adsr(n, 0.08, 0.3, 0.8, 0.3), t0, 0.3)
        elif mood in ("upbeat", "tech", "cinematic"):
            for e in range(8):
                d = beat / 2 * 0.9
                n = int(d * SR)
                x = np.sin(2 * np.pi * bnote * np.arange(n) / SR) + 0.25 * saw(bnote, n, 6)
                bass.add(np.tanh(1.5 * x) * adsr(n, 0.005, 0.08, 0.6, 0.05), t0 + e * beat / 2, 0.38 if e % 2 else 0.45)
        else:
            for half in (0, 2):
                n = int(2 * beat * 0.9 * SR)
                x = np.sin(2 * np.pi * bnote * np.arange(n) / SR)
                bass.add(x * adsr(n, 0.02, 0.4, 0.4, 0.2), t0 + half * beat, 0.22)

        # ---- harmony
        if mood == "lofi":
            for k, m in enumerate(ch):
                keys.add(epiano(hz(m), bar * 0.95), t0 + k * 0.012 + swing * 0.05, 0.22, pan=(k - 1.5) * 0.15)
        elif mood == "documentary":  # strings: brighter than the pad, slow swell, top voice an octave up
            pads.add(pad([hz(m) for m in ch] + [hz(ch[0] + 12)], bar, cutoff=2400, attack=0.7), t0,
                     0.22 if intro else 0.32)
        else:
            pads.add(pad([hz(m) for m in ch], bar), t0, 0.5 if mood != "suspense" else 0.35)

        # ---- melody / arpeggio
        if mood in ("upbeat", "tech") and not intro:
            steps = 8 if mood == "upbeat" else 16
            arp = ch + [ch[1] + 12]
            for e in range(steps):
                m = arp[(e * (2 if mood == "upbeat" else 1)) % len(arp)] + 12
                lead.add(pluck(hz(m), beat / (steps / 4) * 1.6, rng), t0 + e * bar / steps, 0.3,
                         pan=0.35 if e % 2 else -0.35)
        elif mood == "lofi" and b % 2 == 1:
            for e, off in enumerate((0, 0.75, 1.5, 3)):
                m = ch[(e + 1) % 4] + 12
                lead.add(epiano(hz(m), beat), t0 + off * beat, 0.1, pan=0.2)
        elif mood == "documentary":
            # piano ostinato in 8ths (A4-G5 range), accents on the beat; a bell on the chord's fifth every bar
            arp = [ch[0], ch[1], ch[2], ch[1], ch[3], ch[1], ch[2], ch[1]]
            last = b == nbars - 1
            for e in range(1 if last else 8):
                vel = (0.8 if e % 2 == 0 else 0.58) * rng.uniform(0.9, 1.05)
                keys.add(piano(hz(arp[e] + 12), bar if last else beat * 2, vel), t0 + e * beat / 2, 0.42,
                         pan=0.18 if e % 2 else -0.18)
            if b >= 1:
                lead.add(bell(hz(ch[2] + 24), bar), t0, 0.1, pan=0.3)

    side2 = side[:, None]
    keys_mix = reverb(keys.buf, 2.0, 0.3, seed=2) if mood == "documentary" else keys.buf
    music = (drums.buf * 0.9 + bass.buf * side2 + keys_mix * side2 + reverb(pads.buf, 2.4, 0.35) * side2
             + reverb(lead.buf, 1.6, 0.3) * side2)
    if mood == "lofi":
        music = lp(music, 4200)
        crackle = np.zeros(len(music))
        idx = rng.integers(0, len(music), int(total * 25))
        crackle[idx] = rng.uniform(-0.3, 0.3, len(idx))
        music += np.stack([crackle, crackle], 1) * 0.15 + rng.standard_normal((len(music), 2)) * 0.003
    music = hp(music, 50)
    n = int((duration + 1.5) * SR)
    music = music[:n]
    fo = int(1.5 * SR)
    music[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    music[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    music = np.tanh(music / (np.max(np.abs(music)) + 1e-9) * 1.4) / np.tanh(1.4)
    return (music * 10 ** (-1.5 / 20)).astype(np.float32), bpm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--mood", default="upbeat", choices=list(MOODS))
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    music, bpm = compose(a.mood, a.duration, a.bpm, a.seed)
    sf.write(a.out, music, SR, subtype="PCM_16")
    print(f"wrote {a.out} ({a.mood}, {bpm} bpm, {len(music)/SR:.1f}s)")


if __name__ == "__main__":
    main()
