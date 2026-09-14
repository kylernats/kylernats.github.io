# Lab Runner

A local, browser-based guide for working through the cloud labs. Python standard
library only — nothing to install.

```bash
./projects/lab-runner/start.sh            # opens lab 01
./projects/lab-runner/start.sh 02-backup  # a different lab
```

Then visit <http://127.0.0.1:7878>.

## What it does beyond static instructions

- **Progress that persists** — check steps off; saved to the lab's repo folder
- **Live Azure panel** — subscription, resource count, budgets, and spend
  against the $200 credit, polled every 60s
- **Live Terraform status** — runs `check.sh` and shows remaining TODOs with
  file and line
- **Live evidence tracker** — scans the screenshots folder and marks each of the
  21 capture points captured or not yet
- **Copy buttons** on every command
- **Three-tier hints** — nudge, then argument names, then working code. The
  level you opened is recorded, so the write-up can stay honest about which
  parts you wrote unaided
- **Built-in tutor** — a chat dock scoped to whichever step you are reading. It
  routes through the local `claude` CLI in print mode, so it uses the existing
  Claude Code plan rather than a separate API key. Read-only tools, so it can
  inspect your actual Terraform and tell you what is wrong, but cannot change
  anything. Threads are per-step and persist in `docs/lab-chat.json`
- **Per-step notes** — saved to `docs/lab-state.json` in the lab's folder, and
  exportable to markdown. This is the raw material for the case study

## Why it's safe to run

- Binds to `127.0.0.1` only
- Every shell command it can run is hardcoded in `server.py`; nothing from the
  browser reaches a shell
- Static file serving is confined to `web/`
- Lab ids are validated against `[0-9a-z-]` before touching the filesystem
- The tutor runs with `--allowed-tools Read Grep Glob` only — no Write, Edit, or
  Bash, so it cannot modify your work or run anything

## Adding a lab

Drop a JSON file in `labs/`. Shape:

```jsonc
{
  "id": "02-backup", "title": "...", "subtitle": "...",
  "phases": [{
    "id": "P1", "title": "Foundation",
    "steps": [{
      "id": "1.1", "title": "Resource group",
      "what": "...", "real": "...", "why": "...",
      "props": ["..."],
      "commands": [{"label": "...", "cmd": "..."}],
      "shots": [{"slug": "...", "desc": "...", "caption": "..."}],
      "hints": [{"label": "...", "text": "..."}, {"label": "...", "code": "..."}]
    }]
  }]
}
```

Everything is optional except `id` and `title`.
