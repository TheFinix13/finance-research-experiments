# E013 - Safety-layer contribution study (pre-registered)

**Status:** PRE-REGISTERED 2026-07-01 · **Date frozen:** 2026-07-01

E013 asks the honest question about the three live-side safety layers
that were installed on the trading agent after the June 2026 blow-up:
**what is each layer's marginal contribution to OOS Sharpe, and does
the PostLossGuard actually block bad regimes (or does it mostly block
future winners)?**

Layers under attribution:

1. **Wick-proof SL** (`SoftStopConfig.confirm_on_close`) - SL fires
   only when a bar CLOSES beyond the stop, with an intrabar panic
   escape at `panic_mult` * soft_dist. Purpose: survive hunting wicks
   that would sweep a resting broker stop.
2. **BE migration** (`LiveConfig.move_be_at_r = 1.0`) - SL migrates
   to entry price when trade reaches +1R intrabar. Purpose: convert a
   winner into a scratch-or-better instead of round-tripping.
3. **PostLossGuard (PLG)** (`agent.risk.post_loss_guard.PostLossGuard`)
   - after a loss, cooldown for `cooldown_bars`; after 3 consecutive
   losses in a UTC day, halt for the rest of the day. Purpose: kill
   the revenge-trade reflex that blew the account in June 2026.

None of these layers has been measured for its **individual OOS
contribution** on the deployed cell (`zone_d1_against/H4/all`). The
existing E004 walk-forward verdict is computed via the raw-signal
`run_alpha` harness (no safety layers), so E004's +11.34 pips/trade is
the ALPHA edge, not the LIVE edge. E013 measures the live-vs-alpha
gap.

Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md). Registered
in [`EXPERIMENTS.md`](../../EXPERIMENTS.md). Data accounting in
[`DATA_LEDGER.md`](../../DATA_LEDGER.md).

---

## §0 Reuse declaration

E013 reuses the following artefacts exactly. The ONLY new code is
the `_run_alpha_ab` driver + arm toggles; production safety-layer
logic is mirrored in the driver but not modified.

| Purpose | Module / artefact |
|---|---|
| Alpha under test | `multi-pair-trading-agent/agent/alphas/concepts/zone_alpha.py::SupplyDemandAlpha(htf_align="D1", htf_align_mode="against", htf_lookback=10, htf_min_move_pips=60.0)` |
| Soft-stop reference | `multi-pair-trading-agent/agent/live/soft_stop.py::evaluate_soft_stop` (behaviour mirrored in driver `_check_exit_ab`) |
| PLG reference | `multi-pair-trading-agent/agent/risk/post_loss_guard.py::PostLossGuard` (behaviour mirrored in driver `BarPlg`; bar-driven variant) |
| BE migration reference | `multi-pair-trading-agent/agent/live/config.py::LiveConfig.move_be_at_r` (behaviour mirrored in driver) |
| A/B driver | `finance-research-experiments/scripts/run_walk_forward_ab.py::_run_alpha_ab` |
| Bar loader | `multi-pair-trading-agent/agent/data/loader.py::BarLoader` |
| Bootstrap CI | `multi-pair-trading-agent/agent/backtest/metrics.py::bootstrap_p_value` |

**Fidelity note.** The driver's `BarPlg` is bar-driven (cooldown in
bars, not minutes), and it uses discrete outcome recording rather
than the live event bus. This is intentional: measuring the LAYER's
contribution to OOS Sharpe does not need live-fidelity latency
modeling. Production port validation (Wave 6) is where live-fidelity
returns to the loop.

---

## §1 Hypothesis (operational)

**Arm design (leave-one-out).**

| Arm | wick-proof | BE migration | PLG | Interpretation |
|---|---|---|---|---|
| A `all_on` | on | on | on | Current live configuration |
| B `wick_off` | **off** | on | on | Isolates wick-proof's marginal contribution |
| C `be_off` | on | **off** | on | Isolates BE migration's marginal contribution |
| D `all_off` | off | off | off | Raw alpha (matches E004 harness) |

Sharpe deltas:

