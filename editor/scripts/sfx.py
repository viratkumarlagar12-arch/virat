"""Copyright-free sound-effect library, synthesized from scratch (no licences to worry about).

usage: python sfx.py [out_dir]     -> writes whoosh.wav, pop.wav, ding.wav, ... (48 kHz stereo)
"""
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def env(n, a, d, curve=4.0):
    """attack seconds a, exponential decay over the rest"""
    na = max(1, int(a * SR))
    e = np.ones(n)
    e[:na] = np.linspace(0, 1, na) ** 2
    rest = n - na
    if rest > 0:
        e[na:] = np.exp(-curve * np.linspace(0, 1, rest))
    return e


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)


def sweep_filter_noise(d, f0, f1, q=0.6, block=256):
    """noise through a band-pass whose centre glides f0 -> f1 (the classic whoosh)"""
    n = int(d * SR)
    noise = rng.standard_normal(n + block)
    out = np.zeros(n)
    centers = np.geomspace(f0, f1, n // block + 1)
    zi = None
    for k, c in enumerate(centers):
        s = k * block
        if s >= n:
            break
        lo, hi = c * (1 - q / 2), min(c * (1 + q / 2), SR / 2 - 100)
        sos = butter(2, [lo, hi], "bandpass", fs=SR, output="sos")
        seg = noise[s : s + block]
        if zi is None:
            from scipy.signal import sosfilt_zi
            zi = sosfilt_zi(sos) * 0
        y, zi = sosfilt(sos, seg, zi=zi)
        out[s : s + len(y)] = y[: n - s]
    return out


def stereo(x, width=0.0):
    if width <= 0:
        return np.stack([x, x], 1)
    d = int(0.012 * SR * width)
    r = np.concatenate([np.zeros(d), x[:-d]]) if d else x
    return np.stack([x, 0.7 * x + 0.3 * r], 1)


def norm(x, peak_db=-3.0):
    m = np.max(np.abs(x)) or 1.0
    return x / m * 10 ** (peak_db / 20)


def fade(x, fin=0.003, fout=0.02):
    n = len(x)
    a, b = int(fin * SR), int(fout * SR)
    x = x.copy()
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[-b:] *= np.linspace(1, 0, b)
    return x


# ---------------------------------------------------------------- effects
def whoosh(d=0.55, f0=350, f1=4500):
    n = int(d * SR)
    x = sweep_filter_noise(d, f0, f1, q=0.9)
    e = np.sin(np.linspace(0, np.pi, n)) ** 1.6
    return stereo(fade(norm(x * e, -4)), 1)


def swoosh():  # short fast one for small text slides
    return whoosh(0.28, 900, 7000)


def whoosh_down():
    return whoosh(0.6, 5000, 300)


def pop():
    t = t_(0.12)
    f = 900 * np.exp(-t * 38) + 260
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 0.12, 9)
    click = hp(rng.standard_normal(len(t)), 3000) * env(len(t), 0.0005, 0.01, 60) * 0.3
    return stereo(fade(norm(x + click, -4), 0.001, 0.01))


def bubble():  # softer, rounder pop for captions/emoji
    t = t_(0.09)
    f = 500 + 1400 * (t / t[-1])
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / t[-1]) ** 2
    return stereo(fade(norm(x, -6), 0.001, 0.005))


def click():
    t = t_(0.04)
    x = bp(rng.standard_normal(len(t)), 1800, 6000) * env(len(t), 0.0003, 0.04, 30)
    x += 0.4 * np.sin(2 * np.pi * 2200 * t) * env(len(t), 0.0003, 0.04, 50)
    return stereo(fade(norm(x, -6), 0.0005, 0.005))


def tick():
    t = t_(0.06)
    x = np.sin(2 * np.pi * 1600 * t) * env(len(t), 0.0005, 0.06, 40)
    x += 0.5 * hp(rng.standard_normal(len(t)), 4000) * env(len(t), 0.0003, 0.02, 80)
    return stereo(fade(norm(x, -6), 0.0005, 0.005))


def _bell(f, d, partials=((1, 1), (2.76, 0.45), (5.4, 0.25), (8.93, 0.12)), decay=5):
    t = t_(d)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * decay * (1 + r / 3)) for r, a in partials)
    return x * env(len(t), 0.002, d, 0.5)


def ding():
    return stereo(fade(norm(_bell(1318.5, 1.4), -5)), 0.5)


def cash():  # "ka-ching" for money/numbers
    x = np.zeros(int(1.1 * SR))
    for start, f in ((0.0, 2093), (0.09, 2637)):
        b = _bell(f, 1.0, decay=6)
        s = int(start * SR)
        x[s : s + len(b)] += b[: len(x) - s]
    rattle = bp(rng.standard_normal(len(x)), 4000, 9000) * env(len(x), 0.001, 0.25, 25) * 0.25
    return stereo(fade(norm(x + rattle, -5)), 0.6)


