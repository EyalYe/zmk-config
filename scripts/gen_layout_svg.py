#!/usr/bin/env python3
"""Generate SVG layout diagrams from config/corne_dongle.keymap.

Usage: python3 scripts/gen_layout_svg.py .
Writes <repo_root>/docs/layer_<name>.svg, docs/keymap.svg and docs/dongle_wiring.svg
"""
import re
import sys
from pathlib import Path
from html import escape

root = Path(sys.argv[1])
keymap = (root / "config/corne_dongle.keymap").read_text()
out = root / "docs"
out.mkdir(exist_ok=True)

# ---------- parse ----------
keymap = re.sub(r"//.*", "", keymap)
keymap_body = keymap[keymap.index("compatible = \"zmk,keymap\""):]
layers = re.findall(r"(\w+)\s*\{[^{}]*?bindings\s*=\s*<(.*?)>;", keymap_body, re.S)


def split_bindings(text):
    text = re.sub(r"//.*", "", text)
    return ["&" + b.strip() for b in text.split("&") if b.strip()]


LABELS = {
    "TAB": "Tab", "RET": "Enter", "SPACE": "Space", "BACKSPACE": "Bksp", "ESCAPE": "Esc",
    "DEL": "Del", "LEFT_SHIFT": "Shift", "LEFT_CONTROL": "Ctrl", "LEFT_ALT": "Alt",
    "RIGHT_ALT": "AltGr", "LEFT_GUI": "Cmd", "LGUI": "Cmd", "SEMI": ";", "SQT": "'",
    "COMMA": ",", "DOT": ".", "FSLH": "/", "EXCL": "!", "AT": "@", "HASH": "#",
    "DLLR": "$", "PRCNT": "%", "CARET": "^", "AMPS": "&", "ASTRK": "*", "LPAR": "(",
    "RPAR": ")", "MINUS": "-", "EQUAL": "=", "LBKT": "[", "RBKT": "]", "BSLH": "\\",
    "GRAVE": "`", "UNDER": "_", "PLUS": "+", "LBRC": "{", "RBRC": "}", "PIPE": "|",
    "TILDE": "~", "LEFT": "←", "RIGHT": "→", "UP": "↑", "UP_ARROW": "↑",
    "DOWN": "↓", "DOWN_ARROW": "↓", "PAGE_UP": "PgUp", "PAGE_DOWN": "PgDn",
    "C_VOL_DN": "Vol−", "C_VOLUME_UP": "Vol+", "C_PREV": "Prev", "C_NEXT": "Next",
    "C_PLAY_PAUSE": "Play", "NUMBER_4": "4",
    "LCLK": "L Click", "RCLK": "R Click", "MCLK": "M Click", "MB4": "Back", "MB5": "Fwd",
}
MODS = {"LS": "⇧", "LC": "⌃", "LG": "⌘", "LA": "⌥"}
LAYER_NAMES = {i: n for i, (n, _) in enumerate(layers)}


def key_label(param):
    m = re.match(r"(\w+)\((.*)\)$", param)
    if m and m.group(1) in MODS:
        return MODS[m.group(1)] + key_label(m.group(2))
    if re.fullmatch(r"N\d", param):
        return param[1]
    return LABELS.get(param, param)


def label(binding):
    parts = binding[1:].split(None, 1)
    beh, param = parts[0], (parts[1] if len(parts) > 1 else "")
    if beh == "kp":
        if param == "LS(LC(LG(NUMBER_4)))":
            return "Shot", "kind-macro"
        return key_label(param), ""
    if beh == "mkp":
        return key_label(param), "kind-mouse"
    if beh == "mo":
        return f"▼ {pretty(LAYER_NAMES[int(param)])}", "kind-layer"
    if beh == "trans":
        return "", "kind-trans"
    if beh == "none":
        return "", "kind-trans"
    if beh == "bt":
        if param == "BT_CLR":
            return "BT Clr", "kind-bt"
        return f"BT {int(param.split()[-1]) + 1}", "kind-bt"
    if beh == "bootloader":
        return "Boot", "kind-danger"
    return beh, ""


def pretty(name):
    return {"default_layer": "Base", "lower_layer": "Lower", "raise_layer": "Raise",
            "F_keys": "Fn"}.get(name, name)


# ---------- geometry ----------
U = 54          # key unit in px
GAP = 6
KEY = U - GAP
STAGGER = [0.45, 0.45, 0.15, 0.0, 0.15, 0.3]   # per-column y offset (left half, col 0..5)
SPLIT_GAP = 2.2                                  # units between halves
PAD = 24


def key_positions():
    """(x, y, rot, cx, cy) in units for the 42 Corne keys + 5 dongle keys."""
    pos = []
    right_x0 = 6 + SPLIT_GAP
    for row in range(3):
        for col in range(6):
            pos.append((col, row + STAGGER[col], 0))
        for col in range(6):
            pos.append((right_x0 + col, row + STAGGER[5 - col], 0))
    thumbs_l = [(3.5, 3.55, 0), (4.6, 3.6, 8), (5.75, 3.85, 18)]
    thumbs_r = [(right_x0 + 6 - 1 - (x - 0) + 0, y, -r) for x, y, r in thumbs_l]
    thumbs_r = [(right_x0 + (5 - x), y, -r) for x, y, r in thumbs_l][::-1]
    pos += thumbs_l + thumbs_r
    return pos


