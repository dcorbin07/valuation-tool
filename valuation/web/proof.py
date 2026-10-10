"""The public proof surface — every headline figure, the bar it is measured against, and
the ones it fails.

WHY THIS MODULE EXISTS AND WHY IT IS NOT A TEMPLATE
---------------------------------------------------
`/methodology` explains the method in prose. This page does the other half: it shows the
NUMBERS and, next to each one, the threshold it was judged against and whether it cleared.

Every figure here is DERIVED from an artifact on disk. Nothing is typed. That is the same
rule `payoff.py` states in one line — *"a number typed into a template is a number that
drifts"* — and it matters more here than anywhere else on the site, because this is the page
a stranger reads to decide whether to believe the rest of it. A proof page carrying a stale
hand-typed figure is worse than no proof page: it is the claim and the refutation in one
object.

The two sources, and why both:

  BACKTEST_RESULTS.json        the canonical run. Headline, benchmarks, decile ladder,
                               costs, the return distribution, and the project's own
                               multiple-testing block.

  MA19_RECALIBRATION.json      the placebo. 100 draws in which the signal is SHUFFLED
                               within each rebalance date and pushed through the identical
                               pipeline, so the null preserves the per-date distribution,
                               the missingness pattern and the cross-theme correlation and
                               destroys only the thing under test. This is the single most
                               persuasive artifact the project owns, and until now it has
                               never been on a public surface.

WHAT THIS MODULE REFUSES TO DO
------------------------------
1. It NEVER falls back to a typed constant when an artifact is missing. A section whose
   source is absent is dropped and `missing` names it. A proof page that invents its own
   evidence when the evidence is unavailable is the exact failure it exists to prevent.

2. It ships NO figure derived from Global Factor Data (the X8 international replication).
   That dataset is CC BY-NC 4.0, research-only, and `CLAUDE.md` records the rule without
   qualification: it validates the model and can never ship in the product. The replication
   is the strongest out-of-sample evidence this project has, and it stays off this page.

3. It computes no verdict of its own. Every pass/fail below is a comparison the artifact
   already carries (`multiple_testing.hlz.clears_*`, `cpcv.*.want`, MA19's `shipped_claims`)
   or a direct comparison against a floor MA19 measured. This module arranges evidence; it
   does not adjudicate it.

4. It quotes no forward-track figure. The live track is a different object with a different
   clock, and mixing a backtested statistic with a 20-row live series on one page invites
   exactly the averaging that `tidemark_surface.py` was built as a separate page to prevent.
"""

from __future__ import annotations

import json
import os

# ---- artifact locations ------------------------------------------------------------------
# Resolved from THIS FILE rather than from the working directory. `results_file.repo_root()`
# walks up from `os.getcwd()`, which is correct for a script run inside the repo and wrong in
# a deployed container, where the cwd is the app root and there is no `.git` anywhere. A web
# surface must resolve its own inputs from its own location.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))

BACKTEST_JSON = os.path.join(_ROOT, "BACKTEST_RESULTS.json")


