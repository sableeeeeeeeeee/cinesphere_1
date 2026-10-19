"""Generates original vector artwork (SVG) for the demo: movie posters, backdrops and food illustrations.

    python tools/generate_assets.py

Output goes to frontend/public/{posters,backdrops,images/food}. Everything here is original artwork
made from simple shapes, so there are no copyright issues. Replace any file (or the URL in the admin
panel) with your own licensed photo whenever you like.
"""
import math
import os
import random

ROOT = os.path.join(os.path.dirname(__file__), "..", "frontend", "public")
SERIF = "Georgia, 'Times New Roman', serif"
SANS = "'Helvetica Neue', Arial, sans-serif"


def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def grad(id_, stops, x2=0, y2=1):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{id_}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


# ----------------------------------------------------------------- poster scenes (400 x 600 space)
def scene_neon(r):
    out = ['<circle cx="270" cy="250" r="95" fill="url(#sun)" opacity=".95"/>']
    x = -10
    while x < 410:
        w, h = r.randint(28, 60), r.randint(120, 330)
        out.append(f'<rect x="{x}" y="{520 - h}" width="{w}" height="{h}" fill="#0b0720"/>')
        for wy in range(520 - h + 10, 510, 16):
            for wx in range(x + 6, x + w - 8, 12):
                if r.random() < .35:
                    out.append(f'<rect x="{wx}" y="{wy}" width="5" height="7" fill="{r.choice(["#ff4fd8", "#4fd8ff", "#ffd84f"])}" opacity=".9"/>')
        x += w + r.randint(0, 6)
    for _ in range(70):
        rx, ry = r.randint(0, 400), r.randint(0, 520)
        out.append(f'<line x1="{rx}" y1="{ry}" x2="{rx - 8}" y2="{ry + 26}" stroke="#9fb4ff" stroke-width="1" opacity=".35"/>')
    out.append('<rect x="0" y="520" width="400" height="80" fill="#07041a"/>')
    return "".join(out), '<radialGradient id="sun"><stop offset="0" stop-color="#ffd1f5"/><stop offset=".55" stop-color="#ff4fd8"/><stop offset="1" stop-color="#7a1fff" stop-opacity="0"/></radialGradient>'


def scene_lighthouse(r):
    out = ['<circle cx="310" cy="120" r="34" fill="#e8eefc" opacity=".95"/><circle cx="322" cy="112" r="30" fill="#14233f"/>']
    for _ in range(60):
        out.append(f'<circle cx="{r.randint(0, 400)}" cy="{r.randint(0, 260)}" r="{r.random() * 1.3 + .3:.1f}" fill="#fff" opacity=".7"/>')
    out.append('<polygon points="200,250 400,170 400,300" fill="#ffe9a8" opacity=".25"/>')
    out.append('<path d="M150 560 L175 250 L225 250 L250 560 Z" fill="#e9e4da"/>')
    for i in range(4):
        y = 300 + i * 65
        out.append(f'<path d="M{168 - i * 4} {y} L{232 + i * 4} {y} L{233 + i * 4} {y + 30} L{167 - i * 4} {y + 30} Z" fill="#9c2f2f"/>')
    out.append('<rect x="170" y="222" width="60" height="32" fill="#2b3550"/><rect x="178" y="228" width="44" height="20" fill="#ffe08a"/>')
    out.append('<polygon points="165,222 200,190 235,222" fill="#9c2f2f"/>')
    for i, c in enumerate(["#0d1a33", "#0a1428", "#070d1d"]):
        y = 470 + i * 45
        out.append(f'<path d="M0 {y} Q50 {y - 18} 100 {y} T200 {y} T300 {y} T400 {y} L400 600 L0 600 Z" fill="{c}"/>')
    return "".join(out), ""


