#!/usr/bin/env python3
"""Pull the live annotations from the deployed Worker back into this repo
(and optionally into research_log). Usage:
  python3 scripts/pull_annotations.py https://<worker-url> <ADMIN_KEY>
"""
import json, sys, urllib.request
from pathlib import Path
R = Path(__file__).resolve().parent.parent
base, admin = sys.argv[1].rstrip("/"), sys.argv[2]
data = json.loads(urllib.request.urlopen(f"{base}/export?key={admin}").read())
dest = R / "annotations/shared"
for k, v in data.items():
    (dest / f"{k}.json").write_text(json.dumps(v, indent=1))
print(f"pulled {len(data)} records into {dest}")
print("commit the change to keep a versioned audit backup")
