# Lab log — 01 Cost Visibility Dashboard

Running record of what was done, in order, including what broke. Kyler runs the
commands; entries get written up as the work happens rather than reconstructed
afterward.

Format: what was attempted, what happened, what fixed it.

---

## 2026-09-09 — Environment setup

**Azure CLI install.** `brew install azure-cli` — clean, v2.90.0.

**`az login --use-device-code` failed.**

```
AADSTS530035: Access has been blocked by security defaults.
```

The tenant has Entra ID security defaults enabled, which block the device code
flow. That is deliberate on Microsoft's part: device code is a known phishing
vector, because an attacker can generate a code and talk a target into entering
it on their own machine.

**Fix:** browser-based `az login --tenant <id>`. The auth code flow ties the
session to the browser that started it, so security defaults allow it.

Worth noting the temptation here was to disable security defaults to make the
tooling work. That would have traded a real protection for convenience on a
subscription that holds billing data.

**Account confirmed:** Owner on `Azure subscription 1`, which is the level
needed to create the subscription-scope role assignment later.

---

## Entries below are added as the build progresses
