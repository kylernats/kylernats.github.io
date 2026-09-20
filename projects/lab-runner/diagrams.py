"""Inline SVG diagrams for the lab guide.

Styled through CSS classes rather than hardcoded fills, so the same markup works
on the dark screen theme and the light print theme.
"""

ARCHITECTURE = """
<svg viewBox="0 0 880 500" role="img" aria-labelledby="archTitle" class="dg">
  <title id="archTitle">Cost visibility architecture: how the fourteen resources connect</title>
  <defs>
    <marker id="ah" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto">
      <polygon points="0 0, 9 3.5, 0 7" class="dg-head"/>
    </marker>
  </defs>

  <!-- source -->
  <rect x="16" y="150" width="160" height="86" rx="8" class="dg-box dg-src"/>
  <text x="96" y="182" class="dg-t" text-anchor="middle">Azure Cost</text>
  <text x="96" y="200" class="dg-t" text-anchor="middle">Management</text>
  <text x="96" y="220" class="dg-s" text-anchor="middle">the billing data</text>

  <!-- budget -->
  <rect x="236" y="26" width="196" height="104" rx="8" class="dg-box dg-key"/>
  <text x="334" y="50" class="dg-t" text-anchor="middle">Budget</text>
  <text x="334" y="72" class="dg-s" text-anchor="middle">50% · 80% · 100% actual</text>
  <text x="334" y="92" class="dg-s dg-hl" text-anchor="middle">100% FORECASTED</text>
  <text x="334" y="114" class="dg-s" text-anchor="middle">the early warning</text>

  <!-- anomaly -->
  <rect x="236" y="152" width="196" height="72" rx="8" class="dg-box"/>
  <text x="334" y="180" class="dg-t" text-anchor="middle">Anomaly alert</text>
  <text x="334" y="202" class="dg-s" text-anchor="middle">daily spend vs pattern</text>

  <!-- export -->
  <rect x="236" y="288" width="196" height="72" rx="8" class="dg-box"/>
  <text x="334" y="316" class="dg-t" text-anchor="middle">Daily export</text>
  <text x="334" y="338" class="dg-s" text-anchor="middle">ActualCost, month to date</text>

  <!-- action group -->
  <rect x="492" y="60" width="160" height="72" rx="8" class="dg-box"/>
  <text x="572" y="88" class="dg-t" text-anchor="middle">Action group</text>
  <text x="572" y="110" class="dg-s" text-anchor="middle">delivery</text>

  <!-- email -->
  <rect x="704" y="60" width="160" height="72" rx="8" class="dg-box dg-out"/>
  <text x="784" y="88" class="dg-t" text-anchor="middle">Email</text>
  <text x="784" y="110" class="dg-s" text-anchor="middle">a human is told</text>

  <!-- storage -->
  <rect x="492" y="276" width="160" height="96" rx="8" class="dg-box"/>
  <text x="572" y="302" class="dg-t" text-anchor="middle">Storage account</text>
  <text x="572" y="322" class="dg-s" text-anchor="middle">TLS 1.2 · no public</text>
  <text x="572" y="340" class="dg-s" text-anchor="middle">versioning · soft delete</text>
  <text x="572" y="360" class="dg-s" text-anchor="middle">private container</text>

  <!-- workbook -->
  <rect x="704" y="288" width="160" height="72" rx="8" class="dg-box dg-out"/>
  <text x="784" y="316" class="dg-t" text-anchor="middle">Workbook</text>
  <text x="784" y="338" class="dg-s" text-anchor="middle">the dashboard</text>

  <!-- log analytics -->
  <rect x="492" y="412" width="160" height="72" rx="8" class="dg-box"/>
  <text x="572" y="440" class="dg-t" text-anchor="middle">Log Analytics</text>
  <text x="572" y="462" class="dg-s" text-anchor="middle">who read the data</text>

  <!-- identity -->
  <rect x="16" y="300" width="160" height="96" rx="8" class="dg-box dg-id"/>
  <text x="96" y="326" class="dg-t" text-anchor="middle">Managed identity</text>
  <text x="96" y="348" class="dg-s" text-anchor="middle">no password exists</text>
  <text x="96" y="370" class="dg-s dg-hl" text-anchor="middle">Cost Mgmt Reader</text>
  <text x="96" y="388" class="dg-s" text-anchor="middle">and nothing else</text>

  <!-- arrows -->
  <path d="M176 176 L236 92"   class="dg-line" marker-end="url(#ah)"/>
  <path d="M176 193 L236 188"  class="dg-line" marker-end="url(#ah)"/>
  <path d="M176 210 L236 318"  class="dg-line" marker-end="url(#ah)"/>
  <path d="M432 92  L492 96"   class="dg-line" marker-end="url(#ah)"/>
  <path d="M432 188 L492 110"  class="dg-line dg-dash" marker-end="url(#ah)"/>
  <path d="M652 96  L704 96"   class="dg-line" marker-end="url(#ah)"/>
  <path d="M432 324 L492 324"  class="dg-line" marker-end="url(#ah)"/>
  <path d="M652 324 L704 324"  class="dg-line" marker-end="url(#ah)"/>
  <path d="M572 372 L572 412"  class="dg-line" marker-end="url(#ah)"/>
  <path d="M176 330 L200 330 L200 200 L236 195" class="dg-line dg-dash" marker-end="url(#ah)"/>
  <text x="206" y="150" class="dg-l">reads</text>
</svg>
"""


