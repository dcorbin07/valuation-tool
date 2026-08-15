# GO LIVE — the one master checklist

Everything you need to take this live, in order. Deep dives are linked per step;
this page is the map. Costs are approximate — verify before relying on them.

**Where things stand:** the whole product is built and tested — adaptive valuation
engine (with a bank/financial P/B–ROE lens + earnings awareness), daily hot-stocks
screener, ⚡ Signals (bull **and** bear, horizon selector, contract ideas),
🚨 screaming-buy alerts (Discord + opt-in email) + a **Discord daily top-10 digest**,
📊 **Track Record** (live forward returns vs S&P at 1/3/6/12-mo **and all-time**) with
a **paper account** that trades the top-10 on real sell logic, 🔬 Edge Lab, and the SaaS
layer (accounts/billing/beta). ~45 automated tests pass. Data runs **free today**; paid
sources drop in with a one-line change. Owner account (`donniecorbin6@gmail.com`) is
**Premium free**.

**Beta mode is ON.** Right now the site is in an open free beta: a banner says it's in
development, **everyone who signs up gets full Premium free**, and a **recruiter
master-link** (`/demo/<token>`) opens a full read-only preview with no signup — that's the
link for your résumé. There is **no default token**: unset means the preview is off. When
you're ready to charge, flip `BETA_ALL_PREMIUM=false` (and set a long random
`DEMO_ACCESS_TOKEN`); the master-link keeps working for recruiters. See **ENV_REFERENCE.md → Beta / launch switches**.

**You are LIVE** at `https://valuation-tool-h2hr.onrender.com` (master-link:
`/demo/preview`), now on **Render Starter + a persistent disk** — so the hot list,
Signals, alert de-dupe, and the Track Record / paper account **persist and accrue**
(they no longer reset on restart). The daily scans still run on the **free-tier bridge**
(GitHub Actions computes them and pushes to the site — see **FREE_BRIDGE.md**), which
keeps the heavy work off the web box. Remaining work is mostly Phase 0 (legal, to
charge), email/domain polish (Phase 3), and Stripe (Phase 4) — all optional during the
free beta.

---

## Phase 0 — Legal & entity (the gate) · do first · ~1–2 wks, ~$100–500
- [ ] **Securities/fintech attorney consult.** You're charging for stock signals —
      confirm the publisher's-exemption posture or adjust the product. **Don't take a
      paid subscriber until this is cleared.**
- [ ] **Entity** — likely a **separate LLC** from On The Steps (ring-fence the
      securities risk). VA LLC = $100 + $50/yr (your `FORMATION_CHECKLIST` flow).
- [ ] **Finalize Terms + Privacy** — fill the `[brackets]` in `terms.html` /
      `privacy.html`, attorney review, set dates. (Drafts match your On The Steps style.)
- [ ] **Data-display license** — confirm your data vendor allows showing data to
      paying users (SEC EDGAR is public; for a paid product use FMP/paid tiers).
> Details: **LAUNCH_CHECKLIST.md** (Phase 0) and **SAAS_RUNBOOK.md** (Compliance).

## Phase 1 — See it yourself · $0 · ✅ deployed
- [x] Deployed free on Render → `https://valuation-tool-h2hr.onrender.com`.
- [ ] Open **`/demo/preview`** → lands on the dashboard (`/app`) with full Premium and
      no signup. (The address bar showing `/app` after the redirect is normal.)
- [ ] To run it locally too: double-click **`run_saas.bat`** → `127.0.0.1:5000`.
- Tip: the free box **sleeps after 15 min idle**, so the first visit takes ~30–60s to
  wake. Kill that with the keep-warm ping in Phase 2.5 so recruiters never see a spinner.

## Phase 2 — Env vars on the free Render (make it presentable) · 15 min · $0
Render → your web service → **Environment**. **Everything here is free** — none of it
requires buying anything. Set them, then Manual Deploy.

