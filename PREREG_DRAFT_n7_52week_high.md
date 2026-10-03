# PREREG DRAFT — N7, 52-WEEK-HIGH PROXIMITY

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Don's Addition 2 candidate.
**Ranked LAST of the cross-sectional arms, for a reason that is a fact rather than a judgement:
it is already a shipped input to the composite.**

---

## 1. MECHANISM AND THE ONE FACT THAT DECIDES ITS RANK

George–Hwang's result is that a stock's price relative to its 52-week high predicts returns, and
predicts them *better* than standard momentum — the 52-week high acting as an anchor that investors
under-react to.

**`high_prox` IS ALREADY ONE OF THE THREE `momentum` Z-COLUMNS IN THE SHIPPED COMPOSITE.** The
AST-derived census is `momentum = {ret_12_1, ret_6_1, high_prox}`. So this is **not a new signal on
this panel** — it is an incumbent input, scored on every date since the panel was built, and
carried at one third of a theme that holds 0.125 of the weight.

**ARM — ONE arm.** A long-only book inside the N1 small/mid-cap band selected on **`high_prox`
alone**, at the served construction's weighting, 8% cap, 0.30 band, quarterly rebalance. The
question is not *"is this signal real"* — the panel has been scoring it for months — but *"does a
standalone small-cap book on it beat SPY net of cost"*.

## 2. EVIDENCE *FOR*

* **Zero build cost.** `high_prox` is a banked panel column at every date; the band and floor come
  from `N1`. Nothing to construct, nothing to validate, no pull.
* **It is the one Addition 2 candidate whose literature claim is about DOMINATING an incumbent**,
  so it is a sharper question than "does it add": if a `high_prox`-only book beats the composite's
  served book, that is informative about the composite's construction as well as about the signal.
* **`momentum` is a theme the book genuinely loads on** — `R1`'s corrected re-run puts **UMD at
  +0.205, *t* +3.65**, one of only two significant loadings — so the family is live rather than
  speculative.
* **`S16`'s rank-identity trap does NOT apply.** Extracting one of three averaged z-columns is not
  a monotone re-expression of the theme: `momentum` is `mean(z_ret_12_1, z_ret_6_1, z_high_prox)`,
  and a single component does not preserve that mean's ordering. (The register should verify this
  rather than assume it — §5, K2.)

## 3. EVIDENCE *AGAINST*

* **`P6`'s rule is the direct objection and it has five demonstrations.** A component's own IC does
  not predict what a book built on it does; `S16`'s buyback-only arm posted the **best theme IC of
  its four at +3.21**, clearing `X7`'s 2.71, **and still failed the gate** — which `CLAUDE.md` calls
  *"the fifth demonstration that theme IC does not judge a construction change."*
* **`X3` is the sharper form**: `size` has the **worst** theme IC (−0.30) and carries the
  composite's **entire** significance. Component-level attractiveness is not book-level value.
* **It is momentum, in the weak space, with no event.** Per `SEARCH_DOCTRINE` §1.4 the
  cross-section's 80%-power MDE is **0.4274–0.5071 SD**, approximately the largest effect the panel
  has ever held, and **a 52-week-high tilt has no dated event** so it cannot be moved into the
  high-power space. It is structurally the weakest design in Addition 2's list.
* **It needs DAILY prices, which ties it to Part B's expensive pull.** `high_prox` is proximity to
  a **252-day daily** high. The pre-2009 eras therefore require **`crsp.dsf`** (0.4–1 GB), and the
  cheap `crsp.msf` fallback turns it into a 12-month-high approximation — **which voids the frozen
  definition for exactly this column.** So of all the arms here, this is the one whose pre-2009
  check is most sensitive to which price file gets pulled.
* **Momentum in small caps is where transaction cost is worst**, because the names that have run
  are the ones with the widest spreads and the highest turnover. `P1`'s **87 bps at $1M** on a
  concentrated all-cap book is the relevant upper bound.

## 4. BAR AND MDE

**Bar: charter clause 1** — net-of-cost return vs SPY, long-only, Roth, built on **2009–2019 × half
the tickers** and checked **once** on **2020–2026 × the other half**, against the served book's
**+1.9488pp/yr** and recent-half **+0.2702pp**.

**MDE.** Row set changes; no paired SE. A single-column small-cap momentum book is the least
diversified and highest-turnover design in Part C, so its tracking error — and therefore its
detectable edge — is the largest. Print it before scoring. Equity `N` **252**, hurdle **3.3254862**
(derived).

## 5. THE FREE PRE-OUTCOME KILLS

**K1 (FREE). The incumbent-decomposition disclosure.** Report, before any return, the mean per-date
rank correlation between a `high_prox`-only ranking and the full `momentum` theme's ranking, and
between it and the **composite**. **This is a disclosure and not a kill**: a high correlation with
`momentum` is expected and is not disqualifying, but it must be on the record so the result is
attributed to the right object.

**K2 (FREE). Verify the non-identity.** Confirm the `high_prox`-only ordering is **not** the
`momentum` theme's ordering at within-date rank correlation 1.0. If it is, the arm is the theme
renamed and `S16`'s closure applies verbatim.

**K3 (FREE). The price-file dependency, stated in advance.** Declare which price file the pre-2009
check will use and what it costs the definition: `dsf` preserves the 252-day daily high exactly;
`msf` does not, and a `high_prox` built on monthly data is **a different column wearing the same
name**.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption.** Derive it; derived today **vintage 4, OPEN since
2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES for 2009–2026** (banked panel column). **CONDITIONAL for the pre-2009 eras** — it
is the one arm in Part C that genuinely requires the **daily** CRSP pull rather than being
indifferent to it.
