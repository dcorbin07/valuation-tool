# HANDOFF — live app (app-fixer lane)

Own lane: live scan / universe / display. Does not touch `valuation/edge/` options work, the
ThetaData miner, or `fairvalue.py`.

---

# Session 9 — 2026-08-04 — Private mode: Valquo becomes a personal tool (PROMPT_appfixer_private.md)

All seven items shipped. Valquo is now owner-only behind one reversible flag, every commercial
surface is off, and the forward track — the one dataset here that cannot be rebuilt — is backed
up into git on a weekly schedule. Nothing in this session touches the options backtest, the
fundamental panel or the miner.

## The flag

**`PRIVATE_MODE`, default `true`** (`valuation/config.py`). Also declared in `render.yaml` so it
is visible and flippable in the Render dashboard rather than hidden in a code default.

It is read in exactly two kinds of place, which is what makes it auditable:

1. **Three derived properties on `Config`** — `public_access`, `signup_enabled`,
   `billing_enabled`, plus `beta_banner_enabled`. No template or route tests `private_mode`
   arithmetic itself; they read a named concept.
2. **`valuation/saas/private.py`** — the request-level policy, called from `app_saas._guard`
   before any other access decision. `check(path, user, cfg)` is a pure function returning
   `None` (allow) or a refusal dict, so "prove the lockdown holds" is a unit test rather than a
   browser session.

**It outranks every flag that would open the product**, and each is asserted separately:
`OPEN_ACCESS=true`, `BETA_ALL_PREMIUM=true`, an explicit `FEATURE_BILLING=on` and a configured
Stripe key all fail to re-open anything. A lockdown that another flag can quietly undo is not a
lockdown, and `FEATURE_BILLING=on` in particular used to be an explicit "force the pricing page
visible" override — it is now refused.

**Nothing is deleted.** Every tier, route, template and Stripe path is intact and still under
test. See "Reversing this" at the end.

## 1. Locked to the owner

`_guard` refuses everyone but the owner, ahead of the landing page, the tier caps and the
per-visitor rate limit — because all three implement the public product, and shaping a
stranger's request with "what may a visitor see" logic before asking whether there is supposed
to be a visitor is the wrong order.

- **Owner = a real signed-in account whose address is in `OWNER_EMAILS`.** A demo/preview
  session is explicitly *not* the owner even though `gating._active` grants it Premium.
- **Signed in but not the owner is refused too** — which is why the concept is `public_access`
  and not simply `open_access`.
- **The refusal is identical for anonymous and for signed-in-as-someone-else.** The difference
  is not information a stranger should have, and leaking it is a free account-enumeration
  oracle. Pinned by a test.
- **Anonymous gets a plain holding page** (`private_landing.html`), not a trimmed landing page:
  no sample valuation, no track, no screenshot, no feature list, no signup. Plus
  `noindex, nofollow` and no Open Graph card — a rich preview advertising "a whole-market
  screener" is the wrong public face for an instance nobody can use.
- **`/demo` (the recruiter link) is refused outright**, handled conservatively per the brief.
  It is the one route whose entire purpose is letting a third party read the tool without an
  account. `private.is_owner` separately refuses to honour a surviving demo cookie.

Five things stay open, each for a stated reason, and the allowlist is pinned by a test so it
cannot be widened by accident:

| Open | Why |
|---|---|
| `/api/health` | `render.yaml` health probe. Blocking it makes Render roll back every deploy — the lockdown would take the service *down* rather than lock it. Returns three config booleans, no market data. |
| `/login`, `/forgot`, `/reset/<token>` | Or the owner can never get in. |
| `/admin/*`, `/api/option-alerts/*` | The crons. This lets them REACH `_admin_ok`; it does not skip it. |
| `/alerts/unsubscribe/<token>` | An unsubscribe link that requires signing in first is not an unsubscribe link. |
| `/static/` | The login page needs its stylesheet. |

Everything else is denied, so forgetting a route fails as "the owner has to log in", never as
"a stranger reads the book". A test sweeps the app's own URL map — not a hand-written list — so
an `/api/` route added next month is covered the day it is added.

## 2. Commercial surfaces off

No payment can be initiated: `/billing/checkout` and `/billing/portal` return **403**, and they
say why rather than claiming a misconfiguration — "Billing isn't configured (set
STRIPE_SECRET_KEY)" would be a lie that invites someone to "fix" it by setting a key, which
would not in fact re-enable checkout. `/pricing` and `/register` redirect (route-level, not just
hidden buttons). The Stripe webhook no-ops. The beta strip — "you're exploring the full app,
everything unlocked, no sign-up needed" — is off; it addresses prospective users and there are
none. Nav and footer drop every link that now 401s, so a logged-out visitor never sees a row of
dead links.

## 3. Vendor audit — what each surface actually serves

**Confirmed: no raw ThetaData and no raw Sharadar rows are exposed on any page or API route.**
Traced by reading each route's imports through to the provider, not by assuming.

| Surface | Numbers come from | Category |
|---|---|---|
| `/app` dashboard shell, `/methodology` | nothing — static copy | — |
| Single valuation (`/api/value`) | yfinance + SEC EDGAR (+ FMP if keyed), live Treasury | live vendor, derived (DCF output) |
| Hot stocks (`/api/hotstocks`) | the daily scan snapshot → FMP / yfinance / SEC EDGAR | derived (z-scores, 1–100 rank) |
| Valquo Index (`/api/valquo-index`) | the **same** snapshot, top-sliced | derived |
| Index forward track (`/api/index-track`) | Valquo's own recorded series (+ ingested Cowork tracker) | Valquo's own record |
| Signals (`/api/signals`, `/api/options-alerts`) | Tradier quotes + option chains (yfinance delayed fallback) | live vendor, derived (scores, sizing) |
| Options scorecard (`/api/options-scorecard`) | Valquo's own `option_alerts` table | Valquo's own record |
| Options paper (`/api/options-paper`) | Valquo's own alert table vs a hard-coded backtest constant | Valquo's own record + derived constant |
| Regime (`/api/regime`) | 10Y yield, VIX, S&P vs 200-day | live public market data |
| `/api/whatdo` | stored state only; recomputes nothing | derived |
| Edge Lab (`/api/edge/*`) | **Sharadar/WRDS exports** | **derived only** — walk-forward folds, ICs, Sharpes, row counts. No vendor rows. Owner-only before this change; now private-gated as well. |

Two honest notes, since the brief asked for the distinction rather than an assumption:

- **Derived vs raw.** The screener's factor weights in `screener/settings.py` are committed
  constants *measured on* the Sharadar panel, and `options_paper.py` compares against a
  hard-coded expectancy figure derived from the ThetaData panel. These are statistics computed
  from licensed data, not the licensed data — the ordinary output of research, and the category
  the vendors sell the data to produce. Worth knowing they exist; not a redistribution of rows.
- **ThetaData appears in `valuation/edge/options_*` only as research modules and comments.** No
  web route imports a ThetaData provider. The live options path is Tradier.
- **The new `data_export/` backup** contains Valquo's own paper record — Tradier *sandbox*
  marks, timestamps and computed P&L. No Sharadar and no ThetaData content. A test scans the
  written files for credential-shaped strings on every run.

## 4. Framing copy

The visible surfaces under private mode are the holding page, the login page and the dashboard.
The holding page says what this is in two sentences and offers a login. The dashboard header
carries a standing line — *"Private research tool — personal use only. Vendor data under
individual licences; not for redistribution"* — which is not a disclaimer for anyone else's
benefit (there is nobody else) but a reminder that makes "share a screenshot of the hot list" a
decision rather than a reflex. "Send feedback" is gone; it addresses a user of a service.
`/terms` and `/privacy` are kept and marked **Not in force**, which is more honest than leaving
a service agreement sitting on an instance with no users. **The "educational only, not
investment advice" disclaimers are untouched** — they still apply to Don.

## 5. The crons still run

All six admin routes reach `_admin_ok` unchanged, verified end-to-end and pinned by a test that
uses a **wrong** token deliberately — a correct one would actually run a market scan, a broker
cycle or a Discord post. The discriminator is which layer refused: private mode answers
`{"private_mode": true}`, `_admin_ok` answers `{"error": "unauthorized"}`. Seeing the latter
proves the request got through. Covered: `run-scan`, `run-intraday`, `run-paper-track`,
`post-recap`, `ingest-snapshot`, `ingest-index-track`, `export-track`, `option-alerts/*`.

They were never at risk of a session wall — they authenticate with a token and no cookie — but
"never at risk" is exactly the assumption worth testing before locking the front door.

## 6. Track backup — the irreplaceable dataset

Everything else here can be rebuilt: the panel re-reads Sharadar, the backtest re-runs, the hot
list re-scans. **The forward track cannot.** It records what the model said on days that have
already happened, and its whole value is that nobody could have seen the outcome first.
Recreating it later from current data would produce a different object with the same column
names — worse than losing it, because it would look fine.

It lives in one place: the SQLite DB on the Render service's persistent disk.

