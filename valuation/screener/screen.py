"""
The scan — turn a universe into a ranked list of "hot" buy candidates.

Flow: pull the universe → fetch each name's metrics (cached) → apply liquidity/
hygiene gates → build standardized factors → composite-score within each bucket →
convert to a 1–100 hot score by cross-sectional percentile → rank. Optionally run
the full adaptive DCF on just the top names to attach a fair-value gap to the
winners (cheap, because it's only the top dozen, not the whole market).

Results are saved as a dated snapshot so the web UI reads instantly and we keep a
week-over-week history.
"""
from __future__ import annotations

import collections
import datetime as _dt
from typing import Optional, Callable

import numpy as np
import pandas as pd

from ..config import CONFIG
from . import settings as S
from .attribution import decompose, p_established as _p_established
from .factors import build_frame, prefilter
from .providers import get_provider
from .store import Store

# LA1 — how many times the DCF pass tries a name before failing open. Two, not more: the
# upstream feed is free and rate-limited, and the point is to absorb ONE flaky call, not to
# hammer a name that is genuinely unreachable. A failure after this is COUNTED, stamped on the
# row as `dcf_error`, and re-asked by the cheap refusal-only screen.
DCF_ATTEMPTS = 2

# LA1 — A MOP-UP PASS WAS BUILT HERE AND IS DELIBERATELY NOT USED. The record of why is the
# point, so it stays.
#
# The bulk refusal screen runs 8 workers over ~488 names against a free rate-limited feed; 13
# came back with NO statements and NO exception. Re-asked at TWO workers they ALL returned data
# — 12 valued and KSPI refused at 5.6x — which looked like proof the leak was our own
# instantaneous request rate, so a slow second pass was added.
#
# IT MADE THINGS WORSE: `no_data` went 13 -> 32 on the very next full scan, because the binding
# constraint is CUMULATIVE quota across the whole scan, not concurrency, and the mop-up spent
# more of it. The small-scale measurement was real and the inference from it was wrong.
#
# The residue now FAILS CLOSED instead, which costs no requests at all. Keep this off.
NO_DATA_RETRY_WORKERS = 2      # unused; retained with the measurement above


def _effective_weights(store):
    """Live weights = the latest self-learning-adopted weights, else the defaults."""
    est = (store.latest_learned_weights("established") if store else None) or S.WEIGHTS_ESTABLISHED
    spec = (store.latest_learned_weights("speculative") if store else None) or S.WEIGHTS_SPECULATIVE
    return est, spec


def _decompose(df: pd.DataFrame, est_w=None, spec_w=None, soft=None):
    """(composite, per-theme contributions). The composite IS the row-sum of the pieces.

    Both live in `attribution.py` so the score and the explanation of the score cannot come
    from two different calculations — the failure mode where a "why" panel quietly stops
    describing the ranking it sits next to.
    """
    est_w = est_w or S.WEIGHTS_ESTABLISHED
    spec_w = spec_w or S.WEIGHTS_SPECULATIVE
    if soft is None:
        soft = getattr(CONFIG, "soft_bucket", True)
    return decompose(df, est_w, spec_w, soft=soft)


def _composites(df: pd.DataFrame, est_w=None, spec_w=None, soft=None) -> pd.Series:
    return _decompose(df, est_w, spec_w, soft)[0]


