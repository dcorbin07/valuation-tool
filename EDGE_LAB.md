# Edge Lab — your private research bench (owner-only)

This is the part that keeps you honest: it measures whether the tool's picks
actually have an edge, tracks a live paper account vs the S&P, and re-tunes the
rules over time **without overfitting**. It's gated to owner emails only — your
subscribers never see it.

Three ways to use it: the **🔬 Edge Lab tab** (visible only to you), or the CLI:

```bash
python -m valuation.edge.lab backtest --strategy momentum --hold 15 --limit 150
python -m valuation.edge.lab optimize --limit 150
python -m valuation.edge.lab track
```

## 1. Backtest — would following the picks have beaten the S&P?
Simulates holding an equal-weight basket of the top-N ranked names, rebalanced on a
fixed cadence, **choosing picks point-in-time** (only past data at each date), over
history — and reports **1/5/10-year** CAGR, alpha, Sharpe, and max drawdown vs SPY,
after costs. Two strategies work on free data today:
- `momentum` — 12-1 month momentum ranking.
- `technical` — the Signals tab's technical score.

> **Survivorship caveat:** free price history only contains names still listed, so
> the historical backtest **overstates** edge. Treat a positive result as "worth
> confirming on survivorship-free data," not proof. (This is why the live track
> record below matters — it's survivorship-free going forward.)

## 2. Track record — the live "paper account"
Every daily hot-list is a dated set of picks. `track` computes each matured pick's
realized return at 1m/3m/6m/1y and the S&P's return over the same window, then
reports average return, **alpha**, and **hit rate vs SPY** per horizon. This accrues
honestly over time — no survivorship bias, no look-ahead. Run it periodically (or
wire it into the daily job) and watch whether real alpha shows up.

## 3. Optimize — tune the rules without overfitting
Builds a multi-factor, point-in-time **price** panel (momentum 12-1 and 3-1,
short-term reversal, trend vs 200-DMA, low-volatility) and runs **walk-forward
optimization**: tune weights on the past, apply to the *next unseen fold*, roll
forward, stitch the out-of-sample results. New weights are adopted **only if they
beat the baseline out-of-sample**. A **Claude advisor** (if your key is set)
proposes mechanism-driven weightings, but an untouched **holdout half decides** —
Claude advises, the data rules. Below ~30 rebalance dates it refuses to conclude
anything (sample-aware). This is the same discipline as your screener's self-review.

## How to make the engine as smart as possible (the honest way)
1. **Let the track record accrue.** Real, dated, survivorship-free evidence beats any
   backtest. Give it months.
2. **Run `optimize` periodically** as data grows; adopt weights only when walk-forward
   blesses them. Never hand-tune to make a backtest look good.
3. **Add point-in-time fundamentals** to unlock optimizing the *fundamental composite*
   (not just price factors). Port your screener's `pit_data.py` EDGAR reconstruction
   into `edge/panel.py` as extra factor columns — the walk-forward + advisor already
   handle any factor set. This is the single highest-value upgrade.
4. **Confirm on survivorship-free data** (a paid vendor, or your PIT EDGAR set) before
   sizing real capital.

## The honest bottom line
The lab is built to find edge if it's there — and to tell you plainly when it isn't,
the way your screener did ("no reliable edge after costs" is a *valid, valuable*
result). Don't deploy real money on an in-sample curve; deploy on an edge that
survived walk-forward and showed up in the live track record. Educational tooling,
not investment advice.
