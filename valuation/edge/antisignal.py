"""Anti-signal decomposition — where the R2 gap lives.  [O13]

Pre-registered in `PREREG_o13_antisignal.md`, committed before this file existed.

WHAT THIS IS. R2 measured that the options alert's day-selection subtracts value: the alert book
earns +3.2702%/trade against a five-seed random-entry control's +8.3342%, a gap of -5.0640pp
(split-clean, U1-SPLIT 2026-08-11). The path study then found the same thing in path terms —
at every touch level and on both recovery measures the control recovers more often, while the
drawdowns are identical. This module asks WHERE that gap lives across the alert's own features,
whether it is concentrated or diffuse, and whether the inverse of it carries information.

WHAT THIS IS NOT. It does not re-open R2 and nothing here can revive the entry signal. Every
figure it produces is a description of a book already shown to lose to random entry.

THE ONE STRUCTURAL FACT THAT SHAPES THE WHOLE DESIGN. The control book carries the alert's own
features (`score`, `iv`, `labels`, `flow_read`, and the surface fields) at *0.0%* coverage — a
random entry has no alert to describe it. So those features reach the control only through the
`_control_for` back-link, which maps 29,564 of 29,654 control rows to exactly one alert with
zero ambiguity. A control row is then bucketed by its PARENT ALERT's feature value, and the
comparison reads "on alerts that looked like this, did the alert's chosen day beat random days
on the same name?". Structural features (`dte`, `target_delta`, ...) are carried by both books
and need no join.

There is no networking, no data access and no I/O here — callers pass rows in. That keeps the
algebra testable on a machine with no licensed data, which is every CI runner.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Iterable, Optional

# The features, fixed by the register. `iv_rank` is deliberately absent: it is 0.0% populated on
# BOTH books, so it has no values to bin. That is reported as a bug in its own right rather than
# being scored as a feature that failed.
TRACK_A = ("score", "iv", "flow_read", "labels", "skew_25d", "term_slope", "vrp", "gex_proxy")
TRACK_S = ("dte", "target_delta", "cap_tier", "marketcap_musd", "entry_spread_pct",
           "pit_atm_oi", "pit_median_spread_pct", "opt_right", "horizon")

CATEGORICAL = frozenset({"cap_tier", "horizon", "opt_right", "flow_read"})
LIST_VALUED = frozenset({"labels"})

N_QUANTILES = 5
MIN_LEVEL_N = 100          # categorical levels below this are pooled into OTHER
MAX_REFUSE_SHARE = 0.30    # the refusal rule may not refuse more than 30% of the decide half
REFUSE_MARGIN_PP = 1.50    # Q3a margin, pre-committed
N_PERM_DRAWS = 2000


# ------------------------------------------------------------------------------------------- #
# Binning
# ------------------------------------------------------------------------------------------- #
def quantile_edges(values: Iterable[float], k: int = N_QUANTILES) -> list:
    """k-quantile breakpoints (k-1 of them), computed on the ALERT book and applied to both.

    Ties are not broken: if a value repeats across a breakpoint the bins are simply uneven, which
    is honest. Deduplicating the edges would silently change the bin count and make the
    calibrated null describe a different statistic than the observed one.
    """
    xs = sorted(float(v) for v in values if v is not None and not _isnan(v))
    if not xs:
        return []
    out = []
    for i in range(1, k):
        pos = i * len(xs) / k
        lo = int(math.floor(pos))
        if lo >= len(xs):
            lo = len(xs) - 1
        out.append(xs[lo])
    return out


def _isnan(v) -> bool:
    try:
        return isinstance(v, float) and math.isnan(v)
    except Exception:                                    # pragma: no cover - defensive
        return False


def bin_numeric(value, edges: list) -> Optional[str]:
    """Bin label `q1`..`qk`, or None when the value is missing (the row drops out of that arm)."""
    if value is None or _isnan(value) or not edges:
        return None
    v = float(value)
    i = 0
    while i < len(edges) and v > edges[i]:
        i += 1
    return "q%d" % (i + 1)


def categorical_levels(values: Iterable, min_n: int = MIN_LEVEL_N) -> set:
    counts = {}
    for v in values:
        if v is None:
            continue
        counts[str(v)] = counts.get(str(v), 0) + 1
    return {k for k, n in counts.items() if n >= min_n}


def bin_categorical(value, levels: set) -> Optional[str]:
    if value is None:
        return None
    s = str(value)
    return s if s in levels else "OTHER"


def label_levels(rows: list, field: str = "labels", min_n: int = MIN_LEVEL_N) -> list:
    """Individual labels appearing on >= min_n alert trades. Each becomes a present/absent arm."""
    counts = {}
    for r in rows:
        for lab in (r.get(field) or []):
            counts[str(lab)] = counts.get(str(lab), 0) + 1
    return sorted([k for k, n in counts.items() if n >= min_n])


def make_binner(feature: str, alert_rows: list) -> Callable:
    """Return `row -> bin label or None`, with breakpoints fixed on the alert book.

    The same callable is applied to the control, so both books are cut at identical thresholds.
    That is the whole point: a bin must mean the same thing on both sides or the within-bin gap
    is not a comparison.
    """
    if feature in LIST_VALUED:
        raise ValueError("list-valued features expand to indicator arms; use make_label_binner")
    if feature in CATEGORICAL:
        levels = categorical_levels(r.get(feature) for r in alert_rows)
        return lambda r: bin_categorical(r.get(feature), levels)
    edges = quantile_edges(r.get(feature) for r in alert_rows)
    return lambda r: bin_numeric(r.get(feature), edges)


def make_label_binner(label: str) -> Callable:
    def _b(r):
        labs = r.get("labels")
        if labs is None:
            return None
        return "has" if any(str(x) == label for x in labs) else "no"
    return _b


# ------------------------------------------------------------------------------------------- #
# The gap table, and mix vs rate
# ------------------------------------------------------------------------------------------- #
def gap_table(alert_rows: list, ctrl_rows: list, binner: Callable, ret: str = "pnl_pct") -> dict:
    """Per-bin alert mean, control mean, gap, and the alert-share weight.

    Rows whose bin is None are dropped from THIS arm only — a missing feature value is not a bin.
    Both books drop on their own bin, so a feature present on one side and absent on the other
    yields an empty table rather than a silently one-sided comparison.
    """
    A, C = {}, {}
    for r in alert_rows:
        b = binner(r)
        if b is None:
            continue
        v = r.get(ret)
        if v is None:
            continue
        A.setdefault(b, []).append(float(v))
    for r in ctrl_rows:
        b = binner(r)
        if b is None:
            continue
        v = r.get(ret)
        if v is None:
            continue
        C.setdefault(b, []).append(float(v))

    n_a_tot = sum(len(v) for v in A.values())
    bins = {}
    for b in sorted(set(A) | set(C)):
        a, c = A.get(b, []), C.get(b, [])
        ma = sum(a) / len(a) if a else None
        mc = sum(c) / len(c) if c else None
        bins[b] = {
            "n_alert": len(a), "n_ctrl": len(c),
            "mean_alert": ma, "mean_ctrl": mc,
            "gap": (ma - mc) if (ma is not None and mc is not None) else None,
            "w": (len(a) / n_a_tot) if n_a_tot else 0.0,
        }
    return {"bins": bins, "n_alert": n_a_tot,
            "n_ctrl": sum(len(v) for v in C.values())}


def rate_component(table: dict) -> Optional[float]:
    """Sum_b w_b * gap_b — the gap holding the alert's own bin mix fixed."""
    tot, seen = 0.0, False
    for b, d in table["bins"].items():
        if d["gap"] is None:
            continue
        tot += d["w"] * d["gap"]
        seen = True
    return tot if seen else None


