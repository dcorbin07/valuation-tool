# -*- coding: utf-8 -*-
"""`VALREADS` — the append-only weekly record of what the valuation page actually said.

    python -m scripts.valreads_record --selfcheck      # day 1, before anything is recorded
    python -m scripts.valreads_record                  # one week

**REGISTERED FIRST.** `PREREG_valuation_reads.md` is committed ALONE and is a strict git ancestor
of this file. It fixes the five reads, their declared signs, the population, the bars, the read
dates and the power statement. **This module records. It computes no outcome statistic, scores
nothing against a bar, and reads no forward return** — the last of those is asserted over this
module's own syntax tree by `tests/test_valreads.py`, not by grep, because a docstring describing
the rule contains the words the rule forbids (`MA49`/`MB1`, the substring-ban family).

WHY THIS EXISTS RATHER THAN A BACKFILL
--------------------------------------------------------------------------------------------
`V6` established the live sub-scores are not computable point-in-time, and `S23` measured that
path fetching **live Yahoo prices to value 1999**. So nothing can reconstruct what the page said
last year; a forward record is the only route. And the archive this project already has cannot
stand in: `archive.archive_scan` keeps the top 100 hot names a day and **none of these reads**,
while NVDA — item 52's own worked example — sits at hot rank 1,262.

THE THREE RULES THAT DECIDE THE SHAPE, each of them a measurement rather than a preference
--------------------------------------------------------------------------------------------
1. **A REFUSAL IS A RECORD, NEVER A BLANK.** `archive.py` is this project's own account of the
   opposite: it stored `fair_value` but neither the refusal flag nor its reason, so a permanent
   archive could not tell *"we declined to value this"* from *"we never tried"*. Every row here
   carries a `status` and, when refused, a `refused_reason`.
2. **THE CANARY GATE, AND IT REFUSES THE WHOLE WEEK.** The live feed's per-IP quota **does not
   raise when exhausted — it silently degrades `CompanyData`** (measured 2026-08-07: 302 of 403
   names arrived with `beta=None`, the tell being many names reporting one identical WACC as it
   collapses to pure cost of debt). A degraded week would be **fast, complete-looking and wrong**.
   So one known name is valued first and a degraded answer aborts before a single row is written.
   **A missing week is a fact a reader can see. A week of hollow reads recorded as reads is a lie**
   — and it is the direction that reads as a quiet record rather than as an error.
3. **ONE FILE PER WEEK, PLUS AN APPEND-ONLY MANIFEST, and the reason is cost rather than taste.**
   `append_only.append` rewrites the whole file per row, so appending ~542 rows a week into one
   growing CSV is quadratic and reaches ~141,000 rows by the first read date. Each week's rows
   therefore land in their own immutable file, and the **manifest** — one row per week — goes
   through `append_only.append(key="date", append_only=True)`, so the index of the record carries
   this project's own byte-prefix guarantee, its idempotent retry and its backfill refusal.
   **Nothing is re-implemented here** (`B7`): a second append-only writer is exactly the split
   `append_only.py`'s docstring exists to prevent.

WHAT A WEEK'S FILE IS NOT: it is not re-written, not re-ordered and not corrected. A week already
on disk is REFUSED rather than replaced, because a record whose past can be edited is not evidence.
"""
from __future__ import annotations

import csv
import io
import json
import os
import time
from typing import Optional

from . import append_only as AO

#: The canary. A name the product values on every scan, so "it did not resolve" is a fact about
#: the feed rather than about the ticker — `stooq-is-dead`'s control lesson, where a primary
#: vendor 404ing for *every* symbol was only distinguishable from missing tickers by a control.
CANARY = "AAPL"

#: Serial pacing, from the measured recovery behaviour rather than chosen: a paced 46-name sample
#: completed clean in 2.2 minutes where 400 names at 6 workers throttled 176 of 402.
PACE_S = 1.5

#: THE POPULATION RULE, FIXED IN THE REGISTER'S §3 BEFORE ANY ROW EXISTED AND FROZEN HERE.
#: The union of the published hot list's served rows and every published Index constituent.
#: Measured 2026-10-13: the hot route caps at 500 whatever `top` asks for; the Index carries 86
#: positions and only 44 of them are INSIDE that 500 — so a hot-list-only population would have
#: omitted 42 names of the product's own book. Changing this rule VOIDS the item (register §8.1).
BASE_URL = "https://valquo.co"
HOT_PATH = "/api/hotstocks?top=500"
INDEX_PATH = "/api/valquo-index"

