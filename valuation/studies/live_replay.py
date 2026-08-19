"""AUDIT M4 — a live-replay harness.

WHY THIS EXISTS
---------------
Audit **B7** found three composite functions in the tree and **no shipped code path that
reproduced the backtested one**. The live screener called `build_frame(metrics)` with no
keyword arguments, inheriting `CONFIG.sector_neutral` (then `True`) and
`CONFIG.residual_momentum` (then `True`), while the backtest forces both `False`. So the hot
list users saw was scored under an intervention the research had eliminated.

**That was found by reading code. It should have been found by a test** — which is M4.

WHAT IT DOES, AND WHY IT IS NOT THE EXISTING B7 PIN
---------------------------------------------------
B7's fix is pinned by `test_audit_b7_the_live_path_and_the_backtest_path_score_identically`,
which compares the two paths on **one synthetic frame**. That is a unit test of the wiring.

This replays a **real historical rebalance date on the real universe**: it takes the exact
`metrics` list the panel built for that date — captured, never re-derived, because a second
assembly of the same quantity is B7's own defect class — scores it through the **LIVE** call
(`build_frame(metrics)`, production CONFIG, no keywords) and through the **BACKTEST** call
(`build_frame(metrics, sector_neutral=False, residual_momentum=False)`), and compares the
resulting composite RANKS.

THE THING IT IS ACTUALLY GUARDING
---------------------------------
The panel hard-codes `residual_momentum=False`; the live path reads `CONFIG`. **The two agree
today only because the CONFIG defaults were changed to match.** Nothing structurally prevents
a future default flip, an env var, or a new keyword from separating them again — and the
divergence would be silent, because both paths return a perfectly well-formed frame. This
harness is the detector for that entire class, and it **raises** rather than warning.

RANKS, NOT VALUES
-----------------
The comparison is Spearman on the composite, because the composite is a weighted sum of
z-scores and an affine rescaling of every input would move the values while leaving the book
identical. **What a user receives is an ORDER**, so the order is what is asserted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import CONFIG as _CFG
from ..screener.cross_sectional import composite_score
from ..screener.factors import build_frame

#: Registered in `PREREG_x5_m4_b23_s10acct.md` §3. Set where a MATERIAL divergence trips it
#: while ordinary floating-point and tie-handling do not. Given B7's fix the expectation is
#: ~1.0; this is a floor, not a target.
MIN_RANK_CORRELATION = 0.99

#: The deployed weights: flat over the scored themes. Imported rather than restated so a
#: weight change cannot make the harness disagree with the product for the wrong reason.
THEMES = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional")


class LiveReplayDivergence(AssertionError):
    """The live path and the backtest path rank a real historical date differently."""


def _composite(frame) -> pd.Series:
    cols = [c for c in THEMES if c in frame.columns]
    w = {c: 1.0 / len(cols) for c in cols}
    return pd.to_numeric(composite_score(frame[cols], w), errors="coerce")


def replay(metrics: list, date: str = "", raise_on_divergence: bool = True) -> dict:
    """Score one date's metrics through BOTH paths and compare ranks.

    `metrics` must be the panel's OWN list for that date (see `build_fundamental_panel`'s
    `metrics_sink`). Re-deriving it here would be the defect this harness exists to catch.
    """
    if not metrics:
        return {"date": date, "status": "no metrics", "ok": False, "n": 0}

    live = build_frame(metrics)                     # production CONFIG, no keywords
    back = build_frame(metrics, sector_neutral=False, residual_momentum=False)

    a, b = _composite(live), _composite(back)
    joined = pd.concat([a.rename("live"), b.rename("back")], axis=1).dropna()
    n = int(len(joined))
    rho = (float(joined["live"].corr(joined["back"], method="spearman"))
           if n >= 3 else float("nan"))
    max_abs = (float((joined["live"] - joined["back"]).abs().max()) if n else None)

    # how many names would actually CHANGE the shipped book — the consequence, not the metric
    top_n = min(25, n)
    top_live = set(joined["live"].nlargest(top_n).index) if n else set()
    top_back = set(joined["back"].nlargest(top_n).index) if n else set()

    out = {
        "date": date, "n_names": n,
        "rank_correlation": rho,
        "max_abs_composite_diff": max_abs,
        "identical_values": bool(max_abs is not None and max_abs == 0.0),
        "top25_overlap": (len(top_live & top_back) if n else None),
        "top25_changed": (top_n - len(top_live & top_back) if n else None),
        "threshold": MIN_RANK_CORRELATION,
        # The two CONFIG flags whose defaults are the ONLY thing holding the live path and
        # the backtest together (see the module docstring). Recorded WITH the result, so a
        # future divergence can be read against the settings that produced it.
        "config_sector_neutral": bool(getattr(_CFG, "sector_neutral", False)),
        "config_residual_momentum": bool(getattr(_CFG, "residual_momentum", False)),
        "ok": bool(n >= 3 and rho == rho and rho >= MIN_RANK_CORRELATION),
    }
    if raise_on_divergence and not out["ok"]:
        raise LiveReplayDivergence(
            f"live-vs-backtest rank correlation {rho!r} on {date!r} "
            f"(n={n}) is below {MIN_RANK_CORRELATION}: the shipped hot list is not the "
            f"book the research measures. top-25 changed: {out['top25_changed']}")
    return out


def replay_from_sink(metrics_sink: dict, date: str = None, **kw) -> dict:
    """Replay one date out of a `metrics_sink` captured during a panel build.

    With no `date`, replays the LAST one — the most recent cross-section, which is the one
    closest to what the live product is scoring today.
    """
    if not metrics_sink:
        return {"status": "empty sink", "ok": False, "n_names": 0}
    d = date or sorted(metrics_sink)[-1]
    return replay(metrics_sink.get(d) or [], date=d, **kw)
