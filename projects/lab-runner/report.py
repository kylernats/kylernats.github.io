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

import diagrams


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


# ================================================================== guide ====
GUIDE_CSS = CSS + diagrams.CSS + """
/* ---- screen: dark, with a sticky contents rail ---- */


/* ---- print: light, A4, no rail ---- */


figure.shotimg{margin:12px 0;page-break-inside:avoid}
figure.shotimg img{width:100%;border:1px solid var(--line);border-radius:6px;display:block}
figure.shotimg figcaption{font-size:9.5pt;color:var(--mut);margin-top:6px}
.dgcap{font-size:9.5pt;color:var(--mut);margin:-4px 0 16px;text-align:center}
.anng{border:1px solid var(--line);border-radius:5px;padding:8px 12px;margin:6px 0 12px}
.anng-code{background:none;border:none;border-left:none;border-radius:0;padding:4px 0 0;
  margin:0;font-size:8.5pt;line-height:1.5;color:var(--accent);white-space:pre-wrap}
.anng-note{font-size:9pt;line-height:1.55;color:var(--mut);margin:2px 0 8px;
  padding-left:10px;border-left:2px solid var(--line)}

.toc{columns:2;column-gap:26px;font-size:9.5pt;margin-top:10px}
.toc div{break-inside:avoid;margin-bottom:3px;color:var(--mut)}
.toc .p{font-weight:650;color:var(--ink);margin-top:9px}
.toc .n{font-family:ui-monospace,monospace;color:var(--faint);font-size:8.5pt}

.where{background:#f7f9fc;border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:4px;padding:8px 11px;margin:0 0 11px;font-size:9.5pt}
.where .k{font:600 7.5pt ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;
  color:var(--faint);margin-right:5px}

.lbl{font:600 7.5pt ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;
  color:var(--faint);display:block;margin:12px 0 5px}
.real{border-left:2px solid #0284c7;background:#f0f9ff;padding:9px 12px;margin:10px 0;
  border-radius:0 4px 4px 0;font-size:9.5pt}
.real .lbl{color:#0284c7;margin-top:0}
.why2{border-left:2px solid #7c3aed;background:#f5f3ff;padding:9px 12px;margin:10px 0;
  border-radius:0 4px 4px 0;font-size:9.5pt}
.why2 .lbl{color:#7c3aed;margin-top:0}
ul.props{margin:4px 0 0;padding-left:18px;font-size:9.5pt}
ul.props li{margin-bottom:3px}

.cmd{background:#1e232b;color:#e8ebf0;border-radius:4px;padding:9px 12px;margin:8px 0;
  font-family:ui-monospace,monospace;font-size:8.5pt;line-height:1.5;white-space:pre-wrap;
  word-break:break-word}

.answer{border:1px solid var(--line);border-radius:4px;margin:11px 0;overflow:hidden;
  page-break-inside:avoid}
.answer .h{background:#f1f4f8;padding:6px 11px;font:600 8pt ui-monospace,monospace;
  letter-spacing:.1em;text-transform:uppercase;color:var(--mut);border-bottom:1px solid var(--line)}
.answer pre{border:none;border-left:none;border-radius:0;margin:0;background:#fff}

.shotbox{border:1px dashed var(--amber);background:var(--amber-bg);border-radius:4px;
  padding:9px 12px;margin:10px 0;font-size:9.5pt;page-break-inside:avoid}
.shotbox .h{font:600 8pt ui-monospace,monospace;letter-spacing:.1em;text-transform:uppercase;
  color:var(--amber);margin-bottom:4px}
.shotbox .slug{font-family:ui-monospace,monospace;font-weight:650}
.callout2{background:#f7f9fc;border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:4px;padding:10px 13px;margin:11px 0;font-size:9.5pt}

@media screen {
  :root{--ink:#E8EBF0;--mut:#98A2B3;--faint:#6B7484;--line:#232932;--accent:#2DD4BF;
        --accent-bg:rgba(45,212,191,.08);--amber:#FBBF24;--amber-bg:rgba(251,191,36,.07);}
  body{background:#0B0D10;font-size:15px;line-height:1.65}
  code{background:#1A1F27;border-color:#232932;color:#5EEAD4}
  pre{background:#0F1216;border-color:#232932}
  th{background:#0F1216}
  .wrapg{display:grid;grid-template-columns:260px minmax(0,1fr);gap:40px;
         max-width:1280px;margin:0 auto;padding:0 28px}
  .railg{position:sticky;top:0;align-self:start;max-height:100vh;overflow-y:auto;
         padding:26px 0;font-size:13px}
  .railg a{display:block;padding:4px 8px;border-radius:5px;color:var(--mut);text-decoration:none}
  .railg a:hover{background:#13171D;color:var(--ink)}
  .railg .p{font:600 10px ui-monospace,monospace;letter-spacing:.12em;text-transform:uppercase;
            color:var(--faint);margin:14px 0 4px;padding:0 8px}
  .bodyg{padding:26px 0 90px;min-width:0}
  .cover{min-height:auto;padding:40px 0 30px;border-bottom:1px solid var(--line)}
  .cover h1{font-size:34px}
  .cover .sub{font-size:17px}
  .phase{padding-top:34px}
  .step{background:#13171D;border:1px solid var(--line);border-radius:12px;padding:20px;
        margin-bottom:18px}
  .step:last-child{border-bottom:1px solid var(--line)}
  .where{background:#0F1216}
  .real{background:rgba(56,189,248,.07);border-left-color:#38BDF8}
  .real .lbl{color:#38BDF8}
  .why2{background:rgba(167,139,250,.07);border-left-color:#A78BFA}
  .why2 .lbl{color:#A78BFA}
  .answer{border-color:var(--line)}
  .answer .h{background:#1A1F27;color:var(--mut);border-color:var(--line)}
  .answer pre{background:#0B0D10}
  .shotbox{background:rgba(251,191,36,.07)}
  .callout2{background:#0F1216}
  .cmd{background:#0F1216;border:1px solid var(--line)}
  .stats div{background:#13171D}
  .contents-print{display:none}
  .dg{--dg-fill:#13171D;--dg-fill-key:rgba(45,212,191,.1);--dg-fill-out:#0F1216;
      --dg-stroke:#313947;--dg-stroke2:#6B7484;--dg-ink:#E8EBF0;--dg-mut:#98A2B3;
      --dg-accent:#2DD4BF;--dg-violet:#A78BFA;--dg-bad:#FB7185;
      border:1px solid var(--line);border-radius:10px;background:#0F1216;padding:14px}
  figure.shotimg img{border-color:var(--line)}

  /* print sizes are set in pt; on screen they read as cramped */
  .callout2,.real,.why2,.shotbox{font-size:14px;line-height:1.65;padding:13px 16px}
  ul.props{font-size:14px;line-height:1.7}
  .task{font-size:13.5px}
  .cmd{font-size:12.5px;line-height:1.6;padding:11px 14px}
  .dgcap{font-size:13px;line-height:1.6}
  .where{font-size:13.5px;padding:10px 13px}
  .answer pre{font-size:12.5px;line-height:1.6}
  .step p{line-height:1.65}
  .section-title{font-size:22px}
  .phase-title{font-size:24px}
  .step-h h3{font-size:17px}
  .phase-blurb{font-size:14px}
}

@media print {
  .railg{display:none}
  .wrapg{display:block;max-width:none;padding:0}
  .dg{--dg-fill:#fff;--dg-fill-key:#ecfdf9;--dg-fill-out:#f7f9fc;
      --dg-stroke:#dde2e9;--dg-stroke2:#8a93a1;--dg-ink:#14181f;--dg-mut:#5b6472;
      --dg-accent:#0d9488;--dg-violet:#7c3aed;--dg-bad:#be123c;
      page-break-inside:avoid}
}
"""