def scene_train(r):
    out = ['<circle cx="200" cy="300" r="120" fill="#ffd27a" opacity=".85"/>']
    out.append('<path d="M0 420 Q100 330 200 400 T400 380 L400 600 L0 600 Z" fill="#5a2a16"/>')
    out.append('<path d="M0 470 Q120 410 240 460 T400 440 L400 600 L0 600 Z" fill="#2c130c"/>')
    out.append('<g transform="translate(0 -80)">')
    for i in range(4):
        x = 10 + i * 95
        out.append(f'<rect x="{x}" y="440" width="88" height="60" rx="6" fill="#1a0b07"/>')
        for j in range(3):
            out.append(f'<rect x="{x + 10 + j * 26}" y="452" width="16" height="18" fill="#ffcf6a"/>')
    out.append('<rect x="-4" y="500" width="410" height="6" fill="#120805"/>')
    for i in range(14):
        out.append(f'<circle cx="{20 + i * 28}" cy="508" r="7" fill="#120805"/>')
    out.append('</g>')
    return "".join(out), ""


def scene_forest(r):
    out = ['<circle cx="120" cy="150" r="46" fill="#eaffd0" opacity=".9"/>']
    layers = [("#1c4a2c", 330, .55), ("#123a22", 400, .75), ("#0a2615", 470, 1)]
    for col, base, sc in layers:
        x = -20
        while x < 420:
            h = r.randint(120, 220) * sc
            w = h * .45
            out.append(f'<polygon points="{x},{base} {x + w / 2},{base - h} {x + w},{base}" fill="{col}"/>')
            x += w * .7
        out.append(f'<rect x="0" y="{base - 2}" width="400" height="{600 - base}" fill="{col}"/>')
    out.append('<g fill="#06150c" transform="translate(0 -110)"><ellipse cx="250" cy="500" rx="62" ry="38"/><circle cx="198" cy="480" r="26"/>'
               '<path d="M178 490 q-24 20 -10 54 q6 12 12 0 q-6 -26 8 -40 z"/><rect x="214" y="520" width="14" height="46"/>'
               '<rect x="242" y="522" width="14" height="46"/><rect x="270" y="520" width="14" height="46"/><rect x="292" y="516" width="14" height="46"/></g>')
    return "".join(out), ""


def scene_cricket(r):
    out = []
    for fx in (60, 340):
        out.append(f'<rect x="{fx - 3}" y="170" width="6" height="260" fill="#222a3a"/><rect x="{fx - 26}" y="150" width="52" height="26" fill="#fff6c8"/>')
        out.append(f'<polygon points="{fx - 20},176 {fx + 20},176 {fx + 120 if fx < 200 else fx - 120},470 {fx - 120 if fx < 200 else fx + 120},470" fill="#fff6c8" opacity=".12"/>')
    out.append('<ellipse cx="200" cy="470" rx="260" ry="90" fill="#1f6b3a"/><ellipse cx="200" cy="470" rx="260" ry="90" fill="none" stroke="#e9f7ee" stroke-width="2" opacity=".4"/>')
    out.append('<polygon points="175,430 225,430 245,560 155,560" fill="#c9a96a" opacity=".9"/>')
    for i in range(3):
        out.append(f'<rect x="{188 + i * 12}" y="440" width="4" height="40" fill="#f2e6c9"/>')
    out.append('<circle cx="300" cy="320" r="16" fill="#c0262d"/><path d="M290 312 q10 6 20 0 M290 328 q10 -6 20 0" stroke="#fff" stroke-width="1.5" fill="none"/>')
    return "".join(out), ""


def scene_orbit(r):
    out = []
    for _ in range(110):
        out.append(f'<circle cx="{r.randint(0, 400)}" cy="{r.randint(0, 600)}" r="{r.random() * 1.4 + .2:.1f}" fill="#fff" opacity="{r.random() * .7 + .2:.2f}"/>')
    out.append('<circle cx="230" cy="330" r="120" fill="url(#planet)"/>')
    out.append('<ellipse cx="230" cy="330" rx="200" ry="38" fill="none" stroke="#e8d8ff" stroke-width="5" opacity=".65" transform="rotate(-18 230 330)"/>')
    out.append('<circle cx="80" cy="160" r="9" fill="#e8e8f5"/><rect x="62" y="156" width="36" height="3" fill="#8fa2ff"/><rect x="77" y="141" width="3" height="34" fill="#8fa2ff"/>')
    return "".join(out), '<radialGradient id="planet" cx=".35" cy=".3"><stop offset="0" stop-color="#e5b6ff"/><stop offset=".6" stop-color="#7d3fd0"/><stop offset="1" stop-color="#220a4a"/></radialGradient>'


