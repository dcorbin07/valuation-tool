# data_export — backup of the forward paper track

**These files are a backup, not an input.** Nothing reads them; the live record lives in the
screener database on the Render service's persistent disk. They exist because that disk is the
only copy, and this record is the one thing in the project that cannot be re-derived: it is
what the model said on days that have already happened. Re-creating it later from current data
would produce a different object with the same column names.

Written by `python -m valuation.edge.track_export`, regenerated in full each run (idempotent —
same database in, byte-identical files out), and committed weekly by the `track-backup`
GitHub Actions workflow, which pulls them from the live service's `/admin/export-track`.

| File | What |
|---|---|
| `paper_track_history.json` | everything below, structured — the complete artifact |
| `paper_track_index.csv` | daily Valquo Index vs SPY, cumulative since inception |
| `paper_track_trades.csv` | every paper option trade: entry, exit, reason, P&L |
| `paper_track_holdings.csv` | the index book the daily series is measured from |

**Paper only.** Tradier sandbox fills on delayed quotes, entries at the ask and exits at the
bid. No real money and no real orders. It is a forward, out-of-sample record — which is the
one thing the backtest cannot claim — and it is thin, and thin records mean very little.

To restore: read `paper_track_history.json` and re-insert into `paper_index_track`,
`paper_index_holdings`, `paper_option_orders` and `option_alerts`. Column names in the JSON
match the table columns exactly, which is why the JSON is stored raw rather than summarised.

No secrets: market data, timestamps and sandbox order ids only.
