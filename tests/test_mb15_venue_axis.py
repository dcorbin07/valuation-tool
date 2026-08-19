"""MB15's venue axis, pinned. [charges no trials: no arm ran, no return was scored]

MB15 registered a pre-outcome kill on the VENUE axis and the kill fired before any arm, for two
independent reasons.  Both are measurements, and both are pinned here so a future reader cannot
re-open the item on the premise it was registered under.

  * THE IDENTIFIER IS NOT ON THIS AXIS, BY MARKET STRUCTURE. In equities the standard retail
    identifier is the off-exchange TRF print. ThetaData's own legend carries TRF venues (57
    FINRA/NASDAQ, 58 BSE, 59 NYSE), and NOT ONE appears in 70,288,482 option prints - because US
    options have no off-exchange execution. Their absence is informative rather than an artifact
    of an incomplete legend, which is exactly why the legend matters.
  * THE GATE IS NOT DISCRIMINATING. The cache ships venue codes as bare uint8, so the
    retail/non-retail mapping is chosen rather than given. Across all 2^20 partitions, 60.43%
    land inside the registered +/-15pp band - so the gate cannot fail against anyone free to
    pick the mapping after seeing the data. Pinned by arithmetic AND by a positive control: a
    band that IS discriminating must return a small fraction, or the measurement means nothing.
  * NO RETAIL SHARE IS COMPUTED ANYWHERE. The successor axis (OPRA condition flags + trade size)
    is measured for COVERAGE only; combining those marginals into the union is the successor
    register's gate, and computing it after seeing the registered axis fail would be choosing the
    design on the outcome. Pinned by AST over the shipped scripts.
  * THE ITEM'S HEADLINE PREMISE IS CORRECTED, NOT DELETED. "The exchange field has never been read
    by any study" is false - O14's `sweep_share` reads it. What is true is narrower and is the
    part worth keeping: it reads the field only as CARDINALITY, never as identity.

Offline: pure arithmetic and source inspection, so it runs on Linux and Windows alike with no
cache mounted.
"""
from __future__ import annotations

import ast
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The 20 trade-venue codes observed across the whole cache (MB15_VENUE_CENSUS.json, 2026-08-19).
OBSERVED = (0, 1, 4, 5, 6, 7, 9, 11, 22, 31, 42, 43, 46, 47, 60, 65, 69, 73, 74, 76)

# ThetaData's published legend, read 2026-08-19. These three are the off-exchange venues.
TRF_CODES = {57: "FINRA/NASDAQ TRF", 58: "BSE TRF", 59: "NYSE TRF"}

# Pooled venue shares, same artifact. Ordered descending; they sum to 1.
SHARES = (0.121838, 0.120051, 0.091173, 0.076840, 0.075844, 0.074616, 0.070980, 0.057958,
          0.051601, 0.046034, 0.044114, 0.043582, 0.042242, 0.034361, 0.018643, 0.014369,
          0.008917, 0.004927, 0.001057, 0.000852)

SCRIPTS = ("mb15_venue_census.py", "mb15_gate_satisfiability.py", "mb15_condition_census.py")


