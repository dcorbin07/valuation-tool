"""
AUDIT M6 — the FIELD-level schema guard for the canonical results file.

The block-level half of M6 landed with B22: `RESULT_BLOCKS` plus `missing_result_blocks`
means a whole missing block is now an error rather than an absence nobody can distinguish
from "ran and had nothing to say". This module closes the other half.

THE CLASS THIS EXISTS TO CATCH. A hand-written fixed list of field names projects a
producer's dict into the payload, and anything the producer computes that is not on the
list is dropped SILENTLY. It has bitten twice, and both times a human caught it by reading
two files side by side:

  1. A COMPUTED T-STAT. `quantile_backtest` computed
     `top_decile_alpha_tstat = 4.517421601141459` correctly on the first full run after R9;
     `build_payload` whitelists what it writes, so the canonical file recorded `None` beside
     it. Nothing raised.
  2. A REFUSAL FLAG. `archive.archive_scan` names ten keys explicitly and stores
     `fair_value` but not the refusal flag or reason, so the permanent archive cannot
     distinguish "refused" from "not computed".

WHY IT ENUMERATES FROM THE SOURCE. M3's census established the shape of every guard failure
in this project: *a guard whose input is computed elsewhere is not a guard*, and a coverage
guard that iterates a REGISTRY cannot see the thing it exists to catch, because an
unregistered field is invisible to it. So this guard iterates the keys the PRODUCER actually
returned and requires every one of them to be accounted for — carried, renamed, or
explicitly allowed. A newly computed field is accounted for by none of those, which is
exactly when it should be loud.

An allowlist entry is a decision somebody wrote down and left in a diff. A silent drop is
not. That is the whole difference this module buys.
"""
from __future__ import annotations


def dropped_fields(source: dict, projected: dict, renames=(), allow=()) -> list:
    """Keys the producer computed that the projection does not account for.

    `renames` maps SOURCE key -> payload key, for the places `build_payload` deliberately
    republishes a field under a clearer name. `allow` names source keys deliberately not
    carried. Everything else the producer emits must appear in `projected` under its own
    name, or it is reported.
    """
    if not isinstance(source, dict) or not isinstance(projected, dict):
        return []
    accounted = set(projected) | set(dict(renames)) | set(allow)
    return sorted(k for k in source if k not in accounted)


# Per-block specification. `src` is the key in the `run_backtests` result that feeds the
# block; `renames` and `allow` are the two sanctioned ways for a source field not to appear
# in the payload under its own name. Anything else is a finding.
#
# Every `allow` entry carries its reason. "Nobody got round to it" is not a reason, and an
# entry without one should be treated as a bug in this table rather than a settled decision.
BLOCK_SPEC = {
    "construction": {
        "src": "construction",
        "renames": {"horizon": "horizon_days",
                    "sw_top_decile_alpha": "signal_weighted_top_decile_alpha"},
        "allow": {
            "series": "opt-in per-period draws (V2G); large, and the payload is a summary",
            "sw_top_decile_ann": "the level; the payload carries the ALPHA, which is the claim",
            "status": "surfaced by the `errors` block instead",
        },
    },
    "portfolio": {
        "src": "hold_until_exit",
        "renames": {"bench_cagr": "benchmark_cagr", "ew_cagr": "equal_weight_cagr",
                    "ew_alpha": "alpha_vs_equal_weight",
                    "bench_return": "benchmark_total_return"},
        "allow": {"status": "surfaced by the `errors` block instead"},
    },
    # AUDIT R4 — carried through verbatim, so there are no renames and nothing to allow. It
    # is registered here rather than left unguarded precisely because R4's own finding is
    # that bullet 4 was COMPUTED and never REPORTED: a multiple-testing correction that can
    # be silently dropped on its way to the file would repeat that failure one level up.
    "multiple_testing": {"src": "multiple_testing", "renames": {}, "allow": {}},
    "cpcv": {
        "src": "cpcv",
        "renames": {"recommended_weights_cols": "recommended_weights",
                    "challenger_weights_cols": "challenger_weights"},
        "allow": {"status": "surfaced by the `errors` block instead"},
    },
    "institutional_dependence": {
        "src": "institutional_dependence",
        "renames": {},
        "allow": {"status": "surfaced by the `errors` block instead"},
    },
    "ev_freshness": {
        "src": "ev_freshness",
        "renames": {},
        "allow": {},
    },
    "signal_coverage": {
        "src": "signal_coverage",
        "renames": {},
        "allow": {},
    },
}


def _threw(block: dict) -> bool:
    """Did this block raise? Then it computed nothing, and has nothing to drop."""
    st = (block or {}).get("status")
    return isinstance(st, str) and st.lower().startswith("error")


def check_payload(res: dict, payload: dict) -> list:
    """Every field-level drop between a `run_backtests` result and its payload.

    Returns a list of {block, field, source_key} — empty when nothing was silently lost.

    A block that THREW is skipped: it produced no fields, so "you dropped a field" would be
    noise layered on top of the real failure. Keeping the two error classes distinct is the
    same lesson `missing_result_blocks` already carries — assuming one guard covers another
    is how a degraded run comes to read as a run that found nothing.
    """
    findings = []
    for block, spec in BLOCK_SPEC.items():
        source = (res or {}).get(spec["src"]) or {}
        projected = (payload or {}).get(block) or {}
        if not source or _threw(source):
            continue                     # absent block is the BLOCK-level guard's business
        for field in dropped_fields(source, projected,
                                    renames=spec["renames"], allow=spec["allow"]):
            findings.append({"block": block, "field": field, "source_key": spec["src"]})
    return findings


class PayloadSchemaError(AssertionError):
    """A computed field never reached the canonical file. Fails the run (audit M6)."""


def describe(findings) -> str:
    if not findings:
        return "no dropped fields"
    by = {}
    for f in findings:
        by.setdefault(f["block"], []).append(f["field"])
    return "; ".join(f"{b}: {', '.join(sorted(v))}" for b, v in sorted(by.items()))