def _rows_from(scored: pd.DataFrame) -> list:
    rows = []
    for tkr, r in scored.iterrows():
        extra = {k: (None if pd.isna(r.get(k)) else float(r.get(k)))
                 for k in ["earnings_yield", "fcf_yield", "ev_ebitda", "ev_sales", "pe",
                           "op_margin", "roic", "revenue_growth", "ret_12_1", "net_debt_to_ebitda",
                           # net_debt + revenue let fairvalue.py bridge EV multiples to a
                           # per-share equity value and run the growth (revenue) lens.
                           "net_debt", "revenue", "gross_margin"]
                 if k in scored.columns}
        # Persist EVERY theme column (not just the legacy five) so the monthly
        # learner can tune the newer themes too. Legacy z_* columns stay for the UI.
        extra["factors"] = {f: _f(r.get(f)) for f in S.FACTORS_ALL if f in scored.columns}
        # Persist each individual number's z-score too, so the Edge Lab can measure
        # each number's standalone predictive power over time (visibility only).
        extra["numbers"] = {n: _f(r.get("z_" + n)) for n in S.NUMBERS_ALL if ("z_" + n) in scored.columns}
        extra["vol"] = _f(r.get("realized_vol"))       # for inverse-volatility position sizing
        # Which feed this row's fundamentals came from ("free+broker", "broker", "free").
        # Carried per NAME, not just as a scan-level total, because the two sources cover
        # different fields — a broker-only row has no margins, FCF or revenue growth, so its
        # score rests on fewer themes and a reader comparing two picks should be able to see
        # that rather than infer it.
        src = r.get("source")
        extra["source"] = None if (src is None or (isinstance(src, float) and pd.isna(src))) else str(src)
        rows.append({
            "ticker": tkr, "name": r.get("name") or tkr, "sector": r.get("sector") or "",
            "bucket": r.get("bucket"), "price": _f(r.get("price")), "market_cap": _f(r.get("market_cap")),
            "hot_score": _f(r.get("hot_score")), "composite": _f(r.get("composite")),
            "rank": int(r.get("rank")),
            "z_value": _f(r.get("value")), "z_quality": _f(r.get("quality")),
            "z_growth": _f(r.get("growth")), "z_momentum": _f(r.get("momentum")),
            "z_insider": _f(r.get("insider")), "fair_value": None, "upside": None, "extra": extra,
        })
    return rows


def _theme_contribution(scored: pd.DataFrame) -> dict:
    """Fraction of names each theme actually scores, measured after standardization.

    A theme that is present but constant across the cross-section carries no information:
    zscore() divides by a zero standard deviation and returns all-NaN, and composite_score
    then renormalizes the remaining weights over the themes that survive. Reported next to
    theme_coverage so "the column is full" and "the theme moves the score" stay distinct.
    """
    from .cross_sectional import standardize_factors
    cols = [t for t in S.FACTORS_ALL if t in scored.columns]
    if not cols or scored.empty:
        return {}
    z = standardize_factors(scored, cols)
    return {t: round(float(z[t].notna().mean()), 2) for t in cols}


def _cov(rows: list, ok) -> float:
    """Fraction of rows for which `ok` holds — used for the display-field health panel."""
    if not rows:
        return 0.0
    return round(sum(1 for r in rows if ok(r)) / len(rows), 3)


def _fill_from_universe(m: dict, u: Optional[dict]) -> dict:
    """Backfill display fields the per-name fetch didn't supply, from the universe listing.

    Only fills what is genuinely missing, so a real fetched value always wins. A `name` equal
    to the ticker counts as missing: that is what the Yahoo path falls back to when its `.info`
    call is throttled, and "DELL" is not a company name. Market cap is a display/eligibility
    field here, and the listing reports it in USD dollars like everything else.
    """
    if not u:
        return m
    tkr = (m.get("ticker") or u.get("ticker") or "").upper()
    if not (m.get("name") or "").strip() or (m.get("name") or "").strip().upper() == tkr:
        if (u.get("name") or "").strip():
            m["name"] = u["name"]
    for k in ("sector", "industry"):
        if not (m.get(k) or "").strip() and (u.get(k) or "").strip():
            m[k] = u[k]
    # Live quote fields the broker supplies for free with the universe (price, average
    # dollar volume, nearness to the 52-week high). Only used where the fundamentals feed
    # left a hole — which for `high_prox` is every FMP row, so momentum gains an input it
    # never had rather than having one overwritten.
    for k in ("price", "avg_dollar_volume", "high_prox"):
        if m.get(k) is None and u.get(k) is not None:
            m[k] = u[k]
    if not m.get("market_cap") and u.get("market_cap"):
        m["market_cap"] = u["market_cap"]
    return m


