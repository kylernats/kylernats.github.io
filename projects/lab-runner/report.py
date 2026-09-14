#!/usr/bin/env python3
"""Build a printable lab report from the lab content, the learner's notes, the
captured evidence, and the running logs.

Rendered light rather than in the site's dark theme: this is a document meant to
be read and printed, not a web page.
"""

import html
import json
import re
import time
from pathlib import Path


# ------------------------------------------------------------------ markdown --
def md(text: str) -> str:
    """Enough markdown for the notes and the two log files. Not a full parser."""
    if not text:
        return ""

    fence = chr(96) * 3
    chunks = text.split(fence)
    out = []

    for i, chunk in enumerate(chunks):
        if i % 2 == 1:                                   # fenced code
            body = re.sub(r"^[\w-]*\n", "", chunk).rstrip("\n")
            out.append(f"<pre><code>{html.escape(body)}</code></pre>")
            continue

        lines = html.escape(chunk).split("\n")
        buf, list_items = [], None

        for line in lines:
            stripped = line.strip()

            if re.fullmatch(r"-{3,}", stripped):
                if list_items is not None:
                    buf.append("<ul><li>" + "</li><li>".join(list_items) + "</li></ul>")
                    list_items = None
                buf.append("<hr>")
                continue

            h = re.match(r"(#{1,4})\s+(.*)", stripped)
            if h:
                if list_items is not None:
                    buf.append("<ul><li>" + "</li><li>".join(list_items) + "</li></ul>")
                    list_items = None
                lvl = min(len(h.group(1)) + 1, 5)
                buf.append(f"<h{lvl}>{h.group(2)}</h{lvl}>")
                continue

            li = re.match(r"[-*]\s+(.*)", stripped)
            if li:
                if list_items is None:
                    list_items = []
                list_items.append(li.group(1))
                continue

            if list_items is not None:
                buf.append("<ul><li>" + "</li><li>".join(list_items) + "</li></ul>")
                list_items = None

            if stripped:
                buf.append(f"<p>{stripped}</p>")

        if list_items is not None:
            buf.append("<ul><li>" + "</li><li>".join(list_items) + "</li></ul>")

        chunk_html = "".join(buf)
        chunk_html = re.sub(r"`([^`]+)`", r"<code>\1</code>", chunk_html)
        chunk_html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", chunk_html)
        chunk_html = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", chunk_html)
        out.append(chunk_html)

    return "".join(out)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