FORECAST = """
<svg viewBox="0 0 880 330" role="img" aria-labelledby="fcTitle" class="dg">
  <title id="fcTitle">Why a forecast alert fires earlier than an actual-spend alert</title>

  <line x1="70" y1="270" x2="840" y2="270" class="dg-axis"/>
  <line x1="70" y1="40"  x2="70"  y2="270" class="dg-axis"/>
  <text x="70"  y="292" class="dg-s" text-anchor="middle">day 1</text>
  <text x="455" y="292" class="dg-s" text-anchor="middle">day 15</text>
  <text x="840" y="292" class="dg-s" text-anchor="end">day 30</text>
  <text x="26"  y="64"  class="dg-s">$25</text>
  <text x="26"  y="274" class="dg-s">$0</text>

  <!-- budget ceiling -->
  <line x1="70" y1="58" x2="840" y2="58" class="dg-limit"/>
  <text x="840" y="50" class="dg-s dg-hl" text-anchor="end">budget</text>

  <!-- actual spend, climbing steeply -->
  <path d="M70 270 L170 246 L270 210 L370 160 L470 104 L520 76 L560 58"
        class="dg-actual"/>
  <text x="120" y="236" class="dg-s">actual spend</text>

  <!-- projection taken at day 12 -->
  <path d="M310 190 L840 -30" class="dg-proj"/>
  <circle cx="310" cy="190" r="5" class="dg-dot"/>
  <text x="322" y="168" class="dg-s">day 12: already on pace to overshoot</text>

  <!-- markers -->
  <line x1="310" y1="60" x2="310" y2="270" class="dg-mark dg-mark-early"/>
  <text x="316" y="252" class="dg-s dg-ok">FORECAST alert fires here</text>

  <line x1="560" y1="60" x2="560" y2="270" class="dg-mark dg-mark-late"/>
  <text x="566" y="252" class="dg-s dg-bad">ACTUAL 100% fires here</text>

  <path d="M318 226 L552 226" class="dg-gap"/>
  <text x="435" y="218" class="dg-s dg-hl" text-anchor="middle">18 days to react</text>
</svg>
"""


CSS = """
.dg{width:100%;height:auto;margin:14px 0;display:block}
.dg-box{fill:var(--dg-fill);stroke:var(--dg-stroke);stroke-width:1.2}
.dg-src{stroke:var(--dg-accent);stroke-width:1.8}
.dg-key{stroke:var(--dg-accent);stroke-width:1.8;fill:var(--dg-fill-key)}
.dg-out{fill:var(--dg-fill-out)}
.dg-id{stroke:var(--dg-violet);stroke-width:1.6}
.dg-t{fill:var(--dg-ink);font:600 13px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.dg-s{fill:var(--dg-mut);font:11px ui-monospace,SFMono-Regular,Menlo,monospace}
.dg-hl{fill:var(--dg-accent);font-weight:700}
.dg-ok{fill:var(--dg-accent);font-weight:700}
.dg-bad{fill:var(--dg-bad);font-weight:700}
.dg-l{fill:var(--dg-mut);font:10px ui-monospace,monospace}
.dg-line{stroke:var(--dg-stroke2);stroke-width:1.6;fill:none}
.dg-dash{stroke-dasharray:5 4}
.dg-head{fill:var(--dg-stroke2)}
.dg-axis{stroke:var(--dg-stroke);stroke-width:1.2}
.dg-limit{stroke:var(--dg-accent);stroke-width:1.5;stroke-dasharray:6 4}
.dg-actual{stroke:var(--dg-ink);stroke-width:2.4;fill:none}
.dg-proj{stroke:var(--dg-accent);stroke-width:2;stroke-dasharray:7 5;fill:none}
.dg-dot{fill:var(--dg-accent)}
.dg-mark{stroke-width:1.4;stroke-dasharray:3 3}
.dg-mark-early{stroke:var(--dg-accent)}
.dg-mark-late{stroke:var(--dg-bad)}
.dg-gap{stroke:var(--dg-accent);stroke-width:1.2;fill:none}
"""
