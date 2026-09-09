# Portfolio — working notes

Personal cybersecurity portfolio for Kyler Nats, served at https://kylernats.github.io via GitHub Pages.

## Hard constraints

- **No build step, no framework, no dependencies.** Plain HTML/CSS/JS. GitHub Pages serves the repo as-is.
- **No fabricated claims.** Every metric, role, and credential on this site must trace back to the resume
  at `assets/files/KylerNats-Resume.pdf`. Do not invent projects, numbers, or outcomes.
- **Employer work stays unpublished.** Runbooks, playbooks, and controls built at Sunflower Bank or FirstBank
  belong to them. The site describes methodology and rebuilds equivalents independently — it never reproduces
  employer material.
- **Status honesty.** Use the `badge--live` / `badge--building` / `badge--planned` states accurately.
  Planned work is labeled planned.

## Structure

Root-absolute paths throughout (`/assets/...`), so pages work at any depth. Header and footer are duplicated
across pages by design — there is no template engine. When changing nav or footer, change every page.

## The Azure project series

Five builds, each from a real business problem. Two-loop workflow:

1. **Local loop** — Azurite, Azure Functions Core Tools, containerized SQL Server, local OpenAI-compatible
   model endpoint. Free, unlimited iteration.
2. **Real loop** — `terraform apply` on Azure free tier, exercise it, capture evidence (architecture diagram,
   screenshots, logs, cost report, Defender for Cloud findings), then `terraform destroy`.

Order: build 02 → 03 → 04 → 05 first, then 01 last so the cost dashboard reports on the genuine spend
the other four generated.

Note: Azurite does **not** support blob versioning, soft delete, lifecycle policy, or immutability, and there
is no emulator for Cost Management, Azure Monitor, managed identity, RBAC, or Defender for Cloud. Local
emulation is for iteration speed only — the security substance requires the real deploy.

## Local preview

```bash
python3 -m http.server 8000
```
