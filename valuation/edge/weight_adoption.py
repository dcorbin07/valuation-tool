"""Master audit MA1/MA3 — a learned weight may reach the live scoring path ONLY the way S14 did.

WHAT THIS EXISTS TO STOP, stated as the audit found it. `auto-scan.yml` ran a monthly cron into
`/admin/run-learning`, which ran `autolearn.run_learning`, which called `save_learned(...,
adopted=True)`, which `screen._effective_weights` then PREFERRED over `settings.WEIGHTS_*`. Every
link was real, tested and shipped. So a scheduled job could change the composite users receive,
by writing a row into Render's own SQLite, with **no code commit, no diff, no review** — and
`PAPER_TRACK_CONTRACT` §5a's vintage rule would never have noticed, because `track_meter.VINTAGES`
is a literal tuple in Python source and there is no path from a database row to it. The forward
track would have kept accruing under the old vintage while the model underneath it changed: the
exact condition Amendment 1 VOIDED vintage 1 for.

THE ASYMMETRY THAT DECIDES THE DESIGN. A wrong REFUSAL costs a month of not re-tuning weights that
CPCV has declined to adopt on every run this project has ever done. A wrong ADOPTION silently
invalidates the forward test, which is the project's only out-of-sample evidence and costs five
years to rebuild. Those are not comparable, so this fails CLOSED in every direction: an
unreadable contract, an absent register key, a malformed row, a signature naming a different
vintage, and any exception at all all read NOT AUTHORISED.

WHY TWO INDEPENDENT FACTS, AND WHY BOTH LIVE IN TRACKED FILES. Authorisation requires

  (1) the OPEN vintage in `track_meter.VINTAGES` to carry a `weights_adoption` key naming the
      bucket — i.e. the adoption was REGISTERED as the vintage event itself, which is what puts
      it under the shadow-vintage machinery (`shadow_vintage.py`), and

  (2) a row in `PAPER_TRACK_CONTRACT.md` signed by Don naming that same vintage:

          | Learned weights adopted | YES - vintage 5 - 2026-09-01 |

Both are TRACKED SOURCE. Reaching either takes a commit, a diff and the auto-land gate. Neither is
reachable by a cron with an admin token writing to a database, which is precisely the hole MA1
found. Requiring BOTH means neither a lane editing Python nor a human editing markdown can ship a
weight alone.

THE SIGNATURE NAMES A VINTAGE ON PURPOSE. A bare `YES` would authorise the first adoption and then
every later one forever — a signature that outlives what it signed. Tying it to the open vintage's
NUMBER means the next adoption needs its own vintage and its own row, so Rule 6's five-year clock
reset is paid consciously each time rather than once.

WHAT THIS DOES NOT DO. It does not judge whether a weight is any good — that is MA2's gate, which
the same audit found uncalibrated (`optimize.py`). It does not delete or rewrite anything already
in a database: an adopted row written before this landed stays exactly where it is and is
REPORTED by `live_override_report`, because a live vintage violation is a finding to disclose with
dates, not something to erase on the way past.
"""

from __future__ import annotations

import datetime as _dt

# The contract row that carries Don's signature. Deliberately a DIFFERENT field from
# `index_track.GATE_FIELD` — the operational gate is about whether the track is being RECORDED
# properly and says nothing about weights; reusing it would let one signature answer two
# unrelated questions.
CONTRACT_FIELD = "learned weights adopted"
REGISTER_KEY = "weights_adoption"

# The canonical row, quoted here so the docstring and the parser cannot drift apart.
CONTRACT_ROW_EXAMPLE = "| Learned weights adopted | YES - vintage <n> - <date> |"


class VintageRefusal(RuntimeError):
    """Raised when something tries to adopt a live weight without a registered vintage.

    Loud on purpose. The alternative — quietly downgrading the write to `adopted=0` — is how a
    caller comes to believe it shipped something it did not, and a self-learning loop that
    believes it adopted is exactly the object this audit item is about.
    """


