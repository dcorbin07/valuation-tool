"""MA1 — the self-learning loop is disarmed, and every link in the chain is pinned.

Run: python tests/test_ma1_learning_disarmed.py

THE CHAIN THIS EXISTS TO KEEP BROKEN:

    auto-scan.yml monthly cron -> POST /admin/run-learning -> autolearn.run_learning
      -> store.save_learned(bucket, weights, adopted=True)
      -> screen._effective_weights prefers the learned row over settings.WEIGHTS_*

so a *scheduled job* could change the composite the live hot list, `/api/hotstocks` and the
Valquo Index are scored with, by writing a row into Render's database -- **no code commit, no
diff, no review**. `PAPER_TRACK_CONTRACT` Amendment 1 makes an adopted weight change a VINTAGE
EVENT that closes the current vintage and restarts the five-year clock; `track_meter.VINTAGES` is
a literal tuple in Python source, and there is no path from a SQLite row to it. The forward track
would have kept accruing under a vintage whose model had already changed -- the exact condition
vintage 1 was voided for.

THREE INDEPENDENT LOCKS, because any one of them can be undone by a plausible-looking edit:
  1. the cron is gone from the workflow (someone must re-add a schedule);
  2. `learn_enabled` defaults FALSE and fails closed (someone must set an env var);
  3. the adoption path REFUSES without an Amendment 1 vintage authorisation (someone must edit
     Python source, which is a commit with a diff).

Lock 3 is the load-bearing one: locks 1 and 2 can be reversed by a person with the Render
dashboard and no diff, lock 3 cannot.

THE GATE IS SHOWN TO FIRE, NOT ASSUMED TO. `test_the_gate_adopts_when_a_vintage_authorises_it`
is the positive control -- without it, every refusal test would pass on a learner that simply
never adopts anything, which is audit M3's known-bad-fixture point and the vacuity failure MA13
was written about.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import autolearn as AL                  # noqa: E402
from valuation.edge import track_meter as TM                # noqa: E402

WF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  ".github", "workflows", "auto-scan.yml")


# --------------------------------------------------------------------------- lock 1: the cron
def test_the_monthly_learning_cron_is_gone_from_the_workflow():
    import yaml
    with open(WF, encoding="utf-8") as f:
        raw = f.read()
    doc = yaml.safe_load(raw)

    # `on:` parses as the boolean True in YAML 1.1, which is why this reads doc[True].
    on = doc.get("on") or doc.get(True) or {}
    crons = [c["cron"] for c in (on.get("schedule") or [])]
    assert "0 12 1 * *" not in crons, f"the monthly self-learning cron is back: {crons}"

    assert "learn" not in doc["jobs"], "the `learn:` job is back in auto-scan.yml"

    # And no job may POST the endpoint, whatever it is called. Comments are stripped first so
    # that the explanatory block left in place does not satisfy its own test.
    live = "\n".join(l.split("#", 1)[0] for l in raw.splitlines())
    assert "/admin/run-learning" not in live, (
        "a workflow step POSTs /admin/run-learning again")

    # The other schedules must survive -- a disarm that quietly kills the hot list would pass a
    # test that only checked for absence.
    assert len(crons) >= 8, f"unrelated crons were lost in the disarm: {crons}"
    assert "23 22 * * 1-5" in crons, "the primary hot-list cron went missing"


# --------------------------------------------------------------------------- lock 2: the default
def test_learn_enabled_defaults_false_and_fails_closed():
    from valuation.config import Config

    saved = os.environ.pop("LEARN_ENABLED", None)
    try:
        assert Config().learn_enabled is False, "LEARN_ENABLED must default to FALSE"

        # Only the exact string "true" arms it; anything unrecognised fails CLOSED. The old
        # implementation was `!= "false"`, under which every one of these read TRUE.
        for val in ("yes", "1", "on", "TRUE-ish", "", "maybe", "0"):
            os.environ["LEARN_ENABLED"] = val
            assert Config().learn_enabled is False, f"{val!r} armed the learner"

        for val in ("true", "True", "TRUE"):
            os.environ["LEARN_ENABLED"] = val
            assert Config().learn_enabled is True, f"{val!r} should arm the learner"
    finally:
        os.environ.pop("LEARN_ENABLED", None)
        if saved is not None:
            os.environ["LEARN_ENABLED"] = saved


def test_learn_enabled_is_documented():
    """MA1 measured that LEARN_ENABLED appeared in no .md / .yml / .example file at all."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in (".env.example", "ENV_REFERENCE.md"):
        with open(os.path.join(root, name), encoding="utf-8") as f:
            body = f.read()
        assert "LEARN_ENABLED" in body, f"{name} does not document LEARN_ENABLED"
        assert "false" in body.lower(), f"{name} does not state the default"


# --------------------------------------------------------------------------- lock 3: the gate
def test_no_open_vintage_authorises_learned_weights_today():
    """The register is the gate. Today nothing in it authorises an adoption, and that is the
    state this file defends: if a vintage ever does authorise one, that must be a deliberate,
    reviewed commit -- and this test going red is how it announces itself."""
    for bucket in ("established", "speculative"):
        assert TM.learned_weight_authorisation(bucket) is None, (
            f"a vintage now authorises learned weights for {bucket} -- if that is intended, it "
            f"is a VINTAGE EVENT and must be registered, signed off and recorded as such")


