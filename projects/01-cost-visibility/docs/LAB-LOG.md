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

---

## 2026-09-13 — Step 0: baseline evidence

Three baseline screenshots captured before any resource existed: empty resource
group list, subscription showing Owner and $200 credit, and Cost analysis
reading `BUDGET: NONE` / `FORECAST UNAVAILABLE`.

The last one is the useful one. Those same two tiles will read `$25` and show a
live forecast once the budget is deployed, so the before/after sits in a single
frame.

### Bug: screenshot filenames would not move

Filing them broke in a way that took three wrong guesses to pin down.

```
mv: rename /Users/arfies123/Desktop/Screenshot 2026-09-13 at 1.29.05 PM.png
    to 00-baseline-empty-rg.png: No such file or directory
```

`ls` listed the file. `stat`, `cp`, and `head` all said it did not exist. The
first theory was macOS TCC protection on `~/Desktop`, since that returns
misleading errors for protected paths. Wrong — running outside the sandbox
failed identically.

Hexdumping the filename gave it away:

```
$ ls ~/Desktop | grep 2026-09-13 | head -1 | xxd
00000010: 3039 2d31 3320 6174 2031 2e32 392e 3035  09-13 at 1.29.05
00000020: e280 af50 4d2e 706e 670a                 ...PM.png
```

`e2 80 af` is U+202F, a narrow no-break space. macOS uses it before AM/PM in
screenshot filenames. A typed path with a regular space (`0x20`) does not match,
so the file genuinely did not exist under the name being used. Globs matched
because the wildcard covered the character, which is exactly why `ls` worked and
everything else failed.

**Fix:** always glob, never type these filenames. `capture.sh` already globbed,
so the script was fine; the manual commands were not.

**Second bug, same batch:** the filing loop indexed a zsh array from 0. zsh
arrays are 1-indexed, so the first file was named `.png` and every other name
shifted by one. Caught it by checking file sizes against the originals rather
than trusting that the move worked.

**Takeaway:** "No such file or directory" for a file you can see listed means
the name you are using is not the name on disk. Check the bytes before blaming
permissions.
