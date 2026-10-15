"""Text to SVG paths with shared glyphs.

Each glyph is defined once in <defs> (in font units, y up) and reused with <use>,
so long texts stay small. Fonts are variable WOFF2 files instanced at a weight.
"""

from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer


def _num(v):
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


class Face:
    def __init__(self, path: Path, key: str, weight=None):
        font = TTFont(path)
        if weight is not None and "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": weight})
        self.key = key
        self.cmap = font.getBestCmap()
        self.glyphs = font.getGlyphSet()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm
        self.used = {}

    def _gid(self, ch):
        name = self.cmap.get(ord(ch)) or self.cmap.get(ord("?"))
        if name not in self.used:
            pen = SVGPathPen(self.glyphs, ntos=_num)
            self.glyphs[name].draw(pen)
            self.used[name] = (f"{self.key}{len(self.used)}", pen.getCommands())
        return self.used[name][0], self.hmtx[name][0]

    def width(self, text, size, tracking=0.0):
        scale = size / self.upm
        total = sum(self.hmtx[self.cmap.get(ord(c)) or self.cmap.get(ord("?"))][0] for c in text)
        return total * scale + tracking * size * max(len(text) - 1, 0)

    def text(self, text, x, y, size, fill, tracking=0.0, anchor="start", extra=""):
        w = self.width(text, size, tracking)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        scale = size / self.upm
        uses = []
        cursor = 0.0
        for ch in text:
            gid, adv = self._gid(ch)
            if ch != " ":
                uses.append(f'<use href="#{gid}" x="{_num(cursor)}"/>')
            cursor += adv + tracking * self.upm
        return (
            f'<g transform="translate({_num(x)} {_num(y)}) scale({scale:.5f} -{scale:.5f})" fill="{fill}"{extra}>'
            + "".join(uses)
            + "</g>"
        )

    def defs(self):
        return "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in self.used.values() if d)


def load_faces(fonts: Path):
    return {
        "jost": Face(fonts / "jost-latin.woff2", "j", 580),
        "dm": Face(fonts / "dm-sans-latin.woff2", "d", 420),
        "dmb": Face(fonts / "dm-sans-latin.woff2", "b", 600),
        "mono": Face(fonts / "plex-mono-latin.woff2", "m"),
    }
