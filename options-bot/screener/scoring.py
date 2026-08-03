"""
Scoring engine — the brain.

Two buckets, scored on different logic:
  ESTABLISHED (profitable): sector-relative value + quality + momentum + insider
  SPECULATIVE (unprofitable): EV/Sales-vs-peers value + revenue growth + momentum + insider

Profitability HELPS in Established and is IRRELEVANT in Speculative, so an
unprofitable gem is never crowded out by mature profitable names.

-----------------------------------------------------------------------------
 CHANGE (Jul 2026): the Established value score is no longer a DCF gap.
-----------------------------------------------------------------------------
The old `value_score_established(dcf_upside)` was the single largest weight in the
model (35%) and NOTHING in the pipeline ever computed `dcf_upside` — every
established name got the neutral 50.0, every day. A 35% weight that is a constant
is not a factor, it is a rounding error with extra steps.

A DCF also needs a discount rate, a terminal growth rate and a multi-year cash-flow
forecast per name. For ~13k names, refreshed daily, from free data, those inputs
would be guesses, and a guess run through a compounding model produces a very
confident-looking number with no information in it.

Value is now what we can actually observe: SECTOR-RELATIVE CHEAPNESS on two
independent yields — earnings yield (net income / market cap) and EBIT yield
(operating income / enterprise value, i.e. the inverse of EV/EBIT). Both are
computed cross-sectionally, so "cheap" means cheap versus this sector today rather
than versus a hard-coded multiple that is wrong for half the market.

Three deliberate details:

* YIELDS, NOT MULTIPLES. P/E and EV/EBIT go NEGATIVE when earnings are negative,
  and a naive "low multiple = cheap" rank puts the biggest loss-maker at the top of
  the value screen. Inverted (yield form), a loss ranks below every profitable name,
  which is the honest ordering. Same trick for EV/Sales in the Speculative bucket.
* NEGATIVE ENTERPRISE VALUE IS UNDEFINED, NOT CHEAP. A company holding more net
  cash than its market cap produces a negative EV; dividing by it flips the sign of
  the yield and would rank a cash-burning shell as the cheapest name on the board.
  Those names are excluded from the EV-based percentile and the remaining weight is
  renormalized — see the missing-data convention below.
* WHY EV/EBIT AND NOT EV/EBITDA. `edgar.get_fundamentals` falls back to EBIT when
  D&A is not tagged, so an "EBITDA" cross-section would silently be part EBITDA and
  part EBIT — the same mixing-two-different-things error that made the
  quarterly/annual bug in pit_data so damaging. EBIT is defined identically for
  every filer. It also maps 1:1 onto Sharadar SF1's `ebit`/`ev` when that lands.

-----------------------------------------------------------------------------
 Missing-data convention (ONE convention, applied everywhere)
-----------------------------------------------------------------------------
Every sub-score returns None when it has NO information, and `score_stock`
renormalizes the bucket weights over whatever IS available (the same rule
`cross_sectional.composite_score` uses on the backtest panel). Consequences:

  * missing data is NEUTRAL, never a zero. The old `quality_score` did
    `(op_margin or 0)`, which mapped "we couldn't parse the margin" to "the margin
    is zero" and actively punished names for our parser's gaps.
  * a partial input renormalizes INSIDE a sub-score too: `growth_score` with no
    prior year scores on level alone, instead of the old accel=0.0 which silently
    capped every short-history name at 70 — precisely the newly-public names the
    Speculative bucket exists to find.
  * a name scored on a sliver of the model is not comparable to a fully-scored one,
    so `MIN_FACTOR_COVERAGE` of the nominal weight must be present or the name is
    not ranked at all.

An EMPTY insider list is not missing data — it means "no qualifying Form 4 activity",
which is a real, neutral observation. `insider_score(None)` means "not fetched" and
is the value that renormalizes away.
"""

import logging
from dataclasses import dataclass, field

import numpy as np

import config as C

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Gates (run before scoring) — liquidity, price, ticker hygiene
# ---------------------------------------------------------------------------

