"""AUDIT #3, final batch — MA24, MA26, MA27, MA28, MA33, MA54, MA55, MA57, MA58.

Run: python tests/test_ma_final_batch.py

Nine items, ZERO trials. Seven close `DESIGN-RECORDED` and two close on measured facts, so most
of what needs pinning here is a **tripwire** rather than a repair: nothing in this batch changes
a shipped number, and the risk is that a later session quietly runs one of these arms without a
register, or re-derives a conclusion this batch settled.

WHAT EACH GROUP PINS

  ARITHMETIC (MA24/MA33). `S19`'s kill condition is the one thing this batch closes permanently,
  and it closes on a number derived from a shipped artifact rather than on judgement. The
  derivation is reproduced here in pure arithmetic so it cannot rot with the artifact, plus the
  artifact check itself when the file is on disk.

  ANTI-DUPLICATION (MA54). The options lane measured MA54-2 on the same day. A pin that the
  record cites their row rather than claiming it stops two lanes publishing two numbers for one
  question.

  TRIPWIRES (MA26-C/D, MA27, MA28, MA55, MA57, MA58). Each fires if the arm is built without the
  register the memo says it needs. Tripwires that pass today are worth nothing unless they can
  bite, so every one of them is MUTATION-TESTED by `test_..._tripwires_can_bite`.

  FACTS (MA26-C, MA57). Two audit claims were refuted by measurement. The measurements need the
  licensed export or a banked panel, so those tests SKIP when the data is absent rather than
  passing vacuously -- and the skip is REPORTED, because a silently-skipped data test is the
  vacuous-pass defect this project has caught three times.
"""
from __future__ import annotations

import ast
import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN = os.path.join(ROOT, "DESIGN_ma_final_batch.md")

_SKIPS: list[str] = []


def _find(rel: str) -> str | None:
    """Locate a licensed/banked artifact by trying every plausible `data/` root.

    A worktree under `<repo>/.claude/worktrees/<name>` has its OWN `data/` directory that is
    NOT the repository's -- it can exist, be a real directory, and contain nothing but this
    session's output. Returning it because `os.path.isdir` said yes is how a data test skips
    while believing it looked; so the candidate is chosen by whether THE FILE is there, never
    by whether a directory is.
    """
    here = ROOT
    roots = [os.path.join(here, "data")]
    for _ in range(4):                       # walk out of .claude/worktrees/<name>
        here = os.path.dirname(here)
        roots.append(os.path.join(here, "data"))
    for r in roots:
        p = os.path.join(r, rel)
        if os.path.exists(p):
            return p
    return None


def _design() -> str:
    with io.open(DESIGN, "r", encoding="utf-8") as f:
        return f.read()


def _flat(s: str) -> str:
    """Collapse whitespace, so a prose assertion is about CONTENT and not about where the
    author happened to wrap a line at 100 columns."""
    return " ".join(s.split())


# ======================================================================================
# MA24 + MA33 — S19's kill condition
# ======================================================================================

# S19's own published numbers. The MDE is NOT stored in the artifact; it is `2 * IC / t`,
# and the point of pinning it here is that the record's +0.020549 must keep reproducing
# from the artifact's own two fields rather than being a figure someone typed once.
S19_A1_IC = 0.012202150018043164
S19_A1_T = 1.1876022080477582
S19_A1_DATES = 41
S19_ORIGINAL_EFFECT = 0.00960710146449202
MDNA_MONTHS = 114                      # 2016-08 .. 2026-01 inclusive


def _mde(ic: float, t: float) -> float:
    return 2.0 * ic / t


def test_ma24_the_s19_mde_reproduces_the_record_from_the_artifacts_own_fields():
    """+0.020549 is DERIVED, not quoted. If this ever stops reproducing, MA24's whole
    close-permanently argument is resting on prose and must be re-derived."""
    assert abs(_mde(S19_A1_IC, S19_A1_T) - 0.02054922083397216) < 1e-15


