#!/usr/bin/env python3
"""Build a self-contained animated walkthrough for a lab.

Plays like a short video: timed scenes, animated diagrams, play/pause, and
optional narration through the browser's built-in speech synthesis. No ffmpeg,
no media files, nothing to install -- it opens by double-clicking.

    python3 projects/lab-runner/build-walkthrough.py [lab-id]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import diagrams  # noqa: E402

PROJECTS = ROOT.parent
LAB_ID = sys.argv[1] if len(sys.argv) > 1 else "01-cost-visibility"

SCENES = [
    {
        "k": "The problem",
        "h": "A cloud bill nobody is watching",
        "n": ("A business moves to the cloud on a five thousand dollar a month estimate. "
              "The first bill is eight thousand. Nobody notices, because nobody is watching "
              "a number that only shows up once a month."),
        "sec": 11,
        "body": """
          <div class="bill">
            <div class="billrow"><span>Estimated</span><b>$5,000</b></div>
            <div class="billrow"><span>Month 1</span><b class="up1">$8,000</b></div>
            <div class="billrow"><span>Month 2</span><b class="up2">$17,000</b></div>
            <div class="billrow"><span>Month 3</span><b class="up3">$30,000</b></div>
          </div>
          <p class="kick">Nothing failed. Nobody was breached.<br>The bill grew where nobody was looking.</p>""",
    },
    {
        "k": "Why the usual fix fails",
        "h": "An alert at 100% tells you the money is gone",
        "n": ("Most people set a budget alert at one hundred percent and stop there. "
              "That alert is correct and useless. By the time it fires, the budget is "
              "already spent."),
        "sec": 10,
        "body": """
          <div class="two">
            <div class="pane bad">
              <div class="pt">What most people build</div>
              <div class="pb">Budget alert at 100%</div>
              <div class="pn">Fires on day 30. Money already spent.</div>
            </div>
            <div class="pane good">
              <div class="pt">What this build does</div>
              <div class="pb">Forecast alert at 100%</div>
              <div class="pn">Fires on day 12. Still time to act.</div>
            </div>
          </div>""",
    },
    {
        "k": "The core idea",
        "h": "Watch the slope, not the total",
        "n": ("A forecast alert watches the rate of spending instead of the running total. "
              "On the same spending curve it fires eighteen days earlier. That difference "
              "is the entire point of this project."),
        "sec": 13,
        "body": diagrams.FORECAST,
    },
    {
        "k": "Architecture",
        "h": "Fourteen resources, three paths",
        "n": ("Fourteen resources, but only three paths through them. An alerting path that "
              "ends at a human. A data path that ends at a dashboard. And an identity that is "
              "allowed to read the bill and nothing else."),
        "sec": 15,
        "body": diagrams.ARCHITECTURE,
    },
    {
        "k": "Security layer",
        "h": "The part that makes it a security project",
        "n": ("Cost data is sensitive. It reveals what systems you run and how big you are. "
              "So the identity that reads it holds one role and nothing more, the storage is "
              "locked down, and every read of the data is logged."),
        "sec": 14,
        "body": """
          <ul class="sec">
            <li><b>Cost Management Reader</b><span>One role. If it leaks, someone learns a bill. That is the whole blast radius.</span></li>
            <li><b>No password exists</b><span>A managed identity, so there is no credential to hardcode and leak.</span></li>
            <li><b>TLS 1.2, no public access</b><span>The control that stops the storage breach that makes headlines every year.</span></li>
            <li><b>Versioning + soft delete</b><span>Ransomware overwrites files. Versioning means the originals are still there.</span></li>
            <li><b>Diagnostic logging</b><span>Records who <i>read</i> the billing data, not just what it said.</span></li>
          </ul>""",
    },
    {
        "k": "How it gets built",
        "h": "Local first, then real, then destroyed",
        "n": ("Development happens locally where it costs nothing. Then it deploys to real "
              "Azure, gets exercised, and the evidence is captured. Then terraform destroy, "
              "so the bill stays near zero."),
        "sec": 13,
        "body": """
          <div class="loops">
            <div class="loop"><span class="ln">1</span><b>Build locally</b>
              <p>Azurite, Functions Core Tools, SQL in Docker. Free, break it as often as you like.</p></div>
            <div class="arrowr">&rarr;</div>
            <div class="loop"><span class="ln">2</span><b>Deploy for real</b>
              <p>terraform apply, use it, capture screenshots, logs, the cost report.</p></div>
            <div class="arrowr">&rarr;</div>
            <div class="loop"><span class="ln">3</span><b>Tear it down</b>
              <p>terraform destroy, confirm nothing is still billing, write up what broke.</p></div>
          </div>
          <p class="kick small">The local emulator cannot fake versioning, cost data, RBAC, or Defender.
          That is why the real deploy is not optional.</p>""",
    },
    {
        "k": "What you end up with",
        "h": "Seven things you can say in an interview",
        "n": ("At the end you can say you built cloud cost governance as infrastructure as code, "
              "configured alerting that warns before overspend, applied a storage security "
              "baseline, implemented least privilege and proved it by testing denial, and "
              "documented the gap you could not close."),
        "sec": 15,
        "body": """
          <ul class="out">
            <li>Built cost governance as infrastructure-as-code</li>
            <li>Alerting that warns <i>before</i> overspend, not after</li>
            <li>Storage baseline: TLS 1.2, no public access, versioning, soft delete</li>
            <li>Least privilege &mdash; and <b>proved it by testing denial</b></li>
            <li>Verified the alert path end to end, code to inbox</li>
            <li>Logged access to sensitive billing data</li>
            <li>Documented the gap free tier could not close, and why</li>
          </ul>""",
    },
]

CSS = """
*{box-sizing:border-box}*{margin:0}
:root{--bg:#0B0D10;--surface:#13171D;--line:#232932;--line2:#313947;
 --ink:#E8EBF0;--mut:#98A2B3;--faint:#6B7484;--acc:#2DD4BF;--bad:#FB7185;--amb:#FBBF24;
 --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
 --sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 --dg-fill:#13171D;--dg-fill-key:rgba(45,212,191,.1);--dg-fill-out:#0F1216;
 --dg-stroke:#313947;--dg-stroke2:#6B7484;--dg-ink:#E8EBF0;--dg-mut:#98A2B3;
 --dg-accent:#2DD4BF;--dg-violet:#A78BFA;--dg-bad:#FB7185;}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);min-height:100vh;
 display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
.stage{width:min(1080px,100%);background:var(--surface);border:1px solid var(--line);
 border-radius:18px;padding:clamp(24px,4vw,48px);min-height:min(660px,78vh);
 display:flex;flex-direction:column;position:relative;overflow:hidden}
.kicker{font:500 11px var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--acc)}
h1{font-size:clamp(23px,3.4vw,34px);letter-spacing:-.025em;margin:10px 0 22px;line-height:1.2}
.content{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0}
.scene{animation:in .55s cubic-bezier(.22,1,.36,1) both}
@keyframes in{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.kick{margin-top:22px;color:var(--mut);font-size:16px;line-height:1.6}
.kick.small{font-size:14px;margin-top:18px}

.bill{display:flex;flex-direction:column;gap:9px;max-width:460px}
.billrow{display:flex;justify-content:space-between;align-items:baseline;
 background:#0F1216;border:1px solid var(--line);border-radius:9px;padding:13px 18px;
 opacity:0;animation:pop .5s ease both}
.billrow span{color:var(--mut);font-size:14px}
.billrow b{font:650 21px var(--sans);letter-spacing:-.02em}
.billrow:nth-child(1){animation-delay:.2s}.billrow:nth-child(2){animation-delay:1.3s}
.billrow:nth-child(3){animation-delay:2.6s}.billrow:nth-child(4){animation-delay:3.9s}
.up1{color:var(--amb)}.up2{color:#FB923C}.up3{color:var(--bad)}
@keyframes pop{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}

.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.pane{border:1px solid var(--line);border-radius:12px;padding:20px;background:#0F1216;
 opacity:0;animation:pop .5s ease both}
.pane:nth-child(1){animation-delay:.3s}.pane:nth-child(2){animation-delay:1.6s}
.pane.bad{border-color:rgba(251,113,133,.35)}
.pane.good{border-color:var(--acc)}
.pt{font:500 10.5px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}
.pb{font-size:19px;font-weight:620;margin:9px 0 7px;letter-spacing:-.02em}
.pane.bad .pb{color:var(--bad)}.pane.good .pb{color:var(--acc)}
.pn{color:var(--mut);font-size:14px;line-height:1.55}

ul.sec{list-style:none;padding:0;display:flex;flex-direction:column;gap:11px}
ul.sec li{background:#0F1216;border:1px solid var(--line);border-left:2px solid var(--acc);
 border-radius:9px;padding:12px 16px;opacity:0;animation:pop .45s ease both}
ul.sec li:nth-child(1){animation-delay:.2s}ul.sec li:nth-child(2){animation-delay:.9s}
ul.sec li:nth-child(3){animation-delay:1.6s}ul.sec li:nth-child(4){animation-delay:2.3s}
ul.sec li:nth-child(5){animation-delay:3s}
ul.sec b{display:block;font-size:15px;margin-bottom:3px}
ul.sec span{color:var(--mut);font-size:13.5px;line-height:1.55}

.loops{display:grid;grid-template-columns:1fr auto 1fr auto 1fr;gap:12px;align-items:stretch}
.loop{background:#0F1216;border:1px solid var(--line);border-radius:11px;padding:16px;
 opacity:0;animation:pop .5s ease both}
.loop:nth-child(1){animation-delay:.2s}.loop:nth-child(3){animation-delay:1.4s}
.loop:nth-child(5){animation-delay:2.6s}
.ln{display:inline-grid;place-items:center;width:23px;height:23px;border-radius:50%;
 background:rgba(45,212,191,.12);border:1px solid rgba(45,212,191,.4);color:var(--acc);
 font:700 11px var(--mono);margin-bottom:8px}
.loop b{display:block;font-size:15px;margin-bottom:6px}
.loop p{color:var(--mut);font-size:13px;line-height:1.5}
.arrowr{align-self:center;color:var(--faint);font-size:20px;opacity:0;animation:pop .4s ease both}
.arrowr:nth-child(2){animation-delay:1.1s}.arrowr:nth-child(4){animation-delay:2.3s}

ul.out{list-style:none;padding:0;display:flex;flex-direction:column;gap:8px}
ul.out li{padding:11px 16px 11px 38px;background:#0F1216;border:1px solid var(--line);
 border-radius:9px;position:relative;font-size:15px;opacity:0;animation:pop .4s ease both}
ul.out li::before{content:"";position:absolute;left:15px;top:50%;width:7px;height:7px;
 margin-top:-3.5px;border-radius:50%;background:var(--acc)}
ul.out li:nth-child(1){animation-delay:.2s}ul.out li:nth-child(2){animation-delay:.7s}
ul.out li:nth-child(3){animation-delay:1.2s}ul.out li:nth-child(4){animation-delay:1.7s}
ul.out li:nth-child(5){animation-delay:2.2s}ul.out li:nth-child(6){animation-delay:2.7s}
ul.out li:nth-child(7){animation-delay:3.2s}

.dg{width:100%;height:auto;max-height:46vh}
.dg-box{fill:var(--dg-fill);stroke:var(--dg-stroke);stroke-width:1.2}
.dg-src{stroke:var(--dg-accent);stroke-width:1.8}
.dg-key{stroke:var(--dg-accent);stroke-width:1.8;fill:var(--dg-fill-key)}
.dg-out{fill:var(--dg-fill-out)}.dg-id{stroke:var(--dg-violet);stroke-width:1.6}
.dg-t{fill:var(--dg-ink);font:600 13px var(--sans)}
.dg-s{fill:var(--dg-mut);font:11px var(--mono)}
.dg-hl{fill:var(--dg-accent);font-weight:700}.dg-ok{fill:var(--dg-accent);font-weight:700}
.dg-bad{fill:var(--dg-bad);font-weight:700}.dg-l{fill:var(--dg-mut);font:10px var(--mono)}
.dg-line{stroke:var(--dg-stroke2);stroke-width:1.6;fill:none}
.dg-dash{stroke-dasharray:5 4}.dg-head{fill:var(--dg-stroke2)}
.dg-axis{stroke:var(--dg-stroke);stroke-width:1.2}
.dg-limit{stroke:var(--dg-accent);stroke-width:1.5;stroke-dasharray:6 4}
.dg-actual{stroke:var(--dg-ink);stroke-width:2.4;fill:none;
 stroke-dasharray:1200;stroke-dashoffset:1200;animation:draw 3.4s ease .3s forwards}
.dg-proj{stroke:var(--dg-accent);stroke-width:2;stroke-dasharray:7 5;fill:none;
 opacity:0;animation:fade .6s ease 2.1s forwards}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes fade{to{opacity:1}}
.dg-dot{fill:var(--dg-accent)}
.dg-mark{stroke-width:1.4;stroke-dasharray:3 3}
.dg-mark-early{stroke:var(--dg-accent)}.dg-mark-late{stroke:var(--dg-bad)}
.dg-gap{stroke:var(--dg-accent);stroke-width:1.2;fill:none}

.bar{position:absolute;left:0;right:0;bottom:0;height:3px;background:#0B0D10}
.bar i{display:block;height:100%;background:var(--acc);width:0}
.ctl{display:flex;align-items:center;gap:10px;margin-top:22px;width:min(1080px,100%)}
.ctl button{background:var(--surface);border:1px solid var(--line2);color:var(--ink);
 border-radius:9px;padding:9px 15px;font:550 13.5px var(--sans);cursor:pointer}
.ctl button:hover{border-color:var(--acc)}
.ctl .play{background:var(--acc);border-color:var(--acc);color:#04211D;font-weight:650;min-width:92px}
.dots{display:flex;gap:6px;margin-left:auto}
.dots i{width:22px;height:4px;border-radius:2px;background:var(--line2);cursor:pointer;display:block}
.dots i.on{background:var(--acc)}.dots i.seen{background:var(--faint)}
.hint{color:var(--faint);font-size:12px;margin-top:10px;text-align:center;
 width:min(1080px,100%);font-family:var(--mono)}
@media(max-width:820px){.two,.loops{grid-template-columns:1fr}.arrowr{display:none}}
"""


def build() -> str:
    scenes = []
    for i, s in enumerate(SCENES):
        scenes.append(
            f'<div class="scene" data-sec="{s["sec"]}" data-n="{s["n"]}" hidden>'
            f'<div class="kicker">{s["k"]}</div><h1>{s["h"]}</h1>'
            f'<div class="content">{s["body"]}</div></div>')

    dots = "".join(f'<i data-i="{i}"></i>' for i in range(len(SCENES)))

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cost Visibility Dashboard — watch first</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>

<div class="stage" id="stage">{''.join(scenes)}<div class="bar"><i id="bar"></i></div></div>

<div class="ctl">
  <button class="play" id="play">Play</button>
  <button id="prev">Back</button>
  <button id="next">Next</button>
  <button id="narr">Narration: off</button>
  <div class="dots" id="dots">{dots}</div>
</div>
<div class="hint">Space = play/pause &nbsp;·&nbsp; arrow keys = skip &nbsp;·&nbsp; about 90 seconds</div>

<script>
(function(){{
  var scenes=[].slice.call(document.querySelectorAll('.scene'));
  var dots=[].slice.call(document.querySelectorAll('#dots i'));
  var bar=document.getElementById('bar'), play=document.getElementById('play');
  var i=0, playing=false, t0=0, raf=null, narrate=false;

  function speak(s){{
    if(!narrate||!window.speechSynthesis) return;
    speechSynthesis.cancel();
    var u=new SpeechSynthesisUtterance(s.dataset.n);
    u.rate=1.0; u.pitch=1.0;
    speechSynthesis.speak(u);
  }}

  function show(n,restart){{
    if(n<0||n>=scenes.length) return;
    scenes[i].hidden=true; i=n;
    var s=scenes[i];
    // re-trigger the CSS animations
    var c=s.cloneNode(true); s.parentNode.replaceChild(c,s); scenes[i]=c;
    c.hidden=false;
    dots.forEach(function(d,k){{ d.className = k===i?'on':(k<i?'seen':''); }});
    t0=performance.now();
    if(playing) speak(c);
    if(restart!==false) bar.style.width='0%';
  }}

  function tick(now){{
    if(!playing) return;
    var dur=+scenes[i].dataset.sec*1000;
    var p=Math.min(1,(now-t0)/dur);
    bar.style.width=(p*100)+'%';
    if(p>=1){{
      if(i<scenes.length-1) show(i+1);
      else {{ stop(); bar.style.width='100%'; play.textContent='Replay'; }}
    }}
    raf=requestAnimationFrame(tick);
  }}

  function start(){{
    if(play.textContent==='Replay'){{ show(0); }}
    playing=true; play.textContent='Pause'; t0=performance.now();
    speak(scenes[i]);
    raf=requestAnimationFrame(tick);
  }}
  function stop(){{
    playing=false; play.textContent='Play';
    if(raf) cancelAnimationFrame(raf);
    if(window.speechSynthesis) speechSynthesis.cancel();
  }}

  play.onclick=function(){{ playing?stop():start(); }};
  document.getElementById('next').onclick=function(){{ show(i+1); }};
  document.getElementById('prev').onclick=function(){{ show(i-1); }};
  document.getElementById('narr').onclick=function(e){{
    narrate=!narrate;
    e.target.textContent='Narration: '+(narrate?'on':'off');
    if(!narrate&&window.speechSynthesis) speechSynthesis.cancel();
    else if(playing) speak(scenes[i]);
  }};
  dots.forEach(function(d){{ d.onclick=function(){{ show(+d.dataset.i); }}; }});
  document.addEventListener('keydown',function(e){{
    if(e.code==='Space'){{ e.preventDefault(); playing?stop():start(); }}
    if(e.key==='ArrowRight') show(i+1);
    if(e.key==='ArrowLeft') show(i-1);
  }});

  show(0,false);
}})();
</script>
</body></html>"""


def main() -> None:
    matches = sorted(PROJECTS.glob(f"{LAB_ID}*"))
    if not matches:
        sys.exit(f"No project folder matching {LAB_ID!r}")
    out = matches[0] / "docs" / "watch-first.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    print(f"  {out}")
    print(f"  {round(out.stat().st_size / 1024)} KB, {len(SCENES)} scenes")
    print(f"\n  open {out}")


if __name__ == "__main__":
    main()