def is_junk_ticker(ticker):
    """
    True for warrants / units / rights / preferred series — things that carry a
    ticker but are not the common equity we mean to screen.

    Two conventions:
      * NYSE/AMEX use a separator: ABC.W, ABC-WS, ABC.U
      * Nasdaq appends a 5th letter to a 4-letter root: ABCDW (warrant), ABCDU
        (unit), ABCDR (right). On Nasdaq the 5th character of a 5-letter ticker IS
        a suffix code, so matching the whole class is safe — and it sweeps up
        5-letter preferred series, which are also not common equity.
    Only the separator form was checked before, so every bare Nasdaq SPAC warrant
    walked straight through the gate.
    """
    tkr = (ticker or "").upper()
    if not tkr:
        return False
    if any(tkr.endswith("." + s) or tkr.endswith("-" + s) for s in C.JUNK_SUFFIXES):
        return True
    if len(tkr) == 5 and tkr.isalpha() and tkr[-1] in C.JUNK_FIFTH_LETTERS:
        return True
    return False


def passes_gates(d):
    """True if the name is tradeable common equity worth scoring."""
    if not d.get("is_common_equity", True):
        return False, "not common equity"
    if is_junk_ticker(d.get("ticker")):
        return False, "warrant/unit/right"
    if (d.get("price") or 0) < C.PRICE_FLOOR:
        return False, f"price < ${C.PRICE_FLOOR}"
    if (d.get("avg_dollar_volume") or 0) < C.MIN_AVG_DOLLAR_VOLUME:
        return False, "below liquidity floor"
    return True, "ok"


def classify_bucket(d):
    """
    Profitable -> established; unprofitable -> speculative; UNKNOWN -> None.

    The old version mapped `operating_income is None` to "speculative", which turns
    a parser gap into a strategy decision: a profitable name whose OperatingIncomeLoss
    tag we failed to read got scored against loss-making growth names on a completely
    different factor set. Net income is a reasonable second read (a filer that omits
    operating income almost always reports net income); if BOTH are missing we do not
    know what this company is and the name is skipped instead of guessed at.
    """
    op_inc = d.get("operating_income")
    if op_inc is not None:
        return "established" if op_inc > 0 else "speculative"
    ni = d.get("net_income")
    if ni is not None:
        return "established" if ni > 0 else "speculative"
    return None


# ---------------------------------------------------------------------------
#  Cross-sectional value inputs
#
#  Value is inherently relative, so it cannot be computed from one name's dict.
#  This runs once per cross-section (one day's universe, or one rebalance date in
#  the backtest) and writes the percentile fields score_stock() reads.
# ---------------------------------------------------------------------------

def _enterprise_value(d):
    """market cap + total debt - cash. None if we can't form it."""
    mc = d.get("market_cap")
    if not mc or mc <= 0:
        return None
    return mc + (d.get("total_debt") or 0) - (d.get("cash") or 0)


def _assign_percentiles(rows, metric_key, out_key):
    """
    Write `out_key` = fraction of peers that are MORE EXPENSIVE on `metric_key`,
    where metric_key is a YIELD (higher = cheaper). 1.0 = cheapest of the pool.

    Peer set = the name's sector when the sector has >= MIN_SECTOR_PEERS priceable
    names, else the whole cohort (a thin sector produces a noisy rank). If the whole
    COHORT is thinner than MIN_SECTOR_PEERS the percentile is left None: a "rank"
    among three names carries no information, and handing back 0.0 or 1.0 anyway is
    how you manufacture a value signal out of nothing.
    """
    for d in rows:
        d.setdefault(out_key, None)
    have = [d for d in rows
            if d.get(metric_key) is not None and np.isfinite(d[metric_key])]
    if len(have) < C.MIN_SECTOR_PEERS:
        log.debug("%s: cohort of %d too thin for a percentile; left neutral",
                  out_key, len(have))
        return
    by_sector = {}
    for d in have:
        by_sector.setdefault(d.get("sector") or "?", []).append(d)
    all_vals = [d[metric_key] for d in have]
    for d in have:
        peers = by_sector[d.get("sector") or "?"]
        pool = ([p[metric_key] for p in peers]
                if len(peers) >= C.MIN_SECTOR_PEERS else all_vals)
        mine = d[metric_key]
        d[out_key] = sum(1 for v in pool if v < mine) / len(pool)


