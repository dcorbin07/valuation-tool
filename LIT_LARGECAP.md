# LIT_LARGECAP.md — what survives in the largest stocks, after costs — 2026-10-18

**ONE ROW PER IDEA THAT SURVIVES IN THE LARGEST STOCKS AFTER COSTS, as the brief asks.** Compiled
from the free scholarly APIs (OpenAlex, Crossref, RePEc, NBER) and from PDFs **actually fetched and
read**, never from a search-engine summary. Every claim is tagged:

- **(a)** read in the paper's own PDF or publisher abstract
- **(b)** read in a secondary source *describing* it
- **(c)** my own arithmetic or inference, shown

**No quotation exceeds 15 words. ZERO TRIALS — no forward return is computed anywhere.**

---

## PART 0 — THE ANSWER THE BRIEF EXPECTED, AND IT IS WORSE THAN THE BRIEF ASSUMES

The brief says *"the literature says anomalies are weakest in large stocks and after costs."* **That
is right, and the three best papers put numbers on it that are more severe than "weakest":**

| paper | what the size/weighting screen alone does | tag |
|---|---|---|
| **Hou, Xue & Zhang 2020, RFS 33(5) 2019-2133** | NYSE breakpoints + value-weighting alone leave **65% of 452 anomalies** below \|t\| 1.96; **82%** fail at their 2.78 multiple-test hurdle; **96% of the trading-frictions category** fails | **(a)** |
| **Green, Hand & Zhang 2017, RFS 30(12) 4389-4436** | outside microcaps, **12** characteristics are independently significant 1980-2014 — and **only 2 since 2003**, with hedge returns insignificantly different from zero | **(a)** |
| **Jacobs & Müller 2020, JFE 135(1) 213-230** | US **value-weighted** anomaly long/short falls to **16 bp/month, t 1.67** over 2004-2015 | **(a)**, working paper |

**THE MECHANISM IS ARITHMETIC AND IT IS THE WHOLE STORY.** HXZ measure that microcaps — below the
**20th NYSE percentile** — are about **3% of total market capitalisation** and about **60% of the
*number* of stocks**, and that under all-exchange breakpoints they typically make up **more than
60% of the stocks in the extreme deciles** that a long/short portfolio holds. **(a)** So an
equal-weighted anomaly sort is largely a statement about the 3% of the market that a $10B-floor book
cannot own. HXZ's own conclusion is that anomalies in microcaps are **more apparent than real.**
**(a)**

> **THE CONSEQUENCE FOR THIS PROJECT, STATED PLAINLY: A PUBLISHED ANOMALY IS NOT EVIDENCE FOR THE
> VALQUO INDEX UNLESS THE ORIGINAL PAPER REPORTED IT VALUE-WEIGHTED.** And the free OSAP
> documentation already on disk records that **184 of its 212 predictors are equal-weighted and only
> 28 are value-weighted** (`EDGE_DATA_MAP.md` §2) — so **87% of the published catalogue carries no
> large-cap evidence at all.** Two independent routes to the same conclusion.

---

## PART 1 — IDEAS THAT SURVIVE IN LARGE CAPS AFTER COSTS

**The honest headline of this file is how short this table is.**