def _f(x):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def run_scan(scope: str = "bundled", limit: Optional[int] = None, cfg=CONFIG,
             store: Optional[Store] = None, provider=None, run_dcf_top: int = 0,
             progress: Optional[Callable] = None, save: bool = True,
             refusal_screen: int = 0) -> dict:
    """`refusal_screen` = how many ranked names to ASK whether the model refuses them.

    Defaults to 0 so nothing that calls this in-process (tests, ad-hoc scans, the web
    "rescan" button) starts making hundreds of network calls it did not ask for. The
    scheduled scan sets it to the size of the served list — see `scripts/ci_scan.py`.
    """
    store = store or Store()
    provider = provider or get_provider(cfg, store)

    uni = provider.get_universe(scope)
    if limit:
        uni = uni[:limit]
    # The universe listing already carries a company name / sector / market cap (FMP's
    # screener returns all three; SEC EDGAR's filer list returns the legal name). The
    # per-name fetch does NOT reliably re-supply them — yfinance's `.info` is rate-limited
    # from cloud IPs and comes back empty, which is how the book ended up showing bare
    # tickers and an "unknown" sector breakdown. Keep the listing's values as a fallback.
    hints = {u["ticker"]: u for u in uni}

    # Bulk-load fundamentals for the whole universe up front, where the provider supports it.
    # The broker serves 100 symbols per call, so this is ~3 calls per 100 names against a feed
    # that is already paid for — versus one metered per-name round trip each. Optional by
    # contract: a provider without prefetch() behaves exactly as it did before.
    if hasattr(provider, "prefetch"):
        try:
            provider.prefetch([u["ticker"] for u in uni])
        except Exception:
            pass

    total = len(uni)
    workers = max(1, int(getattr(cfg, "scan_workers", 8) or 8)) if cfg is not None else 8

    # Fetch metrics concurrently — each get_metrics is I/O-bound (network), so a bounded
    # thread pool cuts a whole-market scan from ~sequential minutes to a fraction. Results
    # are keyed by ticker, then processed in the original order for deterministic output.
    fetched = {}
    if workers > 1 and total > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(provider.get_metrics, u["ticker"]): u["ticker"] for u in uni}
            for fut in as_completed(futs):
                try:
                    fetched[futs[fut]] = fut.result()
                except Exception:
                    fetched[futs[fut]] = None
                done += 1
                if progress and done % 50 == 0:
                    progress(done, total)
    else:
        for i, u in enumerate(uni):
            try:
                fetched[u["ticker"]] = provider.get_metrics(u["ticker"])
            except Exception:
                fetched[u["ticker"]] = None
            if progress and i % 25 == 0:
                progress(i, total)

    metrics = []
    filtered = {}          # reason -> count
    filtered_examples = {}  # reason -> sample tickers
    for u in uni:
        m = fetched.get(u["ticker"])
        if not m:
            filtered["no data"] = filtered.get("no data", 0) + 1
            continue
        _fill_from_universe(m, hints.get(u["ticker"]))
        m.setdefault("ticker", u["ticker"])
        keep, reason = prefilter(m)
        if not keep:
            filtered[reason] = filtered.get(reason, 0) + 1
            ex = filtered_examples.setdefault(reason, [])
            if len(ex) < 8:
                ex.append(m["ticker"])
            continue
        metrics.append(m)

    audit = {"total_removed": sum(filtered.values()), "by_reason": filtered,
             "examples": filtered_examples}

    if not metrics:
        return {"scan_date": _today(), "rows": [], "universe_size": total,
                "scored": 0, "filtered": audit}

    df = build_frame(metrics)
    est_w, spec_w = _effective_weights(store)
    df["composite"], contrib = _decompose(df, est_w, spec_w)
    scored = df[df["composite"].notna()].copy()
    if scored.empty:
        return {"scan_date": _today(), "rows": [], "universe_size": total, "scored": 0}

    scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1
    scored = scored.sort_values("composite", ascending=False)
    scored["rank"] = range(1, len(scored) + 1)
    rows = _rows_from(scored)

    # Per-pick "why" — the exact decomposition of this name's composite into per-theme
    # contributions, biggest mover first, so a pick is explainable ("here because: quality,
    # value; held back by: momentum") rather than a bare number.
    #
    # These come from `decompose()`, the same call that produced the composite, so they SUM
    # to it. The previous version multiplied the stored weight by the pre-standardization
    # theme value and by whichever weight set the hard bucket named — it ranked the themes
    # roughly right but its numbers added up to nothing in particular, and under soft
    # bucketing it credited a weight set the name was only partly scored under.
    from .attribution import row_attribution
    for r in rows:
        tkr = r["ticker"]
        r["extra"]["why"] = row_attribution(contrib.loc[tkr]) if tkr in contrib.index else []
        r["extra"]["why_composite"] = r.get("composite")

    # Deep-value the top names with the full DCF (optional, network-heavy).
    dcf_errors: dict = {}
    if run_dcf_top and run_dcf_top > 0:
        dcf_errors = _enrich_with_dcf(rows[:run_dcf_top], cfg) or {}
        # Stamp the failure ON THE ROW. LA1's whole mechanism was that a fail-open left no
        # trace anywhere, so the row was indistinguishable from one that had never been asked.
        for r in rows[:run_dcf_top]:
            if r.get("ticker") in dcf_errors:
                r["dcf_error"] = dcf_errors[r["ticker"]]
    # ...and ask every OTHER served name only whether the model REFUSES it. Without this the
    # names outside the DCF window publish a peer estimate that nothing has ever checked
    # against the valuation page's verdict (Bug B). Off by default in-process so tests and
    # ad-hoc scans do not hit the network; the scheduled scan turns it on.
    if refusal_screen:
        health_refusals = _screen_refusals(rows[run_dcf_top:refusal_screen], cfg, workers)
        # LA1 — CLOSE THE COUNTER HOLE. The screen ran on `rows[run_dcf_top:]`, so the top
        # `SCAN_DCF_TOP` rows — the most-read on the site, and the ones the audit found the
        # defect on — were excluded from it by construction. Any DCF-window row that came back
        # SILENT (no value, no refusal) is re-asked here with the cheap refusal-only pass.
        # Rows that already hold a good DCF value are deliberately NOT re-fetched: that buys
        # nothing and doubles their cost.
        retry = [r for r in rows[:run_dcf_top]
                 if r.get("fair_value") is None and not r.get("fair_value_withheld")]
        if retry:
            again = _screen_refusals(retry, cfg, workers)
            health_refusals = _merge_screen(health_refusals, again,
                                            dcf_window_rescreened=len(retry))
        # NO MOP-UP PASS. One was built and it MADE THINGS WORSE — see NO_DATA_RETRY_WORKERS
        # below for the measurement. The residue now fails closed instead, which needs no
        # extra requests at all.
    else:
        health_refusals = {"screened": 0, "refused": 0, "errors": 0,
                           "note": "refusal screen off"}

    # Data-health panel — catch silent data rot (a whole theme going missing, coverage
    # cratering) the day it happens, instead of finding out via bad picks weeks later.
    health = {
        "universe": total,
        "fetched": int(sum(1 for v in fetched.values() if v)),
        "passed_filter": len(metrics),
        "scored": len(rows),
        "theme_coverage": {t: round(float(scored[t].notna().mean()), 2)
                           for t in S.FACTORS_ALL if t in scored.columns},
        # PRESENT is not the same as USABLE, and reporting only the former is how a dead
        # theme hides in plain sight. `insider` is the live example: with no insider_score in
        # the metrics, build_frame sets the whole column to the constant 0.0 — so it is 100%
        # "covered", yet zscore() of a zero-variance column is all-NaN, composite_score
        # renormalizes it away, and its 12.5% weight does nothing. This measures the theme
        # AFTER standardization, i.e. what actually reaches the score.
        "theme_contributing": _theme_contribution(scored),
        # How many served names were actually ASKED whether the model refuses them, and how
        # many it did. `screened: 0` on a scan that served hundreds of names is the tell that
        # Bug B is back — a silent zero here is exactly how the gap survived unnoticed.
        "refusal_screen": health_refusals,
        # LA1's detector, run on EVERY scan. `asked_but_silent` is the rule that catches the
        # class the cold audit found on rank 1 of the public list; `band_breach` is the
        # invariant that nothing served may exceed the 5x band unwithheld. Reported separately
        # on purpose: a green `band_breach` is NOT evidence the LA1 class is absent, because a
        # refused 11x model is replaced by a peer estimate that sits inside the band.
        "publication_audit": publication_audit(
            rows[:refusal_screen] if refusal_screen else rows,
            dcf_window=min(run_dcf_top or 0, refusal_screen or (run_dcf_top or 0))),
        # Display-field coverage. A blank company name or sector is not a scoring bug, so
        # nothing else would ever report it — and it went unnoticed on the live site for
        # weeks. Measured on the rows that actually ship.
        "display_coverage": {
            "name": _cov(rows, lambda r: (r.get("name") or "").strip()
                         and (r.get("name") or "").strip().upper() != r["ticker"].upper()),
            "sector": _cov(rows, lambda r: (r.get("sector") or "").strip()),
            "market_cap": _cov(rows, lambda r: r.get("market_cap")),
        },
    }
    # Where each name's fundamentals actually came from, and how completely each field is
    # filled. Without this the free route's real coverage is invisible: a name served entirely
    # by the broker still produces a score, so "it ran" says nothing about whether the flow
    # factors (margins, FCF, growth) were present or silently absent.
    try:
        from . import broker_fundamentals as BF
        health["fundamentals"] = BF.coverage(metrics)
    except Exception:
        pass
    bstats = getattr(provider, "broker_stats", None)
    if bstats:
        health.setdefault("fundamentals", {})["broker"] = bstats

    note = getattr(provider, "universe_note", "")
    if note:
        health["universe_note"] = note
    budget = getattr(provider, "budget", None)
    if budget:
        health["api_budget"] = budget

    scan_date = _today()
    if save:
        store.save_snapshot(scan_date, rows, provider.name,
                            {"universe_size": total, "scope": scope, "filtered": audit, "health": health})
        # Dated, append-only archive of what we picked and when — a survivorship-free
        # record independent of the DB (which a Render restart can lose without a disk).
        try:
            from ..edge.archive import archive_scan
            archive_scan(rows, scan_date, provider.name)
        except Exception:
            pass
    return {"scan_date": scan_date, "rows": rows, "universe_size": total,
            "scored": len(rows), "provider": provider.name, "filtered": audit, "health": health}