def compute_value_percentiles(rows):
    """
    Compute every cross-sectional value input for one cross-section, in place.

    Writes onto each dict:
      earnings_yield          net income / market cap
      ebit_ev_yield           operating income / enterprise value   (EV/EBIT inverted)
      sales_ev_yield          revenue / enterprise value            (EV/Sales inverted)
      earnings_yield_percentile / ebit_ev_percentile / ev_sales_percentile

    All three metrics are yields so that losses and negative EV rank at the bottom
    rather than at the top (see the module docstring). Names with a non-positive
    enterprise value are dropped from the two EV-based metrics — their yield has no
    meaningful ordering — and the value weight renormalizes onto whatever is left.
    """
    neg_ev = 0
    for d in rows:
        mc = d.get("market_cap")
        ni = d.get("net_income")
        d["earnings_yield"] = (ni / mc) if (ni is not None and mc and mc > 0) else None

        ev = _enterprise_value(d)
        if ev is not None and ev <= 0:
            neg_ev += 1
            ev = None
        op = d.get("operating_income")
        rev = d.get("revenue")
        d["ebit_ev_yield"] = (op / ev) if (op is not None and ev) else None
        d["sales_ev_yield"] = (rev / ev) if (rev is not None and rev > 0 and ev) else None

    if neg_ev:
        log.info("value percentiles: %d/%d names have non-positive enterprise value "
                 "(net cash > market cap); excluded from EV-based percentiles", neg_ev, len(rows))

    _assign_percentiles(rows, "earnings_yield", "earnings_yield_percentile")
    _assign_percentiles(rows, "ebit_ev_yield", "ebit_ev_percentile")
    _assign_percentiles(rows, "sales_ev_yield", "ev_sales_percentile")
    return rows


# ---------------------------------------------------------------------------
#  Sub-scores (each returns 0-100, or None when it has no information)
# ---------------------------------------------------------------------------

def _clip01(x):
    return float(np.clip(x, 0.0, 1.0))


def _weighted(parts):
    """
    parts: [(value_0_to_1_or_None, weight), ...]. Returns the weighted mean over the
    parts that are present, renormalized — or None if nothing is present. This is the
    missing-data convention, applied identically inside every sub-score.
    """
    present = [(v, w) for v, w in parts if v is not None]
    if not present:
        return None
    return sum(v * w for v, w in present) / sum(w for _, w in present)


def value_score_established(earnings_yield_percentile, ebit_ev_percentile):
    """
    Sector-relative cheapness for a profitable name: the blend of its earnings-yield
    and EBIT-yield percentiles. 1.0 (cheapest in the peer set) -> 100.

    Two yields rather than one because they disagree in informative ways: earnings
    yield is levered (it flatters a debt-heavy name whose interest is tax-shielded),
    EBIT/EV is not (it prices the whole capital structure). A name that is cheap on
    both is cheap; a name cheap on only one usually has a balance-sheet story.
    """
    w = C.VALUE_ESTABLISHED_WEIGHTS
    v = _weighted([
        (None if earnings_yield_percentile is None else _clip01(earnings_yield_percentile),
         w["earnings_yield"]),
        (None if ebit_ev_percentile is None else _clip01(ebit_ev_percentile),
         w["ebit_ev"]),
    ])
    return None if v is None else 100.0 * v


def value_score_speculative(ev_sales_percentile):
    """Cheapness vs peers on EV/Sales. percentile = fraction of peers MORE expensive.
    1.0 (cheapest in peer set) -> 100 ; 0.0 (most expensive) -> 0."""
    if ev_sales_percentile is None:
        return None
    return 100.0 * _clip01(ev_sales_percentile)


def growth_score(latest_rev_growth, prior_rev_growth):
    """Revenue growth + acceleration (speculative bucket).
    Rewards high growth, with a bonus for accelerating vs decelerating.

    With no prior year we score on LEVEL ALONE (renormalized), not on level plus a
    zero for acceleration. The old accel=0.0 capped every short-history name at 70,
    which is a 30-point penalty for being newly public — applied to exactly the
    newly-public names this bucket exists to surface."""
    if latest_rev_growth is None:
        return None
    level = _clip01(latest_rev_growth / 0.50)             # 50% YoY -> full level credit
    accel = None
    if prior_rev_growth is not None:
        accel = _clip01(0.5 + (latest_rev_growth - prior_rev_growth) / 0.40)  # +/-40% swing
    return float(100 * _weighted([(level, 0.7), (accel, 0.3)]))


