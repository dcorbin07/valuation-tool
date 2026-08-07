"""b8_holdout_scope.py — AUDIT B8. Does enforcing the decide-half rule change a shipped verdict?

`holdout_theme_validate` computed `rule_fired` and never read it, so its verdict was a
both-halves stability check while its docstring described an out-of-sample protocol. Both now
ship, separately named. This prints the two side by side so the difference is a measurement
rather than a code-reading claim, and so any future change to either is visible in a diff.

    python -m scripts.b8_holdout_scope <panel.pkl>
"""
import json
import sys

import pandas as pd

from valuation.edge.fundamental_panel import holdout_theme_validate
from valuation.screener import settings as S

PANEL = sys.argv[1]
panel = pd.read_pickle(PANEL)
cols = [c for c in S.BUCKET_FACTORS["established"]
        if c in panel.columns and panel[c].notna().any()]
print(f"[B8] panel {len(panel):,} rows, {panel['date'].nunique()} dates, cols={cols}", flush=True)

r = holdout_theme_validate(panel, cols, horizon=63)
print(f"[B8] boundary embargoed: {r.get('boundary_date_embargoed')}", flush=True)

rows = []
for c in cols:
    fired = {s: r["splits"][s]["themes"][c]["rule_fired"] for s in r["splits"]}
    impr = {s: r["splits"][s]["themes"][c]["improves"] for s in r["splits"]}
    rows.append({
        "theme": c,
        "stability_verdict": r["verdicts"][c],
        "oos_verdict": r["oos_verdicts"][c],
        "oos_directions_tested": r["oos_directions_tested"][c],
        "rule_fired_early": fired["decide_early_measure_late"],
        "rule_fired_late": fired["decide_late_measure_early"],
        "improves_early": impr["decide_early_measure_late"],
        "improves_late": impr["decide_late_measure_early"],
        "changed": r["verdicts"][c] != r["oos_verdicts"][c].replace("_oos", ""),
    })

hdr = f"{'theme':22s} {'stability':16s} {'oos':20s} {'dirs':4s} {'fired E/L':10s} {'impr E/L':9s}"
print(hdr)
print("-" * len(hdr))
for x in rows:
    print(f"{x['theme']:22s} {x['stability_verdict']:16s} {x['oos_verdict']:20s} "
          f"{x['oos_directions_tested']:<4d} "
          f"{str(x['rule_fired_early'])[0]}/{str(x['rule_fired_late'])[0]:8s} "
          f"{str(x['improves_early'])[0]}/{str(x['improves_late'])[0]}")

out = {"panel": {"rows": int(len(panel)), "dates": int(panel["date"].nunique())},
       "cols": cols, "rows": rows,
       "verdicts_scope": r["verdicts_scope"], "oos_verdicts_scope": r["oos_verdicts_scope"]}
with open("B8_IMPACT.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("\n[B8] wrote B8_IMPACT.json")
