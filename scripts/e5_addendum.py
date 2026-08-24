"""E-5 addendum -- POST-HOC DIAGNOSTICS, NO VERDICT. `PREREG_e5_hazard_curve.md` §7/§8.

**Nothing here can change the verdict.** The register's grammar is a conjunction of three legs
fixed before the run; this file recomputes no leg and reads no new outcome. It exists because
running the item surfaced one honest limitation of the L2 bar and one reading of L3 that a
consumer will want and the arm's artifact does not spell out.

THE LIMITATION, STATED RATHER THAN LEFT TO BE NOTICED
------------------------------------------------------
L2's bar is the within-date flag-permutation p95, which is the right null for *"does the flag
carry anything at all"* -- under it `HR(k)` is about 1 at every quarter and the decay statistic
is centred near zero. It is NOT calibrated at the alternative the statistic is actually
measured under, where `HR(1)` is about 3: a ratio's sampling variance grows with the ratio, so
the permutation `sd` can understate the decay statistic's real sampling error.

That cuts AGAINST the verdict's L2 leg, so it is measured rather than argued. The delta-method
standard error of `HR = h_f / h_k` under the OBSERVED rates is

    Var(HR) ~ HR^2 * (1/E_f + 1/E_k)

with `E` the event counts, and the front/back difference is taken at independence, which is
CONSERVATIVE here: the two windows share names, and a positive correlation between them would
make the difference's variance SMALLER than the sum. So the reported sigma is a floor on the
precision, never a flattering one.

THE READING L3 NEEDS
---------------------
L3 failed at 0.5701 against 0.60. The arm's own per-quarter excess counts say why, and the
reason is not the flag: the KEPT base rate nearly doubles from quarter 1 to quarter 2, because
a two-quarter cumulative window has more room to reach -50% than a one-quarter window does. So
the excess COUNT can stay flat while the RATIO falls. Both readings ship, because the two named
consumers want different ones -- a card quotes the ratio, an option tenor is chosen on where
the excess events are.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.edge import power_gate as PG                         # noqa: E402


def ratio_se(ratio: float, e_f: int, e_k: int) -> float:
    """Delta-method se of a ratio of two rates, from the EVENT counts."""
    return float(ratio) * math.sqrt(1.0 / max(1, int(e_f)) + 1.0 / max(1, int(e_k)))


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms-json", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    with io.open(a.arms_json, encoding="utf-8") as fh:
        arm = json.load(fh)

    out = {
        "item": "E-5", "kind": "POST-HOC DIAGNOSTIC, NO VERDICT",
        "register": "PREREG_e5_hazard_curve.md",
        "verdict_is_unchanged": arm["verdict"],
        "why_this_file_exists": (
            "L2's permutation bar is calibrated at HR ~ 1 and the statistic is measured at "
            "HR ~ 3; a ratio's sampling variance grows with the ratio, so the null sd can "
            "understate the decay's real sampling error. Measured here rather than argued, "
            "because it cuts against the leg that passed."),
        "windows": {},
    }

    for w, W in arm["windows"].items():
        fr, bk = W["front"], W["back"]
        se_f = ratio_se(fr["ratio"], fr["event_flagged"], fr["event_kept"])
        se_b = ratio_se(bk["ratio"], bk["event_flagged"], bk["event_kept"])
        se_d = math.sqrt(se_f ** 2 + se_b ** 2)
        dec = float(W["decay"])
        out["windows"][w] = {
            "front_ratio": fr["ratio"], "front_events_flagged": fr["event_flagged"],
            "front_events_kept": fr["event_kept"], "front_se": se_f,
            "back_ratio": bk["ratio"], "back_events_flagged": bk["event_flagged"],
            "back_events_kept": bk["event_kept"], "back_se": se_b,
            "decay": dec, "decay_se_independent": se_d,
            "decay_sigma": dec / se_d if se_d else None,
            "detection_threshold_50pct_power_at_crit_2": PG.detection_threshold(se_d, crit=2.0),
            "mde_at_80pct_power_at_crit_2": (2.0 + PG.Z_POWER_CONVENTION) * se_d,
            "note": ("independence between the front and back windows is CONSERVATIVE -- they "
                     "share names, and a positive correlation would shrink this variance"),
        }

    ex = arm["windows"]["full_sample"]["excess"]["per_quarter_excess"]
    per_q = arm["windows"]["full_sample"]["per_quarter"]
    out["why_L3_failed_while_L2_passed"] = {
        "per_quarter_excess_crash_count": ex,
        "kept_base_rate_by_quarter": {k: per_q[k]["pooled"]["rate_kept"] for k in per_q},
        "hazard_ratio_by_quarter": {k: per_q[k]["pooled"]["ratio"] for k in per_q},
        "reading": (
            "The RATIO falls monotonically while the excess COUNT peaks in quarter 2, because "
            "the KEPT base rate itself roughly doubles from quarter 1 to quarter 2 -- a "
            "cumulative-window effect, not a property of the flag. A card quotes the ratio; an "
            "option tenor is chosen on where the excess EVENTS are, and those are not "
            "front-loaded."),
    }
    out["consumers"] = {
        "risk_card": ("the elevation is real, largest in the first quarter and still about 1.9x "
                      "four quarters out -- it fades, it does not vanish. Quote the ratio and "
                      "BOTH rates, never the difference (crash_gate's measured rule)."),
        "O1_put_tenor": ("NOT SUPPORTED as a short-tenor argument. Quarters 3 and 4 together "
                         "still carry about 43% of the four-quarter excess crash count, and the "
                         "single largest quarter is the SECOND. 'Flags decay, therefore buy "
                         "short-dated' is the inference this item refutes."),
        "scope": ("PANEL, not book. MB8 measured this flag firing on 3.56% of the top-decile "
                  "book and catching one crash of eighty-four; nothing here transfers to it."),
    }

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with io.open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    for w, r in out["windows"].items():
        print(f"[{w}] decay {r['decay']:.4f} +/- {r['decay_se_independent']:.4f} "
              f"= {r['decay_sigma']:.2f} sigma  (80% MDE at crit 2 "
              f"{r['mde_at_80pct_power_at_crit_2']:.4f})")
    print(f"[addendum] -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