CORNE = key_positions()
CORNE_W = 12 + SPLIT_GAP
DONGLE_Y = 5.5
DONGLE_X0 = (CORNE_W - 5 * 1.15) / 2 + 0.6


STYLE = """
<style>
  .bg { fill: #1e1f29; }
  .half { fill: #262837; stroke: #3a3d52; stroke-width: 1.5; }
  .key { fill: #343746; stroke: #4b4f66; stroke-width: 1; }
  .lbl { fill: #f2f2f7; font: 600 13px 'Inter','Segoe UI',Helvetica,Arial,sans-serif; text-anchor: middle; dominant-baseline: central; }
  .small { font-size: 10.5px; }
  .title { fill: #f2f2f7; font: 700 20px 'Inter','Segoe UI',Helvetica,Arial,sans-serif; }
  .sub { fill: #9a9cb3; font: 500 12px 'Inter','Segoe UI',Helvetica,Arial,sans-serif; }
  .kind-layer { fill: #3b3363; stroke: #8b7cf6; }
  .kind-mouse { fill: #1f4a4a; stroke: #3cc9b4; }
  .kind-bt { fill: #1f3a5c; stroke: #4c9cf5; }
  .kind-danger { fill: #5c1f2a; stroke: #f5576c; }
  .kind-macro { fill: #4d3d1d; stroke: #f5b84c; }
  .kind-trans { fill: #2a2c3a; stroke: #3a3d52; stroke-dasharray: 3 3; }
  .sensor { fill: #15161e; stroke: #3cc9b4; stroke-width: 2; }
  .sensor-dot { fill: #3cc9b4; }
  .wire { fill: none; stroke-width: 2.2; }
  .pin { fill: #f2f2f7; font: 500 11.5px 'JetBrains Mono','Fira Code',Menlo,monospace; dominant-baseline: central; }
  .pinbox { fill: #343746; stroke: #4b4f66; }
  .board { fill: #17351f; stroke: #3ccf6e; stroke-width: 2; }
</style>
"""


def draw_key(x, y, rot, text, kind, ox, oy):
    px, py = ox + x * U, oy + y * U
    cx, cy = px + KEY / 2, py + KEY / 2
    t = f' transform="rotate({rot} {cx:.1f} {cy:.1f})"' if rot else ""
    cls = f"key {kind}".strip()
    small = " small" if len(text) > 5 else ""
    s = f'<g{t}><rect class="{cls}" x="{px:.1f}" y="{py:.1f}" width="{KEY}" height="{KEY}" rx="7"/>'
    if text:
        s += f'<text class="lbl{small}" x="{cx:.1f}" y="{cy:.1f}">{escape(text)}</text>'
    return s + "</g>"


def layer_svg(name, bindings, ox, oy, with_title=True):
    parts = []
    if with_title:
        parts.append(f'<text class="title" x="{ox}" y="{oy - 18}">{escape(pretty(name))} layer</text>')
    # half outlines
    for hx in (0, 6 + SPLIT_GAP):
        parts.append(f'<rect class="half" x="{ox + hx * U - 10}" y="{oy - 10}" width="{6 * U + 14}" '
                     f'height="{4.7 * U + 14}" rx="16"/>')
    # dongle outline + sensor
    dx = ox + (DONGLE_X0 - 1.6) * U
    dy = oy + (DONGLE_Y - 0.3) * U
    dw = (5 * 1.15 + 1.9) * U
    parts.append(f'<rect class="half" x="{dx:.1f}" y="{dy:.1f}" width="{dw:.1f}" height="{1.85 * U:.1f}" rx="16"/>')
    scx, scy = dx + 0.8 * U, dy + 0.8 * U
    parts.append(f'<circle class="sensor" cx="{scx:.1f}" cy="{scy:.1f}" r="{0.55 * U:.1f}"/>'
                 f'<circle class="sensor-dot" cx="{scx:.1f}" cy="{scy:.1f}" r="4"/>'
                 f'<text class="lbl small" x="{scx:.1f}" y="{scy + 0.75 * U:.1f}">PAW3395</text>')
    for i, b in enumerate(bindings):
        text, kind = label(b)
        if i < 42:
            x, y, r = CORNE[i]
        else:
            x, y, r = DONGLE_X0 + (i - 42) * 1.15, DONGLE_Y, 0
        parts.append(draw_key(x, y, r, text, kind, ox, oy))
    return "\n".join(parts)


W = int(CORNE_W * U + 2 * PAD + 20)
LAYER_H = int(8.3 * U)


def svg(width, height, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">{STYLE}<rect class="bg" width="100%" height="100%" rx="18"/>'
            f"{body}</svg>\n")