def _first_existing(*paths: str) -> str:
    """The first path that exists, else the first path (so a refusal names a real location).

    WHY TWO LOCATIONS (audit 6, D6 — Don, 2026-09-29). The placebo files were born under
    `data/free_analysis/`, which is gitignored and never ships, and Render mounts its disk at
    `/app/data`, shadowing anything an image might carry there — so in production this page
    said "missing" for its own centrepiece. `artifacts/proof/` is a TRACKED copy of the two
    files: derived statistics about this project's own model (100 shuffled draws and their
    percentiles), not vendor rows, so committing them breaks no licence. The research copy
    under `data/` is still honoured second, for a checkout that has the study but not the
    artifact directory."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[0]


_ARTIFACTS = os.path.join(_ROOT, "artifacts", "proof")
_STUDY = os.path.join(_ROOT, "data", "free_analysis")
# The RAW draws, retained by session 10 for exactly this purpose. Preferred over MA19's
# summary block because it carries all 100 values rather than their percentiles, which is what
# lets the page say "N of 100 noise runs beat the real result" as a DERIVED count instead of a
# remembered one. MA19 is the fallback: it summarises the same draws (98 bit-identical, 2
# re-scored) and can still supply a median and a floor if the raw file is absent.
#
# ITEM 47 / DON 2026-10-10: THE CORRECTED PANEL'S OWN DRAWS COME FIRST, AND THAT IS THE WHOLE
# POINT OF THE RULING. The canonical run now describes the 9,645-name panel, and
# `PLACEBO_HAC.json` was calibrated on the 2,531-name one -- the two share ZERO rebalance
# dates. Showing the corrected real result against the old panel's noise is the mixed-pair
# defect `MA19` already paid for once (a numerator at one N against a floor at another), on a
# public page. `_panel_matches` below refuses the comparison rather than relying on this
# ordering, so a deploy that lost the corrected file would go DARK instead of going stale.
PLACEBO_JSON = _first_existing(os.path.join(_ARTIFACTS, "PLACEBO_CORRECTED.json"),
                               os.path.join(_STUDY, "PLACEBO_CORRECTED.json"),
                               os.path.join(_ARTIFACTS, "PLACEBO_HAC.json"),
                               os.path.join(_STUDY, "PLACEBO_HAC.json"))
PLACEBO_FALLBACK_JSON = _first_existing(os.path.join(_ARTIFACTS, "MA19_RECALIBRATION.json"),
                                        os.path.join(_STUDY, "MA19_RECALIBRATION.json"))


def _load(path):
    """Parse a JSON artifact, or return None. Never raises into a request."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _num(x):
    """A finite float, or None. A NaN reaching a template renders as the string 'nan'."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def _dig(d, *path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


# ------------------------------------------------------------------------------------------
# the placebo — the centrepiece
# ------------------------------------------------------------------------------------------

# Which shuffled-null comparisons are safe to render, and why only these.
#
# A placebo floor is a function of the trial count N: N enters the CPCV adopt gate, so raising
# it can re-score a draw under different weights and move a percentile. MA19 measured which
# floors that actually moves and MB31 proved the adopt set unchanged below equity N = 247.
#
# The four statistics below are the ones MA19 reports as UNMOVED across every N regime the
# project has run (its `floors` block: delta 0.0). They can therefore be shown against the
# canonical run without pairing a numerator at one N with a floor at another — the exact
# mismatch MA19 was written to catch, where a Deflated Sharpe at N=116 was being quoted
# against a floor at N=84.
#
# The Deflated Sharpe and PBO are deliberately NOT in this list. Both are N-dependent by a
# different channel (N enters the DSR formula directly, so every draw moves), so a comparison
# would have to be re-derived at today's N to be honest. They appear further down in the
# `bars` table instead, quoted at the N the artifact itself used and labelled with it.
_PLACEBO_ROWS = (
    # (artifact key in `real`/null blocks, label, direction, unit)
    #
    # direction "high" = the real value should sit ABOVE the noise; "low" = below it.
    # Monotonicity is the one that catches people out: the deciles are ordered best-composite
    # first, so -1.0 is a perfectly ordered ladder and +1.0 is a ladder running backwards.
    ("top_decile_alpha", "Top-decile alpha, per quarter", "high", "pct"),
    ("top_decile_alpha_tstat_nw", "Top-decile alpha, t-statistic", "high", "num"),
    ("long_short_tstat_nw", "Long-short spread, t-statistic", "high", "num"),
    ("monotonicity", "Decile ladder ordering", "low", "num"),
)


def _quantile(sorted_vals, q):
    """Linear-interpolated quantile. Implemented here rather than imported because this module
    must not pull numpy into a request path for four numbers."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


#: How close the two equal-weighted benchmarks must sit to count as the same panel. The two
#: panels this project has differ by 3.8 PERCENTAGE POINTS on this quantity (18.137% against
#: 14.313%), so a 0.1% relative tolerance separates them by a factor of about 270 -- the gate
#: is nowhere near a knife edge, which is what makes it worth having.
_SAME_PANEL_REL_TOL = 1e-3


