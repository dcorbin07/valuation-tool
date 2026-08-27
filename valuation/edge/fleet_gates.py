"""READ THE FLEET'S GATE FLAGS in the deployed image, where the licensed exports are not.

`.dockerignore` excludes `data/` WHOLESALE, and the fleet cycle runs on the Render service.
So a rule that reads a licensed export passes in a worktree and **fails on the service** --
the worst place to find out. `scripts/fleet_export_gates.py` reduces those exports to one
BOOLEAN PER NAME under `data_export/`, which is tracked and shipped; this module reads it.

**THREE STATES, NEVER TWO.** `True`, `False` and `None`, and `None` is the important one:

    unknown gate    -- the artifact does not carry this gate at all
    unknown ticker  -- the gate exists and this name was not in its cross-section
    stale gate      -- the gate exists and its `as_of` is older than the caller allows

**AN UNKNOWN IS NEVER A PASS AND IS NEVER A FAIL. THE CALLER DECIDES, EXPLICITLY.** A book
whose declaration says *"MA28 0-of-3"* must SKIP a name it cannot evaluate, and a book that
counts skips must be able to count them -- which is why `gate()` returns `None` rather than a
bool, and why nothing here offers a `default=`. **`MB8`'s finding is the general form: the
bucket a rule cannot evaluate is a real bucket, and it is not the safe one.** `MA28`'s own
`crash_flag` fails OPEN on a missing outcome and `I-3` had to add a coverage report to make
that visible; this module refuses to repeat it.

**STALENESS IS REPORTED, NOT HIDDEN, AND IT IS PER GATE.** The MA28 flags are a QUARTERLY
compute and E-4's tail panel ends months earlier still. Both stamp their own `as_of`, and a
single top-level timestamp would have averaged two different vintages into one reassuring
number. For F-4 and F-10 the quarterly cadence IS the rule -- their declarations say *"at the
latest quarterly compute"* -- so `age_days` is a disclosure, not automatically a fault.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

SCHEMA = "fleet_gates/1"
ARTIFACT_REL = os.path.join("data_export", "fleet_gates.json")

UNKNOWN_GATE = "UNKNOWN_GATE"
UNKNOWN_TICKER = "UNKNOWN_TICKER"
STALE = "STALE"

#: A FOURTH unknown, and it is `L3`'s. The caller did not declare a staleness bar, so this
#: module does not know whether the vintage it is holding is fit for the question being asked.
#:
#: IT USED TO BE A SILENT SKIP. `max_age_days` had no default -- correctly, because inventing
#: one is exactly how `MA5` measured the Harvey-Liu-Zhu bar freezing at 3.0 for months -- but
#: omitting it simply BYPASSED the staleness test and returned the bit. So the one caller most
#: likely to be wrong (the one that never thought about vintage at all) was the one caller that
#: got an unqualified answer.
#:
#: Refusing to default and refusing to answer without a declaration are the same rule; only the
#: second one is enforceable. A caller that genuinely wants no bar says so with `NO_BAR`, which
#: is still a declaration and still leaves a trace in the code that asked for it.
BAR_NOT_DECLARED = "BAR_NOT_DECLARED"

#: The explicit opt-out. `gate(..., max_age_days=NO_BAR)` reads the bit at any vintage, and the
#: sentinel is deliberately not `None`: forgetting an argument and choosing to ignore vintage
#: must not be spelled the same way.
NO_BAR = "NO_BAR"

OK = "OK"


def repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def artifact_path(root: str = None) -> str:
    return os.path.join(root or repo_root(), ARTIFACT_REL)


def load(root: str = None) -> dict:
    """The artifact, or an explicit ABSENT marker. Never raises on a missing file.

    A cycle must be able to report *"the gates artifact has not been exported"* as a state.
    Raising would make an un-exported artifact indistinguishable from a broken one, and the
    two need different fixes.
    """
    path = artifact_path(root)
    try:
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
    except OSError:
        return {"ok": False, "absent": True, "path": path,
                "reason": "no gates artifact; run python -m scripts.fleet_export_gates "
                          "where the licensed exports live"}
    except ValueError as e:
        return {"ok": False, "absent": False, "path": path,
                "reason": "gates artifact is not valid JSON: %s" % e}
    if payload.get("schema") != SCHEMA:
        return {"ok": False, "absent": False, "path": path,
                "reason": "gates artifact schema is %r, expected %r"
                          % (payload.get("schema"), SCHEMA)}
    return {"ok": True, "absent": False, "path": path, "payload": payload,
            "gates": payload.get("gates") or {}}


def as_of(name: str, root: str = None) -> Optional[str]:
    g = (load(root).get("gates") or {}).get(str(name)) or {}
    return g.get("as_of")


def age_days(name: str, today=None, root: str = None) -> Optional[int]:
    """How old this gate's compute is, in calendar days. `None` if the gate is absent."""
    stamp = as_of(name, root)
    if not stamp:
        return None
    try:
        d = _dt.date.fromisoformat(str(stamp)[:10])
    except ValueError:
        return None
    return int(((today or _dt.date.today()) - d).days)


