"""
sprites.py - turns the drawings in assets/sprites/*.json into pictures.

Each JSON file stores a drawing as text. "palette" maps a letter to a color and
"rows" is the 32x32 picture, one string per row, where "." means transparent:

    "palette": {"a": "#1b1b26", "b": "#5b2a86"},
    "rows": ["..aab..", ...]

`load_all()` only reads the files (plain Python, no graphics), so the game
logic can ask "which characters exist?" without opening a window.
`SpriteBank` builds the actual pygame images and remembers them so each one
is only built once.
"""
import json
from pathlib import Path

import pygame

SPRITE_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def load_all():
    """Return {sprite_id: data} for every drawing in assets/sprites."""
    sprites = {}
    for path in sorted(SPRITE_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        sprites[path.stem] = data
    return sprites


def hex_to_rgb(text):
    text = text.lstrip("#")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


class SpriteBank:
    def __init__(self, data):
        self.data = data          # {sprite_id: json data}
        self._cache = {}

    def get(self, sprite_id, scale=2, flip=False, flash=False):
        """The picture for `sprite_id`, scaled up, optionally mirrored
        (facing left) or flashed white (just got hit)."""
        key = (sprite_id, scale, flip, flash)
        if key not in self._cache:
            base = self._build(sprite_id, flash)
            img = pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
            if flip:
                img = pygame.transform.flip(img, True, False)
            self._cache[key] = img
        return self._cache[key]

    def _build(self, sprite_id, flash):
        d = self.data[sprite_id]
        size = d.get("size", 32)
        colors = {k: hex_to_rgb(v) for k, v in d["palette"].items()}
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for y, row in enumerate(d["rows"]):
            for x, ch in enumerate(row):
                if ch in colors:
                    surf.set_at((x, y), (255, 255, 255) if flash else colors[ch])
        return surf

    def bounds(self, sprite_id):
        """(left, top, right, bottom) of the drawn pixels, in sprite pixels.
        Used to sit the drawing on its shadow no matter where it was drawn."""
        rows = self.data[sprite_id]["rows"]
        xs = [x for row in rows for x, ch in enumerate(row) if ch != "."]
        ys = [y for y, row in enumerate(rows) if row.strip(".")]
        if not xs:
            return 0, 0, 1, 1
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1