#: Both routes are PUBLIC and TOKENLESS, which is why the recorder can run on a free runner with
#: no secret at all. It never reads `.env` and never needs the admin token.
TOKENLESS = True

#: One row per (date, ticker). The key is `date|ticker`, which sorts correctly as a string --
#: "2026-10-20|AAPL" < "2026-10-20|ZZZ" < "2026-10-27|AAPL" -- so the manifest's append-only
#: ordering check means what it says.
ROW_COLUMNS = (
    "key", "date", "ticker", "source", "status", "refused_reason",
    # what the page was looking at
    "price", "market_cap", "regime", "dcf_reliability",
    # the five sub-scores. RECORDED, and NOT registered arms -- they are the register's own
    # power control (§6), because `business_quality` is a weighted mean of four of them.
    "sub_valuation", "sub_quality", "sub_growth", "sub_health", "sub_momentum",
    # THE FIVE READS UNDER TEST (register §1), each with the page's own words beside the number
    # so a successor can tell a changed threshold from a changed value.
    "business_quality", "business_quality_score",
    "price_vs_model", "price_vs_model_pct",
    "price_implied_growth", "business_growth", "story_gap_pp", "is_story_stock",
    # AMENDMENT 1: a FINANCIAL's implied figure is an implied RETURN ON EQUITY, not a growth
    # rate -- `price_assumes` takes a deliberate separate branch for it under the same `implied`
    # key. Two quantities in one column is the wrong-object family, so they get two columns and
    # these two carry NO registered arm.
    "price_implied_roe", "book_roe", "implied_is_roe", "page_implied_available",
    "warning", "warning_triggers",
    # the valuation the reads are about
    "base_value", "value_low", "value_high", "valuable", "withheld",
    "blend_method", "growth_led", "hot_score", "hot_rank",
    # provenance -- the composite's own score, so a changed scoring version is visible
    "page_score", "confidence",
)

MANIFEST_COLUMNS = (
    "date", "recorded_at_utc", "rows", "n_valued", "n_refused",
    "n_population", "n_hot", "n_index", "n_index_outside_hot",
    "canary", "canary_seconds", "seconds_total", "rows_file", "rows_sha256",
    "register", "recorder_version", "note",
)

REFUSAL_COLUMNS = ("at_utc", "date", "stage", "reason", "canary", "recorder_version")

#: Bumped when the RECORDED SHAPE changes, so a reader can tell a schema change from a data
#: change. It is NOT a bar and gates nothing.
RECORDER_VERSION = "1"

REGISTER = "PREREG_valuation_reads.md"


# ----------------------------------------------------------------------------------------------
# where the record lives
# ----------------------------------------------------------------------------------------------
def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def export_root(root: Optional[str] = None) -> str:
    """`data_export/valreads`.

    **`data_export/` and not `data/`, deliberately.** `data/` is gitignored, so a record living
    there would exist only on whichever machine or runner wrote it — and this project has twice
    lost an artifact to exactly that (`MA28_CARD.json` and `I2_BURN_IN_CENSUS.json`, both
    stranded in a worktree that was later deleted). `data_export/` is the tracked directory the
    forward Index record is already backed up into, so the backup route exists rather than being
    invented here.
    """
    return os.path.join(root or repo_root(), "data_export", "valreads")


def rows_path(date, root: Optional[str] = None) -> str:
    return os.path.join(export_root(root), "VALREADS_%s.csv" % date)


def manifest_path(root: Optional[str] = None) -> str:
    return os.path.join(export_root(root), "VALREADS_MANIFEST.csv")


def refusals_path(root: Optional[str] = None) -> str:
    return os.path.join(export_root(root), "VALREADS_REFUSALS.csv")


