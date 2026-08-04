# HANDOFF — deep research thread #2: the cross-section of option returns

`OPTIONS_DEEP_RESEARCH.md` thread #2. Pre-specified module committed at `64955ef` **before** the
panel was built; every published sign was declared up front. Full run completed 2026-08-03.

**VERDICT: REJECT. Nothing clears the gate. One characteristic sorts BACKWARDS from the
literature.** No adoption, no follow-on run recommended on this data.

---

## 1. What was tested, and why this instrument

The published basis, one line each, with the sign declared **before** any sort:

| characteristic | source | published prediction |
|---|---|---|
| `iv_rv` | Goyal–Saretto (2009) | high IV/RV → **lower** option returns (the variance risk premium cross-section) |
| `idio_vol` | Cao–Han (2013) | high idiosyncratic vol → **lower** delta-hedged option returns |
| `idio_skew` | Boyer–Vorkink | high expected idiosyncratic skewness → **lower** returns (lottery preference) |
| `vol_of_vol` | vol-of-vol risk premium | high vol-of-vol → **lower** returns |
| `smile_slope` | put-skew richness (weak prior) | steep skew → **lower** returns |
| `illiq` | **MECHANICAL CONTROL, never a discovery** | wide spreads → lower returns *by construction*, since returns are net of spread |

Every sign is `+1` = "high predicts lower returns", so Q1 (low characteristic) should earn the
most. **A cross-sectional sort has two ends; a study that picks which end to go long after seeing
the numbers wins half the time by construction.** That is why the signs are in the module and
pinned by a test.

**Instrument:** a one-month ATM straddle, bought at the **ask on both legs**, held to expiry and
settled at intrinsic against the underlying. Three deliberate choices:

- **Both legs pay the ask.** A straddle crosses two spreads at entry — the most spread-punished
  instrument in this project. Marking either leg at the mid would manufacture most of any result.
- **Held to expiry, settled at intrinsic.** This carries thread #1's lesson directly: the
  simulator marks a position that outlives its last usable quote at that stale quote, higher than
  the truth in 94.7% of cases. Holding to expiry removes the mark entirely — there is only a
  payoff. (That defect is now fixed in production too, as audit item **B3**.)
- **Straddle, not Cao–Han's delta-hedged call.** Stated as a deviation up front: their instrument
  needs roughly a million IV solves. A straddle is delta-neutral at inception, which is the
  property the test needs.

**Two further deviations, stated before the run:** the market proxy is the equal-weighted daily
return of the universe, because the Sharadar equity export carries no ETFs; and `vol_of_vol` is
computed off the 60-DTE ATM-IV series while the instrument is ~30 DTE.

## 2. The panel

**3,373 straddles · 242 names · 117 months · 2016-02 → 2025-10.** Full mined universe (284 names
scored), aggression 1.0, **not a smoke test.**

```
mean return  +0.0568     median  -0.1636     total losses  1.16%
median spread 0.0841     median DTE 28
```

The median is deeply negative while the mean is positive — exactly the shape a long-straddle book
should have, and the reason every statistic below is read on monthly means across a wide
cross-section rather than on any pooled average.

**COVERAGE FIRST, per the standing rule:** `iv_rv` 99.4%, `idio_vol` 99.0%, `idio_skew` 99.0%,
`vol_of_vol` 99.9%, `smile_slope` 82.1%, `illiq` 100.0%. Nothing is empty; no result below is a
coverage artefact. (The 12-name smoke test earlier showed `idio_vol`/`idio_skew` at 0.0% because
`build_market` requires ≥20 names per date — the guard working, correctly.)

## 3. Results — quintile mean straddle returns, Q1 = LOW characteristic

| characteristic | Q1 | Q2 | Q3 | Q4 | Q5 | monotonicity | Q1 excess | t | months | both halves | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `iv_rv` | +0.039 | +0.017 | +0.091 | +0.157 | +0.030 | **+0.20** | −0.0272 | −0.69 | 71 | no | **no** |
| `idio_vol` | +0.033 | +0.033 | +0.049 | +0.109 | +0.110 | **+0.90** | −0.0331 | −0.70 | 71 | no | **no — CONTRADICTS** |
| `idio_skew` | +0.100 | −0.047 | +0.053 | +0.194 | +0.041 | 0.00 | +0.0340 | +0.68 | 71 | yes | **no** |
| `vol_of_vol` | +0.056 | +0.148 | +0.076 | +0.006 | +0.028 | −0.60 | −0.0084 | −0.20 | 71 | no | **no** |
| `smile_slope` | +0.019 | +0.027 | +0.090 | −0.023 | +0.090 | +0.20 | −0.0223 | −0.50 | 63 | no | **no** |
| `illiq` | +0.109 | +0.047 | +0.182 | +0.013 | −0.015 | −0.70 | +0.0446 | +1.06 | 71 | yes | **no — control** |

