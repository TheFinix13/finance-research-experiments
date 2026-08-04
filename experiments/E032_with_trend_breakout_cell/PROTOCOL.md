# E032 — With-trend H4 breakout-continuation cell (second-strategy candidate)

Status: **PRE-REGISTERED 2026-08-04** (commit hash recorded below once
pushed). No Stage-1 outcome has been computed at registration time.

Follows `PROTOCOL_DISCIPLINE.md` in full.

---

## 0. Motivation (hypothesis-generating evidence, not proof)

The deployed book is fade-only (`zone_d1_against` fades the D1 trend).
In the 2026-07-28 → 08-03 live week the two largest moves — EURUSD
+200p up, USDCAD −140p down — were structurally invisible to it. Three
hand-picked with-trend entries on that tape (EURUSD impulse-close long
Jul 29 16:00; EURUSD continuation long Jul 30 08:00; USDCAD breakdown
short Jul 29 16:00) all reached mechanical 1.5R TPs (verified on
Dukascopy H4, MAE 10–21p). This is a 3-trade hindsight anecdote from a
single week and is quarantined as motivation only.

**Priors AGAINST, stated for the record:**

- E004 found `against` beat `with` for ZONE-TOUCH entries — but that
  is an entry-class statement about fading zones, not about breakouts.
- E030 London-continuation drift: DEAD (session-level with-trend drift
  does not exist as a holdable edge on M15).
- M001 A4 Chigiri (breakout-momentum, the designated anti-thesis to
  the zone fade) v1 posted the squad's weakest quality: TQS 0.229,
  win 39.9% over 11y — naive breakout logic underperforms; its
  planned refinement is three conjunctive guards (multi-TF ADX rising,
  top-decile σ, 20-bar high/low), which informed this design.

If this family dies, that is a valid and useful outcome: it closes the
"we're missing the big moves" complaint with evidence.

## 1. Hypothesis (operational)

- **H1:** A D1-aligned H4 breakout-continuation entry with the
  deployed exit geometry (bar-structure SL, fixed 1.5R TP) has
  positive per-trade expectancy at base costs on EURUSD/GBPUSD/USDCAD,
  OOS-stable.
- **H0:** expectancy ≤ 0 at base costs, or unstable across folds.

Outcome metric: **mean pips/trade at base costs** (primary) and pooled
Sharpe of per-trade R (secondary), per cell.

## 2. Separation

- Touches the trading agent: **no**. Detector implemented lab-side in
  `programs/E032/`; the D1-trend operationalisation copies the
  production `_htf.py` rule (lookback 10 D1 bars, net move ≥ 60p) so a
  surviving cell is directly translatable, but no agent code changes.
- A surviving cell is a **candidate for a NEW routed cell**
  (`htf_with_breakout`) beside the existing fade cell — never a
  modification of `zone_d1_against`. Deployment (if ever) goes through
  the agent's full validation chain (grid → holdout → walk-forward →
  cross-pair → sealed) and a routing decision, exactly like the
  original strategy did.

## 3. Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| D1 trend filter | Production rule, mode WITH: last 10 D1 bars net move ≥ 60p defines trend direction; no trend → no trade | Translatability; same regime lens as production |
| Entry (long; short mirrored) | H4 bar CLOSES above max high of prior N H4 bars, in D1-trend direction, AND bar range ≥ k × ATR14(H4); enter at bar close | Breakout + impulse quality guard (Chigiri-refinement-informed) |
| Grid | N ∈ {10, 20}; k ∈ {1.0, 1.5} | 4 arms; smallest honest grid |
| Stop | Breakout bar's opposite extreme (bar low for longs); floor 10p | Structure stop, mirrors live-week counterfactual definition |
| Take profit | Fixed 1.5R | Deployed geometry; keeps comparability with the fade cell |
| Position rule | One position per symbol; signals while open are dropped (cap=1) | Keeps E032 orthogonal to E031 |
| Sizing | Fixed 1.0% risk per trade | Expectancy study; sizing out of scope |
| Costs | Round-trip spread 1.0p EURUSD, 1.5p GBPUSD, 2.0p USDCAD; stress sensitivity ×2 spreads reported | Base-cost convention |
| Symbols/TF | EURUSD, GBPUSD, USDCAD H4 | Deployed universe |

Family size at screen: **12 cells** (4 arms × 3 symbols).

## 4. Statistical pipeline

| Stage | Data | Period | Family | Test |
|---|---|---|---|---|
| 1 screen | 3 pairs H4 | 2015-01-01 → 2021-12-31 | 12 | mean pips/trade > 0, one-sided bootstrap p, BH-FDR α=0.05; n ≥ 100 trades/cell else `parked_insufficient_n`; ≥ 4/5 time folds positive |
| 2 confirm | 3 pairs H4 | 2022-01-01 → 2024-12-31 | survivors | per-cell α=0.05, no re-tuning, n ≥ 40 |
| 3 sealed | 3 pairs H4 | 2025-01-01 → 2026-07-25, run ONCE | survivors | report only; negative-at-stress kills |

Data-ledger notes: EURUSD H4 2015–2021 8th registered use — overuse
acknowledged; hypothesis is orthogonal to all prior uses of the slice
(no prior experiment tested breakout-continuation entries on H4). H4
2025+ sealed slices previously touched only by E005 (documented).
GBPUSD H4 2015–2024 carries an E005/E006 sealed history — prior use
documented; this study's claims on GBPUSD are therefore
`screen+confirm`-grade unless the sealed stage is reached, and the
REPORT must carry that caveat.

## 5. Stop rules

- Stage 1: 0/12 cells alive → STOP, file STOP_NOTICE. The "missing
  the big moves" thesis is then closed as not mechanically capturable
  under this operationalisation (folk-concept clause: closes this
  definition, not every conceivable with-trend entry).
- Any cell alive at sealed → candidate handed to the agent validation
  chain. If E031 also lands alive arms, a pre-registered JOINT slot
  simulation (both strategies feeding one book) is REQUIRED before
  any deployment decision — a second signal stream mechanically
  raises slot contention and interacts with any cap change.
- The 2026-07-28 → 08-03 live week is BURNT as motivation and must
  never be cited as out-of-sample support for any surviving cell.

## 6. Amendments

(none at registration)

---

**Pre-registration commit:** `c838b28` (pushed 2026-08-04, before any
Stage-1 computation)