# ----------------------------------------------------------------------------------------------
# the population
# ----------------------------------------------------------------------------------------------
def fetch_population(base: str = BASE_URL, timeout: int = 60) -> dict:
    """The register's §3 union, with the counts that make a cap change visible.

    **The counts are stamped on the manifest rather than assumed stable.** The hot route's 500
    is a server-side constant this lane does not own and the Index rebalances, so the RULE is
    frozen and the realised COUNT is recorded. A cap change then shows up in the record instead
    of silently shrinking the population.
    """
    import urllib.request
    out = {"hot": [], "index": [], "error": ""}
    try:
        with urllib.request.urlopen(base + HOT_PATH, timeout=timeout) as r:
            h = json.load(r)
        out["hot_scan_date"] = h.get("scan_date") or ""
        for x in (h.get("rows") or []):
            t = (x.get("ticker") or "").strip().upper()
            if t:
                out["hot"].append({"ticker": t, "hot_score": x.get("hot_score"),
                                   "hot_rank": x.get("rank")})
    except Exception as e:                                                  # noqa: BLE001
        out["error"] = "hot list unreachable: " + repr(e)[:160]
        return out
    try:
        with urllib.request.urlopen(base + INDEX_PATH, timeout=timeout) as r:
            d = json.load(r)
        for p in (d.get("positions") or []):
            t = (p.get("ticker") or "").strip().upper()
            if t:
                out["index"].append(t)
    except Exception as e:                                                  # noqa: BLE001
        # THE INDEX LEG IS REQUIRED, NOT BEST-EFFORT. Falling back to the hot list alone would
        # silently record the exact population the register rejected, and the record would not
        # say so. Refusing the week is the honest direction.
        out["error"] = "index unreachable: " + repr(e)[:160]
        return out
    hot_t = {r["ticker"] for r in out["hot"]}
    idx_t = set(out["index"])
    out["n_hot"] = len(hot_t)
    out["n_index"] = len(idx_t)
    out["n_index_outside_hot"] = len(idx_t - hot_t)
    by = {r["ticker"]: r for r in out["hot"]}
    names = []
    for t in sorted(hot_t | idx_t):
        r = by.get(t) or {}
        names.append({
            "ticker": t,
            "hot_score": r.get("hot_score"),
            "hot_rank": r.get("hot_rank"),
            "source": ("both" if (t in hot_t and t in idx_t) else
                       ("hot" if t in hot_t else "index")),
        })
    out["names"] = names
    out["n_population"] = len(names)
    return out


# ----------------------------------------------------------------------------------------------
# one name
# ----------------------------------------------------------------------------------------------
def _num(v):
    if v is None:
        return ""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return "" if f != f else repr(round(f, 8))


