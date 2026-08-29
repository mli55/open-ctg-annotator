#!/usr/bin/env python3
"""Turn a full KV export into a bulk-put file for a different account.

Usage:
  python3 scripts/migrate_kv.py backups/kv-export-<stamp>.json [out.json]

The export holds every key the Worker serves: the shared records as rec_N
and each reader's blind set as ann_blind/<reader>/rec_N. Both shapes go
across verbatim -- the blind sets are one copy per reader, and flattening
them would merge two readings that the study exists to keep apart.

Then, against the NEW namespace:
  wrangler kv bulk put <out.json> --namespace-id <new id> --remote
"""
import json
import sys
from pathlib import Path

src = Path(sys.argv[1])
dest = Path(sys.argv[2] if len(sys.argv) > 2 else "worker/migrate.json")
data = json.loads(src.read_text())

out, shared, blind = [], 0, 0
for k, v in sorted(data.items()):
    if v is None:
        print(f"  skipped empty key {k}")
        continue
    out.append({"key": k, "value": json.dumps(v)})
    if k.startswith("ann_blind/"):
        blind += 1
    else:
        shared += 1

dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out))
print(f"{len(out)} keys -> {dest}  ({shared} shared, {blind} blind)")
print(f"  decels {sum(len(v.get('decels', [])) for v in data.values() if v)}"
      f" · contractions {sum(len(v.get('contractions', [])) for v in data.values() if v)}"
      f" · history {sum(len(v.get('history') or []) for v in data.values() if v)}")
print()
print("next:  wrangler kv bulk put", dest.name,
      "--namespace-id <new id> --remote")