LEGEND = [("kind-layer", "Layer hold"), ("kind-mouse", "Mouse button"), ("kind-bt", "Bluetooth"),
          ("kind-macro", "Shortcut"), ("kind-danger", "Bootloader"), ("kind-trans", "Transparent")]


def legend(ox, oy):
    s, x = [], ox
    for cls, txt in LEGEND:
        s.append(f'<rect class="key {cls}" x="{x}" y="{oy}" width="18" height="18" rx="4"/>'
                 f'<text class="sub" x="{x + 26}" y="{oy + 13}">{txt}</text>')
        x += 40 + len(txt) * 7
    return "".join(s)


all_bodies = []
for idx, (name, text) in enumerate(layers):
    b = split_bindings(text)
    assert len(b) == 47, f"{name}: {len(b)} bindings"
    body = layer_svg(name, b, PAD + 10, PAD + 40)
    (out / f"layer_{pretty(name).lower()}.svg").write_text(svg(W, LAYER_H, body))
    all_bodies.append(layer_svg(name, b, PAD + 10, PAD + 40 + idx * LAYER_H))

total_h = LAYER_H * len(layers) + 70
(out / "keymap.svg").write_text(
    svg(W, total_h, "\n".join(all_bodies) + legend(PAD + 10, total_h - 36)))

# ---------- wiring diagram ----------
WIRES = [
    # (pro_micro pin, nrf pin, device pin, color)
    ("D1", "P0.06", "SCLK", "#3cc9b4"),
    ("D0", "P0.08", "MOSI", "#4c9cf5"),
    ("D2", "P0.17", "MISO", "#8b7cf6"),
    ("D3", "P0.20", "NCS", "#f5b84c"),
    ("D4", "P0.22", "MOTION", "#f5576c"),
]
BUTTONS = [
    ("D8", "P1.04", "BTN1 · L Click"),
    ("D9", "P1.06", "BTN2 · M Click"),
    ("D10", "P0.09", "BTN3 · R Click"),
    ("D16", "P0.10", "BTN4 · Back"),
    ("D14", "P1.11", "BTN5 · Fwd"),
]
ww, wh = 900, 470
p = ['<text class="title" x="30" y="44">Dongle wiring: nice!nano v2</text>',
     '<text class="sub" x="30" y="66">PAW3395 on high-frequency pins · buttons on low-frequency pins, to GND (internal pull-ups)</text>']
bx, by, bw, bh = 340, 100, 220, 330
p.append(f'<rect class="board" x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="12"/>'
         f'<text class="lbl" x="{bx + bw / 2}" y="{by + 22}">nice!nano v2</text>'
         f'<rect x="{bx + bw / 2 - 22}" y="{by - 8}" width="44" height="16" rx="3" fill="#9a9cb3"/>')
# sensor block (left)
sx, sy = 40, 110
p.append(f'<rect class="half" x="{sx}" y="{sy}" width="170" height="{len(WIRES) * 44 + 70}" rx="12"/>'
         f'<text class="lbl" x="{sx + 85}" y="{sy + 22}">PAW3395</text>'
         f'<text class="sub" x="{sx + 85}" y="{sy + 40}" text-anchor="middle">+ VCC 3.3V, GND</text>')
for i, (pm, nrf, dev, col) in enumerate(WIRES):
    y = sy + 70 + i * 44
    p.append(f'<rect class="pinbox" x="{sx + 90}" y="{y - 13}" width="70" height="26" rx="5"/>'
             f'<text class="pin" x="{sx + 100}" y="{y}">{dev}</text>')
    py_ = by + 60 + i * 40
    p.append(f'<path class="wire" stroke="{col}" d="M{sx + 160},{y} C{sx + 240},{y} {bx - 80},{py_} {bx},{py_}"/>'
             f'<text class="pin" x="{bx + 10}" y="{py_}">{pm}</text>'
             f'<text class="pin" x="{bx + 52}" y="{py_}" fill="#9a9cb3">{nrf}</text>')
# buttons (right)
rx0 = 700
for i, (pm, nrf, name) in enumerate(BUTTONS):
    py_ = by + 60 + i * 40
    y = py_
    p.append(f'<text class="pin" x="{bx + bw - 10}" y="{py_}" text-anchor="end">{pm}</text>'
             f'<text class="pin" x="{bx + bw - 48}" y="{py_}" text-anchor="end" fill="#9a9cb3">{nrf}</text>'
             f'<path class="wire" stroke="#9a9cb3" d="M{bx + bw},{py_} L{rx0 - 30},{y}"/>'
             f'<rect class="key kind-mouse" x="{rx0 - 30}" y="{y - 14}" width="28" height="28" rx="6"/>'
             f'<text class="pin" x="{rx0 + 8}" y="{y}">{name}</text>')
p.append(f'<text class="sub" x="{rx0 - 30}" y="{by + 60 + 5 * 40 + 10}">other leg of each button → GND</text>')
(out / "dongle_wiring.svg").write_text(svg(ww, wh, "\n".join(p)))
print("wrote", sorted(f.name for f in out.iterdir()))