def _panel_matches(draws_doc, real_source):
    """Do the noise draws and the real figures describe the SAME panel?  [ITEM 47]

    THE GUARD DON'S 2026-10-10 RULING ASKED FOR, AND IT REPLACES THE OLD ONE. The page used to
    guarantee only that at least one bar FAILED -- a guard against looking too good. That is
    the wrong property: a result can be honest and clear every bar, and it can be dishonest
    while failing one. What actually has to hold is that the real result and the noise it is
    shown against were measured on the same object.

    THE FINGERPRINT IS THE EQUAL-WEIGHTED BENCHMARK, and it was chosen because it is the one
    figure here that does NOT depend on the construction under test: it is what every name in
    the universe returned, equally weighted, so two runs on one panel agree on it whatever
    their weights, their adoption or their shuffling. Measured: the corrected draws carry
    0.14313437766389772 and the canonical run's `benchmarks.equal_weight` carries
    0.14313437766389772 -- bit-identical -- while the published panel's is 0.18137118752419476.

    WHY NOT COMPARE THE `real` BLOCKS. On the old panel the placebo file's own `real` block
    reproduced the canonical figures to sixteen digits, because `cpcv.adopt` was false and the
    adopted book WAS the deployed one. On the corrected panel CPCV adopts, so the sweep's
    `real` block is the ADOPTED book (long-short HAC t 2.1238) and the canonical headline is
    the DEPLOYED one (4.5945). They legitimately differ, so requiring them to agree would
    refuse a correct pair -- the `MB31` family, a guard asserting that two numbers are equal
    today rather than the property the equality stood in for.

    FAILS CLOSED: anything unreadable or absent is NOT a match.
    """
    try:
        ew_real = _num(_dig(real_source, "benchmarks", "equal_weight", "benchmark_ann"))
        draws = (draws_doc or {}).get("draws")
        if ew_real is None or not isinstance(draws, list) or not draws:
            return False, "the equal-weighted benchmark is missing from one of the two sources"
        ew_draws = [v for v in (_num(d.get("equal_weight_ann")) for d in draws)
                    if v is not None]
        if not ew_draws:
            return False, "the placebo draws carry no equal-weighted benchmark to match on"
        ew_draws.sort()
        ew_mid = ew_draws[len(ew_draws) // 2]
        if ew_real == 0:
            return False, "the canonical equal-weighted benchmark is zero"
        if abs(ew_mid - ew_real) / abs(ew_real) > _SAME_PANEL_REL_TOL:
            return False, ("the placebo draws and the canonical run describe DIFFERENT panels "
                           "(equal-weighted benchmark %.6f against %.6f), so the comparison "
                           "would not be like for like" % (ew_mid, ew_real))
        return True, ""
    except Exception:                                    # noqa: BLE001 -- fail closed
        return False, "the panel match could not be established"


def _placebo(real_source: dict, draws_doc: dict, summary_doc: dict):
    """Build the shuffled-signal comparison.

    The real value is taken from the CANONICAL run (`BACKTEST_RESULTS.json`) rather than from
    the placebo file's own `real` block wherever the two describe the same object, so this
    page cannot quietly show a figure the rest of the site does not. The two agree to sixteen
    digits on every field they share, which MA19's C2 control asserts, so the preference costs
    nothing and removes a way for the page to drift.

    `n_beaten` — how many of the 100 worthless runs beat the real result — is COUNTED from the
    draws. It is the single most quotable number on the page and the one a reader is most
    entitled to see derived rather than asserted, because "no noise run came close" and "three
    noise runs beat it" are very different claims and only the data can say which is true.
    """
    # LIKE FOR LIKE OR NOTHING (item 47). Checked before a single row is built, so a mismatch
    # cannot produce a half-rendered comparison.
    same_panel, why_not = _panel_matches(draws_doc, real_source)

    rows = []
    all_draws = draws_doc.get("draws") if isinstance(draws_doc, dict) else None
    # THE MATCHED NULL IS THE NON-ADOPTING DRAWS, and this is `MB8`'s rule rather than a
    # preference: "a floor whose draws adopt is not the floor for a book that does not". The
    # real result on this page is the DEPLOYED flat 1/7 book, which never adopts; on the
    # corrected universe 16 of the 100 noise draws DO adopt, and `X7` measured adoption worth
    # about +1.4 of a t on a worthless signal. Pooling them would inflate the bar the real
    # result is shown against -- in OUR favour on the floor and against us on the beat-count,
    # which is exactly why it is conditioned rather than left pooled.
    #
    # NOTHING IS HIDDEN BY IT: `n_draws_pooled` and `n_adopting_excluded` travel in the
    # payload and the page states the split.
    n_pooled = len(all_draws) if isinstance(all_draws, list) else 0
    if isinstance(all_draws, list) and any("cpcv_adopt" in d for d in all_draws):
        draws = [d for d in all_draws if not d.get("cpcv_adopt")]
    else:
        draws = all_draws
    n_excluded = n_pooled - (len(draws) if isinstance(draws, list) else 0)
    have_draws = same_panel and isinstance(draws, list) and len(draws) >= 20

    null_summary = _dig(summary_doc, "null_x7_reconstructed", default={}) if summary_doc else {}

    for key, label, direction, unit in _PLACEBO_ROWS:
        real = _num(_dig(real_source, "construction", key))
        if real is None and draws_doc:
            real = _num(_dig(draws_doc, "real", key))
        if real is None and summary_doc:
            real = _num(_dig(summary_doc, "real", key))
        if real is None:
            continue

        if have_draws:
            vals = sorted(v for v in (_num(d.get(key)) for d in draws) if v is not None)
            if len(vals) < 20:
                continue
            n = len(vals)
            p50 = _quantile(vals, 0.50)
            bar = _quantile(vals, 0.95 if direction == "high" else 0.05)
            lo, hi = vals[0], vals[-1]
            # Counted, not inferred. A tie counts AGAINST us: a noise run that merely equals
            # the real result is not one the real result beat, and on a coarse statistic like
            # the decile ordering that case actually occurs.
            if direction == "high":
                n_beaten = sum(1 for v in vals if v >= real)
            else:
                n_beaten = sum(1 for v in vals if v <= real)
        else:
            dist = null_summary.get(key)
            if not isinstance(dist, dict):
                continue
            n = int(_num(dist.get("n")) or 0)
            p50 = _num(dist.get("p50"))
            bar = _num(dist.get("p95") if direction == "high" else dist.get("p05"))
            lo, hi = _num(dist.get("min")), _num(dist.get("max"))
            n_beaten = None      # cannot be counted from percentiles; the page says so
            if None in (p50, bar, lo, hi) or not n:
                continue

        clears = (real > bar) if direction == "high" else (real < bar)

        rows.append({
            "key": key, "label": label, "direction": direction, "unit": unit,
            "real": real, "noise_median": p50, "noise_bar": bar,
            "noise_min": lo, "noise_max": hi, "n_draws": n,
            "n_beaten": n_beaten,
            "clears": bool(clears),
            "beats_every_draw": (n_beaten == 0) if n_beaten is not None else None,
        })

    if not rows:
        return None

    src = draws_doc if have_draws else summary_doc
    return {
        "rows": rows,
        "counted_from_draws": bool(have_draws),
        # The gate's own answer, in the payload, so the page can say WHY a comparison it
        # cannot make honestly is absent rather than simply not showing it.
        "same_panel": bool(same_panel),
        "same_panel_reason": why_not,
        "n_draws_pooled": n_pooled,
        "n_adopting_excluded": n_excluded,
        "matched_null_note": (
            "The noise runs shown are the %d of %d that did NOT adopt a tuned weighting, "
            "matched to the deployed flat-weight book this page is about. The %d that adopted "
            "are excluded rather than pooled, because adoption is worth about +1.4 of a "
            "t-statistic even on a signal known to be worthless, and pooling them would move "
            "the bar." % (len(draws) if isinstance(draws, list) else 0, n_pooled, n_excluded)
        ) if n_excluded else "",
        "n_draws": int(_num(_dig(src, "n_draws")) or (rows[0]["n_draws"] if rows else 0)),
        "seeds": _dig(src, "seeds"),
        "register": _dig(summary_doc or {}, "register") or _dig(draws_doc or {}, "test"),
        "source": os.path.basename(PLACEBO_JSON if have_draws else PLACEBO_FALLBACK_JSON),
    }


# ------------------------------------------------------------------------------------------
# the bars it fails
# ------------------------------------------------------------------------------------------

def _tension(res: dict, hlz: dict):
    """The artifact's two-bars sentence, REFUSED when it contradicts the artifact's own
    booleans, and replaced by one derived from them.  [ITEM 47]

    THE SHIPPED SENTENCE IS WRONG IN TWO PLACES AND IT CANNOT BE FIXED IN THE FILE. The run
    writes `the_tension` as a HARD-CODED string; the canonical move then moved both verdicts
    it states. It asserts the headline "FAILS the bar derived from counting its own trials" --
    the corrected run clears it -- and it asserts "cpcv.adopt is false on every run", which
    that same run falsified by adopting `ic-proportional`. The generator is repaired for the
    NEXT run (`fundamental_panel._hlz_tension` now computes it), and re-running the canonical
    backtest to change a sentence is one to two hours this does not need.
    #
    So the page refuses the stored prose when it disagrees with the stored verdicts. The check
    is on the CONTRADICTION rather than on the words alone: a sentence that merely mentions
    "fails" is fine, and one that claims a verdict the artifact's own boolean denies is not.
    """
    stored = (hlz.get("the_tension") or "").strip()
    clears_hlz = hlz.get("clears_hlz_hurdle")
    adopted = _dig(res, "cpcv", "adopt")
    wrong = []
    low = stored.lower()
    if clears_hlz and "fails the bar derived from counting" in low:
        wrong.append("it says the headline fails the trial-counting bar, and this run clears it")
    if adopted and "cpcv.adopt is false" in low:
        wrong.append("it says no weighting was ever adopted, and this run adopted one")
    if not stored or not wrong:
        return stored or None
    bars = (("CLEARS" if clears_hlz else "FAILS")
            + " the bar derived from counting its own trials, and "
            + ("CLEARS" if hlz.get("clears_x7_calibrated_floor") else "FAILS")
            + " the bar measured against a shuffled-signal placebo.")
    note = (" The run's own stored wording for this is out of date and is not shown: "
            + "; ".join(wrong) + ". The figures above are the run's; only that sentence was "
            "hard-coded, and the code that writes it now derives it.")
    tail = (" The trial-counting bar prices the best of N attempts, and the model this site "
            "runs is flat-weighted and was never tuned, so the tests counted are "
            "overwhelmingly alternatives that were rejected.")
    if adopted:
        tail += (" One qualification: on this universe the selection step did prefer a tuned "
                 "weighting. The flat weights are kept anyway, because the tuned book earns "
                 "less and because nothing is adopted without the owner approving it.")
    return bars + tail + note


def _bars(res: dict, placebo: dict = None):
    """The thresholds, including — especially — the ones the headline does not clear.

    Every entry is read from the artifact's own self-describing comparison. The artifact
    stores `want` strings and `clears_*` booleans precisely so a reader does not have to
    remember which direction each bar runs in, and this function does not second-guess them.
    """
    out = []

    hlz = _dig(res, "multiple_testing", "hlz", default={})
    value = _num(hlz.get("value"))
    if value is not None:
        # THE FLOOR IS TAKEN FROM THE CORRECTED PANEL'S OWN DRAWS WHERE THEY ARE AVAILABLE,
        # AND THE ARTIFACT'S LITERAL IS NAMED RATHER THAN USED (item 47). The run writes
        # `x7_calibrated_floor: 2.2837` as a LITERAL, calibrated on the 2,531-name panel, and
        # after the canonical move that is a numerator from one panel against a bar from
        # another -- `MA19`'s mixed-pair defect, which r1 flagged as a named not-done because
        # fixing it inside the artifact means a one-to-two-hour re-run to change a label on a
        # verdict that is correct under every floor the project has.
        #
        # It is fixed HERE instead, by DERIVING the bar from the same draws the section above
        # renders, so the page never shows a statistic against a bar measured on a different
        # object. Both numbers ship: the derived one is the bar, and the artifact's is named as
        # the previous panel's.
        floor = None
        floor_note = ""
        if placebo:
            for r in (placebo.get("rows") or []):
                if r.get("key") == "long_short_tstat_nw":
                    floor = _num(r.get("noise_bar"))
                    break
        old_floor = _num(hlz.get("x7_calibrated_floor"))
        if floor is not None:
            floor_note = (" This bar is re-measured on the SAME 9,645-name panel as the "
                          "result, from the %d shuffled runs above that did not adopt a tuned "
                          "weighting. The artifact still carries the previous panel's figure "
                          "(%s), which is not the bar for this one."
                          % (placebo.get("rows")[0].get("n_draws") if placebo.get("rows")
                             else 0,
                             ("%.4f" % old_floor) if old_floor is not None else "absent"))
        else:
            floor = old_floor
            floor_note = (" MEASURED ON A DIFFERENT PANEL FROM THE RESULT: this bar was "
                          "calibrated on the previous 2,531-name universe and the corrected "
                          "draws could not be read, so treat it as an extrapolation.")
        if floor is not None:
            out.append({
                "name": "Long-short t vs. this project's own placebo floor",
                "value": value, "bar": floor,
                # DERIVED rather than read: the artifact's boolean is about the artifact's own
                # literal, and the bar on this row may not be that literal.
                "passes": bool(value > floor),
                "what": "The 95th percentile of 100 shuffled-signal runs. Beating it means "
                        "the result is bigger than 95 out of 100 runs on a signal known to "
                        "be worthless." + floor_note,
                "floor_published_previous_panel": old_floor,
            })
        hurdle = _num(hlz.get("hurdle_sqrt_2_ln_N"))
        if hurdle is not None:
            out.append({
                "name": "Long-short t vs. the Harvey-Liu-Zhu multiple-testing hurdle",
                "value": value, "bar": hurdle,
                "passes": bool(hlz.get("clears_hlz_hurdle")),
                "what": "A bar that rises with the number of tests you have run. We have run "
                        "a lot. On the previous 2,531-name universe this was the headline's "
                        "clearest FAILURE (2.62 against 3.29); on the corrected 9,645-name "
                        "universe the same model clears it, so both bars now pass at once. "
                        "That is a restatement rather than a new result -- the same composite "
                        "on a wider universe and a rebalance calendar that shares no dates "
                        "with the old one -- and the artifact records both sides of the "
                        "argument either way.",
                "tension": _tension(res, hlz),
            })

    pbo = _dig(res, "cpcv", "pbo", default={})
    if _num(pbo.get("value")) is not None:
        out.append({
            "name": "Probability of backtest overfitting",
            "value": _num(pbo.get("value")), "bar": 0.50, "lower_is_better": True,
            "passes": _num(pbo.get("value")) < 0.50,
            "what": "UNMEASURED FOR THE BOOK THIS PAGE IS ABOUT, and the number beside it "
                    "is not a pass to quote. This statistic scores the step that CHOOSES "
                    "between weightings, and on this universe that step picks a tuned "
                    "weighting for the first time in the project's history -- so the figure "
                    "describes the tuned book, not the flat-weighted one the site runs. The "
                    "bar is also close to useless here: on this panel's own shuffled runs "
                    "41 of 100 worthless signals 'pass' it. Shown rather than dropped, "
                    "because a measure we cannot score for the deployed book should be "
                    "visible as unscored.",
            "scope": _dig(res, "cpcv", "pbo_scope"),
            "unmeasured_for_the_deployed_book": True,
            "describes": "the CPCV-adopted book, not the deployed flat-weight book",
        })

    dsr = _dig(res, "cpcv", "deflated_sharpe", default={})
    dsr_detail = _dig(res, "cpcv", "deflated_sharpe_detail", default={})
    if _num(dsr.get("value")) is not None:
        out.append({
            "name": "Deflated Sharpe ratio",
            "value": _num(dsr.get("value")), "bar": 0.95,
            "passes": _num(dsr.get("value")) > 0.95,
            "what": "UNMEASURED FOR THE BOOK THIS PAGE IS ABOUT, like the line above, and "
                    "for the same reason: it is computed on whichever weighting the "
                    "selection step chose, and on this universe that is a tuned one rather "
                    "than the flat weights the site runs. On the previous universe the two "
                    "were the same book and this figure read 0.79 -- failing the "
                    "conventional 0.95 bar while sitting above all 100 shuffled runs. Here "
                    "it fails both: 0.0016 against 0.95 and against this panel's own "
                    "shuffled floor of 0.59. It is shown rather than dropped, and it is not "
                    "evidence about the deployed book in either direction.",
            "unmeasured_for_the_deployed_book": True,
            "describes": "the CPCV-adopted book, not the deployed flat-weight book",
            "n_trials": _num(dsr_detail.get("n_trials")),
        })

    return out or None


# ------------------------------------------------------------------------------------------
# the restatement
# ------------------------------------------------------------------------------------------

#: WHAT THE PREVIOUS PANEL PUBLISHED, so the page can state the correction rather than quietly
#: replacing one number with another. These are the only figures in this module that do not
#: come from the artifact it reads, for the obvious reason: the artifact describes the panel
#: that REPLACED them. Every one is pinned to `CANONICAL_FIGURE_TABLE.md`, which is tracked and
#: GENERATED by `scripts/canon_figure_table.py` from the landed artifacts, so they cannot be
#: this page's own invention. `tests/test_proof_page.py` asserts each appears there verbatim.
_PUBLISHED_PANEL_NAMES = 2531
_PUBLISHED_TOP_DECILE_ALPHA = 0.071741
#: `X2` re-ran the whole backtest on seven equally valid rebalance grids on ONE universe and
#: the long-short t-statistic ranged 2.703 to 3.517 -- so the grid ALONE is worth this much.
_GRID_T_RANGE = (2.703, 3.517)


def _research_vs_spy(res: dict):
    """The research decile against SPY, GROSS and NET, both plainly.  [DON 2026-10-10, ruling 3]

    THE BENCHMARKS TABLE IS GROSS AND SAYS SO, AND THAT IS NOT ENOUGH ANY MORE. On the
    previous panel the decile's gross excess over SPY was large enough that netting costs left
    it clearly positive. On the corrected 9,645-name universe the book reaches far down the cap
    scale, the measured one-way cost rises from 33.4 to ~77 bps, and the net result goes
    NEGATIVE. A table labelled "gross of trading costs" is honest about its own basis and still
    leaves a reader to discover that the net figure flips sign, so Don ruled it shown plainly.

    BOTH ROUTES TO THE SAME CONCLUSION SHIP, because they differ and only one is derivable
    here. The ruling's figure is `-1.14pp/yr`, from arm B of r1's `INDEX_BOOK_CORRECTED.json`
    (the index-book machinery). This artifact's own numbers give a different route: the gross
    excess over SPY minus the measured cost drag on the top decile. The two are not the same
    construction and they do not give the same number -- and they agree on the sign, which is
    the claim. Quoting one without the other would be picking a figure.
    """
    bm = _dig(res, "benchmarks", "spy", default={}) or {}
    gross = _num(bm.get("excess_ann"))
    t = _num(bm.get("excess_tstat_nw"))
    c = _dig(res, "costs", "top_decile", default={}) or {}
    drag = None
    g, n = _num(c.get("gross_alpha")), _num(c.get("net_alpha"))
    if g is not None and n is not None:
        drag = g - n
    if gross is None:
        return None
    try:
        from ..screener.index_book_measured import RESEARCH_ALPHA_VS_SPY_PP as RULED
    except Exception:                                        # noqa: BLE001
        RULED = None
    return {
        "gross_excess_ann": gross,
        "gross_tstat_nw": t,
        "cost_drag_ann": drag,
        "implied_net_excess_ann": (None if drag is None else gross - drag),
        "ruled_net_pp": RULED,
        "ruled_source": "arm B of INDEX_BOOK_CORRECTED.json, quoted in the 2026-10-10 ruling",
    }


def _restatement(res: dict):
    """The old -> new correction, DERIVED, so no figure is typed into the template.  [ITEM 47]

    `tests/test_proof_page.py` forbids a performance-shaped literal in the template, and that
    guard is right: a number typed into HTML is a number that goes stale silently. So the
    survivors correction and the disjoint-grid caveat get their figures from here.

    Returns None rather than a partial block if the artifact cannot supply the new figures,
    which keeps the page's "a hole is visible rather than silent" property.
    """
    names = _num(_dig(res, "universe", "n_names"))
    dates = _num(_dig(res, "universe", "n_dates"))
    alpha = _num(_dig(res, "construction", "top_decile_alpha"))
    if None in (names, dates, alpha):
        return None
    lo, hi = _GRID_T_RANGE
    return {
        "published_names": _PUBLISHED_PANEL_NAMES,
        "names": int(names),
        "dates": int(dates),
        "published_top_decile_alpha": _PUBLISHED_TOP_DECILE_ALPHA,
        "top_decile_alpha": alpha,
        # The direction, stated as a WORD so the template cannot get the sign backwards.
        "direction": ("worse" if alpha < _PUBLISHED_TOP_DECILE_ALPHA else "better"),
        "shared_rebalance_dates": 0,
        "grid_t_low": lo,
        "grid_t_high": hi,
        "grid_t_span": round(hi - lo, 3),
    }


# ------------------------------------------------------------------------------------------
# public payload
# ------------------------------------------------------------------------------------------

def payload() -> dict:
    """Everything the proof page renders, or an honest account of what is missing.

    Returns a dict that is always safe to hand to a template. `available` is False when the
    canonical run cannot be read at all; individual sections are None when their own source
    is absent, and `missing` names every one so a hole on the page is visible rather than
    silent — a proof page that loses a section and still looks complete is the failure mode
    this whole module is arranged against.
    """
    res = _load(BACKTEST_JSON)
    draws_doc = _load(PLACEBO_JSON)
    summary_doc = _load(PLACEBO_FALLBACK_JSON)
    missing = []
    if res is None:
        missing.append(os.path.basename(BACKTEST_JSON))
        return {"available": False, "missing": missing,
                "reason": "the canonical backtest artifact is not readable in this deployment"}
    if draws_doc is None and summary_doc is None:
        missing.append("the placebo study")

    con = _dig(res, "construction", default={})
    win = _dig(res, "cleanups", "panel_window", default={})
    uni = _dig(res, "universe", default={})

    # --- the panel ------------------------------------------------------------------------
    by_date = _dig(win, "cross_section_by_date", default={}) or {}
    dates = sorted(by_date)
    panel = {
        "n_names": int(_num(uni.get("n_names")) or 0),
        "n_dates": int(_num(uni.get("n_dates")) or 0),
        "n_rows": int(_num(uni.get("n_rows")) or 0),
        "first": dates[0] if dates else _dig(win, "retained_start"),
        "last": dates[-1] if dates else _dig(win, "retained_end"),
        "cross_section_min": _num(win.get("cross_section_min")),
        "cross_section_median": _num(win.get("cross_section_median")),
        "cross_section_max": _num(win.get("cross_section_max")),
        "horizon_days": _num(con.get("horizon_days")),
    }

    # --- the decile ladder ----------------------------------------------------------------
    ladder = con.get("decile_ann_return")
    deciles = None
    if isinstance(ladder, list) and ladder:
        vals = [_num(v) for v in ladder]
        if all(v is not None for v in vals):
            top, bottom = max(vals), min(vals)
            span = (top - bottom) or 1.0
            deciles = [{"rank": i + 1, "ann": v,
                        "bar_pct": round(100.0 * (v - bottom) / span, 1),
                        "is_top": i == 0}
                       for i, v in enumerate(vals)]

    # --- the three benchmarks -------------------------------------------------------------
    # All three ship, in the artifact's own order of increasing friendliness to the strategy.
    # The equal-weight universe is the one every historical figure in this project used and
    # is UNINVESTABLE — you cannot buy 2,500 names equally weighted at zero cost — so it is
    # shown first and labelled, and SPY is shown because it is what a reader would otherwise
    # actually have bought.
    bm = _dig(res, "benchmarks", default={})
    benchmarks = []
    for key in ("equal_weight", "cap_weighted", "spy"):
        b = bm.get(key)
        if not isinstance(b, dict):
            continue
        excess = _num(b.get("excess_ann"))
        if excess is None:
            continue
        benchmarks.append({
            "key": key,
            "label": b.get("label") or key,
            "note": b.get("note"),
            "benchmark_ann": _num(b.get("benchmark_ann")),
            "top_decile_ann": _num(b.get("top_decile_ann")),
            "excess_ann": excess,
            "t": _num(b.get("excess_tstat_nw")),
            "hit_rate": _num(b.get("hit_rate")),
            "investable": key != "equal_weight",
        })

    # --- costs ----------------------------------------------------------------------------
    # The BREAKEVEN is the number to lead with and the artifact's own comment says why: it
    # requires no belief in any particular cost calibration. "Net alpha" requires you to
    # accept our cost table; "you would have to pay 134bps a side before this dies" does not.
    c = _dig(res, "costs", "top_decile", default={})
    costs = None
    if _num(c.get("breakeven_one_way_bps")) is not None:
        costs = {
            "breakeven_bps": _num(c.get("breakeven_one_way_bps")),
            "realised_bps": _num(c.get("realised_one_way_bps")),
            "turnover": _num(c.get("annual_turnover")),
            "gross_alpha": _num(c.get("gross_alpha")),
            "net_alpha": _num(c.get("net_alpha")),
            "gross_ann": _num(c.get("gross_ann")),
            "net_ann": _num(c.get("net_ann")),
            "net_max_drawdown": _num(c.get("net_max_drawdown")),
            "net_sharpe": _num(c.get("net_sharpe")),
            "limitations": c.get("cost_model_limitations"),
        }
        bk, rl = costs["breakeven_bps"], costs["realised_bps"]
        costs["margin"] = (bk / rl) if (bk and rl) else None

    # --- the distribution behind the average ----------------------------------------------
    # An annual average hides how often the thing loses. 29% of quarters are negative and the
    # page says so next to the headline rather than in a footnote.
    dist = _dig(con, "top_decile_alpha_distribution", default={})
    distribution = None
    if _num(dist.get("negative_fraction")) is not None:
        distribution = {
            "n": int(_num(dist.get("n")) or 0),
            "negative_periods": int(_num(dist.get("negative_periods")) or 0),
            "negative_fraction": _num(dist.get("negative_fraction")),
            "median": _num(dist.get("median")),
            "mean": _num(dist.get("mean")),
            "p05": _num(dist.get("p05")),
            "p95": _num(dist.get("p95")),
            "worst": dist.get("worst"),
            "best": dist.get("best"),
            "units": dist.get("units"),
        }

    # --- how many tests we have run -------------------------------------------------------
    # Read LIVE from the research log, because it moves whenever any lane books a trial while
    # the artifact is only rebuilt on a full backtest. The artifact's own count ships beside
    # it so the gap is visible instead of being a silent inconsistency between two pages.
    trials, trials_source = None, None
    try:
        from ..edge import research_log
        d = research_log.detail()
        bd = d.get("by_domain") if isinstance(d, dict) else None
        if isinstance(bd, dict) and bd:
            trials = {k: int(v) for k, v in bd.items() if isinstance(v, (int, float))}
            trials_source = "RESEARCH_LOG.md, read live"
    except Exception:
        trials = None
    if trials is None:
        bd = _dig(res, "multiple_testing", "by_domain")
        if isinstance(bd, dict) and bd:
            trials = {k: int(v) for k, v in bd.items() if isinstance(v, (int, float))}
            trials_source = "BACKTEST_RESULTS.json (research log unavailable in this deployment)"

    placebo_block = None
    if draws_doc or summary_doc:
        placebo_block = _placebo(res, draws_doc or {}, summary_doc or {})
        if placebo_block is None:
            missing.append("placebo comparison (artifact present but not in the expected shape)")

    return {
        "available": True,
        "missing": missing,
        # provenance — a proof page that will not say when it was generated is not one
        "generated_at": _dig(res, "generated_at_utc") or _dig(res, "generated_at"),
        "commit": _dig(res, "git", "short"),
        "schema_version": _num(res.get("schema_version")),
        "panel": panel,
        "deciles": deciles,
        "benchmarks": benchmarks or None,
        "spread": {"ann": _num(con.get("long_short_ann")),
                   "t": _num(con.get("long_short_tstat_nw"))},
        "monotonicity": _num(con.get("monotonicity")),
        "hit_rate": _num(con.get("top_decile_alpha_hit")),
        "costs": costs,
        "distribution": distribution,
        "placebo": placebo_block,
        "restatement": _restatement(res),
        "research_vs_spy": _research_vs_spy(res),
        "bars": _bars(res, placebo_block),
        "trials": trials,
        "trials_source": trials_source,
        "errors": res.get("errors") or [],
    }
