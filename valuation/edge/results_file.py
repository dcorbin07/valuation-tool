"""
Canonical machine-readable backtest results.

Writes two files at the REPO ROOT on every backtest run, both git-tracked:

    BACKTEST_RESULTS.json   canonical, for the Cowork agent to parse exactly
    BACKTEST_RESULTS.md     the same numbers as a short table for a human

Tracked-and-committed is deliberate: that is what carries the current numbers out of a
worktree and onto main, where another agent can read them. It is license-safe because
everything here is a DERIVED METRIC — IC values, t-stats, annualized returns, weights.
No raw Sharadar rows, no per-name fundamentals, no prices. Nothing that could redistribute
licensed data.

The contract with the reader: **numbers and metadata only, no interpretation.** Verdict
STRINGS produced by the validators (e.g. cpcv.verdict) are carried through verbatim because
they are part of the machine output, but nothing here adds a reading of what the numbers
mean — that is the consumer's job, and HANDOFF_STATUS.md is where this repo's own narrative
lives. Thresholds ship next to the metrics (`pbo.want`, `deflated_sharpe.want`) so the file
is self-describing without a human to explain it.

Overwritten in full on every run: it is a snapshot of the latest run, not a log.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess

from . import payload_schema as _schema      # AUDIT M6 — field-level schema guard

JSON_NAME = "BACKTEST_RESULTS.json"
MD_NAME = "BACKTEST_RESULTS.md"
# 2 adds the `signal_coverage` block: {signal: coverage} for every wired number and theme,
# plus `below_floor` — the signals that are wired but effectively empty. Purely additive, so
# a v1 reader still works; the bump is the signal that new fields exist.
# 3 adds `sanity_check` (correctness: range / subgroup-pegging / market-cap divergence),
# `per_theme`, `holdout_validation` and `costs`. All additive; a v2 reader still works.
# 4 adds `ev_freshness`: what fraction of rows carry an enterprise value priced at the
# REBALANCE date rather than the filing date, and how far re-pricing moved it. Additive.
# 5 adds, all additive: `*_inference` blocks (audit M2 — clustered-by-default cross-date
# inference, with n_eff beside n and the naive figure labelled a diagnostic); B17's hold-book
# disclosure on `portfolio` (`label_warning`, `held_*`, `exit_rank`, `charges_*`) which was
# being computed and silently dropped; and `cpcv.adopt_detail` / `cpcv.challenger_weights`,
# banked by session 12 and likewise never serialised. A v4 reader still works.
SCHEMA_VERSION = 5


def repo_root(start: str | None = None) -> str:
    """Nearest ancestor containing .git — so a run from a worktree writes to that worktree."""
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(start or os.getcwd())
        d = parent


def _git(root: str, *args) -> str | None:
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


def _num(x):
    """Plain float, or None. Guards against numpy scalars and NaN reaching json.dump."""
    if x is None or isinstance(x, bool):
        return None if x is None else x
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def build_payload(res: dict, universe_label: str | None = None,
                  cleanups: dict | None = None, per_signal: dict | None = None,
                  root: str | None = None) -> dict:
    """Map a `run_backtests` result dict into the canonical, verdict-free shape."""
    root = root or repo_root()
    horizons = res.get("horizons") or {}
    primary = str(res.get("primary_horizon") or "")
    # The universe block must describe the horizon CPCV / construction actually ran on, not
    # `primary_horizon`. Those differ: primary was 756d (9 dates) on the full run while the
    # validators used 63d (2,710 names x 110 dates), and reporting 9 dates next to a PBO
    # computed over 110 would misdescribe the whole run.
    _cn_h = str((res.get("construction") or {}).get("horizon") or "")
    validated = _cn_h if _cn_h in horizons else primary
    ph = horizons.get(validated) or {}

    n_names = ph.get("names")
    label = universe_label
    if label is None:
        label = "full" if (n_names or 0) >= 2000 else "subset"

    cp = res.get("cpcv") or {}
    cov = res.get("signal_coverage") or {}
    pt = res.get("per_theme") or {}
    hv = res.get("holdout_validation") or {}
    cst = res.get("costs") or {}
    san = res.get("sanity_check") or {}
    evf = res.get("ev_freshness") or {}
    atx = res.get("after_tax") or {}
    ntb = res.get("no_trade_band") or {}
    bkc = res.get("book_configs") or {}
    if per_signal is None:
        per_signal = res.get("per_signal") or None
    wf = (res.get("walk_forward") or {}).get("weights") or {}
    cn = res.get("construction") or {}
    idp = res.get("institutional_dependence") or {}
    hue = res.get("hold_until_exit") or {}

    def candidates(block):
        out = {}
        for name, c in (block.get("candidates") or {}).items():
            c = c or {}
            out[name] = {"median_oos_ic": _num(c.get("median_oos_ic")),
                         "folds_positive": _num(c.get("folds_positive")),
                         "n": c.get("n"), "selected": c.get("selected")}
        return out

    # A run where a validation block threw still writes this file, with every metric null —
    # which reads as "the backtest ran and found nothing" rather than "the backtest broke".
    # That is the exact silently-wrong pattern this project keeps hitting, so surface it.
    _errors = []
    for _k in ("hold_until_exit", "construction", "walk_forward", "cpcv", "regime",
               "institutional_dependence"):
        _st = (res.get(_k) or {}).get("status")
        if isinstance(_st, str) and _st.lower().startswith("error"):
            _errors.append({"block": _k, "status": _st})

    payload = {
        "schema_version": SCHEMA_VERSION,
        # Non-empty means the run is DEGRADED: some validation block raised and its metrics
        # below are null for that reason, not because the edge is absent.
        "errors": _errors,
        "generated_at": _dt.datetime.now().replace(microsecond=0).isoformat(),
        "generated_at_utc": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "git": {"commit": _git(root, "rev-parse", "HEAD"),
                "short": _git(root, "rev-parse", "--short", "HEAD"),
                "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": bool(_git(root, "status", "--porcelain"))},
        "provider": res.get("provider"),
        "survivorship_free": res.get("survivorship_free"),
        "universe": {"label": label, "n_names": n_names, "n_dates": ph.get("dates"),
                     "n_rows": ph.get("rows"),
                     "validated_horizon_days": validated, "primary_horizon_days": primary,
                     "horizons_days": sorted(horizons.keys(), key=lambda k: int(k))},
        # Which data-quality corrections were active for THIS run. Numbers from runs with
        # different cleanups are not comparable, so they travel with the metrics.
        "cleanups": cleanups or {},
        "signals_wired": res.get("factors_used") or ph.get("factors") or [],

        "per_horizon": {
            h: {"n_names": (horizons[h] or {}).get("names"),
                "n_dates": (horizons[h] or {}).get("dates"),
                "in_sample_ic": _num((horizons[h] or {}).get("in_sample_ic")),
                "out_sample_ic": _num((horizons[h] or {}).get("out_sample_ic")),
                "accepted": (horizons[h] or {}).get("accepted"),
                "default_weights": (horizons[h] or {}).get("default_weights"),
                "optimized_weights": (horizons[h] or {}).get("optimized_weights")}
            for h in horizons
        },
        # Realized track of the held portfolio vs the benchmark and vs equal-weight.
        "portfolio": {"cagr": _num(hue.get("cagr")),
                      "benchmark_cagr": _num(hue.get("bench_cagr")),
                      "equal_weight_cagr": _num(hue.get("ew_cagr")),
                      "alpha_vs_equal_weight": _num(hue.get("ew_alpha")),
                      "alpha_vs_benchmark": (None if hue.get("cagr") is None or hue.get("bench_cagr") is None
                                             else _num(hue["cagr"] - hue["bench_cagr"])),
                      "total_return": _num(hue.get("total_return")),
                      "benchmark_total_return": _num(hue.get("bench_return")),
                      "years": _num(hue.get("years")), "n_periods": hue.get("n_periods"),
                      "hit_rate": _num(hue.get("hit_rate")),
                      "avg_hold_years": _num(hue.get("avg_hold_years")),
                      # AUDIT M6 — B17's ENTIRE DISCLOSURE was being computed and dropped
                      # here. `_backtest_hold` has been returning all of these; none of them
                      # reached the canonical file, so `cagr` above shipped as "the top-25
                      # hold book" with no warning that the realised book is ~`exit_rank`
                      # names and pays neither costs nor taxes, unlike every other book in
                      # this file. That warning is the reason B17 exists.
                      "label_warning": hue.get("label_warning"),
                      "target_n": hue.get("target_n"), "exit_rank": hue.get("exit_rank"),
                      "held_min": hue.get("held_min"), "held_median": hue.get("held_median"),
                      "held_max": hue.get("held_max"),
                      "charges_costs": hue.get("charges_costs"),
                      "charges_taxes": hue.get("charges_taxes")},

        "cpcv": {"n_paths": cp.get("n_paths"),
                 "pbo": {"value": _num(cp.get("pbo")), "want": "<0.50",
                         "meaning": "probability_of_backtest_overfitting"},
                 # AUDIT B9 — the label is not the claim. `deflated_sharpe_detail` carries
                 # sr0, the trial count and the cross-trial variance, and `metric` says
                 # plainly when the statistic degenerated to an UNDEFLATED PSR (sr0 ~ 0,
                 # which is what eight near-identical weight schemes produce). `pbo_scope`
                 # says which selection step the PBO covers.
                 "deflated_sharpe_detail": cp.get("deflated_sharpe_detail"),
                 "pbo_scope": cp.get("pbo_scope"),
                 "deflated_sharpe": {"value": _num(cp.get("deflated_sharpe")), "want": ">0.95",
                                     "meaning": "probability_edge_is_real_after_trials_correction"},
                 "recommend": cp.get("recommend"), "adopt": cp.get("adopt"),
                 "verdict": cp.get("verdict"),
                 "recommended_weights": cp.get("recommended_weights_cols"),
                 # AUDIT M6 — session 12 banked these two SPECIFICALLY so that "what would
                 # this run have scored one haircut lower" is arithmetic rather than a
                 # re-run, after the X7 8%-vs-7% discrepancy proved undiagnosable without
                 # them. Neither reached the canonical file, which is the only place a later
                 # session would look. Banking a number into a dict nobody serialises is not
                 # banking it.
                 "adopt_detail": cp.get("adopt_detail"),
                 "challenger_weights": cp.get("challenger_weights_cols"),
                 "candidates": candidates(cp)},

        "walk_forward": {"n_folds": (res.get("walk_forward") or {}).get("n_folds"),
                         "recommend": wf.get("recommend"), "adopt": wf.get("adopt"),
                         "verdict": wf.get("verdict"),
                         "recommended_weights": wf.get("recommended_weights_cols"),
                         "candidates": candidates(wf)},

        "construction": {"weighting": res.get("construction_weighting"),
                         "n_periods": cn.get("n_periods"), "n_quantiles": cn.get("n_quantiles"),
                         "horizon_days": cn.get("horizon"),
                         "decile_ann_return": [_num(x) for x in (cn.get("decile_ann_return") or [])],
                         "equal_weight_ann": _num(cn.get("equal_weight_ann")),
                         "long_short_ann": _num(cn.get("long_short_ann")),
                         "long_short_tstat": _num(cn.get("long_short_tstat")),
                         # AUDIT R9 — HAC inference and the serial-correlation diagnostic that
                         # says whether the naive t above is entitled to be believed. If
                         # `long_short_ljung_box.p_value` < 0.05 the series is autocorrelated
                         # and `long_short_tstat_nw` is the number to quote.
                         "long_short_tstat_nw": _num(cn.get("long_short_tstat_nw")),
                         "long_short_ljung_box": cn.get("long_short_ljung_box"),
                         # AUDIT M2 — clustered-by-default inference. `t` is the HAC figure
                         # (identical to `long_short_tstat_nw`), `t_naive` the i.i.d. one,
                         # and `n_eff` travels with `n` for the first time. The flat keys
                         # above keep their meanings: the gates were calibrated on them.
                         "long_short_inference": cn.get("long_short_inference"),
                         "long_short_hit": _num(cn.get("long_short_hit")),
                         # -1.0 = returns fall perfectly from the best decile to the worst
                         # (ideal); +1.0 = the composite is exactly backwards. NEGATIVE IS
                         # GOOD — this repo's older notes read the sign the wrong way round.
                         "monotonicity": _num(cn.get("monotonicity")),
                         "monotonicity_want": "negative (-1.0 = perfectly ordered)",
                         "top_decile_alpha": _num(cn.get("top_decile_alpha")),
                         # AUDIT R9 — the number on the front of the product had no
                         # significance statistic of any kind until now.
                         "top_decile_alpha_tstat": _num(cn.get("top_decile_alpha_tstat")),
                         "top_decile_alpha_tstat_nw": _num(cn.get("top_decile_alpha_tstat_nw")),
                         "top_decile_alpha_ljung_box": cn.get("top_decile_alpha_ljung_box"),
                         "top_decile_alpha_inference": cn.get("top_decile_alpha_inference"),
                         "top_decile_alpha_hit": _num(cn.get("top_decile_alpha_hit")),
                         "signal_weighted_top_decile_alpha": _num(cn.get("sw_top_decile_alpha"))},

        # AUDIT R10 — the top decile against benchmarks a person could actually hold, beside
        # the uninvestable equal-weight universe every historical figure used.
        "benchmarks": res.get("benchmarks"),

        "institutional_dependence": {
            "institutional_weight": _num(idp.get("institutional_weight")),
            "with": {k: _num(v) for k, v in (idp.get("with") or {}).items()},
            "without": {k: _num(v) for k, v in (idp.get("without") or {}).items()}},

        "regime": {t: {"median_ic": _num((v or {}).get("median_ic")),
                       "long_short_ann": _num((v or {}).get("long_short_ann")),
                       "n_periods": (v or {}).get("n_periods")}
                   for t, v in ((res.get("regime") or {}).get("tiers") or {}).items()},

        # {signal: {median_ic, ic_tstat, coverage}} when a caller measured them; an empty
        # dict with available=false means "not computed this run", not "no signal".
        "per_signal": {"available": bool(per_signal), "signals": per_signal or {}},

        # Same measurement one level up: the IC of each composite THEME. An input can be
        # worthless while the theme it feeds is worth carrying, or the reverse, so the
        # keep/drop decisions need both.
        "per_theme": {"available": bool(pt), "themes": pt or {}},

        # Held-out time split: does zeroing a theme still help on data that did NOT inform
        # the decision? CPCV/DSR correct for the weight search, NOT for a human dropping a
        # theme after seeing its IC — so this is the only block that speaks to that.
        # verdicts: confirmed = helped in both split directions; not_replicated = one only.
        "holdout_validation": hv or {"status": "not computed"},

        # Tradeability. EVERY other performance number in this file is gross of costs, and
        # the book tilted smaller-cap when low_risk was zeroed — which is where costs bite.
        # `breakeven_one_way_bps` is the figure to quote: the cost level at which net alpha
        # vs equal-weight hits zero, so it can be compared against real execution costs
        # without having to believe any particular cost calibration.
        "costs": cst or {"status": "not computed"},

        # After-TAX, for a taxable account. The book turns over ~250%/yr, so most
        # gains are short-term and taxed as ordinary income — a drag several times
        # larger than trading costs. A tax-advantaged account pays none of it and
        # earns the `costs` net figure instead.
        "after_tax": atx or {"status": "not computed"},

        # Turnover/alpha tradeoff of a no-trade band (hysteresis). `none` is the
        # shipped behaviour: sell the moment a name leaves the book.
        "no_trade_band": ntb or {"status": "not computed"},

        # The two shipped book constructions (settings.BOOK_CONFIGS), scored on this
        # run. `roth` optimizes net-of-cost Sharpe with free rotation; `taxable`
        # optimizes AFTER-TAX Sharpe with a no-trade band.
        "book_configs": bkc or {"status": "not computed"},

        # CORRECTNESS, as distinct from coverage. signal_coverage says a factor is present;
        # this says its VALUES are believable. `flags` is the load-bearing part: an empty list
        # means the range / subgroup-pegging / market-cap-divergence checks all passed.
        "sanity_check": san or {"available": False, "flags": []},

        # Coverage says a factor is PRESENT and sanity says it is BELIEVABLE; this says the
        # EV ratios are CURRENT. `ev` used to be read straight off the filing, so `ebit_ev` /
        # `ev_sales` / `ev_ebitda` priced cheapness against a ~111-day-old quote while
        # `earnings_yield` / `fcf_yield` / `book_to_price` used the rebalance-date one. A
        # rebuild that silently falls back to the filing value raises nothing and leaves both
        # of the other blocks perfectly happy, so it needs its own number. `fresh` is the
        # load-bearing part; `drift` is the effect size (a rebuild that never moves anything
        # is its own kind of broken).
        "ev_freshness": {
            "available": bool(evf),
            "fresh": _num(evf.get("fresh")),
            "stale": _num(evf.get("stale")),
            "floor": _num(evf.get("floor")),
            "ok": evf.get("ok"),
            "by_source": {k: int(v) for k, v in (evf.get("by_source") or {}).items()},
            "drift": {k: _num(v) for k, v in (evf.get("drift") or {}).items()},
            "warnings": evf.get("warnings") or []},

        # {signal: coverage} for every wired number and theme — the fraction of panel rows
        # where it actually reached the composite. `below_floor` is the load-bearing part:
        # a wired factor at ~0% is a plumbing bug that no other metric in this file exposes,
        # because an empty column simply contributes nothing and raises no error.
        "signal_coverage": {
            "available": bool(cov),
            "floor": _num(cov.get("floor")),
            "numbers": {k: _num(v) for k, v in (cov.get("numbers") or {}).items()},
            "themes": {k: _num(v) for k, v in (cov.get("themes") or {}).items()},
            "below_floor": [{"kind": r.get("kind"), "name": r.get("name"),
                             "theme": r.get("theme"), "coverage": _num(r.get("coverage"))}
                            for r in (cov.get("below_floor") or [])],
            "exempt_themes": cov.get("exempt_themes") or []},
    }

    # AUDIT M6 — FIELD-level schema check. The block-level one (B22's
    # `missing_result_blocks`) catches a whole block going missing; this catches the case
    # that actually bit twice — a field the producer computed that this whitelist never
    # carried. It enumerates from the SOURCE, so a newly computed metric is caught the first
    # time it is added rather than the first time somebody happens to read two files side by
    # side. Findings land in `errors`, which already renders as a DEGRADED banner, and
    # `write()` then fails the run.
    for _f in _schema.check_payload(res, payload):
        payload["errors"].append(
            {"block": _f["block"],
             "status": (f"error: computed field `{_f['field']}` was dropped from the payload "
                        f"(audit M6). Carry it in build_payload, or declare it in "
                        f"payload_schema.BLOCK_SPEC['{_f['block']}']['allow'] with a reason."),
             "dropped_field": _f["field"]})
    return payload


def _pct(x, d=1):
    """Signed percent — for returns and alphas, where direction matters."""
    return "n/a" if x is None else f"{x*100:+.{d}f}%"


def _rate(x, d=0):
    """Unsigned percent — for probabilities, hit rates and coverage, where a leading
    '+' would read as an improvement rather than a level (PBO '+53%' is nonsense)."""
    return "n/a" if x is None else f"{x*100:.{d}f}%"


def _f2(x, d=2):
    return "n/a" if x is None else f"{x:.{d}f}"


def _prob(x):
    """A model-derived probability, never rounded to a bare 0% or 100%.

    Deflated Sharpe came back as 0.9999991 and rendered as a flat '100%', which reads as
    certainty about an 18-year backtest. It is a saturated normal CDF, not a proof, and this
    file is read by another agent that won't see the raw value.
    """
    if x is None:
        return "n/a"
    if x >= 0.9995:
        return ">99.9%"
    if 0 < x <= 0.0005:
        return "<0.1%"
    return f"{x*100:.0f}%"


def render_md(p: dict) -> str:
    u, cp, cn = p["universe"], p["cpcv"], p["construction"]
    L = []
    A = L.append
    A("# Backtest results — latest run\n")
    A("Generated by the backtest; **overwritten every run**. Numbers only — the narrative and")
    A("interpretation live in `HANDOFF_STATUS.md`. Canonical machine-readable copy:")
    A(f"`{JSON_NAME}`.\n")
    g = p["git"]
    A(f"- **Run:** {p['generated_at']}  ·  commit `{g.get('short') or '?'}`"
      f"{' (dirty tree)' if g.get('dirty') else ''} on `{g.get('branch') or '?'}`")
    A(f"- **Universe:** {u['label']} — {u['n_names']} names × {u['n_dates']} dates "
      f"({u['n_rows']} rows), primary horizon {u['primary_horizon_days']}d")
    A(f"- **Provider:** {p.get('provider')}  ·  survivorship-free: {p.get('survivorship_free')}")
    if p.get("errors"):
        A("")
        A(f"> ⚠️ **DEGRADED RUN — {len(p['errors'])} validation block(s) FAILED.** The null "
          f"metrics below mean the code raised, NOT that the edge is absent. Do not read this "
          f"as a result:")
        for e in p["errors"]:
            A(f">   - `{e['block']}`: {e['status']}")
        A("")
    if p.get("cleanups"):
        A(f"- **Cleanups active:** " + ", ".join(f"{k}={v}" for k, v in p["cleanups"].items()))
    if p.get("signals_wired"):
        A(f"- **Signals wired ({len(p['signals_wired'])}):** " + ", ".join(p["signals_wired"]))
    sc = p.get("signal_coverage") or {}
    if sc.get("available"):
        bf = sc.get("below_floor") or []
        if bf:
            A(f"- **EMPTY SIGNALS ({len(bf)}) — wired but below "
              f"{_rate(sc.get('floor'))} coverage, so contributing nothing:** "
              + ", ".join(f"`{r['name']}` ({_rate(r['coverage'], 1)})" for r in bf))
        else:
            A(f"- **Coverage guard:** all wired signals above {_rate(sc.get('floor'))} coverage")
    ev = p.get("ev_freshness") or {}
    if ev.get("available"):
        _dr = ev.get("drift") or {}
        _md = ("" if _dr.get("median") is None else
               f", median re-pricing {_rate(_dr['median'], 1)} "
               f"(>25% on {_rate(_dr.get('frac_over_25pct'), 1)} of rows)")
        if ev.get("ok"):
            A(f"- **EV freshness:** {_rate(ev.get('fresh'), 1)} of rows priced at the "
              f"REBALANCE date{_md}")
        else:
            A(f"- **⚠️ EV IS STALE — only {_rate(ev.get('fresh'), 1)} of rows priced at the "
              f"rebalance date:** " + "; ".join(ev.get("warnings") or []))
    A("")
    A("## Validation\n")
    A("| metric | value | want |")
    A("|---|---|---|")
    A(f"| PBO (prob. of backtest overfitting) | {_prob(cp['pbo']['value'])} | {cp['pbo']['want']} |")
    A(f"| Deflated Sharpe | {_prob(cp['deflated_sharpe']['value'])} | {cp['deflated_sharpe']['want']} |")
    A(f"| CPCV paths | {cp.get('n_paths')} | — |")
    _dsd = cp.get("deflated_sharpe_detail") or {}
    if _dsd.get("n_trials"):
        A(f"| Deflated Sharpe trial count N | {_dsd.get('n_trials')} "
          f"({_dsd.get('n_trials_source', 'n/a')}) | the real trial count, audit M1 |")
    _lb = (cn.get("long_short_ljung_box") or {})
    if _lb.get("p_value") is not None:
        A(f"| Long-short HAC t (Newey-West) | {_f2(cn.get('long_short_tstat_nw'))} | "
          f"quote this one if Ljung-Box rejects |")
        A(f"| Ljung-Box p on the spread | {_f2(_lb.get('p_value'))} | "
          f"< 0.05 = autocorrelated, naive t overstates |")
    A(f"| CPCV recommend / adopt | {cp.get('recommend')} / {cp.get('adopt')} | — |")
    A(f"| Walk-forward recommend / adopt | {p['walk_forward'].get('recommend')} / "
      f"{p['walk_forward'].get('adopt')} | — |")
    A("")
    A("## Portfolio & construction\n")
    pf = p["portfolio"]
    A("| metric | value |")
    A("|---|---|")
    A(f"| CAGR | {_pct(pf['cagr'])} |")
    A(f"| Benchmark CAGR | {_pct(pf['benchmark_cagr'])} |")
    A(f"| Equal-weight CAGR | {_pct(pf['equal_weight_cagr'])} |")
    A(f"| Alpha vs equal-weight | {_pct(pf['alpha_vs_equal_weight'])} |")
    A(f"| Top-decile alpha | {_pct(cn['top_decile_alpha'])} (t {_f2(cn.get('top_decile_alpha_tstat'))}, "
      f"HAC t {_f2(cn.get('top_decile_alpha_tstat_nw'))}) |")
    A(f"| Long-short (D1−D10) | {_pct(cn['long_short_ann'])} (t {_f2(cn['long_short_tstat'])}, "
      f"hit {_rate(cn['long_short_hit'])}) |")
    A(f"| Monotonicity (−1 = perfectly ordered D1→D10, +1 = backwards) "
      f"| {_f2(cn['monotonicity'])} |")
    dec = cn.get("decile_ann_return") or []
    if dec:
        A("")
        A("Deciles D1 (best composite) → D10: " + " · ".join(_pct(x, 0) for x in dec))
    idp = p["institutional_dependence"]
    if idp.get("with"):
        A("")
        A("## Institutional (13F) dependence\n")
        A(f"weight {_rate(idp.get('institutional_weight'))}\n")
        A("| | top-decile alpha | long-short t |")
        A("|---|---|---|")
        A(f"| with | {_pct(idp['with'].get('top_decile_alpha'))} | {_f2(idp['with'].get('long_short_tstat'))} |")
        A(f"| without | {_pct(idp['without'].get('top_decile_alpha'))} | {_f2(idp['without'].get('long_short_tstat'))} |")
    if p.get("regime"):
        A("")
        A("## By market-cap tier\n")
        A("| tier | median IC | long-short/yr |")
        A("|---|---|---|")
        for t, v in p["regime"].items():
            A(f"| {t} | {_f2(v.get('median_ic'), 4)} | {_pct(v.get('long_short_ann'))} |")
    cands = cp.get("candidates") or {}
    if cands:
        A("")
        A("## CPCV candidates (median out-of-sample IC)\n")
        A("| weighting | median OOS IC | folds positive |")
        A("|---|---|---|")
        for name, c in sorted(cands.items(), key=lambda kv: -(kv[1].get("median_oos_ic") or -9)):
            A(f"| {name} | {_f2(c.get('median_oos_ic'), 4)} | {_rate(c.get('folds_positive'))} |")
    ps = p.get("per_signal") or {}
    if ps.get("available"):
        A("")
        A("## Per-signal\n")
        A("| signal | median IC | IC t | coverage |")
        A("|---|---|---|---|")
        for name, v in sorted((ps.get("signals") or {}).items(),
                              key=lambda kv: -(kv[1].get("ic_tstat") or -99)):
            A(f"| {name} | {_f2(v.get('median_ic'), 4)} | {_f2(v.get('ic_tstat'))} | "
              f"{_rate(v.get('coverage'))} |")
    th = (p.get("per_theme") or {}).get("themes") or {}
    if th or (sc.get("themes") or {}):
        A("")
        A("## Per-theme\n")
        A("A theme with a NEGATIVE IC is actively costing the composite; one near zero is")
        A("dead weight diluting the themes that work.\n")
        A("| theme | median IC | IC t | coverage |")
        A("|---|---|---|---|")
        _cov = sc.get("themes") or {}
        keys = sorted(set(th) | set(_cov), key=lambda k: -((th.get(k) or {}).get("ic_tstat") or -99))
        for t in keys:
            v = th.get(t) or {}
            A(f"| {t} | {_f2(v.get('median_ic'), 4)} | {_f2(v.get('ic_tstat'))} | "
              f"{_rate(_cov.get(t, v.get('coverage')), 1)} |")
    sn = p.get("sanity_check") or {}
    if sn.get("available"):
        A("")
        A("## Correctness (sanity) — are the factor VALUES believable?\n")
        A("Distinct from coverage: coverage says a factor is *present*, this says it is")
        A("*sane*. The currency bug filled every column and was simply wrong, so coverage was")
        A("blind to it.\n")
        fl = sn.get("flags") or []
        if not fl:
            A("**No flags** — range, subgroup-pegging and market-cap-divergence checks all passed.")
        else:
            A(f"**{len(fl)} FLAG(S):**\n")
            A("| check | factor | detail |")
            A("|---|---|---|")
            for f in fl[:20]:
                A(f"| {f.get('check')} | `{f.get('factor','-')}` | {f.get('detail','')} |")
        _fp = ((sn.get("checks") or {}).get("subgroup") or {}).get("foreign_median_percentile") or {}
        if _fp:
            A("")
            A("Foreign reporters' median percentile per factor "
              "(0.50 = no tilt; near 0 or 1 = pegged):\n")
            A("| factor | median pctile |")
            A("|---|---|")
            for k, v in list(_fp.items())[:8]:
                A(f"| {k} | {v:.2f} |")
    cs = p.get("costs") or {}
    if cs.get("top_decile"):
        A("")
        A("## Tradeability — net of transaction costs\n")
        A("Every other performance figure in this file is **gross**. `breakeven` is the")
        A("one-way cost at which net alpha vs equal-weight reaches zero — compare it against")
        A("what execution actually costs. (Annualized by COMPOUNDING here, vs arithmetically")
        A("in the construction table above, so the gross figures differ slightly by")
        A("convention.)\n")
        A("| book | annual turnover | gross alpha | net alpha | cost drag | breakeven one-way |")
        A("|---|---|---|---|---|---|")
        for key, name in (("top_decile", "top decile"), ("top_25", "top 25")):
            b = cs.get(key) or {}
            be = b.get("breakeven_one_way_bps")
            be_s = ("n/a" if be is None else
                    (">grid" if be == float("inf") else f"{be:.0f} bps"))
            A(f"| {name} | {_rate(b.get('annual_turnover'), 0)} | {_pct(b.get('gross_alpha'))} "
              f"| {_pct(b.get('net_alpha'))} | {_pct(b.get('cost_drag_ann'))} | **{be_s}** |")
    at = p.get("after_tax") or {}
    if (at.get("top_decile") or {}).get("after_tax_alpha") is not None:
        A("")
        A("## After tax — what a TAXABLE account actually keeps\n")
        A("The book turns over ~250%/yr on a quarterly rebalance, so almost every gain is")
        A("realized inside a year and taxed as ordinary income. Lot-level FIFO accounting,")
        A("tax paid from the portfolio so the compounding is genuinely after-tax.\n")
        A("| book | gross alpha | after-tax alpha | tax drag | short-term share of gains |")
        A("|---|---|---|---|---|")
        for key, name in (("top_decile", "top decile"), ("top_25", "top 25")):
            b = at.get(key) or {}
            if b.get("after_tax_alpha") is None:
                continue
            A(f"| {name} | {_pct(b.get('gross_alpha'))} | **{_pct(b.get('after_tax_alpha'))}** "
              f"| {_pct(b.get('total_drag_ann'))} | {_rate(b.get('short_term_share_of_gains'))} |")
        b = at.get("top_decile") or {}
        A("")
        A(f"Rates: short-term {_rate(b.get('short_rate'))} / long-term "
          f"{_rate(b.get('long_rate'))} (US federal top bracket incl. NIIT; **state tax NOT "
          f"included** — CA would add ~13.3%).")
        A(f"**A tax-advantaged account (IRA/401k) pays none of this** and earns the net-of-cost "
          f"figure in the Tradeability table instead.")
    hvp = p.get("holdout_validation") or {}
    if hvp.get("splits"):
        A("")
        # AUDIT B8 — this section used to be headed "Held-out confirmation ... out-of-sample"
        # and to describe a protocol the code did not run. `stability` is the demanding
        # both-halves check (the decide-half rule is NOT consulted); `OOS` is the rule-gated
        # verdict, and `not_flagged` there means no out-of-sample test of that theme was run at
        # all. Both ship, because reading one as the other is the error B8 exists to stop.
        A("## Held-out theme checks — stability, and the rule-gated out-of-sample verdict\n")
        A("Dates split in half by time, boundary date embargoed, both directions.\n")
        A("**stability** = zeroing the theme improved BOTH long-short t and top-decile alpha in")
        A("BOTH directions. Demanding, and it is what every shipped decision here rested on —")
        A("but it is a both-halves check on the full sample, NOT an out-of-sample confirmation.\n")
        A("**OOS** applies the pre-specified decide-half rule (median IC ≤ 0) as a gate, so a")
        A("direction counts only where the rule actually flagged the theme. `not_flagged` means")
        A("no out-of-sample test was run — which is not the same as a negative result.\n")
        A("| theme | stability | OOS | dirs | ΔLS t (early→late) | Δtop-dec (early→late) | "
          "ΔLS t (late→early) | Δtop-dec (late→early) |")
        A("|---|---|---|---|---|---|---|---|")
        a_s = (hvp["splits"].get("decide_early_measure_late") or {}).get("themes") or {}
        b_s = (hvp["splits"].get("decide_late_measure_early") or {}).get("themes") or {}
        oos = hvp.get("oos_verdicts") or {}
        dirs = hvp.get("oos_directions_tested") or {}
        for t, v in sorted((hvp.get("verdicts") or {}).items(),
                           key=lambda kv: {"confirmed": 0, "not_replicated": 1}.get(kv[1], 2)):
            a, b = a_s.get(t) or {}, b_s.get(t) or {}
            A(f"| {t} | **{v}** | {oos.get(t, 'n/a')} | {dirs.get(t, '-')} | "
              f"{_f2(a.get('delta_long_short_tstat'))} | "
              f"{_pct(a.get('delta_top_decile_alpha'))} | "
              f"{_f2(b.get('delta_long_short_tstat'))} | "
              f"{_pct(b.get('delta_top_decile_alpha'))} |")
    if cp.get("recommended_weights"):
        A("")
        A("## Weights CPCV would adopt\n")
        A("```")
        A(json.dumps(cp["recommended_weights"], indent=2, sort_keys=True))
        A("```")
    A("")
    return "\n".join(L)


def write(res: dict, universe_label: str | None = None, cleanups: dict | None = None,
          per_signal: dict | None = None, root: str | None = None) -> dict:
    """Write both files at the repo root. Returns {"json": path, "md": path}."""
    root = root or repo_root()
    payload = build_payload(res, universe_label=universe_label, cleanups=cleanups,
                            per_signal=per_signal, root=root)
    jp = os.path.join(root, JSON_NAME)
    mp = os.path.join(root, MD_NAME)
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)
        f.write("\n")
    with open(mp, "w", encoding="utf-8") as f:
        f.write(render_md(payload))
    # AUDIT M6 — fail the run, but only AFTER both files are on disk. A 20-40 minute run must
    # not lose its output to a schema complaint, and the evidence has to be readable to be
    # actionable. There is deliberately NO environment-variable escape hatch (RUN_RULES A5 —
    # never silence a check); the documented allowlist in `payload_schema.BLOCK_SPEC` is the
    # legitimate door, and it leaves a diff.
    _dropped = [e for e in (payload.get("errors") or []) if e.get("dropped_field")]
    if _dropped:
        raise _schema.PayloadSchemaError(
            f"{len(_dropped)} computed field(s) dropped from {JSON_NAME}: "
            + _schema.describe([{"block": e["block"], "field": e["dropped_field"]}
                                for e in _dropped])
            + f". Files were written to {jp} so the run's work is not lost.")
    return {"json": jp, "md": mp, "payload": payload}
