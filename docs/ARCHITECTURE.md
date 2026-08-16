# Architecture

A single-file Flask app (`app.py`, ~780 lines) with Jinja templates and one
hand-written stylesheet (`static/css/style.css`, ~2.9k lines). No build step, no
framework, no bundler. `static/js/main.js` is the only script file; the rest of
the behaviour is inline `<script>` at the bottom of each template.

## The database is Excel

There is no database. pandas reads and writes `.xlsx` files on every request.

| File | Rows | Columns |
|---|---|---|
| `products.xlsx` | 6 | `id, name, collection, price, description, description_card, sizes, image, sold_out, bestseller` |
| `collections.xlsx` | 1 | `id, name, image, description, product_ids` |
| `users.xlsx` | 2 | `id, name, email, phone, password, email_verified, verification_token, verification_sent_at` |
| `orders.xlsx` | 2 | `order_id, user_id, items, total, processing, production, shipping, created_at` |
| `orders_pending.xlsx` | 0 | same as `orders` |
| `user_carts.xlsx` | 1 | `user_id, cart_data` |
| `orders_temp.xlsx` | 0 | empty, no columns — vestigial |

Row counts are for the **local fixtures**. Production data lives only on the
server and differs.

Passwords are hashed with Werkzeug (`generate_password_hash` /
`check_password_hash`), not stored plainly. Order status is three integer flags
(`processing`, `production`, `shipping`) rather than one state column.

### Email verification

New accounts start with `email_verified=0` and cannot log in
(`/auth`, `action=login`) until they visit `/verify-email/<token>`, which sets
`email_verified=1` and clears `verification_token` so the link can't be reused.
`verification_sent_at` drives both a 24h link expiry and a 60s resend cooldown
(`action=resend_verification` on `/auth`). Mail goes out via
`send_verification_email()` in `app.py` using plain `smtplib` (stdlib, no new
dependency) and `SMTP_HOST`/`SMTP_PORT`/`SMTP_USER`/`SMTP_PASSWORD` from the
environment — same pattern as `SECRET_KEY`. **If `SMTP_USER` is unset the app
does not send anything; it prints the verification link to stdout instead**,
so the flow is testable locally without real credentials. See `DEPLOY.md` for
the required `/etc/eato.env` entries and the one-time production migration of
existing accounts.

`product_ids` on a collection is a comma-separated string (`"1,2,3,4,7,8"`).
**Product IDs are not contiguous** — 5 and 6 are missing — so never assume
`range(1, n)` anywhere.

All `*.xlsx` are gitignored so local fixtures never overwrite production data.
The flip side: the live catalogue, accounts and orders exist **only** on the
server and are **not backed up anywhere**.

### The "Excel is open" mechanism (does not work)

`save_order()` checks `is_file_locked(ORDERS_FILE)`; if the file looks locked it
writes to `orders_pending.xlsx`, and a daemon thread started at import
(`background_sync`) merges pending into `orders.xlsx` every 30 seconds. This
only makes sense if the brand owner opens the spreadsheet directly on the
server — worth confirming with him.

**It never triggers.** `is_file_locked()` tests by opening the file in append
mode, which succeeds on Linux regardless of who else has it open, so it always
returns `False`. It is Windows thinking on an Ubuntu box.

## Routes

```
/                            index         hero, about, pre-order steps, bestsellers,
                                           photo album (paginated 9/page), collections, socials
/catalog                     catalog
/collections                 collections_page
/collection/<int:id>         collection
/lookbook                    lookbook
/product/<int:id>            product
/cart                        cart
/auth            GET POST    auth          login + register + resend_verification, `action` switches
/verify-email/<token>        verify_email  confirms a registration, logs the user in, then redirects to /
/logout                      logout
/checkout        GET POST    checkout      GET renders cart.html; POST takes JSON, writes the order
/order-status/<order_id>     order_status  ⚠️ broken — see DEFECTS.md
/api/cart/add    POST        JSON
/api/cart/remove POST        JSON
/api/cart/update POST        JSON
/favicon.ico                 favicon       nginx only serves /static/, so root requests need this
/site.webmanifest            manifest      nginx has no mime type for .webmanifest
```

Context processors inject globals into every template: `inject_user`
(`current_user` from the session), `inject_static_url` (cache-busting, below)
and one that injects `gallery_images` for the photo album.

## Static assets and cache-busting

nginx serves `/static` directly with `Cache-Control: max-age=2592000` — **30
days**. That bit the project once already (see `HISTORY.md`): replacing a file
at the same URL leaves returning visitors on the old copy for a month.

`app.py` defines `static_url()` and injects it over `url_for` in the template
context, stamping every static asset with its mtime:

```
/static/css/style.css?v=1786799562
/static/videos/hero.mp4?v=1786706111
```

**This only covers assets referenced through `url_for('static', …)`.** Product
and collection images come out of the `image` column in Excel as raw path
strings and are **not** versioned. Changing a product photo in place will not
reach anyone who has already seen it — give it a new filename.

### Image layout

```
static/images/
  albom/                 photo album
  clothes/<product_id>/  1_back.jpg, 2_chest.jpg, N_location.jpg
  collections/           collection cover art
  lookbook/              lookbook1..5.jpg
  tech/                  logo.jpg, favicon-16/32.png, apple-touch-icon.png, icon-192/512.png
static/videos/
  hero.mp4               3.2 MB, H.264 Main/yuv420p 1280×720 25fps, faststart
static/favicon.ico       3 frames (16/32/48), packed by hand
static/site.webmanifest
```

Product photos are **~1 MB each and unoptimised** — `clothes/1/1_back.jpg` alone
is 1,044 KB. Six products × 5–6 photos is a heavy catalogue for phone users on
mobile data. There is real, easy performance work here whenever it matters.

## Front-end conventions

- `base.html` holds header, footer and the two blocks (`content`, `scripts`).
  Every page extends it. It also holds the mobile hamburger, the off-canvas
  drawer (`#mobileNav`) and its backdrop — **below 968px that drawer is the only
  navigation**, because `.main-nav` is `display: none` there.
- **Several templates carry their own `<style>` block.** Those sit *after*
  `style.css` in the document and therefore **override it** at equal
  specificity. If a CSS change appears to do nothing, check the template first.
  `style.css` uses `body .selector` in a few places specifically to outrank them.
- The mobile layout is one marked block at the **end** of `style.css`,
  deliberately last so it wins on cascade without `!important` and can be
  removed whole.
- Scroll animations: elements carry `animate-on-scroll` / `animate-fade-up` /
  `animate-zoom-in` plus `delay-{1..5}`, start at `opacity: 0`, and an
  `IntersectionObserver` adds `.visible`. Each template repeats its own copy of
  the observer. **A screenshot that jumps straight to a section renders it
  blank.**
- Every `<img>` carries an inline `onerror` that hides itself and swaps in a
  `.placeholder-image` div. Convenient — and it means **a broken image path
  fails silently** and looks like a design choice.
- Fonts come from Google Fonts over the network (`Oswald`, `Roboto Mono`), so
  the page has a third-party dependency on the critical path.

## Deploy topology

See `DEPLOY.md` for the runbook. In short: Ubuntu VPS, nginx in front serving
`/static/` directly, gunicorn behind on `127.0.0.1:8000`, systemd unit
`eato.service` running as user `eato`, `/opt/eato` a plain file copy, manual
`rsync` as root.
