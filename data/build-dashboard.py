#!/usr/bin/env python3
"""Inject data/metrics.json into dashboard/index.html.

The dashboard can't fetch a sibling file when published as an Artifact, so the
metrics are embedded in a <script type="application/json"> block. This keeps
metrics.json as the single source of truth and regenerates the embed.

Usage:  python3 data/build-dashboard.py
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
METRICS = ROOT / "data" / "metrics.json"
DASH = ROOT / "dashboard" / "index.html"

BLOCK = re.compile(
    r'(<script id="metrics-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)


def main() -> int:
    data = json.loads(METRICS.read_text())
    html = DASH.read_text()

    if not BLOCK.search(html):
        print("error: metrics-data block not found in dashboard/index.html", file=sys.stderr)
        return 1

    payload = json.dumps(data, indent=2)
    if "</script" in payload:
        print("error: metrics.json contains a closing script tag", file=sys.stderr)
        return 1

    html = BLOCK.sub(lambda m: m.group(1) + "\n" + payload + "\n" + m.group(3), html, count=1)
    DASH.write_text(html)
    print(f"injected {len(payload)} bytes of metrics into {DASH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
