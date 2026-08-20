# Decel Review

Shared expert review of fetal heart rate decelerations on the CTU-CHB
intrapartum cohort (21-record pilot). One shared annotation copy; every edit
is name-attributed and listed in each record's History panel; ⚑ flags mark
events a reviewer wants the next person to look at.

## Layout

- `tool/` — the annotator page + local dev server (`python3 serve.py`,
  canonical working copies live in `research_log/scripts/decel_annotator`)
- `public/` — deployable static assets: `index.html`, `pilot.json`,
  `data/rec_*.json` (slimmed traces, 2.7 MB)
- `worker/` — Cloudflare Worker backend (`/status`, `/ann/*`, `/save`,
  `/export`) with `?key=` access gating and 409 conflict protection
- `annotations/shared/` — the live shared annotations (versioned backup;
  after deployment, refresh via `scripts/pull_annotations.py`)
- `annotations/claude/` — immutable first-pass archive (do not edit)
- `scripts/` — seed/pull/sync helpers

## Data licence

CTU-CHB Intrapartum Cardiotocography Database (Chudáček et al., BMC Pregnancy
and Childbirth 2014) via PhysioNet, Open Data Commons Attribution License v1.0.
The page footer carries the required attribution.