def _enrich_with_dcf(rows, cfg, refusal_only: bool = False):
    """Attach the real DCF to the rows that get one — and RECORD a refusal as a refusal.

    This function used to write `r["fair_value"] = res.base_fair_value` and nothing else.
    On a refusal that value is None, and `estimate_fair_values` (below) reads a None fair
    value as "no DCF computed yet" and substitutes a peer estimate — so the publication
    guard's decision was silently erased and the name went onto the PUBLIC hot list with a
    number its own valuation page refuses to show. That is how KSPI, STLA and CHTR were
    served fair values while their pages said "cannot value this name".

    A REFUSAL IS NOT THE SAME AS "NOT VALUABLE", and the first version of this fix merged
    them. It refused on `base_fair_value is None and reason`, which is ALSO true for a name
    the model simply cannot value — no free cash flow, no revenue, an ADR bank whose P/B–ROE
    inputs are missing. Nothing has been refused about those names, and a peer multiple is
    exactly the right tool for them. Measured on the real production list: of 387 served names
    outside the DCF window, **0** are a genuine refusal, while the count reporting a "not
    DCF-valuable" reason came out **17 in one run and 77 in another** — the free upstream feed
    is not stable run to run, so under throttling MORE names get mislabelled as refused.
    Feeding NVS, SAP or TD through the old expression blanked a perfectly ordinary peer
    estimate ($185.41, $364.97, $79.73) and told the reader "no fair value is published".

    So the test is the VERDICT, not the presence of a reason string: ask
    `publication.decide` about the value the model actually had. That reads the one decision
    rather than restating its threshold, which is the rule that module exists to enforce.

    `refusal_only=True` asks solely "would the model refuse this name?" and never writes a
    fair value — that is the mode used for names outside the DCF window, where the point is
    to stop publishing a refused name, not to swap the published number for a different one.
    """
    errors: dict = {}
    try:
        from ..engine.pipeline import value_ticker
        from ..engine.publication import (record_refusal, record_unavailable,
                                          decide as decide_publication, ROW_WITHHELD)
    except Exception as e:
        # LA1: even the import failing is a fail-open. It used to return silently, so a
        # deployment missing the engine would serve unchecked peer estimates for every name
        # and report a clean scan.
        for r in rows:
            errors[r.get("ticker", "?")] = f"import: {type(e).__name__}"
        return errors
    for r in rows:
        # LA1 — RETRY ONCE BEFORE FAILING OPEN. The audit's KSPI case is the top-ranked name on
        # the public list, and it is the one name in the top three that needs an extra network
        # hop its neighbours do not (a KZT->USD rate) against a free, rate-limited feed. A
        # single retry is what a transient fetch failure is for; it does not weaken the
        # fail-open policy, it just stops one flaky call from silently publishing an unchecked
        # peer estimate on rank 1.
        last: Exception | None = None
        for attempt in range(DCF_ATTEMPTS):
            try:
                # The Monte Carlo is not an input to the publication decision (`blend` never
                # sees it), and it costs 0.03-0.08s against a 1.1-6.6s fetch, so the
                # refusal-only pass runs it at 1 trial rather than 1500.
                res = value_ticker(r["ticker"], cfg, mc_trials=(1 if refusal_only else 1500))
                blend = res.fair_value_blend
                # The number the model HELD before the guard blanked it — that is what was judged.
                had = blend.withheld_value if blend.withheld_value is not None else blend.value
                verdict = decide_publication(had, getattr(res.company, "price", None),
                                             cd=res.company,
                                             growth_led=getattr(blend, "growth_led", False))
                # WHAT THE PROBE ACTUALLY SAW — stamped on the row, because "the model
                # refused", "the model doesn't apply here" and "we could not look" are three
                # different states that all leave `fair_value` empty, and only the first two
                # are acceptable reasons to publish a peer estimate unchecked.
                #
                # This is LA1's second door, found by re-running the scan after fixing the
                # first: with 8 workers over 488 names against a free rate-limited feed, KSPI
                # came back with NO statements and NO exception. `had` was None,
                # `decide(None, price)` returns publish=False with an EMPTY reason by design,
                # and the row sailed through with `errors: 0` — a clean bill of health on a
                # name that refuses at 5.6x when asked on its own.
                # DID WE LOOK? Two independent signs that we did, and either is enough.
                #
                # A DIAGNOSIS is the stronger one: if the model can say WHY it cannot value a
                # name ("Not DCF-valuable: the company doesn't generate positive free cash
                # flow"), then it read the statements and formed that view. A throttled fetch
                # has nothing to say at all. Caught by `test_not_dcf_valuable_is_not_a_refusal`
                # — an existing pin whose stub company carries no `revenue` attribute, so
                # revenue alone would have mislabelled NVS as unfetchable and blanked exactly
                # the ordinary peer estimate that test exists to protect.
                has_reason = bool((getattr(blend, "reason", "") or "").strip())
                has_data = bool(getattr(res.company, "revenue", None)) or has_reason
                if had is None and not has_data:
                    r["dcf_probe"] = "no_data"
                    if attempt < DCF_ATTEMPTS - 1:
                        continue          # a throttled fetch is transient; ask again
                    # FAIL CLOSED (Don's decision, 2026-08-11). We could not look, so we
                    # publish nothing rather than letting `estimate_fair_values` substitute a
                    # peer estimate nothing has checked. Recorded as `unavailable`, NOT as a
                    # refusal: it is a statement about the fetch, it is temporary, and the next
                    # scan retries it automatically once the quota resets.
                    record_unavailable(r)
                    break
                elif had is None:
                    r["dcf_probe"] = "no_value"     # the model genuinely does not apply here
                if verdict.reason:
                    r["dcf_probe"] = "refused"
                    record_refusal(r, verdict.reason)  # a DECISION, not a gap
                elif had is not None:
                    r["dcf_probe"] = "valued"
                    if not refusal_only:
                        r["fair_value"] = res.base_fair_value
                        r["upside"] = res.upside
                        r.pop(ROW_WITHHELD, None)
                last = None
                break
            except Exception as e:
                # FAIL OPEN. A fetch that fails tells us nothing about whether the model would
                # refuse, and the upstream feed is a free, rate-limited one — a 401 was observed
                # during the 387-name measurement. Failing closed would blank hundreds of fair
                # values on a bad upstream day. The cost of failing open is stated plainly in
                # the handoff: a name we could not reach keeps its peer estimate unchecked.
                #
                # WHAT CHANGED (LA1): the cost is now COUNTED. It used to be `continue`, so a
                # swallowed raise on rank 1 left no trace anywhere — no counter, no log, no key
                # on the row — and `estimate_fair_values` read the untouched `fair_value: None`
                # as "no DCF yet" and substituted a peer estimate. The policy is unchanged; its
                # invisibility is not.
                last = e
        if last is not None:
            errors[r.get("ticker", "?")] = f"{type(last).__name__}: {last}"[:160]
    return errors