def quality_score(op_margin, roe, net_debt_to_ebitda):
    """Profitability + returns + balance-sheet strength (established bucket).

    Each input is optional and the weights renormalize over what's present. Note
    what `net_debt_to_ebitda=None` now means: `edgar.get_fundamentals` used to emit
    0.0 when EBITDA was negative or missing, and 0.0 reads as "zero net debt", which
    earned a loss-making company FULL balance-sheet credit. None means "leverage is
    not measurable", and leverage simply drops out of this name's quality score."""
    m = None if op_margin is None else _clip01(op_margin / 0.25)
    r = None if roe is None else _clip01(roe / 0.20)
    lev = None if net_debt_to_ebitda is None else _clip01(1 - net_debt_to_ebitda / 4.0)
    v = _weighted([(m, 0.40), (r, 0.35), (lev, 0.25)])
    return None if v is None else float(100 * v)


def momentum_score(ret_12_1):
    """Trailing 12-minus-1-month return. +30% -> 100, flat -> 50, -30% -> 0."""
    if ret_12_1 is None:
        return None
    return float(np.clip(50 + 50 * (ret_12_1 / 0.30), 0, 100))


def _buyer_key(t, i):
    """
    Stable identity for the "how many DIFFERENT insiders are buying" count.

    `t.get("person", id(t))` was broken twice over: dict.get only returns the default
    when the KEY IS ABSENT, and edgar._parse_form4_xml always sets "person" — to None
    when the owner name doesn't parse. So every unnamed filer collapsed onto the
    single key None and a genuine four-person cluster registered as one buyer. id(t)
    is also not stable across runs. edgar now falls back to the owner CIK and then to
    the filing accession so transactions from one filing keep one identity; this is
    the last-resort guard for hand-built dicts.
    """
    return t.get("person") or t.get("owner_cik") or f"__anon_{i}"


def insider_score(transactions):
    """
    Quality-weighted insider signal, 0-100 (50 = neutral / no activity).
    transactions: list of {code, role, value_usd, date, person}.
      None  -> not fetched (missing data; renormalized away by the composite)
      []    -> fetched, nothing qualifying (a real observation: neutral 50)

    Weights open-market BUYS (code P) heavily, penalizes SALES (code S), scales by
    role (CEO/CFO > director) and rewards clustering (multiple distinct buyers).

    RANGE: the old squash was 50 + 25*tanh(raw/2), which could never leave [25, 75].
    The np.clip(...,0,100) around it was a no-op, and a component nominally worth
    20-30% of the composite delivered about HALF the cross-sectional dispersion of
    value/quality/momentum/growth, which all span 0-100. It also saturated almost
    immediately: one $250k CEO buy scored 67.6 and ten $10M CEO buys scored 75.0, so
    the size and clustering machinery stopped discriminating exactly where conviction
    was highest. The scale below is logarithmic in raw pressure and spans the full
    0-100, so nominal weight and effective weight finally agree.
    """
    if transactions is None:
        return None
    if not transactions:
        return 50.0
    pressure = 0.0
    buyers = set()
    for i, t in enumerate(transactions):
        code = t.get("code") or ""
        code_w = C.INSIDER_CODE_WEIGHTS.get(code, 0.0)
        if code_w == 0.0:
            continue
        role_w = C.INSIDER_ROLE_WEIGHTS.get(t.get("role", "Dir"), 1.0)
        pressure += code_w * role_w * _size_weight(t.get("value_usd"))
        # Only genuine open-market purchases count toward the cluster. An option
        # exercise is a calendar event; giving it the same clustering credit as a
        # purchase erases the distinction the code weights exist to draw.
        if code in C.INSIDER_CLUSTER_CODES:
            buyers.add(_buyer_key(t, i))
    pressure += min(len(buyers), C.INSIDER_CLUSTER_MAX_BUYERS) * C.INSIDER_CLUSTER_BONUS
    return float(np.clip(50 + 50 * _squash(pressure), 0, 100))


def _size_weight(value_usd):
    """
    Dollar size -> conviction weight, on a per-decade scale.

    The old log1p(size)/log1p(250_000) is nearly flat across the range that actually
    occurs: a $1,000 buy earned 0.556 of the credit a $250,000 buy earned. Here every
    10x adds INSIDER_SIZE_DECADE_W from a $1k floor, so $1k->0.0, $10k->0.5,
    $100k->1.0, $250k->1.2, $1M->1.5, $10M->2.0 — real separation where the real
    variation is, capped so a single enormous ticket can't own the score.
    """
    try:
        size = float(value_usd or 0)
    except (TypeError, ValueError):
        size = 0.0
    if size <= 0:
        return C.INSIDER_SIZE_UNKNOWN_W          # unparseable size -> small, not large
    size = max(size, C.INSIDER_SIZE_FLOOR_USD)
    w = C.INSIDER_SIZE_DECADE_W * np.log10(size / C.INSIDER_SIZE_FLOOR_USD)
    return float(np.clip(w, 0.0, C.INSIDER_SIZE_MAX_W))


