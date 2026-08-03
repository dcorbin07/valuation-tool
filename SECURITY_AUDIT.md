# SECURITY_AUDIT.md — read-only secret-exposure sweep

Date: 2026-08-02. Auditor: Claude Code (security-audit agent). **Read-only — no code was changed.**
Scope: `origin/main` @ `ef659c1` (the shipping state), plus the local working tree and all 261 commits
of git history. This file is a map, not a repair; fixes are sequenced separately.

**No secret value appears anywhere in this document.** Findings reference name + location only.

> **STATUS — updated 2026-08-02, later the same day.** This file is the original snapshot and
> is kept as the historical record; the `file:line` references below are pre-fix and have
> since moved. **Every finding here is now fixed and pinned by a test except M7**, which this
> document itself flags as a decision for Don rather than a bug. See
> `HANDOFF_security_fixes.md` for what shipped, what was deliberately deferred (CSP, full
> email verification, the `/forgot` timing side-channel) and why. New regression suite:
> `tests/test_security.py`, 22/22.

---

## 0. Headline

**Good news first, because it is the question that mattered most: no live secret has ever been
committed to this repository.** Every other finding below is a code fix, not a rotate-now emergency.

The one finding that needs attention today is **C1 — the password-reset link is handed straight back
to whoever asks for it whenever SMTP is unconfigured or failing.** That is a full account-takeover
path against any account including the owner's, and whether it is live right now depends on a single
Render env var. Check it first (10-second test in C1).

The FMP leak the app-fixer caught was correctly and properly fixed — but **the fix is local to one
file.** `_redact()` lives in `screener/providers.py` and is called from four places in that same
file. Twenty-three other handlers return raw exception text to unauthenticated callers (H2). The
class of bug is still open; only the one instance was closed.

---

## 1. Ranked findings

### CRITICAL

#### C1 — Password-reset link is disclosed in the HTTP response when email is not sending
- **Where:** `valuation/saas/auth.py:101-103` → `valuation/web/templates/forgot.html:9-11`,
  enabled by `valuation/saas/emailer.py:13-14` and `:26-27`.
- **What:** `send_email()` returns `False` for *two different* reasons — "SMTP not configured"
  (`emailer.py:13`) and "the send threw" (`emailer.py:26`). `auth.py:102` treats that single `False`
  as "we must be in dev" and sets `dev_link = link`; `forgot.html:11` then renders the live reset URL
  into the page body.
- **Failure scenario:** an anonymous attacker POSTs `/forgot` with `email=<owner address>`. The owner
  address is not a secret — it is the committed default at `config.py:163` and appears in
  `.github/workflows/auto-scan.yml:72`. If SMTP is unset or the SMTP host is merely *down*, the
  response contains a valid 1-hour reset token. They reset the password and own the account. The
  owner account is the one that unlocks `/api/edge/*` (`gating.py:89-91`), the research bench.
- **Also:** this leaks account existence. A real user gets `sent=True` **with** a `dev_link`; an
  unknown address gets `sent=True` with none (`auth.py:104`). The "same message regardless" comment
  on that line is not true once SMTP is broken.
- **Live or not:** `render.yaml:50-55` marks `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` as `sync: false`,
  meaning they must be typed into the Render dashboard by hand. If that was never done, this is live
  in production right now. **Test:** POST `/forgot` with a known-good address against the live site
  and look at the HTML body for a `/reset/` URL.
- **Fix (one line):** gate the disclosure on an explicit developer flag rather than on send failure —
  `dev_link = link if (not sent and app.debug) else None` — or drop `dev_link` entirely and log the
  URL server-side.

---

### HIGH

#### H2 — 23 handlers return raw exception text to unauthenticated callers (the FMP-leak class, still open)
- **Where — the redaction that exists:** `valuation/screener/providers.py:70-81`, called at
  `:208`, `:301`, `:315`, `:370`. That is the whole of its coverage.
- **Where — the handlers that bypass it:**
  - `valuation/web/app.py:100, 120, 148, 171, 247, 286, 302, 575, 610, 645, 658, 668, 678`
  - `valuation/saas/app_saas.py:137, 183, 217, 239, 274, 296`
  - `valuation/saas/billing.py:52, 66, 77, 103`
- **Why it can carry a key:** both paid providers put the credential in the **query string** —
  `providers.py:281` (`params["apikey"] = self.key`) and `data_providers.py:113`
  (`params["api_key"] = self.key`). `requests.raise_for_status()` raises an `HTTPError` whose text is
  the full request URL, query string included. That is exactly the mechanism `_redact`'s own
  docstring describes at `providers.py:72-76`. Any such error that escapes a provider's internal
  `try` and reaches one of the handlers above is republished verbatim.
