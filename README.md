# kylernats.github.io

Personal website showing what I am learning and working on — a cybersecurity portfolio — cloud security, detection engineering, AI security, GRC, offensive security, and network analysis.

**Live:** https://kylernats.github.io

## How it's built

Plain HTML, one CSS file, one JS file. No framework, no build step, no dependencies.
GitHub Pages serves the files exactly as they sit in this repo — push to `main` and it's live.

```
index.html              Home
work/index.html         All work, filterable by domain and type
work/<domain>/          One page per security domain
writing/                Write-ups
about/                  Background
resume/                 Full resume + PDF download
assets/css/style.css    Entire design system
assets/js/main.js       Nav, filters, scroll reveal
assets/img/             Images
assets/files/           Resume PDF
```

## Local preview

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

A server is required (not `file://`) so that root-absolute paths like `/assets/css/style.css` resolve.

## Adding a project

1. Copy an existing `<article class="card">` block into the relevant domain page.
2. Add a matching card to `work/index.html` with `data-filter-item`, `data-domain`, and `data-type`
   so the filters pick it up.
3. Add the URL to `sitemap.xml`.

## Design tokens

All colors, type, and spacing are CSS custom properties at the top of `assets/css/style.css`.
Change a token there and it propagates across every page.
