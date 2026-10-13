"""SELL-PREMIUM — THE ARM GATE. It REFUSES, and on 2026-10-12 it refused for real.

`PREREG_sellpremium.md`, committed ALONE at `2e9fe7b`. The register's §6 (inherited from the
draft) makes the four kills pre-outcome and says the arm runner **refuses without a passing
artifact**. **`K3` FIRED** — the measured strike distribution puts one crash at **8.90 years of
premium** against a bar of **6.0 fixed before it was computed** — so the program stops, the five
arms never run, and **the 5 options trials stay charged** (`E-1`, `MA6`: un-booking after watching
a kill fire is the shape this record distrusts most, and overstating `N` is the safe direction).

**WHY THE ARM BODIES ARE DELIBERATELY NOT WRITTEN HERE, stated rather than left to be noticed.**
`DIP-CALL` shipped its arm complete and unrun, and that was right because `DIP-CALL-2` executed
the same scoring path a day later and validated it. Nothing will execute these arms: a successor
needs its own blind register, and the five arms would reach it as **scoring code that has never
run against the panel and that no test can exercise end to end**. `V6-OPT`'s own docstring records
the cost of that — *"the scoring path has never executed against the panel; treat the first run as
an instrument build, with controls, not as a measurement."* **Unvalidated scoring sitting in the
tree under a register that forbids running it is worse than no scoring**, so what ships is the
gate, complete and exercised, and the arms are named as NOT BUILT.

**THE TWO REFUSAL STATES ARE DISTINCT** (`E-1`: a hard-coded refusal cannot tell *"the control
never ran"* from *"the control ran and fired"*), and a third is distinguished here — the kill pass
ran, some gates passed and one fired, which is this register's actual state.

Usage:  python -m scripts.sellpremium_arm
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                    # noqa: E402
from valuation.studies import sellpremium as SP                               # noqa: E402

PREFIX = "SELLPREMIUM"
ARMS = ("A1_delta_hedged", "A2_cash_secured", "A3p_strike_rule", "A4_health", "A5_random_day")


def require_kills(path: str = None) -> dict:
    """Returns the kill artifact, or REFUSES. Three distinct states, three distinct messages."""
    p = path or D.out_path("%s_KILLS.json" % PREFIX)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: %s is ABSENT. The free pre-outcome kill pass has NOT BEEN RUN, which is a "
            "different state from it having run and fired. Run "
            "`python -m scripts.sellpremium_kills` first and READ it (O10's process defect)." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    gates = k.get("gates") or {}
    if not gates:
        raise SystemExit(
            "REFUSING: %s carries no `gates` block. An artifact that records no verdict cannot "
            "be read as a passing one." % p)
    fired = sorted(g for g, v in gates.items() if not v)
    if fired:
        raise SystemExit(
            "REFUSING: the kill pass RAN and %d of %d gates FIRED: %s.\n"
            "  A kill firing stops the program at zero further trials. The bars were "
            "pre-committed and W-28 forbids relaxing one after watching it fail.\n"
            "  The %d gates that passed are NOT a licence to run the arms behind the one that "
            "did not.\n"
            "  The 5 options trials STAY CHARGED (E-1, MA6: overstating N is the safe "
            "direction)." % (len(fired), len(gates), ", ".join(fired),
                             len(gates) - len(fired)))
    return k


def main():
    print("SELL-PREMIUM arm gate — register PREREG_sellpremium.md (ALONE at 2e9fe7b)")
    print("arms the register names, NONE of which is built: %s" % ", ".join(ARMS))
    print("BH q=%.2f across k=%d FIXED; a firing kill does not shrink k (W-28)\n"
          % (SP.BH_Q, SP.BH_K))
    kills = require_kills()
    # Unreachable on the 2026-10-12 artifact, and kept so the refusal is a GATE rather than a
    # hard stop: if a successor's kill pass ever clears, this is where it would say so.
    raise SystemExit(
        "STOPPING: every gate passed (%s), and the arms are NOT BUILT in this register — see "
        "the module docstring. A successor that wants them must commit its own blind register "
        "first." % ", ".join(sorted(kills.get("gates") or {})))


if __name__ == "__main__":
    sys.exit(main())