def mix_component(table: dict, ctrl_mean_all: float) -> Optional[float]:
    """What the control's DIFFERENT bin mix contributes: Sum_b (w_b - v_b) * mean_ctrl_b.

    Mix and rate together reconstruct the total gap. Reported separately because they mean
    different things: rate is "the alert loses inside a bin", mix is "the alert picks bins that
    happen to pay differently".
    """
    n_c = table["n_ctrl"]
    if not n_c:
        return None
    tot = 0.0
    for b, d in table["bins"].items():
        if d["mean_ctrl"] is None:
            continue
        v_b = d["n_ctrl"] / n_c
        tot += (d["w"] - v_b) * d["mean_ctrl"]
    return tot


def s_worst(table: dict) -> Optional[float]:
    """Share of the rate component carried by its single worst bin.

    Perfectly diffuse over k equal bins -> 1/k. Perfectly concentrated -> 1.0. It can exceed 1.0
    when other bins carry POSITIVE contributions that partly offset the worst one, which is a
    meaningful reading (concentrated and offset), not an error.
    """
    denom = rate_component(table)
    if denom is None or abs(denom) < 1e-12:
        return None
    contribs = [d["w"] * d["gap"] for d in table["bins"].values() if d["gap"] is not None]
    if not contribs:
        return None
    return min(contribs) / denom


