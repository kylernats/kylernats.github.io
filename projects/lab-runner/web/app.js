/* Lab runner UI. State lives on disk via /api/state so the notes can be read
   back later and turned into the case study. */
(function () {
  'use strict';

  const LAB = new URLSearchParams(location.search).get('id') || '01-cost-visibility';
  const $ = (s, r) => (r || document).querySelector(s);
  const el = (t, c, h) => { const n = document.createElement(t); if (c) n.className = c; if (h != null) n.innerHTML = h; return n; };
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  let lab = null;
  let state = { checked: [], hints: {}, notes: {} };
  let evidence = { screenshots: [] };
  let saveTimer = null;

  /* ---------------------------------------------------------------- utils -- */
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._t);
    t._t = setTimeout(() => t.classList.remove('show'), 2200);
  }

  async function api(path, opts) {
    const sep = path.includes('?') ? '&' : '?';
    const r = await fetch(`${path}${sep}id=${encodeURIComponent(LAB)}`, opts);
    return r.json();
  }

  function saveState() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      await api('/api/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state)
      });
    }, 500);
  }

  /* --------------------------------------------------------------- render -- */
  function cmdBox(cmd) {
    const box = el('div', 'cmd', esc(cmd));
    const b = el('button', 'copy', 'Copy');
    b.onclick = () => {
      navigator.clipboard.writeText(cmd).then(() => {
        b.textContent = 'Copied'; b.classList.add('done');
        setTimeout(() => { b.textContent = 'Copy'; b.classList.remove('done'); }, 1400);
      });
    };
    box.appendChild(b);
    return box;
  }

  function renderStep(step) {
    const done = state.checked.includes(step.id);
    const wrap = el('div', 'step' + (done ? ' done' : ''));
    wrap.id = 'step-' + step.id;

    // header + checkbox
    const head = el('div', 'step-head');
    const chk = el('input', 'chk');
    chk.type = 'checkbox';
    chk.checked = done;
    chk.onchange = () => {
      if (chk.checked) { if (!state.checked.includes(step.id)) state.checked.push(step.id); }
      else state.checked = state.checked.filter(x => x !== step.id);
      wrap.classList.toggle('done', chk.checked);
      saveState(); refreshProgress(); buildToc();
    };
    head.appendChild(chk);
    const titleWrap = el('div', '', `<div class="step-id">${esc(step.id)}</div><h3>${esc(step.title)}</h3>`);
    titleWrap.style.flex = '1';
    head.appendChild(titleWrap);
    wrap.appendChild(head);

    if (step.where) {
      wrap.appendChild(el('div', 'where',
        `<span class="k">Write it in</span> <code>${esc(step.where.file)}</code>` +
        `<span class="k">replacing</span> <code>${esc(step.where.marker)}</code>`));
    }

    if (step.what) wrap.appendChild(el('div', 'block', `<div class="label">What it is</div><p>${step.what}</p>`));
    if (step.real) wrap.appendChild(el('div', 'block real', `<div class="label">Real life</div><p>${step.real}</p>`));
    if (step.why) wrap.appendChild(el('div', 'block why', `<div class="label">Why it matters</div><p>${step.why}</p>`));

    if (step.props && step.props.length) {
      const b = el('div', 'block', `<div class="label">Write a <code>${esc(step.resource || '')}</code> with</div>`);
      const ul = el('ul', 'props');
      step.props.forEach(p => ul.appendChild(el('li', '', p)));
      b.appendChild(ul);
      wrap.appendChild(b);
    }

    (step.commands || []).forEach(c => {
      const b = el('div', 'block');
      if (c.label) b.appendChild(el('div', 'label', esc(c.label)));
      b.appendChild(cmdBox(c.cmd));
      wrap.appendChild(b);
    });

    if (step.table) {
      const w = el('div', 'tbl-wrap');
      let h = '<table><thead><tr>' + step.table.head.map(x => `<th>${esc(x)}</th>`).join('') + '</tr></thead><tbody>';
      step.table.rows.forEach(r => { h += '<tr>' + r.map(x => `<td>${x}</td>`).join('') + '</tr>'; });
      w.innerHTML = h + '</tbody></table>';
      wrap.appendChild(w);
    }

    if (step.callout) wrap.appendChild(el('div', 'callout', step.callout));

    // screenshot callouts, with live capture status
    (step.shots || []).forEach(s => {
      const have = evidence.screenshots.some(f => f.includes(s.slug));
      const box = el('div', 'shot');
      box.innerHTML =
        `<div class="label">📸 Screenshot <span class="status ${have ? 'have' : ''}">${have ? 'captured' : 'not yet'}</span></div>
         <h4>${esc(s.slug)}</h4><p>${s.desc}</p>`;
      box.appendChild(cmdBox(`./scripts/capture.sh ${s.slug} "${s.caption}"`));
      wrap.appendChild(box);
    });

    // three-tier hints
    if (step.hints && step.hints.length) {
      const h = el('div', 'hints');
      step.hints.forEach((hint, i) => {
        const lvl = i + 1;
        const d = el('details', 'hint');
        const badge = step.hintStyle === 'faq'
          ? '<span class="lvl lvlq">?</span>'
          : `<span class="lvl lvl${lvl}">LEVEL ${lvl}</span>`;
        const sum = el('summary', '', `${badge} ${esc(hint.label)}`);
        d.appendChild(sum);
        const body = el('div', 'body');
        if (hint.text) body.appendChild(el('p', '', hint.text));
        if (hint.code) body.appendChild(el('pre', '', `<code>${esc(hint.code)}</code>`));
        d.appendChild(body);
        d.ontoggle = () => {
          if (!d.open || step.hintStyle === 'faq') return;
          const cur = state.hints[step.id] || 0;
          if (lvl > cur) { state.hints[step.id] = lvl; saveState(); }
          if (lvl === 3) toast('Level 3 used — noted, so the write-up stays honest');
        };
        if ((state.hints[step.id] || 0) >= lvl) d.open = false;
        h.appendChild(d);
      });
      wrap.appendChild(h);
    }

    // notes → these become the case study
    if (step.notes !== false) {
      const n = el('div', 'notes');
      n.innerHTML = `<div class="label" style="font:500 10.5px var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin-bottom:6px">Your notes — what happened, what broke</div>`;
      const ta = el('textarea');
      ta.placeholder = 'In your own words. Errors, surprises, what you had to look up…';
      ta.value = state.notes[step.id] || '';
      const line = el('div', 'hintline', `<span>Saved to the repo. This becomes the write-up.</span><span id="sv-${step.id}"></span>`);
      ta.oninput = () => {
        state.notes[step.id] = ta.value;
        saveState();
        const s = $('#sv-' + step.id);
        if (s) { s.textContent = 'saved'; s.className = 'saved'; setTimeout(() => s.textContent = '', 1400); }
      };
      n.appendChild(ta); n.appendChild(line);
      wrap.appendChild(n);
    }

    return wrap;
  }

  function render() {
    const c = $('#content');
    c.innerHTML = '';
    c.appendChild(el('div', '', `
      <div class="eyebrow">${esc(lab.eyebrow || 'Lab')}</div>
      <h1>${esc(lab.title)}</h1>
      <p class="lede">${lab.subtitle || ''}</p>`));

    if (lab.intro) c.appendChild(el('div', 'callout', lab.intro));

    lab.phases.forEach(ph => {
      const sec = el('section', 'phase');
      sec.id = 'phase-' + ph.id;
      sec.appendChild(el('div', 'phase-head', `<span class="n">${esc(ph.id)}</span><h2>${esc(ph.title)}</h2>`));
      if (ph.blurb) sec.appendChild(el('p', '', ph.blurb));
      ph.steps.forEach(s => sec.appendChild(renderStep(s)));
      c.appendChild(sec);
    });

    buildToc();
    refreshProgress();
  }

  function allSteps() { return lab.phases.flatMap(p => p.steps); }

  function buildToc() {
    const toc = $('#toc');
    toc.innerHTML = '';
    lab.phases.forEach(ph => {
      toc.appendChild(el('div', 'ph', esc(ph.title)));
      ph.steps.forEach(s => {
        const done = state.checked.includes(s.id);
        const a = el('a', done ? 'done' : '', `<span class="tick">${done ? '✓' : '○'}</span><span>${esc(s.title)}</span>`);
        a.href = '#step-' + s.id;
        toc.appendChild(a);
      });
    });
  }

  function refreshProgress() {
    const steps = allSteps();
    const done = steps.filter(s => state.checked.includes(s.id)).length;
    const pct = steps.length ? Math.round(done / steps.length * 100) : 0;
    $('#pct').textContent = pct + '%';
    $('#pcount').textContent = `${done} / ${steps.length} steps`;
    $('#pfill').style.width = pct + '%';
  }

  /* ---------------------------------------------------------- live panels -- */
  async function pollAzure() {
    const p = $('#azPanel');
    try {
      const d = await api('/api/azure');
      if (!d.logged_in) {
        p.innerHTML = `<div class="stat"><span><span class="dot off"></span> not signed in</span></div>
                       <div style="font-size:12px;color:var(--faint);margin-top:6px">Run <code>az login</code></div>`;
        return;
      }
      const used = d.spend || 0, pctUsed = Math.min(100, used / d.credit * 100);
      p.innerHTML =
        `<div class="stat"><span><span class="dot ok"></span> ${esc(d.subscription || '')}</span></div>
         <div class="stat"><span>Resources</span><b>${d.resource_count}</b></div>
         <div class="stat"><span>Budgets</span><b>${(d.budgets || []).length}</b></div>
         <div class="meter ${pctUsed > 50 ? 'hot' : ''}"><i style="width:${pctUsed}%"></i></div>
         <div class="stat"><span>Spent</span><b>$${used.toFixed(2)} / $${d.credit}</b></div>`;
    } catch (e) {
      p.innerHTML = `<div class="stat"><span style="color:var(--faint)">unavailable</span></div>`;
    }
  }

  async function pollTerraform() {
    const p = $('#tfPanel');
    try {
      const d = await api('/api/terraform');
      if (!d.available) { p.innerHTML = '<div class="stat"><span style="color:var(--faint)">no check script</span></div>'; return; }
      const ok = d.remaining === 0;
      let h = `<div class="stat"><span><span class="dot ${ok ? 'ok' : 'warn'}"></span> ${d.remaining == null ? '?' : d.remaining} TODO left</span></div>
               <div class="stat"><span>Validates</span><b style="color:${d.valid ? 'var(--accent)' : 'var(--amber)'}">${d.valid ? 'yes' : 'no'}</b></div>`;
      if (d.todos && d.todos.length) {
        h += `<div style="font:11px var(--mono);color:var(--faint);margin-top:8px;line-height:1.7">` +
             d.todos.slice(0, 6).map(t => `${esc(t.task)} · ${esc(t.file)}:${t.line}`).join('<br>') + `</div>`;
      }
      p.innerHTML = h;
    } catch (e) {
      p.innerHTML = '<div class="stat"><span style="color:var(--faint)">unavailable</span></div>';
    }
  }

  async function pollEvidence() {
    const p = $('#evPanel');
    try {
      evidence = await api('/api/evidence');
      const shots = allShots();
      const have = shots.filter(s => evidence.screenshots.some(f => f.includes(s.slug))).length;
      p.innerHTML =
        `<div class="stat"><span>Screenshots</span><b>${have} / ${shots.length}</b></div>
         <div class="meter"><i style="width:${shots.length ? have / shots.length * 100 : 0}%"></i></div>
         <div class="stat"><span>Snapshots</span><b>${(evidence.snapshots || []).length}</b></div>`;
      document.querySelectorAll('.shot').forEach(() => {});
    } catch (e) { p.innerHTML = '<div class="stat"><span style="color:var(--faint)">unavailable</span></div>'; }
  }

  function allShots() { return lab ? allSteps().flatMap(s => s.shots || []) : []; }

  /* ---------------------------------------------------------------- export -- */
  function exportNotes() {
    let md = `# ${lab.title} — lab notes\n\n_Exported ${new Date().toISOString().slice(0, 16).replace('T', ' ')}_\n\n`;
    lab.phases.forEach(ph => {
      const withNotes = ph.steps.filter(s => (state.notes[s.id] || '').trim());
      if (!withNotes.length) return;
      md += `## ${ph.title}\n\n`;
      withNotes.forEach(s => {
        const lvl = state.hints[s.id];
        md += `### ${s.id} — ${s.title}\n\n${state.notes[s.id].trim()}\n\n`;
        if (lvl) md += `_(hint level ${lvl} used)_\n\n`;
      });
    });
    navigator.clipboard.writeText(md).then(() => toast('Markdown copied to clipboard'));
  }

  /* ------------------------------------------------------------------ init -- */
  (async function init() {
    [lab, state] = await Promise.all([api('/api/lab'), api('/api/state')]);
    state.checked = state.checked || []; state.hints = state.hints || {}; state.notes = state.notes || {};
    if (lab.error) { $('#content').innerHTML = `<h1>Lab not found</h1><p>${esc(lab.error)}</p>`; return; }

    evidence = await api('/api/evidence');
    render();
    pollAzure(); pollTerraform(); pollEvidence();

    setInterval(pollAzure, 60000);
    setInterval(pollEvidence, 15000);

    $('#tfRefresh').onclick = async e => {
      e.target.textContent = 'Running…';
      await pollTerraform();
      e.target.textContent = 'Re-run check';
      toast('Terraform check refreshed');
    };
    $('#exportBtn').onclick = exportNotes;

    $('#viewGuide').href = '/guide?id=' + encodeURIComponent(LAB);

    $('#guideBtn').onclick = async e => {
      const b = e.target, label = b.textContent;
      b.textContent = 'Building guide…'; b.disabled = true;
      try {
        const d = await api('/api/report?kind=guide');
        if (d.error) toast(d.error);
        else toast(`Saved ${d.rel} (${d.size_kb} KB)`);
      } catch (err) { toast('Guide build failed'); }
      b.textContent = label; b.disabled = false;
    };

    $('#pdfBtn').onclick = async e => {
      const b = e.target, label = b.textContent;
      b.textContent = 'Building PDF…'; b.disabled = true;
      try {
        const d = await api('/api/report');
        if (d.error) toast(d.error);
        else toast(`Saved ${d.rel} (${d.size_kb} KB)`);
      } catch (err) { toast('PDF build failed'); }
      b.textContent = label; b.disabled = false;
    };

    // Highlight the section you're reading
    const obs = new IntersectionObserver(es => {
      es.forEach(en => {
        if (!en.isIntersecting) return;
        document.querySelectorAll('#toc a').forEach(a => a.classList.remove('active'));
        const a = document.querySelector(`#toc a[href="#${en.target.id}"]`);
        if (a) a.classList.add('active');
      });
    }, { rootMargin: '-10% 0px -80% 0px' });
    document.querySelectorAll('.step').forEach(s => obs.observe(s));
  })();
})();
