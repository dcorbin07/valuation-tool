# -*- coding: utf-8 -*-
"""ITEM 30 — EXERCISE EVERY USER-FACING FEATURE ON THE LIVE SITE, DAILY.

**WHY THIS EXISTS, AS A MEASUREMENT RATHER THAN A WORRY.** Three features were dead on the live
service for weeks and nobody could have known from the inside:

  * the Dip Detector measured ZERO names for two months (items 19 and 23) while the page said
    "no name cleared", which is a positive assertion of absence derived from a measurement that
    did not happen;
  * `/admin/score-alerts` answered a bare HTTP 500 to its only authorised caller, and the test
    suite was 10 of 10 green because every assertion tested a REFUSAL path (item 27);
  * the weekly theme-cache job had never once started, failing three seconds in on a missing
    directory, so `institutional` and `insider` have contributed nothing to the live score for
    the life of the job (item 28).

Every one of those was found by a person using the site, not by a test. **A suite proves the code
does what the code says; only the live service can prove the product does anything at all.**

## WHAT "FAILS ON BEHAVIOUR, NOT WORDING" MEANS HERE

Each check asserts a NUMBER or a FILE TYPE, and prints it whether it passes or fails, so a
degradation is visible before it crosses a threshold. Specifically:

  * freshness is `scan_date == last_closed_session()`, from the project's own market calendar —
    which knows the holidays, so this does not fail on Thanksgiving the way a weekday test would;
  * an export is checked by its MAGIC BYTES (`PK` for xlsx, `%PDF-` for pdf), because this app
    returns `200` with a JSON error body on failure and a JSON error is "non-empty";
  * a not-found ticker is checked for its STATUS, because the defect it guards was a `200`
    carrying a score of 40 and a recommendation of "Reduce" for a company nobody identified;
  * the two alert surfaces are compared to EACH OTHER, because they disagreed by exactly the 8
    rows one of them was mis-classifying.

## THE THREE RULES THIS FILE OBEYS

**1. PUBLIC ENDPOINTS ONLY, NO TOKEN.** Nothing here can write, and nothing here needs a secret.
A checker that needs the admin token is one that cannot run from a public runner without putting
a credential somewhere, and it would also be able to mutate the thing it is checking.

**2. A SKIP IS NOT A PASS.** `/api/signals` cannot be checked against market hours on a weekend;
that prints `SKIP` with its reason, is counted separately, and is never added to the pass total.
This project has paid for the other convention more than once — a guard whose only real execution
is skipped is the defect, not a limitation of it.

**3. STDLIB ONLY.** `urllib` rather than `requests`, so the workflow needs a checkout and nothing
else — no `pip install`, no lockfile, no dependency that can fail on a runner and be mistaken for
the site being down.

    python scripts/live_check.py                  # against https://valquo.co
    python scripts/live_check.py --base http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from valuation.screener import market_session as MS   # noqa: E402  (stdlib-only module)

DEFAULT_BASE = "https://valquo.co"

#: Generous on purpose. US equities trade 13:30-20:00 UTC in EDT and 14:30-21:00 in EST, and this
#: band spans both plus a margin, because the point of the check is "the intraday feed ran during
#: a session today" and NOT "the clock is correct about daylight saving". A narrow band would fail
#: twice a year for a reason that has nothing to do with the product.
MARKET_OPEN_UTC = _dt.time(13, 0)
MARKET_CLOSE_UTC = _dt.time(21, 30)

#: Checked on the RENDERED Index card. `undefined` is a key that does not exist reaching the page
#: as a string; `Roth/IRA): highest` is the tail of a sentence describing an account type the
#: Index is not. Both were live defects (item 21).
BANNED_IN_CARD = ("undefined", "Roth/IRA): highest")


# =============================================================================================
# plumbing
# =============================================================================================
class Report:
    """One line per check, and the exit code."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.lines = []

    def ok(self, name, detail):
        self.passed += 1
        self._emit("PASS", name, detail)

    def bad(self, name, detail):
        self.failed += 1
        self._emit("FAIL", name, detail)

    def skip(self, name, detail):
        # COUNTED SEPARATELY AND NEVER AS A PASS. A skip that reads as success is how a check
        # stops being a check.
        self.skipped += 1
        self._emit("SKIP", name, detail)

    def _emit(self, verdict, name, detail):
        line = "%-4s  %-44s %s" % (verdict, name, detail)
        self.lines.append(line)
        print(line, flush=True)

    def finish(self):
        print("-" * 100, flush=True)
        print("%d passed, %d failed, %d skipped" % (self.passed, self.failed, self.skipped),
              flush=True)
        if self.skipped:
            print("a SKIP is not a PASS — the reason is on its line above", flush=True)
        return 1 if self.failed else 0