def _squash(raw):
    """
    Signed log compression of raw insider pressure into [-1, 1], pinning at
    +/- INSIDER_SATURATION_RAW. Logarithmic (not tanh) so it keeps separating
    conviction well past the point tanh flattens out:
      raw  0.35 (one tiny director buy)     -> ~54
      raw  2.3  (one $250k CEO buy)         -> ~66
      raw 10    (a handful of large buys)   -> ~82
      raw 31    (ten $10M CEO buys)         -> ~97
    """
    scale = np.log1p(C.INSIDER_SATURATION_RAW)
    s = np.sign(raw) * np.log1p(abs(raw)) / scale
    return float(np.clip(s, -1.0, 1.0))


# ---------------------------------------------------------------------------
#  Composite
# ---------------------------------------------------------------------------

@dataclass
class Score:
    ticker: str
    bucket: str
    composite: float
    components: dict = field(default_factory=dict)
    coverage: float = 1.0      # share of the bucket's nominal weight that was computable


def score_stock_verbose(d):
    """Score one stock. Returns (Score|None, reason). `reason` explains every skip."""
    ok, why = passes_gates(d)
    if not ok:
        return None, why
    bucket = classify_bucket(d)
    if bucket is None:
        return None, "profitability unknown (no operating or net income)"

    ins = insider_score(d.get("insider_transactions"))
    mom = momentum_score(d.get("ret_12_1"))

    if bucket == "established":
        raw = {
            "value": value_score_established(d.get("earnings_yield_percentile"),
                                             d.get("ebit_ev_percentile")),
            "quality": quality_score(d.get("op_margin"), d.get("roe"),
                                     d.get("net_debt_to_ebitda")),
            "momentum": mom,
            "insider": ins,
        }
        w = C.WEIGHTS_ESTABLISHED
    else:
        raw = {
            "value": value_score_speculative(d.get("ev_sales_percentile")),
            "growth": growth_score(d.get("latest_rev_growth"), d.get("prior_rev_growth")),
            "momentum": mom,
            "insider": ins,
        }
        w = C.WEIGHTS_SPECULATIVE

    comp = {k: v for k, v in raw.items() if v is not None}
    avail = sum(w[k] for k in comp)
    coverage = avail / sum(w.values())
    if coverage < C.MIN_FACTOR_COVERAGE:
        missing = sorted(set(raw) - set(comp))
        return None, (f"insufficient factor coverage {coverage:.0%} "
                      f"(missing: {', '.join(missing) or 'none'})")

    composite = sum(comp[k] * w[k] for k in comp) / avail
    return Score(ticker=d.get("ticker", "?"), bucket=bucket,
                 composite=round(composite, 2), components=comp,
                 coverage=round(coverage, 4)), "ok"


def score_stock(d):
    """Score one stock into its bucket. Returns a Score (or None if gated out)."""
    sc, why = score_stock_verbose(d)
    if sc is None:
        log.debug("skip %s: %s", d.get("ticker"), why)
    return sc


def rank_universe(scored):
    """Split scored names into the two buckets, each sorted high->low."""
    est = sorted([s for s in scored if s.bucket == "established"],
                 key=lambda s: s.composite, reverse=True)
    spec = sorted([s for s in scored if s.bucket == "speculative"],
                  key=lambda s: s.composite, reverse=True)
    return {"established": est, "speculative": spec}


def market_cap_eligible(d, composite_rank, insider_open_market):
    """Apply the >$10B ceiling with the extreme-signal override."""
    cap = d.get("market_cap") or 0
    if cap <= C.MARKET_CAP_CEILING:
        return True
    # override: top-rank OR insider cluster of open-market buys
    if composite_rank is not None and composite_rank <= C.OVERRIDE_TOP_RANK:
        return True
    n_buyers = len({_buyer_key(t, i) for i, t in enumerate(insider_open_market)})
    total = sum(float(t.get("value_usd") or 0) for t in insider_open_market)
    if n_buyers >= C.OVERRIDE_INSIDER_CLUSTER and total >= C.OVERRIDE_INSIDER_USD:
        return True
    return False
