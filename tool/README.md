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
  added by hand as `origin: manual / review: added`
  (signal-loss-adjacent, saturated, or >180 s footprint events the
  detector rejects). Known caveat for a future prefill v3: max_dur 180 s
  cuts real 181-214 s events; 210-240 s would recover ~8 of these.

## Decel typing: consensus seeding (2026-08-20)

Deceleration types are NOT taken from any single source. Three independent
labellings were compared per event:

- `det_type` - the pipeline linker (`link_fhr_uc_events_v4`): candidate
  contractions ranked by timing score, peak-dominant early logic with
  confidence tiers, separate handling of FHR-loss decels;
- `src_rule` - a geometric rule pass over (onset, nadir, offset, uc_peak)
  applying the NICHD thresholds literally;
- `src_claude` - the visual first pass (archived in `decel_manual/claude/`).

All three are stored on every event for later audit. Then:

- **295 events (71%)** where >=2 sources agree and none dissents: the agreed
  type is pre-filled, for quick expert confirmation;
- **121 events (29%)** where sources conflict, or only one source had an
  opinion: type cleared to unclassified and the event flagged with a
  question, so the expert types it fresh with no anchor.

This concentrates expert effort on the 29% that is genuinely uncertain.
Rationale: deceleration type/morphology is the least reliable CTG judgement
in the literature (inter-observer kappa ~0.12-0.23, versus intra-observer
0.74-1.0), so a single annotator - human or algorithmic - yields a
self-consistent but idiosyncratic reference. That is the known flaw of the
Romagnoli reference this tool replaces.

Caveat carried forward: `onset -> nadir` (which decides abrupt vs gradual,
i.e. variable vs early/late) is dominated by where the *onset* sits, not by
nadir jitter. Reviewers should drag the onset to where the decel visibly
begins before typing borderline cases.

The client only needs five endpoints (`/pilot.json`, `/data/rec_*.json`,
`/ann/rec_*.json`, `/status`, `POST /save`), so for publishing to external
experts the static page can stay as-is and any small hosted backend
implementing these routes can replace `serve.py`.

## Measurements panel (2026-08-21)

Selecting any event now shows a **Measurements** block in the side card — the
same morphological quantities the model reads as per-minute channels
(8/20 meeting ask), computed live off the 1 Hz strip so they follow the
boundaries while you drag them:

- decel: duration, depth at nadir, onset→nadir, nadir→end, fall/recovery
  rates, area below baseline, in-decel variability, overshoot within 60 s
  after the end, and (when a contraction pairs within 45 s) the nadir-vs-UC-
  peak lag and onset-vs-onset lag;
- contraction: duration, intensity over resting tone (p10 of the 2 min
  before onset), rise/fall, area over tone, and the rest gaps either side.

Raw geometry only — deliberately no derived type suggestion, so the panel
cannot anchor the classification. Reviewers comment on the numbers through
the existing note box (logged to History under their name). The model-side
counterpart (34 new channels, feature set `morph`, AUROC and importance) is
in `research_log/morph_channels_2026-08-21.html`.

## Manual pairing (2026-08-21, LOCAL ONLY — not yet deployed)

The decel↔contraction pairing in the side list is automatic (overlap or gap
< 45 s, greedy), and sometimes wrong — a decel reads "no UC match" while its
real contraction sits one row up, already claimed. Two ways to fix it:

- **drag** one cell onto its partner in the paired list (either direction) —
  pointer-based, not HTML5 drag-and-drop, because Safari refuses to start a
  native drag inside this list's user-select:none region;
- **select**: with a decel selected, the "Paired UC" dropdown in the card
  offers automatic / no contraction / every contraction within ±3 min.

Stored as `pair` on the decel (`<contraction id>` forced, `"none"` forced
unmatched, absent = automatic), saved with the annotation, attributed and
logged to History, undoable. A contraction claimed manually is released
from any other decel (that decel falls back to automatic, logged). Manual
rows show a ✎. The nadir-vs-peak lag in Measurements follows the manual
pairing. Card layout (same date): measurements directly under the title,
type buttons below them, duration dropped from the title.

Deployment note: the Measurements panel + card layout ARE live on
decel-review (Cloudflare) as of 2026-08-21; manual pairing is deliberately
local pending review — sync with decel-review's
`scripts/sync_from_research_log.sh` + `wrangler deploy` when approved.