def test_the_authorisation_helper_refuses_on_every_malformed_register():
    """A gate that cannot read its register must refuse, never guess."""
    d = TM._dt.date(2026, 1, 1)
    closed_but_authorising = [{"vintage": 9, "status": "CLOSED", "opened": d,
                               TM.LEARNED_WEIGHT_AUTHORISATION_KEY: True}]
    assert TM.learned_weight_authorisation("established", closed_but_authorising) is None, (
        "a spent authorisation on a CLOSED vintage must not license a later adoption")

    two_open = [{"vintage": 1, "status": "OPEN", "opened": d,
                 TM.LEARNED_WEIGHT_AUTHORISATION_KEY: True},
                {"vintage": 2, "status": "OPEN", "opened": d,
                 TM.LEARNED_WEIGHT_AUTHORISATION_KEY: True}]
    assert TM.learned_weight_authorisation("established", two_open) is None, (
        "an ambiguous register must refuse rather than pick one")

    assert TM.learned_weight_authorisation("established", []) is None
    assert TM.learned_weight_authorisation("established", [{"status": "OPEN", "opened": d}]) is None

    # Naming a DIFFERENT bucket must not authorise this one.
    other = [{"vintage": 1, "status": "OPEN", "opened": d,
              TM.LEARNED_WEIGHT_AUTHORISATION_KEY: ["speculative"]}]
    assert TM.learned_weight_authorisation("established", other) is None
    assert TM.learned_weight_authorisation("speculative", other) is not None


# --------------------------------------------------------------------------- the loop end to end
class _FakeStore:
    """Records what the learner tried to write. Deliberately not a real Store: this test is
    about the ADOPTION DECISION, and a real database would let a write succeed silently."""

    def __init__(self):
        self.saved = []

    def latest_learned_weights(self, bucket):
        return None                                   # nothing adopted yet -> falls back to base

    def save_learned(self, bucket, weights, stats, adopted, note):
        self.saved.append({"bucket": bucket, "weights": dict(weights), "stats": stats,
                           "adopted": bool(adopted), "note": note})


def _panel_that_will_adopt():
    """A panel engineered so `optimize_weights` ACCEPTS -- the positive control's fuel."""
    import numpy as np
    import pandas as pd
    from valuation.screener import settings as S

    rng = np.random.default_rng(7)
    factors = list(S.BUCKET_FACTORS["established"])
    rows = []
    for di in range(24):
        for t in range(40):
            r = {"date": f"2026-01-{di + 1:02d}", "ticker": f"T{t}", "bucket": "established"}
            for f in factors:
                r[f] = float(rng.normal())
            # A single factor genuinely predicts, so a re-weighting really is an improvement.
            r["fwd_ret"] = 0.05 * r[factors[0]] + 0.001 * float(rng.normal())
            rows.append(r)
    return pd.DataFrame(rows)


def test_the_gate_refuses_an_adoption_that_passed_its_out_of_sample_test():
    """THE CORE OF MA1. Passing out-of-sample is necessary and NOT sufficient."""
    cfg = type("C", (), {"learn_min_dates": 4, "learn_horizon_days": 21,
                         "learn_top_per_date": 60})()
    store = _FakeStore()
    report = AL.run_learning(cfg, store, panel=_panel_that_will_adopt())

    est = (report.get("buckets") or {}).get("established") or {}
    assert est.get("adopted") is False, "the gate did not refuse"
    assert est.get("refused") is True, "the refusal was not reported as a refusal"
    assert "Amendment 1" in (est.get("note") or ""), est.get("note")

    # Refusals are RECORDED, not silent: an adopted=False row carrying what WOULD have been
    # adopted, so `learning_history` distinguishes "found nothing" from "found something and was
    # refused". `latest_learned_weights` reads adopted=1 only, so the row is inert.
    assert store.saved, "the refusal wrote nothing at all"
    assert all(r["adopted"] is False for r in store.saved), (
        "something was written as ADOPTED despite the gate")
    written = [r for r in store.saved if r["bucket"] == "established"][0]
    assert written["stats"].get("refused_by") == "amendment_1_vintage_gate"
    assert written["stats"].get("would_have_adopted"), "the refused weights were not preserved"


def test_the_gate_adopts_when_a_vintage_authorises_it():
    """POSITIVE CONTROL. Without this, every test above would pass on a learner that can never
    adopt anything -- which is indistinguishable from a working gate and is exactly the vacuity
    failure M3 and MA13 exist to catch."""
    cfg = type("C", (), {"learn_min_dates": 4, "learn_horizon_days": 21,
                         "learn_top_per_date": 60})()
    store = _FakeStore()

    real = TM.VINTAGES
    try:
        TM.VINTAGES = tuple(
            dict(v, **({TM.LEARNED_WEIGHT_AUTHORISATION_KEY: ["established"]}
                       if v.get("status") == "OPEN" else {}))
            for v in real)
        assert TM.learned_weight_authorisation("established") is not None, "fixture did not arm"
        report = AL.run_learning(cfg, store, panel=_panel_that_will_adopt())
    finally:
        TM.VINTAGES = real

    est = (report.get("buckets") or {}).get("established") or {}
    assert est.get("adopted") is True, f"an authorised adoption was still refused: {est}"
    assert est.get("authorised_by_vintage"), "the adoption did not record its authorising vintage"
    adopted_rows = [r for r in store.saved if r["adopted"]]
    assert adopted_rows, "nothing was written as adopted"
    assert "authorised by vintage" in adopted_rows[0]["note"]

    # And the gate is closed again the moment the fixture is removed.
    assert TM.learned_weight_authorisation("established") is None


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
    print(f"\n{passed}/{len(tests)} MA1 disarm tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
