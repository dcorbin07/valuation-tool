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

import csv as _csv
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


def _measured_for(cfg_meta: dict) -> dict:
    """The config's measured figures, from the artifact. Delegated, never copied (`B7`)."""
    try:
        from ..screener import settings as _S
        for name, cfg in (_S.BOOK_CONFIGS or {}).items():
            if cfg is cfg_meta or cfg == cfg_meta:
                return _S.measured(name)
        return _S.measured()
    except Exception:                                                    # noqa: BLE001
        return {}


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


#: The deployed seven, at ONE weight each. `1/7` and the live `0.125` are the SAME OBJECT here
#: and that is measured, not assumed: `attribution._branch` divides every contribution by
#: `sum(present * w)`, so multiplying all weights by a constant leaves the contributions exactly
#: unchanged. A rescaling cannot move a ranking, and D9's "flat 1/7 against bucket-specific
#: weights" is therefore NOT a scaling difference.
#:
#: WHAT ACTUALLY DIFFERS, measured on `settings.WEIGHTS_ESTABLISHED` and `WEIGHTS_SPECULATIVE`:
#:   * **MEMBERSHIP** -- established blends `quality`, speculative blends `growth`, at the same
#:     weight. Every other entry is identical. So a speculative-bucket name is currently scored
#:     with `growth` INSTEAD OF `quality`, which is a different composite rather than a
#:     differently-weighted one.
#:   * **SOFT BUCKETING** -- the live path scores a borderline name under BOTH rulebooks and
#:     blends by `p_established`, so its composite is a mixture of two weight sets.
#:
#: The index build uses one set, hard, over the panel's seven. `growth` is absent because it
#: carries zero weight in the deployed composite the record was built on.
FLAT_SEVEN = {"value": 1.0 / 7, "quality": 1.0 / 7, "momentum": 1.0 / 7,
              "insider": 1.0 / 7, "capital_discipline": 1.0 / 7, "size": 1.0 / 7,
              "institutional": 1.0 / 7}


def rescore_flat_seven(rows) -> dict:
    """Overwrite `hot_score` on a copy of `rows` with the FLAT-SEVEN ranking. Returns a report.

    FOR THE INDEX BUILD ONLY. The hot list keeps its own bucket-specific score, because that is
    what the site has always shown and changing it is a product decision rather than a fidelity
    one. This changes which names the BOOK selects, and nothing else.

    IT DELEGATES TO `attribution.decompose` (B7) -- the same function `screen._decompose` calls,
    with `soft=False` and one weight set for both buckets, so there is no second composite
    implementation to drift. `hot_score` is rebuilt as the same percentile rank of the same
    composite that `screen.py` builds it from, so `build_index` needs no knowledge of this.
    """
    import pandas as pd
    from ..screener.attribution import decompose

    have = [r for r in rows if isinstance(r.get("factors"), dict)]
    if not have:
        return {"rescored": False, "reason": "no row carries theme factors", "n": 0}
    df = pd.DataFrame([r["factors"] for r in have],
                      index=[r.get("ticker") for r in have])
    for c in FLAT_SEVEN:
        if c not in df.columns:
            df[c] = float("nan")
    df["bucket"] = "established"          # ONE rulebook: the bucket switch is what is removed
    comp, _ = decompose(df, FLAT_SEVEN, FLAT_SEVEN, soft=False)
    ranked = comp.rank(pct=True) * 99 + 1
    moved = 0
    for r in have:
        t = r.get("ticker")
        if t in ranked.index and ranked[t] == ranked[t]:            # not NaN
            before = r.get("hot_score")
            r["hot_score"] = float(ranked[t])
            r["hot_score_basis"] = "flat_seven"
            if before is not None and abs(float(before) - float(ranked[t])) > 1e-9:
                moved += 1
    return {"rescored": True, "n": len(have), "moved": moved,
            "weights": dict(FLAT_SEVEN),
            "note": ("the index book is ranked on ONE flat weight set over the deployed seven, "
                     "with the live path's bucket switch (quality vs growth) and its soft "
                     "blending both off. The hot list keeps its own score.")}


def trim_universe(rows, universe_rank: int, rank_key=None):
    """The top `universe_rank` rows by `rank_key` (default: point-in-time market cap).

    THE UNIVERSE IS AN INPUT AND THE CONSTRUCTION IS `build_index`'s. `INDEX-BEST`'s arms 2 and
    3 differ from the incumbent in exactly this trim -- the names `build_index` is allowed to
    see -- and in nothing else, which is why they could be measured by calling the live
    function rather than a lookalike (`B7`).

    THIS LIVED INSIDE `served_index_book.book_fn` UNTIL `INDEX-CANDIDATE` NEEDED IT OUTSIDE A
    BACKTEST, and it moved here rather than being copied. A second copy of a universe boundary
    is how a construction comes to be MEASURED on one population and SHIPPED on another, with
    both halves looking correct in isolation -- and the boundary is the only thing separating
    arm 2 from the book in force, so a drift here would be invisible and total.

    TIES ARE BROKEN BY TICKER so the boundary is deterministic. An unstable boundary would make
    the same inputs produce different books run to run, which is the defect the trade loop's set
    iteration had: a 1,500th and 1,501st name on the same market cap must not be decided by
    dict ordering.

    A ROW WITH NO RANK VALUE SORTS LAST rather than being dropped. Dropping would silently
    shrink the universe, so a vendor gap would read as a smaller market; sorting last keeps the
    count honest and lets it be trimmed off by the rank it actually has.
    """
    if not universe_rank or universe_rank <= 0:
        raise ValueError("universe_rank must be a positive integer, got %r" % (universe_rank,))
    key = rank_key or (lambda r: r.get("market_cap") or 0.0)
    return sorted(rows, key=lambda r: (-(key(r) or 0.0), r["ticker"]))[:universe_rank]


