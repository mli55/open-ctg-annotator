#!/usr/bin/env python3
"""Local server for the manual decel annotation tool.

Serves annotator.html plus slimmed record JSON from the ctg-analyzer webapp
data directory, and persists annotation files under
research_log/annotations/decel_manual/<annotator>/rec_<id>.json (atomic writes).

Run:  python3 serve.py            (then open http://127.0.0.1:8765)
"""
import argparse
import json
import re
import tempfile
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEF_DATA = Path.home() / "Documents/git/ctg-analyzer/data"
DEF_ANN = HERE.parent.parent / "annotations" / "decel_manual"

REC_RE = re.compile(r"^rec_(\d{1,6})\.json$")
NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,40}$")


def slim_record(d):
    ph = None
    for row in (d.get("meta") or {}).get("Outcome measures", []):
        if row and str(row[0]).strip().lower() == "ph":
            ph = row[1]
    return {
        "record_id": d.get("record_id"),
        "hypoxia": d.get("hypoxia"),
        "ph": ph,
        "ii_start": d.get("ii_start"),
        "cov": d.get("cov"),
        "strip": d.get("strip"),
        "events": d.get("events"),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DecelAnnotator/1"

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        cfg = self.server.cfg
        qname = (parse_qs(u.query).get("annotator") or [cfg.annotator])[0]
        if not NAME_RE.match(qname):
            qname = cfg.annotator
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "annotator.html").read_bytes(),
                       "text/html; charset=utf-8")
        elif path == "/pilot.json":
            f = HERE / "pilot.json"
            if f.exists():
                self._send(200, f.read_bytes())
            else:
                self._send(404, {"error": "run make_pilot_list.py first"})
        elif path == "/config":
            self._send(200, {"annotator": cfg.annotator})
        elif path == "/status":
            out = {}
            d = cfg.ann_dir / "shared"
            if d.is_dir():
                for f in d.glob("rec_*.json"):
                    try:
                        a = json.loads(f.read_text())
                    except Exception:
                        continue
                    decels = a.get("decels", [])
                    done_d = sum(1 for e in decels
                                 if e.get("review") != "pending")
                    cons = a.get("contractions", [])
                    out[str(a.get("record_id"))] = {
                        "decels_done": done_d, "decels": len(decels),
                        "cons_done": sum(1 for e in cons
                                         if e.get("review") != "pending"),
                        "cons": len(cons),
                        "n_flag": sum(1 for e in decels + cons if e.get("flag")),
                        "updated": a.get("updated"),
                    }
            self._send(200, out)
        elif path.startswith("/data/"):
            m = REC_RE.match(path[len("/data/"):])
            if not m:
                return self._send(400, {"error": "bad record path"})
            f = cfg.data_dir / f"rec_{m.group(1)}.json"
            if not f.exists():
                return self._send(404, {"error": "no such record"})
            self._send(200, slim_record(json.loads(f.read_text())))
        elif path.startswith("/ann/"):
            m = REC_RE.match(path[len("/ann/"):])
            if not m:
                return self._send(400, {"error": "bad record path"})
            f = cfg.ann_dir / "shared" / f"rec_{m.group(1)}.json"
            if not f.exists():
                return self._send(404, {"error": "not annotated yet"})
            self._send(200, f.read_bytes())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path.split("?")[0] != "/save":
            return self._send(404, {"error": "not found"})
        cfg = self.server.cfg
        try:
            n = int(self.headers.get("Content-Length", 0))
            ann = json.loads(self.rfile.read(n))
            rid = int(ann["record_id"])
            name = ann.get("annotator") or ""
            if not NAME_RE.match(name):
                raise ValueError("annotator name required")
        except Exception as e:
            return self._send(400, {"error": str(e)})
        base = ann.pop("base_updated", None)
        d = cfg.ann_dir / "shared"
        d.mkdir(parents=True, exist_ok=True)
        dest = d / f"rec_{rid}.json"
        if dest.exists():
            try:
                cur = json.loads(dest.read_text()).get("updated")
            except Exception:
                cur = None
            if cur is not None and cur != base:
                return self._send(409, {"error": "conflict", "updated": cur})
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(ann, f, indent=1)
        os.replace(tmp, dest)
        self._send(200, {"ok": True, "path": str(dest)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--data-dir", type=Path, default=DEF_DATA)
    ap.add_argument("--ann-dir", type=Path, default=DEF_ANN)
    ap.add_argument("--annotator", default="mengning")
    cfg = ap.parse_args()
    if not cfg.data_dir.is_dir():
        raise SystemExit(f"data dir not found: {cfg.data_dir}")
    cfg.ann_dir.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", cfg.port), Handler)
    srv.cfg = cfg
    print(f"decel annotator: http://127.0.0.1:{cfg.port}  "
          f"(data: {cfg.data_dir}, annotations: {cfg.ann_dir}/{cfg.annotator})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
