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
| `DEMO_ACCESS_TOKEN` | `preview` | The **recruiter master-link**. Anyone visiting `/demo/<token>` gets an instant Premium preview with **no signup** — this is the URL you put on your résumé. It keeps working even after beta ends, so before you start charging, change it to something long and unguessable (e.g. `python -c "import secrets;print(secrets.token_urlsafe(12))"`). |

> Master-link format: `https://YOUR-SITE/demo/preview` (swap in your token). Owner
> (`donniecorbin6@gmail.com`) still gets Premium regardless of any of these.

## Leave blank until you need them
| Variable | Fill it in when… | Where to get it |
|---|---|---|
| `PUBLIC_BASE_URL` | after the first deploy — set it to your site URL (e.g. `https://valuation-tool.onrender.com`) | Render shows the URL after deploy |
| `FMP_API_KEY` | you want fast whole-market scans | financialmodelingprep.com (~$22/mo) |
| `TRADIER_TOKEN` | you want real-time intraday **Signals** | your Tradier account → API access token |
| `TRADIER_ENV` | with Tradier | `sandbox` (delayed) or `live` (real-time) |
| `EDGE_DATA_PROVIDER` | research data source | `free` (default), `sharadar`, or `wrds` |
| `SHARADAR_API_KEY` | you switch Edge Lab to Sharadar | Nasdaq Data Link account key |
| `WRDS_DATA_DIR` | you switch Edge Lab to WRDS | folder of CRSP/Compustat exports (free via W&M) |
| `STRIPE_SECRET_KEY` | you're ready to charge money | Stripe → Developers → API keys |
| `STRIPE_PUBLISHABLE_KEY` | " | Stripe → Developers → API keys |
| `STRIPE_WEBHOOK_SECRET` | " | Stripe → Developers → Webhooks |
| `STRIPE_PRICE_PRO` | " | Stripe → Products → Pro **monthly** price (`price_…`) |
| `STRIPE_PRICE_PREMIUM` | " | Stripe → Products → Premium **monthly** price |
| `STRIPE_PRICE_PRO_ANNUAL` | you offer annual billing | Stripe → Pro product → add a **yearly** price ($99/yr) |
| `STRIPE_PRICE_PREMIUM_ANNUAL` | " | Stripe → Premium product → add a **yearly** price ($299/yr) |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | you want to send emails (receipts, weekly digest, alerts) | your email provider — Zoho works, like On The Steps |
| `DISCORD_WEBHOOK_URL` | you want screaming-buy alerts posted to a Discord channel | Discord → channel → Integrations → Webhooks → New Webhook → Copy URL |
| `ALERT_MIN_SCORE` | you want to tune how strict the alerts are (default 80) | a number 0–100 — higher = fewer, higher-conviction alerts |

## The cron job section (weekly-scan-trigger)
| Variable | What to put |
|---|---|
| `PUBLIC_BASE_URL` | the same site URL (after deploy) |
| `ADMIN_TOKEN` | leave blank for now; set the weekly auto-scan up later |

## Bottom line
Fill the **two** in the first table, leave the rest blank, and deploy. Add Stripe
when you've cleared the legal step and are ready to charge; add SMTP when you want
emails; add FMP when scans need to be fast. Nothing breaks by leaving them empty.