# -------------------------------------------------------------------------------------------
# CANDIDATE CONSTRUCTIONS -- NAMED, NOT DEFAULT, NOT ADOPTED, NOT PUBLISHED.
#
# `INDEX-CHOICE` settled one of its two questions and left the other open: "IF you move, move to
# arm 2" is decided on the evidence, "whether to move at all" is Don's call on period risk. This
# registry exists so that call can be taken on 2026-10-20 instead of being designed on the 22nd
# -- the construction is ready and switched off, which is the whole deliverable.
#
# WHY THIS IS NOT AN ENTRY IN `settings.BOOK_CONFIGS`, AND IT IS NOT TIDINESS. Four consumers
# ITERATE that dict -- `scripts/backtest_card.py`, `fundamental_panel.py`'s `book_configs`
# block, this module's own `config_block` helper and `results_file.py` -- so a third entry would
# be measured by the backtest card, carried into `BACKTEST_RESULTS.json`, and listed back to any
# caller of a `?config=` endpoint inside a 400's `known` array. On the plainest reading that is
# PUBLISHED, which the item forbids. A separate namespace cannot leak into a surface that does
# not know it exists, and a test pins that `BOOK_CONFIGS` still holds exactly the two shipped
# books -- in both directions, because a one-way containment test passes if the dicts are merged.
#
# EVERY MEASURED FIGURE BELOW IS A COMMITTED LITERAL READ OUT OF `INDEX_BEST.json` (`MA13`), so
# a re-run that moves one shows up as a diff here rather than as two documents disagreeing.
# `scripts/index_best.py`'s own gate literals were FABRICATED on their first cut and its run
# refused them at 1.795e-07; these were copied from the artifact, and the test re-reads them
# from it rather than trusting this comment.
INDEX_CANDIDATES = {
    "liquid-decile": {
        "arm": "2_liquid_decile",
        "label": "top 1500 by point-in-time MARKET CAP, top decile, score-weighted",
        "register": "PREREG_index_best.md (arm 2); DECISION_index_choice.md",
        "artifact": "data/free_analysis/INDEX_BEST.json arms.2_liquid_decile",
        # --- the construction, one knob at a time ------------------------------------------
        "universe_rank": 1500,
        "rank_key": "market_cap",
        # THE NAME SAYS "LIQUID" AND THE CONSTRUCTION IS MARKET CAP, and that is a correction
        # `PREREG_index_best.md` §1a makes about its OWN arm names rather than a slip here:
        # "there is NO point-in-time liquidity measure, so 'most liquid' CANNOT be built as
        # stated" -- `B13` is PARTIAL-BLOCKED-ON-DATA for exactly this, the price export being
        # `date,close`. Measured, the within-date Spearman between market cap and 63-day dollar
        # ADV is 0.7119, so the proxy explains about half the variance of a true liquidity
        # screen and IS a materially different screen; that register's own words are "every
        # arm's universe is a MARKET-CAP universe wearing a liquidity label".
        #
        # THE NAME IS KEPT ANYWAY, deliberately: it is the name Don will be reading in
        # `DECISION_index_choice.md` on the 20th, and a builder whose name does not match the
        # memo is the worse hazard. So the correction travels in the payload and in the CLI
        # output instead, where it cannot be missed by someone who only runs the command.
        "rank_key_is_market_cap_not_liquidity": {
            "spearman_vs_63d_dollar_adv": 0.7119,
            "source": "PREREG_index_best.md 1a (B13)",
        },
        # 0.0, NOT the $10B default: the 1,500-name trim IS the tier, so a second large-cap
        # filter on top of it would cut the universe twice and make the arm a different object.
        # Measured consequence, from the artifact: `tilt_values` is still ["large-cap only"] on
        # every date and `dates_on_the_fallback` is 0, because every row passes `>= 0.0` and the
        # `MIN_NAMES` fallback therefore never fires.
        "large_cap_min": 0.0,
        "top_decile": 0.10,
        "top_n": None,
        "weighting": "score",
        "exit_frac": 0.30,
        "rebalance_days": 63,
        "horizon": 63,
        # --- what it measured (literals, from the artifact) -------------------------------
        "measured": {
            "roth_net_ann": 0.2294646167705674,
            "roth_sharpe": 1.1442622403420502,
            "roth_max_drawdown": -0.27600090292443336,
            "annual_turnover": 1.9268114715770899,
            "realised_one_way_bps": 29.344051612262923,
            "book_size": {"min": 147, "median": 150.0, "max": 150},
            "eligible_tier": {"min": 1471, "median": 1500.0, "max": 1500},
            "dates_below_contract_min_positions": 0,
            "cap_binds_on_dates": 0,
        },
        # --- the three things an operator has to know BEFORE building it -------------------
        #
        # (1) IT IS NOT BUILDABLE BY THE FREE ROUTE, and the artifact's own field says the
        # opposite because it answers a different question. `INDEX_BEST.json` carries
        # `buildable_from_live_scan: true`, which means "can a 1,500-name universe be FORMED
        # from a live scan" -- it can, the scan scores ~1,800 names. `DECISION_index_choice.md`
        # says NO, which means "does the resulting BOOK match the one that was measured" -- it
        # does not: on `D9`'s own shared population the live-route decile overlaps the
        # Sharadar-built decile by 0.2326 against `D9`'s pre-committed 0.60 bar. Both
        # statements are true and only the second one decides anything.
        "free_route": {
            "buildable": False,
            "decile_overlap": 0.2326,
            "bar": 0.60,
            "source": "DECISION_index_choice.md; PREREG_index_choice.md B2",
            "note": "INDEX_BEST.json's buildable_from_live_scan answers whether a 1500-name "
                    "universe can be FORMED, not whether the resulting book MATCHES. It does "
                    "not. Path B (Sharadar) only.",
        },
        # (2) ADOPTING IT IS A VINTAGE EVENT. Book vintage 4 has been open since 2026-08-13;
        # this changes the construction, which `PAPER_TRACK_CONTRACT.md` §5a names outright, so
        # it closes vintage 4 and opens vintage 5 -- discarding the accrued clock and restarting
        # the 60-month horizon for no statistical gain. That is the price, and it is Don's to
        # pay or not. The vintage NUMBER is derived from the register at build time and is not
        # read from here; 5 is the expectation, not the source of truth.
        "vintage_event": True,
        # (3) THE CONTRACT'S POSITION FLOOR HOLDS, and it is the one thing arm 2 has over arm 3.
        # `CONTRACT_MIN_POSITIONS` is 50 and arm 2's smallest book is 147, conformant on 69 of
        # 69 dates, so `seed_book` accepts it unchanged. Arm 3's 25-name book is refused on
        # every date and would have required changing the floor.
        "contract_min_positions_holds": True,
        "adopted": False,
        "default": False,
    },
}


def candidate(name: str) -> dict:
    """Resolve a candidate by name, or refuse naming the ones that exist."""
    cfg = INDEX_CANDIDATES.get(name)
    if not cfg:
        raise RuntimeError("unknown index candidate %r; known: %s"
                           % (name, sorted(INDEX_CANDIDATES)))
    return cfg