- **Most exposed:** `/api/value` (`app.py:100`) and `/api/rank` (`app.py:120`) are unauthenticated
  under the current config (see H1) and sit directly on top of the fetcher stack.
- **Fix:** promote `_redact()` out of `screener/providers.py` into a shared module and wrap every
  error string above in it. It is the same one-line call at each site.

#### H1 — `OPEN_ACCESS` defaults to true, so almost every `/api/` route is unauthenticated — including the ones that spend money
- **Where:** `valuation/config.py:212` (default `true`) → `valuation/saas/gating.py:95-96`, which
  returns `None` (allow) before every login check, feature lock and usage cap below it.
- **What is exposed:** everything under `/api/` except `/api/edge/*`, which is correctly checked
  *before* the short-circuit at `gating.py:89-91`. Notably:
  - `/api/signals/run` (`app.py:626`) → `explain_top()` → **Anthropic API calls on your key**, per request.
  - `/api/scan/run` (`app.py:559`) → whole-market scan → **FMP quota**, 3 requests per uncached name.
  - `/api/value` (`app.py:80`) with `run_ai: true` → another Anthropic call per request.
  - `/api/backtest/run` (`app.py:592`), `/api/portfolio` (`app.py:578`) → CPU-heavy on a 512 MB box.
- **No rate limiting exists anywhere in the codebase** (verified: no limiter, no 429 path, no
  per-IP counter). The only quota control is `FMP_MAX_CALLS` (`config.py:138`), which defaults to
  `0` = unlimited.
- **Failure scenario:** a script hitting `/api/signals/run` in a loop drains the Anthropic balance
  and the FMP daily allowance, and starves the 22:23 UTC scan the product depends on. No account
  needed, no token needed.
- **Note:** open access is a deliberate product decision and this finding is not an argument against
  it. Reading the hot list freely is fine; *spending the owner's API budget* freely is the problem.
- **Fix:** keep the read endpoints open, put the four `run`/`scan` endpoints behind the existing
  `X-Admin-Token` (they are already cron-driven) or a per-IP rate limit.