| Variable | Value | What it unlocks (presentability) |
|---|---|---|
| `SECRET_KEY` | long random (`python -c "import secrets;print(secrets.token_hex(32))"`) | Secure logins — drops the "insecure dev key" default. |
| `ADMIN_TOKEN` | long random | **Lets the daily scans post to the site.** Without it, Hot Stocks + Signals stay empty. Must match the GitHub secret (Phase 2.5). |
| `SEC_USER_AGENT` | `Donovan Corbin donniecorbin6@gmail.com` | Reliable SEC EDGAR scans (a generic agent gets throttled). |
| `ANTHROPIC_API_KEY` | your key (you have it) | AI moat/risk/thesis notes + Signals reasoning. Pay-per-use, ~cents; not a subscription. |
| `TRADIER_TOKEN` + `TRADIER_ENV=live` | your Tradier token | **Real-time** quotes + option chains for Signals. Free with your brokerage account. No account number needed. |
| `PUBLIC_BASE_URL` | `https://valuation-tool-h2hr.onrender.com` | Correct links in emails/redirects. |
| `DEMO_ACCESS_TOKEN` | a fresh random value — **never `preview`** | Your résumé master-link (`/demo/<token>`) and the on/off switch for the `/work` button. `preview` is guessable and was published in `/work`'s HTML until 2026-08-14 (MA9). Generate: `python -c "import secrets;print(secrets.token_urlsafe(24))"`. |
| `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` + `EMAIL_FROM` | your Zoho (optional) | Real password-reset + daily digest + opt-in alert emails → feels like a finished product. |
| `DISCORD_WEBHOOK_URL` | ✅ set | Posts the **daily top-10 digest** + **screaming-buy** alerts to your Discord channel. |

*(`OWNER_EMAILS`, `BETA_MODE`, `BETA_ALL_PREMIUM` already default correctly — nothing to set.)*
> Reference: **ENV_REFERENCE.md** (every setting explained).

## Phase 2.5 — Turn on the daily scans (free bridge) · 10 min · $0
So the hot list + Signals are pre-computed and already showing for everyone.
- [ ] GitHub repo → **Settings → Secrets → Actions**: add `SITE_BASE_URL`,
      `ADMIN_TOKEN` (same as above), and optionally `ANTHROPIC_API_KEY`, `TRADIER_TOKEN`.
- [ ] **Actions → "Auto scans" → Run workflow → hot** to populate immediately; after
      that it runs itself (hot list pre-market, Signals every 30 min in market hours).