# ------------------------------------------------------------------------------------------- #
# The calibrated null
# ------------------------------------------------------------------------------------------- #
def permutation_null(alert_rows: list, ctrl_rows: list, binner: Callable,
                     n_draws: int = N_PERM_DRAWS, seed: int = 0,
                     ret: str = "pnl_pct") -> list:
    """Null distribution of `s_worst` under "this feature carries nothing".

    Hold every row's (book, return) fixed and PERMUTE THE BIN LABELS WITHIN BOOK. That preserves
    each book's bin marginal, each book's return distribution, and — the property that makes it
    the right null — the TOTAL GAP EXACTLY, since shuffling which bin a row lands in cannot move
    either book's overall mean. Only the feature-to-return association is destroyed.

    A null that moved the total gap would be calibrating a different question.
    """
    a_bins = [binner(r) for r in alert_rows]
    a_rets = [r.get(ret) for r in alert_rows]
    c_bins = [binner(r) for r in ctrl_rows]
    c_rets = [r.get(ret) for r in ctrl_rows]

    a = [(b, float(v)) for b, v in zip(a_bins, a_rets) if b is not None and v is not None]
    c = [(b, float(v)) for b, v in zip(c_bins, c_rets) if b is not None and v is not None]
    if not a or not c:
        return []

    ab = [x[0] for x in a]
    ar = [x[1] for x in a]
    cb = [x[0] for x in c]
    cr = [x[1] for x in c]

    rng = random.Random(seed)
    out = []
    for _ in range(n_draws):
        rng.shuffle(ab)
        rng.shuffle(cb)
        t = _table_from_pairs(ab, ar, cb, cr)
        s = s_worst(t)
        if s is not None:
            out.append(s)
    return out


def _table_from_pairs(ab: list, ar: list, cb: list, cr: list) -> dict:
    A, C = {}, {}
    for b, v in zip(ab, ar):
        A.setdefault(b, []).append(v)
    for b, v in zip(cb, cr):
        C.setdefault(b, []).append(v)
    n_a = len(ar)
    bins = {}
    for b in set(A) | set(C):
        aa, cc = A.get(b, []), C.get(b, [])
        ma = sum(aa) / len(aa) if aa else None
        mc = sum(cc) / len(cc) if cc else None
        bins[b] = {"n_alert": len(aa), "n_ctrl": len(cc), "mean_alert": ma, "mean_ctrl": mc,
                   "gap": (ma - mc) if (ma is not None and mc is not None) else None,
                   "w": len(aa) / n_a if n_a else 0.0}
    return {"bins": bins, "n_alert": n_a, "n_ctrl": len(cr)}


def bin_sizes(rows: list, binner: Callable, ret: str = "pnl_pct") -> tuple:
    """`(ordered bin names, sizes, returns)` for the fast null. Order is sorted and shared."""
    by = {}
    for r in rows:
        b = binner(r)
        if b is None:
            continue
        v = r.get(ret)
        if v is None:
            continue
        by.setdefault(b, []).append(float(v))
    names = sorted(by)
    return names, [len(by[b]) for b in names], [v for b in names for v in by[b]]