def gate(name: str, ticker: str, *, max_age_days: int = None, today=None,
         root: str = None) -> dict:
    """One gate for one name. Returns `{"value", "state", "as_of", "age_days", "reason"}`.

    `value` is `True`, `False` or **`None`**, and `state` says which of the FOUR unknowns
    produced a `None` so a caller can count them apart.

    **THE BAR IS REQUIRED, NOT MERELY UN-DEFAULTED.  [L3]**  `max_age_days` still has no
    default -- inventing one is how `MA5` measured the HLZ bar freezing at 3.0 -- but omitting
    it no longer BYPASSES the staleness test and returns the bit anyway. It returns
    `BAR_NOT_DECLARED` and no value. Measured on the shipped artifact when this changed:
    `evt_clean` was **304 days** old and `ma28_clean` **211**, with no consumer anywhere in the
    tree, so the only reader this could break is one that had not thought about vintage.

    A caller that genuinely wants the bit at any age passes `max_age_days=NO_BAR`. That is
    still a declaration, and it leaves a trace at the call site where a reviewer will see it.
    """
    res = load(root)
    out = {"value": None, "state": UNKNOWN_GATE, "as_of": None, "age_days": None,
           "reason": res.get("reason", "")}
    if max_age_days is None:
        out["state"] = BAR_NOT_DECLARED
        out["reason"] = ("no staleness bar was declared for gate %r. Pass max_age_days=<int>, "
                         "or max_age_days=NO_BAR to read it at any vintage." % name)
        return out
    if not res["ok"]:
        return out
    g = (res["gates"] or {}).get(str(name))
    if not g or g.get("absent"):
        out["reason"] = (g or {}).get("reason") or ("no gate named %r in the artifact" % name)
        return out
    out["as_of"] = g.get("as_of")
    out["age_days"] = age_days(name, today=today, root=root)
    if max_age_days != NO_BAR and out["age_days"] is not None \
            and out["age_days"] > int(max_age_days):
        out["state"] = STALE
        out["reason"] = ("gate %s is %d days old against a caller bar of %d"
                         % (name, out["age_days"], int(max_age_days)))
        return out
    tick = (g.get("tickers") or {}).get(str(ticker).upper())
    if tick is None:
        out["state"] = UNKNOWN_TICKER
        out["reason"] = ("%s was not in %s's cross-section on %s"
                         % (str(ticker).upper(), name, g.get("as_of")))
        return out
    out["value"] = bool(tick)
    out["state"] = OK
    out["reason"] = ""
    return out


#: Licensed exports a fleet rule might reach for. NONE of these may exist in the image, and
#: the audit asserts their ABSENCE rather than trusting `.dockerignore` to have been read.
LICENSED_PATHS = (
    os.path.join("data", "bulk", "events.csv"),
    os.path.join("data", "backtest", "insiders.csv"),
    os.path.join("data", "bulk", "fundamentals.csv"),
    os.path.join("data", "free_analysis", "E5_FLAGS.pkl"),
    os.path.join("data", "free_analysis", "E4_TAIL_PANEL.pkl"),
)