Monotonicity is Spearman across the five quintile means against the characteristic. **−1.0 is the
ideal** (returns falling as the characteristic rises, i.e. the published direction); **+1.0 is
backwards.**

**Multiplicity:** BH-FDR at q = 0.10 across all six, one-sided in the predicted direction —
**zero discoveries.** Smallest p is `illiq` at 0.291, then `idio_skew` at 0.499; the other four sit
at 1.000, which is what a one-sided screen returns when the sort runs the wrong way.
**PBO 41.4%** over 70 CSCV splits of the characteristic × time-block grid (passes the <50% bar,
but on a grid where nothing was worth selecting).

## 4. What this actually says

**`iv_rv` — Goyal–Saretto does not replicate here.** Monotonicity **+0.20**: there is no ordering
at all, in either direction. Q4 is the best quintile and Q5 is near the bottom. This is the
headline null of the thread, and it is the characteristic with the strongest published prior.

**`idio_vol` — CONTRADICTS Cao–Han, and clearly.** Monotonicity **+0.90** is a strong, clean sort
running **opposite** to the published sign: in this panel, high-idiosyncratic-vol names' straddles
earned *more*, not less (+0.110 for Q5 against +0.033 for Q1). Per the module's own rule S2 this
is reported as a **contradiction of the literature**, not re-signed into a result. A +0.90 sort is
the kind of thing that would be extremely tempting to flip and call a discovery; the sign was
declared before the panel existed precisely so that is not available.

Two honest caveats on that contradiction, both of which cut against reading anything into it:
the instrument is a straddle rather than Cao–Han's delta-hedged call, and a long straddle on a
high-idio-vol name is a *directional volatility* bet in a way a delta-hedged position is not. The
sign difference may be the instrument, not the market.

**`idio_skew` and `illiq` sort in the predicted direction and still fail.** Both clear the
both-halves check and both have the right sign, but `t` = +0.68 and +1.06 against a `MIN_T` of
2.0, and neither is monotone enough. `illiq` **cannot be adopted under any statistics** — it is
carried as a mechanical control, because returns here are net of spread so a wide-spread name must
earn less by construction. That it sorts at all (mono −0.70, the cleanest in the table) is the
reassuring result: it says the panel is measuring what it thinks it is.

**`vol_of_vol` and `smile_slope` are nulls.** `vol_of_vol` has the right sign (−0.60) and no
magnitude (t −0.20); `smile_slope` has neither, on the thinnest coverage (82.1%, 63 months).

## 5. The verdict, and what does not follow from it

**REJECT. Zero adoptions, zero FDR discoveries, one contradiction of a published result.**

What this does **not** license: it does not say the variance risk premium is not real. It says
that **on 242 names over 117 months, in one-month ATM straddles bought at the ask and held to
expiry, none of six published cross-sectional sorts survives**. The published studies use larger
universes, delta-hedged instruments, and in Goyal–Saretto's case a longer sample.

The long-short Q1−Q5 statistics are computed and shipped but **were never the basis of any verdict
here, and must not become one**: the short leg is a naked short straddle, which is unlimited risk
and not permitted in this account. The gate reads the long-only Q1 excess only, and the key is
literally named `long_short_NOT_INVESTABLE` so it cannot be quoted by accident.

## 6. Standing on the thread

The mandate's framing was that since the entry signal is dead, any edge most likely lives in the
exit, the sizing, or the cross-section of *which* options. Thread #1 said the exit is not it — and
found a simulator bug that was faking one. Thread #2 says the cross-section is not it either, at
least not through these six characteristics on this universe.

**Note on B1:** the external edge audit found that five call sites across the options codebase fed
a split- and dividend-adjusted close into option maths. **This module is not affected** — it uses
`bars.get("raw_close")` for every option calculation. Thread #1 and roadmap 22c *are* affected and
need re-running; this one does not.

**Next thread is #3, "The VRP done RIGHT"** — which is worth reading against this result before it
is run, since thread #2 is the cheap version of the same question and it rejected.

## 7. Reproduce

```
python optxs_run.py --data-root <repo>/data --iv-series --panel --workers 6
python optxs_run.py --data-root <repo>/data          # re-analyse the banked panel
```

Panel banked at `data/options_xsection/panel.pkl`; results at
`data/options_xsection/XSECTION_RESULTS.json`. 10 pre-registration tests in `tests/test_edge.py`
(`test_xsection_*`) pin the decisions that would otherwise let a two-ended sort produce a winner by
construction — the declared signs, both legs at the ask, intrinsic settlement, thin-date dropping,
the monotonicity bar, the uninvestable long-short, and `illiq`'s control-only status.
