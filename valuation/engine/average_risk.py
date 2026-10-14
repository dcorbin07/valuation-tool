"""THE SAME MODEL'S BASE VALUE AT AN ORDINARY DISCOUNT RATE.  [item 53 part 3]

**THE PROBLEM THIS MAKES VISIBLE.** NVDA is discounted at **16.3%** and TSLA at **14.7%**,
because their vendor betas are about 2 — and nothing on the page said so. A reader sees a base
value far below the price and reads it as a claim about the business, when a large part of it is
a claim about the stock's volatility. `DECISIONS.md` already records that the 10-year Treasury
really is 5.28%, so the high discount rate is **NOT A DEFECT**; what was missing is the reader
being able to see how much of the answer it accounts for.

**IT RE-RUNS THE REAL MODEL RATHER THAN REIMPLEMENTING THE DISCOUNT CHAIN.** The obvious
approach — recompute a WACC at beta 1.0 and re-derive a DCF here — would be a second
implementation of the thing it is reporting on, which is the `B7` family: two definitions that
agree until one of them is edited. So this calls the pipeline's own `value_from_company` through
an injected callable, with `beta` overridden and nothing else touched, and reads the headline
off the result. **The pipeline injects itself** rather than this module importing it, because
importing upward would make the engine's valuation path depend on a presentation module.

**PRESENTATION ONLY, AND THAT IS STRUCTURAL RATHER THAN PROMISED.** The figure is attached to
a field of its own that no score, verdict, blend or recorded number reads. Pinned by test.

**IT DOES NOT MUTATE THE COMPANY.** `value_from_company` appends to `cd.quality_notes` — the
financial regime note, for one — and that list becomes the result's `warnings`. A second pass
over the same `CompanyData` would therefore duplicate every note on the FIRST result, which is
a recorded number changing. The notes are snapshotted and restored, and a test holds it.

**A SECOND PASS COSTS NO NETWORK CALL.** `compute_comps` only fetches when it is handed peers,
and this passes none; the company data is already in hand. The Monte Carlo is the slow part and
is run at a token trial count, which is safe because the trials feed `prob_undervalued` — a
SCORE input — and not the fair value this reports.
"""
from __future__ import annotations

from typing import Callable, Optional

#: The beta an "average-risk" company has by definition. Not a tuned constant: beta 1.0 IS the
#: market, so this is the one value for which the sentence "average-risk" is true by
#: construction rather than by choice.
AVERAGE_BETA = 1.0

#: Monte Carlo trials for the second pass. Low deliberately -- see the module docstring. It is
#: not zero because some consumers of a `MonteCarloResult` divide by its trial count.
REVALUE_TRIALS = 64

#: How far the two discount rates must differ before the sentence is worth showing. Below this
#: the two numbers are the same answer twice, and a page that prints "at an average-risk rate of
#: 10.0%, the base value would be $57.06" beside a headline of $57.06 is noise competing with
#: the thing a reader came for. In RATE terms, not value terms, because the rate is the input
#: the reader is being told about.
MIN_RATE_GAP = 0.005


def _pct(x) -> str:
    return "%.1f%%" % (float(x) * 100.0)


def _money(x) -> str:
    v = float(x)
    return ("$%.2f" % v) if abs(v) < 1000 else ("$%,.0f" % v).replace(",", ",")


def average_risk_read(cd, cfg, *, deployed_wacc, deployed_beta, deployed_value,
                      revalue: Callable, beta: float = AVERAGE_BETA) -> dict:
    """What the same model says at beta `beta`, as a figure and a sentence.

    `revalue(cd, cfg, overrides, mc_trials)` must return something with `base_fair_value` and
    `wacc`. The pipeline passes its own `value_from_company`; a test can pass a stub.

    Returns `available: False` with a `reason` rather than raising, and rather than returning
    `None` — an absent read and a read of zero must not look the same to the surface.
    """
    out = {"available": False, "reason": "", "beta_used": float(beta),
           "deployed_beta": None, "deployed_wacc": None, "deployed_value": None,
           "wacc": None, "value": None, "sentence": "", "is_material": False,
           "relative_change_pct": None}
    try:
        out["deployed_beta"] = float(deployed_beta) if deployed_beta is not None else None
        out["deployed_wacc"] = float(deployed_wacc) if deployed_wacc is not None else None
        out["deployed_value"] = float(deployed_value) if deployed_value else None
    except (TypeError, ValueError):
        pass

    if out["deployed_wacc"] is None:
        out["reason"] = "no discount rate was computed for this company"
        return out
    if out["deployed_value"] is None:
        # Nothing to compare against. Saying "the base value would be $X" beside a headline
        # the model DECLINED to publish would hand a reader the number the refusal withheld.
        out["reason"] = "the model published no base value for this company"
        return out

    notes = list(getattr(cd, "quality_notes", []) or [])
    try:
        alt = revalue(cd, cfg, {"beta": float(beta)}, REVALUE_TRIALS)
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the second pass failed: %s" % type(e).__name__
        return out
    finally:
        # Restore BEFORE anything reads the result, and unconditionally -- a failure partway
        # through is exactly when the notes are half-appended.
        try:
            cd.quality_notes[:] = notes
        except (AttributeError, TypeError):
            pass

    try:
        out["value"] = (float(alt.base_fair_value)
                        if alt.base_fair_value is not None else None)
        out["wacc"] = float(alt.wacc.wacc)
    except (AttributeError, TypeError, ValueError):
        out["reason"] = "the second pass returned no comparable value"
        return out

    if out["value"] is None:
        # The model values this company at its own beta and refuses at beta 1.0, or the other
        # way round. Reported rather than hidden: it is a fact about the model's own stability.
        out["reason"] = ("the model publishes no base value for this company at an "
                         "average-risk discount rate")
        return out

    gap = abs(out["wacc"] - out["deployed_wacc"])
    out["is_material"] = bool(gap >= MIN_RATE_GAP)
    if out["deployed_value"]:
        out["relative_change_pct"] = round(
            (out["value"] / out["deployed_value"] - 1.0) * 100.0, 1)
    out["available"] = True
    if not out["is_material"]:
        out["reason"] = ("this company is already discounted at close to an average-risk "
                         "rate, so the two answers are the same")
        return out
    out["sentence"] = (
        "At an average-risk discount rate of %s, the base value would be %s."
        % (_pct(out["wacc"]), _money(out["value"])))
    # The WHY, which is the half a reader needs to act on the sentence: the rate is high
    # because the beta is, and the beta is the vendor's measurement of this stock's own
    # volatility rather than a view anybody took about the company.
    out["why"] = (
        "This company is discounted at %s because its measured beta is %.2f — a reading of how "
        "much its share price moves against the market, not a judgement about the business. "
        "An average-risk company has a beta of 1.0."
        % (_pct(out["deployed_wacc"]), out["deployed_beta"] or 0.0)
        if out["deployed_beta"] else
        "This company is discounted at %s. An average-risk company has a beta of 1.0."
        % _pct(out["deployed_wacc"]))
    return out
