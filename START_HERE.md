# START HERE

The one page that takes you from `git clone` to knowing what is true. Written for a stranger —
a new agent, a new collaborator, or Don in six months — because the bus test (master audit MA17)
found that **the code survives a stranger and the claims do not**: every guard and gate is
verifiable from a clean clone, and not one headline number is.

---

## 1. What this repository is

**Valquo** (valquo.co) — a Flask stock-analysis SaaS. Three things share one codebase:

| | what it does | where it lives |
|---|---|---|
| **Valuation engine** | adaptive DCF for any ticker, live data, no key needed | `valuation/engine/`, `valuation/data/` |
| **Screener** | 9-theme "hot score" over the market, plus options/intraday signals | `valuation/screener/`, `valuation/intraday/` |
| **Edge Lab** | the point-in-time backtest that tries to disprove the screener | `valuation/edge/` |

The Edge Lab is the unusual part: it exists to **falsify** the product, and most of what it has
produced are rejections and nulls.

## 2. Clone to green suites (no data, no keys, ~5 minutes)

```bash
git clone <repo> && cd valuation-tool
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt                  # NOT the .lock files — see §5
python tests/test_edge.py                        # the biggest single suite
for f in tests/test_*.py; do python "$f" || echo "FAILED $f"; done   # all of them
```

**Every suite passes with no `data/` directory at all** — that is what CI does on every land,
since `data/` is gitignored and the runner never has it. So a stranger can verify every guard,
gate and pinned identity in the repo. Judge a suite by its **exit code**, never by grepping for
`OK`: they print at least three different summary formats.

## 3. Clone to a number — you cannot, and this is the honest reason

Every published figure comes from `data/backtest`, licensed Sharadar exports that are gitignored
and roughly 18 GB. `BACKTEST_RUNBOOK.md` does document how to rebuild them with a
`SHARADAR_API_KEY`, so the path is written down. The barrier is narrower and worse than a missing
document:

> **Sharadar's terms are personal-use only and forbid commercial use of the data "or any
> derivation"** (ledger row `D1`, verified 2026-08-06).

So a stranger can reproduce the numbers only under a licence that would not let them publish what
they derived. **State this before quoting any headline to anyone.** The same applies to the JKP
international factor data (`data/factors/research_only/`), which is CC BY-NC 4.0, research-only,
and may never ship in the product.

## 4. What is actually true, in five lines

Read these with their caveats or not at all:

- **Top-decile alpha +7.17%/yr** vs the equal-weighted universe, on 2,531 names × 69 quarterly
  rebalances (2009–2026), **gross of costs**, on **one panel**. Costs clear comfortably: breakeven
  134 bps one-way against a measured 33.4 bps.
- **Long-short HAC *t* = 2.62.** It **clears** the project's own placebo-calibrated floor of 2.2837
  and **fails** the Harvey–Liu–Zhu hurdle of 3.29 implied by its own 224 logged trials. Both are in
  `BACKTEST_RESULTS.json` under `multiple_testing.hlz`, including the sentence explaining the
  tension. Quote both or neither.
- **The out-of-sample evidence is X8**, an untuned replication on international data (Japan
  *t* 3.85, developed Europe *t* 4.30, and the **USA is the weakest region tested**). It
  corroborates that the premia are real; it does **not** corroborate Valquo's magnitude.
- **The forward paper track is the real test and it is not due.** Verdict 2031; ~13% power at one
  year. `PAPER_TRACK_CONTRACT.md` is the signed pre-registration.
- **Nothing is auto-adopted.** `cpcv.adopt` is `false`; the live weights are flat 1/7 and were
  never tuned.

## 5. Which file answers which question

| question | file |
|---|---|
| **Where do we stand? Is item X done?** | **`VALQUO_LEDGER.md`** — one row per audit item. This is the contractual answer; never dig through `git log` for it. |
| What are the non-negotiable rules? | `RUN_RULES.md` — short, read first, and now carries the operating instructions too |
| What has been measured, and what was wrong? | `CLAUDE.md` — the findings record. Large, and its *numbers* are trustworthy; treat file:line citations as stale until re-resolved |
| How do I rebuild the data / run the backtest? | `BACKTEST_RUNBOOK.md` |
| How is the panel built, and from what? | `DATA_AND_METHODS.md` |
| What did session N do? | `HANDOFF_<lane>.md` — one per lane, so parallel agents never clobber each other |
| How does a change reach production? | Push a `worktree-*` branch; the gated Action lands it. **Never merge `main` by hand.** |

## 6. Two things that will bite you

- **`requirements.lock.txt` will not install on Windows or on any Python but 3.11.** It is a
  hash-pinned linux/cp311 lock for CI and the container (master audit MA12). Locally, always use
  `requirements.txt`.
- **A landed commit is not a deployed commit.** The shared checkout on Don's machine drifts;
  `scripts/checkout_drift.py` reports it and `scripts/sync_checkout.py` repairs it (MA20).

---

*Educational tool, not investment advice. Fair value is a model output, not a price target.*
