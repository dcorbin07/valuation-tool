# GO LIVE — the one master checklist

Everything you need to take this live, in order. Deep dives are linked per step;
this page is the map. Costs are approximate — verify before relying on them.

**Where things stand:** the whole product is built and tested (valuation engine,
daily hot-stocks screener, ⚡ Signals watcher, 📊 backtest, 🔬 Edge Lab, SaaS with
accounts/billing, deploy config, backups, GitHub). Data runs **free today**; paid
sources drop in with a one-line change. Your owner account (`donniecorbin6@gmail.com`)
already gets **Premium free**.

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

## Phase 1 — See it yourself now · 5 min · $0
- [ ] Double-click **`run_saas.bat`** → the real site opens at `127.0.0.1:5000`.
- [ ] Register **donniecorbin6@gmail.com** → you're auto-Premium; click through
      Hot stocks, ⚡ Signals, 📊 Backtest, and your private 🔬 Edge Lab tab.

## Phase 2 — Product config (`.env`) · 15 min · $0
- [ ] `SECRET_KEY` = long random (`python -c "import secrets;print(secrets.token_hex(32))"`)
- [ ] `ADMIN_TOKEN` = long random (used by the auto-scan crons)
- [ ] `SEC_USER_AGENT` = your name + email  ·  `ANTHROPIC_API_KEY` = ✅ already set
- [ ] (owner Premium is defaulted to your email — nothing to do)
> Reference: **ENV_REFERENCE.md** (what every setting is; fill only what you use).

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

## Phase 5 — Deploy · ~30 min · ~$7/mo (Render Starter)
- [ ] Push to GitHub (double-click **`connect_github.bat`** once — already set up).
- [ ] Render → **New → Blueprint** → pick the repo. `render.yaml` provisions the web
      service + disk + generated secrets + the **daily hot-scan** and **15-min intraday
      Signals** crons (auto-authenticated — nothing to wire).
- [ ] Set `PUBLIC_BASE_URL` to your domain; attach the custom domain + HTTPS.
> Details: **SAAS_RUNBOOK.md**.

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

## All-in monthly cost
Render **$7** + domain **~$2** + (optional) FMP **$22**, Tradier (your account), Anthropic
(a few $), Sharadar (tens, only if not using free WRDS). **≈ $10–35/mo to start.**

## The doc map
| Doc | What |
|---|---|
| **GO_LIVE.md** (this) | the master checklist |
| LAUNCH_CHECKLIST.md | detailed launch + On-The-Steps reuse cheat sheet |
| SAAS_RUNBOOK.md | Stripe/hosting/email + compliance deep dive |
| ENV_REFERENCE.md | every setting explained |
| RUNBOOK.md | the core tool (single valuations, scans) |
| EDGE_LAB.md | private research bench (backtest, track record, no-overfit optimize) |
| DATA_AND_METHODS.md | how to prove an edge: data + reputable methods |
| GITHUB_SETUP.md | pushing to a private repo |

*Educational tooling, not investment advice.*