def build_candidate(rows, name: str, *, held=None, index_fn=None) -> dict:
    """Build a NAMED, NON-DEFAULT candidate construction from scan rows.

    IT REFUSES RATHER THAN APPROXIMATES. If `rows` cannot form the declared universe -- fewer
    rows than `universe_rank` -- this raises instead of trimming to whatever is there. A
    30-name "top 1500" is not a smaller version of this book, it is a different construction
    wearing its name, and it would be undetectable downstream: the payload would carry the
    right label, the right cap and a plausible count.

    THAT IS STRICTER THAN THE BACKTEST WAS, and the difference is reported rather than smoothed.
    In `served_index_book` the universe is "the top 1,500 or all of them where fewer exist" --
    the artifact's `eligible_tier.min` is 1471, so the early cross-sections genuinely are
    smaller. For a one-shot operator build a short universe means an incomplete export, which
    is worth refusing; for a 69-date backtest it is just the panel's early width.

    `held` IS NOT DEFAULTED FROM DISK, and that is deliberate. The book on disk is the
    INCUMBENT's -- a different construction over a different universe -- so banding against it
    would hold names this universe may not even contain. The first build under a new
    construction is necessarily band-less, exactly as `INDEX-BEST`'s own first date was
    (`build_index`: "with no previous book there is nothing to hold ... the band's effect
    begins at the SECOND one"). A caller that genuinely has a prior book OF THIS CONSTRUCTION
    passes it explicitly.
    """
    cfg = candidate(name)
    n = int(cfg["universe_rank"])
    if len(rows) < n:
        raise RuntimeError(
            "candidate %r declares a %d-name universe and only %d rows were supplied; "
            "refusing to build a different construction under this name. Use the Sharadar "
            "export (--full-universe) rather than a live scan snapshot." % (name, n, len(rows)))
    _rk = None if cfg["rank_key"] == "market_cap" else (lambda r: r.get(cfg["rank_key"]))
    trimmed = trim_universe(rows, n, rank_key=_rk)
    ix = index_fn or build_index
    bk = ix(trimmed, large_cap_min=cfg["large_cap_min"], top_decile=cfg["top_decile"],
            top_n=cfg["top_n"], weighting=cfg["weighting"], exit_frac=cfg["exit_frac"],
            held=held)
    bk["candidate"] = {
        "name": name, "arm": cfg["arm"], "label": cfg["label"],
        "register": cfg["register"], "artifact": cfg["artifact"],
        "universe_rank": n, "universe_supplied": len(rows), "eligible_tier": len(trimmed),
        "rank_key": cfg["rank_key"],
        "rank_key_is_market_cap_not_liquidity": cfg["rank_key_is_market_cap_not_liquidity"],
        "adopted": False, "default": False,
        "vintage_event": cfg["vintage_event"],
        "contract_min_positions_holds": cfg["contract_min_positions_holds"],
        "free_route": cfg["free_route"],
        "band_applied": bool(held) and cfg["exit_frac"] is not None,
    }
    return bk


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
        # WHERE THE PUBLISHED HEADLINE AND THE LIVE BOOK DIFFER.
        #
        # ITEM 18 -- THIS DISCLOSED THE SMALLEST OF THREE DIFFERENCES AND WAS SILENT ON THE TWO
        # LARGER ONES. `INDEX-BOOK` (r1, 2026-10-02, `ceffd04`) reported it against this lane
        # by name: the field named the no-trade BAND and not the UNIVERSE, so the payload a user
        # receives quoted all-cap EQUAL-WEIGHTED figures for a large-cap SCORE-WEIGHTED book.
        #
        # That study decomposed the gap one knob at a time, all four arms calling this same
        # `build_index`, and the band is the least of it:
        #     tier (all-cap -> $10B)      -5.9871 pp/yr
        #     weighting (equal -> score)  +0.6804 pp/yr
        #     no-trade band (0 -> 0.30)   -0.8009 pp/yr
        # So the one thing disclosed was worth about an eighth of the one that was not.
        #
        # NOTHING ABOUT THE BOOK CHANGES HERE. This is a disclosure field: no position, weight,
        # eligibility or ordering reads it, so `--config taxable` builds exactly what it built
        # before and the 2026-10-22 runbook is unaffected. A test asserts the positions and
        # weights are identical across this change.
        "headline_scope": _headline_scope(exit_frac, weighting, large_cap_min),
        "contract_conformance": conformance(len(positions), cap, len(large)),
        "n_scored": len(scored), "n_eligible": len(large), "n_positions": len(positions),
        "sector_data_available": sector_data,
        "sector_weights": sectors,
        "positions": positions,
    }