CSS = """
@page { size: A4; margin: 18mm 16mm 20mm; }
:root{--ink:#14181f;--mut:#5b6472;--faint:#8a93a1;--line:#dde2e9;--accent:#0d9488;
      --accent-bg:#ecfdf9;--amber:#b45309;--amber-bg:#fffbeb;}
*{box-sizing:border-box}
body{margin:0;font:11pt/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     color:var(--ink);background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
code{background:#f1f4f8;border:1px solid var(--line);border-radius:3px;padding:.05em .3em;font-size:.88em}
pre{background:#f7f9fc;border:1px solid var(--line);border-left:3px solid var(--accent);
    border-radius:4px;padding:10px 12px;overflow-x:auto;font-size:9pt;line-height:1.5}
pre code{background:none;border:none;padding:0}
h1,h2,h3,h4{line-height:1.25;margin:0}
a{color:var(--accent);text-decoration:none}
hr{border:none;border-top:1px solid var(--line);margin:14px 0}

.cover{min-height:88vh;display:flex;flex-direction:column;justify-content:center;
       page-break-after:always}
.cover .kicker{font:600 9pt/1 ui-monospace,monospace;letter-spacing:.18em;text-transform:uppercase;
       color:var(--accent);margin-bottom:14px}
.cover h1{font-size:30pt;letter-spacing:-.02em;margin-bottom:10px}
.cover .sub{font-size:13pt;color:var(--mut);max-width:34em;margin-bottom:28px}
.cover .meta{border-top:1px solid var(--line);padding-top:16px;display:grid;
       grid-template-columns:repeat(2,1fr);gap:10px 28px;max-width:30em}
.cover .meta div{font-size:10pt}
.cover .meta .k{color:var(--faint);font:600 8pt/1.4 ui-monospace,monospace;
       letter-spacing:.12em;text-transform:uppercase;display:block;margin-bottom:2px}

.phase{page-break-before:always}
.phase-title{font-size:17pt;letter-spacing:-.01em;padding-bottom:7px;
       border-bottom:2px solid var(--accent);margin-bottom:6px}
.phase-n{font:600 8.5pt ui-monospace,monospace;letter-spacing:.14em;color:var(--accent);
       text-transform:uppercase}
.phase-blurb{color:var(--mut);font-size:10pt;margin:8px 0 18px}

.step{page-break-inside:avoid;margin-bottom:22px;padding-bottom:18px;border-bottom:1px solid var(--line)}
.step:last-child{border-bottom:none}
.step-h{display:flex;align-items:baseline;gap:9px;margin-bottom:8px}
.step-h .id{font:600 9pt ui-monospace,monospace;color:var(--faint)}
.step-h h3{font-size:12.5pt}
.step-h .tick{color:var(--accent);font-weight:700}
.meta-line{font-size:8.5pt;color:var(--faint);font-family:ui-monospace,monospace;margin-bottom:8px}
.task{font-size:9.5pt;color:var(--mut);margin-bottom:10px;padding-left:11px;
   border-left:2px solid var(--line)}
.task .lbl{display:block;font:600 7.5pt ui-monospace,monospace;letter-spacing:.12em;
   text-transform:uppercase;color:var(--faint);margin-bottom:3px}
.task p{margin:0}

.note{background:var(--accent-bg);border:1px solid #bfeee5;border-left:3px solid var(--accent);
      border-radius:4px;padding:11px 13px;margin:10px 0}
.note .lbl{font:600 8pt ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;
      color:var(--accent);margin-bottom:5px}
.note p{margin:0 0 6px}.note p:last-child{margin:0}

.shot{margin:12px 0;page-break-inside:avoid}
.shot img{width:100%;border:1px solid var(--line);border-radius:4px;display:block}
.shot figcaption{font-size:8.5pt;color:var(--mut);margin-top:5px;padding-left:2px}
.shot .slug{font:600 8pt ui-monospace,monospace;color:var(--faint)}

.missing{font-size:9pt;color:var(--amber);background:var(--amber-bg);border:1px solid #fde68a;
      border-radius:4px;padding:7px 10px;margin:8px 0}

table{width:100%;border-collapse:collapse;font-size:9.5pt;margin:10px 0}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{font:600 8pt ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;
   color:var(--faint);background:#f7f9fc}

.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);
   border:1px solid var(--line);border-radius:5px;overflow:hidden;margin:16px 0}
.stats div{background:#fff;padding:12px 14px}
.stats .v{font-size:17pt;font-weight:650;letter-spacing:-.02em}
.stats .k{font-size:8.5pt;color:var(--faint);margin-top:2px}

.section-title{font-size:15pt;margin:0 0 4px;padding-bottom:6px;border-bottom:2px solid var(--accent)}
footer{margin-top:26px;padding-top:10px;border-top:1px solid var(--line);
   font-size:8.5pt;color:var(--faint);text-align:center}
"""


