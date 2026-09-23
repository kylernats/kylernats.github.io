#!/usr/bin/env python3
"""Serves the lab pages and gives each step a tutor you can send screenshots to.

Python standard library only. Binds to loopback. The tutor runs through the
local `claude` CLI in print mode, so it uses the Claude Code plan already on
this machine rather than an API key, and it gets read-only tools only.

    python3 projects/labs-server.py
    open http://localhost:7070
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = 7070
PROJECTS = Path(__file__).resolve().parent
SHOTS = PROJECTS / ".lab-shots"
MODEL = "claude-sonnet-5"

ENV = {**os.environ,
       "PATH": f"{Path.home()}/.local/bin:/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH','')}"}

LABS = [
    ("lab-01-aws-basics", "Lab 01 — Your local AWS environment",
     "Fundamentals. Commands, the console, and what a bucket policy is."),
    ("ir-01-exposed-customer-data", "Lab 02 — Customer data left open to the internet",
     "Incident response. Investigate a live exposure, then close it."),
]

TUTOR = """You are the tutor sitting beside Kyler while he works through a hands-on
AWS security lab on a local emulator (Floci) on his Mac.

He is a cybersecurity analyst. He knows security concepts well. What is new to him
is AWS command-line work and this specific environment.

When he sends a screenshot:
- Say plainly whether it looks right or not, first line, no preamble.
- If it is wrong, say exactly what is wrong and the one thing to do next.
- If it is right, confirm it and say what the important part of the output was.
- Read error messages carefully and explain what the error actually means before
  suggesting a fix.

When he asks a question:
- Answer it directly. Short. Plain words.
- Explain what a command does in terms of what it changes, not its syntax.
- Do not give him the answer to a graded question in Lab 02 (when the bucket was
  made public, who did it, what was taken). Point him at how to find it instead.

