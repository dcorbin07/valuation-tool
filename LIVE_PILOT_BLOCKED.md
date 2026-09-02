# LIVE PATH, PERCENTAGE-OF-EQUITY — NOT BUILT. The §8 gate fired.

**2026-09-02, app-fixer lane. No code was written. No order path exists. Nothing is armed.**

The instruction was *"per contract §8 (refuse to build if §8 is absent)"*. **§8 is absent.** So
this document is the deliverable: the evidence for that, the STEP 0 answer — which is a fact
about a vendor and needs no §8 — and what §8 has to settle before anyone builds this.

---

## 1. THE GATE — verified, not assumed

`PAPER_TRACK_CONTRACT.md` on `origin/main`, 1,156 lines. Its sections are **0a, 0, 1, 2, 3, 4,
5, 5a, 5b, 5c, 5d, 6 (incl. 6.6), 7.** It ends at *"§7. Known gaps this contract does not itself
fix"*. **There is no §8, and no cross-reference to one anywhere in the file.**

Checked four ways, because a refusal should not rest on one grep:

* my working copy is **byte-identical to `origin/main`** (`git diff --stat` empty), so this is
  not a stale checkout;
* the last three commits touching the contract are `09ea4cc`, `df5e637`, `66cc47e` — none adds
  a section;
* the other files in the repo carrying a "§8" are **pre-registration documents** (`PREREG_o11…`,
  `PREREG_s10…`, `PREREG_sc1b…`, `HANDOFF_edge_audit.md`), whose §8 is a register's own
  numbering and has nothing to do with the paper-track contract;
* **`LIVE_PCT`, `LIVE_PILOT_ENABLED`, `MAX_DAILY_LOSS_PCT`, `MAX_DRAWDOWN_PCT` and
  `LIVE_PILOT_DRYRUN_SESSIONS` appear nowhere in the repository** — no code, no doc, no test.

**AND THERE IS A SECOND STANDING RULE POINTING THE SAME WAY, which the brief does not mention.**
`CLAUDE.md` carries, as a hard rule: *"**Do NOT execute trades or move money** — a Robinhood
connector exists (Cowork side); produce target/rebalance lists, Don executes."* A live order
path is the thing that rule exists to forbid. §8 would have to supersede it **explicitly and in
writing**, not by implication, and the supersession should be visible in `CLAUDE.md` too or the
next agent reads a rule that is no longer true.

**`.env.example` IS DELIBERATELY NOT WRITTEN EITHER**, and that is the one refusal worth
arguing for rather than merely stating. A tracked file documenting `LIVE_PCT`,
`MAX_DAILY_LOSS_PCT` and `LIVE_PILOT_ENABLED` would describe a mechanism that **does not
exist**. Someone could reasonably set those variables on Render and believe a stop was in force.
**A documented safety control that nothing reads is worse than no control at all**, because it
is indistinguishable from one that works until the day it is needed.

---

## 2. STEP 0 — THE ANSWER IS NO, AND THE VENDOR'S OWN SOURCES DISAGREE WITH EACH OTHER

**Tradier's API reference states the equity order `quantity` is "The number of shares to be
ordered, _in whole numbers_."** That is the contract the code would be written against.
Fractional shares are not mentioned; the FAQ is silent on them, on notional orders and on
partial shares.

**The marketing page says otherwise** — *"trade equities, including fractional shares"* — which
is a claim about the brokerage, plausibly through its own app or a separate product. **Where a
vendor's marketing and its API reference disagree, the reference is the one that governs an
order your code places.** Treat fractional support as **unavailable on the API order path**
until someone demonstrates the opposite against a sandbox account, which is a test nobody should
run before §8 exists.

**No order was placed, in any environment, to establish this.** It is read from the published
documentation.

---

## 3. WHAT WHOLE-SHARE-ONLY DOES TO THE BOOK — measured on the real Index

68 published holdings, their published weights, their recorded entry prices as a stand-in for a
live quote. Prices run **$19.31 to $2,271.31, median $125.12**.

| account equity | names getting ZERO shares | % of money deployed | weight tracking error |
|---:|---:|---:|---:|
| $1,000 | **67 of 68** | 2.6% | 97.4% |
| $2,500 | 60 | 12.8% | 87.2% |
| $5,000 | **51** | 27.8% | 72.2% |
| $10,000 | 32 | 51.9% | 48.1% |
| $25,000 | 14 | 72.6% | 27.4% |
| $50,000 | 6 | 85.3% | 14.7% |
| $100,000 | 2 | 92.0% | 8.0% |
| $250,000 | 0 | 96.2% | 3.8% |

**Below roughly $100,000 the whole-share book is not the Index.** At $5,000 three quarters of
the money never gets invested and three quarters of the names are missing — what remains is a
concentrated position in whichever names happen to be cheap, which is a **different strategy**
with none of this project's evidence behind it.

**And the constraint binds per name, not on average.** MKL at $1,841/share on a 1.43% weight
needs **$128,561 of account equity** before one share is affordable at its weight; FCNCA needs
$126,269. So a percentage-of-equity pilot at, say, `LIVE_PCT=10` on a $50,000 account is a
**$5,000 book — the 51-zero-name row** — not a small version of the Index.

**THIS IS THE FINDING THAT SHOULD SHAPE §8.** The brief's design — percentage of equity, no
dollar cap — is coherent only if fractional shares work. Without them there is an implicit
minimum account size of roughly $100k–250k for the book to resemble what was backtested, and
below it the pilot would be testing something nobody has measured. Whichever way §8 goes, it
should say which of these it intends:

1. require fractional execution, and therefore a venue whose **API** supports it (Tradier's
   documented one does not);
2. state a minimum `LIVE_PCT × equity` below which a slot refuses to arm, derived from this
   table rather than chosen;
3. deliberately trade a **reduced book** — in which case that book needs measuring before it is
   funded, not after.

---

## 4. WHAT §8 MUST SETTLE — offered as input, not as a design

Not built, and not to be inferred from this list. Recorded because the questions surfaced while
checking the gate and they are cheaper to answer now than after a first fill:

* **Supersession.** Explicit words releasing `CLAUDE.md`'s "do not execute trades or move money"
  for this path, and only this path.
* **Minimum viable book**, from §3 above — the one thing the brief's design does not contain and
  cannot be derived without the fractional-share answer.
* **What a "session" is** for `LIVE_PILOT_DRYRUN_SESSIONS`. A cycle? A trading day? The brief's
  dry-run gate is counted in them and the count is meaningless until the unit is fixed.
* **Who the loss stops are measured against.** `MAX_DAILY_LOSS_PCT` "% of the book" — the live
  book, or the target book? Those differ by exactly the undeployed cash in the table above, and
  at small equity that is most of it.
* **What happens to an armed slot when equity moves intraday**, given the target is
  `LIVE_PCT × current equity` read every cycle: a falling market shrinks the target below what
  is already held, and "buys never exceed it, sells never blocked" does not say whether that
  forces a sell.
* **Whether the vintage clock resets.** Trading the book live is not obviously a scoring change,
  but it is the first time the contract's object would exist as a funded position, and §5a's
  vintage rule was not written with that case in view.

---

## 5. STATUS

**Nothing was built. No token was entered, requested or read. No order was placed in any
environment, live or sandbox. No file under `valuation/` changed.** The repository is exactly
as it was, plus this document.

**Unblocks when `PAPER_TRACK_CONTRACT.md` carries a §8 authorising this path.** At that point
the design review this brief asks for has something to review, and §3 above is the first input
it should take.