def build_guide(lab: dict, lab_root: Path, evidence_url: str = "") -> str:
    """The full instruction manual: every step, every argument, the reference
    code, and every screenshot point. Meant to be followed start to finish."""
    today = time.strftime("%d %B %Y")
    all_steps = [s for ph in lab["phases"] for s in ph["steps"]]
    n_shots = sum(len(s.get("shots") or []) for s in all_steps)

    shots_dir = lab_root / "docs" / "evidence" / "screenshots"
    have = sorted(p.name for p in shots_dir.glob("*.png")) if shots_dir.is_dir() else []

    def shot_file(slug: str):
        return next((n for n in have if slug in n), None)

    o = ["<!DOCTYPE html><html lang=en><head><meta charset=utf-8>",
         f"<title>{html.escape(lab['title'])} — full guide</title>",
         f"<style>{GUIDE_CSS}</style></head><body>",
         '<div class="wrapg">']

    rail = ['<nav class="railg">']
    for ph in lab["phases"]:
        rail.append(f'<div class="p">{html.escape(ph["title"])}</div>')
        for st in ph["steps"]:
            rail.append(f'<a href="#s{html.escape(st["id"])}">{html.escape(st["id"])} &nbsp; '
                        f'{html.escape(st["title"])}</a>')
    rail.append("</nav>")
    o += rail
    o.append('<div class="bodyg">')

    o.append(f"""
<section class="cover">
  <div class="kicker">{html.escape(lab.get('eyebrow','Lab'))} &nbsp;·&nbsp; Full guide</div>
  <h1>{html.escape(lab['title'])}</h1>
  <div class="sub">{html.escape(lab.get('subtitle',''))}</div>
  <div class="meta">
    <div><span class="k">For</span>Kyler Nats</div>
    <div><span class="k">Generated</span>{today}</div>
    <div><span class="k">Steps</span>{len(all_steps)} across {len(lab['phases'])} phases</div>
    <div><span class="k">Screenshots</span>{n_shots} capture points</div>
  </div>
</section>""")

    # contents
    o.append('<section class="contents-print"><h2 class="section-title">Contents</h2><div class="toc">')
    for ph in lab["phases"]:
        o.append(f'<div class="p">{html.escape(ph["id"])} &nbsp; {html.escape(ph["title"])}</div>')
        for st in ph["steps"]:
            o.append(f'<div><span class="n">{html.escape(st["id"])}</span> &nbsp; {html.escape(st["title"])}</div>')
    o.append("</div></section>")
    o.append(f'<section><div class="callout2">Every command in this guide is run '
             f'from <code>projects/01-cost-visibility/</code> unless the command says otherwise. '
             f'Terraform files live in <code>terraform/</code> inside that folder. '
             f'Check progress any time with <code>./scripts/check.sh</code> — it never touches '
             f'Azure and never costs anything.</div></section>')

    # ---- how the pieces fit together ----
    o.append('<section class="phase"><h2 class="section-title">How it fits together</h2>')
    o.append('<p style="font-size:10pt;color:var(--mut)">Fourteen resources, but only three '
             'paths through them. An alerting path that ends at a human, a data path that ends '
             'at a dashboard, and an identity that is allowed to read the bill and nothing '
             'else.</p>')
    o.append(diagrams.ARCHITECTURE)
    o.append('<div class="dgcap">Solid lines carry data. Dashed lines are permission and '
             'delivery. Everything left of the storage account is built by Terraform; the '
             'workbook tiles get added in the portal in phase 11.</div>')

    o.append('<h3 style="margin-top:26px;font-size:13pt">Why the forecast alert is the one '
             'that matters</h3>')
    o.append('<p style="font-size:10pt;color:var(--mut)">Most people set a budget alert at '
             '100% and stop. That alert tells you the money is already gone. A forecast alert '
             'watches the slope instead of the total, so it fires while there is still a month '
             'left to do something about it.</p>')
    o.append(diagrams.FORECAST)
    o.append('<div class="dgcap">Same spending, two alerts. The actual-spend alert is correct '
             'and useless; by the time it fires the budget is spent.</div>')
    o.append('</section>')

    for ph in lab["phases"]:
        o.append(f'<section class="phase"><div class="phase-n">{html.escape(ph["id"])}</div>'
                 f'<h2 class="phase-title">{html.escape(ph["title"])}</h2>')
        if ph.get("blurb"):
            o.append(f'<div class="phase-blurb">{ph["blurb"]}</div>')

        for st in ph["steps"]:
            o.append(f'<div class="step" id="s{html.escape(st["id"])}">')
            o.append(f'<div class="step-h"><span class="id">{html.escape(st["id"])}</span>'
                     f'<h3>{html.escape(st["title"])}</h3></div>')

            if st.get("where"):
                o.append(f'<div class="where"><span class="k">Write it in</span>'
                         f'<code>{html.escape(st["where"]["file"])}</code> '
                         f'<span class="k" style="margin-left:8px">replacing</span>'
                         f'<code>{html.escape(st["where"]["marker"])}</code></div>')

            if st.get("what"):
                o.append(f'<p style="font-size:10pt;margin:0 0 8px">{st["what"]}</p>')
            if st.get("real"):
                o.append(f'<div class="real"><span class="lbl">Real life</span>{st["real"]}</div>')
            if st.get("why"):
                o.append(f'<div class="why2"><span class="lbl">Why it matters</span>{st["why"]}</div>')

            if st.get("props"):
                res = st.get("resource")
                o.append('<span class="lbl">What to set'
                         + (f' on <code>{html.escape(res)}</code>' if res else '') + '</span>')
                o.append('<ul class="props">' +
                         "".join(f"<li>{x}</li>" for x in st["props"]) + "</ul>")

            if st.get("annotated"):
                o.append('<span class="lbl">Line by line</span><div class="anng">')
                for r in st["annotated"]:
                    o.append(f'<pre class="anng-code"><code>{html.escape(r["code"])}</code></pre>')
                    if r.get("note"):
                        note = re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(r["note"]))
                        note = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", note)
                        o.append(f'<div class="anng-note">{note}</div>')
                o.append("</div>")

            if st.get("table"):
                t = st["table"]
                o.append("<table><thead><tr>" +
                         "".join(f"<th>{h}</th>" for h in t["head"]) + "</tr></thead><tbody>" +
                         "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                                 for r in t["rows"]) + "</tbody></table>")

            for c in (st.get("commands") or []):
                if c.get("label"):
                    o.append(f'<span class="lbl">{html.escape(c["label"])}</span>')
                o.append(f'<div class="cmd">{html.escape(c["cmd"])}</div>')

            if st.get("callout"):
                o.append(f'<div class="callout2">{st["callout"]}</div>')

            for sh in (st.get("shots") or []):
                o.append(f'<div class="shotbox"><div class="h">Screenshot</div>'
                         f'<div><span class="slug">{html.escape(sh["slug"])}</span> — {sh["desc"]}</div>'
                         f'<div class="cmd" style="margin-bottom:0">'
                         f'./scripts/capture.sh {html.escape(sh["slug"])} '
                         f'"{html.escape(sh.get("caption",""))}"</div></div>')
                f = shot_file(sh["slug"])
                if f and evidence_url:
                    o.append(f'<figure class="shotimg"><img src="{evidence_url}{f}" alt="">'
                             f'<figcaption>Captured: {html.escape(sh.get("caption",""))}'
                             f'</figcaption></figure>')

            hints = st.get("hints") or []
            if hints and st.get("hintStyle") != "faq":
                for i, hn in enumerate(hints):
                    if hn.get("text") and i == 0:
                        o.append(f'<span class="lbl">Hint</span>'
                                 f'<div style="font-size:9.5pt;color:var(--mut)">{hn["text"]}</div>')
                    if hn.get("code") and i == len(hints) - 1:
                        o.append('<div class="answer"><div class="h">Reference solution — '
                                 'try it yourself first</div>'
                                 f'<pre><code>{html.escape(hn["code"])}</code></pre></div>')
            elif hints:
                for hn in hints:
                    o.append(f'<span class="lbl">{html.escape(hn["label"])}</span>'
                             f'<div style="font-size:9.5pt;color:var(--mut)">{md(hn.get("text",""))}</div>')
                    if hn.get("code"):
                        o.append(f'<pre><code>{html.escape(hn["code"])}</code></pre>')
            o.append("</div>")
        o.append("</section>")

    o.append(f'<footer>{html.escape(lab["title"])} — full guide, generated {today}</footer>')
    o.append("</div></div></body></html>")
    return "".join(o)