#### H3 — Owner privilege is granted by an unverified email string, and there is no email verification anywhere
- **Where:** `valuation/saas/gating.py:57` and `:90`, against `config.py:163`
  (`OWNER_EMAILS` default is the owner's real address, committed).
- **What:** owner status is `user["email"] in owner_email_set`. There is **no email verification in
  the codebase at all** (verified: no `verify_email` / `email_verified` / `confirm_email` anywhere),
  and `create_user` (`models.py:75-86`) only checks the address is unique and contains `@`.
- **Failure scenario:** if no account with the owner address exists yet, the first person to register
  it becomes the owner and gains `/api/edge/*` — the learning history, adopted weights and the
  research bench.
- **Currently latent, not live:** `/register` is closed because `signup_enabled` is
  `not open_access` = `False` (`config.py:232-244`, enforced at the route in `auth.py:46-47`). It
  goes live the moment `OPEN_ACCESS=false` or `FEATURE_BILLING=on` — i.e. the day you start charging.
- **Fix:** resolve owner against a verified user id, not a typed string; add verification before
  re-opening signup.

---

### MEDIUM

#### M1 — Sharadar key written to logs unredacted
- **Where:** `valuation/edge/data_providers.py:212` prints the raw exception to stderr; the same
  provider builds `?api_key=` URLs at `:113` and `:125`. Also `:105` and `:107` put `r.text[:200]`
  and `{e}` into returned strings, and `:108` returns `Could not reach Nasdaq Data Link: {e}`.
- **Impact:** Render / GitHub Actions logs. Lower than H2 (not public), but it is a live key sitting
  in a log aggregator, and `check()`'s return value surfaces through `/admin/run-fundamental-backtest`
  (`app_saas.py:183`).
- **Fix:** route all four through the shared `_redact()` from H2.

#### M2 — No CSRF protection on any state-changing POST
- **Where:** `/login` (`auth.py:60`), `/register` (`auth.py:39`), `/reset/<token>` (`auth.py:107`),
  `/account/alerts` (`app_saas.py:340`), `/billing/checkout` (`billing.py:22`), `/billing/portal`
  (`billing.py:54`). All are cookie-authenticated form POSTs with no token.
- **Compounding:** no `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE` or `PERMANENT_SESSION_LIFETIME`
  is set anywhere (verified — no such config in the codebase), so the session cookie also rides over
  plain HTTP if the site is ever reached without TLS.
- **Fix:** Flask-WTF CSRF, plus `SESSION_COOKIE_SAMESITE="Lax"` and `SESSION_COOKIE_SECURE=True`.

#### M3 — Session and reset-token signing key falls back to a committed literal
- **Where:** `valuation/config.py:79` — `SECRET_KEY` defaults to `"dev-insecure-change-me"`. Used for
  Flask sessions (`app_saas.py:31`) **and** password-reset token signing (`auth.py:34-35`) **and**
  unsubscribe tokens (`notify.py:25`).
- **Impact:** if `SECRET_KEY` is ever unset in an environment, anyone reading this repo can forge a
  session cookie for any `uid` and mint valid reset tokens. `render.yaml:16-17` sets
  `generateValue: true`, so production is covered — this is a fail-open default, not a live breach.
- **Fix:** raise on boot if `SECRET_KEY` is the default and the app is not in debug.

#### M4 — `DEMO_ACCESS_TOKEN` defaults to the guessable string `"preview"`
- **Where:** `valuation/config.py:213`; consumed at `valuation/saas/auth.py:71-83`.
- **Impact:** `/demo/preview` grants a permanent Premium session with no signup. Near-zero impact
  while `OPEN_ACCESS=true` (everything is open anyway); becomes a free-Premium bypass the day you
  start charging. `config.py:203` already flags this ("set it to something unguessable before you
  charge") — recording it so it is not missed.
- **Fix:** no default; disable `/demo` entirely when the env var is unset.

#### M5 — Admin token compared with `==` (non-constant-time)
- **Where:** `valuation/saas/app_saas.py:66, 120, 159, 189, 211, 223, 246, 279`.
- **Impact:** theoretically byte-at-a-time recoverable over the network; in practice heavily masked by
  jitter. Low real risk, trivial fix, and these eight endpoints are the whole admin surface.
- **Good, keep it:** every one of them fails closed when `ADMIN_TOKEN` is empty (`not cfg.admin_token`
  short-circuits to 401). That is the right default and it is correct in all eight.
- **Fix:** `hmac.compare_digest`.

#### M6 — LLM output injected into the DOM as raw HTML
- **Where:** `valuation/web/static/app.js:485-493` — `business_summary`, `moat.text`, `bull_thesis`,
  `bear_thesis`, `key_risks`, `catalysts`, `assumption_critique`, `overall_take` are concatenated and
  assigned via `innerHTML` at `:493`. Also `:709` and `:711` interpolate server/JS error strings.
- **Impact:** the model writes from filings and news text, which is attacker-influenceable. A
  crafted string in a filing becomes script in the user's page. Jinja autoescape protects the
  templates (verified: no `|safe` anywhere), but this path bypasses templates entirely.
- **Fix:** `textContent` for each field, or sanitize before assignment.

#### M7 — Any `worktree-*` branch push auto-merges to `main` and deploys to production
- **Where:** `.github/workflows/land-agent-branch.yml:30-31` (trigger), `:38-39`
  (`contents: write`), `:62-68` (merge → test → `git push origin HEAD:main`).
- **Impact:** production deploys have no human review. The test gate is `tests/test_edge.py`, which
  the pushed branch can itself modify — and step `:64-65` executes branch-controlled code on a runner
  holding a `contents: write` token, so a malicious branch can bypass the gate or exfiltrate the
  token. Anyone or anything with push access — a leaked PAT, a compromised agent session — reaches
  production in one step.
- **Judgement call, not a bug:** this was clearly a deliberate trade of review for hands-off shipping,
  and it is documented as such in the file header. Recording the exposure, not second-guessing it.
- **Fix if you want the safety back:** require a PR + review for `main`, or at minimum reject a branch
  that modifies `tests/` or `.github/`.

---

### LOW

- **L1 — `PUBLIC_PATHS` is dead code.** `valuation/saas/app_saas.py:22-23` defines a public-path
  allowlist that is **never referenced anywhere** (verified). `_guard` (`:361-383`) implements a
  different and narrower policy. It reads like enforced access control and enforces nothing —
  a real trap for the next person. Delete it or wire it in.
- **L2 — No security headers.** No CSP, `X-Frame-Options`, `X-Content-Type-Options` or HSTS; there is
  no `after_request` hook in the codebase at all. Add one small hook.
- **L3 — Stack traces to stdout on public error paths.** `traceback.print_exc()` at
  `valuation/web/app.py:99, 147, 170, 285, 574, 609, 645, 657, 668, 677` (10 sites). Server-side only,
  so not a direct disclosure — but they land in Render logs next to the URLs described in H2/M1.
- **L4 — Absolute file paths disclosed via the H2 handlers.** A `FileNotFoundError` from the store or
  data layer stringifies to `/app/data/...`, reaching unauthenticated clients through the same 23
  handlers. Fixed for free by the H2 fix.
- **L5 — Licensed Sharadar data can be baked into a locally built image.** `.dockerignore` excludes
  `data/*.db` and `data/*.sqlite` but **not** `data/**/*.csv` or `data/raw/`, while `Dockerfile:9`
  does `COPY . .`. A `docker compose up --build` (`docker-compose.yml:4`) therefore embeds the
  licensed exports in the image. Not a secret, but it is against the project's hard rule on `data/`.
  Fix: replace the two lines with `data/`.
- **L6 — Unsubscribe tokens never expire.** `valuation/saas/notify.py:25` and `:30` use
  `URLSafeSerializer`, not the `URLSafeTimedSerializer` used for resets (`auth.py:35`). Signed and
  unguessable, so impact is limited to a permanently valid unsubscribe link.

---

## 2. What is clean — checked, and genuinely fine

Recorded so the next audit does not redo it.

**Secrets in git history — clean.** All 261 commits swept for: known key formats (`sk-ant-`,
`sk-proj-`, `sk_live_`, `pk_live_`, `whsec_`, `ghp_`, `github_pat_`, Discord webhook URLs); generic
`api_key|apikey|_token|secret_key|password|webhook_url|access_key` assignments to real-looking values;
and 32-hex / 35-45-char high-entropy literals across all `.py .yml .yaml .bat .sh .json .md .txt
.toml Dockerfile Procfile` history. **Zero 32-hex literals (the FMP key format) have ever existed in
this repo.** The only hit was `ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx` — a placeholder in
`.env.example`. No `.env`, `.pem`, `.key`, or credential file has ever been added.

**Secrets at rest — clean.** `.env` exists locally, is untracked, and is covered by `.gitignore:2`.
Only `.env.example` files are tracked (3 of them), all placeholders. No `data/` path and no `*.db`
is tracked. `.dockerignore` correctly excludes `.env`.

**`render.yaml` — clean.** Zero plaintext secret values. `SECRET_KEY` and `ADMIN_TOKEN` use
`generateValue: true`; every vendor key is `sync: false`. The cron jobs pass the token via
`fromService` and send it as a **header**, not a query string (`:71`, `:93`).

**GitHub Actions — clean.** `auto-scan.yml` passes every secret through `secrets.*` into `env:`,
never echoes one, and `curl`s the admin token as a header (`:116`). `scripts/ci_scan.py:46` likewise
uses `X-Admin-Token`. `ci_scan.py:91` prints `universe_note`, which is redacted at source
(`providers.py:315`) — correct.

**The FMP fix itself — correct.** `_redact()` (`providers.py:70-81`) covers `?/&apikey=`,
`api_key=`, `token=`, `access_token=` case-insensitively plus `Bearer <x>`, and is applied *before*
truncation at `:370` (order matters — truncating first could strand a partial key). The public health
block reached by `/api/hotstocks` (`app.py:339` ← `screen.py:250-272`) draws only from
`universe_note` and `budget`, both redacted at write time.

**Also verified sound:** Stripe webhook signature *is* verified (`billing.py:74-77`); all SQL is
parameterized and the one f-string in `models.py:122` interpolates only fixed literal column names;
passwords use werkzeug hashing (`models.py:85, 90`); Jinja autoescape is on with no `|safe` in any
template; `debug=False` in both entrypoints (`run.py:35`, `run_saas.py:14`); no CORS is configured,
which is the safe default; `/api/edge/*` is correctly gated *ahead* of the open-access short-circuit
so the research bench stays private (`gating.py:89-96`), and the demo session cannot reach it either.

---

## 3. Suggested fix order

1. **C1** — one line, closes an account-takeover path. Verify against the live site first.
2. **H2 + M1** — promote `_redact()` to a shared module, wrap all 23 sites + the 4 log/return sites.
   One change closes the whole bug class, which is the point.
3. **H1** — token or rate-limit the four spending endpoints.
4. **M2, M3, M5** — CSRF + cookie flags, boot check on `SECRET_KEY`, `compare_digest`.
5. **M6, L1, L2, L5, L6** — cleanups.
6. **H3, M4** — must be done *before* `OPEN_ACCESS=false`. Latent today, live the day you charge.
7. **M7** — a decision for Don, not a fix.
