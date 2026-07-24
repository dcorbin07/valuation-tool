# LAUNCH CHECKLIST — getting this ready to sell

The definitive "what Don needs to do" list. Written to reuse your **On The Steps**
playbook (VA LLC, Zoho, Stripe, expense tracking) — most of it transfers. Costs are
in the same spirit as your FORMATION_CHECKLIST; verify before relying on them.

> **The one thing that's different from On The Steps:** that business aggregates
> *public foreclosure records*. This one outputs *stock "buy" signals for a fee*,
> which is the exact activity U.S. securities law regulates. **Phase 0 is a real
> gate — don't take a paid subscriber until it's cleared.**

---

## Phase 0 — Legal & entity (DO THIS FIRST)  ·  ~1–2 weeks, ~$100–500
- [ ] **One-hour consult with a securities/fintech attorney.** Ask specifically:
      does an interactive buy-score tool qualify for the publisher's exclusion, or
      do I need to change the product (keep it impersonal/general) or register?
      This is the launch gate — everything else is cheap by comparison.
- [ ] **Entity decision.** You already have (or are forming) *On The Steps LLC*.
      Because this product carries securities-law risk the foreclosure business
      doesn't, strongly consider a **separate LLC** to ring-fence liability, rather
      than bolting it onto On The Steps. Attorney/CPA to confirm. (VA LLC = $100
      filing + $50/yr, same process as your FORMATION_CHECKLIST.)
- [ ] **Finalize Terms + Privacy.** Fill every `[bracket]` in `terms.html` /
      `privacy.html`, have the attorney review (esp. the investment-adviser and
      liability sections), then update the "Last updated" dates.
- [ ] **Data-vendor display license.** Confirm you're allowed to *show* vendor data
      to paying users. SEC EDGAR is public/fine. Yahoo's terms are restrictive —
      for a paid product, use **FMP** (or similar) on a tier that permits display.

## Phase 1 — Product config (keys)  ·  ~20 min, $0
Paste into `.env` (already in the folder):
- [ ] `SECRET_KEY` = a long random string (`python -c "import secrets;print(secrets.token_hex(32))"`)
- [ ] `ADMIN_TOKEN` = another random string (for the weekly-scan cron)
- [ ] `SEC_USER_AGENT` = `Donovan Corbin donovan.corbin@onthesteps.co` (or the new brand's email)
- [ ] `ANTHROPIC_API_KEY` (optional — unlocks the AI analysis)
- [ ] `FMP_API_KEY` (~$22/mo Starter — needed for fast whole-market scans at scale)

## Phase 2 — Brand · domain · email  ·  ~1 hr, ~$20–40/yr
- [ ] Pick a product name + buy a domain (Namecheap, like onthesteps.co — ~$20/yr).
- [ ] Email: add a Zoho alias/mailbox on the new domain (you already run Zoho), set
      `EMAIL_FROM` and the `SMTP_*` values in `.env` (Zoho app password, as your
      pipeline already does).

## Phase 3 — Stripe  ·  ~30 min, $0 (2.9%+30¢ per charge)
- [ ] Same Stripe account is fine. **Products → add** "Pro" and "Premium" recurring
      monthly Prices (you floated $59–79 for On The Steps; I defaulted this to
      $29 Pro / $79 Premium — edit in `pricing.html` + Stripe). Copy the Price IDs.
- [ ] **Webhook** → `https://YOURDOMAIN/billing/webhook`, events:
      `checkout.session.completed`, `customer.subscription.created/updated/deleted`.
- [ ] Put `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`,
      `STRIPE_PRICE_PRO`, `STRIPE_PRICE_PREMIUM` in `.env` (start in **test mode**).

## Phase 4 — Deploy  ·  ~30 min, ~$7/mo (Render Starter)
- [ ] Push the repo to GitHub (you have `git_push.bat` patterns from On The Steps).
- [ ] Render → **New → Blueprint** (reads `render.yaml`): it provisions the web
      service, a 1 GB disk, a generated `SECRET_KEY`/`ADMIN_TOKEN`, and the weekly
      cron. Fill the `sync:false` secrets in the dashboard.
- [ ] Set `PUBLIC_BASE_URL` to your domain; attach the custom domain + HTTPS.
- [ ] (Railway/Fly/VPS work too — the `Procfile` + `Dockerfile` are generic.)

## Phase 5 — Weekly automation  ·  built-in
- [ ] The `render.yaml` cron POSTs to `/admin/run-scan` every Monday to refresh the
      hot list + email subscribers. Confirm it ran (check the snapshot date on the
      dashboard). *(Local alternative: `install_schedule.bat` on your PC.)*

## Phase 6 — Pre-launch test (Stripe TEST mode)  ·  ~30 min
- [ ] Register a test account → subscribe with Stripe test card `4242 4242 4242 4242`
      → confirm the webhook flips your tier to Pro → confirm Pro features unlock →
      open the customer portal → cancel → confirm it drops to Free.
- [ ] Trigger `/admin/run-scan` once and confirm a snapshot + (if SMTP set) a digest email.
- [ ] Click through `/terms`, `/privacy`, password reset, and the daily free limit.

## Phase 7 — GO LIVE
- [ ] Attorney sign-off + Terms/Privacy live + disclaimers visible ✅ (they already are)
- [ ] Swap Stripe to **live** keys; do one real $ test on yourself; refund it.
- [ ] Announce (reuse your Tally beta-list / outreach patterns). Watch the first
      signups with `check_signups.bat`-style habits from On The Steps.

---

## Reuse-from-On-The-Steps cheat sheet
| Need | Reuse |
|---|---|
| Entity / formation | Your VA LLC process (consider a *separate* LLC here) |
| Email | Your Zoho setup (add an alias/mailbox + app password) |
| Payments | Your Stripe account (add 2 new products) |
| Domain/DNS | Namecheap, same as onthesteps.co |
| Bookkeeping | Add these subscriptions to `expenses.xlsx`; business card only |
| Deploy habits | `git_push.bat` → host; this one needs a dynamic host (Render), not Netlify |

## All-in monthly cost at launch
- Render Starter **$7** + domain **~$2** + (optional) FMP **$22** + (optional) Anthropic **a few $**
- **≈ $10–35/mo** to run. Break-even ≈ 1 Pro subscriber.

*Not legal, tax, or investment advice. Verify costs and obligations with your attorney/CPA.*