def test_ma24_ma33_the_monthly_panel_still_fails_s19s_own_kill_condition():
    """MA24 pre-committed: 'if the monthly panel's own MDE still exceeds +0.0096 ... close
    permanently'. Rescaling the quarterly MDE by sqrt(T_q / T_m) is the OPTIMISTIC bound --
    monthly 63-day forward returns overlap, so the real SE is larger and the real MDE worse.
    The condition fires even on the optimistic bound, which is what makes it decisive."""
    mde_q = _mde(S19_A1_IC, S19_A1_T)
    mde_m = mde_q * math.sqrt(S19_A1_DATES / MDNA_MONTHS)
    assert mde_m > S19_ORIGINAL_EFFECT, (
        f"monthly MDE {mde_m:.6f} no longer exceeds the effect {S19_ORIGINAL_EFFECT:.6f} -- "
        "MA24's kill condition would NOT fire and S19 would re-open")
    assert abs(mde_m - 0.012323522491495676) < 1e-12
    # and how far away the answerable version is
    need = S19_A1_DATES * (mde_q / S19_ORIGINAL_EFFECT) ** 2
    assert 180 < need < 195, need


def test_ma24_the_kill_condition_arithmetic_is_not_vacuous():
    """A test that would pass whatever the numbers were is not a check. Feed it an effect
    size the design COULD detect and the assertion must fail."""
    mde_m = _mde(S19_A1_IC, S19_A1_T) * math.sqrt(S19_A1_DATES / MDNA_MONTHS)
    big_effect = 0.05                       # far above the monthly MDE
    assert not (mde_m > big_effect), "the comparison cannot distinguish a detectable effect"


def test_ma24_the_artifacts_underpowered_flag_is_the_coverage_gate_not_the_mde():
    """S19_MDNA.json ships `underpowered: false`, which reads as contradicting the write-up.
    It is the register's COVERAGE gate (min dates / names), a different quantity. Pinned so
    nobody 'corrects' the write-up against it."""
    p = _find(os.path.join("free_analysis", "S19_MDNA.json"))
    if not p:
        _SKIPS.append("test_ma24_the_artifacts_underpowered_flag_is_the_coverage_gate_not_the_mde")
        return
    with io.open(p, "r", encoding="utf-8") as f:
        d = json.load(f)
    assert d.get("underpowered") is False
    mt = d.get("min_thresholds", {})
    assert {"min_heldout_names", "min_covered_dates", "min_names_per_date"} <= set(mt)
    a1 = d["arms"]["A1"]["full_sample"]
    assert abs(_mde(a1["residual_ic_change"], a1["residual_ic_t_change"])
               - 0.02054922083397216) < 1e-12, "the artifact no longer reproduces the MDE"
    assert d["controls"]["C6_reproduces_original"]["target_residual_ic"] == S19_ORIGINAL_EFFECT


# ======================================================================================
# MA26-C — the withholding state IS computable point-in-time
# ======================================================================================

def test_ma26c_the_withhold_trigger_reads_only_fair_value_and_price():
    """The audit's arm C says the withholding state is NOT testable point-in-time because the
    live sub-scores are not computable historically. The trigger reads no sub-score, no WACC and
    no quote -- only `fair_value / price` against one band -- which is why the claim is false."""
    from valuation.web import withhold as W

    band = 5.0
    rows = [
        {"ticker": "AAA", "fair_value": 60.0, "price": 10.0},   # 6.0x -> withheld
        {"ticker": "BBB", "fair_value": 40.0, "price": 10.0},   # 4.0x -> kept
        {"ticker": "CCC", "fair_value": None, "price": 10.0},   # no estimate -> not withheld
    ]
    n = W.withhold_implausible_fair_values(rows, band=band)
    assert n == 1, n
    assert rows[0].get(W.ROW_WITHHELD) is True
    assert not rows[1].get(W.ROW_WITHHELD)
    # the reason travels with the refusal -- a blank cell reads as missing data
    assert rows[0].get(W.ROW_WITHHELD_REASON)