- Δ_wick = Sharpe(A) - Sharpe(B) → wick-proof contribution given
  the other two layers are on.
- Δ_be = Sharpe(A) - Sharpe(C) → BE contribution given the other two
  layers are on.
- Δ_combined = Sharpe(A) - Sharpe(D) → combined contribution of all
  three layers.
- Δ_plg is NOT identifiable from these four arms alone. Instead, PLG
  contribution is quantified via the false-negative / false-positive
  analysis in §4.

**H0 (per-layer).** Δ_wick ≤ 0 AND Δ_be ≤ 0 (neither layer adds Sharpe
on top of the other two).

**H1 (per-layer).** At least one of Δ_wick, Δ_be > 0 with bootstrap-95 %
CI > 0.

**H0 (combined).** Δ_combined ≤ 0 (the safety-layer stack does not
improve on the raw alpha).

**H1 (combined).** Δ_combined > 0 with bootstrap-95 % CI > 0.

**PLG H0 / H1.** Aggregating over the arm-A run's PLG-blocked-signal
would-be outcomes: PLG's false-negative rate (blocked signals that
would have won) is NOT strictly higher than its false-positive rate
(blocked signals that would have lost). H1: false-negative rate is
strictly higher OR the median would-be pips per block is > 0 (both
imply PLG is blocking future money).

**Outcome metric.** Annualised Sharpe over trade P&L per (arm,
walk-forward window), then pooled across 7 windows. Bootstrap 95 % CI
over the per-window Sharpe values, 5,000 resamples, seed 42.

---

## §2 Separation

- **Does this touch the trading agent?** No. Safety-layer logic is
  mirrored inside the research-side driver. Production code is
  read-only.
- **Prior uses of the same data slice.** EURUSD H4 2015-2025 used by
  E001-E005 + E011. E013 is a **new statistical draw** because the
  toggles change the trade outcome sample (exit prices differ from
  E004's raw-signal harness). DATA_LEDGER row added at Stage 1.

---

## §3 Locked parameters

| Knob | Value | Rationale |
|---|---|---|
| Alpha | `zone_d1_against/H4/all` | Deployed |
| Wick-proof `panic_mult` | 1.0 | Matches `SoftStopConfig.panic_mult` default |
| Wick-proof `confirm_on_close` | True (when arm has wick-proof on) | Matches production `LiveConfig.confirm_on_close = True` |
| BE trigger R multiple | 1.0 | Matches `LiveConfig.move_be_at_r = 1.0` |
| PLG `cooldown_bars` | 2 | H4 mapping of `LiveConfig.post_loss_cooldown_minutes = 60` (roughly 60 min ≈ 0.25 H4 bar, floor to 2 bars for a meaningful cooldown) |
| PLG `max_consecutive_losses` | 3 | Matches `LiveConfig.max_consecutive_losses = 3` |
| PLG `catastrophic_loss_frac` | 0.10 | Matches `LiveConfig.catastrophic_loss_frac = 0.10` |
| Fixed lot | 0.1 | Matches `agent.alphas.backtest.FIXED_LOT`; sizing is out of scope for E013 |
| Initial balance | `cfg.backtest.initial_balance` | For catastrophic-loss threshold only; sizing is fixed lot |
| Bootstrap resamples | 5,000 | Convention |
| Random seed | 42 | Convention |
| n-gate per arm per window | 15 trades | Below this, per-window Sharpe is dropped from the pool |

**Verdict (locked):**

- `wick_alive` iff Δ_wick bootstrap-95 % CI lower bound > 0.
- `be_alive` iff Δ_be bootstrap-95 % CI lower bound > 0.
- `combined_alive` iff Δ_combined bootstrap-95 % CI lower bound > 0.
- `plg_earns_keep` iff (false-negative rate > false-positive rate) AND
  (median would-be pips per block > 0). Note: this is the **PLG is
  costly** verdict - PLG blocks future winners.
- `plg_dead` iff (false-positive rate > false-negative rate) AND
  (median would-be pips per block < 0). PLG is correctly averting
  losses; keep as-is.

The two PLG verdicts are named from the ATTACKER's perspective (does
PLG block money we would have made?). `plg_earns_keep` is the
uncomfortable answer that says PLG is expensive; `plg_dead` is the
comforting answer that PLG is doing its job.

