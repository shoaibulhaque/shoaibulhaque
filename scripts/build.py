"""Builds README.md and its images from profile.json and live GitHub data.

Usage:  python scripts/build.py
Needs:  pip install fonttools brotli
Token:  GITHUB_TOKEN from the environment, or `gh auth token` when run locally.

README.md is generated. Edit profile.json, then run this script. The "profile"
GitHub Action runs it on every change to profile.json and once a day, so
project stars, dates, descriptions, and "Recently active" stay current.

Style: the hand-drawn look of the LinkedIn cover. Cream paper, ink outlines,
a few marker colours, and lots of empty space.
"""

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from svgtext import load_faces  # noqa: E402

FONTS = ROOT / "fonts"
GEN = ROOT / "assets" / "generated"
DATA = json.loads((ROOT / "profile.json").read_text())
ICONS = json.loads((ROOT / "assets" / "icons" / "icons.json").read_text())["icons"]
USER = os.environ.get("PROFILE_USER", "shoaibulhaque")

THEMES = {
    "light": dict(
        paper="#F7F5F0", card="#FBFAF7", line="#E6E2D8", ink="#1A1A1A", muted="#5F5B54",
        blue="#1D6AE5", purple="#9B7BEA", lilac="#DCD3FA", green="#2E9E5B", orange="#F08A32",
        pink="#F29CC3", yellow="#F2B732", chip="#EFECE4",
    ),
    "dark": dict(
        paper="#15171C", card="#1A1D23", line="#2A2E36", ink="#EDEBE6", muted="#A19C93",
        blue="#5B9CFF", purple="#B8A0FF", lilac="#3B3355", green="#4CC07E", orange="#FF9F4D",
        pink="#FF9ECB", yellow="#FFCB52", chip="#23262D",
    ),
}
MARKERS = ["purple", "green", "orange", "pink", "blue"]
ALIASES = {"java": "openjdk", "bash": "gnubash", "claude code": "claude", "gemini": "googlegemini"}

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178C6", "JavaScript": "#F1E05A", "Go": "#00ADD8", "Java": "#B07219",
    "HTML": "#E34C26", "CSS": "#663399", "Shell": "#89E051", "Jupyter Notebook": "#DA5B0B", "C": "#555555",
}


# ---------------------------------------------------------------- GitHub data

def token():
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


TOKEN = token()


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-build")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def public_repos():
    repos, page = [], 1
    while True:
        batch = api(f"users/{USER}/repos?per_page=100&sort=pushed&page={page}")
        repos += [r for r in batch if not r["fork"] and not r["archived"] and not r["private"]]
        if len(batch) < 100:
            return repos
        page += 1


def month(iso):
    return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %Y")


def short(text, limit=90):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "..."


# ---------------------------------------------------------------- drawing helpers

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(face, text, size, max_w, max_lines=None):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if face.width(test, size) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while face.width(last + "...", size) > max_w and " " in last:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "..."
    return lines


def svg(w, h, title, desc, faces, css, body):
    defs = "".join(face.defs() for face in faces.values())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc><defs>{defs}</defs>'
        "<style>"
        ".draw{stroke-dasharray:1 1;animation:draw 7s ease-in-out infinite}"
        "@keyframes draw{0%{stroke-dashoffset:1}22%,92%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}"
        ".twinkle{animation:twinkle 2.8s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
        "@keyframes twinkle{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(0.6);opacity:0.5}}"
        ".bob{animation:bob 3.2s ease-in-out infinite}"
        "@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-3px)}}"
        ".caret{animation:blink 1.1s steps(1) infinite}@keyframes blink{50%{opacity:0}}"
        + "".join(css)
        + "@media (prefers-reduced-motion: reduce){*{animation:none!important}.fly{display:none}.draw{stroke-dasharray:none}}"
        "</style>" + "".join(body) + "</svg>\n"
    )


def paper(w, h, c, rx=18):
    return (
        f'<rect width="{w}" height="{h}" rx="{rx}" fill="{c["paper"]}"/>'
        f'<rect x="0.75" y="0.75" width="{w - 1.5}" height="{h - 1.5}" rx="{rx - 0.75}" fill="none" stroke="{c["line"]}" stroke-width="1.5"/>'
    )


def stroke(c, color=None, width=2.6, fill="none"):
    return f'fill="{fill}" stroke="{color or c["ink"]}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"'


