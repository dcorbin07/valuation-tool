# SaaS Go-Live Runbook — turning this into a subscription service

The subscription layer is **built and tested**: accounts, login, a marketing
landing + pricing page, per-tier feature gating, Stripe billing (checkout +
webhook + customer portal), a weekly server-side scan worker, and email digests.
What remains is *your* accounts, keys, hosting, and — importantly — the legal
groundwork. This is the checklist.

> ⚠️ **Read the Compliance section first.** Charging money for stock "buy" signals
> can trigger securities regulation. Sort that out before you take a dollar.

---

## What's already done (no action needed)
- Multi-user accounts with hashed passwords (`valuation/saas/`).
- Tiers **Free / Pro / Premium** with feature gating (`gating.py`) — edit limits/prices in one place.
- Stripe Checkout, webhook subscription sync, and customer portal (`billing.py`).
- Landing, pricing, login, register, account pages.
- Weekly scan worker + email digest (`scan_worker.py`, `emailer.py`).
- Docker / gunicorn / Procfile / docker-compose for one-command deploy.
- Run locally right now: `python run_saas.py` → http://127.0.0.1:5000

---

## What I need from you (the go-live list)

### 1. Stripe (billing) — ~30 min
1. Create a Stripe account → **Developers → API keys**: copy the **Secret** and **Publishable** keys.
2. **Products → add product** twice: "Pro" and "Premium", each a **recurring monthly Price**. Copy the two **Price IDs** (`price_...`).
3. **Developers → Webhooks → add endpoint**: URL `https://YOURDOMAIN/billing/webhook`, events:
   `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`. Copy the **Signing secret** (`whsec_...`).
4. Paste all of these into `.env`:
   ```
   STRIPE_SECRET_KEY=sk_live_or_test_...
   STRIPE_PUBLISHABLE_KEY=pk_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_PRO=price_...
   STRIPE_PRICE_PREMIUM=price_...
   ```
   Start with **test-mode** keys and Stripe's test cards; flip to live keys when ready.

### 2. Hosting — ~30 min (Render is the easiest)
The app is a standard Docker/gunicorn web service + a scheduled worker.
- **Render:** New → **Web Service** from your repo (it reads the `Dockerfile`). Add a **Cron Job**
  running `python -m valuation.saas.scan_worker` weekly (e.g. `0 6 * * 1`). Add a **Persistent Disk**
  mounted at `/app/data` (or use Postgres, below). Set all `.env` values as environment variables.
- **Railway / Fly.io / a VPS** work the same way (the `Procfile` defines `web` and `worker`).
- Set `PUBLIC_BASE_URL=https://yourdomain.com` so Stripe redirects and emails use the right URL.

### 3. Database — SQLite is fine to launch; Postgres for scale
Default is SQLite on the mounted disk (zero setup). When you outgrow it: provision Postgres, add
`psycopg2-binary` to `requirements-saas.txt`, set `DATABASE_URL=postgresql://…`, and swap the thin
`UserStore` for a SQLAlchemy version (the interface is small — 12 methods).

### 4. Email (optional but recommended) — ~15 min
Sign up for SendGrid/Postmark/SES, verify your sending domain, and set `SMTP_*` + `EMAIL_FROM` in
`.env`. Without it, receipts and the weekly digest simply don't send (everything else still works).

### 5. Domain + a strong secret
Point a domain at your host and set `SECRET_KEY` to a long random string
(`python -c "import secrets;print(secrets.token_hex(32))"`).

### 6. Data at scale
For a real subscriber base, add an **FMP_API_KEY** so the weekly whole-market scan is fast and
reliable (the free feed is fine for dozens of users, not thousands).

---

## Compliance — please take this seriously (not legal advice)

I'm not a lawyer, and this is not legal advice — but you're about to **charge money for stock
recommendations**, which is exactly the activity U.S. securities law regulates. Get real advice
before launch. The key issues to raise with a **securities attorney**:

- **Investment Adviser status.** The Investment Advisers Act (federal) and state RIA rules can apply
  to anyone who, *for compensation*, is in the business of advising others about securities. There is
  a **"publisher's exclusion"** (from *Lowe v. SEC*) for bona fide, regular, and **impersonal**
  publications of general circulation — many stock newsletters rely on it. Whether an **interactive,
  data-driven tool** that outputs buy scores qualifies is fact-specific and *not* something to guess at.
- **Keep it impersonal and general** if you're relying on the publisher's exclusion: no personalized
  recommendations, no managing anyone's money, no "what should *I* buy" advice tailored to a user.
- **Disclaimers everywhere** (already in the app footer and reports): educational only, not advice,
  past/backtested performance is not indicative of future results, you may hold positions, etc.
- **Marketing rules.** Avoid performance claims, testimonials, and cherry-picked results — these have
  specific legal requirements and are a common enforcement target.
- **Terms of Service + Privacy Policy.** You need both before taking payments (and for Stripe). Use a
  reputable generator or attorney; cover disclaimers, refunds, liability limits, and data handling.
- **Data licensing.** Confirm your data vendor's terms permit *redistribution/display* to paying users
  (Yahoo's terms are restrictive; SEC EDGAR is public; **FMP and other paid APIs offer display/
  redistribution licensing** — get the right tier). This matters the moment you show vendor data to
  subscribers.
- **State registration & taxes.** RIA registration (if applicable) is often at the state level; sales
  tax on SaaS varies by state.

A one-hour consult with a securities/fintech attorney is the cheapest insurance you'll buy here.

---

## Launch checklist (tl;dr)
- [ ] Stripe products + webhook, keys in `.env`
- [ ] Deploy to Render/Railway/Fly (Docker) with env vars set
- [ ] Weekly cron → `python -m valuation.saas.scan_worker`
- [ ] `PUBLIC_BASE_URL`, `SECRET_KEY`, (optional) `FMP_API_KEY`, `SMTP_*`
- [ ] Test the full flow in Stripe **test mode** (register → subscribe → webhook flips tier → portal cancel)
- [ ] **Terms of Service + Privacy Policy live, disclaimers visible, attorney consulted**
- [ ] Data-vendor display license confirmed
- [ ] Flip Stripe to live keys → open the doors