def _headline_scope(exit_frac, weighting: str = "score", large_cap_min=None) -> dict:
    """What the published figures describe, against what the live book is.

    THREE DIFFERENCES, NOT ONE -- AND `differs` KEEPS ITS ORIGINAL MEANING.
    `INDEX-BOOK` reported that this field named the no-trade BAND and was silent on the
    UNIVERSE and the WEIGHTING, so the payload quoted all-cap equal-weighted figures for a
    large-cap score-weighted book. Its one-knob decomposition, all four arms calling this same
    `build_index`, shows the band is the least of it:

        tier (all-cap -> $10B)      -5.9871 pp/yr
        weighting (equal -> score)  +0.6804 pp/yr
        no-trade band (0 -> 0.30)   -0.8009 pp/yr

    **THE NEW FACTS ARE ADDED, NOT FOLDED INTO `differs`.** My first cut made `differs` mean
    "differs at all", which is a redefinition in place -- the `provider` trap -- and
    `test_no_trade_band` caught it: that field is the BAND question, two of its tests read it
    as such, and an unbanded book must still report `differs: False`. So `differs` is unchanged
    and `universe_differs` / `weighting_differs` / `differs_on` are new.

    **`weighting` IS READ RATHER THAN ASSUMED.** The first cut hard-coded "score-weighted",
    which is wrong for any caller passing `weighting="equal"` -- including that suite's own
    fixtures. A disclosure that misdescribes the book it is disclosing about is worse than none.

    Nothing about the book changes here: no position, weight, eligibility or ordering reads
    this, so `--config taxable` builds exactly what it built before and the 2026-10-22 runbook
    is unaffected. `tests/test_index_book_measured.py` proves it on a 400-name cross-section.
    """
    banded = bool(exit_frac)
    score_weighted = str(weighting or "").lower().startswith("score")
    tiered = bool(large_cap_min)
    try:
        from ..screener import index_book_measured as _M
        served = {"roth_pct": _M.SERVED_ROTH_PCT,
                  "taxable_pct": _M.SERVED_TAXABLE_PCT,
                  "alpha_vs_own_tier_pp": _M.ALPHA_VS_OWN_TIER_PP,
                  "alpha_vs_all_cap_ew_pp": _M.ALPHA_VS_ALL_CAP_EW_PP,
                  "alpha_vs_spy_pp": _M.ALPHA_VS_SPY_PP,
                  "study": _M.STUDY, "study_commit": _M.STUDY_COMMIT}
    except Exception:                                        # noqa: BLE001
        served = None

    extra = []
    if tiered:
        extra.append("universe (all-cap vs a large-cap tier)")
    if score_weighted:
        extra.append("weighting (equal vs score)")

    note = ("the published backtest figures in `method` were measured WITHOUT a "
            "no-trade band. The live book applies one from vintage 4 (2026-08-13). "
            "S14's own evidence is a held-out DIFFERENCE (+1.78pp and +1.77pp net "
            "alpha in the two split directions), not a re-measured level, so the "
            "headline is deliberately not restated." if banded else
            "no band applied; the live book matches the construction the headline "
            "describes on the band.")
    if extra:
        note += (" AND THE BAND IS NOT THE LARGEST DIFFERENCE: the published figures are an "
                 "ALL-CAP, EQUAL-WEIGHTED decile, and this book differs on " +
                 " and ".join(extra) + ".")
        if served:
            note += (" INDEX-BOOK measured the live construction directly: "
                     "+%.4f%%/yr in a Roth, +%.4f%% after tax, +%.4fpp against an "
                     "equal-weighted basket of its own tier and %+.4fpp against the all-cap "
                     "equal-weighted universe. Quote those for the live book."
                     % (served["roth_pct"], served["taxable_pct"],
                        served["alpha_vs_own_tier_pp"], served["alpha_vs_all_cap_ew_pp"]))

    return {
        "headline_describes": "all-cap, EQUAL-WEIGHTED top-decile book, no no-trade band",
        "live_book_applies_band": banded,
        # UNCHANGED MEANING: the BAND question. Two tests read it as such.
        "differs": banded,
        # The two larger differences INDEX-BOOK found this field silent on.
        "universe_differs": tiered,
        "weighting_differs": score_weighted,
        "differs_on": (["no-trade band"] if banded else []) + extra,
        "one_knob_decomposition_pp_per_yr": {
            "tier_all_cap_to_10bn": -5.9871,
            "weighting_equal_to_score": 0.6804,
            "no_trade_band_0_to_030": -0.8009,
        },
        "served_book_measured": served,
        "note": note,
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


#: **HOW MANY SESSIONS THE MARKET MAY HAVE TRADED THAT THE MARKET-CAP CACHE CANNOT SEE
#: [item 81].**
#:
#: The 2026-10-22 rebalance was built against a `daily` cache ending **2026-07-29** -- sixty
#: sessions, three months, on the one number that decides which names clear the $10B tier --
#: and nothing anywhere said so. It was caught by hand on the night, worked around by hand on
#: the night, and the worked-around build still scored its caps from **2026-10-02**, fourteen
#: sessions behind the session it was labelled as. Both of those must refuse rather than pass.
#:
#: **FIVE SESSIONS is about a calendar week**, which is the room an operator needs: Sharadar's
#: own recommended pull is after the close, exports are taken a day or two before a build, and
#: a build delayed over a weekend must not be refused for being delayed over a weekend. It is
#: counted in TRADING days through `market_session`, the package's one calendar, so a build on
#: the Monday after Thanksgiving is not refused for the holiday.
#:
#: **IT CANNOT FIRE ON A HISTORICAL BUILD, which is why it needs no escape hatch.** A research
#: build as of 2009 reads a cache whose newest row is years LATER than its as-of, and a cache
#: that reaches past the as-of is not stale -- `_daily_at` walks back to the row on or before
#: the date either way. So the count is zero for every backtest and this constant is only ever
#: consulted by a build dated near today (`MA21`: a gate that cries wolf is one you switch off).
MAX_DAILY_CACHE_STALE_DAYS = 5


#: **HOW FAR BEHIND THE AS-OF THE FUNDAMENTALS MAY BE [item 84].**
#:
#: Item 81 gave the market-cap cache a staleness refusal and the fundamentals none, so the
#: 2026-10-22 book was built on filings through **2026-10-02** -- twenty days -- and nothing
#: said so. In the 10-23 export 230 companies had filed a quarter in between; 69 of them are
#: $10B+, and five were in the recorded book (GGG, JEF, MEDP, MU, SYF).
#:
#: **TEN TRADING DAYS, WHICH IS LOOSER THAN THE MARKET-CAP BAR OF FIVE, AND DELIBERATELY SO.**
#: A market cap exists for every name on every session, so a cache behind by a week is simply
#: stale. A FILING arrives when a company chooses: in the quiet fortnight between earnings
#: seasons the newest `datekey` in a perfectly current export genuinely sits a week or more
#: back, and a five-day bar would refuse a correct export (`MA21`). Ten covers that without
#: admitting the three-week gap this item exists to stop.
#:
#: IT CANNOT FIRE ON A HISTORICAL BUILD, for the same reason item 81's cannot: a research build
#: as of 2009 reads an export whose newest filing is years LATER, the count is zero, and the
#: bar is never consulted.
MAX_FUNDAMENTALS_STALE_DAYS = 10

#: The date column that defines each export table's reach. `datekey` for SF1 and `filingdate`
#: for SF2 because those are the dates the panel is allowed to KNOW something on, which is the
#: same choice `sharadar_freeze.DATE_COL` makes -- stated here rather than imported, because
#: this module must stay importable by a build that has no freeze on disk.
#:
#: **BOTH 13F SPELLINGS ARE TRIED, and that is not defensive dressing:** SF3/SF3A renamed the
#: quarter column `calendardate` -> `date` between the 2026-08 and 2026-10 exports, and a single
#: hard-coded name made an earlier manifest report NO DATE AT ALL for three tables. A reporter
#: that goes silent is worse than one that fails.
EXPORT_DATE_COLS = {"fundamentals.csv": ("datekey",),
                    "insiders.csv": ("filingdate", "transactiondate", "date"),
                    "institutional.csv": ("calendardate", "date")}


def _max_date_in_csv(path: str, cols) -> dict:
    """The newest value of the first of `cols` present -> {present, date, rows, column}.

    ONE STREAMING PASS over the one column that matters, which is the cheapest this can be:
    SF1 is ordered by ticker and then by date, so the newest filing is NOT at the tail and a
    cheap seek cannot find it. About three seconds on the 184MB fundamentals file and under a
    minute on the 691MB insiders one, against a build that takes a quarter of an hour.
    """
    if not os.path.exists(path):
        return {"present": False, "date": None, "rows": 0, "column": None}
    best, n, col = None, 0, None
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            r = _csv.reader(f)
            h = next(r, None)
            if not h:
                return {"present": True, "date": None, "rows": 0, "column": None,
                        "note": "empty or headerless"}
            for c in cols:
                if c in h:
                    col = c
                    break
            if col is None:
                return {"present": True, "date": None, "rows": 0, "column": None,
                        "note": "no date column; tried %s" % ", ".join(cols)}
            i = h.index(col)
            for row in r:
                n += 1
                if i < len(row) and row[i] and (best is None or row[i] > best):
                    best = row[i]
    except OSError as e:
        return {"present": True, "date": None, "rows": n, "column": col,
                "note": "unreadable: %s" % e}
    return {"present": True, "date": best, "rows": n, "column": col}


def export_vintages(data_dir: str) -> dict:
    """The newest date each export table actually reaches -> {name: {...}}.

    Reported on every full-universe build, because it is not recoverable from the payload
    afterwards -- and on 2026-10-22 it was the whole difference between the book the record
    describes and the book that was built. `data_as_of` says which session was ASKED for; this
    says what the inputs could actually see.
    """
    out = {}
    for name, cols in EXPORT_DATE_COLS.items():
        out[name] = _max_date_in_csv(os.path.join(data_dir, name), cols)
    return out


def refuse_stale_fundamentals(vintages: dict, as_of: str | None,
                              max_stale: int = MAX_FUNDAMENTALS_STALE_DAYS) -> str | None:
    """The refusal text, or None. See `MAX_FUNDAMENTALS_STALE_DAYS`.

    **ONLY `fundamentals.csv` GATES, and the other two are REPORTED.** That is a measurement
    rather than a preference: 13F is quarterly, so `institutional.csv` legitimately sits up to
    three months behind -- the 2026-10-23 export's SF3A reaches 2026-09-30 and is perfectly
    current -- and a bar that refused it would refuse every correct build outside the filing
    window. Insider filings are sporadic for the same reason. Gating on either would be a gate
    somebody switches off (`MA21`).
    """
    if not as_of:
        return None
    rec = (vintages or {}).get("fundamentals.csv") or {}
    if not rec.get("present"):
        return ("fundamentals.csv is not in the export directory, so no name can be scored "
                "point-in-time")
    newest = rec.get("date")
    if not newest:
        # ABSENT IS NOT CURRENT. A file whose date column could not be read tells us nothing
        # about how fresh it is, and reading that as "fresh enough" is the `C5` family.
        return ("fundamentals.csv carries no readable %s, so how far behind the requested "
                "as-of it sits cannot be established (%s)"
                % ("/".join(EXPORT_DATE_COLS["fundamentals.csv"]),
                   rec.get("note") or "no further detail"))
    try:
        a = _dt.date.fromisoformat(str(as_of)[:10])
        b = _dt.date.fromisoformat(str(newest)[:10])
    except ValueError:
        return None
    from ..screener.market_session import trading_days_between
    behind = trading_days_between(b, a, inclusive_start=False)
    if behind <= max_stale:
        return None
    return ("fundamentals.csv's newest filing is %s, which is %d trading days before the "
            "requested as-of of %s (the bar is %d). Every name would be scored on accounts "
            "that old, and a company that reported in between would be ranked on its previous "
            "quarter. Re-derive the export from a current pull -- `refresh_sharadar.bat` now "
            "rebuilds a derived table whose source is newer than it is -- and see "
            "REBALANCE_RUNBOOK_2027-01-25.md."
            % (newest, behind, str(as_of)[:10], max_stale))


def daily_cache_vintage(prov) -> dict:
    """The `daily` cache this provider will actually read: newest row, tickers, source.

    Reported on every full-universe build, because the market-cap vintage is not recoverable
    from the payload afterwards. The payload carries `data_as_of`, which is the date the
    operator ASKED for; which export the caps came from is a separate fact, and on 2026-10-22
    the two were three months apart.

    Reads through `prov._bulk`, so it reports the cache the scoring will use -- including any
    `--bulk-overlay`. Reading the directory instead would describe a file that may not be the
    one in play.
    """
    rows = prov._bulk("daily") or {}
    newest, n = None, 0
    for recs in rows.values():
        if recs:
            n += 1
            d = recs[-1][0]
            if newest is None or d > newest:
                newest = d
    ov = getattr(prov, "_bulk_overlay", None)
    return {"newest_row": newest, "tickers": len(rows), "tickers_with_rows": n,
            "source": (ov[0] if (ov and "daily" in ov[1]) else prov.bulk_dir)}


def refuse_stale_daily_cache(vintage: dict, as_of: str | None,
                             max_stale: int = MAX_DAILY_CACHE_STALE_DAYS) -> str | None:
    """The refusal text, or None. See `MAX_DAILY_CACHE_STALE_DAYS`.

    `as_of` of None means "the export's newest close", which is not known until the export is
    loaded -- so the caller checks twice: cheaply against the requested date before the
    fifteen-minute load, and again against the date the scoring resolved. One function, two
    call sites, so the two cannot answer differently (`B7`).
    """
    if not as_of:
        return None
    newest = (vintage or {}).get("newest_row")
    if not newest:
        # **AN ABSENT CACHE IS NOT A STALE ONE, AND REFUSING IT WAS MY OWN DEFECT.**
        #
        # The first cut of this function refused an empty `daily` cache too, on the reasoning
        # that every name would then be scored with no point-in-time market cap. That reasoning
        # is true and the refusal is still wrong: `_bulk` degrades a missing cache to `{}` BY
        # DESIGN, so "no bulk caches" is a configuration the build has always supported -- it
        # falls back to the fundamentals' own `marketcap`. `tests/test_item75.py` builds exactly
        # that way and went red, which is how this was found, and the refusal ALSO pre-empted
        # item 75's own as-of refusals: a more specific and more useful message was replaced by
        # a less specific one.
        #
        # Turning a tolerated absence into a hard stop is the mirror image of `C5` -- and it is
        # the shape `MA21` warns about, because a gate that stops legitimate builds is a gate
        # somebody switches off. It is also not the October defect: that cache had a newest row
        # of 2026-07-29 and is still refused below. An EMPTY cache cannot produce a silently
        # wrong market cap, only an absent one, which the payload's coverage already reports.
        return None
    try:
        a = _dt.date.fromisoformat(str(as_of)[:10])
        b = _dt.date.fromisoformat(str(newest)[:10])
    except ValueError:
        return None
    from ..screener.market_session import trading_days_between
    behind = trading_days_between(b, a, inclusive_start=False)
    if behind <= max_stale:
        return None
    return ("the daily market-cap cache at %s ends %s, which is %d trading days before the "
            "requested as-of of %s (the bar is %d). Market caps decide which names clear the "
            "large-cap floor, so this build would rank today's universe on %s's caps. Refresh "
            "the caches from a current export and point the build at them with "
            "--bulk-overlay DIR -- see REBALANCE_RUNBOOK_2027-01-25.md."
            % (vintage["source"], newest, behind, str(as_of)[:10], max_stale, newest))


def _full_universe_rows(data_dir: str, limit: int = None, as_of: str = None,
                        bulk_overlay: str = None, bulk_overlay_names=None):
    """Score the WHOLE Sharadar universe -> (rows, as_of, dropped).

    `as_of` builds the book as of a NAMED session instead of the export's newest close [item
    75]. It is honoured exactly or refused: a date the export does not cover, or one it has no
    close for, raises rather than sliding quietly to an earlier session, because the payload
    would then publish a `data_as_of` that the operator's runbook, their notes and the event
    they are about to append all disagree with -- and nothing in the record could say which was
    right.

    The live-scan store is whatever the last FMP scan happened to cover, which is a few
    hundred names at best — and a "top decile" of that collapses to the 10-name MIN_NAMES
    floor, i.e. ten mega-caps wearing a decile's label. Scoring the full point-in-time
    universe instead gives a real decile (86 of 861 eligible large caps at last run) and needs
    no live API, so a quarterly rebalance can run headless.

    `bulk_overlay` takes the market-cap and 13F caches from a DATED directory instead of the
    pinned `data/bulk/prepared` [item 81], and the market-cap vintage is printed either way.
    See `WRDSProvider.BULK_OVERLAY_DEFAULT` and `MAX_DAILY_CACHE_STALE_DAYS`.
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
    # ---- ITEM 81: WHICH CACHES, AND HOW OLD -------------------------------------------------
    #
    # THE OVERLAY IS SET BEFORE ANYTHING IS READ, and `bulk_overlay` refuses if it is not. A
    # build that read `daily` from October and `sf3` from July would publish a book neither
    # export describes.
    if bulk_overlay:
        man = prov.bulk_overlay(bulk_overlay, bulk_overlay_names)
        for n in sorted(man):
            e = man[n]
            print("[cache] %-14s %-7s %s (%s entries)"
                  % (n, "USED" if e["used"] else "not used", e["source"],
                     format(e["entries"], ",")), flush=True)
    # ---- ITEM 84: WHAT DATE EACH EXPORT TABLE ACTUALLY REACHES ------------------------------
    #
    # Item 81 gave the market-cap cache a vintage line and a refusal and left the FUNDAMENTALS
    # unchecked, so the 10-22 book was scored on filings through 2026-10-02 and the printout
    # said nothing. All three are reported; only fundamentals gates (see the refusal for why).
    vint = export_vintages(data_dir)
    for _n in ("fundamentals.csv", "insiders.csv", "institutional.csv"):
        _r = vint.get(_n) or {}
        print("[export] %-18s newest %-12s (%s rows, column %s)"
              % (_n, _r.get("date") or _r.get("note") or "ABSENT",
                 format(_r.get("rows") or 0, ","), _r.get("column")), flush=True)
    # **REPORTED HERE, REFUSED AFTER THE AS-OF IS VALIDATED, AND THE ORDER IS THE WHOLE
    # POINT.** My first cut refused here, and it PRE-EMPTED item 75's own refusals: on its
    # 2025 fixture the export ends 2025-03-17 and the as-of is 2025-04-25, where the right
    # complaint is "your as-of is beyond the data" and mine arrived first saying "the
    # fundamentals are stale". **That is item 83's mistake one item later** -- a new guard
    # standing in front of a more specific one and making it unreachable. A stale-fundamentals
    # refusal is only meaningful once the as-of is known to be a session the export covers.
    vintage = daily_cache_vintage(prov)
    print("[cache] market caps from %s, newest row %s (%s tickers)"
          % (vintage["source"], vintage["newest_row"], format(vintage["tickers"], ",")),
          flush=True)
    # CHEAPLY FIRST. The load is about a quarter of an hour and this is a command run once a
    # quarter under time pressure, so a stale cache must be refused in a second rather than
    # after the load (the same reason `--as-of` validates its format before the calendar).
    bad = refuse_stale_daily_cache(vintage, as_of)
    if bad:
        raise RuntimeError(bad)
    tickers = prov.universe(limit=limit) or list(U.bundled_tickers())
    res = score_universe_now(prov, tickers, as_of=as_of)
    # A NAMED REFUSAL REACHES THE OPERATOR INTACT. "scored no rows" is true of a bad as-of and
    # tells them nothing they can act on, and this is a command somebody runs once a quarter,
    # at speed, on an evening with one safe window in it.
    if isinstance(res, dict) and res.get("refused"):
        raise RuntimeError(res["refused"])
    if not res or not res.get("rows"):
        raise RuntimeError("scored no rows from the full universe")
    # AND AGAIN AGAINST THE DATE THE SCORING RESOLVED. With no `--as-of` the effective date is
    # the export's newest close, which is not knowable before the load -- so the cheap check
    # above cannot see it, and a July cache against a fresh export would otherwise pass.
    bad = refuse_stale_daily_cache(vintage, res.get("as_of"))
    if bad:
        raise RuntimeError(bad)
    # The fundamentals refusal, now that `as_of` has been resolved AND validated against the
    # export by `score_universe_now`. Nothing is written until `export()` returns, so
    # refusing here is just as protective as refusing before the load.
    bad = refuse_stale_fundamentals(vint, res.get("as_of"))
    if bad:
        raise RuntimeError(bad)
    # THE VINTAGES TRAVEL WITH THE ROWS, so `data_as_of` can name what each input reached
    # rather than only which session was asked for.
    _vintages = {"daily_cache": {"newest_row": vintage.get("newest_row"),
                                 "source": vintage.get("source"),
                                 "tickers": vintage.get("tickers")},
                 "export": {k: {"date": (v or {}).get("date"),
                                "rows": (v or {}).get("rows"),
                                "column": (v or {}).get("column")}
                            for k, v in vint.items()}}
    return (res["rows"], res.get("as_of"), (res.get("dropped_mc_divergence") or []),
            _vintages)


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
        # READ THROUGH TO THE ARTIFACT (MC11) rather than from the config literals.
        "measured": _measured_for(cfg_meta),
        "measured_width": cfg_meta.get("measured_width"),
        "measured_width_note": (
            # CORRECTED 2026-09-30 (MC11). This used to end "no run has measured this
            # configuration at the adopted width", which was true when written and is not now:
            # the artifact's book_configs.taxable carries annual_turnover 1.3747, the 0.30-band
            # figure, under the 30%-band label. The figures are now READ from there, so the
            # note reports the provenance instead of asserting an absence.
            "the `measured` figures come from BACKTEST_RESULTS.json book_configs, whose own "
            f"label names the band it was measured at; `measured_width` records {cfg_meta.get('measured_width')} "
            f"and the shipped width is {xf}"
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


def _export_candidate(*, store=None, path: str = DEFAULT_PATH, data_dir: str | None = None,
                      limit: int | None = None, candidate_name: str, carry_held: bool = False,
                      allow_free_route: bool = False, as_of: str | None = None,
                      bulk_overlay: str | None = None, bulk_overlay_names=None) -> dict:
    """Write a NAMED CANDIDATE book. Nothing here is adopted, default or published.

    THE FREE ROUTE IS REFUSED BY NAME AND THE REFUSAL IS A MEASUREMENT, NOT A PREFERENCE.
    `DECISION_index_choice.md` put the live-route decile's overlap with the Sharadar-built
    decile at **0.2326** against `D9`'s pre-committed **0.60** bar, on `D9`'s own shared
    population. A book built the free way would carry this candidate's label and be a
    three-quarters-different book. So a live-scan source raises unless a caller explicitly
    takes that on, and the explicit flag is not wired to the CLI -- there is no keystroke that
    produces a mislabelled book by accident.

    THE `--limit` DEFAULT IS RAISED FOR A CANDIDATE, and it has to be. `_full_universe_rows`
    defaults to 3000 rows, which is enough for a 1,500-name trim -- but a caller who passed
    `--limit 1000` to save time would get a REFUSAL rather than a quietly smaller universe,
    which is the direction that matters.
    """
    cfg = candidate(candidate_name)
    if not data_dir and not allow_free_route:
        raise RuntimeError(
            "candidate %r is NOT buildable by the free live route: its live-route decile "
            "overlaps the Sharadar-built decile by %.4f against a %.2f bar (%s). Pass "
            "--full-universe DATA_DIR to build it from the Sharadar export (Path B)."
            % (candidate_name, cfg["free_route"]["decile_overlap"], cfg["free_route"]["bar"],
               cfg["free_route"]["source"]))
    dropped, scan_date = [], None
    _vintages = None
    if data_dir:
        rows, scan_date, dropped, _vintages = _full_universe_rows(
            data_dir, limit=limit, as_of=as_of, bulk_overlay=bulk_overlay,
            bulk_overlay_names=bulk_overlay_names)
        source = ("Sharadar SF1+SEP export via WRDSProvider (point-in-time), "
                  "shipped settings.py weights")
        if as_of:
            source += " as of %s (requested)" % str(as_of)[:10]
    else:
        if as_of:
            raise RuntimeError("--as-of needs --full-universe: the saved live-scan snapshot "
                               "has no history to cut")
        if store is None:
            from ..screener.store import Store
            store = Store()
        scan_date = store.latest_scan_date()
        rows = store.load_snapshot(scan_date) if scan_date else []
        source = "latest saved live scan snapshot (FREE ROUTE -- NOT the measured construction)"
    # `held` is OFF by default for a candidate. The book on disk belongs to a different
    # construction over a different universe, so banding a new book against it would hold
    # names this universe may not contain. See `build_candidate`.
    held = _previous_book(path) if carry_held else None
    payload = build_candidate(rows, candidate_name, held=held)
    payload["profile_enrichment"] = _enrich_profiles(payload, store)
    payload["scan_date"] = scan_date
    payload["data_as_of"] = scan_date
    # **WHAT EACH INPUT ACTUALLY REACHES, BESIDE THE DATE THAT WAS ASKED FOR [item 84].**
    #
    # `data_as_of` is the session the operator REQUESTED, and on 2026-10-22 it read 2026-10-22
    # while the fundamentals behind it stopped at 2026-10-02 and the market caps at 2026-10-02.
    # Both were true statements about different things and the payload carried only the
    # flattering one. A reader of the JSON can now see the gap without re-deriving it.
    #
    # ABSENT ON THE LIVE-SCAN PATH, deliberately: that route reads no export, so an empty
    # block there would be a claim about files it never opened.
    if _vintages is not None:
        payload["data_as_of_inputs"] = _vintages
    payload["source"] = source
    payload["excluded_market_cap_divergence"] = [
        {"ticker": d["ticker"], "daily_mc": d["daily_mc"], "derived_mc": d["derived_mc"],
         "ratio": round(d["ratio"], 2)} for d in dropped]
    payload["generated_at"] = _dt.datetime.now().replace(microsecond=0).isoformat()
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    payload["path"] = path
    return payload


def export(store=None, path: str = DEFAULT_PATH, data_dir: str | None = None,
           limit: int | None = None, config: str | None = None,
           candidate_name: str | None = None, carry_held: bool = False,
           as_of: str | None = None, bulk_overlay: str | None = None,
           bulk_overlay_names=None, **kw) -> dict:
    """Build the book and write the JSON. Returns the payload.

    `data_dir` -> score the full Sharadar universe point-in-time (the headless path, and the
    one that produces a genuine top decile). Otherwise fall back to the latest saved live scan.
    """
    # A named book config (settings.BOOK_CONFIGS) fixes width, cadence and band together, so
    # the emitted book cannot drift from the construction that was actually validated.
    # A NAMED CANDIDATE IS A DIFFERENT NAMESPACE AND IS HANDLED FIRST, because the two cannot
    # be combined: a candidate fixes the same knobs a book config does, so honouring both would
    # silently pick a winner. Refused rather than ordered.
    if candidate_name:
        if config:
            raise RuntimeError("--candidate and --config set the same knobs; pass one. "
                               "A candidate already fixes the decile, weighting, cap and band.")
        return _export_candidate(store=store, path=path, data_dir=data_dir, limit=limit,
                                 candidate_name=candidate_name, carry_held=carry_held,
                                 as_of=as_of, bulk_overlay=bulk_overlay,
                                 bulk_overlay_names=bulk_overlay_names, **kw)
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
    _vintages = None
    if data_dir:
        rows, scan_date, dropped, _vintages = _full_universe_rows(
            data_dir, limit=limit, as_of=as_of, bulk_overlay=bulk_overlay,
            bulk_overlay_names=bulk_overlay_names)
        source = ("Sharadar SF1+SEP export via WRDSProvider (point-in-time), "
                  "shipped settings.py weights")
        if as_of:
            source += " as of %s (requested)" % str(as_of)[:10]
    elif as_of:
        # THE LIVE-SCAN PATH CANNOT HONOUR AN AS-OF AND SAYS SO. The store holds whatever the
        # last scan happened to cover and carries no history to cut, so accepting the argument
        # and ignoring it would publish a `data_as_of` that is simply the last scan's date
        # wearing the name the operator chose -- the exact failure this item exists to close.
        raise RuntimeError("--as-of needs --full-universe: the saved live-scan snapshot has no "
                           "history to cut, so a named session cannot be built from it")
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
    # **WHAT EACH INPUT ACTUALLY REACHES, BESIDE THE DATE THAT WAS ASKED FOR [item 84].**
    #
    # `data_as_of` is the session the operator REQUESTED, and on 2026-10-22 it read 2026-10-22
    # while the fundamentals behind it stopped at 2026-10-02 and the market caps at 2026-10-02.
    # Both were true statements about different things and the payload carried only the
    # flattering one. A reader of the JSON can now see the gap without re-deriving it.
    #
    # ABSENT ON THE LIVE-SCAN PATH, deliberately: that route reads no export, so an empty
    # block there would be a claim about files it never opened.
    if _vintages is not None:
        payload["data_as_of_inputs"] = _vintages
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


def _band_width_pct() -> float:
    """The adopted no-trade band, as a percentage, from the one place it is defined."""
    from .no_trade_band import BAND_WIDTH
    return float(BAND_WIDTH) * 100.0


def main(argv=None):
    import argparse
    _BAND_WIDTH_PCT = _band_width_pct()
    ap = argparse.ArgumentParser(description="Export the Valquo Index (top-decile large caps).")
    ap.add_argument("--out", default=DEFAULT_PATH)
    # DEFAULT None SO AN EXPLICIT KNOB IS DISTINGUISHABLE FROM AN ABSENT ONE. Resolved to the
    # module defaults below, so every existing invocation is bit-identical -- the only thing
    # this buys is that `--candidate` can REFUSE a hand-passed knob by name instead of handing
    # the operator a TypeError about an argument they never typed.
    ap.add_argument("--large-cap-min", type=float, default=None)
    ap.add_argument("--top-decile", type=float, default=None)
    ap.add_argument("--weighting", choices=("score", "equal"), default=None)
    ap.add_argument("--full-universe", nargs="?", const="data/backtest", default=None,
                    metavar="DATA_DIR",
                    help="score the whole Sharadar universe point-in-time instead of the last "
                         "live scan (headless; the only path that yields a real top decile). "
                         "Optionally takes the export dir, default data/backtest.")
    # **THE DEFAULT IS THE WHOLE EXPORT, AND IT USED TO BE A SILENT SUBSET [item 81].**
    #
    # This defaulted to 3000, which was the whole export while the export held 2,827 names and
    # became a market-cap-ranked SUBSET when it grew past 3,000. `WRDSProvider.universe` prints
    # "SMOKE-TEST SUBSET, not a verdict" when that happens -- the function saying its own output
    # may not carry a verdict -- and `CLAUDE.md`'s METHODOLOGY RULE says the same.
    #
    # IT IS NOT A FILTER ON THE EDGES OF THE BOOK. The composite is a cross-sectional z-score,
    # so scoring 1,839 names instead of 2,038 re-standardises every column and moves the decile
    # boundary: item 75 measured NINE of ~85 names changing, and only one of the six that
    # appeared under the full export sat outside the top 3,000 at all.
    #
    # The 2026-10-22 runbook carried `--limit 4000` for exactly this reason, in bold, with the
    # measurement -- and the one-off script that actually built the recorded book did not pass
    # it, so the book in force was scored on 1,835 names rather than the export's 2,038. A
    # default that has to be remembered on the night is the workaround this item removes.
    #
    # `None` means the whole export and no ranking (`universe`'s own branch). An operator who
    # wants the old behaviour types `--limit 3000` and gets the subset banner with it.
    ap.add_argument("--limit", type=int, default=None,
                    help="universe size for --full-universe. Default: the WHOLE export, "
                         "unranked. A value below the export's size takes a market-cap-ranked "
                         "subset and labels itself a smoke test.")
    # **THE BAND WIDTH IS DERIVED, NOT TYPED [item 75].** This help text read "20%% band" long
    # after Don adopted S14 at 0.30 on 2026-08-13, so an operator reading `--help` to check
    # what they were about to build was told the wrong construction. Retyping it as 30 fixes
    # today and is the identical defect at the next width change (`MA5`).
    ap.add_argument("--config", default=None,
                    help="named book config: 'roth' (top-25, 6-week, no band) or 'taxable' "
                         "(decile, quarterly, %d%%%% band). Sets width and emits the cadence."
                         % round(_BAND_WIDTH_PCT))
    # ---- ITEM 75: BUILD AS OF A NAMED SESSION ------------------------------------------------
    #
    # The 2026-10-22 rebalance is built on the EVENING OF 10-23, in the one safe window there
    # is: after the 10-22 track row exists and before track-row writes the 10-23 row at ~03:07
    # UTC on 10-24. Sharadar's own recommended pull is ~5:20pm ET, so by then the export very
    # likely carries the 10-23 close -- and the book would be scored as of 10-23 while being
    # appended as the event for 10-22. That is a one-day look-ahead, and the event carries only
    # a date and positions, so nothing downstream could ever tell.
    #
    # Honoured exactly or refused. See `_full_universe_rows`.
    ap.add_argument("--as-of", dest="as_of", default=None, metavar="YYYY-MM-DD",
                    help="score the export as of this session instead of its newest close. "
                         "Needs --full-universe. Refused if the export has no close on that "
                         "date, or if the date is later than its newest close.")
    ap.add_argument("--candidate", default=None, choices=sorted(INDEX_CANDIDATES),
                    help="a NAMED, NON-DEFAULT candidate construction (INDEX_CANDIDATES). "
                         "Nothing here is adopted or published; requires --full-universe.")
    # ---- ITEM 81: WHICH EXPORT THE MARKET CAPS COME FROM --------------------------------------
    #
    # The 2026-10-22 rebalance needed a hand-written monkeypatch to get a current market cap
    # into the build, because `refresh_sharadar.bat` refreshes `data/backtest` and nothing ever
    # refreshed the `data/bulk/prepared` caches the build also reads -- and those caches must
    # NOT be rebuilt in place, because every banked research figure on this project pins them.
    # So the fresh caches live in the dated freeze directory `sharadar_freeze` already writes,
    # and the build is told to read them from there.
    #
    # THE DEFAULT SET IS DERIVED, NOT TYPED (`MA5`): the help text for `--config` read "20%
    # band" for weeks after Don adopted 0.30, which is the same defect one line up.
    from .data_providers import WRDSProvider as _WP
    _OVERLAY_DEFAULT = ",".join(_WP.BULK_OVERLAY_DEFAULT)
    ap.add_argument("--bulk-overlay", default=None, metavar="DIR",
                    help="take the market-cap and 13F caches from DIR (a dated "
                         "data/backtest_freeze_*/bulk/prepared) instead of the pinned "
                         "data/bulk/prepared, which banked research figures rest on. Needs "
                         "--full-universe.")
    ap.add_argument("--bulk-overlay-names", default=None, metavar="a,b",
                    help="which caches to take from --bulk-overlay (default: %s). Named "
                         "deliberately: two of the five caches a freeze carries hold FEWER "
                         "names than the pinned ones, so overlaying them would narrow the "
                         "universe. See WRDSProvider.BULK_OVERLAY_DEFAULT." % _OVERLAY_DEFAULT)
    ap.add_argument("--carry-held", action="store_true",
                    help="apply the no-trade band against the book already on disk. OFF by "
                         "default for a candidate: the book on disk is a DIFFERENT "
                         "construction, so the first build is band-less by design.")
    a = ap.parse_args(argv)
    if a.as_of:
        # **FORMAT FIRST, CALENDAR LATER.** Whether the date is a trading day needs the union
        # calendar, which needs the whole export loaded -- about a quarter of an hour. Whether
        # it is a date at all costs nothing, and this is a command run once a quarter under
        # time pressure, so a typo must fail in a second rather than after the load.
        try:
            _dt.date.fromisoformat(str(a.as_of)[:10])
        except ValueError:
            print("--as-of %r is not a date; use YYYY-MM-DD." % a.as_of)
            return 1
        if not a.full_universe:
            print("--as-of needs --full-universe: the saved live-scan snapshot has no history "
                  "to cut, so a named session cannot be built from it.")
            return 1
    if a.bulk_overlay and not a.full_universe:
        # The live-scan path reads no bulk cache at all, so accepting the flag there would
        # take a dated directory and ignore it -- and the operator would believe the book
        # carried fresh market caps. Same refusal, same reason, as `--as-of`.
        print("--bulk-overlay needs --full-universe: the saved live-scan snapshot does not "
              "read the bulk caches, so pointing them elsewhere would change nothing.")
        return 1
    if a.bulk_overlay_names and not a.bulk_overlay:
        print("--bulk-overlay-names needs --bulk-overlay.")
        return 1
    _ov_names = ([x.strip() for x in a.bulk_overlay_names.split(",") if x.strip()]
                 if a.bulk_overlay_names else None)
    if a.config and a.config in INDEX_CANDIDATES:
        print("%r is a candidate construction, not a book config -- pass --candidate %s."
              % (a.config, a.config))
        return 1
    _knobs = {"--large-cap-min": a.large_cap_min, "--top-decile": a.top_decile,
              "--weighting": a.weighting}
    _given = sorted(k for k, v in _knobs.items() if v is not None)
    if a.candidate and _given:
        print("--candidate %s already fixes %s; pass one or the other, not both."
              % (a.candidate, ", ".join(_given)))
        return 1
    _kw = {} if a.candidate else {
        "large_cap_min": LARGE_CAP_MIN if a.large_cap_min is None else a.large_cap_min,
        "top_decile": TOP_DECILE if a.top_decile is None else a.top_decile,
        "weighting": "score" if a.weighting is None else a.weighting,
    }
    try:
        p = export(path=a.out, data_dir=a.full_universe, limit=a.limit,
                   config=a.config, candidate_name=a.candidate, carry_held=a.carry_held,
                   as_of=a.as_of, bulk_overlay=a.bulk_overlay,
                   bulk_overlay_names=_ov_names, **_kw)
    except RuntimeError as e:
        print(f"Could not build the book: {e}")
        return 1
    if not p["positions"]:
        print("No positions — no scan snapshot yet (run a scan first), or try --full-universe.")
        return 1
    print(f"Valquo Index -> {p['path']}   as of {p.get('data_as_of')}   "
          f"{p['n_positions']} of {p['n_eligible']} eligible ({p['n_scored']} scored)")
    print(f"  source: {p.get('source')}")
    if p.get("candidate"):
        _k = p["candidate"]
        print("  CANDIDATE: %s -- %s" % (_k["name"], _k["label"]))
        print("  NOT ADOPTED, NOT DEFAULT, NOT PUBLISHED. register: %s" % _k["register"])
        print("  universe %d of %d supplied; eligible tier %d; band %s"
              % (_k["universe_rank"], _k["universe_supplied"], _k["eligible_tier"],
                 "applied" if _k["band_applied"] else "NOT applied (first build is band-less)"))
        print("  adopting this is a VINTAGE EVENT; contract position floor holds: %s"
              % _k["contract_min_positions_holds"])
        # THE NAME SAYS "LIQUID" AND THE RANK IS MARKET CAP. Printed rather than left in the
        # payload, because an operator who only reads the console is exactly the person who
        # would otherwise carry the label into a note about the book.
        _mc = _k["rank_key_is_market_cap_not_liquidity"]
        print("  ranked by %s -- NOT a liquidity screen (no point-in-time liquidity measure "
              "exists; Spearman vs 63d dollar ADV %.4f, %s)"
              % (_k["rank_key"], _mc["spearman_vs_63d_dollar_adv"], _mc["source"]))
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