def underline(x, y, w, color, cls="draw", delay=0.0, amp=3.2):
    """A hand-drawn wavy marker underline."""
    steps = max(int(w / 18), 3)
    seg = w / steps
    d = f"M{x:.1f} {y:.1f}"
    for i in range(steps):
        sign = -1 if i % 2 == 0 else 1
        d += f" q{seg / 2:.1f} {sign * amp:.1f} {seg:.1f} 0"
    return (
        f'<path class="{cls}" style="animation-delay:{delay:.1f}s" pathLength="1" d="{d}" '
        f'fill="none" stroke="{color}" stroke-width="3.4" stroke-linecap="round"/>'
    )


def sparkle(cx, cy, r, color, delay=0.0):
    k = r * 0.28
    d = f"M{cx} {cy - r} Q{cx + k} {cy - k} {cx + r} {cy} Q{cx + k} {cy + k} {cx} {cy + r} Q{cx - k} {cy + k} {cx - r} {cy} Q{cx - k} {cy - k} {cx} {cy - r}Z"
    return f'<path class="twinkle" style="animation-delay:{delay:.1f}s" d="{d}" fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round"/>'


def scribble(x, y, w, h, color, delay=0.0):
    """A loose marker zigzag, like the corner strokes on the cover."""
    n, d = 7, f"M{x:.1f} {y + h:.1f}"
    for i in range(1, n + 1):
        px = x + w * i / n
        py = y if i % 2 else y + h
        d += f" L{px:.1f} {py:.1f}"
    return (
        f'<path class="draw" style="animation-delay:{delay:.1f}s" pathLength="1" d="{d}" fill="none" '
        f'stroke="{color}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" opacity="0.55"/>'
    )


# ---------------------------------------------------------------- hero

def hero(theme):
    c, f = THEMES[theme], load_faces(FONTS)
    jost, dm, mono = f["jost"], f["dm"], f["mono"]
    W, H = 1000, 300
    b, css = [paper(W, H, c)], []

    # Corner marker strokes, like the cover. Two only.
    b.append(f'<clipPath id="clip"><rect width="{W}" height="{H}" rx="18"/></clipPath><g clip-path="url(#clip)">')
    b.append(scribble(-24, 18, 120, 30, c["purple"]))
    b.append(scribble(880, 262, 140, 30, c["green"], delay=0.6))
    b.append("</g>")

    # Words.
    x = 56
    b.append(dm.text(f'{DATA["name"]} · {DATA["role"].lower()} · {DATA["location"].split(",")[0]}', x, 84, 16, c["muted"]))
    size, line1_y, line2_y = 46, 148, 206
    b.append(jost.text(DATA["headline"][0], x - 2, line1_y, size, c["ink"]))
    line2 = DATA["headline"][1]
    hl = DATA.get("highlight", "")
    head = line2[: len(line2) - len(hl)] if hl and line2.endswith(hl) else line2
    b.append(jost.text(head, x - 2, line2_y, size, c["ink"]))
    if hl and line2.endswith(hl):
        hx = x - 2 + jost.width(head, size)
        b.append(jost.text(hl, hx, line2_y, size, c["blue"]))
        b.append(underline(hx + 2, line2_y + 16, jost.width(hl.rstrip("."), size) - 4, c["blue"], delay=0.4))

    # Cloud with three small boxes hanging from it.
    cx, cy = 690, 92
    cloud = (f"M{cx - 52} {cy + 22} a20 20 0 0 1 6 -38 a28 28 0 0 1 52 -10 a22 22 0 0 1 40 14 "
             f"a18 18 0 0 1 4 34 z")
    b.append(f'<path class="draw" pathLength="1" d="{cloud}" {stroke(c, c["blue"])}/>')
    for i, (dx, col) in enumerate([(-34, c["purple"]), (0, c["green"]), (34, c["orange"])]):
        bx = cx + dx
        b.append(f'<line x1="{bx}" y1="{cy + 26}" x2="{bx}" y2="{cy + 58}" {stroke(c, c["ink"], 2)} stroke-dasharray="3 5" opacity="0.55"/>')
        b.append(f'<rect class="bob" style="animation-delay:{i * 0.4:.1f}s" x="{bx - 9}" y="{cy + 60}" width="18" height="16" rx="3" {stroke(c, col, 2.4)}/>')

    # API hub: a soft lilac blob with five spokes.
    ax, ay = 880, 112
    b.append(f'<circle cx="{ax}" cy="{ay}" r="44" fill="{c["lilac"]}"/>')
    for k in range(5):
        import math
        ang = -math.pi / 2 + k * 2 * math.pi / 5
        x1, y1 = ax + 17 * math.cos(ang), ay + 17 * math.sin(ang)
        x2, y2 = ax + 34 * math.cos(ang), ay + 34 * math.sin(ang)
        b.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" {stroke(c, c["ink"], 1.8)}/>')
        b.append(f'<circle class="twinkle" style="animation-delay:{k * 0.35:.2f}s" cx="{x2:.1f}" cy="{y2:.1f}" r="3.6" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="1.8"/>')
    b.append(f'<rect x="{ax - 19}" y="{ay - 11}" width="38" height="22" rx="4" fill="{c["paper"]}" stroke="{c["ink"]}" stroke-width="2"/>')
    b.append(mono.text("API", ax, ay + 5, 13, c["ink"], anchor="middle"))

    # Paper plane flying along a dashed trail.
    trail = "M600 250 C 650 210, 700 270, 760 236 S 840 190, 880 214"
    b.append(f'<path d="{trail}" {stroke(c, c["green"], 2.2)} stroke-dasharray="5 7" opacity="0.8"/>')
    css.append(f'.fly{{offset-path:path("{trail}");offset-rotate:auto;animation:fly 6s ease-in-out infinite}}'
               "@keyframes fly{0%{offset-distance:0%;opacity:0}12%{opacity:1}80%{opacity:1}100%{offset-distance:100%;opacity:0}}")
    b.append(f'<g class="fly"><path d="M-12 -8 L14 0 L-12 8 L-6 0 Z M-6 0 L14 0" {stroke(c, c["green"], 2.2)}/></g>')

    b.append(sparkle(612, 64, 9, c["yellow"]))
    b.append(sparkle(958, 216, 7, c["blue"], delay=0.9))

    desc = f'{DATA["name"]}, {DATA["role"].lower()} in {DATA["location"]}. {" ".join(DATA["headline"])}'
    return svg(W, H, DATA["name"], desc + " Hand-drawn doodles of a cloud, an API hub, and a paper plane.", f, css, b)


