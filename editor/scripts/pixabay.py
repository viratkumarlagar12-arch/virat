"""Licence-free stock b-roll and photos from Pixabay (free for commercial use, no attribution needed).

1) search:   python pixabay.py search "underwater swimmer" [--images] [--vertical] [-n 12] [--sheet out.jpg]
   -> one line per hit (id, duration, size, tags); --sheet tiles the thumbnails so I can look at them
2) get:      python pixabay.py get <id> [<id> ...] --out projects/<name>/media [--images] [--size large|medium|small]
   -> projects/<name>/media/pixabay_<id>.mp4 (or .jpg) — reference it from edl.json or a plan overlay

The key comes from env PIXABAY_API_KEY. Anything pasted around it ("Your key: ...") is ignored.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API = "https://pixabay.com/api/"
FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Inter-700.ttf"


def api_key():
    raw = os.environ.get("PIXABAY_API_KEY", "")
    m = re.search(r"\d{5,12}-[0-9a-f]{20,40}", raw)
    if not m:
        sys.exit("PIXABAY_API_KEY is not set (or holds no key like 12345678-abc...): add it to the environment")
    return m.group(0)


def fetch(url):
    # Pixabay answers 403 to urllib's default "Python-urllib" user agent
    req = urllib.request.Request(url, headers={"User-Agent": "virat-shorts-editor/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def query(q, images=False, vertical=False, n=12, page=1):
    params = {"key": api_key(), "q": q[:100], "per_page": max(3, min(n, 200)), "page": page, "safesearch": "true"}
    if images:
        params["image_type"] = "photo"
        if vertical:
            params["orientation"] = "vertical"
    hits = json.loads(fetch(API + ("" if images else "videos/") + "?" + urllib.parse.urlencode(params)))["hits"]
    if vertical and not images:  # the video API has no orientation filter
        hits = [h for h in hits if h["videos"]["medium"]["height"] >= h["videos"]["medium"]["width"]] or hits
    return hits


def describe(h, images):
    if images:
        return f'{h["id"]:>9}  {h["imageWidth"]}x{h["imageHeight"]:<6}            {h["tags"]}'
    v = next((h["videos"][k] for k in ("large", "medium", "small", "tiny") if h["videos"][k]["width"]), h["videos"]["tiny"])
    return f'{h["id"]:>9}  {v["width"]}x{v["height"]:<6} {h["duration"]:>3}s {v["size"] / 1e6:6.1f}MB  {h["tags"]}'


def sheet(hits, images, out):
    tw, th, cols = 320, 240, 4
    rows = (len(hits) + cols - 1) // cols
    img = Image.new("RGB", (tw * cols, th * rows), "black")
    font = ImageFont.truetype(str(FONT), 22) if FONT.exists() else ImageFont.load_default()
    d = ImageDraw.Draw(img)
    for i, h in enumerate(hits):
        url = h["webformatURL"] if images else h["videos"]["tiny"]["thumbnail"]
        try:
            t = Image.open(io.BytesIO(fetch(url))).convert("RGB")
        except Exception:
            continue
        t.thumbnail((tw, th))
        x, y = (i % cols) * tw, (i // cols) * th
        img.paste(t, (x + (tw - t.width) // 2, y + (th - t.height) // 2))
        label = str(h["id"]) + ("" if images else f' {h["duration"]}s')
        d.rectangle([x, y, x + 12 * len(label) + 10, y + 28], fill="black")
        d.text((x + 5, y + 2), label, font=font, fill="yellow")
    img.save(out, quality=85)
    print("sheet:", out)


def get(ids, out, images=False, size="large"):
    out.mkdir(parents=True, exist_ok=True)
    for pid in ids:
        params = {"key": api_key(), "id": pid}
        hits = json.loads(fetch(API + ("" if images else "videos/") + "?" + urllib.parse.urlencode(params)))["hits"]
        if not hits:
            print(f"{pid}: not found")
            continue
        h = hits[0]
        if images:
            url, dst = h.get("largeImageURL") or h["webformatURL"], out / f"pixabay_{pid}.jpg"
        else:
            order = ["large", "medium", "small", "tiny"]
            order = order[order.index(size):] + order[:order.index(size)][::-1]
            v = next(h["videos"][k] for k in order if h["videos"][k]["url"])
            url, dst = v["url"], out / f"pixabay_{pid}.mp4"
        subprocess.run(["curl", "-fsSL", "--retry", "4", "-o", str(dst), url], check=True)
        print(f"{dst}  ({describe(h, images).strip()})  {h['pageURL']}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("q")
    s.add_argument("--images", action="store_true")
    s.add_argument("--vertical", action="store_true")
    s.add_argument("-n", type=int, default=12)
    s.add_argument("--page", type=int, default=1)
    s.add_argument("--sheet")
    g = sub.add_parser("get")
    g.add_argument("ids", nargs="+")
    g.add_argument("--out", required=True)
    g.add_argument("--images", action="store_true")
    g.add_argument("--size", default="large", choices=["large", "medium", "small", "tiny"])
    a = ap.parse_args()
    if a.cmd == "search":
        hits = query(a.q, a.images, a.vertical, a.n, a.page)
        for h in hits:
            print(describe(h, a.images))
        if a.sheet and hits:
            sheet(hits, a.images, a.sheet)
    else:
        get(a.ids, Path(a.out), a.images, a.size)


if __name__ == "__main__":
    main()
