#!/usr/bin/env python3
"""Render the README's labelled example from the real prompt formatter, offline."""
from pathlib import Path
from html import escape
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pc_mesh import fleet_preprompt


def render():
    now = 2000
    fleet = {"generated_at": now, "offline_after": 150, "stale_after": 5400,
             "nodes": [
                 {"id": name, "hostname": name, "received_at": received,
                  "updates": {"count": count, "status": "OK", "checked_at": 1990}}
                 for name, count, received in (
                     ("workstation", 12, 1999), ("laptop", 5, 1800), ("hub", 0, 1999))]}
    output = fleet_preprompt(fleet, now=now, width=120, color=True)
    colors = {"0": "#d5e0ed", "1;38;5;85": "#77f2af",
              "38;5;39": "#5cceff", "1;38;5;255": "#f7fbff", "38;5;196": "#ff737b"}
    spans, color = [], "#d5e0ed"
    for part in re.split(r"(\x1b\[[0-9;]*m)", output):
        if part.startswith("\x1b["):
            color = colors.get(part[2:-1], "#d5e0ed")
        else:
            spans.append('<tspan fill="%s">%s</tspan>' % (color, escape(part)))
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="350" viewBox="0 0 1120 350" role="img" aria-labelledby="title desc">
<title id="title">UpdateWulf terminal preview</title>
<desc id="desc">Illustrative data rendered by the real formatter: laptop has 5 updates and is offline, workstation has 12 updates, and one device has zero pending updates.</desc>
<rect width="1120" height="350" rx="16" fill="#0b1422"/>
<rect x="1" y="1" width="1118" height="348" rx="15" fill="none" stroke="#2b3d54"/>
<text x="42" y="62" fill="#f7fbff" font-family="Arial,sans-serif" font-size="32" font-weight="700">UpdateWulf</text>
<text x="42" y="91" fill="#9bb2cb" font-family="Arial,sans-serif" font-size="15">UPDATE STATUS • NATIVE PACKAGE MANAGERS • OPERATOR CONTROL</text>
<rect x="30" y="116" width="1060" height="158" rx="10" fill="#121f30" stroke="#2b3d54"/>
<circle cx="51" cy="136" r="4" fill="#ff737b"/><circle cx="67" cy="136" r="4" fill="#e9c469"/><circle cx="83" cy="136" r="4" fill="#77f2af"/>
<text x="1064" y="141" text-anchor="end" fill="#8aa3bf" font-family="Arial,sans-serif" font-size="12">ILLUSTRATIVE DEMO DATA</text>
<text x="50" y="185" xml:space="preserve" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="15">''' + ''.join(spans) + '''</text>
<text x="50" y="223" fill="#77f2af" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="16">$ <tspan fill="#f7fbff">updatewulf status --json</tspan></text>
<text x="50" y="250" fill="#8aa3bf" font-family="Arial,sans-serif" font-size="13">Read the cached snapshot. Choose when to request scans and package updates.</text>
<text x="42" y="315" fill="#9bb2cb" font-family="Arial,sans-serif" font-size="14">Python 3.9+  /  CLI + shell status  /  7 README languages</text>
</svg>
'''


if __name__ == "__main__":
    path = ROOT / "docs/assets/terminal-preview.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")
    print("Rendered docs/assets/terminal-preview.svg from illustrative fleet data")