# ---------------------------------------------------------------- now card

def now_card(theme, item):
    c, f = THEMES[theme], load_faces(FONTS)
    jost, dm, dmb, mono = f["jost"], f["dm"], f["dmb"], f["mono"]
    W, H = 1000, 200
    b, css = [paper(W, H, c)], []
    x = 48
    b.append(jost.text(item["name"], x, 76, 34, c["ink"]))
    nx = x + jost.width(item["name"], 34)
    b.append(underline(x + 2, 92, nx - x - 4, c["orange"], amp=2.6))
    if item.get("status"):
        pw = dmb.width(item["status"], 13) + 24
        b.append(f'<rect x="{nx + 16:.1f}" y="52" width="{pw:.1f}" height="26" rx="13" fill="{c["chip"]}"/>')
        b.append(dmb.text(item["status"], nx + 28, 70, 13, c["muted"]))
    for k, line in enumerate(wrap(dm, item["text"], 17, 500, max_lines=3)):
        b.append(dm.text(line, x, 128 + k * 26, 17, c["muted"]))

    # A doodle laptop typing the command.
    lx, ly, lw, lh = 640, 40, 300, 118
    b.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="10" {stroke(c, c["ink"], 2.4, fill=c["card"])}/>')
    b.append(f'<path d="M{lx - 26} {ly + lh + 12} h{lw + 52} l-14 14 h{-(lw + 24)} z" {stroke(c, c["ink"], 2.4, fill=c["card"])}/>')
    if item.get("command"):
        first, _, rest = item["command"].partition(" ")
        first += " "
        size = 16
        tx, ty = lx + 22, ly + 66
        fw, rw = mono.width(first, size), mono.width(rest, size)
        b.append(mono.text(first, tx, ty, size, c["blue"]))
        n = max(len(rest), 1)
        css.append(
            f"@keyframes type{{0%,8%{{transform:scaleX(0);animation-timing-function:steps({n},end)}}50%,90%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}"
            ".typed{animation:type 6s linear infinite;transform-box:fill-box;transform-origin:left center}"
            f"@keyframes cur{{0%,8%{{transform:translateX(0);animation-timing-function:steps({n},end)}}50%,90%{{transform:translateX({rw:.1f}px)}}100%{{transform:translateX(0)}}}}"
            ".cur{animation:cur 6s linear infinite}"
        )
        b.append(f'<mask id="m"><rect class="typed" x="{tx + fw:.1f}" y="{ty - 18}" width="{rw + 2:.1f}" height="26" fill="#fff"/></mask>')
        b.append('<g mask="url(#m)">' + mono.text(rest, tx + fw, ty, size, c["ink"]) + "</g>")
        b.append(f'<rect class="cur" x="{tx + fw + 1:.1f}" y="{ty - 15}" width="9" height="19" rx="1.5" fill="{c["blue"]}"/>')
    b.append(sparkle(960, 46, 7, c["pink"], delay=0.5))
    return svg(W, H, f'Working on {item["name"]}', f'{item["name"]}, {item.get("status", "")}. {item["text"]}', f, css, b)