def null_draws_fast(a_sizes: list, a_rets: list, c_sizes: list, c_rets: list,
                    idx_a: list, idx_c: list, n_a_tot: int, n_draws: int, seed: int) -> list:
    """Vectorised `s_worst` null. EXACTLY equivalent to permuting bin labels, not an approximation.

    Permuting labels over rows with fixed per-bin counts is the same experiment as shuffling the
    returns and cutting them into consecutive slices of those same counts — both draw a uniform
    partition of the returns into groups of the given sizes. The slice form lets a whole draw be
    one shuffle plus one cumulative sum, which is what makes 2,000 draws x 17 features x 3
    samples finish in under a minute instead of hours.

    `tests/test_antisignal.py` proves the equivalence on a fixed permutation rather than
    asserting it here.
    """
    import numpy as np

    ar = np.asarray(a_rets, dtype=float)
    cr = np.asarray(c_rets, dtype=float)
    a_cut = np.cumsum([0] + list(a_sizes))
    c_cut = np.cumsum([0] + list(c_sizes))
    ia = np.asarray(idx_a, dtype=int)
    ic = np.asarray(idx_c, dtype=int)
    w = (np.asarray(a_sizes, dtype=float)[ia]) / float(n_a_tot)

    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_draws):
        rng.shuffle(ar)
        rng.shuffle(cr)
        acs = np.concatenate(([0.0], np.cumsum(ar)))
        ccs = np.concatenate(([0.0], np.cumsum(cr)))
        a_sum = acs[a_cut[1:]] - acs[a_cut[:-1]]
        c_sum = ccs[c_cut[1:]] - ccs[c_cut[:-1]]
        a_n = np.asarray(a_sizes, dtype=float)
        c_n = np.asarray(c_sizes, dtype=float)
        gap = (a_sum[ia] / a_n[ia]) - (c_sum[ic] / c_n[ic])
        contrib = w * gap
        denom = float(contrib.sum())
        if abs(denom) < 1e-12:
            continue
        out.append(float(contrib.min()) / denom)
    return out


def percentile(xs: list, q: float) -> Optional[float]:
    if not xs:
        return None
    ys = sorted(xs)
    pos = q / 100.0 * (len(ys) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(ys) - 1)
    frac = pos - lo
    return ys[lo] * (1 - frac) + ys[hi] * frac


# ------------------------------------------------------------------------------------------- #
# Q3a — the selection inverse, both-halves
# ------------------------------------------------------------------------------------------- #
def is_degenerate(table: dict) -> bool:
    """A feature with fewer than two comparable bins says nothing about anything.

    Two of the nine structural features turn out to be CONSTANT on this book — it is 100% calls
    and 100% `swing` horizon — so they collapse to a single bin. Their `s_worst` is then exactly
    1.0 and so is every null draw, which means they can never clear a bar. That is the correct
    outcome, but it must be LABELLED: a reader seeing "did not clear" would otherwise take it as
    evidence about calls versus puts, when the book contains no puts at all.
    """
    return len([1 for d in table["bins"].values() if d["gap"] is not None]) < 2


def can_express_refusal(table: dict, max_share: float = MAX_REFUSE_SHARE) -> bool:
    """Whether this feature yields a NON-EMPTY refusal set on the table it is given.

    It exists because `s_worst` is mechanically near 1.0 for a lopsided two-bin feature — one
    alert label sits on 98.5% of the book — so an unrestricted "highest s_worst" selection
    reliably picks a feature whose only negative-gap bin is larger than the cap, and then refuses
    nothing. That measures the statistic's own lopsidedness, not the book.

    WHAT THIS READS, corrected. An earlier version tested bin WEIGHTS only, on the theory that
    eligibility should not consult an outcome at all. That version was wrong and a test caught
    it: the live failure was not "every bin is too big", it was "the only bin with a NEGATIVE GAP
    is too big", and a weights-only predicate cannot tell those apart. So this does read gaps —
    and it is therefore only ever evaluated on a DECIDE half, which is exactly where selection is
    permitted. The measure half is never consulted.
    """
    return len(refusal_set(table, max_share)) > 0


def refusal_set(decide_table: dict, max_share: float = MAX_REFUSE_SHARE) -> list:
    """Bins to refuse: most-negative gap first, stopping before the share cap is exceeded.

    The cap is what stops this collapsing into "refuse the whole book", which would trivially
    win by refusing everything and is not a rule.
    """
    cand = [(d["gap"], b, d["w"]) for b, d in decide_table["bins"].items()
            if d["gap"] is not None and d["gap"] < 0]
    cand.sort()
    out, share = [], 0.0
    for gap, b, w in cand:
        if share + w > max_share:
            continue
        out.append(b)
        share += w
    return out


