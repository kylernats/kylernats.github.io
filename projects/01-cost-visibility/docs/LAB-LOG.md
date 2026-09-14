# Lab log — 01 Cost Visibility Dashboard

What I did, in order, including what broke. Written as it happened.

---

## 2026-09-09 — Environment setup

**Azure CLI install.** `brew install azure-cli` — clean, v2.90.0.

**`az login --use-device-code` failed.**

```
AADSTS530035: Access has been blocked by security defaults.
```

Security defaults are on in this tenant and they block device code login.
Microsoft does this on purpose. Device code is a known phishing method, since an
attacker can generate a code and get someone to enter it themselves.

**Fix:** browser login with `az login --tenant <id>`. That flow ties the login to
the browser that started it, so it isn't blocked.

I could have turned security defaults off to make the CLI work. Not worth it on
the subscription holding my billing data.

**Account:** Owner on `Azure subscription 1`. I need that level to create the
subscription-scope role assignment later.

---

## Entries below are added as the build progresses

---

## 2026-09-13 — Step 0: baseline evidence

Three baseline screenshots captured before any resource existed: empty resource
group list, subscription showing Owner and $200 credit, and Cost analysis
reading `BUDGET: NONE` / `FORECAST UNAVAILABLE`.

The last one is the useful one. Those two tiles will read `$25` and show a
forecast once the budget is deployed, so the before and after are in one image.

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

**Takeaway:** if a file shows up in `ls` but every other command says it doesn't
exist, the name I'm using isn't the name on disk. Check the bytes before assuming
it's a permissions problem.
