"""
ARCHIVED (master audit MA59, 2026-08-15) - a CLOSED study, kept so its
result stays reproducible. It is NOT reachable from the live product and
`tests/test_ma59_quarantine.py` fails if that ever changes.
Still imported by: scripts/o14_tickflow_signals.py, tests/test_tickflow_signals.py.
Do not extend this module; a new question needs a new register.

O14 — the tick-flow signal studies.

Pure, testable pieces for `PREREG_o14_tickflow_signals.md`. Every constant is the register's,
fixed before any measurement code existed.

THE ONE THING THAT MAKES THIS REGISTER DIFFERENT FROM EVERY OTHER OPTIONS REGISTER HERE, and it
is a constraint rather than a choice: **there is no declarable sign.** The audit's own literature
note says buyer-initiated flow predicts returns if it is institutional (Pan-Poteshman) and fades
if it is retail (Bryzgalova et al., who measure retail at over 60% of options volume and losing
money) - and public tick data cannot separate the two populations. So every arm is judged
TWO-SIDED on |t|, which costs power, and a SIGN-AGREEMENT clause between halves does the work a
declared sign would otherwise do. Without it, an arm strongly positive in one half and strongly
negative in the other clears on |t| twice while carrying no usable information.

`quintiles_within_date`, `long_short_series` and `month_block_t` are IMPORTED from
`surface_xsec` - the same arithmetic O3/O4/O5 were judged by - rather than re-implemented.
"""
from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from valuation.edge import surface_xsec as SX

# ---------------------------------------------------------------------------------------------
# Register constants — §2, §3, §7
SEED = 20260812
N_PERM_DRAWS = 2000
N_BOOT_DRAWS = 2000
N_QUANTILES = 5

SWEEP_MIN_EXCHANGES = 3          # "multiple exchanges within a short window"
SWEEP_WINDOW_MS = 500
BLOCK_SIZE_MULT = 10.0           # "size relative to the contract's own average"
UNUSUAL_LOOKBACK = 20            # trailing sessions, EOD chain (A5)

BH_Q = 0.10                      # the audit requires Benjamini-Hochberg
MIN_MONTHS = 40                  # void condition 1
MIN_TRADES = 2500

ARMS = ("signed_volume", "pc_flow_imbalance", "sweep_share", "block_share", "unusual_volume")


# ---------------------------------------------------------------------------------------------
# Lee-Ready aggressor classification
def lee_ready(price, bid, ask, prev_price=None) -> int:
    """+1 buy-initiated, -1 sell-initiated, 0 unclassified.

    Quoted from the audit as "the standard Lee-Ready rule" and specified completely: above the
    mid is a buy, below is a sell, AT the mid falls through to the tick test against the previous
    DIFFERENT price in the same contract. A print at the mid with no usable previous price is
    UNCLASSIFIED (0) rather than assigned a side - guessing there would manufacture flow.
    """
    if price is None or bid is None or ask is None:
        return 0
    p, b, a = float(price), float(bid), float(ask)
    if not all(np.isfinite(x) for x in (p, b, a)) or a <= 0 or b <= 0 or a < b:
        return 0
    mid = 0.5 * (a + b)
    if p > mid:
        return 1
    if p < mid:
        return -1
    if prev_price is None or not np.isfinite(float(prev_price)):
        return 0
    if p > float(prev_price):
        return 1
    if p < float(prev_price):
        return -1
    return 0


def classify_side(price, bid, ask) -> np.ndarray:
    """Vectorised Lee-Ready over one contract's prints, in time order.

    The tick test needs the previous DIFFERENT price, so it is carried forward explicitly; using
    the immediately preceding price would leave runs of equal prints unclassifiable when they are
    in fact classifiable against the last move.
    """
    p = np.asarray(price, dtype=np.float64)
    b = np.asarray(bid, dtype=np.float64)
    a = np.asarray(ask, dtype=np.float64)
    n = p.size
    out = np.zeros(n, dtype=np.int8)
    ok = np.isfinite(p) & np.isfinite(b) & np.isfinite(a) & (a >= b) & (a > 0) & (b > 0)
    mid = np.where(ok, 0.5 * (a + b), np.nan)
    out[ok & (p > mid)] = 1
    out[ok & (p < mid)] = -1
    at_mid = np.where(ok & (p == mid))[0]
    if at_mid.size:
        # prev_diff[i] = the most recent price before i that DIFFERS from p[i].
        # The recurrence matters: if p[i] equals its predecessor then the last different price
        # is whatever it was for the predecessor, so a run of identical mid-prints still
        # classifies against the last actual MOVE. Carrying the immediately preceding price
        # instead leaves every print after the first in such a run unclassified - which is what
        # the first cut of this function did, contradicting its own docstring.
        # Vectorised "last price that differed": mark where the price changed, carry the index
        # of the most recent change forward with a running maximum, and read the price there.
        # Equivalent to the recurrence prev_diff[i] = p[i-1] if p[i] != p[i-1] else prev_diff[i-1].
        changed = np.r_[False, p[1:] != p[:-1]]
        src = np.where(changed, np.arange(n) - 1, -1)
        src = np.maximum.accumulate(src)
        has = src >= 0
        prev_diff = np.where(has, p[np.maximum(src, 0)], np.nan)
        up = at_mid[(prev_diff[at_mid] < p[at_mid]) & has[at_mid]]
        dn = at_mid[(prev_diff[at_mid] > p[at_mid]) & has[at_mid]]
        out[up] = 1
        out[dn] = -1
    return out