def _opener():
    # The site is HTTPS with a normal certificate; this exists so a corporate proxy with its own
    # CA does not look like an outage. It is NOT a verification bypass: the default context is
    # used unless the environment explicitly asks otherwise.
    ctx = ssl.create_default_context()
    if (os.environ.get("LIVE_CHECK_INSECURE") or "").strip() == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def fetch(base, path, *, method="GET", body=None, timeout=240):
    """Return (status, bytes, content_type). Never raises on an HTTP error status."""
    url = base.rstrip("/") + path
    data = None
    headers = {"User-Agent": "valquo-live-check/1.0"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _opener().open(req, timeout=timeout) as r:
            return r.status, r.read(), (r.headers.get("Content-Type") or "")
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b""), (e.headers.get("Content-Type") or "")
    except Exception as e:                                           # noqa: BLE001
        return 0, ("%s: %s" % (type(e).__name__, e)).encode("utf-8"), ""


def get_json(base, path, **kw):
    code, raw, _ = fetch(base, path, **kw)
    try:
        return code, json.loads(raw.decode("utf-8"))
    except Exception:                                                # noqa: BLE001
        return code, None


# =============================================================================================
# the checks
# =============================================================================================
def check_hot_list(base, rep, session):
    code, d = get_json(base, "/api/hotstocks")
    if code != 200 or not d:
        rep.bad("hot list reachable", "HTTP %s" % code)
        return
    rows = d.get("rows") or []
    rep.ok("hot list reachable", "HTTP 200, %d rows" % len(rows)) if rows else \
        rep.bad("hot list reachable", "HTTP 200 but 0 rows")

    scan = str(d.get("scan_date") or "")
    want = session.isoformat() if session else "?"
    if scan == want:
        rep.ok("hot list is fresh", "scan_date %s == last session" % scan)
    else:
        rep.bad("hot list is fresh", "scan_date %s, last session %s" % (scan or "(none)", want))

    tc = (d.get("health") or {}).get("theme_contributing") or {}
    for theme in ("institutional", "insider", "capital_discipline"):
        v = tc.get(theme)
        got = "%.2f" % v if isinstance(v, (int, float)) else repr(v)
        if isinstance(v, (int, float)) and v > 0.5:
            rep.ok("theme contributes: %s" % theme, got)
        else:
            rep.bad("theme contributes: %s" % theme, "%s (want > 0.50)" % got)


def check_dip(base, rep):
    code, d = get_json(base, "/api/dip?min_drawdown=0.10")
    if code != 200 or not d:
        rep.bad("dip detector reachable", "HTTP %s" % code)
        return
    elig = int(d.get("n_eligible") or 0)
    meas = int(d.get("n_measured") or 0)
    rows = len(d.get("rows") or [])
    capped = d.get("capped")
    rep.ok("dip detector reachable", "HTTP 200, %d eligible" % elig)

    # THE DEFECT THIS GUARDS measured 12 of 242 and reported the result as coverage of a market.
    if elig and meas >= elig:
        rep.ok("dip measures every eligible name", "%d of %d" % (meas, elig))
    else:
        rep.bad("dip measures every eligible name",
                "%d of %d measured, capped %s" % (meas, elig, capped))

    if rows:
        rep.ok("dip returns rows at 10% depth", "%d rows" % rows)
    else:
        rep.bad("dip returns rows at 10% depth", "0 rows from %d eligible" % elig)

    # An unmeasured name is not a name that failed; the page must never read the two as one.
    un = d.get("n_unmeasured")
    if un in (0, None):
        rep.ok("dip has no unmeasured names", "n_unmeasured %s" % un)
    else:
        rep.bad("dip has no unmeasured names", "n_unmeasured %s" % un)