def _contract_values(field: str, path: str = None) -> list:
    """Every value cell of a `| field | value |` row matching `field`, in file order.

    Reuses `index_track`'s token rule and path rather than re-deriving them: two parsers for one
    contract is how a signature comes to mean different things to different readers. Fenced
    blocks are skipped and blockquote markers stripped, so the contract can DOCUMENT the
    canonical row (as this module's docstring does) without that example authorising anything.
    """
    from ..screener import index_track as IT

    p = path or IT.contract_path()
    with open(p, encoding="utf-8") as fh:
        text = fh.read()

    want = " ".join(field.lower().split())
    out, fenced = [], False
    for line in text.splitlines():
        s = line.strip()
        while s.startswith(">"):
            s = s[1:].strip()
        if s.startswith("```"):
            fenced = not fenced
            continue
        if fenced or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key = " ".join(cells[0].replace("*", "").lower().split())
        if key == want:
            out.append(cells[1])
    return out


def _signed_vintage(value: str):
    """The vintage number a signature authorises, or None if it authorises nothing.

    `YES - vintage 5 - 2026-09-01` -> 5. A missing or hedged verdict token, or a value naming no
    vintage, returns None — never a default, because "signed but I could not tell which vintage"
    must not read as "signed for the one that happens to be open".
    """
    from ..screener import index_track as IT

    if IT._verdict_token(value or "") not in IT.GATE_YES:
        return None
    low = (value or "").lower()
    if "vintage" not in low:
        return None
    tail = low.split("vintage", 1)[1]
    digits = ""
    for ch in tail.strip():
        if ch.isdigit():
            digits += ch
        elif digits:
            break
        elif ch not in " -:#":
            return None
    return int(digits) if digits else None


def authorisation(bucket: str, vintages=None, contract_path: str = None) -> dict:
    """Is a live-weight adoption for `bucket` authorised right now?

    `vintages` and `contract_path` are injectable so a test can prove this reaches AUTHORISED as
    well as REFUSED. A gate that has only ever been shown to say no is not a gate — it is
    indistinguishable from `return False`, and V1's register makes the same demand of itself
    (HARMED must be exactly as reachable as CONFIRMED-LIVE).
    """
    out = {"authorised": False, "bucket": bucket, "registered": False, "signed": False,
           "vintage": None, "signed_vintage": None, "reason": "",
           "checked_at": _dt.datetime.utcnow().isoformat()}
    try:
        if vintages is None:
            from . import track_meter as TM
            vintages = TM.VINTAGES
        live = [v for v in vintages if v.get("status") == "OPEN"]
        if len(live) != 1:
            out["reason"] = (f"expected exactly one OPEN vintage, found {len(live)} — the vintage "
                             f"register is not in a state that can authorise anything")
            return out
        v = live[0]
        out["vintage"] = v.get("vintage")

        entry = v.get(REGISTER_KEY)
        buckets = tuple((entry or {}).get("buckets") or ())
        if not entry:
            out["reason"] = (f"vintage {out['vintage']} carries no {REGISTER_KEY!r} entry, so no "
                             f"learned-weight adoption was registered as its vintage event")
            return out
        if bucket not in buckets:
            out["reason"] = (f"vintage {out['vintage']} registers a weight adoption for "
                             f"{list(buckets)!r}, which does not include {bucket!r}")
            return out
        out["registered"] = True

        vals = _contract_values(CONTRACT_FIELD, contract_path)
        signed = [_signed_vintage(x) for x in vals]
        signed = [s for s in signed if s is not None]
        out["signed_vintage"] = signed[-1] if signed else None
        if not signed:
            out["reason"] = (f"the vintage register authorises this, but no signed "
                             f"{CONTRACT_FIELD!r} row names a vintage in PAPER_TRACK_CONTRACT.md "
                             f"(expected {CONTRACT_ROW_EXAMPLE})")
            return out
        if out["signed_vintage"] != out["vintage"]:
            out["reason"] = (f"the signature names vintage {out['signed_vintage']} and the open "
                             f"vintage is {out['vintage']} — a signature does not carry forward "
                             f"to an adoption it was not written for")
            return out
        out["signed"] = True
    except Exception as e:                    # fail closed: an unreadable authority authorises nothing
        out["reason"] = f"could not establish authorisation ({type(e).__name__}: {e})"
        return out

    out["authorised"] = True
    out["reason"] = (f"registered as vintage {out['vintage']}'s vintage event and signed for "
                     f"vintage {out['signed_vintage']} in PAPER_TRACK_CONTRACT.md")
    return out


