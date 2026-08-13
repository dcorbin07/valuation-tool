"""
Valquo Index export — the tracked paper book, as a plain JSON file.

A broad top-decile, large-cap-tilted book: the construction the backtest supports, and the
one whose result is least dependent on a handful of names. (The older note here said the
concentrated top-25 "lost" — that was true of the pre-P5 model and is no longer: post-P5 the
top-25 book scores HIGHER gross. It is also the noisiest statistic in the study, so breadth
is still the right choice for a tracked book — for robustness, not because concentration
underperforms.) What this exports:

  1. take the latest scan,
  2. keep the large caps (the market-cap tier where the measured IC was strongest),
  3. keep the top decile of those by hot score,
  4. weight them, and write the list out.

Written to data/ (gitignored) so the Cowork side can pick it up and track it against SPY
without this repo carrying a data file that changes every day.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

DEFAULT_PATH = os.path.join("data", "valquo_index.json")
LARGE_CAP_MIN = 10e9          # $10B+ = "large cap" for the tilt
TOP_DECILE = 0.10
MIN_NAMES = 10                # a "decile" of a small scan would be too thin to be a book
MAX_WEIGHT = 0.08             # no single name dominates

# SESSION 16 (PT-SPLIT) — the floor a book must clear to be THE Valquo Index, i.e. the object
# `PAPER_TRACK_CONTRACT.md` binds, rather than some other book built by the same function.
#
# Why a floor is needed at all: `n = max(MIN_NAMES, round(len(large) * TOP_DECILE))`, so this
# function happily builds a 10-name book out of a truncated scan and labels it "Valquo Index"
# with a perfectly correct method string. The Tradier sandbox engine ran on exactly that for
# four days — 10 names against the published book's 86 — and it was read as a cap violation
# ("10% weights against an 8% cap") when it is nothing of the kind: `cap` below is
# `max(MAX_WEIGHT, 1/len(picks))` BY DESIGN, because 10 names at 8% sum to 80%. The weights
# were right for the book; the BOOK was wrong. One construction, two inputs.
#
# 50 is set from what the cap means rather than from the observed 86: the 8% cap can only bind
# on a book of at least 13 names, and the published method is a top DECILE of the large-cap
# tier, so a book that cannot plausibly be a decile of a real universe is not the Index. It is
# a floor, not a target — the published book is free to be 86 or 120.
CONTRACT_MIN_POSITIONS = 50


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _sector_block(positions) -> tuple:
    """(sector -> weight, whether the source actually carried sectors).

    A source with no sector column (the Sharadar export has none) would otherwise emit
    {"": 1.0} — which reads to a downstream consumer as "one real sector holds the entire
    book" rather than "this data is missing". Say missing explicitly.
    """
    sectors: dict = {}
    for p in positions:
        key = (p.get("sector") or "").strip() or "unknown"
        sectors[key] = round(sectors.get(key, 0.0) + (p.get("weight") or 0.0), 5)
    ordered = dict(sorted(sectors.items(), key=lambda kv: -kv[1]))
    return ordered, any((p.get("sector") or "").strip() for p in positions)


def conformance(n_positions: int, effective_max_weight: float,
                n_eligible: Optional[int] = None) -> dict:
    """Is this book THE Valquo Index, or merely a book this function built?

    SESSION 16 (PT-SPLIT). The contract binds one object; `build_index` can produce several, and
    until now nothing in the payload said which one you were holding. Two conditions, both
    necessary:

      * at least `CONTRACT_MIN_POSITIONS` names, and
      * the 8% cap actually BINDS — `effective_max_weight <= MAX_WEIGHT`. On a small book the cap
        silently relaxes to equal weight (it has to; 10 names at 8% sum to 80%), so an unbound
        cap is the signature of a book too small to be the Index.

    Reported, never enforced here: this is a pure description of a payload. `paper_track.seed_book`
    is where it becomes a gate, because that is where a wrong book would start being recorded.
    """
    n = int(n_positions or 0)
    cap = float(effective_max_weight or 0.0)
    cap_binds = cap <= MAX_WEIGHT + 1e-9
    big_enough = n >= CONTRACT_MIN_POSITIONS
    why = []
    if not big_enough:
        why.append(f"{n} positions, below the contract floor of {CONTRACT_MIN_POSITIONS}"
                   + (f" (eligible tier {n_eligible})" if n_eligible is not None else ""))
    if not cap_binds:
        why.append(f"the {MAX_WEIGHT:.0%} cap does not bind - effective cap is {cap:.4f}, i.e. "
                   f"the book is too small for the cap to be reachable")
    if n and n <= MIN_NAMES:
        why.append(f"the book sits on the MIN_NAMES floor ({MIN_NAMES}), so it is the size the "
                   f"builder fell back to rather than a decile it measured")
    return {"conforms": bool(big_enough and cap_binds),
            "n_positions": n, "effective_max_weight": round(cap, 5),
            "max_weight": MAX_WEIGHT, "min_positions": CONTRACT_MIN_POSITIONS,
            "n_eligible": (int(n_eligible) if n_eligible is not None else None),
            "why_not": why}


def build_index(rows, large_cap_min: float = LARGE_CAP_MIN,
                top_decile: float = TOP_DECILE, weighting: str = "score",
                top_n: int | None = None, held=None,
                exit_frac: float | None = None) -> dict:
    """Top-decile, large-cap-tilted book from scan rows. Pure function — easy to test.

    `held` + `exit_frac` apply the NO-TRADE BAND adopted 2026-08-13 (S14, width 0.30). `held` is
    the previous book's tickers; a held name is kept until it falls past `exit_frac` of the
    ranked eligible tier, instead of being sold the moment it slips out of the top decile.

    BOTH are required for the band to do anything, and that is deliberate rather than defensive:
    with no previous book there is nothing to hold, so the first rebalance after this ships is
    necessarily a plain top-N book. The band's effect begins at the SECOND one.

    The rule itself is imported from `no_trade_band` — the same object the backtest applies — so
    this path cannot drift from the measured one.
    """
    scored = [r for r in rows if _f(r.get("hot_score")) is not None and _f(r.get("price"))]

    large = [r for r in scored if (_f(r.get("market_cap")) or 0) >= large_cap_min]
    tilt = "large-cap only"
    # If the scan doesn't carry market caps (or is a small universe), fall back to the
    # biggest half rather than silently emitting an all-cap book under a large-cap label.
    if len(large) < MIN_NAMES:
        with_mc = [r for r in scored if _f(r.get("market_cap"))]
        if len(with_mc) >= MIN_NAMES:
            with_mc.sort(key=lambda r: -_f(r.get("market_cap")))
            large = with_mc[:max(MIN_NAMES, len(with_mc) // 2)]
            tilt = "largest half (too few names above the large-cap floor)"
        else:
            large = scored
            tilt = "no market-cap data — all scored names"

    large.sort(key=lambda r: -_f(r.get("hot_score")))
    # A FIXED book size (top_n) or a fraction of the eligible tier (top_decile). The roth
    # config is a 25-name book; taxable is the decile.
    n = int(top_n) if top_n else max(MIN_NAMES, int(round(len(large) * top_decile)))
    n = max(MIN_NAMES, n)

    # --- NO-TRADE BAND (S14, adopted 2026-08-13 at width 0.30) -----------------------------
    # Enter on the top `n`; keep a name already held until it falls past `exit_rank`. The rule
    # and the rank derivation are IMPORTED, never restated here.
    from .no_trade_band import (band_select, exit_rank_for, held_within_band,
                                BAND_HELD_NOTE)
    import numpy as _np

    _held = {t for t in (held or []) if t}
    _exit_rank = exit_rank_for(len(large), n, exit_frac)
    band_retained: set = set()
    if _held and _exit_rank > n and large:
        _comp = _np.array([_f(r.get("hot_score")) for r in large], dtype=float)
        _ticks = _np.array([r["ticker"] for r in large], dtype=object)
        _sel = band_select(_comp, _ticks, _held, min(n, len(large)), _exit_rank)
        band_retained = held_within_band(_comp, _ticks, _held, min(n, len(large)), _exit_rank)
        _by_ticker = {r["ticker"]: r for r in large}
        picks = [_by_ticker[t] for t in _sel if t in _by_ticker]
    else:
        picks = large[:min(n, len(large))]

    if weighting == "equal" or not picks:
        raw = {r["ticker"]: 1.0 for r in picks}
    else:
        # Score-weighted above the cohort's floor, so the weight reflects the *edge*
        # rather than the arbitrary 1-100 offset every name carries.
        floor = min(_f(r.get("hot_score")) for r in picks)
        raw = {r["ticker"]: max(0.01, _f(r.get("hot_score")) - floor + 1.0) for r in picks}

    total = sum(raw.values()) or 1.0
    weights = {k: v / total for k, v in raw.items()}
    # The cap is only reachable if n * MAX_WEIGHT >= 1 — with 10 names an 8% cap would
    # sum to 80% and the redistribution below would loop forever pushing past it. So the
    # effective cap never goes below equal weight.
    cap = max(MAX_WEIGHT, 1.0 / len(picks)) if picks else MAX_WEIGHT
    if picks and cap <= 1.0 / len(picks) + 1e-12:
        # The cap has collapsed to equal weight, which is then the ONLY feasible
        # solution. Assign it directly — iterating would just oscillate toward it.
        weights = {k: 1.0 / len(picks) for k in raw}
    for _ in range(12):
        over = {k: w for k, w in weights.items() if w > cap + 1e-12}
        if not over:
            break
        excess = sum(w - cap for w in over.values())
        for k in over:
            weights[k] = cap
        rest = {k: w for k, w in weights.items() if k not in over}
        rest_total = sum(rest.values()) or 1.0
        if rest_total <= 0:
            break
        for k in rest:
            weights[k] += excess * rest[k] / rest_total

    positions = [{
        "ticker": r["ticker"], "name": (r.get("name") or "")[:60],
        "sector": r.get("sector") or "", "rank": r.get("rank"),
        "hot_score": round(_f(r.get("hot_score")), 2),
        "price": round(_f(r.get("price")), 4),
        "market_cap": _f(r.get("market_cap")),
        "weight": round(weights.get(r["ticker"], 0.0), 5),
        # DISPLAY HONESTY (S14 adoption): a name the BAND retained is not an ordinary top-N
        # pick — it is held while a higher-ranked challenger was passed over. Presenting it
        # without saying so would show the user a book they cannot derive from the ranking
        # they are looking at.
        "band_retained": r["ticker"] in band_retained,
        "why_band": (BAND_HELD_NOTE if r["ticker"] in band_retained else ""),
    } for r in picks]

    sectors, sector_data = _sector_block(positions)

    return {
        "name": "Valquo Index",
        # FIGURES REFRESHED 2026-08-08 (P2 crowding memo, BUGS FOUND #3). Every number in this
        # string was measured on the pre-B6 2,710-name / 110-date panel and read as current
        # because it ships inside a payload rather than a results file. Sourced from
        # BACKTEST_RESULTS.json: construction.top_decile_alpha, costs.top_decile.net_alpha /
        # .breakeven_one_way_bps / .realised_one_way_bps, portfolio.alpha_vs_equal_weight.
        "method": ("Broad top-decile of the large-cap tier by hot score, score-weighted and "
                   "capped at 8%. On the full 2,531-name / 69-date backtest the top decile "
                   "returns +7.2%/yr over equal-weight gross, +6.1% net of modelled "
                   "transaction costs (breakeven 134bps one-way vs 33bps measured). Breadth is "
                   "chosen for robustness, not because concentration underperforms: the "
                   "top-25 book actually scores higher (+16.9% gross alpha) but is the "
                   "noisiest number in the study, so the decile is the honest book to track."),
        "criteria": {"large_cap_min": large_cap_min, "top_decile": top_decile,
                     "top_n": (int(top_n) if top_n else None),
                     "tilt": tilt, "weighting": weighting,
                     "max_weight": MAX_WEIGHT, "effective_max_weight": round(cap, 5)},
        # The band, as APPLIED — not as declared. `applied` is false whenever there was no
        # previous book to hold from, which is the honest state at the first rebalance and
        # must not read as "the band is off".
        "no_trade_band": {
            "width": exit_frac, "exit_rank": (_exit_rank if exit_frac else None),
            "n_held_supplied": len(_held), "applied": bool(_held and exit_frac),
            "n_band_retained": len(band_retained),
            "band_retained": sorted(band_retained),
            "note": ("names kept because they are still inside the band, while a higher-ranked "
                     "challenger was passed over" if band_retained else
                     ("no previous book supplied, so the band could not apply" if not _held
                      else "no held name sits inside the band on this cross-section")),
        },
        # WHERE THE PUBLISHED HEADLINE AND THE LIVE BOOK NOW DIFFER (S14 adoption, 2026-08-13).
        # `method` above is UNCHANGED and still describes the validated composite -- the plain
        # top-decile book every published figure was measured on. From this vintage the live
        # book also applies a no-trade band, which those figures do NOT include. Saying so here
        # is the alternative to the two tempting errors: quietly re-pointing the headline at a
        # construction nobody measured, or letting a reader assume the +7.2%/yr describes the
        # book in front of them.
        "headline_scope": {
            "headline_describes": "plain top-decile book, no no-trade band",
            "live_book_applies_band": bool(exit_frac),
            "differs": bool(exit_frac),
            "note": ("the published backtest figures in `method` were measured WITHOUT a "
                     "no-trade band. The live book applies one from vintage 4 (2026-08-13). "
                     "S14's own evidence is a held-out DIFFERENCE (+1.78pp and +1.77pp net "
                     "alpha in the two split directions), not a re-measured level, so the "
                     "headline is deliberately not restated." if exit_frac else
                     "no band applied; the live book matches the construction the headline "
                     "describes"),
        },
        "contract_conformance": conformance(len(positions), cap, len(large)),
        "n_scored": len(scored), "n_eligible": len(large), "n_positions": len(positions),
        "sector_data_available": sector_data,
        "sector_weights": sectors,
        "positions": positions,
    }


def _enrich_profiles(payload: dict, store=None) -> str:
    """Fill blank name/sector on a built book from the live feed; refresh its sector block."""
    positions = payload.get("positions") or []
    if not positions:
        return "no positions to enrich"
    try:
        from ..screener import profiles
        from ..screener.store import Store
        filled = profiles.decorate(positions, store=(store or Store()))
    except Exception as e:
        return f"skipped: {e}"
    payload["sector_weights"], payload["sector_data_available"] = _sector_block(positions)
    return f"filled name/sector on {filled} of {len(positions)} positions from the live feed"


def _full_universe_rows(data_dir: str, limit: int = 3000):
    """Score the WHOLE Sharadar universe as of its latest date -> (rows, as_of, dropped).

    The live-scan store is whatever the last FMP scan happened to cover, which is a few
    hundred names at best — and a "top decile" of that collapses to the 10-name MIN_NAMES
    floor, i.e. ten mega-caps wearing a decile's label. Scoring the full point-in-time
    universe instead gives a real decile (86 of 861 eligible large caps at last run) and needs
    no live API, so a quarterly rebalance can run headless.
    """
    from .data_providers import WRDSProvider
    from .fundamental_panel import score_universe_now
    from ..screener import universe as U

    class _Cfg:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_Cfg())
    ok, msg = prov.ready()
    if not ok:
        raise RuntimeError(f"Sharadar export not readable at {data_dir!r}: {msg}")
    tickers = prov.universe(limit=limit) or list(U.bundled_tickers())
    res = score_universe_now(prov, tickers)
    if not res or not res.get("rows"):
        raise RuntimeError("scored no rows from the full universe")
    return res["rows"], res.get("as_of"), (res.get("dropped_mc_divergence") or [])


def config_block(name: str | None, cfg_meta: dict | None) -> dict:
    """The `config` block a payload publishes, in ONE place.

    CONSOLIDATED 2026-08-13 BY THE S14 ADOPTION, because it had drifted. `export()` and the
    `/api/valquo-index` route each built this dict separately with their own copy of
    `band_note`, and when the band became real one copy would have been corrected and the other
    left telling readers to apply the band by hand -- after which it would have been applied
    twice. Same class of defect as the duplicated publication text; fixed the same way.
    """
    if not cfg_meta:
        return {}
    xf = cfg_meta.get("exit_frac")
    return {
        "name": name, "label": cfg_meta.get("label"),
        "rebalance_days": cfg_meta.get("rebalance_days"),
        # TRADING days -> calendar months, which is what a human schedules on.
        "rebalance_months": (round(cfg_meta["rebalance_days"] / 21.0, 1)
                             if cfg_meta.get("rebalance_days") else None),
        "exit_frac": xf, "exit_mult": cfg_meta.get("exit_mult"),
        "band_note": (("hold an existing position until it falls past this fraction of the "
                       "ranked tier. APPLIED AUTOMATICALLY as of the S14 adoption (2026-08-13) "
                       "against the previous book on disk - do NOT apply it again by hand. See "
                       "the payload's `no_trade_band` block for whether it actually bound, and "
                       "which names it retained.") if xf else
                      "no no-trade band on this configuration"),
        # The `measured` figures were measured at `measured_width`, which is NOT necessarily the
        # width now shipped. Published together so the two can never be silently conflated.
        "measured": cfg_meta.get("measured"),
        "measured_width": cfg_meta.get("measured_width"),
        "measured_width_note": (
            "the `measured` figures were measured at a band width of "
            f"{cfg_meta.get('measured_width')}, not the {xf} now shipped; no run has measured "
            "this configuration at the adopted width"
            if cfg_meta.get("measured_width") not in (None, xf) else ""),
    }


def _previous_book(path: str) -> list:
    """Tickers of the book currently on disk — the `held` set the band needs.

    Returns [] when there is no prior book, which makes the first rebalance after the adoption
    a plain top-N book. That is correct rather than a degraded mode: hysteresis with nothing to
    hold from is just selection.

    FAILS TO [] on any unreadable or malformed file, deliberately. A band that silently held the
    wrong names would be worse than one that does not apply, because the resulting book would
    still look like a valid book. `no_trade_band.applied` in the payload records which happened,
    so an empty read is visible rather than inferred.
    """
    try:
        with open(path, encoding="utf-8") as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(prev, dict):
        return []
    return [p.get("ticker") for p in (prev.get("positions") or [])
            if isinstance(p, dict) and p.get("ticker")]


def export(store=None, path: str = DEFAULT_PATH, data_dir: str | None = None,
           limit: int = 3000, config: str | None = None, **kw) -> dict:
    """Build the book and write the JSON. Returns the payload.

    `data_dir` -> score the full Sharadar universe point-in-time (the headless path, and the
    one that produces a genuine top decile). Otherwise fall back to the latest saved live scan.
    """
    # A named book config (settings.BOOK_CONFIGS) fixes width, cadence and band together, so
    # the emitted book cannot drift from the construction that was actually validated.
    cfg_meta = None
    if config:
        from ..screener import settings as S
        cfg_meta = (S.BOOK_CONFIGS or {}).get(config)
        if not cfg_meta:
            raise RuntimeError(f"unknown book config {config!r}; "
                               f"known: {sorted(S.BOOK_CONFIGS or {})}")
        if cfg_meta.get("top_n"):
            kw["top_n"] = cfg_meta["top_n"]
        if cfg_meta.get("top_frac"):
            kw["top_decile"] = cfg_meta["top_frac"]

    # --- NO-TRADE BAND (S14, adopted by Don 2026-08-13 at width 0.30) ----------------------
    # Until today the band was DECLARED in configs and emitted as an instruction string for a
    # human rebalancer; nothing applied it. It is now applied here, which is the whole content
    # of the adoption.
    #
    # WHERE IT APPLIES, and why not everywhere: S14 measured the DECILE book (enter on the top
    # 10%, hold to the top 30%). `exit_frac` is a fraction of the ranked UNIVERSE, which is
    # meaningful for a decile book and NOT for a fixed-N one -- on a 25-name book against a
    # large universe it would hold almost every name almost forever. So a config carrying
    # `top_n` (roth) stays band-less, and that is a fidelity decision rather than an omission:
    # a banded 25-name book is a construction S14 never measured.
    from .no_trade_band import BAND_WIDTH
    if "exit_frac" not in kw:
        _w = cfg_meta.get("exit_frac") if cfg_meta else BAND_WIDTH
        kw["exit_frac"] = None if kw.get("top_n") else _w
    if "held" not in kw:
        kw["held"] = _previous_book(path)
    dropped, scan_date = [], None
    if data_dir:
        rows, scan_date, dropped = _full_universe_rows(data_dir, limit=limit)
        source = ("Sharadar SF1+SEP export via WRDSProvider (point-in-time), "
                  "shipped settings.py weights")
    else:
        if store is None:
            from ..screener.store import Store
            store = Store()
        scan_date = store.latest_scan_date()
        rows = store.load_snapshot(scan_date) if scan_date else []
        source = "latest saved live scan snapshot"
    payload = build_index(rows, **kw)
    # Fill company names and sectors from the LIVE feed. The point-in-time Sharadar export
    # carries neither field, which is why an exported book listed bare tickers and reported
    # sector_data_available: false — its diversification was invisible. Done on the finished
    # book (tens of names) rather than the whole scored universe (thousands), and only on
    # rows that are actually blank. Descriptive fields only: nothing here feeds a score, so
    # today's classification is safe. It would NOT be safe inside the panel, where applying a
    # current sector label to a 1998 row is look-ahead.
    payload["profile_enrichment"] = _enrich_profiles(payload, store)
    payload["scan_date"] = scan_date
    payload["data_as_of"] = scan_date
    payload["source"] = source
    # Names whose market cap could not be established (DAILY vs shares x price disagree) are
    # excluded from a tradeable book; recorded so the omission is auditable, not silent.
    payload["excluded_market_cap_divergence"] = [
        {"ticker": d["ticker"], "daily_mc": d["daily_mc"], "derived_mc": d["derived_mc"],
         "ratio": round(d["ratio"], 2)} for d in dropped]
    if cfg_meta:
        # CORRECTED 2026-08-13 BY THE S14 ADOPTION. This comment used to read: "The band is a
        # REBALANCE rule (it compares against the previous book), so a one-shot export cannot
        # apply it — it is emitted as instruction for whoever rebalances." The premise was
        # right and the conclusion was wrong: the band does need the previous book, but the
        # previous book is ON DISK at `path`, so the export CAN apply it and now does. The
        # `band_note` below is corrected with it — leaving it would have told a reader the
        # band still had to be applied by hand, and it would then have been applied twice.
        payload["config"] = config_block(config, cfg_meta)
    payload["generated_at"] = _dt.datetime.now().replace(microsecond=0).isoformat()

    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    payload["path"] = path
    return payload


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Export the Valquo Index (top-decile large caps).")
    ap.add_argument("--out", default=DEFAULT_PATH)
    ap.add_argument("--large-cap-min", type=float, default=LARGE_CAP_MIN)
    ap.add_argument("--top-decile", type=float, default=TOP_DECILE)
    ap.add_argument("--weighting", choices=("score", "equal"), default="score")
    ap.add_argument("--full-universe", nargs="?", const="data/backtest", default=None,
                    metavar="DATA_DIR",
                    help="score the whole Sharadar universe point-in-time instead of the last "
                         "live scan (headless; the only path that yields a real top decile). "
                         "Optionally takes the export dir, default data/backtest.")
    ap.add_argument("--limit", type=int, default=3000, help="universe size for --full-universe")
    ap.add_argument("--config", default=None,
                    help="named book config: 'roth' (top-25, 6-week, no band) or 'taxable' "
                         "(decile, quarterly, 20%% band). Sets width and emits the cadence.")
    a = ap.parse_args(argv)
    try:
        p = export(path=a.out, large_cap_min=a.large_cap_min, top_decile=a.top_decile,
                   weighting=a.weighting, data_dir=a.full_universe, limit=a.limit,
                   config=a.config)
    except RuntimeError as e:
        print(f"Could not build the book: {e}")
        return 1
    if not p["positions"]:
        print("No positions — no scan snapshot yet (run a scan first), or try --full-universe.")
        return 1
    print(f"Valquo Index -> {p['path']}   as of {p.get('data_as_of')}   "
          f"{p['n_positions']} of {p['n_eligible']} eligible ({p['n_scored']} scored)")
    print(f"  source: {p.get('source')}")
    if p.get("config"):
        _c = p["config"]
        print(f"  config: {_c['name']} — {_c.get('label')}")
        print(f"  rebalance every {_c.get('rebalance_days')} trading days "
              f"(~{_c.get('rebalance_months')} months)"
              + (f", no-trade band {_c['exit_frac']:.0%}" if _c.get("exit_frac") else ", no band"))
    print(f"  tilt: {p['criteria']['tilt']}")
    if p["n_scored"] < 200:
        print(f"  WARNING: only {p['n_scored']} names scored — a 'top decile' of that is not a "
              f"decile. Use --full-universe for a real book.")
    if p.get("excluded_market_cap_divergence"):
        print("  excluded (market cap unverifiable): "
              + ", ".join(f"{d['ticker']} ({d['ratio']:.0f}x)"
                          for d in p["excluded_market_cap_divergence"][:6]))
    for x in p["positions"][:15]:
        print(f"   {x['ticker']:6} {x['weight']*100:5.2f}%  hot {x['hot_score']:5.1f}  {x['sector'][:22]}")
    if len(p["positions"]) > 15:
        print(f"   ... and {len(p['positions']) - 15} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