def _render_card(payload):
    """The REAL renderer against a stub DOM, or None when node is absent.

    Returns the card's text. `None` means UNCHECKED, and the caller says so rather than passing.
    """
    import shutil
    import subprocess
    import tempfile
    node = shutil.which("node")
    if not node:
        return None
    js = os.path.join(ROOT, "valuation", "web", "static", "app.js")
    if not os.path.exists(js):
        return None
    harness = r"""
const fs = require('fs');
const els = {};
function el(id) {
  if (!els[id]) els[id] = {id: id, innerHTML: "", value: "",
                           set textContent(v) { this.innerHTML = String(v); },
                           get textContent() { return this.innerHTML; }};
  return els[id];
}
global.document = {getElementById: (id) => el(id), querySelectorAll: () => [],
                   querySelector: () => null, addEventListener: () => {},
                   createElement: () => el("_tmp")};
global.window = {addEventListener: () => {}, location: {search: "", href: ""},
                 matchMedia: () => ({matches: false, addEventListener: () => {}})};
global.localStorage = {getItem: () => null, setItem: () => {}, removeItem: () => {}};
global.navigator = {userAgent: "node"};
global.fetch = () => Promise.reject(new Error("no network in the harness"));
const src = fs.readFileSync(process.argv[2], 'utf8');
eval(src + "\nglobal.__render = (typeof _renderValquoIndex === 'function') ? _renderValquoIndex : null;");
if (!global.__render) { console.log("__NO_RENDERER__"); process.exit(0); }
const d = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
try { global.__render(d); } catch (e) { console.log("__THREW__ " + e.message); process.exit(0); }
let out = "";
for (const k of Object.keys(els)) out += (els[k].innerHTML || "") + "\n";
console.log(out);
"""
    with tempfile.TemporaryDirectory() as tmp:
        hp = os.path.join(tmp, "h.js")
        pp = os.path.join(tmp, "p.json")
        with open(hp, "w", encoding="utf-8") as fh:
            fh.write(harness)
        with open(pp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        try:
            r = subprocess.run([node, hp, js, pp], capture_output=True, text=True,
                               errors="replace", timeout=60)
        except Exception:                                            # noqa: BLE001
            return None
        return r.stdout or ""


def check_index(base, rep):
    code, d = get_json(base, "/api/valquo-index")
    if code != 200 or not d:
        rep.bad("Index payload reachable", "HTTP %s" % code)
        return
    rep.ok("Index payload reachable", "HTTP 200")

    # THE BOOK IN FORCE, not a preview of another account type (item 21).
    card = d.get("card") or {}
    if d.get("is_preview") is False and card.get("is_tracked_construction") is True:
        rep.ok("Index shows the book in force",
               "construction %s, is_preview False" % card.get("construction"))
    else:
        rep.bad("Index shows the book in force",
                "is_preview %r, is_tracked %r, construction %r"
                % (d.get("is_preview"), card.get("is_tracked_construction"),
                   card.get("construction")))

    n = int(d.get("n_positions") or 0)
    if n >= 85:
        rep.ok("Index holds 85+ names", "n_positions %d" % n)
    else:
        rep.bad("Index holds 85+ names", "n_positions %d" % n)

    ws = [p.get("weight") for p in (d.get("positions") or [])
          if isinstance(p.get("weight"), (int, float))]
    total = sum(ws)
    if ws and abs(total - 1.0) <= 0.01:
        rep.ok("Index weights sum to 1", "%.6f over %d positions" % (total, len(ws)))
    else:
        rep.bad("Index weights sum to 1", "%.6f over %d positions" % (total, len(ws)))

    card_text = _render_card(d)
    if card_text is None:
        rep.skip("Index card renders clean",
                 "node is absent — the RENDERED card is UNCHECKED on this machine")
    elif "__NO_RENDERER__" in card_text:
        rep.bad("Index card renders clean", "_renderValquoIndex not found in app.js")
    elif "__THREW__" in card_text:
        rep.bad("Index card renders clean", card_text.strip()[:120])
    else:
        hits = [b for b in BANNED_IN_CARD if b in card_text]
        if hits:
            rep.bad("Index card renders clean", "renders %r" % hits)
        else:
            rep.ok("Index card renders clean",
                   "%d chars, none of %d banned strings" % (len(card_text), len(BANNED_IN_CARD)))


def check_index_track(base, rep, session):
    code, d = get_json(base, "/api/index-track")
    if code != 200 or not d:
        rep.bad("Index track reachable", "HTTP %s" % code)
        return
    series = d.get("series") or []
    rep.ok("Index track reachable", "HTTP 200, %d recorded rows" % len(series))
    want = session.isoformat() if session else None
    dates = [str(r.get("date") or "")[:10] for r in series]
    if want and want in dates:
        rep.ok("Index track has the last session", "row for %s" % want)
    else:
        rep.bad("Index track has the last session",
                "no row for %s; latest is %s" % (want, dates[-1] if dates else "(none)"))


def check_alert_surfaces(base, rep):
    c1, st = get_json(base, "/api/scream-track")
    c2, sc = get_json(base, "/api/options-scorecard")
    if c1 != 200 or st is None or c2 != 200 or sc is None:
        rep.bad("alert surfaces reachable", "scream-track %s, scorecard %s" % (c1, c2))
        return
    rep.ok("alert surfaces reachable", "HTTP 200 / 200")
    live = st.get("n_live")
    open_ = sc.get("n_open")
    # THEY DISAGREED BY EXACTLY THE 8 ROWS ONE OF THEM WAS MIS-CLASSIFYING (item 29), so the
    # check is that the two surfaces agree rather than that either matches a number typed here.
    if live is not None and live == open_:
        rep.ok("alert LIVE count agrees with n_open", "%s == %s" % (live, open_))
    else:
        rep.bad("alert LIVE count agrees with n_open",
                "scream-track n_live %r vs scorecard n_open %r" % (live, open_))


def check_valuations(base, rep):
    for t in ("MSFT", "O", "NEE", "BRK.B"):
        code, d = get_json(base, "/api/value", method="POST", body={"ticker": t})
        fv = (d or {}).get("base_fair_value")
        if code == 200 and isinstance(fv, (int, float)) and fv > 0:
            regime = ((d or {}).get("classification") or {}).get("regime")
            rep.ok("value %s" % t, "fair value %.2f, regime %s" % (fv, regime))
        else:
            rep.bad("value %s" % t, "HTTP %s, base_fair_value %r" % (code, fv))

    # A COMPANY NOBODY IDENTIFIED MUST NOT GET A SCORE. This returned 200 with score 40 and
    # "Reduce" until item 25.
    code, d = get_json(base, "/api/value", method="POST", body={"ticker": "ZZZZQ"})
    score = ((d or {}).get("score") or {}).get("score")
    if code == 404 and score is None:
        rep.ok("value ZZZZQ is refused", "HTTP 404, no score")
    else:
        rep.bad("value ZZZZQ is refused", "HTTP %s, score %r" % (code, score))


def check_exports(base, rep):
    for kind, path, magic in (("xlsx", "/api/export/excel?ticker=MSFT", b"PK"),
                              ("pdf", "/api/export/pdf?ticker=MSFT", b"%PDF-")):
        code, raw, ctype = fetch(base, path)
        # MAGIC BYTES, NOT LENGTH. This app answers 200 with a JSON error body when an export
        # fails, and a JSON error is non-empty — so "non-empty" would pass on a broken export.
        if code == 200 and raw[:len(magic)] == magic and len(raw) > 2000:
            rep.ok("export %s" % kind, "%d bytes, starts %r" % (len(raw), magic))
        else:
            head = raw[:80].decode("utf-8", "replace")
            rep.bad("export %s" % kind,
                    "HTTP %s, %d bytes, starts %r" % (code, len(raw), head))


def check_signals(base, rep, now_utc):
    code, d = get_json(base, "/api/signals")
    if code != 200 or d is None:
        rep.bad("signals reachable", "HTTP %s" % code)
        return
    if d.get("empty"):
        rep.bad("signals reachable", "the feed is empty: %s" % str(d.get("message"))[:80])
        return
    rt = str(d.get("run_time") or "")
    rep.ok("signals reachable", "HTTP 200, run_time %s, %d rows"
           % (rt or "(none)", len(d.get("rows") or [])))

    today = now_utc.date()
    # THE CALENDAR DECIDES, NOT THE WEEKDAY: a market holiday is not a failure of the feed.
    if not MS.is_trading_day(today):
        rep.skip("signals ran during today's session",
                 "%s is not a trading day — nothing should have run" % today.isoformat())
        return
    if not (MARKET_OPEN_UTC <= now_utc.time() <= MARKET_CLOSE_UTC):
        rep.skip("signals ran during today's session",
                 "it is %s UTC, outside %s-%s, so today's feed is not due yet"
                 % (now_utc.strftime("%H:%M"), MARKET_OPEN_UTC.strftime("%H:%M"),
                    MARKET_CLOSE_UTC.strftime("%H:%M")))
        return
    d10, _, hhmm = rt.partition(" ")
    ok_date = d10 == today.isoformat()
    try:
        t = _dt.datetime.strptime(hhmm.strip()[:5], "%H:%M").time()
        ok_time = MARKET_OPEN_UTC <= t <= MARKET_CLOSE_UTC
    except Exception:                                                # noqa: BLE001
        ok_time = False
    if ok_date and ok_time:
        rep.ok("signals ran during today's session", "run_time %s" % rt)
    else:
        rep.bad("signals ran during today's session",
                "run_time %r (want %s between %s and %s UTC)"
                % (rt, today.isoformat(), MARKET_OPEN_UTC.strftime("%H:%M"),
                   MARKET_CLOSE_UTC.strftime("%H:%M")))


def check_pages(base, rep):
    """The pages a visitor actually opens. A 200 with HTML, not a redirect to an error."""
    for path, needle in (("/proof", b"RESEARCH DECILE"), ("/methodology", b"<html")):
        code, raw, _ = fetch(base, path)
        if code == 200 and needle in raw:
            rep.ok("page %s" % path, "HTTP 200, %d bytes" % len(raw))
        else:
            rep.bad("page %s" % path, "HTTP %s, %d bytes, needle %s"
                    % (code, len(raw), "present" if needle in raw else "ABSENT"))


# =============================================================================================
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Exercise the live site end to end.")
    ap.add_argument("--base", default=os.environ.get("LIVE_CHECK_BASE") or DEFAULT_BASE)
    a = ap.parse_args(argv)

    now_utc = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    session = MS.last_closed_session()
    state = MS.session_state()

    print("LIVE CHECK  %s" % a.base, flush=True)
    print("  now            %s UTC" % now_utc.strftime("%Y-%m-%d %H:%M"), flush=True)
    print("  last session   %s" % (session.isoformat() if session else "(none)"), flush=True)
    print("  session state  %s" % state.get("reason"), flush=True)
    print("-" * 100, flush=True)

    rep = Report()
    check_hot_list(a.base, rep, session)
    check_dip(a.base, rep)
    check_index(a.base, rep)
    check_index_track(a.base, rep, session)
    check_alert_surfaces(a.base, rep)
    check_valuations(a.base, rep)
    check_exports(a.base, rep)
    check_signals(a.base, rep, now_utc)
    check_pages(a.base, rep)
    return rep.finish()


if __name__ == "__main__":
    sys.exit(main())