# ---------------------------------------------------------------- project card

def project_card(theme, repo, index):
    c, f = THEMES[theme], load_faces(FONTS)
    jost, dm = f["jost"], f["dm"]
    W, H = 480, 176
    b = [paper(W, H, c, rx=16)]
    marker = c[MARKERS[index % len(MARKERS)]]
    b.append(jost.text(repo["name"], 30, 54, 23, c["ink"]))
    b.append(underline(32, 66, min(jost.width(repo["name"], 23), W - 70) - 2, marker, delay=0.3 * index, amp=2.4))
    desc = repo.get("description") or "No description yet."
    for k, line in enumerate(wrap(dm, desc, 15.5, W - 60, max_lines=2)):
        b.append(dm.text(line, 30, 100 + k * 23, 15.5, c["muted"]))
    y, x = 150, 30
    lang = repo.get("language")
    if lang:
        b.append(f'<circle cx="{x + 6}" cy="{y - 5}" r="6" fill="{LANG_COLORS.get(lang, c["muted"])}"/>')
        b.append(dm.text(lang, x + 18, y, 14, c["muted"]))
        x += 18 + dm.width(lang, 14) + 22
    stars = str(repo.get("stargazers_count", 0))
    b.append(f'<path d="M{x + 7} {y - 13} l2.3 4.9 l5.3 .6 l-4 3.6 l1.1 5.3 l-4.7 -2.7 l-4.7 2.7 l1.1 -5.3 l-4 -3.6 l5.3 -.6 z" {stroke(c, c["muted"], 1.5)}/>')
    b.append(dm.text(stars, x + 21, y, 14, c["muted"]))
    x += 21 + dm.width(stars, 14) + 22
    b.append(dm.text(f'updated {month(repo["pushed_at"])}', x, y, 14, c["muted"]))
    return svg(W, H, repo["name"], f'{repo["name"]}: {desc} Language: {lang or "none"}. Stars: {stars}.', f, [], b)


# ---------------------------------------------------------------- stack panel

def icon_for(name):
    key = ALIASES.get(name.lower())
    if key and key in ICONS:
        return ICONS[key]
    for slug, ic in ICONS.items():
        if ic["title"].lower() == name.lower() or slug == name.lower().replace(" ", "").replace(".", "dot"):
            return ic
    return None


def luminance(hex_color):
    r, g, bl = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * bl


def stack(theme):
    c, f = THEMES[theme], load_faces(FONTS)
    jost, dm = f["jost"], f["dm"]
    W, x0, x_max = 1000, 210, 960
    b, css = [], []
    y = 58
    n = 0
    rows = []
    for g_i, group in enumerate(DATA["stack"]):
        row = []
        x = x0
        line_y = y
        for name in group["items"]:
            ic = icon_for(name)
            w = (24 if ic else 0) + dm.width(name, 15.5) + 26
            if x + w > x_max:
                x, line_y = x0, line_y + 34
            row.append((name, ic, x, line_y))
            x += w
        rows.append((group["area"], y, row, g_i))
        y = line_y + 50
    H = y - 14
    b.append(paper(W, H, c))
    total = sum(len(r[2]) for r in rows)
    cycle = max(total * 0.32, 6)
    for area, ry, row, g_i in rows:
        b.append(jost.text(area, 44, ry + 5, 18, c["ink"]))
        b.append(underline(45, ry + 15, jost.width(area, 18) - 2, c[MARKERS[g_i % len(MARKERS)]], cls="", amp=1.8))
        for name, ic, ix, iy in row:
            tx = ix
            if ic:
                s = 18 / 24
                path_attr = f'transform="translate({ix:.1f} {iy - 13:.1f}) scale({s})" d="{ic["path"]}"'
                b.append(f'<path {path_attr} fill="{c["ink"]}" opacity="0.82"/>')
                bright = ic["hex"]
                if (theme == "dark" and luminance(bright) < 0.18) or (theme == "light" and luminance(bright) > 0.85):
                    bright = c["blue"]
                start = n * 0.32 / cycle * 100
                css.append(
                    f"@keyframes h{n}{{0%,{start:.2f}%{{opacity:0}}{start + 2.5:.2f}%,{start + 7:.2f}%{{opacity:1}}{start + 10:.2f}%,100%{{opacity:0}}}}"
                    f".h{n}{{animation:h{n} {cycle:.1f}s linear infinite;opacity:0}}"
                )
                b.append(f'<path class="h{n}" {path_attr} fill="{bright}"/>')
                tx = ix + 24
                n += 1
            b.append(dm.text(name, tx, iy, 15.5, c["ink"]))
    desc = " ".join(f'{a}: {", ".join(x[0] for x in r)}.' for a, _, r, _ in rows)
    return svg(W, H, "Stack", desc, f, css, b)