def image_audit(root: str = None) -> dict:
    """WHAT THIS PROCESS ACTUALLY SEES — run it where the runner runs, not where you test.

    **THE LESSON THIS EXISTS FOR IS ONE THIS LANE PAID FOR FOUR TIMES.** Licensed exports, the
    declarations, the git binary and `read_meter`'s file were each present everywhere the code
    was TESTED and absent where it RUNS, and every one was invisible to a green local suite.
    So the claim *"only a bit leaves the licensed store"* is not asserted from a worktree — it
    is measured **in the image, by the image**, and returned so a dispatch can print it.

    **BOTH DIRECTIONS, because either alone is satisfiable by an accident:**

      * **POSITIVE** -- the derived gates ARE present and readable here, with their counts and
        vintages. Without this the audit would pass on a process that shipped nothing at all.
      * **NEGATIVE** -- **not one licensed export exists on this filesystem**, checked by
        probing for the files themselves rather than by reading `.dockerignore`. A rule that
        reads `data/` cannot be silently working off a stray copy.

    **AND THE TYPE CENSUS IS THE STRUCTURAL HALF.** Every value in every gate is counted by
    Python type. A boolean cannot carry a vendor row; a float could carry a Beneish M and a
    string could carry anything. The census is returned in full so the number is READ rather
    than trusted, and `non_bool` is the one field an alert should key on.
    """
    res = load(root)
    out = {"artifact_present": bool(res.get("ok")), "reason": res.get("reason", ""),
           "gates": {}, "type_census": {}, "non_bool": 0,
           "licensed_present": [], "licensed_checked": len(LICENSED_PATHS)}
    base = root or repo_root()
    for rel in LICENSED_PATHS:
        if os.path.exists(os.path.join(base, rel)):
            out["licensed_present"].append(rel.replace("\\", "/"))
    if not res.get("ok"):
        # THE EARLY RETURN MUST STILL CARRY `ok` AND `verdict`. The first cut did not, so a
        # MISSING artifact raised `KeyError` in any caller that checked the audit's own verdict
        # -- and the one caller is the runner's door, where an exception is the loudest
        # possible way to report the quietest possible fact. A failure path that fails
        # DIFFERENTLY from the success path is not a failure path.
        out["ok"] = False
        out["verdict"] = "AUDIT FAILED: no gates artifact in this process -- " + out["reason"]
        return out
    for name, g in (res.get("gates") or {}).items():
        ticks = g.get("tickers") or {}
        out["gates"][name] = {"n": len(ticks), "as_of": g.get("as_of")}
        for v in ticks.values():
            t = type(v).__name__
            out["type_census"][t] = out["type_census"].get(t, 0) + 1
            if not isinstance(v, bool):
                out["non_bool"] += 1
    out["ok"] = (out["artifact_present"] and out["non_bool"] == 0
                 and not out["licensed_present"])
    out["verdict"] = (
        "ONLY BOOLEANS LEFT THE LICENSED STORE, and no licensed export exists in this process"
        if out["ok"] else
        "AUDIT FAILED: " + ("; ".join(filter(None, [
            "" if out["artifact_present"] else "no gates artifact",
            ("%d non-boolean values in the gates" % out["non_bool"]) if out["non_bool"] else "",
            ("licensed exports PRESENT: " + ", ".join(out["licensed_present"]))
            if out["licensed_present"] else ""]))))
    return out


def coverage(root: str = None, *, max_age_days=None, today=None) -> dict:
    """What the artifact carries, for a cycle to report without opening it.

    `O21-D2`'s `C5` precedent: an ABSENT artifact and a PRESENT-but-empty one must not read
    the same, so an empty gate is reported VACUOUS rather than as coverage of zero names.

    **AND IT SAYS WHETHER THE VINTAGES ARE FIT FOR ANYTHING.  [L3]**  `age_days` alone is a
    number a reader has to judge; `stale` is the judgement, against a bar THE CALLER declares.
    With no bar declared every `stale` is `None` and `bar_declared` is False -- which is the
    honest report, not a clean one, and is what stops an old artifact being quoted as current
    by a surface that never asked how old it was.

    THE BAR IS NOT DEFAULTED HERE EITHER, for `MA5`'s reason, and this function is the place a
    default would have been most tempting: it is the one a status page calls.
    """
    res = load(root)
    if not res["ok"]:
        return {"ok": False, "reason": res.get("reason", ""), "gates": {},
                "bar_declared": max_age_days is not None, "max_age_days": max_age_days,
                "n_stale": None}
    out, n_stale = {}, 0
    for name, g in (res["gates"] or {}).items():
        if g.get("absent"):
            out[name] = {"present": False, "reason": g.get("reason", ""), "stale": None}
            continue
        n = len(g.get("tickers") or {})
        age = age_days(name, today=today, root=root)
        stale = None
        if max_age_days is not None and max_age_days != NO_BAR and age is not None:
            stale = age > int(max_age_days)
            n_stale += bool(stale)
        out[name] = {"present": True, "as_of": g.get("as_of"), "n_tickers": n,
                     "vacuous": n == 0, "age_days": age, "stale": stale}
    return {"ok": True, "reason": "", "gates": out,
            "bar_declared": max_age_days is not None, "max_age_days": max_age_days,
            "n_stale": (n_stale if max_age_days is not None and max_age_days != NO_BAR
                        else None)}