# ---------------------------------------------------------------------------------------------
# The five features
def signed_volume(sides, sizes) -> Optional[float]:
    """A1: (buy contracts - sell contracts) / total CLASSIFIED contracts."""
    s = np.asarray(sides, dtype=np.float64)
    z = np.asarray(sizes, dtype=np.float64)
    m = np.isfinite(s) & np.isfinite(z) & (s != 0)
    if not m.any():
        return None
    tot = z[m].sum()
    if tot <= 0:
        return None
    return float((s[m] * z[m]).sum() / tot)


def pc_flow_imbalance(sides, sizes, prices, rights) -> Optional[float]:
    """A2: buy-initiated PUT premium / (buy-initiated put + buy-initiated call premium).

    Pan-Poteshman's put-call ratio restricted to BUYER-INITIATED flow, which is the form their
    result is stated in. High means put buying dominates.
    """
    s = np.asarray(sides, dtype=np.float64)
    z = np.asarray(sizes, dtype=np.float64)
    p = np.asarray(prices, dtype=np.float64)
    r = np.asarray([str(x).upper()[:1] for x in rights])
    buy = (s > 0) & np.isfinite(z) & np.isfinite(p) & (z > 0) & (p > 0)
    if not buy.any():
        return None
    prem = z * p
    put_prem = float(prem[buy & (r == "P")].sum())
    call_prem = float(prem[buy & (r == "C")].sum())
    tot = put_prem + call_prem
    if tot <= 0:
        return None
    return float(put_prem / tot)


def sweep_share(sides, sizes, prices, contract_ids, times_ms, exchanges,
                min_exchanges: int = SWEEP_MIN_EXCHANGES,
                window_ms: int = SWEEP_WINDOW_MS) -> Optional[float]:
    """A3: share of classified premium in SWEEPS.

    A sweep is prints in the SAME contract touching at least `min_exchanges` distinct exchanges
    within `window_ms`. Grouping by contract matters: the same strike hit across four venues in
    200ms is one order working; four different strikes on four venues is not.
    """
    s = np.asarray(sides, dtype=np.float64)
    z = np.asarray(sizes, dtype=np.float64)
    p = np.asarray(prices, dtype=np.float64)
    cid = np.asarray(contract_ids)
    t = np.asarray(times_ms, dtype=np.float64)
    ex = np.asarray(exchanges)
    ok = np.isfinite(z) & np.isfinite(p) & np.isfinite(t) & (s != 0) & (z > 0) & (p > 0)
    if not ok.any():
        return None
    prem = z * p
    total = float(prem[ok].sum())
    if total <= 0:
        return None
    # ONE sort by (contract, time), then contiguous group slices - the first cut built a fresh
    # boolean mask over the whole array per contract, which dominated the runtime.
    _u, codes = np.unique(cid, return_inverse=True)
    idx_ok = np.where(ok)[0]
    if idx_ok.size < min_exchanges:
        return 0.0
    order = idx_ok[np.lexsort((t[idx_ok], codes[idx_ok]))]
    gcodes = codes[order]
    bounds = np.flatnonzero(np.r_[True, gcodes[1:] != gcodes[:-1], True])
    swept = np.zeros(s.size, dtype=bool)
    for gi in range(bounds.size - 1):
        grp = order[bounds[gi]:bounds[gi + 1]]
        if grp.size < min_exchanges:
            continue
        tt = t[grp]
        j = 0
        for i in range(grp.size):
            while tt[i] - tt[j] > window_ms:
                j += 1
            if i - j + 1 >= min_exchanges:
                win = grp[j:i + 1]
                if np.unique(ex[win]).size >= min_exchanges:
                    swept[win] = True
    return float(prem[ok & swept].sum() / total)


