"""
T5 — Risk: turn the normalized target portfolio into concrete share counts,
scaled to a target risk level and bounded by exposure caps.

Steps:
  1. Kill switch — if the account is down past the daily loss limit, target a
     FLAT book (close everything, open nothing). Reuses core.AccountState.
  2. Volatility targeting — scale the whole portfolio so its estimated
     annualized volatility hits a target (default 10%). See the long note below
     on how that estimate is made; getting it wrong is how a book ends up
     running at a third of its intended risk.
  3. Gross exposure cap — total |notional| / equity must not exceed max_gross
     (default 1.0 = no leverage, suitable for a paper/cash-ish account).
  4. Net exposure cap — (long − short) notional bounded, so the book isn't
     secretly a giant directional bet.
  5. Per-instrument cap — no single position exceeds max_per_instrument of
     equity.
  6. Convert final notional per instrument to whole share counts (signed:
     positive = long, negative = short).

The output is a dict {symbol: target_signed_shares}, consumed by T6 (portfolio)
which diffs it against current holdings and generates rebalance orders.


═══════════════════════════════════════════════════════════════════════════════
WHY THE VOL ESTIMATE IS CORRELATION-AWARE (the single most consequential number
in this file)
═══════════════════════════════════════════════════════════════════════════════

This used to estimate portfolio volatility as the WEIGHTED AVERAGE of the
single-name vols:

    weighted_vol = Σ |w_i| · σ_i

and it was justified in a comment as "conservative — it ignores diversification
benefit, so we err toward SMALLER positions." That justification is wrong in a
way that matters, because diversification is not a small correction. It is the
whole reason a 60-name book behaves differently from one name.

The arithmetic: 60 stocks, each at 35% annualized vol, gross-normalized so
Σ|w_i| = 1. The weighted average is 0.35, so vol_scale = 0.10 / 0.35 = 0.286 and
the book deploys 29% gross. But those 60 names are not one name repeated 60
times — at a realistic average pairwise correlation of ~0.35 the actual
portfolio vol at full gross is nearer 0.21, and a long/short book lower still.
The book therefore ran at roughly 3-6% realized vol against a 10% target: about
a THIRD of the intended risk. Every Sharpe ratio, every correlation, every
allocation decision computed from those curves described a portfolio nobody
would deploy. "Conservative" is not a defence when the number is wrong by 3x
and the config file says 10%.

The correct object is the portfolio standard deviation:

    σ_p = sqrt( wᵀ Σ w )        Σ_ij = σ_i · σ_j · ρ_ij

Note this also finally makes SIGN matter. Under the weighted-average estimate a
long and a short contributed identically (both via |w|). Under wᵀΣw a short
against a correlated long genuinely cancels — which is the entire point of
running a long/short book, and was invisible to the old estimate.

── Why the correlations are SHRUNK, not used raw ──

Σ is estimated from ~63 daily observations across up to ~60 names. That is
fewer observations than names-squared by orders of magnitude: the sample
correlation matrix has more free parameters (N(N−1)/2 ≈ 1,770) than it has data
points (60 × 63 = 3,780 numbers, but only 63 independent draws of the
cross-section). Such a matrix is rank-deficient and its extreme eigenvalues are
badly biased — the smallest are far too small. Since vol targeting DIVIDES by
the estimated vol, an under-estimated portfolio vol becomes over-sized
positions. Raw sample covariance is the failure mode where a risk model
confidently recommends leverage.

The standard remedy (Ledoit-Wolf, and constant-correlation targets in
particular) is to shrink toward a low-parameter structure:

    R_shrunk = (1 − λ) · R_sample + λ · R_const

where R_const has EVERY off-diagonal set to the average sample off-diagonal
correlation. R_const has exactly one free parameter, so it is estimated very
precisely and is badly biased only if the true correlation structure is highly
heterogeneous. Blending trades a little bias for a large variance reduction.

We also keep the two halves of Σ separate on purpose. Volatilities are
estimated well (63 observations for ONE parameter each) and come straight from
the signal layer's σ_i. Correlations are estimated badly (63 observations for
~1,770 parameters) and are the only part that gets shrunk. Shrinking the raw
covariance matrix would needlessly contaminate the vols too.

── Guard rails, because a risk model that can only ever add leverage is not a
   risk model ──

  * max_vol_scale caps how far vol targeting may lever up. If the correlation
    estimate is too low (a regime break, a stale panel, a degenerate matrix),
    σ_p is under-estimated and vol_scale explodes. The cap bounds the damage.
  * max_gross_exposure still applies independently.
  * Names with no usable return history are EXCLUDED from Σ and their risk is
    added back the old linear way (|w_i| · σ_i), i.e. as if perfectly
    correlated with everything else. That over-states their contribution, which
    is the correct direction to be wrong in.
  * Too few observations, too few names, or a degenerate matrix → fall back to
    the naive weighted average and LOG WHICH PATH RAN. Silently switching risk
    models is how you end up unable to explain your own equity curve.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from .signals import Direction
from .strategy import TargetPortfolio

logger = logging.getLogger(__name__)

# Method labels reported on RiskResult (and surfaced in the Discord summary) so
# the sizing path that ran is always attributable after the fact.
VOL_METHOD_CORRELATION = "correlation"
VOL_METHOD_NAIVE = "naive_weighted_avg"


@dataclass(frozen=True)
class RiskConfig:
    target_annual_vol: float = 0.10      # 10% target portfolio volatility
    max_gross_exposure: float = 1.0      # 1.0 = no leverage
    max_net_exposure: float = 1.0        # bound on (long − short) / equity
    max_per_instrument: float = 0.20     # no single name > 20% of equity
    daily_loss_limit_pct: float = -0.05  # kill switch at −5% on the day
    # Hard ceiling on the leverage multiplier vol targeting may request.
    # Correlation-aware sizing legitimately unlocks more gross than the old
    # weighted-average estimate did; it can also be WRONG (correlations jump in
    # exactly the selloffs that matter). 2.0 says: we will size up to twice the
    # normalized book on the strength of a diversification estimate, and not a
    # basis point further, no matter what the covariance matrix claims.
    max_vol_scale: float = 2.0
    # Minimum aligned daily observations before we trust a correlation matrix
    # at all. Below this the sample correlations are noise; fall back to the
    # naive estimate rather than pretend.
    min_return_observations: int = 20
    # Below this many names with usable history there is no meaningful
    # cross-section to estimate; the naive path is as good and is honest.
    min_names_for_correlation: int = 2


@dataclass
class SizedTarget:
    symbol: str
    direction: Direction
    target_shares: int          # signed: + long, − short
    target_notional: float      # signed dollar exposure
    last_price: float


@dataclass
class RiskResult:
    targets: dict               # symbol -> SizedTarget
    kill_switch_active: bool = False
    kill_switch_reason: str = ""
    gross_exposure: float = 0.0
    net_exposure: float = 0.0
    vol_scale_applied: float = 0.0
    # ── Vol-estimate provenance (reported so the Discord summary can say which
    #    risk model actually sized the book) ──
    portfolio_vol_estimate: float = 0.0   # annualized σ_p of the NORMALIZED book
    vol_method: str = ""                  # VOL_METHOD_* above
    vol_names_with_history: int = 0       # names that made it into Σ
    vol_observations: int = 0             # aligned return observations used
    shrinkage_lambda: float = 0.0         # λ actually applied
    binding_constraint: str = ""          # which cap set the final size
    # ── Positions lost to share rounding (see the note in size()) ──
    dropped_positions: int = 0
    dropped_notional: float = 0.0
    dropped_symbols: list = field(default_factory=list)


# ─── Covariance machinery (pure functions — no config, no I/O, fully testable) ─


def align_return_panel(
    symbols: list[str], panel: dict, min_observations: int
) -> tuple[list[str], list[list[float]], int]:
    """
    Reduce a ragged {symbol: [returns]} panel to a rectangular one.

    Different names have different history lengths (new listings, halts, failed
    fetches). Correlations must be computed on CONTEMPORANEOUS returns, so we
    take the common length L = min over the usable series and keep each series'
    LAST L observations — the panel is documented most-recent-last, so trimming
    from the front is what aligns them in time.

    Any name that is missing, too short, or constant (zero variance → an
    undefined correlation) is left out; the caller adds its risk back the
    conservative way. Returns (names, series, L).
    """
    usable = []
    for sym in symbols:
        series = panel.get(sym) or []
        if len(series) >= min_observations:
            usable.append((sym, list(series)))
    if not usable:
        return [], [], 0

    length = min(len(s) for _, s in usable)
    if length < min_observations:
        return [], [], 0

    names, series = [], []
    for sym, s in usable:
        trimmed = s[-length:]
        # A constant series has zero sample variance; its correlation with
        # anything is 0/0. Drop it rather than emit a NaN into Σ.
        mean = sum(trimmed) / length
        if sum((x - mean) ** 2 for x in trimmed) <= 0:
            continue
        names.append(sym)
        series.append(trimmed)
    return names, series, length


def shrinkage_lambda(n_observations: int, n_names: int) -> float:
    """
    Choose the shrinkage intensity λ from the data-to-parameter ratio.

    A full Ledoit-Wolf λ is derived from the sampling variance of every entry of
    the sample matrix. That is worth doing when you have a matrix library; with
    stdlib-only Python and a book of tens of names, the dominant term is simply
    "how many independent observations do I have per name?", so we use it
    directly:

        ratio = n_observations / n_names
        λ     = 1 / (1 + ratio)      clamped to [0.20, 0.90]

    Reading the numbers this produces:
        63 obs /  60 names → ratio 1.05 → λ = 0.49   (the live case: half the
                                                      matrix is the structural
                                                      prior — appropriate, the
                                                      sample is nearly singular)
        63 obs /  25 names → ratio 2.52 → λ = 0.28
       252 obs /  25 names → ratio 10.1 → λ = 0.20   (floor)
        63 obs / 200 names → ratio 0.32 → λ = 0.76

    The floor of 0.20 says we never fully trust a 63-observation correlation
    matrix even when names are few — daily equity correlations are unstable
    enough that a little pull toward the average is always warranted. The cap of
    0.90 keeps at least a tenth of the actual cross-sectional information: a
    matrix that is entirely the constant-correlation prior cannot distinguish a
    sector-concentrated book from a diversified one, which is precisely the
    distinction we are sizing on.
    """
    if n_names <= 0 or n_observations <= 0:
        return 0.9
    ratio = n_observations / n_names
    return max(0.20, min(0.90, 1.0 / (1.0 + ratio)))


def sample_correlation(series: list[list[float]]) -> list[list[float]]:
    """Pearson correlation matrix of equal-length return series (pure Python)."""
    n = len(series)
    length = len(series[0]) if n else 0
    means = [sum(s) / length for s in series]
    devs = [[x - m for x in s] for s, m in zip(series, means)]
    # Sample standard deviation (ddof=1), matching the vol estimator upstream.
    sds = [math.sqrt(sum(d * d for d in dev) / (length - 1)) for dev in devs]

    corr = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if sds[i] <= 0 or sds[j] <= 0:
                rho = 0.0
            else:
                cov = sum(a * b for a, b in zip(devs[i], devs[j])) / (length - 1)
                rho = cov / (sds[i] * sds[j])
            rho = max(-1.0, min(1.0, rho))   # float slop only
            corr[i][j] = corr[j][i] = rho
    return corr


def shrink_correlation(corr: list[list[float]], lam: float) -> list[list[float]]:
    """
    Blend a sample correlation matrix toward the constant-correlation target:
    every off-diagonal replaced by the average sample off-diagonal. Diagonals
    stay exactly 1.0 — a name is perfectly correlated with itself under any
    amount of shrinkage, and letting that drift would corrupt the vols.
    """
    n = len(corr)
    if n < 2:
        return [row[:] for row in corr]

    off = [corr[i][j] for i in range(n) for j in range(i + 1, n)]
    rho_bar = sum(off) / len(off)

    out = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = (1.0 - lam) * corr[i][j] + lam * rho_bar
            out[i][j] = out[j][i] = v
    return out


def portfolio_vol(
    weights: list[float], vols: list[float], corr: list[list[float]]
) -> float:
    """
    σ_p = sqrt( Σ_i Σ_j w_i w_j σ_i σ_j ρ_ij ).

    `weights` are SIGNED (negative = short), which is what makes a hedge
    actually reduce the number. Both the sample correlation matrix and the
    constant-correlation target are positive semi-definite, and a convex
    combination of PSD matrices is PSD, so the variance cannot go negative on
    anything but float noise — the max(0.0, ...) is belt-and-braces.
    """
    n = len(weights)
    var = 0.0
    for i in range(n):
        wi_si = weights[i] * vols[i]
        if wi_si == 0.0:
            continue
        for j in range(n):
            var += wi_si * weights[j] * vols[j] * corr[i][j]
    return math.sqrt(max(0.0, var))


def naive_weighted_vol(weights: list[float], vols: list[float]) -> float:
    """
    The old estimate: Σ |w_i| σ_i. Kept as the explicit fallback path, and
    exactly equal to the correlation estimate when every name is perfectly
    correlated AND on the same side of the book (see the module note).
    """
    return sum(abs(w) * v for w, v in zip(weights, vols))


def estimate_portfolio_vol(
    target: TargetPortfolio, panel: Optional[dict], cfg: RiskConfig
) -> dict:
    """
    Estimate the annualized volatility of the NORMALIZED target portfolio.

    Returns a dict with the estimate plus enough provenance to explain it:
    method, names covered, observations, λ. Never raises — a bad panel degrades
    to the naive path with a log line, it does not take the bot down.
    """
    symbols = [w.symbol for w in target.weights]
    weights = [w.normalized_weight for w in target.weights]
    vols = [w.annualized_vol for w in target.weights]

    naive = naive_weighted_vol(weights, vols)
    fallback = {
        "vol": naive, "method": VOL_METHOD_NAIVE, "names": 0,
        "observations": 0, "lam": 0.0,
    }

    if not panel:
        logger.info(
            "Vol targeting: NAIVE weighted-average path (no return panel "
            "supplied) — σ_p estimated at %.2f%%. Diversification is being "
            "ignored, so the book will be sized SMALLER than the %.0f%% target.",
            naive * 100, cfg.target_annual_vol * 100,
        )
        return fallback

    names, series, n_obs = align_return_panel(
        symbols, panel, cfg.min_return_observations)
    if len(names) < cfg.min_names_for_correlation or n_obs < cfg.min_return_observations:
        logger.info(
            "Vol targeting: NAIVE weighted-average path (only %d name(s) with "
            "%d aligned observation(s); need %d names and %d observations) — "
            "σ_p estimated at %.2f%%.",
            len(names), n_obs, cfg.min_names_for_correlation,
            cfg.min_return_observations, naive * 100,
        )
        return fallback

    index = {sym: i for i, sym in enumerate(symbols)}
    covered_w = [weights[index[s]] for s in names]
    covered_v = [vols[index[s]] for s in names]

    lam = shrinkage_lambda(n_obs, len(names))
    corr = shrink_correlation(sample_correlation(series), lam)
    vol_covered = portfolio_vol(covered_w, covered_v, corr)

    # Names with no usable history: add their risk back LINEARLY, i.e. as if
    # perfectly correlated with the rest of the book. That over-states total
    # risk and therefore under-sizes — the safe direction when we simply do not
    # know how a name co-moves.
    missing = [s for s in symbols if s not in set(names)]
    vol_uncovered = sum(
        abs(weights[index[s]]) * vols[index[s]] for s in missing)
    if missing:
        logger.info(
            "Vol targeting: %d name(s) have no usable return history (%s%s); "
            "their risk is added linearly (assumed perfectly correlated).",
            len(missing), missing[:5], "..." if len(missing) > 5 else "",
        )

    total = vol_covered + vol_uncovered
    if total <= 0:
        logger.warning(
            "Vol targeting: correlation path produced a non-positive σ_p "
            "(%.6f) — falling back to the naive estimate (%.2f%%).",
            total, naive * 100,
        )
        return fallback

    logger.info(
        "Vol targeting: CORRELATION path — σ_p %.2f%% over %d name(s) × %d obs "
        "(λ=%.2f); naive estimate would have been %.2f%% (ratio %.2fx). "
        "Target %.0f%%.",
        total * 100, len(names), n_obs, lam, naive * 100,
        (naive / total) if total > 0 else 0.0, cfg.target_annual_vol * 100,
    )
    return {
        "vol": total, "method": VOL_METHOD_CORRELATION, "names": len(names),
        "observations": n_obs, "lam": lam,
    }


class TrendRiskManager:
    def __init__(self, config: RiskConfig):
        self.config = config

    def size(
        self,
        target: TargetPortfolio,
        account_value: float,
        last_prices: dict[str, float],
        today_pnl_pct: float = 0.0,
        recent_returns: Optional[dict] = None,
    ) -> RiskResult:
        """
        `recent_returns` is the OPTIONAL daily-return panel {symbol: [floats]},
        most recent last. When omitted we fall back to the panel the target
        carries (strategies populate `TargetPortfolio.recent_returns`), and only
        if BOTH are absent do we use the naive weighted-average vol estimate.
        Whichever path runs is logged at INFO and reported on RiskResult — this
        never switches risk models silently.
        """
        cfg = self.config

        # 1. Kill switch → flat book
        if today_pnl_pct <= cfg.daily_loss_limit_pct:
            reason = (f"Day P&L {today_pnl_pct:.2%} ≤ limit "
                      f"{cfg.daily_loss_limit_pct:.2%}; targeting FLAT.")
            logger.warning("KILL SWITCH: %s", reason)
            return RiskResult(targets={}, kill_switch_active=True, kill_switch_reason=reason)

        if not target.weights or account_value <= 0:
            return RiskResult(targets={})

        # 2. Volatility targeting — see the long note at the top of this module.
        panel = recent_returns if recent_returns is not None \
            else getattr(target, "recent_returns", None)
        est = estimate_portfolio_vol(target, panel, cfg)
        portfolio_vol_estimate = est["vol"]
        if portfolio_vol_estimate <= 0:
            return RiskResult(targets={})
        vol_scale = cfg.target_annual_vol / portfolio_vol_estimate
        binding = "vol_target"

        # 3a. Leverage ceiling on what vol targeting may request. A correlation
        # estimate that is too optimistic shows up here as a huge vol_scale;
        # this is the backstop that stops it becoming a huge book.
        if vol_scale > cfg.max_vol_scale:
            logger.warning(
                "Vol targeting requested %.2fx leverage (σ_p %.2f%% vs target "
                "%.0f%%); CAPPED at max_vol_scale %.2fx. If this fires often "
                "the correlation estimate is too low for the regime.",
                vol_scale, portfolio_vol_estimate * 100,
                cfg.target_annual_vol * 100, cfg.max_vol_scale,
            )
            vol_scale = cfg.max_vol_scale
            binding = "max_vol_scale"

        # 3b. Gross cap. The normalized book sums to 1.0 in the ordinary case,
        # so scaled gross = vol_scale. It sums to LESS than 1.0 when a gate
        # suppressed part of the book (see the regime gate in the momentum and
        # reversion strategies) — and we deliberately do NOT re-inflate for
        # that. The gross budget is expressed against the pre-suppression book,
        # so a cycle that drops half its names may deploy at most half the
        # budget. Suppressing one side must REDUCE exposure; normalizing it
        # away is exactly the bug that turned two dollar-neutral bots into
        # 100%-net-long ones.
        normalized_gross = target.gross_weight() if hasattr(target, "gross_weight") \
            else sum(abs(w.normalized_weight) for w in target.weights)
        if vol_scale > cfg.max_gross_exposure:
            vol_scale = cfg.max_gross_exposure
            binding = "max_gross_exposure"
        logger.info(
            "Vol scale %.2fx (binding constraint: %s); normalized gross weight "
            "%.2f → scaled gross ≈ %.0f%% of equity",
            vol_scale, binding, normalized_gross, vol_scale * normalized_gross * 100,
        )

        # Build notionals
        notionals: dict[str, float] = {}
        for w in target.weights:
            notionals[w.symbol] = w.normalized_weight * vol_scale * account_value

        # 5. Per-instrument cap
        cap_dollars = cfg.max_per_instrument * account_value
        n_capped = 0
        for sym in list(notionals.keys()):
            if abs(notionals[sym]) > cap_dollars:
                notionals[sym] = math.copysign(cap_dollars, notionals[sym])
                n_capped += 1
        if n_capped:
            logger.info("Per-instrument cap (%.0f%% of equity) bound on %d name(s)",
                        cfg.max_per_instrument * 100, n_capped)

        # 4. Net exposure cap.
        #
        # This check used to be unreachable: with max_gross_exposure = 1.0
        # forcing vol_scale ≤ 1.0 and a normalized gross of exactly 1.0,
        # |net| ≤ gross ≤ 1.0 = net_limit always held, so the branch never ran.
        # It now evaluates against the real post-cap notionals and is genuinely
        # reachable (any config with max_net_exposure < max_gross_exposure, and
        # any cycle where the caps interact). The default stays at 1.0 so a
        # legitimately long-only cycle is still permitted.
        #
        # When it does bind we scale the DOMINANT side only, which is what the
        # old comment claimed and the old code did not do — it scaled the whole
        # book, shrinking the hedged part too and cutting gross for no reason.
        # Scaling one side brings net to the limit while leaving the offsetting
        # exposure intact.
        net = sum(notionals.values())
        net_limit = cfg.max_net_exposure * account_value
        long_notional = sum(v for v in notionals.values() if v > 0)
        short_notional = -sum(v for v in notionals.values() if v < 0)
        if abs(net) > net_limit:
            if net > 0 and long_notional > 0:
                f = (net_limit + short_notional) / long_notional
                for sym in notionals:
                    if notionals[sym] > 0:
                        notionals[sym] *= f
                side = "long"
            elif net < 0 and short_notional > 0:
                f = (net_limit + long_notional) / short_notional
                for sym in notionals:
                    if notionals[sym] < 0:
                        notionals[sym] *= f
                side = "short"
            else:
                f, side = 1.0, "none"
            logger.warning(
                "NET EXPOSURE CAP BOUND: net %.0f%% of equity exceeded limit "
                "%.0f%%; scaled the %s side by %.3f.",
                net / account_value * 100, cfg.max_net_exposure * 100, side, f,
            )
            binding = "max_net_exposure"
        else:
            logger.info(
                "Net exposure check: net %.0f%% of equity vs limit %.0f%% — not binding.",
                net / account_value * 100, cfg.max_net_exposure * 100,
            )

        # 6. Convert final notional per instrument to whole signed share counts.
        #
        # A position whose intended notional is smaller than ONE share is
        # dropped — we do not invent fractional shares, and the broker would not
        # accept them. But this is a SYSTEMATIC bias, not a rounding detail: it
        # deletes exactly the highest-priced names (BKNG, NVR, AZO...) and it
        # gets worse as the account shrinks or as gross falls, so the book
        # silently tilts toward cheap stocks precisely when it is smallest.
        # Count it, log it, and surface it upward — a bias you can see is a
        # bias you can decide about.
        targets: dict[str, SizedTarget] = {}
        dropped: list[tuple[str, float]] = []
        for w in target.weights:
            price = last_prices.get(w.symbol, 0.0)
            if price <= 0:
                continue
            notional = notionals[w.symbol]
            shares = int(notional / price)  # truncates toward zero
            if shares == 0:
                if abs(notional) > 0:
                    dropped.append((w.symbol, notional))
                continue
            targets[w.symbol] = SizedTarget(
                symbol=w.symbol, direction=w.direction,
                target_shares=shares, target_notional=shares * price,
                last_price=price,
            )

        dropped_notional = sum(abs(n) for _, n in dropped)
        if dropped:
            logger.warning(
                "DROPPED %d position(s) to share rounding — intended notional "
                "$%s (%.2f%% of equity) not deployed. This biases the book "
                "AGAINST high-priced names: %s%s",
                len(dropped), f"{dropped_notional:,.0f}",
                dropped_notional / account_value * 100,
                [f"{s} (${abs(n):,.0f} @ ${last_prices.get(s, 0):,.2f})"
                 for s, n in dropped[:5]],
                "..." if len(dropped) > 5 else "",
            )

        gross_exp = sum(abs(t.target_notional) for t in targets.values()) / account_value
        net_exp = sum(t.target_notional for t in targets.values()) / account_value
        logger.info(
            "Risk sized %d positions: GROSS %.1f%%, NET %.1f%% of equity "
            "(vol_scale %.2f, σ_p est %.2f%% via %s, binding %s)",
            len(targets), gross_exp * 100, net_exp * 100, vol_scale,
            portfolio_vol_estimate * 100, est["method"], binding,
        )
        return RiskResult(
            targets=targets, gross_exposure=gross_exp, net_exposure=net_exp,
            vol_scale_applied=vol_scale,
            portfolio_vol_estimate=portfolio_vol_estimate,
            vol_method=est["method"],
            vol_names_with_history=est["names"],
            vol_observations=est["observations"],
            shrinkage_lambda=est["lam"],
            binding_constraint=binding,
            dropped_positions=len(dropped),
            dropped_notional=dropped_notional,
            dropped_symbols=[s for s, _ in dropped],
        )
