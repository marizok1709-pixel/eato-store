# Known defects

Things that are broken, half-broken, or deliberately left alone. Check here
before investigating something that looks wrong — it may already be known.

---

## Broken

### `/order-status/<order_id>` cannot work

It reads a module-level `ORDERS = {}` dict that nothing ever writes to —
`checkout()` saves orders to `orders.xlsx` instead. Every lookup renders the
"order not found" branch. It also reads keys (`preorder_end`,
`production_start`, `shipping` as datetimes) that do not match the Excel schema
at all, so the route was written against a data model that no longer exists.

**Ask the friend before fixing.** The answer changes whether this is a bug or a
feature that was never finished: either the route is dead code, or customers
have been silently unable to track orders this whole time.

### `is_file_locked()` never returns `True` on Linux

It tests by opening the file in append mode, which POSIX permits even when
another process holds it. So the pending-order fallback path is effectively
dead in production, and the "owner has the spreadsheet open in Excel"
protection does not exist. Harmless today. See `ARCHITECTURE.md`.

### No write locking on the Excel files

`threading` is used only for the 30-second background sync. Concurrent
checkouts do read-modify-write on the same `.xlsx` with nothing guarding them.
At current traffic this is theoretical. **It stops being theoretical if a drop
goes well** — which is exactly when you least want to lose orders.

---

## Risks, not bugs

### There is no backup of production data

The seven `.xlsx` files on the server hold the real catalogue, customer
accounts and orders. They are gitignored (correctly), so they exist **only** on
that VPS. Nothing backs them up. A disk failure loses every account and order.

Pulling a periodic copy down is the single highest-value chore available:

```bash
scp -i ~/.ssh/eato_deploy 'root@82.97.245.77:/opt/eato/*.xlsx' ~/eato/backups/$(date +%F)/
```

### Product photos are unoptimised

~1 MB each, six products × 5–6 photos, served to phone users on mobile data.
Easy, real performance win whenever it matters.

### `app.run(debug=True)` at the bottom of `app.py`

Only affects direct execution; production runs under gunicorn, so this is not
live. **Do not let it become live.**

### `app.secret_key` falls back to a hardcoded literal

`SECRET_KEY` *is* set in `/etc/eato.env` on the server (verified 2026-08-14), so
production does not use the fallback. It remains a footgun for anyone running
this elsewhere.

---

## Fixed — kept here because the failure mode is worth remembering

### `main.js` was a SyntaxError and had never executed — anywhere

Fixed 2026-08-15 (`5ee3667`), deployed the same day.

`const style` was declared twice at top level — an entire block of ~50 lines was
duplicated verbatim — which makes the whole file a `SyntaxError`. So
`updateCartCount` and `showNotification` were `undefined` in every browser,
**including production**. The site only appeared to work because each template
carries its own inline `<script>`.

Two things worth taking from this:

1. It went unnoticed indefinitely because nothing ever checked. `node --check
   static/js/main.js` would have caught it instantly.
2. The fix means `main.js` is now running in production **for the first time
   ever** — add-to-cart from listing pages, cart quantity controls, the checkout
   modal and toast notifications all went from dead to live in one deploy. They
   have never been exercised by real traffic. If something starts behaving
   oddly, look here first.

### Mobile navigation did not exist

Fixed 2026-08-15 (`5ee3667`). Below 968px `.main-nav` was `display: none` with
nothing replacing it, so on a phone Каталог, Коллекции and Лукбук were
unreachable from every page — on a site whose traffic is almost entirely
phones. Replaced with a hamburger and an off-canvas drawer.

### Product page was clipped on phones

Fixed 2026-08-15. `grid-template-columns: 1fr` resolves its auto minimum to
`min-content`, which was 449px inside a 340px container — so the size picker and
the buy button sat off-screen. `minmax(0, 1fr)` fixes it. Worth knowing
generally: **a bare `1fr` can be wider than its container.**

---

## Not the problem — do not re-investigate

Checked against the live site on 2026-08-14 with `curl`, regarding the hero
video (see `HISTORY.md`):

- nginx serves `Content-Type: video/mp4` correctly.
- `Accept-Ranges: bytes` is present and a range request returns `206` with a
  correct `Content-Range`. **Safari's byte-range requirement is satisfied** —
  the usual suspect for "plays in Chrome but not Safari", and not the cause.
- The encoding is fine: H.264 Main, level 4.0, `yuv420p`, 1280×720, 25 fps,
  ~0.9 Mbit/s, `moov` before `mdat` (faststart), so it streams.
