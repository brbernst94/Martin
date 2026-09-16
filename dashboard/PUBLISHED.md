# Published dashboard

**Live URL:** https://claude.ai/artifact/Rx4bbqKecLnMygQ8GkspHF
**First published:** 2026-09-16 · **Owner:** Marty

## Updating it

Never publish a new artifact — republish to this URL so Brian's link never
changes.

1. Update `data/metrics.json` (see the `marty-metrics` skill)
2. `python3 data/build-dashboard.py` — injects the JSON into the HTML
3. Republish `dashboard/index.html` to the URL above, reading the existing
   artifact first
4. Commit both files

## Why the data is embedded

Published artifacts can't fetch a sibling file, so the metrics are inlined into a
`<script type="application/json">` block. `data/metrics.json` stays the single
source of truth; the build script does the injection. Editing the HTML block by
hand will get overwritten.