---

## §4 Statistical pipeline

| Stage | Pair | Period | Family | Test | FDR |
|---|---|---|---|---|---|
| 1 - Sharpe attribution | EURUSD | 7 × 1-yr OOS folds 2019-2025 | 3 deltas (Δ_wick, Δ_be, Δ_combined) | Bootstrap-95 % CI on Sharpe deltas | BH α = 0.05 across 3 |
| 2 - PLG false-neg/pos | EURUSD | same 7 OOS folds | Arm A blocked-signal set | Rate comparison; median would-be pips | per-cell α = 0.05 |
| 3 - Cross-pair replicate | GBPUSD, USDCAD | 2015-2024 (E005 sealed) | Stage-1 survivors | Bootstrap-95 % CI, frozen params | per-cell α = 0.05 |

**Stage 2 method.** Every signal that Arm A's PLG blocks is walked
forward under Arm A's remaining toggles (wick-proof + BE on) as if PLG
did not block it. The would-be pips are recorded per block. False-neg
rate = fraction of blocks with would-be pips > 0. False-pos rate =
fraction with would-be pips < 0.

**Multiplicity.** BH-FDR is applied across the three Δ statistics
because they are pre-declared as a family. The PLG rate comparison
is a single test per Stage 2 (no adjustment).

---

## §5 Stop rules

- **Stage 1.** If Δ_combined CI upper bound < 0 (the entire safety
  stack HURTS Sharpe) → **STOP at Stage 1**, publish honest verdict,
  open a production-side follow-up ticket to consider disabling
  layers. Cross-pair replicate is not run.
- **Stage 2.** If PLG blocks < 20 signals in the arm-A run → PLG
  false-neg/pos is `parked_insufficient_n`; report the count and
  move on.
- **Stage 3.** If Stage-1 survivors fail cross-pair → downgrade to
  `parked_weak_effect` (EURUSD-only) but keep production posture
  unchanged pending a wider study.

**Explicitly not a stop rule.** A per-layer Δ that fails BH-FDR on the
3-cell family is NOT a stop rule; it is a `dead` or `parked` verdict
for that specific layer. The other layers' verdicts stand independently.

---

## §6 Amendments

_(No amendments yet - appended after pre-registration commits only.)_

---

## §7 Cross-references

- **A/B driver** ([`../../scripts/run_walk_forward_ab.py`](../../scripts/run_walk_forward_ab.py))
  - the harness that runs each arm.
- **E004 walk-forward** ([`../E004_walk_forward/PROTOCOL.md`](../E004_walk_forward/PROTOCOL.md))
  - baseline raw-alpha Sharpe (arm D of E013 should replicate E004
  numbers within bootstrap CI).
- **Production layers.**
  - `multi-pair-trading-agent/agent/live/soft_stop.py`
  - `multi-pair-trading-agent/agent/risk/post_loss_guard.py`
  - `multi-pair-trading-agent/agent/live/config.py::LiveConfig`
- **June 2026 blow-up motivation.**
  `multi-pair-trading-agent/docs/reviews/2026-06-01_week_review.md`
  documents the loss cluster that motivated PLG.

---

## §8 Data-ledger declaration

| Stage | Pair | TF | Slice | Status this experiment | Prior uses |
|---|---|---|---|---|---|
| 1 | EURUSD | H4 | 2015-2025 | new sim (4 arms) | E001, E002, E003, E004, E011 |
| 3 | GBPUSD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |
| 3 | USDCAD | H4 | 2015-2024 | new sim on E005 sealed slice | E001, E004, E005 |

Stage 3 consumes cross-pair slices already used by E005 for the
deployed cell verdict. E013's re-sim on those bars uses different
exit paths (different arms' toggles) and is disclosed here as the
second consumption of those slices for `zone_d1_against`.

---

**Pre-registration commit:** _(hash after push)_