def read_one(ticker: str, meta: Optional[dict] = None) -> dict:
    """Value one name and record **what the page would have said about it**.

    The five reads come from the SAME functions the page calls — `scoring.business_quality`,
    `scoring.price_vs_model`, `price_assumes.price_assumes` and `price_assumes.dcf_warning` —
    rather than being re-derived here, so a changed threshold moves the record and the page
    together. `tests/test_valreads.py` gates that by comparing this assembly field for field
    against `app._price_assumes_block` on a real result; the assembly is ~15 shared lines and
    the gate is what stops it drifting into a second definition of the reads (`B7`).

    **NEVER RAISES.** A name that cannot be valued is a RECORD with `status=REFUSED` and a
    reason, because rule 1 above is the whole point of the file.
    """
    meta = meta or {}
    row = {c: "" for c in ROW_COLUMNS}
    row["ticker"] = ticker
    row["source"] = meta.get("source") or ""
    row["hot_score"] = _num(meta.get("hot_score"))
    row["hot_rank"] = ("" if meta.get("hot_rank") in (None, "")
                       else str(int(meta["hot_rank"])))

    from ..engine import pipeline as P
    from ..engine import scoring as SC
    from ..web import price_assumes as PA

    try:
        res = P.value_ticker(ticker, run_ai=False)
    except Exception as e:                                                  # noqa: BLE001
        row["status"] = "REFUSED"
        row["refused_reason"] = ("value_ticker raised: " + repr(e)[:200])
        return row

    cd = getattr(res, "company", None)
    if cd is None or getattr(cd, "fetch_failed", False):
        row["status"] = "REFUSED"
        row["refused_reason"] = "no company data (fetch failed or symbol not found)"
        return row

    cls = getattr(res, "classification", None)
    blend = getattr(res, "fair_value_blend", None)
    sc = getattr(res, "score", None)
    rev = getattr(res, "reverse", None)
    regime = str(getattr(cls, "regime", "") or "")
    is_fin = regime == "financial"

    row["price"] = _num(getattr(cd, "price", None))
    row["market_cap"] = _num(getattr(cd, "market_cap", None))
    row["regime"] = regime
    row["dcf_reliability"] = str(getattr(cls, "dcf_reliability", "") or "")

    subs = dict(getattr(sc, "subscores", None) or {})
    for k in ("valuation", "quality", "growth", "health", "momentum"):
        row["sub_" + k] = _num(subs.get(k))
    row["page_score"] = ("" if sc is None else str(getattr(sc, "score", "") or ""))
    row["confidence"] = ("" if sc is None else str(getattr(sc, "confidence", "") or ""))

    # READ 1 and READ 2 -- the page's own words AND the numbers behind them.
    row["business_quality"] = ("" if sc is None else str(getattr(sc, "business_quality", "")
                                                        or ""))
    row["business_quality_score"] = ("" if sc is None
                                     else _num(getattr(sc, "business_quality_score", None)))
    row["price_vs_model"] = ("" if sc is None else str(getattr(sc, "price_vs_model", "") or ""))

    base = getattr(res, "base_fair_value", None)
    withheld = getattr(blend, "withheld_value", None) if blend is not None else None
    row["base_value"] = _num(base)
    row["value_low"] = _num(getattr(blend, "value_low", None) if blend is not None else None)
    row["value_high"] = _num(getattr(blend, "value_high", None) if blend is not None else None)
    row["valuable"] = ("" if blend is None else ("1" if getattr(blend, "valuable", False)
                                                else "0"))
    row["withheld"] = ("1" if withheld not in (None, "") else "0")
    row["blend_method"] = ("" if blend is None else str(getattr(blend, "method", "") or ""))
    row["growth_led"] = ("" if blend is None else ("1" if getattr(blend, "growth_led", False)
                                                  else "0"))

    # `price_vs_model_pct` IS THE NUMBER THE SENTENCE RENDERS, and it is derived from the same
    # pair the sentence uses rather than from a second source. The register tests the NUMBER;
    # the words are recorded beside it so a re-wording is distinguishable from a re-valuation.
    try:
        pr = float(getattr(cd, "price", None))
        bv = float(base) if base not in (None, "") else None
        row["price_vs_model_pct"] = ("" if not bv else _num(pr / bv - 1.0))
    except (TypeError, ValueError):
        row["price_vs_model_pct"] = ""

    # READS 3, 4 and 5. The business's own LAST-YEAR growth, from the engine's accessor --
    # `blended_growth` is deliberately not used, for item 52's own reason: it mixes a 3-year
    # CAGR with an analyst figure, and the sentence is a measurement of the PAST.
    biz = None
    try:
        biz = cd.revenue_growth(1)
    except Exception:                                                       # noqa: BLE001
        biz = None
    row["business_growth"] = _num(biz)

    # `financial_surfaces`, AND THE FIELD NAME IS A LIVE DEFECT IN ANOTHER LANE'S FILE.
    # `app.py:369` reads `result.financial_extras`, which does not exist on `ValuationResult`
    # at all -- the field is `financial_surfaces` (`pipeline.py:123`). So on the live page
    # `implied_roe` is ALWAYS `None` for a financial, `price_assumes` takes its `available:
    # False` branch, and every bank renders *"We could not work out what return on equity this
    # price assumes"* while the engine has the number sitting there (ABCB: 0.1220). REPORTED,
    # NOT FIXED -- `app.py` is the app lane's and changing what the page renders is a public
    # copy change this lane is barred from. The RECORDER reads the correct field, so the record
    # carries the engine's own figure, and `page_implied_available` records whether the PAGE
    # showed anything -- two different facts, and collapsing them would hide the defect.
    fin_rev = (getattr(res, "financial_surfaces", None) or {}) if is_fin else {}
    fin_rev = (fin_rev.get("reverse") or {}) if isinstance(fin_rev, dict) else {}
    try:
        lead = PA.price_assumes(
            rev, biz, is_financial=is_fin,
            implied_roe=(fin_rev.get("implied_roe") if is_fin else None),
            # `reverse.current_roe` is the engine's own measured book ROE. `app.py` passes
            # `cd.roe`, which on ABCB is `None` -- so the two are NOT the same source and the
            # column is named for what it holds rather than for what the page passes.
            book_roe=((fin_rev.get("current_roe") if is_fin else None)))
        # AMENDMENT 1, AND IT IS A DEFECT IN MY OWN FIRST CUT, CAUGHT BY BUILDING THE RECORDER
        # RATHER THAN BY READING THE REGISTER. For a financial `price_assumes` returns an
        # implied RETURN ON EQUITY under the same `implied` key -- its own comment: *"a bank's
        # value is not a discounted free-cash-flow stream, so 'what growth does the price
        # assume' is the wrong question"*. Writing it into a column named for a growth rate
        # would have made any IC on `R3-PIG` a mixture of two quantities, and it would have
        # computed cleanly and raised nothing. The two are SEPARATED, and the ROE column
        # carries no registered arm.
        row["implied_is_roe"] = "1" if is_fin else "0"
        row["page_implied_available"] = "1" if lead.get("available") else "0"
        if is_fin:
            row["price_implied_roe"] = _num(lead.get("implied"))
            row["book_roe"] = _num(lead.get("business"))
        else:
            row["price_implied_growth"] = _num(lead.get("implied"))
        # `story_gap_pp` RETURNS `None` AND NOT 0.0 WHEN EITHER LEG IS ABSENT, which is why the
        # blank is preserved rather than coerced: a missing gap and a zero gap are different
        # facts, and the register's own expectation 3 is about how often it is missing.
        row["story_gap_pp"] = _num(lead.get("gap_pp"))
        row["is_story_stock"] = ("1" if PA.is_story_stock(rev, biz) else "0")
    except Exception as e:                                                  # noqa: BLE001
        row["refused_reason"] = "price_assumes raised: " + repr(e)[:120]

    try:
        warn = PA.dcf_warning(
            regime=regime,
            dcf_reliability=str(getattr(cls, "dcf_reliability", "") or ""),
            cash_burning=bool(getattr(cls, "cash_burning", False)),
            growth_led=bool(getattr(blend, "growth_led", False) if blend is not None else False),
            reverse=rev, business_growth=biz)
        trg = list(warn.get("triggers") or [])
        row["warning"] = "1" if trg else "0"
        # WHICH RULE FIRED, per name. `STORY_GAP_PP = 15.0` is in item 52's own words "a
        # disclosure threshold and is calibrated against nothing", so the trigger list is the
        # only thing that lets a successor tell a real signal from one rule carrying all of it.
        # The register registers NO per-rule arm and forbids reading one (§8.5).
        row["warning_triggers"] = "|".join(str(t) for t in trg)
    except Exception as e:                                                  # noqa: BLE001
        row["refused_reason"] = ((row["refused_reason"] + "; ") if row["refused_reason"] else ""
                                 ) + "dcf_warning raised: " + repr(e)[:120]

    # A row whose VALUATION resolved but one of whose reads did not is PARTIAL, not REFUSED and
    # not OK. Three states, because collapsing them loses exactly the distinction rule 1 is for.
    if row["refused_reason"]:
        row["status"] = "PARTIAL"
    elif row["business_quality_score"] == "" and row["price_vs_model_pct"] == "":
        row["status"] = "PARTIAL"
        row["refused_reason"] = "valued, but neither registered read resolved"
    else:
        row["status"] = "OK"
    # DEFENSIVE, AND IT IS THE `scoring.py` LESSON: `SC` is imported so the record is built from
    # the page's own vocabulary rather than from retyped band labels. If the module ever stops
    # exposing them the record should go red, not quietly lose a column.
    assert hasattr(SC, "business_quality") and hasattr(SC, "price_vs_model")
    return row


