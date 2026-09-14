#!/usr/bin/env python3
"""
Local lab runner. Python standard library only — nothing to install.

    python3 projects/lab-runner/server.py
    open http://127.0.0.1:7878

Binds to loopback only. Every shell command it can run is hardcoded below;
nothing from the browser is ever passed to a shell.
"""

import json
import os
import re
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 7878
ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT.parent
WEB = ROOT / "web"
LABS = ROOT / "labs"

# az and terraform live in Homebrew's prefix, which a bare server process misses.
ENV = {**os.environ, "PATH": f"/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH','')}"}

_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()


def cached(key: str, ttl: int, producer):
    """Azure calls take seconds; don't re-run them on every poll."""
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    value = producer()
    with _lock:
        _cache[key] = (time.time(), value)
    return value


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except FileNotFoundError:
        return 127, f"not found: {cmd[0]}"


def lab_dir(lab_id: str) -> Path:
    """Map a lab id to its project directory, rejecting anything path-like."""
    if not re.fullmatch(r"[0-9a-z-]{1,40}", lab_id):
        raise ValueError("bad lab id")
    matches = sorted(PROJECTS.glob(f"{lab_id}*"))
    if not matches:
        raise ValueError("unknown lab")
    return matches[0]


# ----------------------------------------------------------------- endpoints --
def ep_labs():
    out = []
    for f in sorted(LABS.glob("*.json")):
        try:
            d = json.loads(f.read_text())
            out.append({"id": d["id"], "title": d["title"], "subtitle": d.get("subtitle", "")})
        except Exception:
            pass
    return {"labs": out}


def ep_lab(lab_id: str):
    f = LABS / f"{lab_id}.json"
    if not f.is_file():
        return {"error": "unknown lab"}
    return json.loads(f.read_text())


def ep_state(lab_id: str):
    f = lab_dir(lab_id) / "docs" / "lab-state.json"
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"checked": [], "hints": {}, "notes": {}}


def ep_save_state(lab_id: str, body: dict):
    d = lab_dir(lab_id) / "docs"
    d.mkdir(parents=True, exist_ok=True)
    f = d / "lab-state.json"
    current = ep_state(lab_id)
    for k in ("checked", "hints", "notes"):
        if k in body:
            current[k] = body[k]
    current["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    f.write_text(json.dumps(current, indent=2))
    return {"ok": True, "saved": str(f.relative_to(PROJECTS))}


def ep_terraform(lab_id: str):
    def go():
        d = lab_dir(lab_id)
        script = d / "scripts" / "check.sh"
        if not script.is_file():
            return {"available": False}
        code, out = run([str(script)], cwd=d, timeout=90)
        remaining = None
        m = re.search(r"Remaining tasks:\s*(\d+)", out)
        if m:
            remaining = int(m.group(1))
        elif "All TODO markers cleared" in out:
            remaining = 0
        todos = re.findall(r"\./([\w.-]+):(\d+)\s+→\s+([\d.]+)", out)
        return {
            "available": True,
            "remaining": remaining,
            "valid": "Success! The configuration is valid" in out,
            "todos": [{"file": f, "line": int(l), "task": t} for f, l, t in todos],
            "checks": re.findall(r"\[(ok|MISS)\]\s+(.+)", out),
            "raw": out[-4000:],
        }
    return cached(f"tf:{lab_id}", 10, go)


def ep_evidence(lab_id: str):
    d = lab_dir(lab_id) / "docs" / "evidence"
    shots = sorted(p.name for p in (d / "screenshots").glob("*.png")) if (d / "screenshots").is_dir() else []
    snaps = sorted(p.name for p in d.glob("state/*")) if d.is_dir() else []
    return {"screenshots": shots, "snapshots": snaps}


def ep_azure(lab_id: str):
    def go():
        code, out = run(["az", "account", "show", "-o", "json"], timeout=25)
        if code != 0:
            return {"logged_in": False, "message": "Not signed in. Run: az login"}
        acct = json.loads(out)

        res: list = []
        c, o = run(["az", "resource", "list", "--resource-group", "rg-costvis",
                    "--query", "[].{name:name,type:type}", "-o", "json"], timeout=30)
        if c == 0:
            try:
                res = json.loads(o)
            except Exception:
                res = []

        spend, currency = 0.0, "USD"
        c, o = run(["az", "consumption", "usage", "list", "--top", "800",
                    "--query", "[].{c:pretaxCost,cur:currency}", "-o", "json"], timeout=45)
        if c == 0:
            try:
                rows = json.loads(o)
                spend = sum(float(r.get("c") or 0) for r in rows)
                if rows and rows[0].get("cur"):
                    currency = rows[0]["cur"]
            except Exception:
                pass

        budgets: list = []
        c, o = run(["az", "consumption", "budget", "list", "-o", "json"], timeout=30)
        if c == 0:
            try:
                budgets = [{"name": b.get("name"), "amount": b.get("amount")}
                           for b in json.loads(o)]
            except Exception:
                pass

        return {
            "logged_in": True,
            "subscription": acct.get("name"),
            "user": (acct.get("user") or {}).get("name"),
            "resources": res,
            "resource_count": len(res),
            "spend": round(spend, 4),
            "currency": currency,
            "credit": 200.0,
            "budgets": budgets,
        }
    return cached(f"az:{lab_id}", 45, go)


ROUTES = {
    "/api/labs":      lambda q, b: ep_labs(),
    "/api/lab":       lambda q, b: ep_lab(q.get("id", ["01-cost-visibility"])[0]),
    "/api/state":     lambda q, b: ep_state(q.get("id", ["01-cost-visibility"])[0]),
    "/api/terraform": lambda q, b: ep_terraform(q.get("id", ["01-cost-visibility"])[0]),
    "/api/evidence":  lambda q, b: ep_evidence(q.get("id", ["01-cost-visibility"])[0]),
    "/api/azure":     lambda q, b: ep_azure(q.get("id", ["01-cost-visibility"])[0]),
}

MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".json": "application/json",
        ".png": "image/png", ".svg": "image/svg+xml"}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass  # quiet

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path in ROUTES:
            try:
                return self._json(ROUTES[u.path](q, None))
            except Exception as e:
                return self._json({"error": str(e)}, 500)

        # Static files, confined to web/
        rel = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
        target = (WEB / rel).resolve()
        if not str(target).startswith(str(WEB.resolve())) or not target.is_file():
            return self._send(404, b"not found", "text/plain")
        return self._send(200, target.read_bytes(),
                          MIME.get(target.suffix, "application/octet-stream"))

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"error": "bad json"}, 400)

        if u.path == "/api/state":
            try:
                return self._json(ep_save_state(q.get("id", ["01-cost-visibility"])[0], body))
            except Exception as e:
                return self._json({"error": str(e)}, 500)
        return self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"\n  Lab runner:  http://127.0.0.1:{PORT}\n  Ctrl+C to stop\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("  stopped")
