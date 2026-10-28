#!/usr/bin/env python3
"""Tiny web server for the Unfinity sticker reveal game.

Routes:
  /               -> index.html (next to this file)
  /api/cards      -> JSON list of {"name", "image"} for the ten stickers
  /cardback.jpg   -> cardback.jpg (next to this file; gitignored)

Card JSON is fetched from the Scryfall API once and cached as a file in
./cache, so later requests (and later runs) read from disk instead.

Run:  python sticker_app.py
Open: http://localhost:8000
Only the Python standard library is used.
"""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
PORT = int(os.environ.get("PORT", 8000))

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


def build_card_list() -> list[dict]:
    cards = []
    for name in STICKER_NAMES:
        try:
            card = get_card(name)
            url = image_url(card)
            if url:
                cards.append({"name": card["name"], "image": url})
            else:
                print(f"no image for {name}")
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            print(f"failed to load {name}: {e}")
    return cards


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str, cache: str = "no-cache"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename: str, content_type: str, cache: str = "no-cache"):
        path = BASE_DIR / filename
        if not path.is_file():
            self.send_error(404, f"{filename} not found")
            return
        self._send(path.read_bytes(), content_type, cache)

    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route in ("/", "/index.html"):
            self._send_file("index.html", "text/html; charset=utf-8")
        elif route == "/cardback.jpg":
            self._send_file("cardback.jpg", "image/jpeg")
        elif route == "/api/cards":
            body = json.dumps(build_card_list()).encode("utf-8")
            self._send(body, "application/json")
        else:
            self.send_error(404)


if __name__ == "__main__":
    build_card_list()  # warm the cache at startup
    print(f"Serving on http://localhost:{PORT}  (cache dir: {CACHE_DIR})")
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()