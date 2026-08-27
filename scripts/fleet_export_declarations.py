"""EXPORT THE DECLARATION MANIFEST — so the fleet can declare where the runner runs.

    python -m scripts.fleet_export_declarations           # write data_export/fleet_declarations.json
    python -m scripts.fleet_export_declarations --check   # compute and print, write nothing

**THE DEFECT THIS CLOSES WAS FOUND IN PRODUCTION, NOT IN A TEST.** Don dispatched
`fleet-cycle.yml` run #1 and it returned `books_declared: 0` on a service where
`entry_rules_registered` was non-empty and `assignment_provider_registered` was true. The
rules were there; **the BOOKS were not.**

TWO STACKED DEPLOYMENT GAPS, both in `.dockerignore`, and neither is fixed by the other:

  1. **`*.md` IS EXCLUDED** (only `!README.md` is negated), so **no `DECL_*.md` file reaches
     the image at all** and `declared_books()` finds nothing to iterate.
  2. **`.git` IS EXCLUDED**, so `declaration_commit()` cannot run `git log` in the image. Even
     with the markdown shipped, every book would refuse with `GIT_UNAVAILABLE` -- the
     "committed ALONE" proof is a git fact and there is no git there.

**SHIPPING THE MARKDOWN WOULD THEREFORE HAVE FIXED NOTHING.** It changes
`books_declared: 0` into eighteen books that all refuse. The commit evidence has to travel
too, which is what this manifest is for.

WHAT IT CARRIES, per book: the declaration's CONTENT HASH, its parsed JSON block, and the
three git facts `declaration_commit` checks -- the introducing commit, that it touched exactly
one file, and that it is an ancestor of the manifest's own HEAD. **Computed HERE, where git
exists. Verified THERE, where it does not.**

**A BOOK WHOSE COMMIT CHECK FAILS IS NOT EXPORTED.** The manifest is a record of what was
verified, so an unverifiable book must be absent from it rather than present-and-flagged --
present-and-flagged is how a reader comes to treat the flag as advisory.

**THAT IS THE ONLY EXCLUSION, AND `DECL_testbook.md` STAYS. DECIDED BY DON, AUDIT #5 `L7`,
2026-08-24 -- RECORDED HERE BECAUSE HERE IS WHERE SOMEBODY WOULD ADD THE FILTER.**

Audit #5 asked whether the day-1 self-verification test-book belongs in a production manifest.
It does, and the reason generalises past this one file: **a manifest that omits things somebody
decided were uninteresting cannot be trusted about the things it includes.** The moment a
reader learns that one book was left out on grounds of taste, every absence becomes ambiguous
-- and the whole value of this artifact is that an absence means exactly one thing, which the
paragraph above defines: the commit check failed.

The two exclusions are different in kind and only one of them is safe. Dropping an
UNVERIFIABLE book preserves the invariant (everything here was verified). Dropping an
UNINTERESTING book destroys it (some things that were verified are here). So the rule is
mechanical -- verified or not -- and never editorial.

**AND THE TEST-BOOK NEEDS NO FILTER, BECAUSE IT DECLARES ITSELF.** Its first line reads
*"THIS IS NOT A RESEARCH BOOK AND IT CARRIES NO VERDICT"*; it is `utility` class, so it charges
no trial in any domain and no meter is ever read on it; and it was CLOSED in the session it was
declared. It is visible, labelled and closed, which is strictly more informative than absent.
`tests/test_fleet_manifest.py` pins that it is still exported and that no name-based exclusion
has appeared here.

**THE HONEST LIMIT, AND IT IS A REAL WEAKENING: ON THE SERVICE THE TAMPER-EVIDENCE IS THIS
MANIFEST'S, NOT GIT'S.** In a worktree `may_fill` re-derives the commit facts from git every
time and this file is never consulted. In the image it cannot, so it trusts a manifest that
was built from a commit and shipped in a built image. That is a weaker chain than git and a
stronger one than nothing, and `fleet.may_fill` REPORTS WHICH IT USED (`evidence: "git"` or
`"manifest"`) so no record can be read as carrying git-grade proof when it does not.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA = "fleet_declarations/1"
OUT_REL = os.path.join("data_export", "fleet_declarations.json")


def _repo() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build(root: str = None) -> dict:
    from valuation.edge import fleet as F
    # Register S3-I3 so `declaration_valid_at_export` is a TRUE snapshot. Without it every
    # SHORT book exports as invalid on a technicality of this process rather than of the
    # declaration, and a reader would take six correct books for broken ones. This is a
    # `scripts/` runner, so `MA59`'s live-app quarantine does not apply here.
    from valuation.edge import assignment as _s3i3
    _s3i3.register(F)

    root = root or _repo()
    head, _ = F._git(["rev-parse", "HEAD"], root)
    books, skipped = {}, {}
    for d in F.declared_books(root):
        book = d["book"]
        if not d["parses"]:
            skipped[book] = "does not parse: " + (d["reason"] or "")
            continue
        path = F.declaration_path(book, root)
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        p = F.parse_declaration(text)
        v = F.validate_declaration(p["declaration"], book=book)
        c = F.declaration_commit(book, root)
        if not c["ok"]:
            # NOT exported. A record of what was verified must not carry what was not.
            skipped[book] = c["code"] + ": " + c.get("reason", "")
            continue
        books[book] = {
            "decl_sha": F.declaration_sha(text),
            "commit": c["commit"],
            "touched": c["touched"],
            "committed_alone": True,
            "is_ancestor_of": (head or "").strip(),
            "declaration_valid_at_export": bool(v["ok"]),
            "refusals_at_export": list(v.get("refusals") or []),
            "declaration": p["declaration"],
        }
    return {
        "schema": SCHEMA,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "head": (head or "").strip(),
        "evidence_note": (
            "Computed where git exists and consumed where it does not. On a service built "
            "from an image with no .git, fleet.may_fill falls back to this manifest and "
            "reports evidence='manifest' rather than 'git'. That is a WEAKER chain and the "
            "record says so on every gate result."),
        "n_books": len(books),
        "books": books,
        "skipped": skipped,
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    payload = build()
    if not payload["books"]:
        print("::error::no book passed the commit check; refusing to write an empty manifest")
        print(json.dumps(payload["skipped"], indent=2))
        return 1
    if "--check" in argv:
        print(json.dumps({k: v for k, v in payload.items()
                          if k not in ("books", "skipped")}, indent=2))
        for b, v in sorted(payload["books"].items()):
            print("  %-26s %s  alone=%s valid=%s"
                  % (b, v["commit"][:9], v["committed_alone"],
                     v["declaration_valid_at_export"]))
        for b, why in sorted(payload["skipped"].items()):
            print("  SKIPPED %-18s %s" % (b, why[:90]))
        print("%d books, NOT written (--check)." % len(payload["books"]))
        return 0
    out = os.path.join(_repo(), OUT_REL)
    with io.open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("wrote %s -- %d books, %d skipped" % (OUT_REL, len(payload["books"]),
                                                len(payload["skipped"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
