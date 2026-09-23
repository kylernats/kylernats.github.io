/* Per-step tutor. Attaches a collapsible chat under every .step on the page.
   Accepts a pasted screenshot (Cmd+V), a dragged file, or a file picker. */
(function () {
  'use strict';

  var LAB = location.pathname.split('/').filter(Boolean)[0] || '';

  var CSS = `
  .tut{margin-top:16px;border-top:1px solid var(--line);padding-top:14px}
  .tut-open{display:inline-flex;align-items:center;gap:7px;background:transparent;
    border:1px solid var(--line2);color:var(--mut);border-radius:8px;padding:7px 13px;
    font:500 13px var(--sans);cursor:pointer}
  .tut-open:hover{color:var(--acc);border-color:var(--acc);background:rgba(45,212,191,.07)}
  .tut-open .dot{width:6px;height:6px;border-radius:50%;background:var(--acc)}
  .tut-panel{display:none;margin-top:12px}
  .tut.on .tut-panel{display:block}
  .tut.on .tut-open{color:var(--acc);border-color:var(--acc)}

  .tut-log{display:flex;flex-direction:column;gap:11px;max-height:420px;overflow-y:auto;
    padding:4px 2px 12px}
  .tut-msg{font-size:14.5px;line-height:1.6;max-width:94%}
  .tut-msg.me{align-self:flex-end;background:rgba(45,212,191,.1);border:1px solid rgba(45,212,191,.3);
    border-radius:11px 11px 4px 11px;padding:9px 13px;color:var(--ink)}
  .tut-msg.me img{max-width:220px;border-radius:7px;margin-top:7px;display:block;border:1px solid var(--line2)}
  .tut-msg.bot{align-self:flex-start;color:var(--ink)}
  .tut-msg.bot .who{font:600 10px var(--mono);letter-spacing:.12em;text-transform:uppercase;
    color:var(--acc);margin-bottom:4px}
  .tut-msg.bot p{margin:0 0 8px;color:var(--ink);font-size:14.5px}
  .tut-msg.bot p:last-child{margin:0}
  .tut-msg.bot pre{background:#0A0C0F;border:1px solid var(--line);border-radius:7px;
    padding:10px 12px;overflow-x:auto;font:12.5px/1.55 var(--mono);margin:8px 0}
  .tut-msg.bot code{font-size:12.5px}
  .tut-msg.err{align-self:stretch;border:1px solid rgba(251,113,133,.4);background:rgba(251,113,133,.08);
    border-radius:9px;padding:9px 12px;color:#FB7185;font-size:13.5px}

  .tut-think{align-self:flex-start;display:flex;align-items:center;gap:7px;color:var(--faint);font-size:13px}
  .tut-think i{width:5px;height:5px;border-radius:50%;background:var(--acc);animation:tb 1.2s infinite}
  .tut-think i:nth-child(2){animation-delay:.15s}.tut-think i:nth-child(3){animation-delay:.3s}
  @keyframes tb{0%,60%,100%{opacity:.25}30%{opacity:1}}

  .tut-drop{border:1px dashed var(--line2);border-radius:10px;padding:10px 12px;margin-bottom:9px;
    font-size:13px;color:var(--faint);text-align:center;cursor:pointer}
  .tut-drop:hover,.tut-drop.over{border-color:var(--acc);color:var(--acc);background:rgba(45,212,191,.05)}
  .tut-thumb{position:relative;display:inline-block;margin-bottom:9px}
  .tut-thumb img{max-width:150px;border-radius:8px;border:1px solid var(--line2);display:block}
  .tut-thumb button{position:absolute;top:-7px;right:-7px;width:21px;height:21px;border-radius:50%;
    background:#FB7185;color:#0B0D10;border:none;cursor:pointer;font:700 13px var(--sans);line-height:1}

  .tut-row{display:flex;gap:8px;align-items:flex-end}
  .tut-row textarea{flex:1;background:var(--sub);border:1px solid var(--line);border-radius:9px;
    padding:9px 12px;color:var(--ink);font:14px/1.5 var(--sans);resize:none;min-height:38px;max-height:110px}
  .tut-row textarea:focus{outline:none;border-color:var(--acc)}
  .tut-row button{background:var(--acc);color:#04211D;border:none;border-radius:9px;padding:9px 15px;
    font:600 13px var(--sans);cursor:pointer;flex:none}
  .tut-row button:disabled{opacity:.45;cursor:default}
  .tut-quick{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px}
  .tut-quick button{background:var(--sub);border:1px solid var(--line);color:var(--mut);
    border-radius:99px;padding:5px 11px;font:12.5px var(--sans);cursor:pointer}
  .tut-quick button:hover{color:var(--ink);border-color:var(--acc)}
  `;
  var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function md(t) {
    var fence = String.fromCharCode(96, 96, 96);
    var parts = String(t).split(fence), html = '';
    parts.forEach(function (part, i) {
      if (i % 2 === 1) {
        html += '<pre><code>' + esc(part.replace(/^[\w-]*\n/, '').replace(/\n$/, '')) + '</code></pre>';
        return;
      }
      var x = esc(part)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      x.split('\n').forEach(function (line) {
        if (line.trim()) html += '<p>' + line + '</p>';
      });
    });
    return html;
  }

  function attach(step) {
    var id = step.id || 'step';
    var titleEl = step.querySelector('h2');
    var title = titleEl ? titleEl.textContent : id;

    var wrap = document.createElement('div');
    wrap.className = 'tut';
    wrap.innerHTML =
      '<button class="tut-open"><span class="dot"></span>Ask about this step &middot; send a screenshot</button>' +
      '<div class="tut-panel">' +
        '<div class="tut-log"></div>' +
        '<div class="tut-quick"></div>' +
        '<div class="tut-drop">Paste a screenshot with &#8984;V, drop an image here, or click to choose</div>' +
        '<input type="file" accept="image/*" hidden>' +
        '<div class="tut-row"><textarea rows="1" placeholder="Ask anything, or just send the screenshot&#8230;"></textarea>' +
        '<button class="tut-send">Send</button></div>' +
      '</div>';
    step.appendChild(wrap);

    var openBtn = wrap.querySelector('.tut-open');
    var panel = wrap.querySelector('.tut-panel');
    var log = wrap.querySelector('.tut-log');
    var drop = wrap.querySelector('.tut-drop');
    var file = wrap.querySelector('input[type=file]');
    var ta = wrap.querySelector('textarea');
    var send = wrap.querySelector('.tut-send');
    var quick = wrap.querySelector('.tut-quick');
    var pending = null, busy = false, loaded = false;

    function bubble(role, text, img) {
      var d = document.createElement('div');
      if (role === 'me') {
        d.className = 'tut-msg me';
        d.textContent = text || '(screenshot)';
        if (img) { var i = new Image(); i.src = img; d.appendChild(i); }
      } else if (role === 'err') {
        d.className = 'tut-msg err'; d.textContent = text;
      } else {
        d.className = 'tut-msg bot';
        d.innerHTML = '<div class="who">Claude</div>' + md(text);
      }
      log.appendChild(d); log.scrollTop = log.scrollHeight;
    }

    ['What does this command actually do?', 'Is my output correct?', "I got an error"].forEach(function (q) {
      var b = document.createElement('button');
      b.textContent = q;
      b.onclick = function () { ta.value = q; ask(); };
      quick.appendChild(b);
    });

    function setThumb(dataUrl) {
      pending = dataUrl;
      var old = wrap.querySelector('.tut-thumb');
      if (old) old.remove();
      var t = document.createElement('div');
      t.className = 'tut-thumb';
      var im = new Image(); im.src = dataUrl;
      var x = document.createElement('button'); x.textContent = '×';
      x.onclick = function () { pending = null; t.remove(); drop.style.display = ''; };
      t.appendChild(im); t.appendChild(x);
      drop.style.display = 'none';
      drop.parentNode.insertBefore(t, drop);
    }

    function readFile(f) {
      if (!f || !/^image\//.test(f.type)) return;
      var r = new FileReader();
      r.onload = function () { setThumb(r.result); };
      r.readAsDataURL(f);
    }

    drop.onclick = function () { file.click(); };
    file.onchange = function () { readFile(file.files[0]); };
    drop.addEventListener('dragover', function (e) { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', function () { drop.classList.remove('over'); });
    drop.addEventListener('drop', function (e) {
      e.preventDefault(); drop.classList.remove('over');
      readFile(e.dataTransfer.files[0]);
    });
    ta.addEventListener('paste', function (e) {
      var items = (e.clipboardData || {}).items || [];
      for (var i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') === 0) {
          e.preventDefault();
          readFile(items[i].getAsFile());
          return;
        }
      }
    });

    function ask() {
      var msg = ta.value.trim();
      if ((!msg && !pending) || busy) return;
      busy = true; send.disabled = true;
      bubble('me', msg, pending);
      ta.value = ''; ta.style.height = 'auto';

      var img = pending;
      pending = null;
      var th = wrap.querySelector('.tut-thumb');
      if (th) th.remove();
      drop.style.display = '';

      var think = document.createElement('div');
      think.className = 'tut-think';
      think.innerHTML = '<i></i><i></i><i></i><span>thinking</span>';
      log.appendChild(think); log.scrollTop = log.scrollHeight;
      var t0 = Date.now();
      var tick = setInterval(function () {
        var s = think.querySelector('span');
        if (s) s.textContent = 'thinking ' + Math.round((Date.now() - t0) / 1000) + 's';
      }, 1000);

      var clone = step.cloneNode(true);
      var t = clone.querySelector('.tut'); if (t) t.remove();

      fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lab: LAB, step: id, message: msg, image: img,
                               stepText: (title + '\n\n' + clone.innerText).slice(0, 2500) })
      }).then(function (r) { return r.json(); })
        .then(function (d) {
          clearInterval(tick); think.remove();
          if (d.error) bubble('err', d.error); else bubble('bot', d.reply || '(empty)');
        })
        .catch(function () {
          clearInterval(tick); think.remove();
          bubble('err', 'Could not reach the tutor. Is labs-server.py still running?');
        })
        .then(function () { busy = false; send.disabled = false; ta.focus(); });
    }

    send.onclick = ask;
    ta.onkeydown = function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); return; }
      setTimeout(function () {
        ta.style.height = 'auto';
        ta.style.height = Math.min(110, ta.scrollHeight) + 'px';
      }, 0);
    };

    openBtn.onclick = function () {
      wrap.classList.toggle('on');
      if (wrap.classList.contains('on')) {
        if (!loaded) {
          loaded = true;
          fetch('/api/chat?lab=' + encodeURIComponent(LAB) + '&step=' + encodeURIComponent(id))
            .then(function (r) { return r.json(); })
            .then(function (d) {
              (d.turns || []).forEach(function (t) {
                bubble(t.role === 'user' ? 'me' : 'bot', t.text);
              });
            }).catch(function () {});
        }
        ta.focus();
      }
    };
  }

  function init() {
    var steps = document.querySelectorAll('.step');
    if (!steps.length) { setTimeout(init, 200); return; }
    steps.forEach(attach);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