# ---------------------------------------------------------------- README

def picture(name, alt, width="100%", link=None):
    tag = (
        "<picture>"
        f'<source media="(prefers-color-scheme: dark)" srcset="./assets/generated/{name}-dark.svg">'
        f'<img alt="{esc(alt)}" src="./assets/generated/{name}-light.svg" width="{width}">'
        "</picture>"
    )
    return f'<a href="{link}">{tag}</a>' if link else tag


def readme(repos, by_name):
    out = ["<!-- Generated by scripts/build.py from profile.json. Edit profile.json, not this file. -->", ""]
    out.append(picture("hero", f'{DATA["name"]}. {" ".join(DATA["headline"])}'))
    out.append("")
    out.append('<p align="center">' + " · ".join(f'<a href="{url}">{name}</a>' for name, url in DATA["links"].items()) + "</p>")
    out.append("")
    out += [p + "\n" for p in DATA["about"]]
    if DATA["now"]:
        out += ["### Working on", ""]
        for i, item in enumerate(DATA["now"]):
            out.append(picture(f"now-{i}", f'{item["name"]}: {item["text"]}', link=item.get("url") or None))
            out.append("")
    show_projects = DATA.get("show_projects", True)
    cards = [by_name[name] for name in DATA["featured"] if name in by_name] if show_projects else []
    if cards:
        out += ["### Selected projects", "", '<p align="center">']
        for r in cards:
            out.append(f'  {picture("project-" + r["name"].lower(), r["name"], width="49%", link=r["html_url"])}')
        out += ["</p>", ""]
    out += ["### Stack", "", picture("stack", "Stack: " + "; ".join(f'{g["area"]}: {", ".join(g["items"])}' for g in DATA["stack"])), ""]
    exclude = set(DATA["recent"].get("exclude", [])) | set(DATA["featured"])
    recent = [r for r in repos if r["name"] not in exclude][: DATA["recent"].get("count", 5)] if show_projects else []
    if recent:
        out += ["### Recently active", ""]
        for r in recent:
            desc = short(r.get("description"))
            out.append(f'- [**{r["name"]}**]({r["html_url"]})' + (f" · {desc}" if desc else "") + f' · <sub>{month(r["pushed_at"])}</sub>')
        out.append("")
    out.append("<sub>This page rebuilds itself from <code>profile.json</code> and the GitHub API.</sub>")
    return "\n".join(out) + "\n"


def write(path, text):
    if path.suffix == ".svg":
        import xml.dom.minidom
        xml.dom.minidom.parseString(text)  # fails loudly on a broken image
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)
        print(f"wrote {path.relative_to(ROOT)}")


def main():
    repos = public_repos()
    by_name = {r["name"]: r for r in repos}
    for name in DATA["featured"]:
        if name not in by_name:
            print(f"warning: featured repo {name} not found or not public")
    files = {}
    for theme in ("light", "dark"):
        files[f"hero-{theme}.svg"] = hero(theme)
        files[f"stack-{theme}.svg"] = stack(theme)
        for i, item in enumerate(DATA["now"]):
            files[f"now-{i}-{theme}.svg"] = now_card(theme, item)
        for i, name in enumerate(n for n in DATA["featured"] if n in by_name):
            files[f"project-{name.lower()}-{theme}.svg"] = project_card(theme, by_name[name], i)
    for name, text in files.items():
        write(GEN / name, text)
    for old in GEN.glob("*.svg"):
        if old.name not in files:
            old.unlink()
            print(f"removed {old.relative_to(ROOT)}")
    write(ROOT / "README.md", readme(repos, by_name))


if __name__ == "__main__":
    main()
