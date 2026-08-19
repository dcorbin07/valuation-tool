# Environment variables — plain-English cheat sheet

These settings live in **two places**, with the **same values**:
- **On your PC:** the `.env` file (for `run_saas.bat` / local running).
- **On Render:** the "Environment Variables" form (for the live site).

Render's form **replaces `.env`** for the hosted site. Never upload `.env` to
Render or GitHub — it's git-ignored on purpose. Fill the boxes instead.

**You can leave almost everything blank and still get a working site.** Only add
each item when you actually need the feature it unlocks.

## Fill these to get the site live
| Variable | What to put | Where it comes from |
|---|---|---|
| `ANTHROPIC_API_KEY` | your key (you have it) | console.anthropic.com |
| `SEC_USER_AGENT` | `Donovan Corbin donniecorbin6@gmail.com` | just your name + email |

*(Render auto-generates `SECRET_KEY`, `DATABASE_URL`, and the web service's
`ADMIN_TOKEN` — you don't touch those.)*

## Beta / launch switches (on by default — nothing to set for the free beta)
| Variable | Default | What it does |
|---|---|---|
| `BETA_MODE` | `true` | Shows the "in beta / in active development" banner site-wide. Set `false` when you no longer want the banner. |
| `BETA_ALL_PREMIUM` | `true` | Treats **every signed-in account** as Premium, free — your open beta. Set `false` to end it and fall back to real tiers/Stripe. No DB change; it flips instantly. |
| `DEMO_ACCESS_TOKEN` | *(unset — the preview is off)* | The **recruiter master-link**. Anyone visiting `/demo/<token>` gets an instant read-only preview with **no signup** — this is the URL you put on a résumé. Also the on/off switch for the **Open the full tool** button on `/work`: clearing it removes the button and kills every copied deep-link at once. **Generate a long random value, never a dictionary word:** `python -c "import secrets;print(secrets.token_urlsafe(24))"`. **This row used to document the value `preview`, and `preview` must never be used again** — it was both guessable and, until 2026-08-14, rendered into the public HTML of `/work` (audit MA9), so it is a published string. See `render.yaml` for the two-step regate. |

| `LEARN_ENABLED` | `false` | The monthly **self-learning** re-tune of the screener's factor weights. **Leave it off.** It defaulted to `true` and was documented nowhere until the master audit (MA1) traced a monthly cron that could change the composite users see by writing to Render's database — no code commit, no diff, nothing the vintage contract could see. The value must be exactly `true` to switch it on — anything else (`1`, `yes`, a typo, a blank) reads **off**, deliberately, so a fat-fingered value cannot arm it. Turning it on only re-arms the **learner**, not the **adoption**: a learned weight still cannot reach the live scorer without a registered vintage and your signed row in `PAPER_TRACK_CONTRACT.md`, so the worst it can do is fill the audit log and email you. |

> Master-link format: `https://YOUR-SITE/demo/preview` (swap in your token). Owner
> (`donniecorbin6@gmail.com`) still gets Premium regardless of any of these.

## Leave blank until you need them
| Variable | Fill it in when… | Where to get it |
|---|---|---|
| `PUBLIC_BASE_URL` | after the first deploy — set it to your site URL (e.g. `https://valuation-tool.onrender.com`) | Render shows the URL after deploy |
| `FMP_API_KEY` | you want fast whole-market scans | financialmodelingprep.com (~$22/mo) |
| `FMP_BACKTEST_API_KEY` | optional — a *second* FMP key used only by the backtest exporters (`export_grades`). The live hot-list scan (22:23 UTC) and the grades export share `FMP_API_KEY`, so on the free tier a big export can eat the quota the scan needs. A second free account is enough to keep the two apart. Falls back to `FMP_API_KEY` when unset. | financialmodelingprep.com |
| `TRADIER_TOKEN` | you want real-time intraday **Signals** | your Tradier account → API access token |
| `TRADIER_ENV` | with Tradier | `sandbox` (delayed) or `live` (real-time) |
| `TRADIER_PAPER_TOKEN` | you want the **forward paper track** running (roadmap #12 — the one thing that tests the edge on data nobody has seen) | a Tradier **sandbox/paper** account → Preferences → API Access. Must be a *different* credential from `TRADIER_TOKEN`: the paper track refuses to start if the two are identical, and never falls back to the production token. |
| `TRADIER_PAPER_ACCOUNT_ID` | with `TRADIER_PAPER_TOKEN` | the paper account number, e.g. `VA12345678` — same Tradier page |
| `PAPER_CONTRACTS_PER_TRADE` | optional (default `1`) | keeps the forward options book on the same fixed-1-contract basis the backtested scorecard uses, so the two expectancies are comparable |
| `EDGE_DATA_PROVIDER` | research data source | `free` (default), `sharadar`, or `wrds` |
| `SHARADAR_API_KEY` | you switch Edge Lab to Sharadar | Nasdaq Data Link account key |
| `WRDS_DATA_DIR` | you switch Edge Lab to WRDS | folder of CRSP/Compustat exports (free via W&M) |
| `THETADATA_API_KEY` | you run the options backtest / live options signals | thetadata.net → your API key (Standard ~$80/mo). Local `.env` for the backtest; add to Render too once live options signals use it. |
| `STRIPE_SECRET_KEY` | you're ready to charge money | Stripe → Developers → API keys |
| `STRIPE_PUBLISHABLE_KEY` | " | Stripe → Developers → API keys |
| `STRIPE_WEBHOOK_SECRET` | " | Stripe → Developers → Webhooks |
| `STRIPE_PRICE_PRO` | " | Stripe → Products → Pro **monthly** price (`price_…`) |
| `STRIPE_PRICE_PREMIUM` | " | Stripe → Products → Premium **monthly** price |
| `STRIPE_PRICE_PRO_ANNUAL` | you offer annual billing | Stripe → Pro product → add a **yearly** price ($99/yr) |
| `STRIPE_PRICE_PREMIUM_ANNUAL` | " | Stripe → Premium product → add a **yearly** price ($299/yr) |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | you want to send emails (receipts, weekly digest, alerts) | your email provider — Zoho works, like On The Steps |
| `DISCORD_WEBHOOK_URL` | you want screaming-buy alerts, the daily hot digest and the **daily/weekly paper-track recaps** posted to a Discord channel | Discord → channel → Integrations → Webhooks → New Webhook → Copy URL. Set it **on Render** (the recaps post server-side); the same value as a GitHub Actions secret only covers the scan-failure alert and the watchdog |
| `ALERT_MIN_SCORE` | you want to tune how strict the alerts are (default 80) | a number 0–100 — higher = fewer, higher-conviction alerts |
| `TRUSTED_PROXY_HOPS` | **only if you put something in front of Render** (a CDN like Cloudflare). Default `1`, which is correct today. | The number of proxies between the visitor and the app. Getting it wrong is silent in both directions: too low and every visitor shares one rate-limit bucket (one scraper can then exhaust the limit for everybody); too high and the limiter is bypassable with a header. **Don't guess — check.** `GET /admin/proxy-shape` with your `ADMIN_TOKEN` reports the observed value and says which to set. (MA8) |

## The cron job section (weekly-scan-trigger)
| Variable | What to put |
|---|---|
| `PUBLIC_BASE_URL` | the same site URL (after deploy) |
| `ADMIN_TOKEN` | leave blank for now; set the weekly auto-scan up later |

## Bottom line
Fill the **two** in the first table, leave the rest blank, and deploy. Add Stripe
when you've cleared the legal step and are ready to charge; add SMTP when you want
emails; add FMP when scans need to be fast. Nothing breaks by leaving them empty.