def scene_lanterns(r):
    out = ['<path d="M-10 90 Q200 170 410 90" fill="none" stroke="#3a0e1c" stroke-width="2"/>']
    for _ in range(22):
        x, y, s = r.randint(10, 390), r.randint(120, 470), r.uniform(.6, 1.4)
        c = r.choice(["#ff9a5c", "#ff6b81", "#ffd166"])
        out.append(f'<g transform="translate({x} {y}) scale({s:.2f})"><line x1="0" y1="-40" x2="0" y2="-24" stroke="#3a0e1c"/>'
                   f'<ellipse cx="0" cy="0" rx="22" ry="26" fill="{c}"/><ellipse cx="0" cy="0" rx="22" ry="26" fill="url(#glow)"/>'
                   f'<rect x="-9" y="-28" width="18" height="5" fill="#5a1a24"/><rect x="-9" y="22" width="18" height="5" fill="#5a1a24"/></g>')
    out.append('<path d="M0 560 Q100 520 200 550 T400 540 L400 600 L0 600 Z" fill="#1d0710"/>')
    return "".join(out), '<radialGradient id="glow"><stop offset="0" stop-color="#fff6d6" stop-opacity=".9"/><stop offset="1" stop-color="#fff6d6" stop-opacity="0"/></radialGradient>'


def scene_alley(r):
    out = ['<polygon points="0,0 150,230 150,460 0,600" fill="#1a1013"/><polygon points="400,0 250,230 250,460 400,600" fill="#150d10"/>']
    out.append('<polygon points="150,230 250,230 250,460 150,460" fill="#2a1519"/><polygon points="0,600 150,460 250,460 400,600" fill="#0d0809"/>')
    for i in range(5):
        y = 90 + i * 55
        out.append(f'<rect x="{12 + i * 8}" y="{y}" width="22" height="30" fill="{"#e8a64a" if i % 2 else "#2a1519"}" opacity=".9"/>')
        out.append(f'<rect x="{366 - i * 8}" y="{y + 20}" width="22" height="30" fill="{"#2a1519" if i % 2 else "#e8a64a"}" opacity=".9"/>')
    out.append('<rect x="198" y="150" width="4" height="120" fill="#0a0506"/><polygon points="200,170 150,470 250,470" fill="#ffd9a0" opacity=".18"/><circle cx="200" cy="168" r="9" fill="#ffe3b3"/>')
    out.append('<g fill="#050203"><circle cx="200" cy="376" r="9"/><path d="M186 388 h28 l6 58 h-12 l-2 -34 l-2 34 h-12 z"/></g>')
    out.append('<ellipse cx="200" cy="450" rx="46" ry="8" fill="#ffd9a0" opacity=".12"/>')
    return "".join(out), ""


MOVIES = {
    "neon-monsoon": ("Neon Monsoon", "SCI-FI", ("#12063a", "#3b0a6b", "#7b1d6c"), scene_neon),
    "the-last-lighthouse": ("The Last Lighthouse", "THRILLER", ("#05122a", "#0c2147", "#173a6b"), scene_lighthouse),
    "masala-express": ("Masala Express", "COMEDY", ("#3a1206", "#b8481a", "#f59a3d"), scene_train),
    "kaadu": ("Kaadu", "ADVENTURE", ("#071a10", "#124a2a", "#4a8f4e"), scene_forest),
    "midnight-cricket": ("Midnight Cricket", "DRAMA", ("#070b20", "#14235a", "#234a8a"), scene_cricket),
    "orbit-zero": ("Orbit Zero", "SCI-FI", ("#05030f", "#150a35", "#2a1260"), scene_orbit),
    "paper-lanterns": ("Paper Lanterns", "ROMANCE", ("#1a0510", "#5a0f2e", "#b8324f"), scene_lanterns),
    "iron-alley": ("Iron Alley", "ACTION", ("#0c0607", "#2a0f12", "#6b2a1a"), scene_alley),
}