**The delivery problem, and why it is solved this way.** Render cannot commit to git and GitHub
Actions cannot read Render's disk. So the backup crosses the gap over HTTP: the service exposes
`/admin/export-track` (admin token, pure read), and a new **weekly `track-backup` workflow**
pulls it, renders the files, and commits them. Committed means it is in git history *and* on
Don's machine after a `git pull`.

Written to `data_export/`: `paper_track_history.json` (the complete artifact),
`paper_track_index.csv` (daily Index vs SPY), `paper_track_trades.csv` (every trade, entry →
exit → P&L), `paper_track_holdings.csv`, and a README so a CSV found in this repo years from now
is not a mystery. Three CSVs rather than the one the brief suggested, because merging a daily
return series with per-contract trades needs a `record_type` column and a union of ~30 mostly-
null columns — unreadable in a spreadsheet, which is the only reason to have CSV here. The JSON
is the complete artifact.

Design points worth knowing:

- **Both forward records are captured** — the Tradier sandbox book *and* the ingested Cowork
  tracker series. Backing up only the one the hero happens to lead with would silently lose the
  other.
- **Rewrite-in-full, not append-only.** Append-only preserves a corrupted row forever; the
  database is the source of truth. Output is deterministic (stable sort, fixed float precision)
  so a quiet week produces no diff and a real change produces a readable one.
- **The workflow refuses to shrink.** The failure that would actually destroy the record is the
  service coming up on a fresh disk and a well-behaved backup faithfully committing nothing over
  months of history. If the new export has fewer index days than the committed one, the job
  fails loudly instead of committing. `curl -fsS` so an HTTP error fails the step rather than
  committing `{"error":"unauthorized"}` over a good backup. Failure posts to Discord.
- **Stored raw-ish, not summarised.** Column names match the table columns exactly, so it can be
  re-inserted. A summary cannot be un-summarised.
- **Committed empty as a placeholder.** This machine's dev database holds synthetic fixture rows,
  and a file whose entire job is to be the real record must not ship with fake data in it.

**How Don gets it locally:** `git pull`, then look in `data_export/`. To make one on demand:
`python -m valuation.edge.track_export`. To pull the live one by hand, run the workflow from the
Actions tab (`workflow_dispatch`) — worth doing **before** ever touching the Render service.

## Verification

`tests/test_private.py` — **22 new tests**. Beyond them, the lockdown was exercised end-to-end
through the real SaaS app against real databases: 21 gated paths anonymous, 3 signed-in as a
non-owner, 7 as the owner, the six cron routes, both billing routes, and `/demo`.

`tests/test_saas.py` and `tests/test_security.py` now set `private_mode = False` at module
level. That is not a workaround — those suites are what prove the **public** product still
works, which is exactly what `PRIVATE_MODE=false` promises to restore. If every suite ran in
private mode, "flipping the flag back brings the product back" would be an untested claim.
Between the three files, both sides of the flag are covered.

## Reversing this — when Valquo goes commercial

One setting, in this order:

1. Get the licences the commercial posture needs: **ThetaData Business** (~$1,600/mo vs
   Individual) and a Sharadar plan permitting redistribution. This is the actual constraint —
   the flag is downstream of it.
2. Set `PRIVATE_MODE=false` on Render (it is already in `render.yaml`).
3. Choose the public posture with the flags that were always there: `OPEN_ACCESS=true` for free
   and open, or `OPEN_ACCESS=false` for the paid, signup-required product. `FEATURE_BILLING=on`
   forces the pricing surfaces regardless.
4. Stripe keys were left configured, so no secrets need re-entering.
5. Optionally re-enable `/demo` by setting `DEMO_ACCESS_TOKEN`.

Nothing was deleted and nothing needs rebuilding. `tests/test_saas.py` and
`tests/test_security.py` are the regression suite for that restored product.

## Honest limits

- **Verified through the app, not a browser.** Real requests against real Flask and real
  databases — which catches routing, gating and status codes, but not "does the holding page
  look right on a phone". Worth a two-minute eyeball after deploy.
- **The backup has not yet run against Render.** The endpoint, the renderer and the shrink-guard
  are all tested locally, but the first real pull happens on the first workflow run (or a manual
  `workflow_dispatch`). **Do that once by hand before trusting it** — it needs `SITE_BASE_URL`
  and `ADMIN_TOKEN` as Actions secrets, which the auto-scan workflow already uses, so there is
  most likely nothing to add.
- **This is the first workflow in the repo that commits to `main`.** That is what "backed up in
  git history" requires, but it is a real change in how the repo operates and Don should know it.
- **The lockdown is an application-layer boundary.** Anyone with the `ADMIN_TOKEN`, the Render
  dashboard or the database file still has everything. That is the right scope for a licence
  posture; it is not a threat model against a determined attacker.
- **Carried forward, still outside my access:** `DISCORD_WEBHOOK_URL` on Render (Session 7);
  `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID` on Render (Session 6) — until those are set
  the paper track does not run, and a backup of an empty track is what it is.
- **Still awaiting a decision from Session 8:** the ~70 lines of dead custom-backtest JS.

---

# Session 8 — 2026-08-03 — Phase 9 UX round 2 (PROMPT_appfixer_phase9.md)

All four items in the prompt shipped, one commit each, all suites green. Nothing in this
session touches the options backtest, the fundamental panel or the miner.

## 1. "Why this score" — the hot score is no longer a black box

Every row in the Hot Stocks table now has a **"why?"** button. It opens a panel showing which
themes produced that name's 1–100: a diverging bar per theme (right = pushed the score up,
left = held it back), the size of each push, and each theme's share of everything that moved
the name. Plain-English labels, so "capital_discipline" reads as "Capital discipline — not
issuing shares to fund itself".

**The important part is that the explanation IS the score, not a story told next to it.**
`valuation/screener/attribution.py::decompose()` returns the composite *and* its per-theme
pieces from one calculation, and the scan's `_composites()` now delegates to it. The pieces
sum to the composite exactly, and a test asserts that on every scored row. A second test
recomputes the composite the old way, directly from `composite_score`, under both bucketing
modes, to prove the ranking itself did not move.

The old per-pick "why" was wrong in a way nobody would have noticed: it multiplied the stored
weight by the theme value *before* the second standardization, using whichever weight set the
hard bucket named. It ordered the themes roughly right, so it looked fine — but its numbers
added up to nothing in particular, and under soft bucketing it credited a weight set the name
was only partly scored under.

**Computed at scan time, deliberately.** `value` is scored on two different input sets
(earnings-based for profitable names, sales-based for loss-makers) and soft bucketing blends
both, so the single blended `value` column in a saved snapshot cannot be split back apart
afterwards. Re-deriving the attribution at read time would also explain the score using
whatever weights the learner has adopted *since*, not the ones the scan ranked on.

**Consequence for Don: the panel is blank until the next daily scan runs.** Rows saved by an
older scan say so ("it is written at scan time … it appears after the next daily scan")
rather than showing an approximation. One scan fixes it; no action needed.