Never invent AWS behaviour. If you are not sure, say so.
No bullet lists unless you are actually listing things. No "great question".
Under 120 words unless he asks for more."""


_lock = threading.Lock()


def run(cmd: list[str], timeout: int = 180) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=PROJECTS, env=ENV, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "The tutor took too long to answer. Try asking again."
    except FileNotFoundError:
        return 127, "The `claude` command was not found on this machine."


def lab_dir(lab: str) -> Path:
    if not re.fullmatch(r"[0-9a-z-]{1,60}", lab):
        raise ValueError("bad lab id")
    d = PROJECTS / lab
    if not d.is_dir():
        raise ValueError("unknown lab")
    return d


def chat_file(lab: str) -> Path:
    d = lab_dir(lab) / ".chat"
    d.mkdir(exist_ok=True)
    return d / "threads.json"


def load_threads(lab: str) -> dict:
    f = chat_file(lab)
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def save_image(data_url: str) -> Path | None:
    """Decode a data: URL from the browser into a real file the CLI can read."""
    m = re.match(r"data:image/(png|jpeg|jpg|webp);base64,(.+)$", data_url, re.S)
    if not m:
        return None
    SHOTS.mkdir(exist_ok=True)
    # keep the folder from growing forever
    now = time.time()
    for old in SHOTS.glob("*"):
        if now - old.stat().st_mtime > 86400:
            old.unlink(missing_ok=True)
    ext = "jpg" if m.group(1) in ("jpeg", "jpg") else m.group(1)
    path = SHOTS / f"{uuid.uuid4().hex}.{ext}"
    try:
        path.write_bytes(base64.b64decode(m.group(2)))
    except (binascii.Error, ValueError):
        return None
    return path


def ask(lab: str, step: str, message: str, step_text: str, image: str | None) -> dict:
    threads = load_threads(lab)
    thread = threads.setdefault(step, {"session": None, "turns": []})

    shot = save_image(image) if image else None

    parts = []
    if not thread["session"] and step_text:
        parts.append(f"He is on this step of the lab:\n\n{step_text[:2000]}")
    if shot:
        parts.append(f"He attached a screenshot of his terminal or browser. "
                     f"Read the image at {shot} and judge whether his work looks correct.")
    parts.append(f"His message: {message or '(no text, just the screenshot)'}")
    prompt = "\n\n".join(parts)

    cmd = ["claude", "-p", prompt, "--model", MODEL,
           "--allowed-tools", "Read", "Grep", "Glob",
           "--append-system-prompt", TUTOR]

    if thread["session"]:
        code, out = run(cmd + ["--resume", thread["session"]])
        if code != 0:
            sid = str(uuid.uuid4())
            code, out = run(cmd + ["--session-id", sid])
            thread["session"] = sid
    else:
        sid = str(uuid.uuid4())
        code, out = run(cmd + ["--session-id", sid])
        thread["session"] = sid

    reply = out.strip()
    if code != 0:
        return {"error": reply[-500:] or f"claude exited {code}"}

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    thread["turns"].append({"role": "user", "text": message,
                            "had_image": bool(shot), "at": stamp})
    thread["turns"].append({"role": "assistant", "text": reply, "at": stamp})
    with _lock:
        chat_file(lab).write_text(json.dumps(threads, indent=2))
    return {"reply": reply}


INDEX = """<!DOCTYPE html><html><head><meta charset=utf-8>
<title>Labs</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0}}
body{{background:#0B0D10;color:#E8EBF0;font:16px/1.6 Inter,-apple-system,sans-serif;
padding:70px 20px;display:flex;justify-content:center}}
.w{{max-width:640px;width:100%}}
.k{{font:500 11px "JetBrains Mono",monospace;letter-spacing:.16em;text-transform:uppercase;color:#2DD4BF}}
h1{{font-size:32px;letter-spacing:-.025em;margin:10px 0 28px}}
a.card{{display:block;background:#13171D;border:1px solid #232932;border-radius:12px;
padding:20px 22px;margin-bottom:12px;text-decoration:none;transition:.15s}}
a.card:hover{{border-color:#2DD4BF;transform:translateY(-1px)}}
a.card b{{display:block;color:#E8EBF0;font-size:17px;margin-bottom:5px}}
a.card span{{color:#98A2B3;font-size:14.5px}}
p.n{{color:#6B7484;font-size:13.5px;margin-top:22px;font-family:"JetBrains Mono",monospace}}
</style></head><body><div class=w>
<div class=k>Local AWS labs</div><h1>Pick a lab</h1>
{cards}
<p class=n>Tutor is live — every step has a chat you can send screenshots to.</p>
</div></body></html>"""


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code: int, body: bytes, ctype: str):
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

        if u.path in ("/", "/index.html"):
            cards = "".join(
                f'<a class="card" href="/{i}/lab.html"><b>{t}</b><span>{d}</span></a>'
                for i, t, d in LABS)
            return self._send(200, INDEX.format(cards=cards).encode(), "text/html; charset=utf-8")

        if u.path == "/lab-chat.js":
            f = PROJECTS / "lab-chat.js"
            return self._send(200, f.read_bytes(), "text/javascript; charset=utf-8")

        if u.path == "/api/chat":
            try:
                lab = q.get("lab", [""])[0]
                step = q.get("step", ["general"])[0]
                return self._json({"turns": load_threads(lab).get(step, {}).get("turns", [])})
            except Exception as e:
                return self._json({"error": str(e)}, 400)

        # static files under projects/, confined there
        target = (PROJECTS / u.path.lstrip("/")).resolve()
        if not str(target).startswith(str(PROJECTS.resolve())) or not target.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = {".html": "text/html; charset=utf-8", ".js": "text/javascript",
                 ".css": "text/css", ".png": "image/png", ".json": "application/json",
                 ".svg": "image/svg+xml"}.get(target.suffix, "application/octet-stream")
        return self._send(200, target.read_bytes(), ctype)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/chat":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length") or 0)
        if n > 22_000_000:
            return self._json({"error": "That screenshot is too large."}, 413)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad request"}, 400)
        try:
            return self._json(ask(
                body.get("lab", ""), str(body.get("step", "general"))[:40],
                (body.get("message") or "").strip(),
                body.get("stepText") or "", body.get("image")))
        except Exception as e:
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"\n  Labs:  http://localhost:{PORT}\n  Ctrl+C to stop\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("  stopped")
