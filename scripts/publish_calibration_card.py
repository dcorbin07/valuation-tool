"""Publish `SC-1b`'s calibration verdict as a tracked card the public page can read.  [SC-1]

WHY THIS SCRIPT EXISTS, AND IT IS A CONSTRAINT RATHER THAN A PREFERENCE. `/research` must
derive its calibration figures at render rather than carry them as literals -- a count of
scored predictions is exactly the kind of number that goes stale the moment the record grows,
which is the reason `MB38`'s denominator is derived and not typed. But the study's artifact
lives under the repo-root `data/`, which is gitignored and never ships with a deploy, so a
surface that read it directly would be permanently unavailable in production. Both halves are
real, and this script is the join between them.

ONE AUTHORITY, ONE DIRECTION. `data/free_analysis/SC1B_CLUSTER_BY_ITEM.json` is the authority.
This writes a strict SUBSET of it into `data_export/`, which is tracked, ships in the image
(`.dockerignore` excludes `data/` and not `data_export/`) and already exists for exactly this
-- publishing something derived out of the ignored data root. Nothing is typed here: every
value is copied out of the artifact, and the card carries the artifact's SHA-256 so a test can
prove which artifact it came from rather than trusting that it matched once.

THE CARD IS NOT A SECOND VERSION OF THE TRUTH, and the test is what makes that true rather
than a hope. `tests/test_research_page.py` re-derives the card from the artifact whenever the
artifact is present and requires the committed file to match byte for byte, so a card edited by
hand, or left behind by a re-run, fails the suite. Where the artifact is absent -- CI, the
service -- the card is simply the published fact, and the page's own fail-closed rule covers
the case where it is missing or malformed.

WHAT IS DELIBERATELY NOT COPIED. The Murphy decomposition, the Brier skills, the two intervals
and every power figure past the detection threshold stay in the artifact. The page publishes a
verdict word, a count, one half-width, one pre-committed ceiling and the study's own list of
things it may not be quoted as. A card that carried everything would become the back door
around the publishing rule that the page's whole design exists to prevent.

    python -m scripts.publish_calibration_card            # dry run, prints the card
    python -m scripts.publish_calibration_card --write    # write data_export/calibration_card.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

ARTIFACT = os.path.join("data", "free_analysis", "SC1B_CLUSTER_BY_ITEM.json")
CARD = os.path.join("data_export", "calibration_card.json")

#: Every field the page is allowed to see, and where it comes from in the artifact. Written as
#: a table rather than as attribute access so the mapping is inspectable and so a key that
#: disappears from the artifact fails loudly here instead of silently publishing a null.
FIELDS = (
    ("item", ("item",)),
    ("register", ("register",)),
    ("register_commit", ("register_commit_alone",)),
    ("corpus_pinned_to", ("corpus_pinned_to",)),
    ("verdict", ("verdict",)),
    ("n", ("measurement", "n")),
    ("n_clusters", ("measurement", "n_clusters_item")),
    ("gap", ("measurement", "gap")),
    ("half_width", ("the_three_rung_ladder", "item_half_width")),
    ("bar", ("the_three_rung_ladder", "bar")),
    ("detection_threshold_50pct", ("power", "detection_threshold_50pct_power")),
    ("cluster_adjusted_detection_threshold_50pct",
     ("power", "cluster_adjusted_detection_threshold_50pct")),
    ("may_not_be_quoted_as", ("may_not_be_quoted_as",)),
)


def _dig(obj, path):
    cur = obj
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            raise KeyError("the artifact has no %s" % "/".join(path))
        cur = cur[k]
    return cur


def build(artifact_path: str = ARTIFACT) -> dict:
    """The card, derived. Raises if the artifact is missing a field rather than defaulting."""
    raw = open(artifact_path, "rb").read()
    art = json.loads(raw.decode("utf-8"))
    card = {k: _dig(art, path) for k, path in FIELDS}
    # Tamper evidence, and the reason the card can be trusted without the artifact beside it:
    # the test that re-derives this file can prove it came from the artifact it names.
    card["source"] = ARTIFACT.replace(os.sep, "/")
    card["source_sha256"] = hashlib.sha256(raw).hexdigest()
    return card


def text(card: dict) -> str:
    """The exact bytes of the card file. Deterministic: sorted keys, trailing newline."""
    return json.dumps(card, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--artifact", default=ARTIFACT)
    ap.add_argument("--out", default=CARD)
    ap.add_argument("--write", action="store_true", help="write the card (default: dry run)")
    a = ap.parse_args(argv)

    if not os.path.exists(a.artifact):
        print("REFUSED: %s is not on disk. It is produced by "
              "scripts/sc1b_cluster_by_item.py and lives under the gitignored data root."
              % a.artifact)
        return 2
    card = build(a.artifact)
    body = text(card)
    print(body)
    if not a.write:
        print("(dry run -- pass --write to publish to %s)" % a.out)
        return 0
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print("wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
