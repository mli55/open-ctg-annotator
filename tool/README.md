# Decel Annotator

Manual expert annotation tool for CTU decelerations — replaces the Romagnoli 2020
reference the clinical team judged inaccurate (single annotator, tool-seeded).

## Run

```
python3 serve.py            # http://127.0.0.1:8765
```

Options: `--port`, `--annotator` (default `mengning`),
`--data-dir` (default `~/Documents/git/ctg-analyzer/data`),
`--ann-dir` (default `research_log/annotations/decel_manual`).

## Protocol (pilot, 2026-08-20)

- 21 pilot records in `pilot.json` (regenerate: `python3 make_pilot_list.py`);
  12 hypoxia / 9 normal, incl. exemplars 1180/1485.
  2026-08-20: records 1058, 2019, 1092, 1151 dropped from the original 25
  (incl. all three zero-decel controls; their shared/ annotation files are
  kept as archive; note `make_pilot_list.py` would re-add all four if rerun
  as-is).
- Detector prefill provides **intervals only** — every deceleration must be typed
  by the annotator (types 1–5: early/late/variable/prolonged/unsure, `U` = UC
  unreadable). Detector's own types are stored as `det_type` but never shown.
- Every event carries provenance: `origin` (detector/manual), `review`
  (pending/accepted/edited/added), original boundaries `a0/b0`; deletions of
  detector events are kept in `deleted`. This is what lets us quantify anchoring
  bias later — the known flaw of the Romagnoli annotation workflow.
- "Mark record done" is gated on every decel typed (or UC-unreadable) and every
  contraction reviewed.

## Output

`research_log/annotations/decel_manual/<annotator>/rec_<id>.json`, autosaved.
Times are in the webapp coordinate (minutes relative to delivery, negative).
`nadir_min` is recomputed on save from the 1 Hz strip.

## Claude first pass (2026-08-20)

All 25 pilot records annotated under annotator `claude` via `claude_pass.py`
(render per-decel figures with objective features, classify blind to the
detector's types, write tool-compatible JSON). Totals: 442 decels — 322
variable, 57 late, 12 prolonged, 9 early, 15 unsure, 27 untyped+UC-flag
(107 events UC-flagged in total); 29 missed decels added, 9 detector false
positives deleted, 2 boundary edits, 1 missed contraction added. Per-record
rationale sits in each file's `notes`.

## Shared review model (2026-08-20, replaces per-annotator dirs)

Annotations now live in ONE shared copy: `annotations/decel_manual/shared/`
(seeded from the Claude first pass; `claude/` is kept untouched as the
immutable first-pass archive for later diffing). The web tool:

- requires a name (top right) before ANY edit — viewing is open; the name is
  remembered per browser (localStorage) and stamped on every touched event
  (`by`) and every operation;
- has no "done" state (records are permanently open for review); the sidebar
  badge shows reviewer activity (✎N = N expert actions, hover for who);
- classification is a single choice 1-6: early / late / variable / prolonged /
  unsure / n/a (n/a = classification not applicable, e.g. unreadable toco;
  replaces the old UC-unreadable flag — 27 events migrated);
- keeps a per-record **History** panel (who, when, what: type changes, boundary
  drags with old→new intervals, adds, deletes, notes, undo/redo); the note box
  is append-only — Enter logs the note into History under your name;
- lists decels and contractions as left-right PAIRED columns (paired if
  overlapping or within 45 s; unpaired sides read "no decel" / "no UC match");
  a colour legend sits at the panel foot;
- rejects concurrent stale writes (HTTP 409): if two people edit the same
  record simultaneously, the second saver is told to reload. Different
  records never conflict.

## UC prefill v2 (2026-08-20)

The original contraction prefill let through many short/small peaks
(detector defaults: min duration 20 s, hard peak separation 30 s, prominence
floor 0.35). Literature constraints: clinical contractions last ~45-120 s
with a ~60 s resting interval; FIGO 2015 caps normal activity at 5
contractions/10 min (cycle >= 120 s); detection papers use 30-45 s minimum
durations. The prefill was regenerated with the UNMODIFIED pipeline detector
and literature-based options passed externally (min_dur 30 s, max_dur 180 s,
min_peak_sep 60 s, split_min_sep 120 s, valley_drop 4.0/0.20, prominence 5):

- `make_uc_prefill_v2.m` runs the detector -> `uc_prefill_v2.csv`
  (412 contractions over the 21 pilot records, down from 507; no more
  <30 s events, onset gaps <60 s cut 96 -> 20).
- `apply_uc_prefill_v2.py` overwrites the contraction lists in shared/
  (all events `review: pending`; decels and history preserved, the
  overwrite is logged per record). Applied 2026-08-20 while all prior
  contraction reviews were test entries; the Claude first-pass archive in
  `decel_manual/claude/` still holds the v1 lists.
- 2026-08-20 visual review (Claude, full strips of all 21 records): no
  clear false positives among the 412 v2 events; 30 missed contractions
  added by hand as `origin: manual / review: added / by: claude`
  (signal-loss-adjacent, saturated, or >180 s footprint events the
  detector rejects; logged per record in history). Known caveat for a
  future prefill v3: max_dur 180 s cuts real 181-214 s events; 210-240 s
  would recover ~8 of these automatically.

The client only needs five endpoints (`/pilot.json`, `/data/rec_*.json`,
`/ann/rec_*.json`, `/status`, `POST /save`), so for publishing to external
experts the static page can stay as-is and any small hosted backend
implementing these routes can replace `serve.py`.
