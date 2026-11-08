# Rock Layers + Face-off carousels (added Nov 8 2026)

- `data/layers/<ST>.json` — 4–6 rock layers per state (youngest → oldest), with map pins.
- `data/faceoff/<A>-<B>.json` — 24 neighbour pairs, 5 scored rounds + a bonus vote.
- `gen.py` renders the slides (needs `all/<ST>_ig_3_full.jpg` and `_ig_5_etsy[_holiday].jpg` from reels:c/ next to it);
  `detect.py` finds each state's map box in the geology slide (`data/maps.json`, with manual fixes for MA, IN, RI, KY).
- `sched.py` adds the posts to `igc/schedule.json` (Rock Layers Tue/Thu, Face-off Sat, 9:00 AM Denver).
- Slides are on the reels branch: `c/<ST>_rl_<n>.jpg`, `c/<A>-<B>_fo_<n>.jpg` (+ `_holiday` last slide for Nov 20 – Dec 10).
- `../add_calendar_rows.py` adds the rows to the master calendar on the PC.
