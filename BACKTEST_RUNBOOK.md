# Backtest runbook — local run → Render (Sharadar)

**The key idea:** Render never touches Sharadar or the raw data. You run the backtest
on your own machine; the ONLY thing that travels to Render is the **optimized weights**
(a handful of numbers), via a normal code commit. The raw data stays local.

```
  YOUR PC                                              RENDER
  ┌───────────────────────────────┐                   ┌──────────────────────┐
  │ Sharadar key → download data  │   git push        │ live site uses the   │
  │ → backtest → optimized weights│ ────────────────▶ │ new starting weights │
  └───────────────────────────────┘   (weights only)  └──────────────────────┘
```

---

## One-time local setup
Your local `.env` already has:
```
EDGE_DATA_PROVIDER=sharadar
SHARADAR_API_KEY=<paste your Nasdaq Data Link key>   # same key you put on Render
```
Then, in the repo folder: `pip install -r requirements.txt`

---

## Step 1 — export the data once (recommended)
Downloads prices + fundamentals + insiders + institutional into a local folder, so every
re-run afterward is instant and offline (and it's your "keep it for the month" snapshot):
```
python -m valuation.edge.export_sharadar --out ./data/backtest --limit 3000
```
This makes thousands of API calls, so it takes a while — run it once and walk away.

## Step 2 — run the backtest (offline, unlimited re-runs)
```
python -m valuation.edge.fundamental_panel --data-dir ./data/backtest
```
It prints, per holding horizon: your model's total return **vs the S&P**, whether the
optimized weights **beat the defaults out-of-sample**, and — only if they did — a
paste-ready line:
```
WEIGHTS_ESTABLISHED = {"value": 0.28, "quality": 0.24, ...}
```
(You can skip Step 1 and run `python -m valuation.edge.fundamental_panel` straight against
Sharadar live, but it re-downloads every run.)

## Step 3 — get it to Render (the handoff)
Paste that `WEIGHTS_ESTABLISHED = {...}` line over the existing one in
`valuation/screener/settings.py`, then:
```
git add -A && git commit -m "Adopt backtested starting weights" && git push
```
Render redeploys and the live scorer starts from those weights. **That is the entire
local → Render bridge.** The monthly self-learner then refines from that starting point.

---

## Notes
- **Only adopt if a horizon shows `beats-default-OOS: True`.** If nothing beats the
  default out-of-sample, keep the current weights — the backtest just confirmed they're
  already reasonable. (Don't force-fit.)
- **First run — sanity check the two new factors.** The insider (SF2) and institutional
  (SF3) field mappings are set defensively; confirm those columns aren't empty. If they
  are, the field names differ on your plan — grab a sample row and it's a one-line fix.
- **Show the vs-S&P chart on the live site (optional):** hit
  `/admin/run-fundamental-backtest?limit=50` on Render once (small = won't time out). The
  weights are the substance; this is just for the Edge Lab display.
- **Do NOT** run the whole-market backtest on Render — thousands of per-ticker calls will
  time out the 512 MB box and hit Sharadar's rate limit. That's what the local run is for.
- **October (free WRDS):** set `EDGE_DATA_PROVIDER=wrds` + `WRDS_DATA_DIR=<export folder>`,
  re-run Step 2. Zero code change.
- **Cancel Sharadar** once you've captured the weights.
