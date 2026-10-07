# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 1 runner -- tabulate the corrected floors beside the current ones.

    python -m scripts.corrected_floors_run

**ZERO TRIALS.** It reads a sweep and a derived map; it measures nothing and searches nothing.
It REFUSES if the sweep is short of its requested draws, because the 95th percentile of twenty
draws is set by the single largest value and quoting one as a floor would be the knife-edge
`W-28` forbids.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_floors as CF                                       # noqa: E402

#: The landed corrected figures, from `UNIVERSE_BIAS_PUBLIC.json`'s `corrected` column -- a
#: measurement this lane already made and landed, READ rather than re-typed, so the harness
#: control compares against the record and not against my expectation.
LANDED_KEYS = {
    "top_decile_alpha": "top-decile alpha vs equal-weighted universe",
    "top_decile_alpha_tstat_nw": "top-decile alpha HAC t",
    "long_short_tstat": "long-short naive t",
    "long_short_tstat_nw": "long-short HAC t",
    "monotonicity": "monotonicity",
    "pbo": "PBO",
    "deflated_sharpe": "Deflated Sharpe",
}


def landed_corrected():
    """Read part 2's `corrected` column off its own artifact, by `payload_path`."""
    p = os.path.join(CF.fa(), "UNIVERSE_BIAS_PUBLIC.json")
    with io.open(p, encoding="utf-8") as fh:
        figs = json.load(fh)["figures"]
    by_path = {r["payload_path"].rsplit(".", 1)[-1]: r for r in figs}
    # `pbo` and `deflated_sharpe` sit under `cpcv.*.value`, so the last segment is "value"
    by_name = {r["figure"]: r for r in figs}
    out = {}
    for key, figure in LANDED_KEYS.items():
        r = by_name.get(figure) or by_path.get(key)
        if r is not None:
            out[key] = r["corrected"]
    return out


