/* Lab tutor dock.
   Talks to /api/chat, which shells out to the local `claude` CLI in print mode
   with read-only tools. No API key: it rides the existing Claude Code plan. */
(function () {
  'use strict';

  var LAB = new URLSearchParams(location.search).get('id') || '01-cost-visibility';
  var $ = function (s) { return document.querySelector(s); };

  var fab = $('#chatFab'), dock = $('#chatDock'), body = $('#chatBody'),
      input = $('#chatInput'), send = $('#chatSend'), scopeEl = $('#chatScope'),
      quick = $('#chatQuick');
  if (!fab) return;

  var step = 'general', stepTitle = '', busy = false;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  // Prose segments and fenced code alternate when splitting on a triple backtick,
  // so no placeholder characters are needed.
  function md(text) {
    var fence = String.fromCharCode(96, 96, 96);
    var parts = String(text).split(fence);
    var html = '';

    parts.forEach(function (part, i) {
      if (i % 2 === 1) {
        html += '<pre><code>' + esc(part.replace(/^[\w-]*\n/, '').replace(/\n$/, '')) + '</code></pre>';
        return;
      }
      var t = esc(part)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

      var out = [], list = null;
      t.split('\n').forEach(function (line) {
        var m = line.match(/^\s*[-*]\s+(.*)/);
        if (m) { if (!list) list = []; list.push(m[1]); return; }
        if (list) { out.push('<ul><li>' + list.join('</li><li>') + '</li></ul>'); list = null; }
        if (line.trim()) out.push('<p>' + line + '</p>');
      });
      if (list) out.push('<ul><li>' + list.join('</li><li>') + '</li></ul>');
      html += out.join('');
    });
    return html;
  }

  function bubble(role, text) {
    var d = document.createElement('div');
    if (role === 'user') { d.className = 'msg user'; d.textContent = text; }
    else if (role === 'error') { d.className = 'msg err'; d.textContent = text; }
    else { d.className = 'msg bot'; d.innerHTML = '<div class="who">Claude</div>' + md(text); }
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
  }

  function setQuick() {
    var opts = step === 'general'
      ? ['What should I do next?', 'Explain this lab in a paragraph']
      : ['What is this actually doing?', 'I am stuck, nudge me',
         'Check my code for this step', 'Why does this matter for security?'];
    quick.innerHTML = '';
    opts.forEach(function (o) {
      var b = document.createElement('button');
      b.textContent = o;
      b.onclick = function () { input.value = o; ask(); };
      quick.appendChild(b);
    });
  }

  function loadThread() {
    body.innerHTML = '';
    fetch('/api/chat?id=' + encodeURIComponent(LAB) + '&step=' + encodeURIComponent(step))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var turns = d.turns || [];
        turns.forEach(function (t) { bubble(t.role === 'user' ? 'user' : 'bot', t.text); });
        if (!turns.length) {
          bubble('bot', step === 'general'
            ? 'Ask me anything about the lab. I can read your Terraform files, so "check my code" works.\n\nI will nudge rather than hand over answers. Say **just show me** if you want the code.'
            : 'Asking about **' + (stepTitle || step) + '**.\n\nI can read your files, so paste an error or ask me to check your work.');
        }
        setQuick();
      })
      .catch(function () { bubble('error', 'Could not load the thread.'); setQuick(); });
  }

  // Send the on-screen step text so the tutor knows exactly what he is looking at.
  function stepContext() {
    var node = document.getElementById('step-' + step);
    if (!node) return '';
    return 'Step content on screen:\n\n' + node.innerText.replace(/\s+\n/g, '\n').slice(0, 2500);
  }

  function ask() {
    var msg = input.value.trim();
    if (!msg || busy) return;
    busy = true; send.disabled = true; input.value = '';
    input.style.height = 'auto';
    bubble('user', msg);

    var t = document.createElement('div');
    t.className = 'typing';
    t.innerHTML = '<i></i><i></i><i></i><span style="margin-left:4px">thinking</span>';
    body.appendChild(t);
    body.scrollTop = body.scrollHeight;

    var t0 = Date.now();
    var tick = setInterval(function () {
      var s = t.querySelector('span');
      if (s) s.textContent = 'thinking ' + Math.round((Date.now() - t0) / 1000) + 's';
    }, 1000);

    fetch('/api/chat?id=' + encodeURIComponent(LAB), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: step, message: msg, context: stepContext() })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        clearInterval(tick); t.remove();
        if (d.error) bubble('error', d.error);
        else bubble('bot', d.reply || '(empty reply)');
      })
      .catch(function () {
        clearInterval(tick); t.remove();
        bubble('error', 'Request failed. Is the server still running?');
      })
      .then(function () {
        busy = false; send.disabled = false; input.focus();
      });
  }

  function open(nextStep, title) {
    if (nextStep && nextStep !== step) { step = nextStep; stepTitle = title || ''; }
    scopeEl.textContent = step === 'general' ? 'general' : step + ' · ' + stepTitle;
    dock.classList.add('open');
    fab.classList.add('hidden');
    loadThread();
    input.focus();
  }

  fab.onclick = function () { open(window.__currentStep, window.__currentStepTitle); };
  $('#chatClose').onclick = function () {
    dock.classList.remove('open');
    fab.classList.remove('hidden');
  };
  $('#chatClear').onclick = function () {
    fetch('/api/chat?id=' + encodeURIComponent(LAB) + '&step=' + encodeURIComponent(step), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: step, reset: true })
    }).then(function () { loadThread(); });
  };
  send.onclick = ask;

  input.onkeydown = function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); return; }
    setTimeout(function () {
      input.style.height = 'auto';
      input.style.height = Math.min(120, input.scrollHeight) + 'px';
    }, 0);
  };

  // Deep link: ?chat=1.4 opens that step's thread on load.
  var deep = new URLSearchParams(location.search).get('chat');

  // Attach per-step buttons once the lab content has rendered.
  var wire = setInterval(function () {
    var steps = document.querySelectorAll('.step');
    if (!steps.length) return;
    clearInterval(wire);

    steps.forEach(function (s) {
      var id = s.id.replace('step-', '');
      var h3 = s.querySelector('h3');
      var title = h3 ? h3.textContent : '';
      var b = document.createElement('button');
      b.className = 'ask-btn';
      b.textContent = 'Ask about this step';
      b.onclick = function () { open(id, title); };
      s.appendChild(b);
    });

    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (!en.isIntersecting) return;
        var h3 = en.target.querySelector('h3');
        window.__currentStep = en.target.id.replace('step-', '');
        window.__currentStepTitle = h3 ? h3.textContent : '';
      });
    }, { rootMargin: '-20% 0px -60% 0px' });
    steps.forEach(function (s) { io.observe(s); });

    if (deep) {
      var node = document.getElementById('step-' + deep);
      var h = node && node.querySelector('h3');
      open(deep, h ? h.textContent : '');
    }
  }, 300);
})();