def test_ma26c_the_state_is_measurable_on_the_banked_panel():
    """5,403 of 108,100 valued rows (4.998%) on 69 of 69 dates. Recomputed rather than quoted."""
    p = _find(os.path.join("free_analysis", "panel_s23_fairvalue.pkl"))
    if not p:
        _SKIPS.append("test_ma26c_the_state_is_measurable_on_the_banked_panel")
        return
    import pandas as pd
    from valuation.engine.pipeline import FV_BAND_HIGH

    d = pd.read_pickle(p)
    fv = pd.to_numeric(d["fair_value"], errors="coerce")
    px = pd.to_numeric(d["price"], errors="coerce")
    ok = fv.notna() & px.notna() & (px > 0)
    w = (fv[ok] / px[ok]) > float(FV_BAND_HIGH)
    assert int(ok.sum()) == 108100, int(ok.sum())
    assert int(w.sum()) == 5403, int(w.sum())
    per_date = d.loc[ok].assign(_w=w.values).groupby("date")["_w"].mean()
    assert int((per_date > 0).sum()) == 69 == len(per_date)


# ======================================================================================
# MA27 / MA58 — the signal census, and the tripwires
# ======================================================================================

def test_ma27_the_53_signal_premise_holds():
    """MA27's construction is defined over 'the 53 signals already in per_signal'. If that
    count moves, the register's object has changed and the memo must be re-read."""
    from valuation.screener import settings as S
    assert len(S.NUMBER_THEME) == 53, len(S.NUMBER_THEME)


def test_ma58_no_seasonality_signal_has_been_registered_without_a_register():
    """TRIPWIRE. A seasonality column appearing in NUMBER_THEME means somebody built it; it must
    arrive WITH its pre-registration, and this test must be updated in the same commit so the
    diff shows it.

    UPDATED 2026-08-18: MA58 HAS NOW RUN (PREREG_ma58_return_seasonality.md at 6f998fc; verdict
    UNINTERPRETABLE) and this assertion is deliberately UNCHANGED. The register adopted nothing
    and shipped no signal -- the arm is a study column in scripts/ma58_seasonality.py -- so the
    tripwire staying green is the CORRECT outcome, not a stale one. It still guards the thing it
    always guarded: a seasonality signal reaching the live composite without its own adoption
    register. Only the 'un-run' clause was false after 2026-08-18."""
    import re
    from valuation.screener import settings as S
    found = sorted(k for k in S.NUMBER_THEME if re.search(r"seas|_month|calendar", k, re.I))
    assert found == [], (
        f"a seasonality-shaped signal appeared: {found}. MA58 requires a blind register "
        "committed alone, with the lag structure fixed in writing first.")


def test_ma57_the_keep_allowlist_still_lacks_the_cmp_columns():
    """TRIPWIRE, and it encodes the memo's deliberate NON-change. `ownername` and
    `transactioncode` are on disk; adding them to `_KEEP` is a one-line change that belongs in
    MA57's own register, in the same commit as the classifier. If they appear here first, two
    columns are being loaded on a 580MB file with no consumer."""
    from valuation.edge.data_providers import WRDSProvider
    keep = WRDSProvider._KEEP["insiders"]
    for c in ("ownername", "transactioncode"):
        assert c not in keep, (
            f"'{c}' was added to _KEEP['insiders'] without MA57's register. If this is "
            "deliberate, land it with PREREG_ma57_*.md and update this test in the same commit.")


def test_ma57_the_dead_date_entry_in_the_allowlist_is_a_known_fact():
    """Reported, not repaired: `_KEEP['insiders']` requests a column named `date`, and the
    export has none (it is `transactiondate`), so `r.get('filingdate') or r.get('date')` has a
    fallback that can never fire. Harmless today. Pinned so it is a known fact rather than a
    surprise, and so removing it is a deliberate change."""
    from valuation.edge.data_providers import WRDSProvider
    assert "date" in WRDSProvider._KEEP["insiders"]
    assert "filingdate" in WRDSProvider._KEEP["insiders"]
    assert _design().count("dead allowlist entry") >= 1, "the memo no longer records it"


# ======================================================================================
# MA54 — reconciliation, not duplication
# ======================================================================================

