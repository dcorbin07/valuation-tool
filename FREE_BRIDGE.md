# Free-tier auto-scan bridge

**Goal:** the daily hot list (and the Premium Signals feed) are computed once, on a
schedule, and are already showing for everyone the moment they open the site — with
no per-visitor scanning and no paid infra yet.

**Why this exists:** a free Render web service can't run a scheduler and has no
persistent disk, and a whole-market scan is too heavy for its 512 MB box anyway. So
we run the scan on **GitHub Actions** (real internet, 7 GB RAM, free) and push the
finished result to a small token-protected endpoint on your site. Your web box only
does a light database write.

```
GitHub Actions (daily / intraday)                       Your free Render site
  run the scan  ──POST rows + X-Admin-Token──▶  /admin/ingest-snapshot  ──▶  saved
                                                /admin/ingest-intraday        snapshot
                                                                     ▲
                                          every visitor reads it instantly at /app
```

---

## One-time setup (~10 min)

### 1. Set `ADMIN_TOKEN` on Render
Render → your web service → **Environment** → add:

| Key | Value |
|---|---|
| `ADMIN_TOKEN` | `apwCRlcBZ_iSJLY4Lcqbg_4C66_9DJa6` |

(That's a fresh random token — fine to use, or generate your own with
`python -c "import secrets;print(secrets.token_urlsafe(24))"`.) Without it, the ingest
endpoints return 401.

### 2. (For real-time Signals) set Tradier on Render
Same Environment form:

| Key | Value |
|---|---|
| `TRADIER_TOKEN` | your Tradier access token |
| `TRADIER_ENV` | `live` |

**You do NOT need your Tradier account number** — the app only calls market-data
endpoints (quotes, history, option chains), which authenticate with just the token.
`TRADIER_ENV=live` is required: the default is `sandbox`, and a live token is rejected
there. Only downside of the live token vs sandbox: it's a real credential tied to your
brokerage account, so keep it in env vars only (never commit it). The app only *reads*
quotes — it never trades.

### 3. Add the GitHub Actions secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `SITE_BASE_URL` | `https://valuation-tool-h2hr.onrender.com` |
| `ADMIN_TOKEN` | **same** token as step 1 |
| `ANTHROPIC_API_KEY` | *(optional)* your key, for AI notes on top names |
| `TRADIER_TOKEN` | *(optional)* your token, for real-time Signals in the scan runner |

### 4. Populate it now
Repo → **Actions → "Auto scans (free-tier bridge)" → Run workflow → hot → Run**.
In a couple of minutes the hot list is live at `/app`. After that it runs itself:
**hot list** every weekday pre-market, **Signals** every 30 min during market hours.

### 5. (Recommended) keep it warm so the list survives all day
The free box sleeps after 15 min idle and loses the in-memory snapshot until the next
scheduled scan. To keep the list showing between scans, add a free pinger:
[cron-job.org](https://cron-job.org) → new cronjob → **GET**
`https://valuation-tool-h2hr.onrender.com/api/health` every **10 minutes**. (This keeps
one free instance awake ~24/7, which fits inside Render's free monthly hours if it's
your only service.)

---

## What's still limited on free (and why paid fixes it)
- **Data resets** when the box redeploys or sleeps (no persistent disk), so accounts
  created during beta and the snapshot are ephemeral. The scheduled scans repopulate
  the list; the keep-warm ping holds it between them.
- **Signals** every 30 min (Actions minutes), not every 15.

## Flip to the paid setup any time (~$8/mo, everything persistent + hands-off)
Everything's already wired in `render.yaml`:
1. Render → **New → Blueprint** → pick this repo. It provisions the **Starter** web
   service + a **1 GB disk** + the **daily hot-scan cron** + the **15-min intraday
   cron** (auto-authenticated — nothing to type).
2. Set `PUBLIC_BASE_URL`, `ANTHROPIC_API_KEY`, `TRADIER_TOKEN`, `TRADIER_ENV=live`.
3. **Disable this GitHub Action** (Actions → ⋯ → Disable workflow) so you're not
   scanning twice.

Then the snapshot persists across restarts, Signals refresh every 15 min on the
server, and there's no keep-warm hack. See **GO_LIVE.md → Phase 5**.
