# History

Past incidents, and why parts of this codebase look the way they do. Kept
because each one cost real time and the same traps are still reachable.

---

## 2026-08-14 — "the guy in the hoodie"

Some visitors saw a frozen photo of a man in a hoodie instead of the hero
video. It worked fine for Mark every time he checked.

**The hoodie was never a separate element.** It was the `poster` attribute on
the hero `<video>` — the still frame a browser shows until the video paints, and
forever if it never plays. So *every* report of the hoodie was really a report
of "the video did not start."

Four independent causes, in descending order of how much they mattered:

1. **Stale browser cache.** nginx sets `max-age=2592000` on `/static` — 30 days.
   A commit had replaced the video *at the same URL*, so everyone who visited
   before the change stayed pinned to the old broken 8.5 MB file for a month.
   Mark hard-reloaded while testing, so it worked for him. **This is the exact
   signature of "works for me, not for others."**
2. **Autoplay refusal.** `muted playsinline` is necessary but not sufficient.
   iOS Low Power Mode, Android data-saver and in-app webviews all still block
   autoplay, and nothing in the page ever called `.play()` or noticed it failed.
3. **Fragile stacking.** `z-index: -1` on `.hero-background` rendered only
   because no ancestor happened to create a stacking context — one stray
   `transform` or `filter` away from hiding the video entirely.
4. **A stray timecode track** in the MP4, a DaVinci export artifact.

**What came out of it:** `static_url()` mtime cache-busting on every asset,
`poster` removed, an autoplay-recovery script, `z-index: 0` + `isolation:
isolate`, a black hero background so a blocked video degrades to brand black
rather than a stale photo, and the hoodie JPEG deleted outright.

**The lesson that keeps applying:** nothing in the page ever checked whether the
video actually played. Three of the four causes are the same class of bug —
*no one verified the thing they shipped actually did what it was supposed to.*

---

## 2026-08-15 — mobile UI, and a file that had never run

The site was rebuilt for phones. Two findings stand out.

### `main.js` had never executed, in any browser, ever

A duplicated block meant `const style` was declared twice at top level, making
the entire file a `SyntaxError`. `updateCartCount` and `showNotification` were
`undefined` everywhere — including live. It went unnoticed because every
template carries its own inline `<script>`, so the site *looked* fine.

Found by running `node --check` on it, almost incidentally, while adding the
drawer code. See `DEFECTS.md` for what this means going forward.

### There was no mobile navigation at all

Below 968px `.main-nav` was `display: none` with nothing in its place. On a
phone, Каталог / Коллекции / Лукбук were unreachable from every page — on a site
where nearly all traffic arrives from Telegram, TikTok and Instagram in-app
browsers. It had been that way the whole time.

### A measurement trap worth remembering

Headless Chrome with `--window-size=390` does **not** give a 390px layout
viewport on macOS. The window is clamped to a wider minimum and the screenshot
is merely cropped — which produces convincing but completely wrong "the layout
still overflows" images. This sent the session down a false path until the
computed styles were checked directly and disagreed with the screenshots.

**Render the page in a 390px iframe inside a normally-sized window instead.**
That matches what real Chrome computes.

---

## 2026-08-15 — favicon

There was none; `/favicon.ico` returned 404, so tabs and Telegram link previews
showed a blank globe.

The icon is **cropped from `static/images/tech/logo.jpg`** — the crew's actual
marker tag — rather than redrawn, so it keeps the real texture. Two tiers,
because one piece of art cannot serve both ends: the slashed Cyrillic «Е» alone
at 16/32/48 (the full «ЕАТО» turns to mush below ~32px, and the whole tall Е
wastes the square), and the complete tag with its swoosh at 180/192/512.

Two traps found here:

- **Pillow's `save(sizes=[…])` only downscales one source image**, which
  silently flattened three tuned frames into a single 16px one. `favicon.ico`
  is now packed by hand with three PNG frames. Verify with
  `Image.open('static/favicon.ico').info['sizes']` if you regenerate it.
- **nginx has no mime mapping for `.webmanifest`** and served it as
  `application/octet-stream`. It is now served from Flask at `/site.webmanifest`
  with the correct type, which avoided touching the nginx config.

---

## 2026-08-16 — moved out of `~/Downloads`

The repo lived at `~/Downloads/eato-site/eato` — one "clean up Downloads" away
from being gone, with no remote and no backup. Moved to `~/eato/site`, with the
136 MB of raw brand assets alongside at `~/eato/photos`, and pushed to a private
GitHub remote so the code finally exists in more than one place.

**The production `.xlsx` data still has no backup.** See `DEFECTS.md`.