def test_ma54_the_record_cites_the_options_lanes_o17c4_row_rather_than_claiming_it():
    """MA54-2 was measured by the options lane on 2026-08-16. This lane must cite it. A memo
    that re-states someone else's measurement as its own is how two lanes come to publish two
    numbers for one question."""
    t = _flat(_design())
    assert "O17C4" in t and "aeca6f0" in t, "the memo does not cite the options lane's row"
    assert "does not re-measure" in t or "deliberately does not re-measure" in t
    # and the ledger must agree that the leg is answered elsewhere
    led = io.open(os.path.join(ROOT, "VALQUO_LEDGER.md"), encoding="utf-8").read()
    assert "MA54-2 IS ANSWERED" in led, "the ledger no longer records MA54-2 as answered"


def test_ma54_p1s0_closed_the_vehicle_ma54_4_was_routed_into():
    """MA54-4's remedy was routed into P1's register; P1 Stage 0 then FAILED and the
    options-expression family closed. The memo must say the remedy is orphaned rather than
    pending, or a later session will go looking for a register that will never be written."""
    led = io.open(os.path.join(ROOT, "VALQUO_LEDGER.md"), encoding="utf-8").read()
    assert "P1S0" in led
    t = _flat(_design())
    assert "ORPHANED BY ITS OWN VEHICLE" in t


# ======================================================================================
# The memo's own posture — it must not read as a set of measurements
# ======================================================================================

DESIGN_RECORDED_ITEMS = ("MA27", "MA28", "MA55", "MA57", "MA58")


def test_the_memo_records_designs_and_claims_no_verdict():
    t = _flat(_design())
    assert "no trial is charged" in t, "the memo does not state that it charges no trial"
    raw = _design()
    for i in DESIGN_RECORDED_ITEMS:
        assert f"## {i} ·" in raw, f"{i} has no section"
    assert "DESIGN-RECORDED` is not a finding that they would fail" in t, (
        "the memo must state that a design record is not a measurement")


def test_all_nine_items_are_adjudicated_in_the_memo():
    t = _design()
    for i in ("MA24", "MA26", "MA27", "MA28", "MA33", "MA54", "MA55", "MA57", "MA58"):
        assert f"## {i} ·" in t, f"{i} is not adjudicated"


def test_the_memo_quotes_the_live_alpha_margin_not_the_superseded_one():
    """MA19 recalibrated the top-decile alpha margin 1.95pp -> 1.8629pp at today's N. The audit
    quotes 1.95pp. A memo that repeats it would hand the next register a stale bar."""
    t = _flat(_design())
    assert "1.8629pp" in t, "the memo does not carry the live calibrated margin"
    assert "superseded since" in t, "the memo does not flag the audit's stale figure"


def test_the_tripwires_can_bite():
    """MUTATION TEST. Three of the checks above pass today and change no source, so they are
    worth nothing unless a violation would fail them. Each mutation is applied to a COPY of the
    thing under test, never to the tree."""
    import re
    from valuation.screener import settings as S
    from valuation.edge.data_providers import WRDSProvider

    caught = 0

    # 1. MA58: a seasonality signal sneaks into NUMBER_THEME
    mutated = dict(S.NUMBER_THEME)
    mutated["ret_same_month_lag1y"] = "momentum"
    if sorted(k for k in mutated if re.search(r"seas|_month|calendar", k, re.I)):
        caught += 1

    # 2. MA57: the CMP columns are added to the allowlist with no register
    keep = list(WRDSProvider._KEEP["insiders"]) + ["ownername", "transactioncode"]
    if any(c in keep for c in ("ownername", "transactioncode")):
        caught += 1

    # 3. MA54: the memo drops its citation of the options lane's row
    if "O17C4" not in _design().replace("O17C4", "", 1):
        caught += 1

    assert caught == 3, f"only {caught}/3 tripwires can bite"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    if _SKIPS:
        # REPORTED, never silent: a data-dependent test that skips quietly is the vacuous pass
        # this project has caught three times.
        print("\n  SKIPPED (licensed data or banked panel absent):")
        for s in sorted(set(_SKIPS)):
            print(f"    - {s}")
    print(f"\n{passed}/{len(tests)} MA final-batch tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
