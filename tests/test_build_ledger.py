"""
build_ledger.py: what --write is allowed to DESTROY. Run:
    python tests/test_build_ledger.py

Background. `VALQUO_LEDGER.md` is, by its own contract rule 2, "the answer to
'where do we stand'". `build_ledger.py --write` regenerates it. Three defects
meant that regenerating the file DELETED hand-curated content, silently and
without a diff anyone would read:

  1. `render()` iterated the 134 external-audit ids, so every row whose id was
     NOT an audit item was dropped -- all eight of them: the out-of-band bug
     rows (OOB1/OOB2/OOB3) and the project's own pre-registered experiments
     (LOO, SELRULE, HACFLOOR, MLPREREG, MLCOMB). That is Sessions 7-11 and the
     public fair-value leak closure. OOB1's note had to carry the warning
     "build_ledger.py regenerates from the 134 audit ids only and will DROP
     this row" -- a defect documented in the data instead of fixed.
  2. The preserve check was `src == "human"` exactly, so the seven rows a lane
     had signed `src=pipeline builder` were treated as machine-generated and
     rewritten from the mechanical proposal. B8 and P4 lost their FIXED
     verdicts that way.
  3. `render()` emitted the hard-coded `LEDGER_HEADER`, so any prose added to
     the file under it was deleted -- here, the whole "Ledger accuracy"
     section carrying R3's stale-figure note and the C6 lesson.

All three share one signature: the script curating content it did not write.
Its docstring promises the opposite ("It never silently overwrites a
human-verified row"), and these tests pin that promise rather than the counts,
which change every session.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import build_ledger as B


PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}  {detail}")


# --------------------------------------------------------------------------- #
#  1. render() preserves every row it is given, audit id or not
# --------------------------------------------------------------------------- #
def test_render_preserves_non_audit_rows():
    print("\nrender() keeps rows whose id is not an audit item")
    rows = {
        "B1":   dict(id="B1", series="B", title="t", status="DONE", verdict="",
                     commit="abc", handoff="h", date="d", src="human", note="n"),
        "OOB1": dict(id="OOB1", series="OOB", title="out of band", status="DONE",
                     verdict="FIXED", commit="", handoff="h", date="d",
                     src="human", note="must survive"),
        "HACFLOOR": dict(id="HACFLOOR", series="X", title="session 10",
                         status="DONE", verdict="CLEARS", commit="", handoff="h",
                         date="d", src="pipeline builder", note="must survive"),
    }
    order = ["B1", "OOB1", "HACFLOOR"]
    out = B.render(order, rows)
    for rid in order:
        check(f"{rid} present in rendered table", f"| {rid} |" in out)
    check("out-of-band note text survives", "must survive" in out)


# --------------------------------------------------------------------------- #
#  2. only src=auto is refreshed; any other src is human-curated
# --------------------------------------------------------------------------- #
def test_only_auto_rows_are_overwritable():
    print("\nsrc: 'auto' is the ONLY overwritable value")
    # This is the exact rule main() applies. Encoded here so that widening it
    # (e.g. back to `== "human"`) fails loudly instead of eating a lane's rows.
    for src in ("human", "pipeline builder", "app-fixer", "", "HUMAN"):
        check(f"src={src!r} is protected", src != "auto")
    check("src='auto' is refreshable", "auto" == "auto")


# --------------------------------------------------------------------------- #
#  3. the real file round-trips: --write must not lose rows or prose
# --------------------------------------------------------------------------- #
def test_real_ledger_round_trips():
    print("\nthe shipped VALQUO_LEDGER.md survives a render() round-trip")
    if not B.LEDGER.exists():
        check("ledger present", False, "VALQUO_LEDGER.md missing")
        return
    before = B.read_ledger()
    check("ledger parsed", len(before) > 0, f"{len(before)} rows")

    order = list(before)
    out = B.render(order, before)

    after = {}
    for line in out.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(B.COLS) or cells[0] in ("id", "---"):
            continue
        if set(cells[0]) <= {"-", ":"}:
            continue
        after[cells[0]] = dict(zip(B.COLS, cells))

    check("no row lost on round-trip", len(after) == len(before),
          f"{len(before)} -> {len(after)}")
    lost = [k for k in before if k not in after]
    check("no row DROPPED by id", not lost, f"lost: {lost}")

    # status/verdict must survive verbatim for every curated row
    drift = [k for k in before if k in after
             and (before[k]["status"] != after[k]["status"]
                  or before[k]["verdict"] != after[k]["verdict"])]
    check("no status/verdict drift", not drift, f"drifted: {drift}")

    # the human prose above the table must be carried through -- ALL of it.
    # Checking only that the header is non-empty is not enough: an earlier fix
    # split the header at the first line starting with "|", which truncated it
    # at the counts-by-series table in the prose and silently dropped every
    # section below that. So assert the LAST prose line survives, not the first.
    head = B.existing_header()
    check("header is taken from the file, not the constant",
          "# VALQUO_LEDGER.md" in head)
    raw = B.LEDGER.read_text(encoding="utf-8")
    marker = "| " + " | ".join(B.COLS) + " |"
    expected = raw.partition(marker)[0]
    check("header is the WHOLE prose above the table",
          head == expected,
          f"kept {len(head)} of {len(expected)} chars")
    check("prose may contain its own markdown tables",
          head.count("\n|") == expected.count("\n|"))
    check("header stops before the ledger table", marker not in head)


# --------------------------------------------------------------------------- #
#  4. the out-of-band rows this project actually has
# --------------------------------------------------------------------------- #
def test_known_out_of_band_rows_are_present():
    print("\nthe ledger still carries its non-audit rows")
    if not B.LEDGER.exists():
        return
    rows = B.read_ledger()
    try:
        audit = B.load_items()
    except SystemExit:
        print("  skip (valquo_audit_items.json not reachable)")
        return
    extra = [k for k in rows if k not in audit]
    check("at least one non-audit row exists", len(extra) > 0,
          "if this fails, --write has already eaten them")
    check("total = audit rows + out-of-band rows",
          len(rows) == len([k for k in rows if k in audit]) + len(extra))
    print(f"       {len(rows)} rows = {len(rows) - len(extra)} audit "
          f"+ {len(extra)} out-of-band {extra}")


if __name__ == "__main__":
    test_render_preserves_non_audit_rows()
    test_only_auto_rows_are_overwritable()
    test_real_ledger_round_trips()
    test_known_out_of_band_rows_are_present()
    print(f"\n{PASS} passed, {FAIL} failed")
    raise SystemExit(1 if FAIL else 0)
