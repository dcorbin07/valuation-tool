"""Finished one-shot research studies — analysis harnesses, NOT product code.  [AUDIT MA23]

WHAT BELONGS HERE, AND THE TEST IS MECHANICAL RATHER THAN A MATTER OF TASTE: a module whose
only callers are its own `scripts/` runner and its own test. That is the signature of a study
whose verdict has already been recorded — the harness exists so the verdict can be re-derived,
not because anything in the shipped product calls it.

WHY THE BOUNDARY EXISTS AT ALL. Before this package these twelve modules sat in
`valuation/edge/` beside the shipped engine, and three things followed from that:

  * the Flask deploy image shipped 4,587 lines of research code it never imports;
  * a reader could not tell product from study by location, which is the same failure class
    `CLAUDE.md` was split up for — the record and the instructions in one undifferentiated pile;
  * `surfaces.py` had to reason about "no raw vendor rows" across a package that mixed both.

NOTHING IS DELETED, AND THE REASON IS THE PROJECT'S OWN RULE. Deleting a study's harness
destroys the ability to re-derive its verdict, which is `RUN_RULES` rule 9 one level up. This
is a MOVE. Every module is byte-identical to its `valuation/edge/` original except for the
relative imports that had to change depth (`.fundamental_panel` -> `..edge.fundamental_panel`),
and `git log --follow` reaches the whole history of each.

THE DEPENDENCY DIRECTION IS ONE-WAY AND IS PINNED BY TEST. A study may import the engine; the
engine may NEVER import a study. `tests/test_studies_boundary.py` fails if any module under
`valuation/` outside this package imports from `valuation.studies` — which is what stops a
study quietly becoming load-bearing again and undoing the move.

WHAT THIS IS NOT. It is not a claim that `valuation/edge/fundamental_panel.py` got smaller.
It did not: the panel is 5,014 lines and is not one of the files moved here. `MA_DEPENDENCY_MAP.md`
names MA23 as the item that would change the panel's one-owner-at-a-time constraint; measured,
it cannot, because the panel is a FILE and this item moves a DIRECTORY's other occupants.
The constraint on the panel is untouched and still binds.

Each module keeps its own docstring naming the register it executes and the verdict it produced.
"""