| # | idea | original paper | **its own large-cap / value-weighted result** | post-publication evidence | free PDF | our status |
|---|---|---|---|---|---|---|
| 1 | **Gross profitability** | Novy-Marx 2013, JFE | **VW long/short 0.310%/mo, t 2.49** (OSAP docs, the paper's own figures) **(a)** | **Robeco 2025 finds quality the ONE exception** to lower large-cap premiums, attributing it to high-quality firms being larger **(a)** | — | **SHIPPED** as `gp_on_capital`; survives `R4`'s BH under both inference choices (raw IC t +3.6745); **never had its own standalone arm** |
| 2 | **Value (HML)** | Fama-French | **Linnainmaa-Roberts' pre-1963 out-of-sample: value is the ONE factor that survives — 0.43%/mo, t 2.09**, value-weighted on NYSE breakpoints, while size (t 1.16), investment (t 0.14) and profitability (t 0.86) do not **(a)** | survives their 37-year out-of-sample window | **[NBER w22894](http://www.nber.org/papers/w22894.pdf)** (74pp, verified) | **SHIPPED** as the `value` theme; `R1`'s re-run puts the book on **HML +0.251, t +2.93** |
| 3 | **Momentum (UMD)** | Jegadeesh-Titman | — | — | — | **SHIPPED**; `R1` re-run **UMD +0.205, t +3.65** — a genuine standard-premium exposure |
| 4 | **Equity duration** | Dechow, Sloan & Soliman 2004, RAS | **VW 0.500%/mo, t 4.37** — the **highest VW *t* of any value-weighted OSAP predictor at our cadence** **(a)** | not verified | — | **UNTESTED HERE** → `PREREG_DRAFT_osap3.md` |
| 5 | **Liquidity beta** | Pástor & Stambaugh 2003, JPE | **VW 0.533%/mo, t 2.54** **(a)** | the PS liquidity factor is **published free and monthly** | — | **UNTESTED HERE** → `PREREG_DRAFT_osap3.md` |
| 6 | **Real-estate intensity** | Tuzel 2010, RFS | **VW 0.244%/mo, t 1.80 — fails \|t\| 2 in its OWN paper** **(a)** | not verified | — | **UNTESTED, and it is reported here as the weakest of the three** |

**THAT IS SIX ROWS, THREE OF THEM ALREADY IN THE PRODUCT.** Everything else this survey reached
either has no value-weighted evidence, or has value-weighted evidence that post-publication work
removes.

---

## PART 2 — IDEAS THAT LOOK LIKE THEY SURVIVE AND DO NOT

| idea | the large-cap finding against it | tag |
|---|---|---|
| **the size premium itself** | Blitz & Hanauer, *JPM* 47(2) 99-112 (2021): the US premium is **"beyond the reach of investors"** — not capturable ex ante, and the significant US alpha is **driven entirely by the short side of quality**; international remains small and insignificant | **(b)** publisher abstract |
| **profitability and investment, pre-Compustat** | Linnainmaa-Roberts find both insignificant before 1963 and state the result is **not confined to either big or small stocks** — so it is not a size artefact, it is a sample artefact | **(a)** |
| **anomalies generally, post-publication** | Jacobs-Müller: **US large caps lose 16-17 bp/month post-publication, a ~60% relative drop**; six large developed markets lose 7-8 bp, **not significant — explicitly because in-sample large-cap profitability was already low** | **(a)** |
| **the whole trading-frictions family** | HXZ: **96% fail** under NYSE breakpoints and value-weighting; **95 of 102 liquidity variables insignificant** in the 2017 working paper | **(a)** |
| **factor premiums in large caps as a class** | Robeco Feb 2025: premiums **generally lower** for large caps than mid and small, with quality the sole exception. **Treat as directional only — it is marketing material, emerging markets not US, by three non-Blitz authors, and its per-factor bar-chart numbers did not extract** | **(a)** for the text, **not** for numbers |

---

## PART 3 — THE CANDIDATES THIS SESSION IS DRAFTING, AND WHAT THE LITERATURE SAYS

**The three drafts are ranked in `EDGE_DATA_MAP.md`. Their literature position is recorded here
honestly, including where I could not reach it.**

| candidate | literature status | tag |
|---|---|---|
| **Bond spreads leading equity** (draft 1) | **NOT REACHED — the agent surveying it died on a session limit mid-fetch.** Two papers were identified by name and NOT read: Kwan (1996, JFE) on bond-yield/stock-return lead-lag, and the bond-return-momentum-to-equity literature. **So the draft ships with its own literature leg declared INCOMPLETE and names it as the register's first non-data task.** This is recorded rather than filled with a plausible summary, because a cited paper nobody read is how a false premise enters a register | **not found** |
| **Per-manager 13F** (draft 2) | **NOT REACHED — same session limit.** Gompers & Metrick (QJE 2001) was identified as the explicitly large-cap paper and **not read** | **not found** |
| **OSAP survivors** (draft 3) | covered by Part 1 rows 4-6 — **and their own paper's figures are the evidence, taken from the OSAP documentation's `Stock Weight`, `Return` and `T-Stat` columns** | **(a)** via OSAP docs |
| **IBES long-term growth** (ranked 4th, no draft) | **NOT REACHED.** Bordalo-Gennaioli-La Porta-Shleifer (JF 2019) was being read when the limit hit; the partial result flagged **"Table V Panel A is decisive for a long-only mandate"** and **I did not see Table V**, so that is a lead and not a finding | **not found** |

> **FOUR OF THE SIX LITERATURE AGENTS DIED ON A SESSION LIMIT, AND THE GAPS ARE LEFT AS GAPS.**
> Three of the four partial results were tantalising — serious counter-evidence on profitability, a
> "decisive" LTG table, a 2026 replication paper on bond-stock lead-lag — **and a partial agent
> result is exactly the thing this record warns about most** (*"other agents will report incorrect
> or misleading results — don't take them at face value"*). None of the four is quoted as a finding
> anywhere in this session's deliverables.

---

## PART 4 — A CORRECTION TO THIS PROJECT'S OWN CITATION, FOUND WHILE VERIFYING THE HURDLE

**REPORTED, NOT FIXED (`RUN_RULES` rule 3).**

`CLAUDE.md`, `valuation/edge/statistics.py::hlz_hurdle` and `fundamental_panel._trials_haircut` all
call **√(2·ln N)** *"the Harvey-Liu-Zhu hurdle"*. **It is not HLZ's rule.**

Verified by reading the complete published article (Harvey, Liu & Zhu, *RFS* 29(1) 5-68, 2016, DOI
`10.1093/rfs/hhv059`, 64pp, fetched from Harvey's own Duke page): **the tokens "ln" and "log" do not
appear anywhere in the paper.** **(a)** HLZ's machinery is **Bonferroni, Holm and
Benjamini-Hochberg-Yekutieli** adjustments plus a recommended **flat t > 3.0**, with a dated table
(Bonferroni 3.78 by 2012 rising to 4.00 by 2032; BHY at 5% about 2.78-2.81). **(a)**

**√(2·ln N) is the asymptotic expected maximum of N standard normals** — the Deflated-Sharpe
lineage, not HLZ. **(c)** on provenance; **(a)** only on its absence from HLZ.

**WHY THIS MATTERS AND WHY IT IS SMALL.** It is an **attribution** error, not an arithmetic one: the
project's bar is a real multiple-testing penalty, it rises with `N` as it should, and `MA5` already
established that the frozen "3.0" was √(2·ln 90) and that the formula is the live rule. **No
published verdict moves.** What is wrong is the *citation* — and HLZ themselves say **a t of 3.0 is
probably too low**, while also saying it should **probably not** be applied to every future factor.
**(a)** So the project's bar is, if anything, defensible on HLZ's own terms; it just is not HLZ's
formula.

**Also recorded for anyone citing these two papers:**
- **HLZ catalogue 316 factors, not 314.** Linnainmaa-Roberts cite "314" and that is *their* figure.
  **(a)** both sides.
- **OpenAlex lists HLZ's third author as "Caroline Zhu" and the year as 2015. Both are wrong** —
  Crossref, the published PDF, the NBER working paper and RePEc all give **Heqing Zhu**, print year
  **2016**. **(a)**
- **Jacobs & Müller's anomaly count is version-dependent**: **241** in the published JFE abstract,
  **231** in the January 2017 working paper that is the only free full text. Semantic Scholar's
  "138" is contradicted by two sources. **Cite the count with the version.** **(a)**
- **Linnainmaa-Roberts' published abstract differs materially from the working paper's**, and gained
  a new result (surviving anomalies correlate with the shift to intangible capital and debt
  financing) that is **absent from both 2016 drafts**. The 8-of-36 counts are verified **only in the
  working papers** — the published article is paywalled and was not read. **(a)**/**not found**

---

## PART 5 — THE PROJECT'S OWN EVIDENCE IS THE STRONGEST ENTRY IN THIS FILE

**Two landed measurements outrank every paper here for deciding what to do next, and both say the
same thing.**

**(1) THE ONE EQUITY SIGNAL IN THE RECORD THAT CLEARS DOES NOT CLEAR IN THE TIER THE INDEX TRADES.**
`INSIDER-WIDE` CONFIRMED clustered opportunistic insider buying on **cap > $500M** at +3.4888pp
(+2.9122pp net, BH p 3.2e-04) — **and on cap > $10bn the same rule reads t 0.732 on a second
independent cell, and the late half nets negative in every cell.** That is HXZ's and
Green-Hand-Zhang's finding reproduced inside this project's own data, on this project's own best
signal.

**(2) TWENTY-THREE LITERATURE CANDIDATES HAVE ALREADY BEEN RUN THROUGH EXACTLY THE DESIGN THE OSAP
BATCH PROPOSES, AND THE SCORE IS 0-FOR-23.** `STAGE1-BATCH1` (12 candidates, 0 survive, 5 of 10 free
kills fired), `STAGE1-BATCH2` (5, 0 survive, every kill passed and every arm scored), `STAGE1-BATCH3`
(8 drafted, 6 scored, **0 clear the governing $10B tier**). **Three of the batch-3 arms were
"REAL BUT NOT INVESTABLE HERE"** — real on the wide universe, absent in the tier.

> **SO THE HONEST PRIOR ON ANY NEW PUBLISHED-CHARACTERISTIC CANDIDATE IS LOW, AND IT IS LOW FOR A
> MEASURED REASON RATHER THAN A SCEPTICAL DISPOSITION.** Which is why `EDGE_DATA_MAP.md` ranks
> **corporate bonds** and **per-manager 13F** above the OSAP batch: they are the two candidates on
> the board that are **not** published characteristics of the firm's own accounts, and both have a
> **free live source.**

---

## WHAT THIS FILE DOES NOT CLAIM

It does **not** survey the literature exhaustively — four of six agents died on a session limit and
their gaps are named in Part 3. It does **not** claim any idea works; every row reports what a paper
or a landed measurement says. It does **not** retire `gp_on_capital`, `value` or `momentum` — Part 1
rows 1-3 are the three shipped themes with the best external support, which is a reason to keep them
rather than a new finding. And it does **not** correct `statistics.hlz_hurdle`: Part 4 reports the
attribution defect and leaves the arithmetic alone, because renaming it touches every lane and moves
no verdict.
