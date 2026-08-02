"""Show progress + the partial verdict of the running scream-buy options backtest.

Run it any time; it is read-only apart from writing a human-readable snapshot JSON.

    python optbt_status.py

The backtest banks its state after EVERY name, so this always reflects completed work - a
partial verdict is available long before the run finishes.
"""
import json
import os
import pickle
import sys

BANK = r"C:\Users\donni\.claude\jobs\7819c8eb\tmp\optbt_trades.pkl"
LOG = (r"C:\Users\donni\AppData\Local\Temp\claude"
       r"\C--Users-donni-Downloads-valuation-tool--claude-worktrees-fix-13f-lag-test"
       r"\7819c8eb-b85f-49ad-a6ec-03b4cf384f37\tasks\bbsxxf32j.output")
SNAPSHOT = r"C:\Users\donni\Downloads\valuation-tool\data\options\optbt_partial.json"
TOTAL = 55

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if not os.path.exists(BANK):
        print("No banked state yet - the first name has not finished.")
        return
    with open(BANK, "rb") as f:
        st = pickle.load(f)
    if "done" not in st:
        print("Bank is from an older run format; the current run has not banked a name yet.")
        return

    done, trades = st.get("done", []), st.get("trades", [])
    gaps, rejects = st.get("gaps", {}), st.get("rejects", {})
    scored = [d for d in done if d not in gaps]
    print(f"NAMES   {len(done)}/{TOTAL} processed   ({len(scored)} scored, "
          f"{len(gaps)} skipped for missing years)")
    print(f"TRADES  {len(trades)} closed   (candidates {st.get('cand', 0)}, "
          f"alerts {st.get('alerts', 0)})")
    if gaps:
        print(f"SKIPPED {', '.join(f'{k}{v}' for k, v in list(gaps.items())[:6])}")
    if rejects:
        print(f"REJECTS {rejects}")

    if not trades:
        print("\nNo closed trades yet.")
        return

    from valuation.edge.options_backtest import expectancy_report
    rep = expectancy_report(trades)
    o = rep["overall"]

    def pct(x):
        return "n/a" if x is None else f"{x*100:+.1f}%"

    print("\n=== PARTIAL VERDICT - net of spread + commission, buy-the-ask/sell-the-bid ===")
    print(f"  closed trades      {o['n_closed']}")
    print(f"  hit rate           {'n/a' if o['hit_rate'] is None else f'{o[chr(104)+chr(105)+chr(116)+chr(95)+chr(114)+chr(97)+chr(116)+chr(101)]*100:.1f}%'}")
    print(f"  avg win            {pct(o['avg_win_pct'])}")
    print(f"  avg loss           {pct(o['avg_loss_pct'])}")
    print(f"  profit factor      {o['profit_factor'] if o['profit_factor'] is not None else 'n/a (no losses yet)'}")
    print(f"  EXPECTANCY / trade {pct(o['expectancy_pct'])}")
    print(f"  cumulative P&L     ${o['cum_pnl_dollars']:,.0f} (1 contract per trade)")
    print(f"  enough to tune?    {o['enough_to_tune']} (needs {o['min_required']} closed)")

    for dim in ("exit_reason", "score", "opt_right"):
        b = rep["buckets"].get(dim)
        if not b:
            continue
        print(f"\n  by {dim}:")
        for name, s in b.items():
            if s["n_closed"]:
                print(f"    {str(name)[:22]:24s} n={s['n_closed']:4d}  "
                      f"exp={pct(s['expectancy_pct'])}  hit="
                      f"{'n/a' if s['hit_rate'] is None else f'{s[chr(104)+chr(105)+chr(116)+chr(95)+chr(114)+chr(97)+chr(116)+chr(101)]*100:.0f}%'}"
                      f"  {'' if s['enough_to_tune'] else '(too few to act on)'}")

    try:
        os.makedirs(os.path.dirname(SNAPSHOT), exist_ok=True)
        with open(SNAPSHOT, "w", encoding="utf-8") as f:
            json.dump({"names_done": len(done), "names_total": TOTAL, "scored": scored,
                       "skipped_for_gaps": gaps, "n_trades": len(trades),
                       "overall": o, "buckets": rep["buckets"], "rejects": rejects},
                      f, indent=1, default=str)
        print(f"\nsnapshot written: {SNAPSHOT}")
    except OSError as e:
        print(f"(snapshot write failed: {e})")

    if os.path.exists(LOG):
        try:
            tail = [ln for ln in open(LOG, encoding="utf-8", errors="replace").read()
                    .splitlines() if ln.strip()][-3:]
            if tail:
                print("\nlast log lines:")
                for ln in tail:
                    print("  " + ln[:150])
        except OSError:
            pass


if __name__ == "__main__":
    main()
