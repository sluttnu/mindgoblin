#!/usr/bin/env python3
"""Tiny web server that shows ten Unfinity stickers in a grid.

Card JSON is fetched from the Scryfall API once and cached as a file in
./cache, so later requests (and later runs) read from disk instead.

Run:  python sticker_app.py
Open: http://localhost:8000
Only the Python standard library is used.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
PORT = 8000

STICKER_NAMES = [
    "Ancestral Hot Dog Minotaur",
    "Eldrazi Guacamole Tightrope",
    "Misunderstood Trapeze Elf",
    "Narrow-Minded Baloney Fireworks",
    "Phyrexian Midway Bamboozle",
    "Playable Delusionary Hydra",
    "Trained Blessed Mind",
    "Unassuming Gelatinous Serpent",
    "Unglued Pea-Brained Dinosaur",
    "Unsanctioned Ancient Juggler",
]

SCRYFALL_URL = "https://api.scryfall.com/cards/named?fuzzy="
# Scryfall asks API clients to send these headers.
HEADERS = {"User-Agent": "StickerGridApp/1.0", "Accept": "application/json"}


def cache_path(name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return CACHE_DIR / f"{slug}.json"


def get_card(name: str) -> dict:
    """Return card JSON from the cache file, or fetch it from Scryfall and save it."""
    path = cache_path(name)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    url = SCRYFALL_URL + urllib.parse.quote_plus(name)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    CACHE_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    time.sleep(0.1)  # be polite: Scryfall asks for 50-100 ms between requests
    return data


def image_url(card: dict) -> str | None:
    """Pull the 'normal' image URL out of the card JSON."""
    if "image_uris" in card:
        return card["image_uris"].get("normal")
    # Multi-faced cards keep images on each face
    faces = card.get("card_faces") or []
    if faces and "image_uris" in faces[0]:
        return faces[0]["image_uris"].get("normal")
    return None


def render_page() -> str:
    cells = []
    for name in STICKER_NAMES:
        try:
            card = get_card(name)
            url = image_url(card)
            if url:
                cells.append(
                    f'<figure><img src="{escape(url)}" alt="{escape(card["name"])}" '
                    f'loading="lazy"><figcaption>{escape(card["name"])}</figcaption></figure>'
                )
            else:
                cells.append(f"<figure class='err'>No image for {escape(name)}</figure>")
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            cells.append(f"<figure class='err'>{escape(name)}<br>Error: {escape(str(e))}</figure>")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unfinity Stickers</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1b1b1f; color: #eee; margin: 0; padding: 2rem; }}
  h1 {{ text-align: center; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 1.25rem; max-width: 1400px; margin: 0 auto; }}
  figure {{ margin: 0; text-align: center; }}
  img {{ width: 100%; height: auto; border-radius: 4.75%; box-shadow: 0 4px 14px rgba(0,0,0,.6); }}
  figcaption {{ margin-top: .5rem; font-size: .9rem; opacity: .8; }}
  .err {{ color: #ff8a8a; }}
</style>
</head>
<body>
<h1>Unfinity Stickers</h1>
<div class="grid">
{chr(10).join(cells)}
</div>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Serving on http://localhost:{PORT}  (cache dir: {CACHE_DIR})")
    HTTPServer(("", PORT), Handler).serve_forever()