def title_lines(title):
    words = title.upper().split()
    if len(words) == 1:
        return words
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def poster(slug, title, genre, colors, scene):
    r = random.Random(slug)
    body, defs = scene(r)
    lines = title_lines(title)
    longest = max(len(l) for l in lines)
    size = min(48, (330 / longest - 4) / .74)
    ty = 500 if len(lines) == 2 else 540
    text = "".join(f'<text x="200" y="{ty + i * (size + 6)}" text-anchor="middle" font-family="{SERIF}" font-weight="700" font-size="{size:.0f}" letter-spacing="4" fill="#fff" filter="url(#ts)">{l}</text>'
                   for i, l in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 600" role="img" aria-label="{title} poster"><defs>'
            f'{grad("bg", [(0, colors[0]), (.55, colors[1]), (1, colors[2])])}{defs}'
            '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".45" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".85"/></linearGradient>'
            '<filter id="ts" x="-10%" y="-10%" width="120%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity=".7"/></filter></defs>'
            f'<rect width="400" height="600" fill="url(#bg)"/>{body}<rect width="400" height="600" fill="url(#fade)"/>'
            f'<text x="200" y="44" text-anchor="middle" font-family="{SANS}" font-size="11" letter-spacing="6" fill="#fff" opacity=".75">{genre}</text>'
            f'<line x1="150" y1="58" x2="250" y2="58" stroke="#fff" opacity=".35"/>{text}'
            f'<text x="200" y="574" text-anchor="middle" font-family="{SANS}" font-size="9" letter-spacing="5" fill="#fff" opacity=".6">NOW SHOWING</text></svg>')


def backdrop(slug, title, genre, colors, scene):
    """Atmospheric wide image: the poster scene enlarged and softly blurred, with a colour wash."""
    r = random.Random(slug)
    body, defs = scene(r)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 540" preserveAspectRatio="xMidYMid slice" role="img" aria-label="{title} backdrop"><defs>'
            f'{grad("bg", [(0, colors[0]), (.5, colors[1]), (1, colors[2])], 1, .3)}{defs}<filter id="b" x="-5%" y="-5%" width="110%" height="110%"><feGaussianBlur stdDeviation="5"/></filter></defs>'
            f'<rect width="1280" height="540" fill="url(#bg)"/><g filter="url(#b)" opacity=".9" transform="translate(-120 -330) scale(3.4)">{body}</g>'
            '<rect width="1280" height="540" fill="#000" opacity=".25"/></svg>')


# ----------------------------------------------------------------------- food illustrations (400 x 300)
def shadow(cx, cy, rx):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{rx * .16:.0f}" fill="#000" opacity=".35" filter="url(#sh)"/>'


def kernels(r, cx, cy, spread, n, base):
    out = []
    for _ in range(n):
        x, y = cx + r.uniform(-spread, spread), cy + r.uniform(-spread * .55, spread * .35)
        s = r.uniform(7, 12)
        out.append(f'<g transform="translate({x:.0f} {y:.0f})"><circle r="{s:.0f}" fill="{base}"/><circle cx="{-s * .4:.0f}" cy="{-s * .3:.0f}" r="{s * .55:.0f}" fill="#fffbe9"/>'
                   f'<circle cx="{s * .5:.0f}" cy="{s * .1:.0f}" r="{s * .45:.0f}" fill="#fff3c4"/><circle cx="{s * .1:.0f}" cy="{s * .5:.0f}" r="{s * .3:.0f}" fill="#f0c452" opacity=".8"/></g>')
    return "".join(out)


def bucket(cx, base, w, h, c1, c2, r, pop):
    top = base - h
    stripes = "".join(f'<polygon points="{cx - w / 2 + i * w / 6 * (1 if True else 1):.0f},{top} {cx - w / 2 + (i + 1) * w / 6:.0f},{top} {cx - w * .36 + (i + 1) * w * .72 / 6:.0f},{base} {cx - w * .36 + i * w * .72 / 6:.0f},{base}" fill="{c1 if i % 2 == 0 else c2}"/>'
                      for i in range(6))
    return (kernels(r, cx, top - 6, w * .5, 26, pop) + stripes +
            f'<ellipse cx="{cx}" cy="{top}" rx="{w / 2}" ry="9" fill="{c2}"/><ellipse cx="{cx}" cy="{base}" rx="{w * .36}" ry="7" fill="{c1}" opacity=".9"/>'
            + kernels(r, cx, top - 4, w * .48, 14, pop))


