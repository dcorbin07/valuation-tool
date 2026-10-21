# PROMPT — app fixer — 2026-10-18 — item 74: send every breakage, and every rebalance that can't happen, to Don on Discord

**Do this BEFORE item 73** (sequencing changed 2026-10-19). The alerts should be live before the 2026-10-22
rebalance, and the live slot stays at 0% either way. One item at a time; don't mix commits.

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.**

This item changes **where messages go**, never what the system trades. A test must pin that every
order plan is identical before and after.

## Don's rulings (chat, 2026-10-18)

1. **Two Discord channels.**
   - **Problems** go to a separate `#valquo-alerts` channel. This covers anything broken, and any
     rebalance that can't happen or is late.
   - **Routine posts** (the daily recap, order sent or filled lines) stay where they are today, on
     `DISCORD_WEBHOOK_URL`.
2. **A free outside monitor, healthchecks.io, catches a job that never runs at all.** GitHub
   stopped running jobs once already (August, a billing hiccup), and nothing inside GitHub can
   report that.
3. **Noise rule:**
   - one post when a problem starts;
   - one when it clears;
   - one reminder per day while it stays broken.
4. **Nothing private in any message, ever:**
   - no P&L, return or verdict;
   - no key, token or webhook URL;
   - no account number or anything else private.

## Names fixed now, so Don can set them up in parallel

Don creates each of these himself. A lane never sees, prints or stores any of them.

| Name | Where Don puts it | What it is |
|---|---|---|
| `DISCORD_ALERT_WEBHOOK_URL` | Render env var **and** GitHub secret | Webhook for `#valquo-alerts` |
| `HC_PING_KEY` | GitHub secret | healthchecks.io project ping key; pings go to `https://hc-ping.com/<key>/<slug>` |

If `DISCORD_ALERT_WEBHOOK_URL` is missing:

- fall back to `DISCORD_WEBHOOK_URL`, and start the message with "(alerts channel not set)", so
  nothing goes silent during setup;
- if both are missing, write a warning in the job log.

If `HC_PING_KEY` is missing, write a warning in the log and continue.

## What must reach `#valquo-alerts`

Inventory every alert source that exists today; many already post to the routine webhook. Then
route and fill gaps so all of the following are covered.

1. **Any scheduled workflow fails.** The service often can't post when the service is the thing
   that failed, so each of these needs a GitHub-side `if: failure()` Discord step: `auto-scan`,
   `daily-doors`, `fleet-backup`, `fleet-cycle`, `fleet-selfcheck`, `live-check`, `live-cycle`,
   `track-backup`, `track-row`, `valreads-record`. A non-200 from the service counts as a failure.
   Leave `land-agent-branch` out: a lane branch failing the gate is normal.
2. **The daily record misses a row**, or `recording_ok` reads false.
3. **A rebalance can't happen or is late:**
   - **Overdue:** more than one trading day past the in-force book's `next_rebalance` and no newer
     book installed. For 10-22 that means an alert from the morning of 10-26.
   - **Refused:** the service refused a new book (conformance, thin data, unpriced names, or
     anything else).
   - **Heads-up:** 14 calendar days before each rebalance date: "Rebalance due `<date>`. It needs
     Sharadar data — make sure your access is active."
   - The overdue check must run at least daily on trading days. Its own failure to run is covered
     by the healthchecks ping.
4. **The paper or live slot can't trade.** This covers:
   - a preflight refusal;
   - a parity mismatch;
   - a broker rejection;
   - a cycle crash;
   - the no-progress ceiling running out;
   - a stale open event;
   - a missing paper client;
   - "waiting for cash" (once, per item 73).

   Orders sent or filled stay **routine**.
5. **The fleet:** self-check failing, a book refused, or a cycle crash. Fills stay routine.
6. **The site watchdog** (stale data, failed scan) moves to alerts. The recap stays routine.

**Every alert kind in the code must be classified as alert or routine in ONE registry.** A test
fails on any unclassified kind, so a future alert can't default to the wrong channel or to
nowhere. Reuse `live_notify`'s and `fleet_notify`'s rules (events once, conditions on change),
add the daily reminder, and keep one path out (`saas.notify.send_discord`) with a channel
argument.

## Message format

Plain words, three short lines:

1. what broke;
2. what it means, for example: *"no orders will be placed for the Index until this is fixed"*;
3. what Don should do, with a link to the run or the page.

## healthchecks.io pings

Each key job pings `https://hc-ping.com/$HC_PING_KEY/<slug>`:

- `/start` when it begins;
- the bare URL on success;
- `/fail` on failure.

Jobs, at minimum: `track-row`, `live-cycle`, `fleet-cycle`, the `auto-scan` watchdog,
`track-backup`, and the rebalance-overdue check.

In the summary, give Don a table, one row per slug: its schedule (cron, in UTC) and the grace
period to set in healthchecks.io. Size the grace to GitHub's measured 3.5–7.5 hour lateness so it
doesn't cry wolf.

## A test button

Add a manual-only workflow, `alert-test.yml` (`workflow_dispatch` only), that:

- posts one test line from GitHub to `#valquo-alerts`;
- asks the service (admin token) to post one test line to each channel;
- reports, for each name, **present or absent only, never the value**.

## Tests

Use real classes and recorded HTTP. For each alert source:

- inject the failure;
- assert exactly one alerts-channel post;
- assert one "resolved" post when it clears;
- assert one reminder after a day, and no more.

Also:

- assert no message body contains a URL from the environment, a token, a key, an account number,
  or a return-shaped word;
- assert order plans are unchanged.

## Workflows and done

- All `.github` changes go in as same-name replacements in `pending_workflows/`. One install must
  leave exactly one copy of each file. `live-cycle.yml` keeps sending `?run=paper`.
- Done means landed on origin/main, with a plain-words summary for Don that includes:
  - the inventory table: source, channel, when it fires;
  - the healthchecks slug table;
  - a one-line note saying when he can double-click `install_workflows.bat`.
- No key, percentage or arming changed.
