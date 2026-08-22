# Deceleration Annotator

Shared expert review of fetal heart rate decelerations on the CTU-CHB
intrapartum cohort — live at https://decel-review.mnli.workers.dev.

25 records, selected for signal quality (13 hypoxia / 12 normal, pH
6.93–7.37). One shared annotation copy; every edit is name-attributed;
⚑ flags mark events still needing a decision.

## What the prefill is

- **Baseline** — our own max-tracking estimator
  (`tool` mirrors `research_log/scripts/baseline/fhr_baseline_ours.py`):
  decelerations only ever pull the trace down, so the resting level is read
  off the upper envelope — an 85th percentile over 4 minutes, refusing a vote
  to spikes and to sustained runs above a first envelope pass. Four published
  estimators (WMFB, Jimenez, Taylor, and the ctg-analyzer rolling median) can
  be overlaid from the header for comparison.
- **Deceleration detection** — the pipeline's `detect_fhr_events`, run
  against that baseline.
- **Typing** — pre-filled only where two independent readings agree (the
  pipeline's FHR–UC linker and a geometric rule from the NICHD thresholds);
  disagreements are left unclassified and flagged, so the expert types them
  unanchored. Both source readings are kept on every event.
- **Contraction detection** — the pipeline's `detect_uc_contractions` with
  literature thresholds (30 s minimum duration, 60 s peak separation, 120 s
  split interval per FIGO's ≤5/10 min).
- The CTU-CHB expert reference overlays as hatching (E) for comparison.

## Layout

- `tool/` — the annotator page + local dev server (`python3 serve.py`);
  canonical working copies live in `research_log/scripts/decel_annotator`
- `public/` — deployable static assets: `index.html`, `pilot.json`,
  `data/`, `baselines/` (the comparison estimators), `expert/` (the CTU
  reference)
- `worker/` — Cloudflare Worker backend (`/status`, `/ann/*`, `/save`,
  `/export`) with 409 conflict protection; `/export` requires the admin key
- `annotations/shared/` — the live shared annotations (versioned backup;
  refresh via `scripts/pull_annotations.py`)
- `scripts/` — seed / pull / sync helpers (see `DEPLOY.md`)

## Data licence

CTU-CHB Intrapartum Cardiotocography Database (Chudáček et al., BMC Pregnancy
and Childbirth 2014) via PhysioNet, Open Data Commons Attribution License v1.0.
The page footer carries the required attribution.
