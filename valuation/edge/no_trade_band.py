"""The no-trade band (hysteresis) — ONE definition, imported by every caller.

ADOPTED 2026-08-13 (Don's call) at **width 0.30**, on S14's double-clear: session 35 swept the
shipped width grid on a decide half and measured the argmax on the held-out half, and BOTH
directions picked 0.30 and cleared (net alpha +1.78pp / +1.77pp, gross +1.02pp / +0.77pp,
turnover roughly halving). S14-WIDTH then discharged the grid-boundary caveat — given 0.40 / 0.50
/ 0.75 to choose from, both halves still picked 0.30, so the optimum is interior.

WHY THIS MODULE EXISTS AT ALL, rather than the rule living where it was measured.
Before this file the band was applied in exactly one place (`fundamental_panel.turnover_and_costs`,
the BACKTEST) and merely *declared* in three others (`settings.BOOK_CONFIGS`, the index payload,
the web display). The live book never applied it. Wiring it live by writing the rule a second time
next to `build_index` would have created two definitions of one construction — the failure this
project has already paid for elsewhere — so the rule MOVED here and both callers import it.

`fundamental_panel` imports `band_select` as its own `_band_select`, so the measured path and the
live path are not merely equivalent implementations, they are THE SAME CODE OBJECT. That identity
is pinned by a test, because equivalence maintained by hand is equivalence that drifts.

NOTHING HERE IS A NEW MEASUREMENT. The rule below is the one S14 measured, moved verbatim; the
only additions are the adopted constant and the exit-rank derivation that was previously inline.
"""

from __future__ import annotations

import numpy as np

# THE ADOPTED WIDTH — the one constant, in the one place. Every caller imports this; nobody
# writes 0.30 anywhere else. A name is held until it falls out of the top 30% of the ranked
# universe, having entered on the top 10%.
BAND_WIDTH = 0.30

# The width the `taxable` book config declared before the adoption. Kept ONLY so the config's
# historical value is traceable to a name rather than sitting as a bare literal — it is not a
# second adopted width, and nothing selects on it.
LEGACY_TAXABLE_WIDTH = 0.20

# The user-facing sentence for a name the band RETAINED. It lives here, beside the rule, so every
# surface says the same thing — the index payload, the web why-attribution and the owner view.
# Don accepted this divergence explicitly; the product's side of that bargain is that a retained
# name is never presented as though the ranking alone selected it.
BAND_HELD_NOTE = "held - challenger within band"


def exit_rank_for(n_universe: int, n_target: int, width: float | None) -> int:
    """Rank past which a held name is finally sold.

    Reproduces the backtest's inline derivation EXACTLY, including its truncation:
    `_xr = max(k, int(len(sub) * exit_frac))`. `int()` truncates rather than rounds, and that
    detail is load-bearing — the fidelity gate compares books name-for-name, so a `round()` here
    would silently select a different book on any cross-section where the product is not integral.

    `width=None` means NO band, which returns `n_target` and makes `band_select` reduce exactly to
    plain top-N. That is what keeps the no-band case a true baseline rather than a second code
    path.
    """
    if width is None:
        return int(n_target)
    return max(int(n_target), int(n_universe * width))


def band_select(comp, tickers, held, n_target, exit_rank):
    """Which names to hold, given a NO-TRADE BAND (hysteresis).

    MOVED VERBATIM from `fundamental_panel._band_select` on 2026-08-13 so that the live book and
    the backtest share one definition. The body is unchanged from the version S14 measured.

    Enter on the top `n_target`; keep an existing holding until it falls past `exit_rank`.
    Without a band a name is sold the instant it slips one place out of the book, and the
    round-trip costs and — far more expensively — realizes a short-term gain. The band lets a
    still-good name drift instead of churning.

    Book SIZE is held at `n_target` so the comparison across widths is like-for-like: survivors
    are kept best-first, then the remaining slots go to the highest-ranked names not held. With
    `exit_rank == n_target` this reduces exactly to plain top-N, which is what makes the
    no-band case a true baseline rather than a different code path.
    """
    order = np.argsort(-comp)
    rank = {tickers[order[r]]: r for r in range(len(order))}
    keep = sorted((t for t in held if rank.get(t, 1 << 30) < exit_rank), key=lambda t: rank[t])
    out = keep[:n_target]
    if len(out) < n_target:
        chosen = set(out)
        for r in range(len(order)):
            t = tickers[order[r]]
            if t not in chosen:
                out.append(t)
                chosen.add(t)
                if len(out) >= n_target:
                    break
    return out


def held_within_band(comp, tickers, held, n_target, exit_rank) -> set:
    """The names the band RETAINED that plain top-N would have sold — the divergence itself.

    This is the set the product must be honest about: each of these is a position kept because
    the band said so, while a challenger ranked above it was passed over. It exists so the
    why-attribution can label those names rather than presenting them as ordinary top-N picks,
    and so the shadow's divergence is describable in names and not only in return.

    Empty whenever there is no band, no previous book, or no held name sitting in the band.
    """
    if not held or exit_rank <= n_target:
        return set()
    order = np.argsort(-comp)
    rank = {tickers[order[r]]: r for r in range(len(order))}
    selected = set(band_select(comp, tickers, held, n_target, exit_rank))
    # A retained name is one that is IN the book, was already held, and sits outside the entry
    # window — i.e. it would not have been bought today on rank alone.
    return {t for t in selected if t in held and rank.get(t, 1 << 30) >= n_target}
