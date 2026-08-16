# CLAUDE.md — Е.А.Т.О. storefront

Guidance for Claude Code working in this repo. Read this before changing anything.

## What this is

A Flask storefront for **Е.А.Т.О.**, a St. Petersburg streetwear brand run by a
graffiti crew. Live at **еато.store** (punycode `xn--80aj2ap.store`). Mark is
the developer and now the maintainer; his friend owns the brand and the
business decisions.

Entirely Russian UI. No build step, no framework, no bundler.

| | |
|---|---|
| Stack | Flask 3 + pandas + openpyxl, Jinja templates, one hand-written CSS file |
| Data | **Excel files**, not a database |
| Server | Ubuntu VPS `82.97.245.77`, nginx in front, gunicorn behind |
| Deploy | manual `rsync` over SSH. No CI |
| Branches | `master` = v1 = **what is live**. `v2` = unreleased re-skin |

## The five rules

1. **Work on `master`. Do not touch `v2`.** `v2` is an unreleased visual
   re-skin and is not ready. Standing instruction from Mark.
2. **Never `rsync` the whole directory to the server.** The live `.xlsx` files
   sit in the same folder as the code and differ from the local copies —
   server `users.xlsx` is real customer accounts. Always deploy an enumerated
   file list. See `docs/DEPLOY.md`.
3. **Almost all traffic is phones in in-app browsers** (Telegram, TikTok,
   Instagram). "Works on my machine" in desktop Chrome proves very little.
   Check narrow viewports before claiming a UI change works.
4. **`*.xlsx` is gitignored on purpose** so local fixtures never overwrite
   production data. Do not commit them, do not "fix" the gitignore.
5. **Port 5000 is unusable on this Mac** — macOS AirPlay Receiver holds it and
   answers `403`, which looks exactly like an app error. Use `5055`.

## Running it locally

```bash
cd ~/eato/site
python3 -m flask run --port 5055 --host 127.0.0.1
```

Dependencies are installed system-wide (Flask, pandas, openpyxl, Werkzeug).
There is no venv in the repo. The `.xlsx` files in the working tree are local
fixtures, not production data.

Note `flask run` without `--debug` **caches templates** — restart after editing
any `.html`, or you will be looking at stale output and think your change
failed.

Registration requires clicking an emailed verification link before login
works. Locally, without `SMTP_USER` set, no email is sent — the link is
printed to the console instead, so the flow is testable without real
credentials. See `docs/ARCHITECTURE.md`.

## Testing a UI change at phone width

Do not trust `--window-size=390` with headless Chrome on macOS: the window is
clamped to a wider minimum and the screenshot is merely cropped, so you get
convincing but wrong "it still overflows" images. This cost a whole debugging
detour once.

Render the page in a **390px iframe inside a normally-sized window** instead —
that matches what real Chrome computes. A same-origin harness page under
`static/` works well (delete it afterwards; do not commit it).

## Layout of the code

- `app.py` — everything: routes, Excel I/O, auth, cart. ~770 lines.
- `templates/base.html` — header, mobile drawer, footer. Every page extends it.
- `templates/*.html` — one per page. **Several carry their own `<style>` block**,
  which sits *after* `style.css` in the document and therefore **overrides it**.
  If a CSS change seems to have no effect, check the template's own block first.
- `static/css/style.css` — ~2.4k lines. The mobile layout is one clearly marked
  block at the **end** of the file, deliberately last so it wins on cascade
  without `!important` and can be deleted whole.
- `static/js/main.js` — the only script file; the rest is inline `<script>` at
  the bottom of each template.

## Conventions worth matching

- Comments in this codebase are in Russian. Match that when editing Russian
  sections; the newer explanatory comments say *why*, not *what*.
- Scroll animations: elements carry `animate-on-scroll` + `delay-{1..5}`, start
  at `opacity: 0`, and an `IntersectionObserver` adds `.visible`. **This means a
  screenshot that jumps straight to a section renders it blank** — scroll to it
  in steps, or force the class, or you will think the page is broken.
- Every `<img>` has an inline `onerror` that hides it and swaps in a
  placeholder. A broken image path therefore **fails silently** and looks like
  a design choice.
- Product IDs are **not contiguous** (5 and 6 are missing). Never assume
  `range(1, n)`.

## Before you say a change works

This project has a history of changes that were "done" but never actually
observed working — see the hero video in `docs/HISTORY.md`, and `main.js`,
which was a syntax error and had never executed in production at all. So:

- Verify against the running app, not just the diff.
- After deploying, verify against **the live site**, not the server filesystem.
- If you cannot observe it, say so plainly rather than implying it works.

## Deploying

Full runbook with the exact commands: **`docs/DEPLOY.md`**. Summary of the
non-negotiable parts: check the server matches the last deployed commit, back
up what you are about to overwrite, push an enumerated file list, `chown` to
`eato:eato`, restart, then verify the live site and confirm the `.xlsx`
timestamps did not change.

Deploy only when asked. Do not deploy as a side effect of a code change.

## Documentation

- `README.md` — orientation, setup, project map.
- `docs/ARCHITECTURE.md` — routes, the Excel "database", deploy topology.
- `docs/DEPLOY.md` — the runbook.
- `docs/DEFECTS.md` — known broken things, and what is deliberately left alone.
- `docs/HISTORY.md` — past incidents worth not repeating.

Keep these updated when you change the things they describe.