def _screen_refusals(rows, cfg, workers: int = 8) -> dict:
    """Ask the model, for every name the DCF window does NOT reach, only whether it REFUSES.

    Bug B: `_enrich_with_dcf` ran on `rows[:run_dcf_top]` and production runs `dcf_top=12`, so
    the other ~387 served names were never valued at all — no refusal could be recorded for
    them, and the public list published a peer estimate with no check against the valuation
    page's verdict. The 5x band on the served value cannot catch this class by construction:
    a refused 11x model is replaced by a 3.2x peer estimate that sits comfortably under it.

    This screens for the refusal ONLY and leaves every non-refused row exactly as it was. The
    alternative — raising `dcf_top` to cover the list — costs the same (the fetch is the whole
    price) but would also REPLACE the published fair value on ~387 names with a different
    model's number. That is a product decision, not a leak fix, and it is one constant away if
    it is wanted.

    Measured cost: 387 names in 3.0 min at 6 workers, median 2.51s per name.
    """
    if not rows:
        return {"screened": 0, "refused": 0, "errors": 0, "error_tickers": []}
    before = sum(1 for r in rows if r.get("fair_value_withheld"))
    errors: dict = {}
    if workers > 1 and len(rows) > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for got in pool.map(lambda r: _enrich_with_dcf([r], cfg, refusal_only=True), rows):
                errors.update(got or {})
    else:
        errors.update(_enrich_with_dcf(rows, cfg, refusal_only=True) or {})
    after = sum(1 for r in rows if r.get("fair_value_withheld"))
    # LA1 — the third counter. `screened` and `refused` alone cannot distinguish "asked 500
    # names and none were refused" from "asked 500 names and 500 fetches failed", and those are
    # opposite states: the first is a clean bill of health, the second is 500 unchecked peer
    # estimates on the public list.
    return {"screened": len(rows), "refused": after - before, "errors": len(errors),
            "error_tickers": sorted(errors)[:20]}