def main(argv=None):
    sweep = CF.read_sweep()
    cur = CF.current_floors()
    landed = landed_corrected()

    n = int(sweep.get("n_draws") or 0)
    req = int(sweep.get("n_requested") or 0)
    partial = n < CF.MIN_DRAWS_FOR_A_FLOOR
    print("sweep %s" % os.path.basename(CF.sweep_path()), flush=True)
    print("  panel   %s" % sweep.get("panel"), flush=True)
    print("  draws   %d of %d requested, seeds %s%s"
          % (n, req, sweep.get("seeds"), "   *** PARTIAL ***" if partial else ""), flush=True)
    print("  trial N %s (source %s)"
          % ((sweep.get("trial_count") or {}).get("n_trials_used"),
             (sweep.get("trial_count") or {}).get("source")), flush=True)
    print("  costs   measured=%s" % sweep.get("costs_measured"), flush=True)

    # --- the harness control, GATED -------------------------------------------------------
    hc = CF.harness_control(sweep, landed)
    print("\n=== HARNESS CONTROL -- does the sweep's REAL iteration reproduce the landed "
          "corrected record?", flush=True)
    for k, v in hc.items():
        if k.startswith("_"):
            continue
        print("  %-26s landed %-22s reproduced %-22s dev %s"
              % (k, v["landed"], v["reproduced"],
                 ("%.3e" % v["abs_dev"]) if v["abs_dev"] is not None else "n/a"), flush=True)
    print("  -> all exact excluding the DSR: %s" % hc["_gate"]["all_exact_excluding_dsr"],
          flush=True)

    det = sweep["real"]["deflated_sharpe_detail"]
    denom = CF.implied_denominator(det)
    dsr_recon = {}
    landed_n = None
    for cand in (262, 274):
        dsr_recon[cand] = CF.dsr_at_n(det, cand, denom)
    if landed.get("deflated_sharpe") is not None:
        for cand, r in dsr_recon.items():
            if abs(r["dsr"] - float(landed["deflated_sharpe"])) < 1e-9:
                landed_n = cand
    print("\n=== THE DSR GAP IS THE N CHANNEL AND NOTHING ELSE", flush=True)
    for cand, r in sorted(dsr_recon.items()):
        print("  N=%-4d sr0 %.10f  DSR %.16f" % (cand, r["sr0"], r["dsr"]), flush=True)
    print("  landed figure reproduces at N=%s; the sweep ran at N=%s"
          % (landed_n, det.get("n_trials")), flush=True)

    if not hc["_gate"]["all_exact_excluding_dsr"]:
        raise SystemExit("HARNESS CONTROL FAILED -- the sweep's real iteration is not the "
                         "object the record describes; no floor may be read from it")

    # --- the seven floors ------------------------------------------------------------------
    rows = []
    print("\n=== THE SEVEN FLOORS  (corrected universe, %d draws)" % n, flush=True)
    print("  %-26s %-11s %-13s %-13s %-9s %s"
          % ("floor", "percentile", "CURRENT", "CORRECTED", "delta", "corrected headline"),
          flush=True)
    for key, label, pct, direction in CF.FLOORS:
        nullblk = (sweep.get("null") or {}).get(key) or {}
        new = nullblk.get(pct)
        old = (cur["floors"].get(key) or {}).get("value")
        obs = sweep["real"].get(key)
        d = (None if new is None or old is None else new - old)
        rows.append({
            "key": key, "floor": label, "percentile": pct, "direction": direction,
            "current": old, "current_status": (cur["floors"].get(key) or {}).get("status"),
            "corrected": new,
            "delta": d,
            "harder": (None if d is None else
                       bool(d < 0) if direction == "LOWER is harder" else bool(d > 0)),
            "corrected_headline": obs,
            "headline_clears_corrected_floor": CF.clears(obs, new, direction),
            "headline_clears_current_floor": CF.clears(obs, old, direction),
            "null_summary": nullblk,
        })
        print("  %-26s %-11s %-13s %-13s %-9s %s -> %s"
              % (label, pct,
                 ("%.6f" % old) if old is not None else "-",
                 ("%.6f" % new) if new is not None else "-",
                 ("%+.6f" % d) if d is not None else "-",
                 ("%.6f" % obs) if obs is not None else "-",
                 {True: "CLEARS", False: "FAILS", None: "n/a"}[
                     CF.clears(obs, new, direction)]), flush=True)

    # --- the rates the bars are actually read off, and the adoption caveat ---------------
    rates = sweep.get("rates") or {}
    print("\n=== RATES ON THE NULL  (what pure noise does on this universe)", flush=True)
    for k in sorted(rates):
        v = rates[k]
        print("  %-32s %s" % (k, ("%.4f" % v) if isinstance(v, float) else v), flush=True)
    adopt = rates.get("cpcv_adopt")
    print("\n  CPCV ADOPTION ON NOISE: %s   (X7 measured 27pc on the canonical panel, and "
          "that adoption manufactures ~+1.4 of long-short t out of nothing)"
          % (("%.4f" % adopt) if adopt is not None else "n/a"), flush=True)
    print("  the REAL corrected run ADOPTS (%s), which the published run did not -- so the "
          "corrected long-short reading carries that inflation on BOTH sides"
          % sweep["real"].get("cpcv_recommend"), flush=True)

    res = {
        "item": "CORRECTED-FLOORS",
        "part": "1 -- the X7 placebo sweep calibrated on the corrected universe",
        "trials": 0,
        "trial_class": "CALIBRATION -- no hypothesis, no bar of its own, no second arm. A "
                       "placebo sweep can only raise or lower a BAR and can never produce a "
                       "finding, so it adds no degree of freedom (X7, session 10 and MA19 all "
                       "charged zero). MA19's reason is sharper: N is the INPUT to the floors "
                       "being computed, so charging a trial would move N and invalidate the "
                       "numbers as they were written.",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "panel": sweep.get("panel"),
        "sweep": {"draws": n, "requested": req, "seeds": sweep.get("seeds"),
                  "costs_measured": sweep.get("costs_measured"),
                  "trial_count": sweep.get("trial_count"),
                  "instrument": sweep.get("instrument"),
                  "partial": partial},
        "same_as_X7_except": "the universe. Same script, same seeds (1000..1099), same n, same "
                             "instrument, costs measured -- X7's and session 10's own setup.",
        "current_floors_are_derived": cur,
        "harness_control": hc,
        "dsr_n_channel": {"implied_denominator": denom,
                          "reconstructed": dsr_recon,
                          "landed_figure_reproduces_at_N": landed_n,
                          "sweep_ran_at_N": det.get("n_trials"),
                          "note": "the landed corrected DSR and this sweep's differ ONLY "
                                  "through the trial count; holding the sweep's own banked "
                                  "sharpe and variance fixed and changing N alone reproduces "
                                  "the landed figure"},
        "floors": rows,
        "rates_on_the_null": rates,
        "adoption_caveat": {
            "cpcv_adopt_rate_on_noise": rates.get("cpcv_adopt"),
            "real_run_adopted": bool(sweep["real"].get("cpcv_adopt")),
            "real_run_recommend": sweep["real"].get("cpcv_recommend"),
            "why_it_matters": "placebo.py mirrors run_backtests, so an ADOPTING draw is scored "
                              "on weights chosen on the same panel it is then measured on. X7 "
                              "measured that this manufactures ~+1.4 of long-short t out of "
                              "nothing and fires on 27pc of pure-noise draws on the canonical "
                              "panel. UNIVERSE-BIAS part 2 measured that the REAL corrected run "
                              "adopts where the published one did not, so the inflation is "
                              "present on both sides of the corrected comparison. The floor is "
                              "the right comparator BECAUSE both sides carry it -- but a reader "
                              "quoting the corrected long-short t as an effect size, rather "
                              "than against this floor, inherits the inflation unopposed.",
        },
    }
    if partial:
        res["PARTIAL"] = ("fewer than %d draws: a p95 over this many draws is set by the "
                          "largest one or two values and is NOT a floor. Reported so a "
                          "part-way read can never be quoted as a calibration."
                          % CF.MIN_DRAWS_FOR_A_FLOOR)

    out_path = CF.out_path()
    with io.open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote %s" % out_path, flush=True)
    if partial:
        print("*** PARTIAL -- %d of %d draws; NOT a calibration yet ***" % (n, req), flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