def cup(cx, base, w, h, color, lid="#f4f4f6"):
    top = base - h
    return (f'<rect x="{cx + 4}" y="{top - 52}" width="6" height="56" rx="3" fill="#e63946" transform="rotate(12 {cx} {top})"/>'
            f'<polygon points="{cx - w / 2},{top} {cx + w / 2},{top} {cx + w * .36},{base} {cx - w * .36},{base}" fill="{color}"/>'
            f'<polygon points="{cx - w * .46},{top + h * .35} {cx + w * .46},{top + h * .35} {cx + w * .42},{top + h * .62} {cx - w * .42},{top + h * .62}" fill="#fff" opacity=".9"/>'
            f'<rect x="{cx - w / 2 - 5}" y="{top - 9}" width="{w + 10}" height="11" rx="5" fill="{lid}"/>'
            f'<polygon points="{cx - w / 2 + 6},{top + 4} {cx - w / 2 + 14},{top + 4} {cx - w * .3},{base - 4} {cx - w * .36 + 4},{base - 4}" fill="#fff" opacity=".18"/>')


def food_frame(inner, c1="#2b2118", c2="#4a3523"):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" role="img"><defs>'
            f'<radialGradient id="bgf" cx=".5" cy=".4" r=".8"><stop offset="0" stop-color="{c2}"/><stop offset="1" stop-color="{c1}"/></radialGradient>'
            '<filter id="sh" x="-20%" y="-100%" width="140%" height="300%"><feGaussianBlur stdDeviation="6"/></filter>'
            '<linearGradient id="gloss" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
            f'<rect width="400" height="300" fill="url(#bgf)"/><rect y="215" width="400" height="85" fill="#000" opacity=".22"/>{inner}</svg>')


def food_salted(r):
    return food_frame(shadow(200, 262, 90) + bucket(200, 258, 150, 150, "#d62839", "#fff4f0", r, "#fff0b0"))


def food_caramel(r):
    return food_frame(shadow(200, 262, 90) + bucket(200, 258, 150, 150, "#1d4e89", "#ffe8b3", r, "#e8a33c"), "#241a12", "#4d3520")


def food_drink(r):
    return food_frame(shadow(200, 262, 70) + cup(200, 258, 120, 170, "#c1121f"), "#1f2a38", "#35506b")


def food_nachos(r):
    out = [shadow(200, 255, 140), '<ellipse cx="200" cy="215" rx="150" ry="46" fill="#2c3440"/><ellipse cx="200" cy="205" rx="138" ry="38" fill="#3b4656"/>']
    for _ in range(30):
        x, y, a = 200 + r.uniform(-115, 115), 200 + r.uniform(-24, 18), r.uniform(0, 360)
        out.append(f'<polygon transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})" points="0,-22 20,14 -20,14" fill="#e9b13c" stroke="#c98f1f" stroke-width="1.5"/>')
    out.append('<path d="M110 195 q30 -26 62 -4 q34 -24 68 -2 q36 -16 54 8 q-30 22 -62 8 q-36 20 -70 2 q-34 14 -52 -12z" fill="#f28c1d" opacity=".95"/>')
    for _ in range(9):
        out.append(f'<circle cx="{200 + r.uniform(-90, 90):.0f}" cy="{198 + r.uniform(-16, 12):.0f}" r="7" fill="#5fa83a" stroke="#3d7a22"/>')
    for _ in range(6):
        out.append(f'<circle cx="{200 + r.uniform(-95, 95):.0f}" cy="{196 + r.uniform(-14, 10):.0f}" r="5" fill="#c8301f"/>')
    return food_frame("".join(out), "#241912", "#46321f")


