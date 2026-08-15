# Е.А.Т.О. — storefront

Flask storefront for **Е.А.Т.О.**, a St. Petersburg streetwear brand run by a
graffiti crew. Live at **[еато.store](https://xn--80aj2ap.store)**.

Russian UI. Flask + Excel files as the database. No build step, no framework,
no bundler — clone it and run it.

```
~/eato/
├── README.md      ← you are here (project-level orientation)
├── site/          ← this git repository (the code)
└── photos/        ← 136 MB of raw brand assets, NOT in git
```

## Quick start

```bash
cd ~/eato/site
python3 -m flask run --port 5055 --host 127.0.0.1
# http://127.0.0.1:5055
```

Dependencies (`pip install -r requirements.txt`): Flask 3, pandas, openpyxl,
Werkzeug, gunicorn.

> **Use port 5055, not 5000.** macOS AirPlay Receiver holds 5000 and answers
> `403`, which looks exactly like an application error.

> `flask run` without `--debug` caches templates. Restart after editing any
> `.html` or you will be looking at stale output.

## Where things are

| Path | What |
|---|---|
| `app.py` | Everything — routes, Excel I/O, auth, cart |
| `templates/base.html` | Header, mobile drawer, footer; every page extends it |
| `templates/*.html` | One per page. Several have their own `<style>` block that **overrides** `style.css` |
| `static/css/style.css` | ~2.4k lines. Mobile layout is one marked block at the end |
| `static/js/main.js` | The only script file |
| `*.xlsx` | The database. **Gitignored** — these are local fixtures, not production data |

## Documentation

| Doc | Read it when |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Working with Claude Code here — the rules and traps, in short form |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | You need to understand the routes, the Excel "database", or the server |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | **Before every deploy.** Copy-pasteable runbook |
| [`docs/DEFECTS.md`](docs/DEFECTS.md) | Something looks broken — check whether it is already known |
| [`docs/HISTORY.md`](docs/HISTORY.md) | You want to know why something is the way it is |

## Branches

- **`master`** — v1. **This is what is live.** Work here.
- **`v2`** — an unreleased visual re-skin. Not deployed, not ready.
  **Do not touch it** unless explicitly asked.

## Two things to know before you touch production

1. **Almost every visitor is on a phone, inside an in-app browser** — Telegram,
   TikTok, Instagram. Those webviews block autoplay, throttle media and cache
   aggressively. Testing in desktop Chrome proves very little.

2. **The live `.xlsx` files are real customer data and are not backed up
   anywhere.** They sit in the same folder as the code on the server, so a
   careless `rsync -av .` destroys real accounts and orders. Always deploy an
   enumerated file list — see [`docs/DEPLOY.md`](docs/DEPLOY.md).

## Deploying

```bash
# the short version — full runbook in docs/DEPLOY.md
cd ~/eato/site
git diff --name-only <last-deployed-sha> HEAD    # exactly what to push
```

Deploy is a manual `rsync` over SSH as root. No CI, no pipeline. Rollback is
whatever backup you remembered to take — the runbook takes one for you.
