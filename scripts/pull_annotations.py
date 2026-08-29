#!/usr/bin/env python3
"""Pull the live annotations from the deployed Worker back into this repo.
Usage:
  python3 scripts/pull_annotations.py https://<worker-url> <ADMIN_KEY>

Shared records land in annotations/shared/rec_N.json. Blind sets are one
copy per reader and keep that shape on disk --
annotations/blind/<reader>/rec_N.json -- so a reader's set stays whole and
no two readers can be confused for one.
"""
import json, sys, urllib.request
from pathlib import Path

R = Path(__file__).resolve().parent.parent
base, admin = sys.argv[1].rstrip("/"), sys.argv[2]
# Cloudflare's edge turns away the default Python-urllib agent, so the
# request carries an ordinary one.
req = urllib.request.Request(f"{base}/export?key={admin}",
                             headers={"User-Agent": "decel-review-pull/1"})
data = json.loads(urllib.request.urlopen(req).read())

n_shared = n_blind = 0
for k, v in data.items():
    if k.startswith("ann_blind/"):
        dest = R / "annotations/blind" / Path(k[len("ann_blind/"):])
        n_blind += 1
    else:
        dest = R / "annotations/shared" / k
        n_shared += 1
    dest = dest.with_suffix(".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(v, indent=1))

print(f"pulled {n_shared} shared + {n_blind} blind records")
print("commit the change to keep a versioned audit backup")
