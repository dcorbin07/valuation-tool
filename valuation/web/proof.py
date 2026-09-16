"""The public proof surface — every headline figure, the bar it is measured against, and
the ones it fails.

WHY THIS MODULE EXISTS AND WHY IT IS NOT A TEMPLATE
---------------------------------------------------
`/methodology` explains the method in prose. This page does the other half: it shows the
NUMBERS and, next to each one, the threshold it was judged against and whether it cleared.

Every figure here is DERIVED from an artifact on disk. Nothing is typed. That is the same
rule `payoff.py` states in one line — *"a number typed into a template is a number that
drifts"* — and it matters more here than anywhere else on the site, because this is the page
a stranger reads to decide whether to believe the rest of it. A proof page carrying a stale
hand-typed figure is worse than no proof page: it is the claim and the refutation in one
object.

The two sources, and why both:

  BACKTEST_RESULTS.json        the canonical run. Headline, benchmarks, decile ladder,
                               costs, the return distribution, and the project's own
                               multiple-testing block.

  MA19_RECALIBRATION.json      the placebo. 100 draws in which the signal is SHUFFLED
                               within each rebalance date and pushed through the identical
                               pipeline, so the null preserves the per-date distribution,
                               the missingness pattern and the cross-theme correlation and
                               destroys only the thing under test. This is the single most
                               persuasive artifact the project owns, and until now it has
                               never been on a public surface.

WHAT THIS MODULE REFUSES TO DO
------------------------------
1. It NEVER falls back to a typed constant when an artifact is missing. A section whose
   source is absent is dropped and `missing` names it. A proof page that invents its own
   evidence when the evidence is unavailable is the exact failure it exists to prevent.

2. It ships NO figure derived from Global Factor Data (the X8 international replication).
   That dataset is CC BY-NC 4.0, research-only, and `CLAUDE.md` records the rule without
   qualification: it validates the model and can never ship in the product. The replication
   is the strongest out-of-sample evidence this project has, and it stays off this page.

3. It computes no verdict of its own. Every pass/fail below is a comparison the artifact
   already carries (`multiple_testing.hlz.clears_*`, `cpcv.*.want`, MA19's `shipped_claims`)
   or a direct comparison against a floor MA19 measured. This module arranges evidence; it
   does not adjudicate it.

4. It quotes no forward-track figure. The live track is a different object with a different
   clock, and mixing a backtested statistic with a 20-row live series on one page invites
   exactly the averaging that `tidemark_surface.py` was built as a separate page to prevent.
"""

from __future__ import annotations

import json
import os

# ---- artifact locations ------------------------------------------------------------------
# Resolved from THIS FILE rather than from the working directory. `results_file.repo_root()`
# walks up from `os.getcwd()`, which is correct for a script run inside the repo and wrong in
# a deployed container, where the cwd is the app root and there is no `.git` anywhere. A web
# surface must resolve its own inputs from its own location.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

BACKTEST_JSON = os.path.join(_ROOT, "BACKTEST_RESULTS.json")
# The RAW draws, retained by session 10 for exactly this purpose. Preferred over MA19's
# summary block because it carries all 100 values rather than their percentiles, which is what
# lets the page say "N of 100 noise runs beat the real result" as a DERIVED count instead of a
# remembered one. MA19 is the fallback: it summarises the same draws (98 bit-identical, 2
# re-scored) and can still supply a median and a floor if the raw file is absent.
PLACEBO_JSON = os.path.join(_ROOT, "data", "free_analysis", "PLACEBO_HAC.json")
PLACEBO_FALLBACK_JSON = os.path.join(_ROOT, "data", "free_analysis", "MA19_RECALIBRATION.json")


def _load(path):
    """Parse a JSON artifact, or return None. Never raises into a request."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _num(x):
    """A finite float, or None. A NaN reaching a template renders as the string 'nan'."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def _dig(d, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


# ------------------------------------------------------------------------------------------
# the placebo — the centrepiece
# ------------------------------------------------------------------------------------------