def build(lab: dict, state: dict, lab_root: Path, evidence_url: str) -> str:
    notes = state.get("notes", {}) or {}
    checked = set(state.get("checked", []) or [])
    hints = state.get("hints", {}) or {}

    shots_dir = lab_root / "docs" / "evidence" / "screenshots"
    have = {p.name for p in shots_dir.glob("*.png")} if shots_dir.is_dir() else set()

    def shot_file(slug: str):
        for n in sorted(have):
            if slug in n:
                return n
        return None

    all_steps = [s for ph in lab["phases"] for s in ph["steps"]]
    all_shots = [sh for s in all_steps for sh in (s.get("shots") or [])]
    captured = [sh for sh in all_shots if shot_file(sh["slug"])]
    written = [s for s in all_steps if (notes.get(s["id"]) or "").strip()]
    unaided = [s for s in all_steps if s.get("hints") and not hints.get(s["id"])
               and s["id"] in checked and s.get("hintStyle") != "faq"]

    today = time.strftime("%d %B %Y")
    out = [f"<!DOCTYPE html><html lang=en><head><meta charset=utf-8>",
           f"<title>{html.escape(lab['title'])} — lab report</title>",
           f"<style>{CSS}</style></head><body>"]

    # ------------------------------------------------------------------ cover --
    out.append(f"""
<section class="cover">
  <div class="kicker">{html.escape(lab.get('eyebrow','Lab report'))}</div>
  <h1>{html.escape(lab['title'])}</h1>
  <div class="sub">{html.escape(lab.get('subtitle',''))}</div>
  <div class="meta">
    <div><span class="k">Author</span>Kyler Nats</div>
    <div><span class="k">Date</span>{today}</div>
    <div><span class="k">Steps completed</span>{len(checked)} of {len(all_steps)}</div>
    <div><span class="k">Evidence captured</span>{len(captured)} of {len(all_shots)} screenshots</div>
  </div>
</section>""")

    # ---------------------------------------------------------------- summary --
    out.append(f"""
<section>
  <h2 class="section-title">Summary</h2>
  <div class="stats">
    <div><div class="v">{len(checked)}/{len(all_steps)}</div><div class="k">Steps done</div></div>
    <div><div class="v">{len(captured)}</div><div class="k">Screenshots</div></div>
    <div><div class="v">{len(written)}</div><div class="k">Steps annotated</div></div>
    <div><div class="v">{len(unaided)}</div><div class="k">Done without hints</div></div>
  </div>
  <p style="color:var(--mut);font-size:10pt">Notes below are what I wrote while working.
  Screenshots were taken at the time. Hint counts show where I needed help.</p>
</section>""")

    # ------------------------------------------------------------------ phases --
    for ph in lab["phases"]:
        steps = ph["steps"]
        if not any(s["id"] in checked or (notes.get(s["id"]) or "").strip() for s in steps):
            continue  # skip phases not started

        out.append(f'<section class="phase"><div class="phase-n">{html.escape(ph["id"])}</div>'
                   f'<h2 class="phase-title">{html.escape(ph["title"])}</h2>')
        if ph.get("blurb"):
            out.append(f'<div class="phase-blurb">{md(strip_tags(ph["blurb"]))}</div>')

        for s in steps:
            note = (notes.get(s["id"]) or "").strip()
            done = s["id"] in checked
            if not done and not note:
                continue

            lvl = hints.get(s["id"])
            out.append('<div class="step">')
            out.append(f'<div class="step-h"><span class="id">{html.escape(s["id"])}</span>'
                       f'<h3>{html.escape(s["title"])}</h3>'
                       f'{"<span class=tick>done</span>" if done else ""}</div>')

            bits = []
            if s.get("where"):
                bits.append(f'{s["where"]["file"]}')
            bits.append("no hints used" if not lvl else f"hint level {lvl} used")
            out.append(f'<div class="meta-line">{html.escape("  ·  ".join(bits))}</div>')

            if s.get("what"):
                out.append('<div class="task"><span class="lbl">Task</span>'
                           f'{md(strip_tags(s["what"]))}</div>')

            if note:
                out.append(f'<div class="note"><div class="lbl">What happened</div>{md(note)}</div>')

            for sh in (s.get("shots") or []):
                f = shot_file(sh["slug"])
                if f:
                    out.append(f'<figure class="shot"><img src="{evidence_url}/{f}" alt="">'
                               f'<figcaption><span class="slug">{html.escape(sh["slug"])}</span> — '
                               f'{html.escape(sh.get("caption",""))}</figcaption></figure>')
                else:
                    out.append(f'<div class="missing">Screenshot <code>{html.escape(sh["slug"])}</code> '
                               f'not captured.</div>')
            out.append("</div>")
        out.append("</section>")

    # ------------------------------------------------- decisions and lab log --
    for fname, title in (("DECISIONS.md", "Decisions"), ("LAB-LOG.md", "Lab log")):
        f = lab_root / "docs" / fname
        if not f.is_file():
            continue
        body = f.read_text(encoding="utf-8")
        body = re.sub(r"^#\s+.*\n", "", body, count=1)   # drop its own H1
        out.append(f'<section class="phase"><h2 class="section-title">{title}</h2>{md(body)}</section>')

    out.append(f'<footer>{html.escape(lab["title"])} — generated {today} from the lab runner</footer>')
    out.append("</body></html>")
    return "".join(out)