Honesty constraints baked in: contributions are in composite units (standard deviations
versus that day's scan), **not** points of the 1–100, because the score is a percentile *rank*
of the composite — monotone but not linear. And shares are of the **absolute** push, so a name
whose themes nearly cancel can't produce shares in the hundreds of percent.

**Bug found along the way:** `.pos` and `.neg` had **never been defined in any stylesheet**,
while app.js applies them in about fifteen places — fair-value upside, track-record alpha,
paper P&L, the why-chips. Every one has been rendering as plain body text, so a −18% and a
+18% looked identical at a glance. Defined once; all of them are now green/red.

## 2. The live forward track leads the page

The one number in this product that nobody could have fitted was three clicks deep, inside the
Index tab, underneath a backtest. There is now a **band above every tab**: Valquo Index vs SPY
since inception, the excess, the day count, the paper options book's live/closed counts, and a
shared-axis sparkline.

**It is server-rendered**, so it is in the HTML the browser receives — no spinner, no layout
shift, no round trip before the most important evidence on the page appears. It is a Jinja
*callable* in the shared context processor rather than a value, so the renders that don't show
it (landing, pricing, error pages) don't pay for its database reads, and a failure returns the
not-started shape instead of 500-ing a page that would otherwise have been fine.

Leading is not boasting. The gates live in `valuation/web/hero.py`, not the template:

- **Paper, always**, labelled with its inception date — and the label comes from the track
  modules themselves (`paper_track._label`, `index_track.summarize`), so the hero cannot grade
  the track more generously than `/api/track` does.
- **Thin until the owning module says otherwise.** While thin the band turns amber, carries a
  "too early to judge" pill, and `may_lead` is False. A week of noise gets shown, not
  celebrated.
- **An expectancy below the 30-closed floor is withheld, not printed small** — a printed number
  gets quoted, a withheld one gets read. One closed winner shows "needs 30 closed".
- **No data means no band for a visitor.** A backtested curve under a "live" heading would be
  the most dishonest thing this page could show, and a "coming soon" strip is clutter. *You*
  (owner) see a muted "not started" line, so a track that quietly stops stays visible to the
  person who can fix it.

Two forward records exist — the ingested Cowork tracker and the Tradier sandbox book. The hero
prefers the one the Index tab leads with, falls back to the other, and **names which it drew**;
an unlabelled fallback would silently swap the meaning of the number between deploys. The
fractions-vs-percent difference between the two is pinned by a test.

Verified by rendering the real template in four states — thin, mature, no-data-visitor,
no-data-owner — 12 assertions, all passing.

## 3. Stock + options in one "what this tool does with this name" view

New card under the valuation hero, on the Single tab. For whatever ticker you just valued it
shows: rank in today's scan, whether the Valquo Index holds it and at what weight, whether the
paper account is in it, any scream-buy options alert with whole-contract sizing, and the same
"why this score" bars from item 1. The opportunity score, the alert and the tracked outcome
used to live on three tabs that never met.

`/api/whatdo` is a **read over stored state** — snapshot, constructed book, logged alerts,
paper positions. It recomputes nothing: every figure comes back from the module that owns it,
so the panel cannot disagree with the tab it summarizes, and it needs no network call. It is
fired *after* the valuation paints and never awaited, so a slow or broken response cannot
delay or break the page it decorates.

Each honesty rule is pinned by a test:

- **Never a per-ticker hit rate.** One name yields a handful of trades at most, so it reads
  "1 of 1 won (too few trades on one name to read as a rate)" — a count, never a percentage.
  The convexity line (~37% backtested hit rate, convex not likely) rides along with every
  options figure.
- **Whole contracts, and zero is a real answer.** A $25 premium against a $1,000 risk budget
  sizes to none, not to one: "one contract costs more than the risk budget — the honest size
  is zero, not one".
- **An absent name is absent, not bad** — "the screen covers a defined universe, so being
  absent says nothing about the company", with no score or rank invented for it.
- **Withheld ≠ empty.** The free tier does not read the options record, so it must not report
  an empty one; it says the contract is part of Signals, and still carries the convexity
  caveat. (Gating: the ranking half is public — it is the same ranking the Hot tab serves —
  while the specific contract follows the existing Signals feature flag.)
- **The action lines describe what the model is doing**, never what you should do, asserted
  against a list of recommendation phrasings.

## 4. Perceived speed + mobile

Hot, Index and Track read a snapshot that changes once a day, so waiting on the network before
painting anything meant staring at a spinner for data the browser already had. They now paint
the **last good copy immediately** and replace it when the fetch lands. A genuinely first visit
gets a **table-shaped skeleton**, so the real table arrives without the page jumping.

Two rules keep the cache from becoming a lie — the second was a bug in my own first version:

- A cached paint is **labelled** ("showing your last copy, loaded 3 hours ago — refreshing…"),
  and if the refresh fails the error says the ranking above is a saved copy, not a fresh one.
- The freshness verdict **inside** a cached payload was computed when it was cached, so a copy
  saved yesterday still said "ranking from today" — exactly the lie the freshness banner was
  built to prevent. It is now suppressed until the live fetch replaces it.

The cache hard-expires at 36 hours, and degrades to nothing under private mode, quota errors
or a corrupted entry (all three exercised).

Mobile: the hot table's min-width goes 560 → 620 now that it carries the "why?" column, or the
columns crush instead of scrolling; the attribution panel is stopped from inheriting that
minimum (it lives *inside* the scrolling table and would otherwise scroll sideways with the
row that opened it); the unified card stacks rather than squeezing four stats across a phone;
the hero sparkline goes full-width under the numbers. Skeletons honour
`prefers-reduced-motion`.

## A finding for Don to decide on

A new static wiring check (app.js writing to an element id that does not exist in the template
fails **silently** — the write lands on nothing and the panel just stays blank) surfaced
pre-existing dead code: the custom-backtest UI block in app.js — `runBacktest`,
`renderBacktest`, `eqChart`, `qChart`, `renderBtStats`, ~70 lines — references a form
(`btSource`, `btTickers`, `btLoader`, …) that is **no longer in index.html**, and nothing calls
it. The `/api/backtest/run` endpoint behind it is still live and still gated as a paid feature.

It is dead, not broken. I left it in place — deleting it is your call, not a UX round's — but
it is allowlisted in the test so it cannot grow, while the new surfaces are asserted by name.
**Say the word and I'll remove it**, or re-wire a UI for it if the feature is wanted back.

## Files changed

| File | What |
|---|---|
| `valuation/screener/attribution.py` | **new** — exact decomposition of the composite into per-theme contributions |
| `valuation/screener/screen.py` | `_composites` delegates to it; rows carry the real `why` + `why_composite` |
| `valuation/web/unified.py` | **new** — the per-name joined view (`name_view`) |
| `valuation/web/hero.py` | **new** — the live-track hero band, with its honesty gates |
| `valuation/web/app.py` | `/api/whatdo`; `live_hero` in the shared template context |
| `valuation/saas/app_saas.py` | per-tier `g.may_see_options` for the options half of the name view |
| `valuation/web/templates/index.html` | hero band, unified card, cache slots |
| `valuation/web/static/app.js` | attribution panel, unified view, skeletons, last-good cache |
| `valuation/web/static/style.css` | attribution bars, hero band, skeletons, cache bars, `.pos`/`.neg`, mobile |
| `tests/test_screener.py` | 51 → 63 (attribution sums, ranking unchanged, name-view honesty) |
| `tests/test_paper_track.py` | 34 → 40 (hero gates) |
| `tests/test_saas.py` | 28 → 30 (static UI wiring) |

## Verification

Every suite green: **edge 142, screener 63, saas 30, paper-track 40, intraday 18, engine 28,
bulk 14, security 22, sector-neutral 6, PEAD 12, calibration 23, EV-multiples 34, freeze 13,
lazy-prices 28, lazy-prices-IC 24, options-greeks 21.**

Beyond the unit tests: `/api/whatdo` exercised end-to-end through the real SaaS app against the
real screener DB (including the no-ticker 400 and an unknown ticker); `index.html` rendered
through the real Jinja environment in four hero states; the JS render helpers and the cache
exercised under a DOM shim in Node (expiry, corruption, blocked storage).

## Honest limits

- **The attribution panel is empty until the next daily scan.** By design — see item 1.
- **The hero shows nothing to visitors until the forward track reports.** It is currently
  gated on the same thing everything else is: the paper track actually running on Render,
  which still depends on `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID` being set there
  (Session 6's outstanding item) and `DISCORD_WEBHOOK_URL` for the recaps (Session 7's).
- **None of this was opened in a real browser.** It is verified by rendering the template, the
  JS helpers under a DOM shim, and static wiring checks — which catches typos, dead ids and
  wrong numbers, but not "does the band look right on an iPhone". Worth a two-minute eyeball
  after deploy.
- The per-name options record is genuinely thin and will stay thin for months. That is the
  point of the labels, not a defect to fix.

---

# Session 7 — 2026-08-03 — Daily + weekly Discord recap of the paper track (PROMPT_appfixer_discord_recap.md)

## What Don gets

Two automated Discord posts about the forward paper track, both server-side, both running with
his computer off:

- **Mon–Thu, ~5 min after the paper-track cycle** — a short daily: options open / opened today /
  closed today with each trade's P&L, expectancy to date against the backtest reference, then
  Index vs SPY for the session and since inception, holdings count and any additions.
- **Friday, same slot** — a fuller weekly: the week's closed trades and P&L for both books, hit
  rate and expectancy to date, best/worst trade, the index cumulative, and a health line.

**Friday posts the weekly INSTEAD of the daily, not as well as.** The weekly is a superset;
firing both a minute apart would just train him to skim past them. Every weekday still gets
exactly one post.

## The one thing Don must do

**Set `DISCORD_WEBHOOK_URL` on RENDER** (Dashboard → valuation-tool → Environment). It is now
declared in `render.yaml` with `sync: false`, so it appears as a blank to fill in.

This is *not* the same as the GitHub Actions secret of the same name. The Actions secret feeds
the scan-failure alert and the watchdog, which run on the runner. The recaps post from inside
the web service, so they read Render's copy. Until it is set the endpoint returns
`posted: false` with a reason and the Actions job emits a **warning, not a failure** — a
missing optional notification must not turn the pipeline red.

Same standing item as the last two sessions, now with a second reason to do it.

## The cron entries

| where | when (UTC) | posts |
|---|---|---|
| `auto-scan.yml` job `recap` | `58 20` **and** `58 21`, Mon–Thu | daily |
| `auto-scan.yml` job `recap` | `59 20` **and** `59 21`, Fri | weekly |
| `render.yaml` cron `paper-recap-daily` | `58 21`, Mon–Thu | daily |
| `render.yaml` cron `paper-recap-weekly` | `59 21`, Fri | weekly |

Two Actions crons per kind for the same DST reason as the paper track: a crontab cannot say
"after the 4pm Eastern close", so one entry is correct under EDT and the other under EST, and
`/admin/post-recap` applies the same `market_session` guard the paper track uses. Render gets a
single entry each at 21:5x UTC, which is after the close in both regimes.

Both land ~11–13 minutes behind the paper-track cron, so the recap describes a **finished**
cycle rather than the previous day's.

Manual run: Actions → "Auto scans" → Run workflow → kind `recap-daily` or `recap-weekly`.

## How it stays honest

The prompt's honesty rules are enforced in code and pinned by tests, not left to the wording:

- Every post carries `paper (Tradier sandbox), since <date>` and the `thin` flag **taken from
  `paper_track._label`** — the same string `/api/track` serves. The recap cannot grade the
  track more generously than the product does.
- **No closed trades → "No closed trades yet".** An empty scorecard printed as `0% hit rate,
  $0 expectancy` is not neutral; it looks like a measured result. Test:
  `test_recap_says_no_closed_trades_rather_than_reporting_zeros`.
- **A hit RATE is only quoted once the sample can carry one.** Below the 30-trade floor it
  reads `1 of 1 won (too few to read as a rate)`. "hit rate 100%" off a single winner was the
  most flattering untrue number available and is now impossible.
- Options are always framed as **convex** — "the backtest hits 37% of the time, most trades
  lose a little and a few win big" — so the hit rate can never be read as a win rate.
- The backtest is quoted as a **reference point, not a target and not a promise**: +10.4%/trade
  full-sample and +4.4% in the recent half, both shown, so the fade is visible.
- Every post ends with "Educational only, not investment advice" and the sandbox/delayed-quote
  caveat.

## Two bugs I fixed in my own first version

1. **Discord truncates at 1900 characters — from the END, where every caveat lives.** A busy
   day with six closed trades would have silently dropped "educational only, not investment
   advice" off the bottom. `_fit()` now trims the per-trade DETAIL lines instead, oldest first,
   leaves a visible "…detail trimmed" marker, and never touches the last lines. Pinned by
   `test_fit_drops_detail_not_caveats_and_says_that_it_did`.
2. **The health line cried wolf on a new track.** It counts recorded sessions against trading
   days in the window; a track that started yesterday reported "1/5 sessions" and warned about
   a hole every day of its first week. It now only counts sessions on or after inception. A
   watchdog that is wrong exactly when you are watching it teaches you to ignore it.

## It reads; it does not recompute

`recap.py` derives no P&L, expectancy or return of its own. It reads
`options_tracker.scorecard`, the `pnl_pct`/`pnl_dollars` that `record_outcome` already stored,
and `paper_track.index_summary`. `test_recap_prints_the_tracked_pnl_rather_than_recomputing_it`
writes a deliberately odd P&L straight into the table and asserts the post shows *that* number
— so a future divergence between the Discord post and the API fails the suite instead of
shipping. The one exception is documented: a trade closed with no entry premium is unscoreable,
so the recap falls back to the stored premiums rather than dropping the trade from the book.

## Idempotency

`post()` marks the day in the same `alerts_sent` table the scream-buy de-dupe uses, keyed
`__RECAP_DAILY__` / `__RECAP_WEEKLY__`. The two DST crons, the Render cron and any manual re-run
therefore produce exactly one post per kind per day. **A failed post is deliberately NOT
marked**, so a Discord outage at 20:58 is retried by the 21:58 cron rather than burning the
day's only slot on a message nobody received.

## Changed

- **NEW `valuation/saas/recap.py`** — collect / format / post, with the honesty rules in the
  module docstring.
- `valuation/saas/app_saas.py` — new `/admin/post-recap` (X-Admin-Token, validates `kind`,
  applies the market-session guard, returns 200 with a reason on every non-post path).
- `.github/workflows/auto-scan.yml` — four crons + the `recap` job + two dispatch options.
- `render.yaml` — `DISCORD_WEBHOOK_URL` declared on the web service; two recap crons.
- `ENV_REFERENCE.md` — says explicitly that the webhook must be on Render, and why.
- Tests: `tests/test_paper_track.py` 22 → **34**, `tests/test_saas.py` 27 → **28**.

## Verified

All seven suites green: **edge 142, screener 51, saas 28, intraday 18, engine 28, bulk 14,
paper-track 34.**

Beyond the unit tests I ran the real Flask route against the real screener database with a
local HTTP sink standing in for Discord: `POST /admin/post-recap` returned
`{"posted": true, "chars": 621}`, the sink received exactly one payload ending in the
disclaimer, and an immediate second POST returned `{"posted": false, "duplicate": true}`
without sending anything. I also eyeballed both posts rendered against a synthetic book with a
winning trade, an open position and two index sessions. The de-dupe row that run left in the
local dev DB has been deleted.

## Honest limits

- **The recaps will say "not started" until the paper track has actually run on Render.** The
  local database has no paper book, and production still needs `TRADIER_PAPER_TOKEN` /
  `TRADIER_PAPER_ACCOUNT_ID` confirmed (Session 6's open item). The recap infrastructure is
  correct and tested either way, but the first real post is gated on that.
- The options scorecard it quotes is `options_tracker.scorecard`, which counts **every** closed
  alert — including any the external Cowork/Robinhood filler closes, not only paper ones. That
  is the existing project-wide definition and `/api/track` already reports it that way; I did
  not fork a second definition just for Discord.
- Index holdings only ever get **added** (`seed_book` never drops a name), so "holdings changes"
  means additions. The post says "added today" rather than implying rotation.

---

# Session 6 — 2026-08-03 — Paper schedule confirmed + the landing now SHOWS (PROMPT_appfixer_landing.md)

## 1. Is the paper track actually scheduled? YES — here is exactly where

| where | when (UTC) | what it does |
|---|---|---|
| `.github/workflows/auto-scan.yml`, job `paper` | `47 20` **and** `47 21`, Mon–Fri | POSTs `/admin/run-paper-track` with `X-Admin-Token` |
| `render.yaml`, cron `paper-track` | `45 21`, Mon–Fri | same endpoint, same token |

Both are on `main`, which is what matters — GitHub only registers cron schedules from the
default branch. Two Actions crons because a crontab cannot express "4pm Eastern": one is
correct under EDT, the other under EST, and the endpoint's session guard turns the early one
into a no-op. The endpoint is deployed and token-gated in production right now (an
unauthenticated POST returns **401**).

**What I still cannot verify from here, and it is the one remaining risk:** whether Render
actually holds `TRADIER_PAPER_TOKEN` / `TRADIER_PAPER_ACCOUNT_ID`. `ADMIN_TOKEN` is not in the
local `.env`, so I cannot call the production admin route, and the endpoint fails closed — a
401 looks identical whether the token is wrong or the paper creds are missing. The local creds
authenticate fine (sandbox account VA35863695).

**One-click check for Don:** Actions → "Auto scans" → Run workflow → kind `paper`, `force`
true. The step now **fails loudly** with an explicit message if the Render credentials are
missing, instead of treating any 200 as success.

**New this session — the watchdog now covers the paper track too.** `scripts/check_staleness.py`
also reads `/api/index-track` and alerts if the track has stopped recording points. It
deliberately stays quiet before the first point (`available: false` is the correct state today,
and alerting on it would train the reader to ignore the channel — which is how the July outage
went unnoticed for four days). Verified against production just now:

```
  hot list: 2026-07-29 (2 trading days old), 154 scored
  paper track: not started yet (no live points) — not an alert
🔴 Valquo data pipeline problem
• the last scan only scored 154 names — the universe has collapsed
```

That hot-list line is last session's outage, still unfixed in production because the first
scheduled run under the fix had not happened yet — **Monday 2026-08-03 22:23 UTC is the test.**

## 2. The landing page now shows the product instead of describing it

Everything is **server-rendered from the store** (`valuation/web/showcase.py`), so the page
paints in one pass with no client fetch and no empty-then-populated flash on the first thing a
visitor ever sees.

**A real sample valuation in the hero.** Not a mock-up — a genuine run of the real engine on
real filings, stamped with the date it ran. Today's AAPL sample renders:

> **$308.91 → $119.65   −61.3%** · Opportunity score **51/100 · Hold · high confidence**
> Bear $99 · base $120 · bull $145, with today's price pinned past the end of the bar and
> labelled *"Today's price is above even the bull case."*
> *"To justify $308.91 you have to believe revenue compounds at **40% a year**. The model's
> base case is **6%**. That is the question, not the price."*

That the flagship demo says a mega-cap is 61% overvalued is the point — it shows the tool will
tell you something you did not want to hear.

**Why it is cached rather than computed per visit:** a full valuation is a multi-second,
network-heavy job. Running it inside the landing request would make every first-time visitor
wait, on the box least able to afford it — the exact opposite of demonstrating the product in
two seconds. CI already has the RAM and the network, so `ci_scan.py` computes it after each hot
scan and POSTs it to the new token-gated `/admin/ingest-sample`. That refresh is **non-fatal**:
the ranking is the product, a stale hero is cosmetic, and failing the job over it would turn a
cosmetic miss into a red run and a Discord alert that teaches people to ignore alerts.

**The forward track is a hero element, directly under the fold.** An inline SVG of Index vs S&P
500 on a **shared** y-axis (drawing each line to its own scale would make a line that lost look
like it won). Inline SVG rather than a chart library because the page must paint immediately
and the site's CSP blocks external scripts anyway.

The honesty rules are enforced by the same `index_track.summarize()` the Index tab uses, so the
landing can never disagree with the page it links to:
- Under 60 trading days it is badged **`paper · thin`** and says *"Far too short to mean
  anything yet — shown because hiding it until it looks good is how track records lie."*
- Past that it becomes **`paper · live`** and the caveat drops. Verified both states in a
  browser by seeding a 70-day series, then restoring the real data.
- With **no live points at all** — today's real state — it shows `not started`, states plainly
  that there is no live curve, and labels the backtested figures as *"a different and weaker
  kind of evidence"*. It never draws a backtested curve under a "live" heading.

**Copy tightened** from a paragraph to three scannable value-props. The beta banner,
"educational only, not investment advice", the footer disclaimer and the per-card "a model
output — an estimate, not a price target or advice" all stay.

**Fixed a pre-existing mobile bug while I was in there.** The three value-prop cards were a
hard-coded `repeat(3,1fr)` grid with no breakpoint, so at 390px the page ran **493px wide** and
each card became roughly one word per line. Now single-column below 860px; verified
`scrollWidth == 390`.

Verified by running the app and driving it in Chromium at 1280px and 390px — no console errors,
no horizontal overflow, screenshots read at both sizes and in both track states.

## Changed

- **NEW `valuation/web/showcase.py`** — cached sample, `range_bar()`, `sparkline()`,
  `landing_context()`. Every block independently optional.
- `valuation/web/templates/landing.html` — rebuilt.
- `valuation/saas/app_saas.py` — landing route passes the showcase context (and **logs** rather
  than silently swallowing a failure); new `/admin/ingest-sample`.
- `scripts/ci_scan.py` — refreshes the landing sample after the hot scan, non-fatally.
- `scripts/check_staleness.py` — watches the paper track.
- Tests: screener 47 → 50, saas 24 → 27.

## Caveats

- The sample is only as fresh as the last successful hot scan — and the hot scan has been down
  since 07-29. Until Monday's run lands there will be **no sample on production** and the
  landing falls back to the static value-props. That fallback is tested, but it means the new
  hero will not appear until the scan recovers.
- `SAMPLE_TICKER` env var overrides AAPL if you ever want a different demo name.
- The sample carries an `as_of` date and is labelled "not refreshed since" past 7 days rather
  than hidden — an old real valuation beats an empty hero, but it must not read as live.
- I did not touch the paper-track lane's files, the options backtest, the panel or the miner.

---

# Session 5 — 2026-08-02 — Paper track verified + scheduled server-side (PROMPT_appfixer_paper_schedule.md)

## READ THIS FIRST: the hot scan has been dead since 2026-07-29, and it is not the paper track

The live site is serving a **four-day-old hot list**. Verified against production just now:

| feed | as of | state |
|---|---|---|
| `/api/hotstocks` | **2026-07-29** | **stale (3 trading days), 154 scored, 191-name universe** |
| `/api/signals` (intraday) | 2026-07-31 | fresh — last run Fri 21:41, correct for a Sunday |
| `/api/index-track` | — | no live series yet (`available: false`) |

Intraday being **fresh** while hot is stale is the useful part: it rules out the boring
explanations. Actions minutes are not exhausted (intraday is the minute-hungry job and it is
running), the schedule is firing, Render is up, and the secrets exist.

**Diagnosis — the FMP lapse killed the hot scan on 07-30 and nothing announced it.** The
workflow was last edited 2026-07-25 and the last code change before today was 07-28, so on
07-30 and 07-31 the hot job ran *the same code that succeeded on 07-29* and failed. What
changed underneath it was FMP: session 2 established the subscription lapsed around 07-29
(FCX/ELV/MU are present in the 07-29 snapshot and 402 now). Under the **old** provider code a
402 made `get_metrics` return `None`, so every name was dropped, the scan produced zero rows,
and `/admin/ingest-snapshot` rejected the empty post with a 400. Red run, nothing ingested,
no notification. Intraday was untouched because it runs on Tradier, not FMP.

**It is already fixed — the fix just has not had a scheduled run yet.** Session 2's free-stack
fallback + circuit breaker and session 4's broker fundamentals both landed on main *today*
(16:30 and later). The first hot run under the fix is **Monday 2026-08-03, 22:23 UTC**. If
`/api/hotstocks` still says 07-29 on Tuesday morning, that hypothesis is wrong and the Actions
log is the next place to look — I could not read it from here (no `gh`, no GitHub token).

**One thing to actually do: set `DISCORD_WEBHOOK_URL` as an Actions secret.** The watchdog and
the scan-failure alert are both wired and both inert without it. A four-day outage that only
manifests as a red run in a tab nobody opens is exactly what it exists to prevent — and this
is now the second time.

## 1. Sandbox connection — verified, output verbatim

```
$ python scripts/paper_track_run.py --health
Tradier SANDBOX https://sandbox.tradier.com/v1  account VA35863695  ok
  paper equity $199,256.75  cash $199,256.75
```

```
$ python scripts/paper_track_run.py --dry-run
Tradier SANDBOX https://sandbox.tradier.com/v1  account VA35863695  ok
  paper equity $199,256.75  cash $199,256.75
  DRY RUN — orders are previewed at the broker, nothing is placed.
Options: 0 submitted, 0 skipped, 0 rejected | 0 newly filled, 0 marked | 0 closed (0 written to the scorecard)
Index: 0 held, 0 added (quote-marked)
  no point written: no index holdings seeded yet
```

**That dry run proves almost nothing, and I did not stop there.** Every number is zero because
the local database is a test fixture — `option_alerts: 0 rows`, one snapshot row, scan date
`2099-01-01`, and a `data/valquo_index.json` whose only holding is a fake ticker `TESTX` that
cannot be quoted. A clean exit with no work done is not a working order path.

So I exercised the real path against the sandbox with real symbols and a throwaway database:

- **equity quotes** — AAPL 308.91, MSFT 464.72, SPY 747.03
- **option chain** — 466 contracts for AAPL, 233 calls with a two-sided market
- **option quote by OCC symbol** — `AAPL261016C00360000` bid 1.97 / ask 2.25
- **option order PREVIEW** — `status: ok, result: true, commission 0.35` (nothing placed)
- **equity order PREVIEW** — `status: ok, result: true, cost 1.00` (nothing placed)
- **index seed + mark** — 2 positions added, 2/2 priced, `index_point` ok against SPY

So the broker, the quote path, the order path and the index mark all work. The zeros were the
fixture, not the plumbing.

## 2. The schedule — and the DST bug I found in it

The paper job already existed (landed in `cde1579` by the paper-track lane): a GitHub Actions
job at `47 20 * * 1-5` and a Render cron at `45 20 * * 1-5`. **Both were wrong for half the
year.**

A crontab cannot express "4pm Eastern". `20:45 UTC` is 4:45pm ET under EDT — but under **EST
it is 3:45pm ET, fifteen minutes BEFORE the close.** From the first weekend in November the
cycle would have started running mid-session every weekday: entering option positions and
marking the index book against *intraday* prices instead of closing prices. Nothing would
error. Every run would have looked completely normal. And the one record whose entire value is
being a clean out-of-sample forward track would have quietly stopped meaning what it says.

Fixed in three places:

1. **NEW `valuation/screener/market_session.py`** — `session_state()` answers "has today's
   session actually closed?" in real Eastern time, including weekends and market holidays
   (holidays are **computed**, not listed, so this does not expire in a year — Good Friday via
   the Easter algorithm, the floating Mondays, and the weekend-observed rule). Verified
   against the published NYSE calendars for 2024 and 2025: **exact match, both years.** There
   is a 15-minute settle after the bell so a mark cannot catch a half-formed close.
2. **The endpoint guards itself** — `/admin/run-paper-track` returns `{"skipped": true,
   "session": {...}}` and does nothing if the session has not closed. This is the part that
   matters: the guard is unit-tested, a crontab is not.
3. **The crons fire generously and let the guard decide** — Actions now has **both**
   `47 20` and `47 21` UTC (one is correct in each DST regime, the other no-ops), and the
   Render cron moved `45 20` -> **`45 21` UTC**, which is after the close in *both* regimes
   (5:45pm EDT / 4:45pm EST) since there is only one entry there.

The workflow step now also distinguishes the three outcomes instead of treating any 200 as
success: a skip logs a notice, `configured: false` **fails the job loudly**, and a real run
says so. A skip every single day would mean the guard never opens, and that must not read
green. `workflow_dispatch` gained a `force` input so the job can be tested outside the window.

Double-running is safe by construction and always was — claim rows are `INSERT OR IGNORE` on
the alert id, and the day's index point is keyed by date.

## 3. What runs server-side (and what does not)

**Server-side, no laptop involved** — GitHub Actions (`auto-scan.yml`), all triggering
token-protected endpoints on Render:

| job | schedule (UTC) | status |
|---|---|---|
| hot list | `23 22` + `41 23` backup, weekdays | scheduled; **failing since 07-30**, fix landed today |
| intraday | `*/30 13-20`, weekdays | **working** — verified fresh 07-31 |
| paper track | `47 20` + `47 21`, weekdays | scheduled; endpoint live (401 without a token) |
| watchdog | `15 13`, weekdays | working; **inert without `DISCORD_WEBHOOK_URL`** |
| self-learning | `0 12 1 * *` monthly | scheduled |

`render.yaml` defines its own equivalent crons, but the Actions workflow is the live path
today (the blueprint's comment says to disable the workflow only once the paid blueprint is
in use). Both hitting the same idempotent endpoints is harmless.

**Still laptop-dependent:**
- **ThetaData miner** — expected and correct; it is a local gateway. Leave it.
- **The Sharadar backtest** (`fundamental_panel`) — licensed local data, run on demand. Not a
  live-product dependency.
- **`scripts/paper_track_run.py`** — the local path only. The scheduled path is the endpoint,
  deliberately: a CI runner gets an empty database and would lose the order state that makes
  the cycle idempotent.
- Nothing the live product serves depends on Don's machine being on.

## Secrets Don must set

| where | key | status |
|---|---|---|
| GitHub Actions | `DISCORD_WEBHOOK_URL` | **missing — please set.** Alerting is wired and inert without it |
| GitHub Actions | `SITE_BASE_URL`, `ADMIN_TOKEN` | already set (the scans reach Render) |
| Render env | `TRADIER_PAPER_TOKEN`, `TRADIER_PAPER_ACCOUNT_ID` | Don says set; **I could not verify from here** |

I could not confirm the Render paper credentials because `ADMIN_TOKEN` is not in the local
`.env`, so I cannot call the production admin endpoint. The local creds authenticate fine
(account VA35863695), but Render holds its own copy. **One-click check:** Actions -> "Auto
scans" -> Run workflow -> kind `paper`, `force` true. It fails loudly with an explicit message
if the Render credentials are missing, and otherwise runs one cycle.

## Changed

- **NEW `valuation/screener/market_session.py`** + 4 tests.
- `valuation/saas/app_saas.py` — session guard on `/admin/run-paper-track` (+ `force` escape).
- `.github/workflows/auto-scan.yml` — second paper cron, `force` dispatch input, outcome-aware
  step that fails on `configured: false`.
- `render.yaml` — paper cron `45 20` -> `45 21` UTC.
- Tests: screener 43 -> 47, saas 22 -> 24.

Did **not** touch `paper_track.py` / `paper_broker.py` (the paper lane's files), the options
backtest, the panel or the miner.

## Caveats

- The session guard uses `zoneinfo`, which needs system tzdata (present on Linux/Render and
  here). It falls back to naive UTC if unavailable, which would make it conservative in
  summer, not permissive.
- Holiday computation covers the ten scheduled NYSE closures. Ad-hoc closures (mourning,
  weather) are not predictable; the cost of a run on one is a single duplicate-priced mark.
- The paper track has **never completed a real scheduled run**. Everything above verifies the
  parts. The first end-to-end proof is Monday's cron.
- Sandbox quotes are delayed ~15 min (the broker's own `data_caveat`), so paper fills are
  close to, but not, what a live account would have received.

---

# Session 4 — 2026-08-02 — Broker fundamentals, the free route (PROMPT_broker_fundamentals.md)

## The verdict up front: NO, you do not need to pay for FMP

Tradier — which you already pay for — carries Morningstar fundamentals at
`beta/markets/fundamentals`, **100 symbols per call**. The whole 800-name universe now costs
about **24 calls** against a feed with no daily quota, versus FMP's ~2,400 metered per-name
calls. It covers market cap, enterprise value, the full valuation-ratio set, ROE, beta,
sector, and shares outstanding at **~99% of liquid names**.

What it does **not** carry is an income statement or a balance sheet. That is the honest
limit, and it is stated precisely in the gap table below.

**Recommendation: do not buy FMP Premium.** The one thing paid FMP would add that nothing free
covers is the growth theme, and there is a caveat on that below that matters more than the
price. If you ever do pay, the reason should be revenue growth, not "better data" generally.

## What is actually in the broker feed (measured, not assumed)

Measured on **200 liquid names, 2026-08-02**. Tradier returns a large envelope in which most
tables are null; I counted per-field fill rates rather than trusting the shape:

| Field | Broker source | Coverage |
|---|---|---|
| market cap, enterprise value, shares outstanding | `share_class_profile` | 99% |
| book value/share, P/S | `valuation_ratios` | 99% / 98.5% |
| P/B, P/E, EV/EBITDA | `valuation_ratios` | 91.5% / 88% / 83.5% |
| ROE, ROA, debt/equity | `operation_ratios` | 89.5% / 95.5% / 87.5% |
| beta (36/48/60-month) | `alpha_beta` | 99% |
| sector | `historical_asset_classification` | 99% |
| EPS (3M/9M/12M) | `earning_reports` | 98.5% |
| 13F + insider ownership tallies | `ownership_summary` | 99% |

**Null for every symbol, at every tier we can reach:** `financial_statements_restate`,
`segmentation`, `earning_reports_restate`, `historical_returns`, `operation_ratios_restate`,
`earning_ratios_restate`, `trailing_returns`, `asset_classification`.

Several absolutes are **derived** rather than reported — `revenue = mktcap / P/S`,
`net income = mktcap / P/E`, `equity = BVPS x shares`, `EBITDA = EV / EV-EBITDA`,
`net debt = EV - mktcap`. These are arithmetic identities, not estimates, but they inherit the
ratio's month-end as-of date while market cap is same-day, so a fast-moving name's derived
revenue can be a few percent off the filed figure. A **reported** value from the free stack
always beats a derived one (`broker_fundamentals.merge`).

### The fields with NO free source anywhere — the real "would need paid data" list

`operating_income`, `gross_profit`, `fcf`, `interest_expense`, `op_margin`, `gross_margin`,
`fcf_yield`, `ebit_ev`, `roic`, `revenue_growth`.

These come only from the slow per-name free stack (yfinance/EDGAR). They feed **growth** and
about half of **quality**. Locally the free stack supplies them fine; from a cloud IP it is
rate-limited, and that is the real exposure.

## Coverage: before vs after (100 liquid names, same universe, cold cache)

| | Before | After (broker + free) | Broker ONLY |
|---|---|---|---|
| Names scored | 99/100 | 99/100 | **97/100** |
| Wall clock | 244s | 230s / 189s (2 runs) | **15s / 16s** |
| growth theme coverage | **0.76** | **1.00** | 0.00 |
| quality / value / momentum / size | 1.00 | 1.00 | 0.94 / 1.00 / 1.00 / 1.00 |
| low_risk (beta) | 1.00 | 1.00 | 0.92 |

Be careful with the middle column's timing: the shipped path still makes the same slow
per-name free call, so **it is not meaningfully faster** — 244s vs 230s/189s is network noise
across three runs, not an improvement. The speed result is the third column.

The "Broker ONLY" column is the one that matters: I forced the free stack to fail outright,
simulating a throttled cloud IP. **97 of 100 names still scored, in 15 seconds instead of 230**
— with value, quality, momentum, size and low-risk intact and **growth gone**.

That is the resilience win, and it is the concrete answer to "what happens when Yahoo throttles
us". Before this change a failed per-name fetch returned nothing and the name was **dropped
from the scan entirely** ("no data"). Now the name survives on the broker's half. A throttled
Yahoo costs the scan some quality per name instead of costing it the name.

## Two bugs found and fixed on the way

**1. Enterprise value is `0` for banks — a "not applicable" sentinel, not a number.** Of 200
liquid names, 11 carry `ev == 0` and **all eleven are Financial Services** (JPM, BAC, WFC, GS,
MS, C, SCHW, AXP, COF, NU, SOFI); no other sector has one and none is negative. Taken
literally it sets `net_debt = -market_cap` (JPM: **-$935B**) and `ev_sales = 0` — i.e. it would
hand every large bank the cheapest possible EV/Sales in the universe and **peg the entire
sector to the top of the value theme**. Now treated as missing, so banks are ranked on earnings
yield / book / sales, which is how a bank should be valued anyway. Pinned by a test.

**2. The `insider` theme is inert in the live scan, and coverage was reporting it as 100%.**
No `insider_score` ever reaches `build_frame` in the live path (only the backtest panel and a
post-scan decoration set it), so the column is the constant `0.0`. A constant has zero
variance, `zscore()` returns all-NaN, and `composite_score` renormalizes its **12.5% weight
away**. But `theme_coverage` measures *presence*, so it read `insider: 1.0` — a dead theme
reported as perfectly healthy. This is the same class of bug as the five silently-empty factors
in CLAUDE.md.

I did **not** change the scoring. I added `theme_contributing` to the health block, which
measures each theme *after* standardization, and pointed the UI warning at it. Present and
usable are now separate numbers.

Measured live, only **4 of 9 themes actually drive the score**: value, quality, momentum, size.
`low_risk` is deliberately weighted 0; `insider`, `capital_discipline`, `sentiment` and
`institutional` are all inert. Worth knowing before reading any live ranking.

## What I did NOT wire, on purpose

The broker carries **13F and insider ownership at 99% coverage** — holder counts, shares
bought/sold, insider buys/sells. That is exactly the input the `institutional` theme
(12.5% weight, currently empty live) and the `insider` theme want, and it is tempting.

I left it unwired because **populating an empty theme changes every ranking**: `composite_score`
renormalizes over whichever themes are present, so a name that was scored on 4 themes would
suddenly be scored on 5 or 6. CLAUDE.md's rule is that a theme change has to clear
`holdout_theme_validate()` first, and I cannot run that here — this is a live-only snapshot
feed with no history, and Morningstar's aggregate 13F summary is a different construction from
the point-in-time Sharadar SF3 data the backtest validated. Wiring it would be an unvalidated
scoring change dressed as a data fix.

**This is the highest-value follow-up and it is Don's call, not mine.** Fields are
`ownership_summary.{13_f_holder_number, 13_f_shares_bought, 13_f_shares_sold, 13_f_shares_held,
insider_shares_bought, insider_shares_sold, number_of_insider_buys, number_of_insider_sellers}`.

## Changed

- **NEW `valuation/screener/broker_fundamentals.py`** — batched fetch, the field map, the
  sector-code map, `merge()` (reported beats derived) and `coverage()`.
- `providers.py` — `FreeProvider.prefetch()` bulk-loads the universe; `get_metrics` merges
  broker + free and no longer drops a name when the free fetch fails. `FMPProvider` delegates
  prefetch to the free stack behind it (on the current FMP tier the fallback IS the hot path).
  Added `METRICS_SCHEMA`, so cache rows written before the merge are discarded rather than
  served — a stale row missing `sector` is indistinguishable from a name that has none.
- `screen.py` — calls `prefetch()` when the provider supports it (optional by contract);
  ships a `fundamentals` health block (per-field fill rates, per-source counts) and
  `theme_contributing`; carries `extra.source` per name.
- `app.js` — per-name `p` marker for broker-only rows, a fundamentals-source line, and the
  theme warning now reads `theme_contributing`.
- `tests/test_screener.py` — 32 -> 43 tests.

Morningstar's 11 sector codes map **exactly** onto the sector names `engine/comps` already
uses, so a broker sector lands straight in the fair-value peer medians instead of falling
through to the generic default. A test pins that — a near-miss like "Financials" would fail
silently.

## Two operational notes

**The next scan will be slow, once.** `METRICS_SCHEMA` went 1 -> 2, so every cached
fundamentals row is discarded and refetched. The Actions `.scan-cache` is effectively empty
for one run: at ~2.3s/name and `SCAN_LIMIT=800` that is roughly 30 minutes against a
`timeout-minutes: 60` budget. It should fit, but if that run goes red on a timeout this is
why, and it is self-correcting on the following run.

**There is a fast mode available and I did not switch it on.** Skipping the per-name free
fetch entirely gives a full scan in ~15s instead of ~230s, at the cost of the growth theme and
part of quality. I did not add a flag for it because nothing needs it today, but if the
scheduled scan ever starts timing out or Yahoo throttling gets worse, that is the lever — and
the measured trade-off is in the table above rather than a guess.

## Caveats — do not drop these

- Coverage is measured on **200 liquid large caps**. Thinner names will have worse ratio
  coverage; the 83.5% EV/EBITDA figure is the weakest link and will be lower down-cap.
- The derived absolutes carry the ratio's month-end as-of date, not today's filing.
- I could not test the throttled-cloud-IP case for real — I simulated it by forcing the free
  fetch to raise. The 97/100 survival number is from that simulation, not from production.
- The broker feed is a **snapshot**, not point-in-time. It is fine for live ranking and must
  never be fed to the backtest panel.

---

# Session 3 — 2026-08-02 — Index tab, dynamic alpha, trust enablers (PROMPT_appfixes_index.md)

## Shipped — all five items, including the "if time" one

**1. The Valquo Index has its own tab.** Moved out of the bottom of Hot Stocks (Hot Stocks now
links across to it). The tab carries: a cumulative Index-vs-SPY chart, the backtested-vs-live
performance pair, the sector-diversification view, and the full holdings table with Company /
Sector / Weight / Market cap / Hot score populated. Verified by actually running the app and
driving it in a browser — screenshots of both the long-track and the real 1-day state.

**2. Dynamic net alpha — backtested and live, side by side, never blended.** Two cards. The
server decides which one may be the headline; the UI never picks based on which number looks
better. Rules encoded in `valuation/screener/index_track.py`:
- Live cannot be the headline until **60 trading days** (`MIN_LIVE_DAYS`). Before that the
  card is badged `thin — Nd` and the backtest keeps the border.
- **Annualised alpha and Sharpe are withheld** (served as `null`, rendered "—" with the
  reason) until there is enough history. Compounding 1 day of drift into a yearly rate
  manufactures a number nobody should believe. Cumulative-since-inception *is* shown from
  day one, because that one is honest at any length.
- Sharpe is also suppressed above **6.0**. A near-constant excess series drives the
  denominator to zero; I hit exactly this in testing and got "Sharpe 444", which on a live
  page would discredit every other number on it.
- Right now the real state is **1 day (2026-07-31): Index +0.41% vs SPY +0.69%, −0.28pp**.
  Thin, shown, not the headline. That is the correct display, not a bug.

**3. Trust enablers.**
- **Staleness stamp** (`valuation/screener/freshness.py`) on the Index, Hot Stocks and
  Signals. Age is in **trading days**, so a Friday scan read on Sunday is correctly "fresh" —
  crying wolf across a weekend is how staleness badges get ignored. 2 days warns, 3+ shows a
  red "the scheduled update has not run. Do not treat it as current."
- **Risk disclaimer** as one shared string (`RISK_DISCLAIMER` in `web/app.py`) served with
  the Index and Signals payloads, so the wording cannot drift between surfaces.
- **`/methodology`** — point-in-time, survivorship, the 236bps-breakeven cost framing, CPCV /
  PBO / Deflated Sharpe, held-out confirmation, full-universe-only. Plus a "where it is weak"
  section that keeps the uncomfortable parts: one 18-year dataset the model was tuned on, a
  saturated Deflated Sharpe, dormant themes, and the degraded data feed. A test asserts those
  weaknesses stay on the page, so it cannot quietly become marketing. Linked from both
  footers and from the Index and Signals tabs.

**4. Scan-failure alerting.** Two layers:
- `scripts/ci_scan.py` posts to Discord if the scan crashes or exits non-zero.
- `scripts/check_staleness.py` — a **separate** `watchdog` job on its own cron (13:15 UTC
  weekdays, before the open). It runs separately on purpose: a check bolted onto the end of
  the scan cannot fire when the scan is the thing that died, which is exactly the July
  failure. It hits the public API from outside, and alerts on a stale scan **or a collapsed
  universe**. Exits non-zero so the Actions run goes red too.
  Run against the live site right now it already fires: *"the last scan only scored **154**
  names — the universe has collapsed"*.

**5. Mobile pass** (the "if time" item). Index tab verified at 390px: no horizontal page
overflow, stat rows and sector labels scaled down, wide tables scroll inside their own box
rather than the page.

## What Don needs to do

1. **Add `DISCORD_WEBHOOK_URL` as a GitHub Actions secret.** Everything in item 4 is wired and
   inert without it — the alerts fall back to "red run in the Actions tab", which is precisely
   what nobody noticed for four days in July.
2. **Point the Cowork tracker at the new ingest endpoint.** `data/` is gitignored, so the
   tracker's files never reach Render and the live column would be permanently empty in
   production while working fine on your laptop. `POST /admin/ingest-index-track` with
   `X-Admin-Token`, body `{"inception_date", "benchmark", "series": [{"date","valquo","spy"}]}`
   — percentages cumulative-since-inception, exactly as `valquo_track_history.csv` holds them.
   → **This is a Cowork-side task.**
3. The 60-trading-day promotion threshold is a judgement call, not a measured one. It is one
   constant (`index_track.MIN_LIVE_DAYS`) if you want it longer.

## Nothing slipped

All five items shipped. The prompt allowed item 5 to be dropped; it wasn't needed.

## Tests

Six suites green: **edge 119/119, screener 32/32 (+5), saas 22/22 (+2), intraday 18/18,
engine 28/28, bulk 14/14.**

New tests worth knowing: `test_live_track_never_annualizes_a_stub_or_leads_with_it` (5 days
must never lead and must never be annualised; 65 days must),
`test_live_track_suppresses_an_implausible_sharpe`,
`test_freshness_counts_trading_days_not_calendar_days` (pins the weekend behaviour and the
real 07-29 case), `test_methodology_page_is_public_and_states_the_weaknesses`,
`test_index_track_ingest_requires_the_admin_token`.

---

# Session 2 — 2026-08-02 — the live universe (PROMPT_appfixes_universe.md)

## Headline

**Universe: 191 names / 154 scored → 800 names / 794 scored**, sourced from a 7,113-name
broker-enumerated pool ranked by liquidity. The Index goes from a decile of 77 eligible names
to a decile of **668**. Verified end to end locally.

The `company-screener` failure is diagnosed and worked around, but the diagnosis is worse than
the prompt assumed and you have a decision to make. Read "The FMP problem" before anything
else. Also note the security item (6) — an API key was one commit away from being public.

## Step 1 — verification: the FMP key did NOT fix it

The live site is still serving the **2026-07-29** scan: 191 universe / 154 scored. There has
been **no successful scan since 07-29** — four days. So the re-run either did not fire or did
not land, and I could not verify from the site. I diagnosed against the live key directly.

## The FMP problem — it is not the screener endpoint, it is the whole subscription

Verified 2026-08-02 against the real key. Two separate restrictions:

**1. Every bulk/list endpoint is 402 Restricted.** Not a parameter problem — I tried the call
with and without `exchange`, `country`, `isActivelyTrading`, and at `limit=10`. All 402.

| endpoint | result |
|---|---|
| `company-screener` | 402 Restricted |
| `stock-list` | 402 Restricted |
| `sp500-constituent` / `nasdaq-constituent` / `dowjones-constituent` | 402 Restricted |
| `available-exchanges`, `batch-quote-short` | 402 Restricted |
| `profile`, `quote`, `key-metrics-ttm`, `ratios-ttm` | 200 OK |

**2. Worse — the per-symbol endpoints serve only an ALLOWLIST.** I sampled 30 names spread
across the liquidity ranking and asked for `key-metrics-ttm`: **29 of 30 came back 402**, with
a symbol-level message — *"Premium Query Parameter: 'Special Endpoint : This value set for
'symbol' is not available under your current subscription"*. Blocked names include FCX, NSC,
ELV, PRU, CLX, WDAY, TDG, HAS. AAPL/NVDA/AMD/GE/AMZN/CSCO still work.

**This is a change, not a long-standing state.** FCX, ELV and MU are all present in the live
07-29 snapshot — FMP served them four days ago and refuses them today. That points at the
subscription lapsing or being downgraded around 2026-07-29, which is also exactly when the
daily scans stopped appearing. **Worth checking your FMP account first — this may be a billing
problem rather than a code problem.**

So: no code change can restore FMP-sourced fundamentals for the large-cap tier. That is the
honest answer the prompt asked for.

## What I built anyway, so the product is not dead in the meantime

**1. Universe from the broker (Tradier) — the name-list fix the prompt asked for.**
New `valuation/screener/broker_universe.py`. Tradier has no bulk restriction and you already
pay for it:
- `markets/lookup`, 26 calls (one per letter) → **7,113 distinct NYSE/Nasdaq common stocks**
  with company names, in ~9s.
- `markets/quotes`, batched 200 at a time → last price, average volume, 52-week high.
- Ranked by **average dollar volume** and cut to a limit. The broker does not publish market
  cap; liquidity is what actually decides tradeability and is a tight proxy for size. Market
  cap still comes from the fundamentals feed per name, so the large-cap gate is unchanged.
- Whole universe costs ~50 free calls and ~4s. ETFs excluded; sub-$1 and illiquid names
  dropped; class shares normalised (`BRK/B` → `BRK-B`, which otherwise fail every downstream
  lookup — that quietly dropped some of the largest companies in the market).

**2. Fixed the actual code bug that capped the universe at 191.** `FMPProvider`'s fallback
hardcoded `"bundled"` regardless of the scope requested. So a `whole_market` scan silently
became a 191-name scan the moment the screener 402'd. It now falls back **for the scope that
was asked for**, through broker → EDGAR → bundled.

**3. Per-symbol fallback to the free stack.** When FMP refuses a symbol, that name is served
by the existing yfinance/EDGAR path instead of being dropped. A circuit breaker stops asking
FMP after 12 consecutive failures, so a refusing subscription costs 36 wasted requests per
scan rather than 2,400. The per-source split ships in the health block — a book built from two
fundamentals feeds should never be a silent fact.

**4. FMP spend ceiling.** `FMP_MAX_CALLS` bounds requests per scan. It caps what we *spend*,
not what we *rank*: names past the budget go to the free path.

**5. Persistent scan cache in CI.** `ci_scan.py` now writes to `.scan-cache/screener.db` and
the workflow restores it with `actions/cache`. Without this every CI run started from a cold
cache and re-paid for every name. With it, a run only pays for entries past the 30-day TTL.

**6. SECURITY — an API key was about to be published.** `requests` puts the full request URL,
query string included, in its `HTTPError` text. My first version of the universe note stored
that verbatim, and the health block is served publicly by `/api/hotstocks` — so the live FMP
key would have been on the open internet. Everything reaching that block now goes through
`_redact()`. Pinned by `test_api_keys_never_reach_the_health_block`. **If you want to be
careful, rotate the FMP key** — it was never actually deployed, but it was one commit away.

## Measured results

Local end-to-end runs (temp DB, live site untouched):

Local end-to-end runs (temp DB, live site untouched):

| run | universe | scored | notes |
|---|---|---|---|
| **before** (live, 07-29) | **191** | **154** | bundled fallback |
| 250-name broker universe | 250 | 247 | 6 via FMP, 244 via free fallback |
| **after** — 800-name broker universe | **800** | **794** | the configured production size, 22 min |

The 800-name run in full: 99.3% scored; display coverage name 99.9% / sector 99.9% /
market cap 100%; only 6 names dropped (3 no market cap, 2 nano-cap, 1 illiquid). Theme
coverage value/quality/momentum/low_risk/size 1.00, growth 0.98. Index:

> `tilt: large-cap only` · **668 eligible** · **67 positions** · **10 sectors**
> (Financials 30.8%, Healthcare 23.1%, Technology 19.4%, Energy 10.9%, …)

Compare the old book: 77 eligible, 25 positions, 5 sectors. **This is a genuinely different
book** — a decile of 668 large caps rather than a decile of 154 mostly-mega-caps, so the
holdings will look unfamiliar (NLY, ARWR, APGE, QXO, SYF at $10–25B rather than DELL/BA/AMD).
That is the intended consequence of ranking the actual tier, but eyeball the first live one.

Throughput ~1.6s/name on a cold cache. The workflow's `timeout-minutes` went 30 → 60 and
`SCAN_LIMIT` 1500 → **800** to fit that honestly. With `actions/cache` warm it will be far
quicker, and 800 can be raised.

Note the 800-name run served **0 names via FMP** — by then my diagnostics had tripped FMP's
**429 rate limit**, the circuit breaker fired, and the free stack carried all 800. That is the
degraded mode working exactly as designed, and it is also a preview of what every scan looks
like until the subscription is sorted.

## The decision you need to make

**Option A — fix the FMP subscription (~$22/mo Starter).** Restores `company-screener` (one
call for the whole market with sector and market cap) and, more importantly, per-symbol access
to the whole universe. Cleanest, and the code already prefers FMP whenever it answers.

**Option B — stay on the free stack.** It works: the 250-name run scored 98.8% of names with
essentially no FMP. But it is yfinance, so it is slower (~25 min for 800), rate-limited from
cloud IPs, and occasionally returns nothing for a name.

My recommendation: **check whether the FMP plan lapsed first** — if this is an expired card
rather than a deliberate downgrade, that is the whole fix. The code works either way.

## Not done (step 3)

The Index-in-its-own-tab with a cumulative-vs-S&P chart, and dynamic net alpha, were step 3
"only if there's time". Step 2 took the session. Left for next time.

## Tests

All six suites green: **edge 91/91, screener 24/24 (+5), saas 20/20, intraday 18/18,
engine 19/19, bulk 14/14.**

New: `test_api_keys_never_reach_the_health_block`,
`test_fmp_universe_falls_back_for_the_scope_that_was_asked_for`,
`test_fmp_budget_and_circuit_breaker_fall_back_instead_of_dropping_names`,
`test_broker_universe_normalizes_class_share_symbols`,
`test_broker_universe_ranks_by_liquidity_and_drops_junk`.

## One cost I incurred

Diagnosing this spent roughly 400–500 FMP requests off your daily allowance (endpoint probes,
a 30-symbol allowlist sample, and end-to-end scans) — enough that FMP was returning **429 Too
Many Requests** by the end. If tonight's scan looks quota-thin, that is why; it resets daily,
and the circuit breaker means the scan still completes off the free stack either way.

To be precise about the allowlist evidence, since the 429s came later and could muddy it: at a
single moment, with the same key and no rate limiting in play, `AAPL` returned **200** while
`FCX` and `NSC` returned **402** with a *symbol-scoped* message. A rate limit does not
discriminate by symbol. The allowlist is real and separate from the quota.

---

# Session 1 — 2026-08-02 — display fixes (PROMPT_app_fixes.md)

Landed on `main` as b459d9a. Summary retained for continuity:

- **$0.00 market caps were a unit bug.** `CompanyData` carries millions, FMP's profile carries
  dollars, both fed the same scan; the UI renders `market_cap/1e9`. The screener's metrics
  contract is now USD dollars everywhere, stamped with `units` so a millions-era cache entry is
  discarded. Ratios computed before scaling, so `earnings_yield`/`pe`/`ps`/margins are unchanged.
  Fell out of it: `prefilter`'s nano-cap floor was comparing dollars against `50`, and the Index
  had silently degraded to "largest half" because nothing cleared the $10B floor.
- **Company names** were present in the data but absent from the UI — the Index table had no
  Company column. Added there and in the portfolio table.
- **Sectors + a diversification view**: new `screener/profiles.py` resolves name/sector from the
  live feed (store → SEC filer list → bundled map → FMP profile, capped); `valquo_index.export()`
  decorates the finished book; new sector-weight breakdown above the Index table with sector
  count, largest sector and effective sectors.
- **Formatting**: one `mcap()` ($B/$T/$M, 2dp) everywhere; removed two local `pct`/`num` shadows;
  added `spct()` and `esc()`.
- Scan health gained `display_coverage` and a recorded reason for universe fallbacks.