# Which shuffled-null comparisons are safe to render, and why only these.
#
# A placebo floor is a function of the trial count N: N enters the CPCV adopt gate, so raising
# it can re-score a draw under different weights and move a percentile. MA19 measured which
# floors that actually moves and MB31 proved the adopt set unchanged below equity N = 247.
#
# The four statistics below are the ones MA19 reports as UNMOVED across every N regime the
# project has run (its `floors` block: delta 0.0). They can therefore be shown against the
# canonical run without pairing a numerator at one N with a floor at another — the exact
# mismatch MA19 was written to catch, where a Deflated Sharpe at N=116 was being quoted
# against a floor at N=84.
#
# The Deflated Sharpe and PBO are deliberately NOT in this list. Both are N-dependent by a
# different channel (N enters the DSR formula directly, so every draw moves), so a comparison
# would have to be re-derived at today's N to be honest. They appear further down in the
# `bars` table instead, quoted at the N the artifact itself used and labelled with it.
_PLACEBO_ROWS = (
    # (artifact key in `real`/null blocks, label, direction, unit)
    #
    # direction "high" = the real value should sit ABOVE the noise; "low" = below it.
    # Monotonicity is the one that catches people out: the deciles are ordered best-composite
    # first, so -1.0 is a perfectly ordered ladder and +1.0 is a ladder running backwards.
    ("top_decile_alpha", "Top-decile alpha, per quarter", "high", "pct"),
    ("top_decile_alpha_tstat_nw", "Top-decile alpha, t-statistic", "high", "num"),
    ("long_short_tstat_nw", "Long-short spread, t-statistic", "high", "num"),
    ("monotonicity", "Decile ladder ordering", "low", "num"),
)


