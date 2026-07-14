# E018 — Regime-aware fade gating (pre-registered)

**Status:** PRE-REGISTERED 2026-07-14 · **Thresholds frozen:** 2026-07-14 (before any labelling or backtest)

The deployed strategy `zone_d1_against` is a Supply/Demand zone alpha
(`multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py`,
`SupplyDemandAlpha`) run in **`htf_against` mode**: at a fresh first-touch of
a zone it takes the trade **only when the D1 higher-timeframe bias OPPOSES the
zone direction** (`agent/alphas/concepts/_htf.py::htf_bias_at`;
`HTFBias.opposes`). It **fades** the D1 bias. When D1 bias is `NEUTRAL` the
gate never fires — so the agent **already stands aside on no-bias/range**.

The 2026-07-08 → 07-12 incident logs
(`programs/E017/data/incident_2026-07/{EURUSD,GBPUSD,USDCAD}/*.log`) show the
fade **lost** on EURUSD/GBPUSD (D1 up, price breaking OUT / extending — e.g.
EURUSD 2026-07-09 01:00 SHORT @1.14212 with `htf_bias=up htf=D1(against)`; GBPUSD
2026-07-08 13:00 SHORT @1.33361 `htf_bias=up`) and **won** on USDCAD (D1 down,
clean demand-zone touch on a pullback: 2026-07-08 09:00 LONG @1.41641
`htf_bias=down`). The discriminating axis is **not** D1 direction (both had a
clear bias) but whether the D1-biased move at signal time is a **pullback**
(fade wins) or an **extension/breakout** (fade loses).

E018 asks: **does gating the fade by a causal, past-bars-only regime label
that stands aside when the D1-biased move is a trend extension/breakout (R2)
improve out-of-sample risk-adjusted performance, while the D1-bias remains the
entry condition it already is?**

This is an **alpha-layer** study. Phase 3 (implementation in
`multi-pair-trading-agent`) is **gated** on a positive Phase 2 verdict from
this protocol (§6). If inconclusive or negative → `STOP_NOTICE.md`, nothing in
live code changes (E012/E015/E016/E017 convention).

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered in
[`EXPERIMENTS.md`](../../EXPERIMENTS.md). Literature in
[`../../reviews/refs.bib`](../../reviews/refs.bib).

---

## §0 Reuse declaration (no production code touched in Phase 1/2)

E018 Phase 1 (this document) writes **no code**. Phase 2 builds a labeller +
replay harness **in this repo only** (`programs/E018/`). Production
`zone_alpha.py`, `_htf.py`, `zone_routing.py` are **read-only references** for
parameter values and the alpha-on-the-wire. Nothing here trades or edits live
parameters. Phase 3 (production wiring) is a **separate, gated** deliverable
and touches only the alpha layer (`agent/alphas/**`, `agent/detectors/**`).

| Purpose | Module / artefact | Status |
|---|---|---|
| Fade alpha under test | `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py::SupplyDemandAlpha` (`htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60`) | read-only |
| D1 bias helper | `.../concepts/_htf.py::htf_bias_at` / `HTFBias.opposes` | read-only, reused verbatim |
| Deployed routing | `.../zone_routing.py` (EURUSD/GBPUSD/USDCAD H4 `htf_against`) | read-only |
| Replay engine | `finance-research-experiments/scripts/run_walk_forward_ab.py::_run_alpha_ab` (E013 `all_on` production-matching toggles) | read-only reuse |
| Walk-forward windows | `multi-pair-trading-agent/scripts/run_walk_forward.py` (7× 4yr-IS / 1yr-OOS) | convention reused |
| Stats | `agent/backtest/metrics.py` (`bootstrap_p_value`, `benjamini_hochberg`, `make_scorecard`) | read-only reuse |
| Frozen breakout priors | `programs/M001_multi_agent_ensemble/sim/agents/a04_chigiri.py` (Φ4.1-locked `CHIGIRI_V1_*`) | read-only, cited |
| Frozen trend prior | `programs/M001_multi_agent_ensemble/sim/regime/classifier.py::label_rule_based` (ADX>25 trend convention) | read-only, cited |
| Regime labeller + replay (Phase 2) | `finance-research-experiments/programs/E018/` (new) | to be built |

---

## §1 Committed design (decided by prior architecture work — grounded, not re-litigated)