def food_sandwich(r):
    out = [shadow(200, 252, 130)]
    out.append('<polygon points="95,225 305,225 270,140 130,140" fill="#c98b4e"/><polygon points="95,225 305,225 300,238 100,238" fill="#a56a30"/>')
    out.append('<path d="M92 150 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 q16 -14 32 0 l-6 24 h-212z" fill="#58a03a"/>')
    out.append('<rect x="100" y="172" width="200" height="16" fill="#f2c94c"/>')
    out.append('<g fill="#d94a3a">' + "".join(f'<ellipse cx="{125 + i * 38}" cy="196" rx="17" ry="7"/>' for i in range(5)) + '</g>')
    out.append('<rect x="98" y="200" width="204" height="10" fill="#e6e0c8"/>')
    out.append('<path d="M96 122 q104 -66 208 0 l-6 34 h-196z" fill="#d9a066"/><path d="M130 118 q70 -36 140 0" fill="none" stroke="#fff" stroke-width="5" opacity=".25" stroke-linecap="round"/>')
    out.append('<g stroke="#7a4a1d" stroke-width="3" opacity=".5">' + "".join(f'<line x1="{150 + i * 28}" y1="108" x2="{140 + i * 28}" y2="146"/>' for i in range(5)) + '</g>')
    return food_frame("".join(out), "#241b14", "#4a3a28")


def food_combo(r):
    inner = shadow(200, 262, 150) + bucket(150, 258, 140, 140, "#d62839", "#fff4f0", r, "#fff0b0") + cup(280, 258, 78, 124, "#1d4e89") + cup(335, 258, 60, 100, "#c1121f")
    return food_frame(inner, "#1c2230", "#34415c")


def food_brownie(r):
    out = [shadow(200, 252, 135), '<ellipse cx="200" cy="228" rx="150" ry="30" fill="#e8e4dc"/><ellipse cx="200" cy="222" rx="132" ry="24" fill="#f6f3ec"/>']
    out.append('<polygon points="115,205 255,205 280,170 140,170" fill="#4a2512"/><polygon points="115,205 255,205 255,232 115,232" fill="#341a0c"/><polygon points="255,205 280,170 280,196 255,232" fill="#2a1409"/>')
    out.append('<path d="M138 172 h140 l-6 14 q-8 18 -16 4 q-6 20 -18 2 q-8 24 -20 2 q-10 16 -18 0 q-10 14 -18 -2 q-12 12 -20 -6z" fill="#1d0d06"/>')
    for x in (160, 205, 245):
        out.append(f'<g transform="translate({x} 178)"><path d="M-12 0 q6 -12 14 -8 q10 -6 12 6 q-6 10 -14 8 q-8 4 -12 -6z" fill="#b98a55"/></g>')
    out.append('<circle cx="300" cy="215" r="26" fill="#fff6e0"/><circle cx="292" cy="206" r="9" fill="#fff" opacity=".6"/>')
    return food_frame("".join(out), "#201810", "#43301d")


def food_icecream(r):
    out = [shadow(200, 262, 100)]
    out.append('<polygon points="130,170 270,170 250,258 150,258" fill="#f4f1ec"/><polygon points="130,170 270,170 266,190 134,190" fill="#d62839"/>')
    out.append('<polygon points="142,196 258,196 255,208 145,208" fill="#fff" opacity=".6"/>')
    out.append('<circle cx="170" cy="150" r="46" fill="#f7e7b4"/><circle cx="232" cy="144" r="44" fill="#5a3320"/><circle cx="200" cy="108" r="40" fill="#fff4d6"/>')
    out.append('<circle cx="186" cy="94" r="12" fill="#fff" opacity=".5"/><circle cx="220" cy="132" r="10" fill="#fff" opacity=".18"/>')
    out.append('<path d="M168 168 q-4 18 4 22 q8 -6 4 -22z" fill="#f7e7b4"/><rect x="262" y="70" width="8" height="120" rx="4" fill="#e9c46a" transform="rotate(18 266 130)"/>')
    return food_frame("".join(out), "#1d2430", "#3a4a63")


FOOD = {"salted-popcorn": food_salted, "caramel-popcorn": food_caramel, "soft-drink": food_drink, "loaded-nachos": food_nachos,
        "veg-sandwich": food_sandwich, "movie-combo": food_combo, "choco-brownie": food_brownie, "ice-cream-tub": food_icecream}


if __name__ == "__main__":
    for slug, (title, genre, colors, scene) in MOVIES.items():
        write(f"posters/{slug}.svg", poster(slug, title, genre, colors, scene))
        write(f"backdrops/{slug}.svg", backdrop(slug, title, genre, colors, scene))
    for slug, fn in FOOD.items():
        write(f"images/food/{slug}.svg", fn(random.Random(slug)))
    print(f"Wrote {len(MOVIES) * 2 + len(FOOD)} files to frontend/public")