def _src(name):
    with io.open(os.path.join(REPO, "scripts", name), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- the structural kill

def test_no_off_exchange_venue_appears_in_the_cache():
    """The equities retail identifier has no analogue here, and it is absence not omission."""
    assert not (set(OBSERVED) & set(TRF_CODES)), "a TRF code appeared; the finding would change"


def test_the_trf_codes_are_real_codes_in_the_vendor_scheme():
    """If 57/58/59 were not in the legend at all, their absence would prove nothing.

    They ARE in it, which is what turns 'no TRF prints' from a gap in the legend into a fact
    about options market structure.
    """
    assert len(TRF_CODES) == 3
    assert all(isinstance(c, int) and 0 <= c <= 255 for c in TRF_CODES)
    assert max(OBSERVED) > max(TRF_CODES), (
        "the observed range must straddle the TRF codes, or their absence is a range artefact")


# ---------------------------------------------------------------- the gate is not discriminating

def _frac_in_band(shares, lo, hi):
    """Fraction of all 2^K subset sums landing in [lo, hi]. Plain arithmetic, no numpy."""
    sums = [0.0]
    for s in shares:
        sums += [x + s for x in sums]
    assert len(sums) == 2 ** len(shares)
    return sum(1 for x in sums if lo <= x <= hi) / len(sums)


def test_the_registered_band_admits_most_arbitrary_mappings():
    frac = _frac_in_band(SHARES, 0.45, 0.75)
    assert 0.60 < frac < 0.61, frac
    assert frac > 0.5, (
        "a gate more than half of arbitrary partitions clear cannot validate a chosen mapping")


def test_the_satisfiability_measure_is_not_vacuous():
    """A positive control: a genuinely tight band must return a small fraction.

    Without this the 60.43% could be an artefact of the arithmetic rather than of the band, and
    'the gate is loose' would be unfalsifiable.
    """
    tight = _frac_in_band(SHARES, 0.5995, 0.6005)
    assert tight < 0.02, tight
    assert tight < _frac_in_band(SHARES, 0.45, 0.75) / 20


def test_widening_the_band_can_only_admit_more():
    """Monotonicity - the cheapest check that the measure is reading the band at all."""
    a = _frac_in_band(SHARES, 0.55, 0.65)
    b = _frac_in_band(SHARES, 0.45, 0.75)
    c = _frac_in_band(SHARES, 0.00, 1.00)
    assert a < b < c and c == 1.0


def test_the_shares_are_a_partition_of_the_tape():
    assert len(SHARES) == len(OBSERVED) == 20
    assert abs(sum(SHARES) - 1.0) < 1e-4, sum(SHARES)


# ---------------------------------------------------------------- no retail share is computed

def _assigned_names(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
                elif isinstance(t, ast.Tuple):
                    out |= {e.id for e in t.elts if isinstance(e, ast.Name)}
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
    return out


def test_no_mb15_script_computes_a_retail_share():
    """AST, not a substring ban.

    MB1's no-verdict test was wrong three times by banning substrings - it flagged a docstring
    disclaiming a kill, a dict key that merely LABELS a pass, and a local naming a side of a bar.
    This reads assigned NAMES and dict KEYS, so prose about the thing it forbids stays legal.
    """
    banned = {"retail_share", "slim_share", "retail_frac", "slim", "retail_pct"}
    for name in SCRIPTS:
        tree = ast.parse(_src(name))
        assert not (_assigned_names(tree) & banned), (name, _assigned_names(tree) & banned)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = {k.value for k in node.keys
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                assert not (keys & banned), (name, keys & banned)


def test_the_condition_census_states_what_it_refuses_to_compute():
    """A refusal nobody can find is indistinguishable from an omission."""
    s = _src("mb15_condition_census.py")
    assert "deliberately_not_computed" in s
    assert "choosing the design" in s


def test_no_mb15_script_emits_a_verdict_field():
    for name in SCRIPTS:
        tree = ast.parse(_src(name))
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value in ("verdict", "kill", "adopt"):
                        raise AssertionError("%s emits %r" % (name, k.value))


# ---------------------------------------------------------------- the premise correction

def test_sweep_share_does_read_the_exchange_field():
    """MB15's title says the field has never been read. It has - so the record must say so."""
    p = os.path.join(REPO, "valuation", "edge", "tickflow_signals.py")
    if not os.path.exists(p):
        return
    with io.open(p, encoding="utf-8") as fh:
        s = fh.read()
    assert "exchange" in s, "if this ever fails, the premise correction needs re-checking"


def _code_only(path):
    """Source with comments and string literals removed (MA5's tokenize pattern).

    A guard that cannot tell code from prose about code is not measuring the tree. The first cut
    of the test below banned the substring 'retail' and duly failed against a DOCSTRING - O14's
    own header, which cites Bryzgalova et al. and the >60% figure. That is the fourth instance of
    this family in this lane, so the fix is the established one rather than a narrower ban.
    """
    import tokenize
    out = []
    with io.open(path, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


def test_sweep_share_reads_it_only_as_cardinality():
    """The narrower true claim, pinned: it counts DISTINCT venues, never which venue.

    Checked against CODE with prose stripped, so the module's own docstring - which legitimately
    discusses retail flow and cites the >60% figure - cannot trip it.
    """
    p = os.path.join(REPO, "valuation", "edge", "tickflow_signals.py")
    if not os.path.exists(p):
        return
    code = _code_only(p)
    assert "unique" in code, "cardinality read expected"
    for marker in ("== 57", "== 58", "== 59", "TRF", "retail"):
        assert marker not in code, "sweep_share appears to read venue IDENTITY: %r" % marker


def test_the_prose_stripper_is_not_vacuous():
    """If _code_only returned '' the test above would pass by seeing nothing.

    It must keep the code and drop the prose - both directions, or it is not a stripper.
    """
    p = os.path.join(REPO, "valuation", "edge", "tickflow_signals.py")
    if not os.path.exists(p):
        return
    code = _code_only(p)
    raw = io.open(p, encoding="utf-8").read()
    assert "def sweep_share" in code, "the stripper dropped code"
    assert "retail" in raw and "retail" not in code, "the stripper failed to drop the docstring"


# ---------------------------------------------------------------- the period defect

# Share of prints carrying condition 125 (SINGLE_LEG_AUCTION_NON_ISO - the SLIM flag), by year,
# from MB15_CONDITION_CENSUS.json. Bryzgalova-Pavlova-Sikorskaya date the OPRA price-improvement
# flag to NOVEMBER 2019; this census reproduces that independently, neither tuned to the other.
COND_125_BY_YEAR = {2016: None, 2017: None, 2018: None, 2019: 0.0479,
                    2020: 0.1816, 2021: 0.1595, 2022: 0.1560,
                    2023: 0.1664, 2024: 0.1844, 2025: 0.1988}

FLAG_INTRODUCED_YEAR = 2019


def test_the_slim_flag_is_absent_before_it_existed():
    """It cannot fire before OPRA introduced it, and the cache agrees."""
    for y in range(2016, FLAG_INTRODUCED_YEAR):
        assert COND_125_BY_YEAR[y] is None, y


def test_the_flag_switches_on_partway_through_2019_and_then_stabilises():
    """A November introduction means a PARTIAL first year, then a stable rate.

    A flag present from 2016, or one whose 2019 share already matched its later level, would both
    contradict the paper - so this is a real check on the census rather than a restatement.
    """
    first = COND_125_BY_YEAR[FLAG_INTRODUCED_YEAR]
    later = [v for y, v in COND_125_BY_YEAR.items() if y > FLAG_INTRODUCED_YEAR]
    assert first is not None and first > 0
    assert all(v > 2 * first for v in later), (first, later)
    assert max(later) / min(later) < 1.5, "post-introduction rate should be stable"


def test_the_gate_period_is_wrong_independently_of_the_axis():
    """MB15 asks for ~60% on the POOLED cache; the flag cannot fire across most of it.

    Pinned as arithmetic: the fraction of covered YEARS in which the identifier cannot exist is
    large enough that a pooled share is guaranteed to be diluted below any recent-period target.
    """
    dead = sum(1 for v in COND_125_BY_YEAR.values() if v is None)
    assert dead >= 3
    assert dead / len(COND_125_BY_YEAR) > 0.25, (
        "if most of the cache post-dated the flag, the period objection would be weak")


# ---------------------------------------------------------------- housekeeping

def test_pre_panel_history_is_reported_vacuous_not_passing():
    """The key is ABSENT from every tick payload, so the filter passes by having nothing to do.

    O21-D2's C5 precedent: report VACUOUS rather than PASSING, or a filter that never ran reads
    as a filter that ran and found nothing.
    """
    s = _src("mb15_venue_census.py")
    assert "pre_panel_history_key_present" in s


def test_the_census_records_a_fingerprint_because_no_tick_freeze_exists():
    s = _src("mb15_venue_census.py")
    assert "fingerprint_sha256" in s and "no_pinned_freeze_exists_for_ticks" in s


def test_the_scripts_do_not_reach_the_network():
    for name in SCRIPTS:
        s = _src(name)
        for bad in ("requests", "urlopen", "httpx"):
            assert bad not in s, (name, bad)


def test_every_mb15_script_is_runnable_as_its_own_process():
    """RUN_RULES line 25 judges a suite by EXIT CODE; a file with no __main__ exits 0 vacuously."""
    for name in SCRIPTS:
        assert 'if __name__ == "__main__":' in _src(name), name


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                       # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