**Regime taxonomy = 3 (committed):**

- **R1 trend-pullback** — D1 has a bias and, at the signal bar, price is *not*
  extending in the bias direction (a pullback / consolidation into the zone).
  **Fade-favorable.**
- **R2 trend-extension/breakout** — D1 has a bias and, at the signal bar, price
  *is* breaking out / extending in the bias direction (vol-expansion breakout).
  **Fade-hostile.**
- **R3 no-bias/range** — D1 bias is `NEUTRAL`. **Already handled**: the
  `htf_against` gate never fires on NEUTRAL, so the agent already stands aside.

**Strategy↔regime assignment (committed):** R1 → keep `htf_against` fade;
R2 → **STAND ASIDE** (no trade); R3 → STAND ASIDE (already enforced).
Stand-aside is the deliberate, non-overfit answer for R2 — the agent does not
need a breakout alpha, it must simply refuse to fade into an extension. The
dormant `htf_with` trend-follow mode is **NOT** deployed here (it is not even
routable; `zone_routing.py` `Mode` literal / `alpha_for`) and never passed a
gate; `htf_with`/ensemble is a Stage-2-only future candidate behind its own
separate validation.

**The entire new intelligence is ONE binary decision boundary: R1 (pullback)
vs R2 (extension), applied only when D1 already has a bias.**

---

## §2 Frozen regime-labeller specification (FROZEN 2026-07-14, before labelling)

The labeller is **causal** (past-bars-only): at decision bar `i` it reads only
`bars[:i+1]`, mirroring the alpha's own causality contract
(`htf_bias_at` uses the strict-past slice; `_has_touched_before` scans
`[created+5, i)`). **Every threshold below is inherited verbatim from a
pre-existing, documented prior. No threshold is chosen by looking at whether it
flips the 2026-07 incident's losers into winners.** Doing so would invalidate
the study (§6 discipline guards).

### §2.1 D1 bias (defines whether R1/R2 apply at all) — reused verbatim

`bias = htf_bias_at(bars, i, htf="D1", htf_lookback=10, min_move_pips=60.0)`.

These are exactly the deployed `htf_against` parameters
(`zone_routing.py::alpha_for`; `run_walk_forward.py::_make_factories`;
`run_walk_forward_ab.py::_make_alpha`). If `bias is NEUTRAL` → **R3** (the fade
does not fire; excluded from all expectancy cells). No new parameter.

### §2.2 Trend-extension / breakout detector (defines R2) — frozen Chigiri Φ4.1 priors

R2 is flagged when, at bar `i`, a **vol-expansion breakout in the D1-bias
direction** is in progress. Operationalized with the **Φ4.1-locked** breakout
constants from `a04_chigiri.py` (`CHIGIRI_V1_*`, documented lines 98–130 and
the Phase V-a lock note lines 441–447):

| Constant | Value | Source (frozen prior) |
|---|---|---|
| `BREAKOUT_LOOKBACK` (N-bar range) | **20** | `CHIGIRI_V1_BREAKOUT_LOOKBACK` |
| `ATR_PERIOD` (Wilder) | **14** | `CHIGIRI_V1_ATR_PERIOD` |
| `ATR_VOL_LOOKBACK` (median-ATR window) | **80** | `CHIGIRI_V1_ATR_VOL_LOOKBACK` |
| `BREAKOUT_ATR_MULT` (min break magnitude) | **0.50** | `CHIGIRI_V1_BREAKOUT_ATR_MULT` |

**Breakout predicate at bar `i` (Chigiri `_detect_breakout`, verbatim logic):**
1. `i ≥ BREAKOUT_LOOKBACK + ATR_VOL_LOOKBACK + 5` warmup;
2. `ATR14[i]` finite and `> 0`;
3. **vol expansion:** `ATR14[i] > median(ATR14[i-80 .. i-1])`;
4. **range break:** `close[i] > max(high[i-20 .. i-1])` (up) **or**
   `close[i] < min(low[i-20 .. i-1])` (down);
5. **magnitude:** `|close[i] − broken_level| ≥ 0.50 · ATR14[i]`.

Breakout direction `up`/`down` is taken from (4)–(5).

### §2.3 Regime decision rule (frozen)

Given a non-neutral D1 `bias` at bar `i`:

- **R2 (extension)** iff a breakout fires (§2.2) **and its direction aligns with
  the D1 bias** (`bias=UP & up-breakout`, or `bias=DOWN & down-breakout`) — the
  fade would be entered *into* a fresh trend extension.
- **R1 (pullback)** otherwise (bias present, but no aligned vol-expansion
  breakout at the signal bar).
- **R3** iff `bias is NEUTRAL`.

A cross-check tag (**not** used to define R2) also records the stricter Chigiri
*regime-specialist* ratios (`REGIME_MIN_MAG_ATR=1.5`, `REGIME_ATR_MULT=1.5`,
lines 127–128) so a reader can gauge sensitivity of the R2 boundary to a
stricter breakout definition. The **primary** R2 definition is §2.3 (the
detector's own firing predicate); the strict variant is reported for
robustness only.

### §2.4 Secondary trend-context tag (reported, not gating) — frozen ADX prior

For descriptive attribution only, each signal bar also records the lab's
existing trend convention `ADX14(D1-context) > 25 ⇒ trending`
(`classifier.py::label_rule_based`, F18). This is **not** part of the R1/R2
boundary (which is defined solely by §2.3); it is reported so the R1/R2 split
can be described against the established ADX trend/chop convention.

---

## §3 Cells, arms, and metrics

**Counterfactual arms** (identical trade generation, identical costs; the only
difference is which trades are *kept*):

| Arm | Behaviour |
|---|---|
| **baseline** | all `htf_against` fades (current production behaviour) |
| **R2-filtered** | drop trades labelled R2; keep R1 (and R3 never fires) |

**Pairs (frozen, = deployed router):** EURUSD, GBPUSD, USDCAD, all H4 / all
sessions.

**Regime × strategy × pair expectancy cells tested (the FDR family):**
{EURUSD, GBPUSD, USDCAD} × {R1, R2} = **6 cells** (one strategy: the fade). Each
cell's OOS per-trade P&L (pips) is tested with a one-sided bootstrap
(`bootstrap_p_value`, 2000 resamples, seed 42): **R2 cells tested
`alternative="less"`** (negative expectancy), **R1 cells `alternative="greater"`**.
**BH-FDR α=0.05** is applied across all 6 cells (`benjamini_hochberg`).

**Sample-size floor:** a cell with `< 30` OOS trades is reported **underpowered**
and cannot be *concluded* (mirrors `metrics.MIN_TRADES_FOR_EDGE=30` and the
task's ≥30 floor).

**Primary metrics per (arm, pair):** expectancy (pips/trade) with bootstrap
95% CI, profit factor, win rate, daily-equity Sharpe, max-drawdown %, n.

**Robustness:** per-window sign of R2 OOS expectancy across the 7 walk-forward
OOS windows (how many windows show R2 ≤ 0), and the strict-breakout variant
(§2.3) as a sensitivity re-run.

---

## §4 Validation method — walk-forward, train/test integrity

The labeller has **zero free parameters to fit** (all frozen §2), so no
"training" occurs; the walk-forward split exists to test **stability** and to
respect the repo's OOS convention, not to select a threshold.

- Windows inherited from `run_walk_forward.py`: 7 rolling **4yr-IS / 1yr-OOS**
  windows over 2015–2025 (IS 2015-2018→OOS 2019, …, IS 2021-2024→OOS 2025).
- **OOS = the union of the 7 one-year OOS windows (2019–2025).** The gate is
  evaluated on pooled OOS. Per-window OOS is reported for robustness.
- **IS band 2015–2018** (never in any OOS window) is reported **descriptively**
  as a pre-OOS consistency check — it is *not* part of the gate and no
  threshold is tuned on it.
- **Sealed final-year holdout:** the **2025 OOS window** is computed but held
  as the last confirmation read — the verdict must not hinge on 2025 alone; it
  is reported separately and inspected only after the pooled-OOS gate decision
  is written.
- The 2026-07 incident is a **descriptive case study only (n=1)**, never a
  tuning/selection set. Incident bars are outside the 2015–2025 cache and are
  not fed to any statistical test.

Trade generation reuses `run_walk_forward_ab._run_alpha_ab` with the E013
`all_on` production-matching toggles (wick-proof + BE migration + PLG),
`start_index=200`, on the full 2015–2025 series per pair, then trades are split
into IS/OOS windows by entry time. Each trade's regime is labelled at its
**signal bar** (the bar whose close produced the signal = entry-bar-index − 1),
strictly causally.

Costs: `cfg.backtest.cost_for("H4")` (spread 1.0p / slippage 0.5p), TF-invariant
and pair-invariant in the config. The R1-vs-R2 contrast is **within-pair**, so a
uniform cost model does not bias the comparison; this is noted as a limitation
(deployed cross-pair costs are scaled ×1.5/×1.8 but that scales both arms
equally).

---

## §5 Go / no-go gate (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4.

**Stage-1 (R2 stand-aside filter) is `alive` iff ALL of:**

1. **R2 is a real negative edge:** R2-labelled fades show significantly
   **negative** OOS expectancy (`q ≤ 0.05` after BH-FDR across the 6 cells) with
   the **≥30-sample floor met**, in the pooled OOS;
2. **Robust across pairs/windows:** the negative-R2 result holds for the
   majority of deployed pairs (≥2 of 3 pairs at `q ≤ 0.05`, and the third not
   contradicting with a significant *positive* R2 edge), and R2 OOS expectancy
   is ≤ 0 in the majority of the 7 walk-forward windows where the cell is
   powered;
3. **Removing R2 helps the survivors:** the **R2-filtered** arm improves OOS
   risk-adjusted performance of the surviving R1 fades vs the baseline
   (expectancy and profit factor no lower, Sharpe no lower, expectancy-CI lower
   bound no lower) **without destroying sample size** (R1 retains the large
   majority of trades; the drop in n is only the R2 count).

If **all** hold → `alive` → implement the R2 stand-aside filter in the live
alpha layer (Phase 3) with unit + integration tests.

- **`parked_underpowered`** — direction of effect matches but an R2 cell misses
  the ≥30 floor or fails BH on ≥2 pairs. Report; do not ship.
- **`dead` / STOP (write `STOP_NOTICE.md`, change nothing live)** — R2 is not
  significantly negative, or filtering does not improve (or degrades) the R1
  survivors' OOS risk-adjusted performance, or the result is pair-inconsistent.

A clean negative (fade left unchanged) is a fully acceptable, correct outcome.

---

## §6 Discipline guards (anti-overfitting)

- All §2 thresholds are **frozen at this pre-registration** from documented
  priors (Chigiri Φ4.1 breakout constants; ADX>25 F18 trend convention;
  deployed D1-bias params). **No continuous tuning, no post-freeze threshold
  changes, no grid extension.**
- The study is **INVALID** the moment a parameter is chosen by looking at
  whether it flips the 2026-07 losers to winners. The incident is descriptive
  only.
- Multiplicity is accounted with **BH-FDR α=0.05** across the 6
  regime×strategy×pair cells; the R2-filter selection context (1 boundary, 2
  arms, 3 pairs) is reported so a reader can gauge search width
  (`bailey2016pbo`, `bailey2014deflated`).
- A negative/inconclusive result **is reported** (`STOP_NOTICE.md`), never
  buried.

---

## §7 Data-ledger declaration

| Stage | Data | Status this experiment | Prior uses |
|---|---|---|---|
| Replay | EURUSD/GBPUSD/USDCAD H4 2015–2025 (production parquet cache, read-only) | walk-forward OOS regime-conditional expectancy | deployed cell validated on same bars (`zone_routing.py`); E013/E017 read-only reuse |
| Case study | agent live logs 2026-07-08 → 07-12 | one-off descriptive, n=1 | E017 incident replay (descriptive) |

No **new** sealed `(pair, TF, split)` slice is opened; the FDR family is the 6
cells in §3. The 2025 OOS window is treated as the sealed final-confirmation
read (§4).

---

## §8 Cross-references

- Deployed router + validation history: `multi-pair-trading-agent/agent/alphas/zone_routing.py`.
- E013 safety-layer study (same replay harness): `../E013_safety_layer_contribution/REPORT.md`.
- E017 incident source + trade-ledger export pattern: `../E017_confidence_gated_cooldown/`, `programs/E017/export_trade_ledger.py`.
- Frozen breakout priors: `programs/M001_multi_agent_ensemble/sim/agents/a04_chigiri.py`.
- Frozen trend convention: `programs/M001_multi_agent_ensemble/sim/regime/classifier.py`.

**Pre-registration commit:** beb60604bbaf68eac3893a80b6a809d02d942818
