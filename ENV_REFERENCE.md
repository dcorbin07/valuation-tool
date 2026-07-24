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

## Leave blank until you need them
| Variable | Fill it in when… | Where to get it |
|---|---|---|
| `PUBLIC_BASE_URL` | after the first deploy — set it to your site URL (e.g. `https://valuation-tool.onrender.com`) | Render shows the URL after deploy |
| `FMP_API_KEY` | you want fast whole-market scans | financialmodelingprep.com (~$22/mo) |
| `STRIPE_SECRET_KEY` | you're ready to charge money | Stripe → Developers → API keys |
| `STRIPE_PUBLISHABLE_KEY` | " | Stripe → Developers → API keys |
| `STRIPE_WEBHOOK_SECRET` | " | Stripe → Developers → Webhooks |
| `STRIPE_PRICE_PRO` | " | Stripe → Products → your Pro price (`price_…`) |
| `STRIPE_PRICE_PREMIUM` | " | Stripe → Products → your Premium price |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` / `EMAIL_FROM` | you want to send emails (receipts, weekly digest) | your email provider — Zoho works, like On The Steps |

## The cron job section (weekly-scan-trigger)
| Variable | What to put |
|---|---|
| `PUBLIC_BASE_URL` | the same site URL (after deploy) |
| `ADMIN_TOKEN` | leave blank for now; set the weekly auto-scan up later |

## Bottom line
Fill the **two** in the first table, leave the rest blank, and deploy. Add Stripe
when you've cleared the legal step and are ready to charge; add SMTP when you want
emails; add FMP when scans need to be fast. Nothing breaks by leaving them empty.