def require(bucket: str, vintages=None, contract_path: str = None) -> dict:
    """`authorisation`, but raises `VintageRefusal` when the answer is no."""
    a = authorisation(bucket, vintages=vintages, contract_path=contract_path)
    if not a["authorised"]:
        raise VintageRefusal(
            f"REFUSED: a learned weight for {bucket!r} may not reach the live scoring path. "
            f"{a['reason']}. Adopting a weight is a VINTAGE EVENT (PAPER_TRACK_CONTRACT §5a) and "
            f"resets the forward track's clock, so it takes a registered vintage carrying a "
            f"{REGISTER_KEY!r} entry AND Don's signed row {CONTRACT_ROW_EXAMPLE} — the way S14 "
            f"was adopted. Nothing was written."
        )
    return a


def live_override_report(store=None, vintages=None, contract_path: str = None) -> dict:
    """MA1 step 5 — is anything CURRENTLY overriding `settings.WEIGHTS_*` in this database?

    Reports; does not repair. An adopted row that predates this module is a live vintage
    violation, and the audit's instruction is to surface it WITH DATES rather than quietly drop
    it — a violation that is silently neutralised leaves the record saying the track was clean.

    Run it against production with the admin token, or locally:
        python -m valuation.edge.weight_adoption --status
    """
    out = {"checked_at": _dt.datetime.utcnow().isoformat(), "store_readable": False,
           "n_rows": 0, "n_adopted": 0, "overriding": [], "violations": [], "authorisation": {}}
    for bucket in ("established", "speculative"):
        out["authorisation"][bucket] = authorisation(bucket, vintages=vintages,
                                                     contract_path=contract_path)
    if store is None:
        try:
            from ..screener.store import Store
            store = Store()
        except Exception as e:
            out["reason"] = f"no store ({type(e).__name__}: {e})"
            return out
    try:
        rows = store.learning_history(limit=500)
        out["store_readable"] = True
    except Exception as e:
        out["reason"] = f"store not readable ({type(e).__name__}: {e})"
        return out

    out["n_rows"] = len(rows)
    seen = set()
    for r in rows:                                   # learning_history is newest-first
        if not r.get("adopted"):
            continue
        out["n_adopted"] += 1
        b = r.get("bucket")
        rec = {"bucket": b, "created_at": r.get("created_at"), "note": r.get("note"),
               "source": (r.get("stats") or {}).get("source") or "monthly_learner",
               "id": r.get("id")}
        if b not in seen:                            # the row `latest_learned_weights` would return
            seen.add(b)
            out["overriding"].append(rec)
            if not out["authorisation"].get(b, {}).get("authorised"):
                out["violations"].append(dict(rec, why=(
                    "this row is the one the live scorer would prefer over settings.WEIGHTS_*, "
                    "and no registered+signed vintage authorises it")))
    out["clean"] = not out["violations"]
    return out


def _cli(argv=None):
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Learned-weight adoption status (master audit MA1).")
    ap.add_argument("--status", action="store_true", help="report what is overriding settings now")
    ap.add_argument("--db", default=None, help="path to a screener.db (default: the live one)")
    a = ap.parse_args(argv)
    store = None
    if a.db:
        from ..screener.store import Store
        store = Store(a.db)
    print(json.dumps(live_override_report(store), indent=2, default=str))
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(_cli())
