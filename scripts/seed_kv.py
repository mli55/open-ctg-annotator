#!/usr/bin/env python3
"""Build seed.json for `wrangler kv bulk put` from annotations/shared/."""
import json
from pathlib import Path
R = Path(__file__).resolve().parent.parent
pilot_ids = {p["id"] for p in json.loads((R / "public/pilot.json").read_text())["records"]}
out = []
for f in sorted((R / "annotations/shared").glob("rec_*.json")):
    rid = int(f.stem.split("_")[1])
    if rid not in pilot_ids:
        continue
    out.append({"key": f.stem, "value": f.read_text()})
dest = R / "worker/seed.json"
dest.write_text(json.dumps(out))
print(f"wrote {dest} with {len(out)} records; next:")
print("  cd worker && wrangler kv bulk put seed.json --namespace-id <ANN id> --remote")