def block_share(sides, sizes, prices, contract_ids,
                mult: float = BLOCK_SIZE_MULT) -> Optional[float]:
    """A4: share of classified premium in prints at least `mult` times that CONTRACT'S OWN mean
    print size that day - the audit's "size relative to the contract's own average"."""
    s = np.asarray(sides, dtype=np.float64)
    z = np.asarray(sizes, dtype=np.float64)
    p = np.asarray(prices, dtype=np.float64)
    cid = np.asarray(contract_ids)
    ok = np.isfinite(z) & np.isfinite(p) & (s != 0) & (z > 0) & (p > 0)
    if not ok.any():
        return None
    prem = z * p
    total = float(prem[ok].sum())
    if total <= 0:
        return None
    # Fully vectorised via group codes. The first cut masked the whole array once per contract,
    # which is O(contracts x prints) - 565 x 32k on a single AAPL alert-day.
    _u, codes = np.unique(cid, return_inverse=True)
    cnt = np.bincount(codes[ok], minlength=_u.size)
    tot_sz = np.bincount(codes[ok], weights=z[ok], minlength=_u.size)
    with np.errstate(divide="ignore", invalid="ignore"):
        avg = np.where(cnt > 0, tot_sz / np.maximum(cnt, 1), np.nan)
    thr = mult * avg[codes]
    big = ok & np.isfinite(thr) & (thr > 0) & (z >= thr)
    return float(prem[big].sum() / total)


def unusual_volume(today_volume, trailing_volumes,
                   lookback: int = UNUSUAL_LOOKBACK) -> Optional[float]:
    """A5: today's contract volume over its trailing median. NOT tick-derived - the cache holds
    alert days only, so a trailing window across sessions must come from the EOD chain."""
    if today_volume is None or not np.isfinite(float(today_volume)):
        return None
    v = [float(x) for x in (trailing_volumes or [])
         if x is not None and np.isfinite(float(x))][-int(lookback):]
    if len(v) < 5:
        return None
    med = float(np.median(v))
    if med <= 0:
        return None
    return float(today_volume) / med


# ---------------------------------------------------------------------------------------------
# Statistics — two-sided, because §1 says no sign can be declared
def perm_null_abs_t(rets, labels, months, draws: int = N_PERM_DRAWS,
                    seed: int = SEED) -> dict:
    """Within-month label permutation null on the ABSOLUTE long-short t.

    Two-sided by construction. `surface_xsec.perm_null_ls_t` is the one-sided sibling and is
    deliberately NOT reused here: comparing a two-sided statistic to a one-sided null would
    understate the bar, which is the error this register exists to avoid.
    """
    r = np.asarray(rets, dtype=np.float64)
    lab = np.asarray(labels)
    mo = np.asarray(months)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(int(draws)):
        perm = lab.copy()
        for m in np.unique(mo):
            idx = np.where(mo == m)[0]
            if idx.size > 1:
                perm[idx] = lab[idx][rng.permutation(idx.size)]
        days, ls, _q = SX.long_short_series(r, perm, mo)
        if not len(days):
            continue
        st = SX.month_block_t(ls, days, draws=200, seed=seed)
        t = st.get("t")
        if t is not None and np.isfinite(t):
            out.append(abs(float(t)))
    if not out:
        return {"p95": None, "median": None, "draws": 0}
    a = np.asarray(out)
    return {"p95": float(np.percentile(a, 95)), "median": float(np.median(a)),
            "draws": int(a.size)}


def permutation_p_two_sided(observed_abs_t, null_abs_ts) -> Optional[float]:
    """Share of null draws whose |t| is at least the observed |t|, with the +1 correction that
    keeps a p-value from ever reading exactly zero on a finite number of draws."""
    if observed_abs_t is None or not np.isfinite(observed_abs_t):
        return None
    a = np.asarray([x for x in (null_abs_ts or []) if x is not None and np.isfinite(x)],
                   dtype=np.float64)
    if a.size == 0:
        return None
    return float((1.0 + (a >= abs(float(observed_abs_t))).sum()) / (a.size + 1.0))


def benjamini_hochberg(pvals: Sequence[Optional[float]], q: float = BH_Q) -> list:
    """Standard BH step-up. Returns a bool per input, True = survives at level q.

    The audit asks for BH explicitly. It is applied ALONGSIDE the calibrated permutation bar,
    not instead of it - they are different instruments and dropping either would weaken the gate
    in a way the register forbids.
    """
    idx = [i for i, p in enumerate(pvals) if p is not None and np.isfinite(p)]
    out = [False] * len(pvals)
    if not idx:
        return out
    m = len(idx)
    order = sorted(idx, key=lambda i: pvals[i])
    kmax = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            kmax = rank
    for rank, i in enumerate(order, start=1):
        if rank <= kmax:
            out[i] = True
    return out


def arm_verdict(abs_t_early, p95_early, sign_early,
                abs_t_late, p95_late, sign_late, bh_survives) -> str:
    """CANDIDATE iff, in BOTH halves, |t| clears that half's own permutation p95, AND the
    long-short SIGN agrees between the halves, AND the arm survives BH on the full sample."""
    for t, p in ((abs_t_early, p95_early), (abs_t_late, p95_late)):
        if t is None or p is None or not np.isfinite(t) or not np.isfinite(p):
            return "NULL"
        if not (abs(t) > p):
            return "NULL"
    if sign_early is None or sign_late is None or sign_early == 0 or sign_late == 0:
        return "NULL"
    if (sign_early > 0) != (sign_late > 0):
        return "NULL"
    if not bh_survives:
        return "NULL"
    return "CANDIDATE"