def apply_refusal(alert_rows: list, ctrl_rows: list, binner: Callable, refused: list,
                  ret: str = "pnl_pct") -> dict:
    """Gap after refusing `refused`, the gap of what was refused, and the baseline."""
    ref = set(refused)

    def _mean(rows, keep: bool):
        vals = []
        for r in rows:
            b = binner(r)
            if b is None:
                continue
            inref = b in ref
            if inref != (not keep):
                continue
            v = r.get(ret)
            if v is not None:
                vals.append(float(v))
        return (sum(vals) / len(vals)) if vals else None, len(vals)

    ka, na = _mean(alert_rows, True)
    kc, nc = _mean(ctrl_rows, True)
    ra, nra = _mean(alert_rows, False)
    rc, nrc = _mean(ctrl_rows, False)

    base_a = [float(r.get(ret)) for r in alert_rows
              if binner(r) is not None and r.get(ret) is not None]
    base_c = [float(r.get(ret)) for r in ctrl_rows
              if binner(r) is not None and r.get(ret) is not None]
    base = ((sum(base_a) / len(base_a)) - (sum(base_c) / len(base_c))) \
        if base_a and base_c else None
    kept = (ka - kc) if (ka is not None and kc is not None) else None
    return {
        "baseline_gap": base,
        "kept_gap": kept,
        "refused_gap": (ra - rc) if (ra is not None and rc is not None) else None,
        "improvement_pp": ((kept - base) * 100.0) if (kept is not None and base is not None)
        else None,
        "n_kept_alert": na, "n_kept_ctrl": nc,
        "n_refused_alert": nra, "n_refused_ctrl": nrc,
        "refused_bins": sorted(ref),
    }


def inverse_verdict(dir1: dict, dir2: dict, margin_pp: float = REFUSE_MARGIN_PP) -> str:
    """Pre-committed rule: both directions clear the margin AND both refused sets really lose.

    A one-direction pass is a NULL. That rule is session 7's and it is why the LOO result did not
    become a finding.
    """
    for d in (dir1, dir2):
        if d is None:
            return "NULL"
        if d.get("improvement_pp") is None or d.get("refused_gap") is None:
            return "NULL"
        if d["improvement_pp"] < margin_pp:
            return "NULL"
        if d["refused_gap"] >= 0:
            return "NULL"
    return "INVERSE_CARRIES_INFORMATION"


def concentration_verdict(cleared_both_halves: list) -> str:
    """CONCENTRATED iff at least one feature cleared its own p95 in BOTH halves."""
    return "CONCENTRATED" if cleared_both_halves else "DIFFUSE"


# ------------------------------------------------------------------------------------------- #
# The control -> alert back-link
# ------------------------------------------------------------------------------------------- #
def attach_parent_features(ctrl_rows: list, alert_rows: list, fields: Iterable[str]) -> tuple:
    """Copy the parent alert's features onto each control row, via `_control_for`.

    Returns `(joined_rows, n_orphans)`. Orphans — control rows whose parent alert is not in the
    book — are DROPPED, not defaulted. A control row carrying a made-up feature value would be
    silently mis-binned, which is the failure this whole join exists to avoid.
    """
    idx = {}
    for r in alert_rows:
        idx[(r.get("ticker"), str(r.get("alert_ts"))[:10])] = r
    out, orphans = [], 0
    flds = list(fields)
    for c in ctrl_rows:
        parent = idx.get((c.get("ticker"), str(c.get("_control_for"))[:10]))
        if parent is None:
            orphans += 1
            continue
        d = dict(c)
        for f in flds:
            d[f] = parent.get(f)
        out.append(d)
    return out, orphans


def split_halves(rows: list, key: str = "alert_ts") -> tuple:
    """Split by calendar date at the median, early first. Ties go to the early half."""
    ds = sorted(str(r.get(key))[:10] for r in rows if r.get(key))
    if not ds:
        return [], []
    mid = ds[len(ds) // 2]
    early = [r for r in rows if str(r.get(key))[:10] <= mid]
    late = [r for r in rows if str(r.get(key))[:10] > mid]
    return early, late
