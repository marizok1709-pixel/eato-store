# Deploy runbook

Manual `rsync` over SSH. No CI, no pipeline, no git on the server.
`/opt/eato` is a **plain file copy, not a checkout**, so deploying means
copying files over the top and restarting the service.

Every command below has been run and verified.

---

## ⚠️ The one rule

**Never `rsync` the whole directory.**

The seven `.xlsx` files on the server are live production data — real customer
accounts and orders — and they sit **in the same folder as the code**. They
differ from your local copies (server `users.xlsx` was 5,413 bytes against
9,447 locally). A bare `rsync -av .` overwrites real customer accounts with
your local fixtures, and there is **no backup of that data anywhere**.

Always enumerate the files you are pushing.

---

## The server

| | |
|---|---|
| Host | `82.97.245.77` (`еато.store` → `xn--80aj2ap.store`) |
| SSH | `root@82.97.245.77` with `~/.ssh/eato_deploy`. `ubuntu`/`deploy`/`eato` are refused — it is root or nothing |
| App path | `/opt/eato` — plain file copy |
| Service | `eato.service` (systemd), runs as user/group `eato` |
| App server | gunicorn, `--workers 1 --threads 4 --timeout 60`, on `127.0.0.1:8000` |
| Web server | nginx 1.18, reverse proxy + serves `/static/` directly |
| Env | `/etc/eato.env` — `SECRET_KEY` lives here |
| TLS | Let's Encrypt via Certbot, auto-renewing |

nginx serves `/static/` itself with `expires 30d`. **Flask never sees those
requests in production.** That 30-day cache is a real trap — see step 5.

---

## 0. What are you pushing?

```bash
cd ~/eato/site
git status --porcelain          # must be empty — commit first
git diff --name-only <last-deployed-sha> HEAD
```

Record the SHA you deploy. The last deployed SHA is noted at the bottom of this
file — **update it when you deploy.**

## 1. Sanity: does the server still match the last deployed commit?

If this does not match, someone edited files directly on the server and you are
about to silently discard their changes.

```bash
ssh -i ~/.ssh/eato_deploy root@82.97.245.77 \
  'cd /opt/eato && sha256sum app.py templates/base.html static/css/style.css'

# compare against:
for f in app.py templates/base.html static/css/style.css; do
  echo "$(git show <last-deployed-sha>:$f | shasum -a 256 | cut -d' ' -f1)  $f"
done
```

## 2. Back up what you are about to overwrite

```bash
ssh -i ~/.ssh/eato_deploy root@82.97.245.77 '
set -e
BK=/root/eato-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $BK && cd /opt/eato
cp --parents <the files you are pushing> $BK/
echo "BACKUP=$BK"
stat -c "%n %s %Y" *.xlsx > /tmp/xlsx-before.txt'
```

Note the `BACKUP=` path. That is your rollback point.

## 3. Push only the changed files

```bash
cd ~/eato/site
git diff --name-only <last-deployed-sha> HEAD > /tmp/deploy-files.txt
cat /tmp/deploy-files.txt        # eyeball it — no .xlsx should appear

rsync -av --no-perms --no-owner --no-group --files-from=/tmp/deploy-files.txt \
  -e "ssh -i ~/.ssh/eato_deploy" . root@82.97.245.77:/opt/eato/
```

## 4. Fix ownership, restart, confirm data untouched

rsync runs as root, so files land root-owned under a service running as `eato`.
Skipping the `chown` is a latent permissions failure.

```bash
ssh -i ~/.ssh/eato_deploy root@82.97.245.77 '
set -e
cd /opt/eato
chown -R eato:eato app.py templates static
systemctl restart eato.service
sleep 4
echo "service: $(systemctl is-active eato.service)"

stat -c "%n %s %Y" *.xlsx > /tmp/xlsx-after.txt
diff -q /tmp/xlsx-before.txt /tmp/xlsx-after.txt >/dev/null \
  && echo "xlsx: IDENTICAL — production data untouched" \
  || { echo "xlsx: *** CHANGED ***"; diff /tmp/xlsx-before.txt /tmp/xlsx-after.txt; }

journalctl -u eato.service --since "2 minutes ago" -p err --no-pager | tail'
```

## 5. Verify against the live site, not the server

```bash
SITE=https://xn--80aj2ap.store
for p in "" catalog collections lookbook auth cart product/1 collection/1; do
  printf '%-16s %s\n' "/$p" "$(curl -sS -o /dev/null -w '%{http_code}' $SITE/$p)"
done
```

Then confirm your actual change is live. A strong check is comparing bytes:

```bash
curl -sS $SITE/static/css/style.css | shasum -a 256
shasum -a 256 < static/css/style.css      # must match
```

**Check the cache-busting stamps changed.** `app.py` stamps every asset
referenced through `url_for('static', …)` with its mtime
(`style.css?v=1786799562`). If a stamp did not change, returning visitors stay
pinned to the old file for **30 days** — this is exactly what caused the hero
video incident (`docs/HISTORY.md`).

```bash
curl -sS $SITE/ | grep -o 'style\.css?v=[0-9]*'
```

> Product and collection images come out of Excel as raw path strings and are
> **not** versioned. Changing a product photo in place will not reach anyone who
> has already seen it — **give it a new filename instead.**

## Rollback

```bash
ssh -i ~/.ssh/eato_deploy root@82.97.245.77 '
cd /root/eato-backup-YYYYMMDD-HHMMSS && cp -r . /opt/eato/ \
  && cd /opt/eato && chown -R eato:eato app.py templates static \
  && systemctl restart eato.service'
```

Locally: `git revert <sha>`. Backups accumulate in `/root/eato-backup-*` and
nothing prunes them.

---

## Deploy log

Newest last. **Update this when you deploy.**

| Date | SHA | What | Backup |
|---|---|---|---|
| 2026-08-14 | `647ced5` | Hero video fixes | `/root/eato-backup-20260814-132410` |
| 2026-08-15 | `c9a631e` | Mobile UI; Instagram link removed | `/root/eato-backup-20260815-135146` |
| 2026-08-15 | `3f5886f` | Favicon set | `/root/eato-backup-20260815-173120` |
| 2026-08-15 | `57e1aa4` | Manifest content type | `/root/eato-backup-20260815-173305` |

**Currently live: `57e1aa4`.**

Commits after that one are documentation only (`*.md`), which is not served and
does not need deploying — so the live code is current. When you next deploy, diff
against `57e1aa4`, and be aware `git diff --name-only` will list the `.md` files;
pushing them is harmless but pointless.