def success():  # rising major arpeggio
    x = np.zeros(int(1.0 * SR))
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        b = _bell(f, 0.7, partials=((1, 1), (2, 0.3), (3, 0.1)), decay=6)
        s = int(k * 0.07 * SR)
        x[s : s + len(b)] += b[: len(x) - s]
    return stereo(fade(norm(x, -5)), 0.6)


def riser(d=1.6):
    t = t_(d)
    noise = sweep_filter_noise(d, 300, 9000, q=1.2)
    tone = sum(np.sin(2 * np.pi * np.cumsum(f0 * np.geomspace(1, 4, len(t))) / SR) for f0 in (110, 111.5, 220.7))
    e = (t / d) ** 2.2
    return stereo(fade(norm((noise + 0.25 * tone) * e, -4), 0.01, 0.01), 1)


def impact():  # deep boom for big statements / hook
    t = t_(1.4)
    f = 90 * np.exp(-t * 6) + 38
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.002, 1.4, 4)
    crack = lp(rng.standard_normal(len(t)), 2500) * env(len(t), 0.0005, 0.25, 18)
    return stereo(fade(norm(sub + 0.35 * crack, -2)), 0.3)


def glitch():
    n = int(0.3 * SR)
    x = np.zeros(n)
    for _ in range(9):
        s = rng.integers(0, n - 2000)
        L = rng.integers(400, 2000)
        f = rng.choice([180, 440, 880, 1760, 3520])
        x[s : s + L] += np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * 0.5
    x += bp(rng.standard_normal(n), 2000, 8000) * 0.2
    return stereo(fade(norm(x, -8), 0.001, 0.01), 0.7)


def typing(d=1.2):
    n = int(d * SR)
    x = np.zeros(n)
    s = 0
    while s < n - 3000:
        c = click()[:, 0] * rng.uniform(0.4, 0.9)
        x[s : s + len(c)] += c[: n - s]
        s += int(rng.uniform(0.06, 0.14) * SR)
    return stereo(fade(norm(x, -8)))


def camera():
    a = click()[:, 0]
    x = np.zeros(int(0.25 * SR))
    x[: len(a)] += a
    s = int(0.09 * SR)
    x[s : s + len(a)] += 0.8 * a
    x += bp(rng.standard_normal(len(x)), 1500, 5000) * env(len(x), 0.001, 0.25, 20) * 0.3
    return stereo(fade(norm(x, -6)))


def slam():  # impact with a mid-range crack: still hits on phone speakers, which drop everything under ~200 Hz
    x = impact()[:, 0]
    n = len(x)
    x = x + 0.8 * norm(bp(rng.standard_normal(n), 150, 1200) * env(n, 0.001, 0.15, 20), -2)
    return stereo(fade(norm(x, -2)), 0.3)


def heartbeat():  # one "lub-dub"; place a few in a row (closer together = rising tension)
    x = np.zeros(int(0.7 * SR))
    for start, f0, amp in ((0.0, 62, 1.0), (0.24, 74, 0.7)):
        t = t_(0.22)
        f = f0 * (1 + 0.6 * np.exp(-t * 40))
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.45 * np.sin(2 * np.pi * np.cumsum(2.1 * f) / SR)
        thud = bp(rng.standard_normal(len(t)), 160, 900) * env(len(t), 0.001, 0.06, 26) * 3.2  # mids so phones hear it
        knock = np.sin(2 * np.pi * np.cumsum(f * 7.5) / SR) * env(len(t), 0.001, 0.05, 40) * 0.9  # ~500 Hz "knock"
        b = (body * env(len(t), 0.004, 0.22, 9) + thud + knock) * amp
        s = int(start * SR)
        x[s : s + len(b)] += b
    return stereo(fade(norm(hp(x, 35), -3), 0.001, 0.03))


def breath():  # soft exhale/relief — band-passed noise swell
    t = t_(0.75)
    x = bp(rng.standard_normal(len(t)), 350, 2600) * np.sin(np.pi * (t / t[-1]) ** 0.6) ** 1.5
    x += 0.4 * bp(rng.standard_normal(len(t)), 2600, 6000) * np.sin(np.pi * t / t[-1]) ** 3
    return stereo(fade(norm(x, -8), 0.02, 0.08), 0.5)


LIBRARY = {
    "whoosh": whoosh, "swoosh": swoosh, "whoosh_down": whoosh_down, "pop": pop, "bubble": bubble,
    "click": click, "tick": tick, "ding": ding, "cash": cash, "success": success, "riser": riser,
    "impact": impact, "glitch": glitch, "typing": typing, "camera": camera, "heartbeat": heartbeat, "breath": breath,
    "slam": slam,
}


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "assets" / "sfx")
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in LIBRARY.items():
        sf.write(out / f"{name}.wav", fn().astype(np.float32), SR, subtype="PCM_16")
        print("  ", name)


if __name__ == "__main__":
    main()
