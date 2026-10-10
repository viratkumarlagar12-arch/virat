"""Build caption/graphic fonts as single TTF files (Latin + Devanagari where available).

Fontsource ships each family split into per-script WOFF2 subsets. Chrome (HyperFrames)
and Pillow both want one file per weight, so we decompress the subsets and merge them.

usage: python fonts.py <node_modules/@fontsource> <out_dir>
"""
import sys
from pathlib import Path

from fontTools.merge import Merger
from fontTools.ttLib import TTFont

# family dir -> (output name, weights)
FAMILIES = {
    "poppins": ("Poppins", [500, 600, 700, 800, 900]),
    "montserrat": ("Montserrat", [600, 700, 800, 900]),
    "anton": ("Anton", [400]),
    "bebas-neue": ("BebasNeue", [400]),
    "mukta": ("Mukta", [500, 700, 800]),
    "noto-sans-devanagari": ("NotoSansDevanagari", [500, 700, 800]),
    "inter": ("Inter", [400, 500, 600, 700, 800, 900]),
}
SUBSETS = ["latin", "latin-ext", "devanagari"]


def build(src_root: Path, out: Path, fam_dir: str, name: str, weight: int) -> Path | None:
    files = src_root / fam_dir / "files"
    parts = []
    for sub in SUBSETS:
        p = files / f"{fam_dir}-{sub}-{weight}-normal.woff2"
        if p.exists():
            tmp = out / f".{fam_dir}-{sub}-{weight}.ttf"
            f = TTFont(p)
            f.flavor = None
            f.save(tmp)
            parts.append(tmp)
    if not parts:
        return None
    dest = out / f"{name}-{weight}.ttf"
    if len(parts) == 1:
        parts[0].rename(dest)
    else:
        try:
            Merger().merge([str(p) for p in parts]).save(dest)
        except Exception as e:  # subsets that refuse to merge: keep Latin only
            print(f"  merge failed for {name}-{weight} ({e}); using latin only")
            parts[0].rename(dest)
        for p in parts:
            p.unlink(missing_ok=True)
    return dest


def main():
    src_root, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for fam_dir, (name, weights) in FAMILIES.items():
        for w in weights:
            dest = out / f"{name}-{w}.ttf"
            if dest.exists():
                continue
            r = build(src_root, out, fam_dir, name, w)
            print(f"  {dest.name}: {'ok' if r else 'missing'}")


if __name__ == "__main__":
    main()
