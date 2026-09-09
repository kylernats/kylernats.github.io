/* Kyler Nats — portfolio behavior.
   Progressive enhancement only: every page is fully readable with JS disabled. */
(function () {
  'use strict';

  /* --- Mobile nav ------------------------------------------------------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('primary-nav');

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.getAttribute('data-open') === 'true';
      nav.setAttribute('data-open', String(!open));
      toggle.setAttribute('aria-expanded', String(!open));
    });

    // Close when a link is chosen or focus leaves the menu.
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        nav.setAttribute('data-open', 'false');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.getAttribute('data-open') === 'true') {
        nav.setAttribute('data-open', 'false');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.focus();
      }
    });
  }

  /* --- Mark the current section in the nav ------------------------------ */
  // Compares the first path segment so /work/cloud-security/ still lights "Work".
  var segment = window.location.pathname.split('/').filter(Boolean)[0] || '';
  document.querySelectorAll('#primary-nav a[data-section]').forEach(function (link) {
    if (link.getAttribute('data-section') === segment) {
      link.setAttribute('aria-current', 'page');
    }
  });

  /* --- Work filters ----------------------------------------------------- */
  // Cards carry data-domain and data-type; buttons carry data-filter="key:value".
  var filterBar = document.querySelector('[data-filter-bar]');

  if (filterBar) {
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-filter-item]'));
    var empty = document.querySelector('[data-filter-empty]');
    var countEl = document.querySelector('[data-filter-count]');
    var active = { domain: 'all', type: 'all' };

    function apply() {
      var shown = 0;

      items.forEach(function (item) {
        var okDomain = active.domain === 'all' || item.dataset.domain === active.domain;
        var okType = active.type === 'all' || item.dataset.type === active.type;
        var visible = okDomain && okType;
        item.hidden = !visible;
        if (visible) shown++;
      });

      if (empty) empty.hidden = shown !== 0;
      if (countEl) countEl.textContent = shown + (shown === 1 ? ' item' : ' items');
    }

    filterBar.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-filter]');
      if (!btn) return;

      var parts = btn.dataset.filter.split(':');
      var group = parts[0];
      var value = parts[1];
      active[group] = value;

      // Only one button per group stays pressed.
      filterBar.querySelectorAll('[data-filter^="' + group + ':"]').forEach(function (b) {
        b.setAttribute('aria-pressed', String(b === btn));
      });

      apply();
    });

    apply();
  }

  /* --- Reveal on scroll ------------------------------------------------- */
  var reveals = document.querySelectorAll('.reveal');

  if (reveals.length) {
    if (!('IntersectionObserver' in window) ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      reveals.forEach(function (el) { el.classList.add('is-visible'); });
    } else {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });

      reveals.forEach(function (el) { io.observe(el); });
    }
  }

  /* --- Footer year ------------------------------------------------------ */
  var year = document.querySelector('[data-year]');
  if (year) year.textContent = new Date().getFullYear();
})();