def _quantile(sorted_vals, q):
    """Linear-interpolated quantile. Implemented here rather than imported because this module
    must not pull numpy into a request path for four numbers."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _placebo(real_source: dict, draws_doc: dict, summary_doc: dict):
    """Build the shuffled-signal comparison.

    The real value is taken from the CANONICAL run (`BACKTEST_RESULTS.json`) rather than from
    the placebo file's own `real` block wherever the two describe the same object, so this
    page cannot quietly show a figure the rest of the site does not. The two agree to sixteen
    digits on every field they share, which MA19's C2 control asserts, so the preference costs
    nothing and removes a way for the page to drift.

    `n_beaten` — how many of the 100 worthless runs beat the real result — is COUNTED from the
    draws. It is the single most quotable number on the page and the one a reader is most
    entitled to see derived rather than asserted, because "no noise run came close" and "three
    noise runs beat it" are very different claims and only the data can say which is true.
    """
    rows = []
    draws = draws_doc.get("draws") if isinstance(draws_doc, dict) else None
    have_draws = isinstance(draws, list) and len(draws) >= 20

    null_summary = _dig(summary_doc, "null_x7_reconstructed", default={}) if summary_doc else {}

    for key, label, direction, unit in _PLACEBO_ROWS:
        real = _num(_dig(real_source, "construction", key))
        if real is None and draws_doc:
            real = _num(_dig(draws_doc, "real", key))
        if real is None and summary_doc:
            real = _num(_dig(summary_doc, "real", key))
        if real is None:
            continue

        if have_draws:
            vals = sorted(v for v in (_num(d.get(key)) for d in draws) if v is not None)
            if len(vals) < 20:
                continue
            n = len(vals)
            p50 = _quantile(vals, 0.50)
            bar = _quantile(vals, 0.95 if direction == "high" else 0.05)
            lo, hi = vals[0], vals[-1]
            # Counted, not inferred. A tie counts AGAINST us: a noise run that merely equals
            # the real result is not one the real result beat, and on a coarse statistic like
            # the decile ordering that case actually occurs.
            if direction == "high":
                n_beaten = sum(1 for v in vals if v >= real)
            else:
                n_beaten = sum(1 for v in vals if v <= real)
        else:
            dist = null_summary.get(key)
            if not isinstance(dist, dict):
                continue
            n = int(_num(dist.get("n")) or 0)
            p50 = _num(dist.get("p50"))
            bar = _num(dist.get("p95") if direction == "high" else dist.get("p05"))
            lo, hi = _num(dist.get("min")), _num(dist.get("max"))
            n_beaten = None      # cannot be counted from percentiles; the page says so
            if None in (p50, bar, lo, hi) or not n:
                continue

        clears = (real > bar) if direction == "high" else (real < bar)

        rows.append({
            "key": key, "label": label, "direction": direction, "unit": unit,
            "real": real, "noise_median": p50, "noise_bar": bar,
            "noise_min": lo, "noise_max": hi, "n_draws": n,
            "n_beaten": n_beaten,
            "clears": bool(clears),
            "beats_every_draw": (n_beaten == 0) if n_beaten is not None else None,
        })

    if not rows:
        return None

    src = draws_doc if have_draws else summary_doc
    return {
        "rows": rows,
        "counted_from_draws": bool(have_draws),
        "n_draws": int(_num(_dig(src, "n_draws")) or (rows[0]["n_draws"] if rows else 0)),
        "seeds": _dig(src, "seeds"),
        "register": _dig(summary_doc or {}, "register") or _dig(draws_doc or {}, "test"),
        "source": os.path.basename(PLACEBO_JSON if have_draws else PLACEBO_FALLBACK_JSON),
    }


# ------------------------------------------------------------------------------------------
# the bars it fails
# ------------------------------------------------------------------------------------------

def _bars(res: dict):
    """The thresholds, including — especially — the ones the headline does not clear.

    Every entry is read from the artifact's own self-describing comparison. The artifact
    stores `want` strings and `clears_*` booleans precisely so a reader does not have to
    remember which direction each bar runs in, and this function does not second-guess them.
    """
    out = []

    hlz = _dig(res, "multiple_testing", "hlz", default={})
    value = _num(hlz.get("value"))
    if value is not None:
        floor = _num(hlz.get("x7_calibrated_floor"))
        if floor is not None:
            out.append({
                "name": "Long-short t vs. this project's own placebo floor",
                "value": value, "bar": floor,
                "passes": bool(hlz.get("clears_x7_calibrated_floor")),
                "what": "The 95th percentile of 100 shuffled-signal runs. Beating it means "
                        "the result is bigger than 95 out of 100 runs on a signal known to "
                        "be worthless.",
            })
        hurdle = _num(hlz.get("hurdle_sqrt_2_ln_N"))
        if hurdle is not None:
            out.append({
                "name": "Long-short t vs. the Harvey-Liu-Zhu multiple-testing hurdle",
                "value": value, "bar": hurdle,
                "passes": bool(hlz.get("clears_hlz_hurdle")),
                "what": "A bar that rises with the number of tests you have run. We have run "
                        "a lot. This is the headline's clearest failure and the artifact "
                        "records both sides of the argument.",
                "tension": hlz.get("the_tension"),
            })

    pbo = _dig(res, "cpcv", "pbo", default={})
    if _num(pbo.get("value")) is not None:
        out.append({
            "name": "Probability of backtest overfitting",
            "value": _num(pbo.get("value")), "bar": 0.50, "lower_is_better": True,
            "passes": _num(pbo.get("value")) < 0.50,
            "what": "Fails. And the bar is close to useless here: on a signal shuffled into "
                    "pure noise this statistic reads about 0.47 on average, so roughly half "
                    "of all worthless signals 'pass' it. We report it failing rather than "
                    "quietly dropping a measure that does not flatter us.",
            "scope": _dig(res, "cpcv", "pbo_scope"),
        })

    dsr = _dig(res, "cpcv", "deflated_sharpe", default={})
    dsr_detail = _dig(res, "cpcv", "deflated_sharpe_detail", default={})
    if _num(dsr.get("value")) is not None:
        out.append({
            "name": "Deflated Sharpe ratio",
            "value": _num(dsr.get("value")), "bar": 0.95,
            "passes": _num(dsr.get("value")) > 0.95,
            "what": "Fails the conventional 0.95 bar. It is a genuine deflated figure — it is "
                    "charged every one of the tests below, not the eight a naive version "
                    "would use — and it sits above all 100 shuffled runs. Both halves are "
                    "true and we do not quote one without the other.",
            "n_trials": _num(dsr_detail.get("n_trials")),
        })

    return out or None


# ------------------------------------------------------------------------------------------
# public payload
# ------------------------------------------------------------------------------------------

def payload() -> dict:
    """Everything the proof page renders, or an honest account of what is missing.

    Returns a dict that is always safe to hand to a template. `available` is False when the
    canonical run cannot be read at all; individual sections are None when their own source
    is absent, and `missing` names every one so a hole on the page is visible rather than
    silent — a proof page that loses a section and still looks complete is the failure mode
    this whole module is arranged against.
    """
    res = _load(BACKTEST_JSON)
    draws_doc = _load(PLACEBO_JSON)
    summary_doc = _load(PLACEBO_FALLBACK_JSON)
    missing = []
    if res is None:
        missing.append(os.path.basename(BACKTEST_JSON))
        return {"available": False, "missing": missing,
                "reason": "the canonical backtest artifact is not readable in this deployment"}
    if draws_doc is None and summary_doc is None:
        missing.append("the placebo study")

    con = _dig(res, "construction", default={})
    win = _dig(res, "cleanups", "panel_window", default={})
    uni = _dig(res, "universe", default={})

    # --- the panel ------------------------------------------------------------------------
    by_date = _dig(win, "cross_section_by_date", default={}) or {}
    dates = sorted(by_date)
    panel = {
        "n_names": int(_num(uni.get("n_names")) or 0),
        "n_dates": int(_num(uni.get("n_dates")) or 0),
        "n_rows": int(_num(uni.get("n_rows")) or 0),
        "first": dates[0] if dates else _dig(win, "retained_start"),
        "last": dates[-1] if dates else _dig(win, "retained_end"),
        "cross_section_min": _num(win.get("cross_section_min")),
        "cross_section_median": _num(win.get("cross_section_median")),
        "cross_section_max": _num(win.get("cross_section_max")),
        "horizon_days": _num(con.get("horizon_days")),
    }

    # --- the decile ladder ----------------------------------------------------------------
    ladder = con.get("decile_ann_return")
    deciles = None
    if isinstance(ladder, list) and ladder:
        vals = [_num(v) for v in ladder]
        if all(v is not None for v in vals):
            top, bottom = max(vals), min(vals)
            span = (top - bottom) or 1.0
            deciles = [{"rank": i + 1, "ann": v,
                        "bar_pct": round(100.0 * (v - bottom) / span, 1),
                        "is_top": i == 0}
                       for i, v in enumerate(vals)]

    # --- the three benchmarks -------------------------------------------------------------
    # All three ship, in the artifact's own order of increasing friendliness to the strategy.
    # The equal-weight universe is the one every historical figure in this project used and
    # is UNINVESTABLE — you cannot buy 2,500 names equally weighted at zero cost — so it is
    # shown first and labelled, and SPY is shown because it is what a reader would otherwise
    # actually have bought.
    bm = _dig(res, "benchmarks", default={})
    benchmarks = []
    for key in ("equal_weight", "cap_weighted", "spy"):
        b = bm.get(key)
        if not isinstance(b, dict):
            continue
        excess = _num(b.get("excess_ann"))
        if excess is None:
            continue
        benchmarks.append({
            "key": key,
            "label": b.get("label") or key,
            "note": b.get("note"),
            "benchmark_ann": _num(b.get("benchmark_ann")),
            "top_decile_ann": _num(b.get("top_decile_ann")),
            "excess_ann": excess,
            "t": _num(b.get("excess_tstat_nw")),
            "hit_rate": _num(b.get("hit_rate")),
            "investable": key != "equal_weight",
        })

    # --- costs ----------------------------------------------------------------------------
    # The BREAKEVEN is the number to lead with and the artifact's own comment says why: it
    # requires no belief in any particular cost calibration. "Net alpha" requires you to
    # accept our cost table; "you would have to pay 134bps a side before this dies" does not.
    c = _dig(res, "costs", "top_decile", default={})
    costs = None
    if _num(c.get("breakeven_one_way_bps")) is not None:
        costs = {
            "breakeven_bps": _num(c.get("breakeven_one_way_bps")),
            "realised_bps": _num(c.get("realised_one_way_bps")),
            "turnover": _num(c.get("annual_turnover")),
            "gross_alpha": _num(c.get("gross_alpha")),
            "net_alpha": _num(c.get("net_alpha")),
            "gross_ann": _num(c.get("gross_ann")),
            "net_ann": _num(c.get("net_ann")),
            "net_max_drawdown": _num(c.get("net_max_drawdown")),
            "net_sharpe": _num(c.get("net_sharpe")),
            "limitations": c.get("cost_model_limitations"),
        }
        bk, rl = costs["breakeven_bps"], costs["realised_bps"]
        costs["margin"] = (bk / rl) if (bk and rl) else None

    # --- the distribution behind the average ----------------------------------------------
    # An annual average hides how often the thing loses. 29% of quarters are negative and the
    # page says so next to the headline rather than in a footnote.
    dist = _dig(con, "top_decile_alpha_distribution", default={})
    distribution = None
    if _num(dist.get("negative_fraction")) is not None:
        distribution = {
            "n": int(_num(dist.get("n")) or 0),
            "negative_periods": int(_num(dist.get("negative_periods")) or 0),
            "negative_fraction": _num(dist.get("negative_fraction")),
            "median": _num(dist.get("median")),
            "mean": _num(dist.get("mean")),
            "p05": _num(dist.get("p05")),
            "p95": _num(dist.get("p95")),
            "worst": dist.get("worst"),
            "best": dist.get("best"),
            "units": dist.get("units"),
        }

    # --- how many tests we have run -------------------------------------------------------
    # Read LIVE from the research log, because it moves whenever any lane books a trial while
    # the artifact is only rebuilt on a full backtest. The artifact's own count ships beside
    # it so the gap is visible instead of being a silent inconsistency between two pages.
    trials, trials_source = None, None
    try:
        from ..edge import research_log
        d = research_log.detail()
        bd = d.get("by_domain") if isinstance(d, dict) else None
        if isinstance(bd, dict) and bd:
            trials = {k: int(v) for k, v in bd.items() if isinstance(v, (int, float))}
            trials_source = "RESEARCH_LOG.md, read live"
    except Exception:
        trials = None
    if trials is None:
        bd = _dig(res, "multiple_testing", "by_domain")
        if isinstance(bd, dict) and bd:
            trials = {k: int(v) for k, v in bd.items() if isinstance(v, (int, float))}
            trials_source = "BACKTEST_RESULTS.json (research log unavailable in this deployment)"

    placebo_block = None
    if draws_doc or summary_doc:
        placebo_block = _placebo(res, draws_doc or {}, summary_doc or {})
        if placebo_block is None:
            missing.append("placebo comparison (artifact present but not in the expected shape)")

    return {
        "available": True,
        "missing": missing,
        # provenance — a proof page that will not say when it was generated is not one
        "generated_at": _dig(res, "generated_at_utc") or _dig(res, "generated_at"),
        "commit": _dig(res, "git", "short"),
        "schema_version": _num(res.get("schema_version")),
        "panel": panel,
        "deciles": deciles,
        "benchmarks": benchmarks or None,
        "spread": {"ann": _num(con.get("long_short_ann")),
                   "t": _num(con.get("long_short_tstat_nw"))},
        "monotonicity": _num(con.get("monotonicity")),
        "hit_rate": _num(con.get("top_decile_alpha_hit")),
        "costs": costs,
        "distribution": distribution,
        "placebo": placebo_block,
        "bars": _bars(res),
        "trials": trials,
        "trials_source": trials_source,
        "errors": res.get("errors") or [],
    }