- [ ] **Keep-warm (recommended):** [cron-job.org](https://cron-job.org) → GET
      `https://valuation-tool-h2hr.onrender.com/api/health` every 10 min, so the list
      survives between scans and there's no cold-start spinner.
> Full walkthrough: **FREE_BRIDGE.md**.

## Phase 3 — Brand · domain · email · ~1 hr · ~$20–40/yr
- [ ] Pick a name + buy a domain (Namecheap, like `onthesteps.co`).
- [ ] Add a Zoho alias on the new domain; set `EMAIL_FROM` + `SMTP_*` (you already run Zoho).

## Phase 4 — Stripe · ~40 min · $0 (2.9%+30¢/charge)
- [ ] Create **Pro** and **Premium** products, each with a **monthly** and a **yearly**
      price ($9.99/$99 and $29.99/$299). Copy all four Price IDs.
- [ ] Webhook → `https://YOURDOMAIN/billing/webhook` (checkout + subscription events).
- [ ] Put `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`,
      `STRIPE_PRICE_PRO`, `STRIPE_PRICE_PREMIUM`, `STRIPE_PRICE_PRO_ANNUAL`,
      `STRIPE_PRICE_PREMIUM_ANNUAL` in `.env`. Start in **test mode**.

## Phase 5 — Paid deploy · ~$8/mo · ✅ Starter + disk added
Persistence is on — the hot list, Signals, alerts, and Track Record now survive
restarts. Remaining optional steps:
- [ ] Make sure **Auto-Deploy is ON** (Render → Settings) so pushes deploy themselves.
- [ ] Render → **New → Blueprint** → pick the repo. `render.yaml` provisions the
      **Starter** web service + **1 GB disk** + generated secrets + the **daily hot-scan**
      and **15-min intraday Signals** crons (auto-authenticated — nothing to wire).
- [ ] Re-add your env vars (Phase 2), set `PUBLIC_BASE_URL`, attach a custom domain + HTTPS.
- [ ] **Disable the "Auto scans" GitHub Action** so you're not scanning twice.
> Details: **SAAS_RUNBOOK.md** and **FREE_BRIDGE.md** (the flip section).

## Phase 6 — Data upgrades (optional, as you grow)
- [ ] **Real-time Signals:** add `TRADIER_TOKEN` (+ `TRADIER_ENV=live`). Free delayed otherwise.
- [ ] **Fast whole-market scans:** add `FMP_API_KEY` (~$22/mo). Free EDGAR/Stooq otherwise.
- [ ] **Research-grade edge data (Edge Lab):** free now. To prove edge properly, set
      `EDGE_DATA_PROVIDER=sharadar` (+`SHARADAR_API_KEY`) or `=wrds` (+`WRDS_DATA_DIR`).
      **Chase free WRDS access through William & Mary first.**
> Details: **DATA_AND_METHODS.md** and **EDGE_LAB.md**.

## Phase 7 — Pre-launch test (Stripe TEST mode) · ~30 min
- [ ] Register → subscribe with test card `4242 4242 4242 4242` → webhook flips your
      tier → Pro/Premium features unlock → open customer portal → cancel → drops to Free.
- [ ] Hit `/admin/run-scan` and `/admin/run-intraday` once; confirm the lists populate.
- [ ] Click `/terms`, `/privacy`, password reset, and the daily free limits.

## Phase 8 — Go live + hands-off
- [ ] Attorney sign-off ✅, Terms/Privacy live ✅, disclaimers visible ✅ (already in app).
- [ ] Flip Stripe to **live** keys; do one real $ test on yourself; refund it.
- [ ] Turn on the local safety nets: **`install_autopush.bat`** (GitHub) and
      **`setup_backup_schedule.bat`** (D: drive backup).
- [ ] Let the **Edge Lab track record accrue** — it's the honest, forward, survivorship-
      free proof of whether the picks beat the S&P. Don't size real capital until it does.

---

## Cost — what's free vs what you'd buy
**Right now (free beta): $0.** Render free + the GitHub-Actions scan bridge + your
existing Anthropic key (pay-per-use, ~cents) + your Tradier account (free real-time).
**Nothing needs to be purchased to make the site fully presentable.**

Optional buys, in order of impact:
- **Custom domain** (~$12/yr) — replaces `valuation-tool-h2hr.onrender.com`; the biggest
  presentability upgrade. Point it at Render.
- **Render Starter + disk** (~$8/mo) — no cold starts, persistent data, server-side crons.
- **FMP** (~$22/mo) — faster/broader scans; *not needed* (free EDGAR/yfinance works, and
  scans run in Actions on free anyway).
- **Sharadar** (tens/mo) — survivorship-free data for the *private* Edge Lab only; chase
  free **WRDS via William & Mary** first.
- **Stripe** — free to set up; only when you start charging (2.9%+30¢/charge).

## The doc map
| Doc | What |
|---|---|
| **GO_LIVE.md** (this) | the master checklist |
| LAUNCH_CHECKLIST.md | detailed launch + On-The-Steps reuse cheat sheet |
| SAAS_RUNBOOK.md | Stripe/hosting/email + compliance deep dive |
| ENV_REFERENCE.md | every setting explained |
| FREE_BRIDGE.md | free-tier auto-scan (GitHub Actions → site) + keep-warm |
| RUNBOOK.md | the core tool (single valuations, scans) |
| EDGE_LAB.md | private research bench (backtest, track record, no-overfit optimize) |
| DATA_AND_METHODS.md | how to prove an edge: data + reputable methods |
| GITHUB_SETUP.md | pushing to a private repo |

*Educational tooling, not investment advice.*