# ----------------------------------------------------------------------------------------------
# contamination
# ----------------------------------------------------------------------------------------------
def canary_ok(row: dict) -> tuple:
    """`(ok, why)` for the canary row. Rule 2 above.

    A throttled feed does not raise, so the only honest check is on the DATA. Three independent
    tells, and the sharpest is not here but in `week_degraded` — many names sharing one WACC.
    """
    if row.get("status") == "REFUSED":
        return False, ("the canary %s refused: %s" % (CANARY, row.get("refused_reason") or "?"))
    if not row.get("price"):
        return False, "the canary came back with no price"
    if not row.get("market_cap"):
        return False, ("the canary came back with no market cap, which is what a throttled feed "
                       "looks like: it does not raise, it empties CompanyData")
    return True, ""


def week_degraded(rows) -> tuple:
    """`(degraded, why)` across a part-finished week, checked CONTINUOUSLY by the runner.

    Measured mid-run rather than afterwards, so a spoiled week is stopped instead of being
    discovered once the figure is already on disk.
    """
    done = [r for r in rows if r.get("status") in ("OK", "PARTIAL")]
    if len(done) < 20:
        return False, ""
    no_cap = [r for r in done if not r.get("market_cap")]
    if len(no_cap) > len(done) // 2:
        return True, ("%d of %d valued names carry no market cap -- the 2026-08-07 throttle "
                      "signature" % (len(no_cap), len(done)))
    return False, ""


