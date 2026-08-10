# data_export — backup of the forward paper track

**These files are a backup, not an input.** Nothing reads them; the live record lives in the
screener database on the Render service's persistent disk. They exist because that disk is the
only copy, and this record is the one thing in the project that cannot be re-derived: it is
what the model said on days that have already happened. Re-creating it later from current data
would produce a different object with the same column names.

Written by `python -m valuation.edge.track_export`, regenerated in full each run (idempotent —
same database in, byte-identical files out), and committed weekly by the `track-backup`
GitHub Actions workflow, which pulls them from the live service's `/admin/export-track`.

## TWO DIFFERENT BOOKS ARE BACKED UP HERE. THEY ARE NOT ONE TRACK RECORDED TWICE.

Read this before quoting any figure out of these files.

**The contract-bound Valquo Index** — `valquo_index_*` — is the record
`PAPER_TRACK_CONTRACT.md` binds: 86 names, score-weighted, capped at 8%, inception
2026-07-30. It is the ONLY series that may be cited as evidence under that contract, and
`index_track.vs_spy_claim()` is the only function allowed to make a vs-SPY statement from it.

**The Tradier sandbox engine** — `paper_track_*` — is a different book: 10 names,
equal-weighted at 10% each, inception 2026-08-03. Those 10% weights break the contract's own
8% cap, so **the sandbox is not the Index and may never be quoted as it.** On 2026-08-05 a
Discord recap printed the sandbox's numbers under the words "Valquo Index vs SPY" and claimed
the Index was beating SPY on a day the bound recorder had it 2.85pp behind.

| File | What |
|---|---|
| `valquo_index_track.csv` | **the contract-bound Index**, daily vs SPY, cumulative since inception |
| `valquo_index_meta.json` | that Index's inception, benchmark and 86-name book |
| `paper_track_history.json` | everything here, structured — the complete artifact |
| `paper_track_index.csv` | **the SANDBOX engine's** daily vs-SPY series — NOT the Index |
| `paper_track_trades.csv` | every paper option trade: entry, exit, reason, P&L |
| `paper_track_holdings.csv` | the sandbox book its daily series is measured from |

**Paper only.** Tradier sandbox fills on delayed quotes, entries at the ask and exits at the
bid. No real money and no real orders. It is a forward, out-of-sample record — which is the
one thing the backtest cannot claim — and it is thin, and thin records mean very little.

To restore the sandbox tables: read `paper_track_history.json` and re-insert into
`paper_index_track`, `paper_index_holdings`, `paper_option_orders` and `option_alerts`.
Column names in the JSON match the table columns exactly, which is why the JSON is stored raw
rather than summarised.

To restore the bound Index: copy `valquo_index_track.csv` to `data/valquo_track_history.csv`
and `valquo_index_meta.json` to `data/valquo_track.json`. The column names are deliberately
identical to the tracker's own, so this is a copy and not a transformation.

**Why the bound Index is committed here when `data/` is gitignored.** `data/` is ignored
because it holds the licensed Sharadar exports, which may not be redistributed. The bound
series is a different object: Valquo's own output, a few hundred bytes, derived and
unlicensed — and until 2026-08-10 it existed on exactly one laptop, with no writer anywhere
in this repository able to reproduce it. This copy is a BACKUP, never an input: nothing reads
it back, and `index_track.load()` still reads `data/` and only `data/`, so there is still
exactly one authority for what the Index did.

No secrets: market data, timestamps and sandbox order ids only.