def _merge_screen(a: dict, b: dict, **extra) -> dict:
    """Combine two refusal-screen reports. The counts ADD; nothing is overwritten.

    Written as one function because the alternative — merging inline at each call site — is
    how a later pass silently replaces an earlier pass's `errors` with its own and a scan
    reports a clean bill of health it never earned.
    """
    out = {
        "screened": a.get("screened", 0) + b.get("screened", 0),
        "refused": a.get("refused", 0) + b.get("refused", 0),
        "errors": a.get("errors", 0) + b.get("errors", 0),
        "error_tickers": sorted(set(a.get("error_tickers") or [])
                                | set(b.get("error_tickers") or []))[:20],
    }
    for k, v in a.items():
        if k not in out:
            out[k] = v
    out.update(extra)
    return out


def publication_audit(rows, dcf_window: int = 0) -> dict:
    """LA1's detection: the two ways a served row can carry a number nothing vouched for.

    Runs on EVERY scan, over the rows the product can actually serve. Pre-registered in
    `PREREG_la1_la3_repair.md` §2 before it was written.

    D1 `asked_but_silent` — a row INSIDE the DCF window with no `fair_value`, no recorded
        refusal and no recorded engine error. It was asked and it answered nothing. **This is
        KSPI's exact state on the 2026-08-08 production scan** and it is detectable without
        knowing which of the two paths produced it (a swallowed raise, or a model that yielded
        no value at all — `publication.decide(None, price)` returns `publish=False` with an
        EMPTY reason by design, so that one is not an exception anywhere).

    D2 `band_breach` — a SERVED row whose `fair_value / price` exceeds `FV_BAND_HIGH` while
        `fair_value_withheld` is falsy. Nothing published may sit outside the band unwithheld,
        whatever produced it.

    **D2 WOULD NOT HAVE CAUGHT KSPI, AND THAT IS RECORDED HERE RATHER THAN IMPLIED AWAY.** Its
    served ratio is 274.13/90.30 = 3.04x, comfortably inside the 5.0 band — the substituted peer
    estimate is plausible-looking, which is the whole reason the refusal mattered. D1 is the rule
    that closes LA1; D2 closes a different real hole. A reader who takes a green D2 as evidence
    that LA1 cannot recur has been misled, so the two are always reported separately.

    LOUD BUT NOT FATAL. The scan is never aborted on a finding here: taking the daily scan down
    over a data-quality signal is a worse failure than the one being reported. `ci_scan` prints
    a LEAK banner naming every offending ticker, and `health.publication_audit` carries them.
    """
    from ..engine.publication import (FV_BAND_HIGH, ROW_WITHHELD, ROW_WITHHELD_KIND,
                                      KIND_UNAVAILABLE, KIND_REFUSED)

    silent, breach, unverified = [], [], []
    for i, r in enumerate(rows):
        # D3 `unverified` — the row was ASKED and we could not look: no statements came back,
        # so the model had nothing to judge and `decide(None, price)` returned an EMPTY reason.
        # Distinct from `no_value`, where the model genuinely does not apply (an ADR bank with
        # no free cash flow) and a peer multiple is the right tool. Found by re-running the
        # scan after the first fix: KSPI passed the refusal screen at rank 97 with `errors: 0`
        # while refusing at 5.6x when asked on its own, because a throttled fetch returns
        # partial data rather than raising, and only raises were being counted.
        if r.get("dcf_probe") == "no_data" and not r.get(ROW_WITHHELD):
            unverified.append(r.get("ticker"))
        px, fv = r.get("price"), r.get("fair_value")
        withheld = bool(r.get(ROW_WITHHELD))
        method = r.get("fair_value_method")
        # "No DCF value on this row", expressed so it holds at BOTH points in the pipeline.
        # `estimate_fair_values` runs at SERVE time (`web/app.py:500`), not in the scan, so
        # the same row looks different depending on where it is inspected: at scan time a
        # silent row is `fair_value None, method None` and a good one is `fair_value set,
        # method None`; by serve time the silent row has acquired a peer estimate and reads
        # `method "blended"`, while the good one reads `"dcf"`. Testing only for a null value
        # would miss the served payload entirely — which is the object the audit looked at.
        no_dcf = fv is None or (method is not None and method not in ("dcf", "withheld"))
        if i < dcf_window and no_dcf and not withheld and not r.get("dcf_error"):
            silent.append(r.get("ticker"))
        if fv is not None and px and px > 0 and not withheld and fv / px > FV_BAND_HIGH:
            breach.append({"ticker": r.get("ticker"), "ratio": round(fv / px, 4),
                           "method": r.get("fair_value_method")})
    return {
        "band": FV_BAND_HIGH,
        "dcf_window": dcf_window,
        "rows_checked": len(rows),
        "asked_but_silent": silent,
        "asked_but_silent_count": len(silent),
        "band_breach": breach,
        "band_breach_count": len(breach),
        "unverified": unverified,
        "unverified_count": len(unverified),
        # QUOTA DEGRADATION AS A NUMBER, NEVER SILENT AGAIN. This is the count of rows whose
        # fair value was withheld because the fetch failed, not because the model refused. On
        # 2026-08-08 the equivalent figure was invisible and the screen reported zero refusals
        # across 500 names it could not actually reach. A rising number here is the feed
        # degrading, and it now says so on every scan.
        "withheld_no_data": sum(1 for r in rows
                                if r.get(ROW_WITHHELD_KIND) == KIND_UNAVAILABLE),
        "withheld_refused": sum(1 for r in rows
                                if r.get(ROW_WITHHELD_KIND) == KIND_REFUSED),
        "probe": dict(sorted(collections.Counter(
            r.get("dcf_probe") for r in rows if r.get("dcf_probe")).items())),
        "clean": not silent and not breach and not unverified,
        "note": ("D2 (band_breach) cannot catch the LA1 class: a refused 11x model is replaced "
                 "by a peer estimate that sits inside the band. D1 (asked_but_silent) is the "
                 "rule that catches it."),
    }


def _today() -> str:
    return _dt.date.today().isoformat()