# ----------------------------------------------------------------------------------------------
# writing
# ----------------------------------------------------------------------------------------------
def _sha256_of(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_week(date, rows, *, root: Optional[str] = None) -> dict:
    """Write one week's rows to their own immutable file. A week already on disk is REFUSED.

    **Not replaced, not merged, not corrected.** A record whose past can be rewritten is not
    evidence, and a retry that silently produced different numbers for the same date would be
    indistinguishable from the first attempt having been right.
    """
    p = rows_path(date, root)
    if os.path.exists(p):
        return {"ok": False, "wrote": False, "path": p,
                "reason": ("refusing to rewrite %s: this week is already recorded, and the "
                           "record is append-only. A correction is a new register, not an "
                           "edit." % p)}
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ROW_COLUMNS))
        w.writeheader()
        for r in rows:
            out = {c: r.get(c, "") for c in ROW_COLUMNS}
            out["date"] = date
            out["key"] = "%s|%s" % (date, r.get("ticker") or "")
            w.writerow(out)
    os.replace(tmp, p)                      # MA4's rule: never `open(path, "w")` in place
    return {"ok": True, "wrote": True, "path": p, "rows": len(rows),
            "sha256": _sha256_of(p), "reason": ""}


def append_manifest(entry: dict, *, root: Optional[str] = None) -> dict:
    """One manifest row per week, through the ONE append-only writer.

    `append_only=True` gives, unchanged and un-re-implemented: a duplicate date is an idempotent
    NO-OP returning the row already on disk, a backward date is REFUSED, a schema change is
    REFUSED, and the file's previous bytes stay an exact prefix of the new file.
    """
    return AO.append(
        dict(entry), manifest_path(root), key="date", columns=list(MANIFEST_COLUMNS),
        append_only=True,
        backfill_hint=(" The record is forward-only by register (PREREG_valuation_reads.md "
                       "§8.2); there is no backfill door."))


def log_refusal(stage: str, reason: str, *, date="", canary="",
                root: Optional[str] = None) -> dict:
    """A refused WEEK is recorded and dated, and it does NOT consume the week's manifest key.

    Keyed on the attempt's timestamp rather than on the date, deliberately: a quota that resets
    should let the same week be recorded properly on a retry, and a manifest row claiming the
    week was refused would make that retry an idempotent no-op — the record would then be
    permanently missing a week that was recoverable.
    """
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return AO.append(
        {"at_utc": at, "date": date, "stage": stage, "reason": reason, "canary": canary,
         "recorder_version": RECORDER_VERSION},
        refusals_path(root), key="at_utc", columns=list(REFUSAL_COLUMNS), append_only=True)


def read_week(date, *, root: Optional[str] = None) -> tuple:
    """`(rows, header, error)` for one week, through `append_only.read_rows`.

    Delegated so a ragged file is REPORTED rather than repaired — `csv.DictReader` files surplus
    cells under one key and pads short rows, so a reader that normalised would quietly discard or
    invent cells.
    """
    return AO.read_rows(rows_path(date, root))
