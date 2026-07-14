# Dispersion primitives round 2 — F19/F20 per-playstyle mechanisms (pre-registration)

- **Registered:** 2026-07-14 (committed BEFORE any result is computed).
- **Program:** M001 multi-agent ensemble.
- **Parent:** doctrine §4.1a (F19 `lot_intent` / F20 `risk_intent`); G7 §3 criteria 5–6; Phase S (§11.6) is round 1 of this same lane.
- **Evaluation vehicle:** one pre-check on the banked §11.13 caches (pure-function recomputation, no new OOS touch) + the §11.15 re-gate replays (verdict-bearing numbers).

---

## 1. Problem (from §11.13, both arms)

Five of six trade-taking agents fail at least one dispersion criterion:

| Agent | C5 (phi41/arm4) | C6 (phi41/arm4) | Root cause (recon 2026-07-14) |
|---|---|---|---|
| Isagi | 0.086 / 0.087 ✗ | 0.083 / 0.082 ✗ | C6: SL anchor damped to 0.25× ATR sensitivity; C5: conviction-only scaling on a narrow conviction range, 0.01-lot grid |
| Bachira | 0.089 ✗ / 0.101 ✓ | 0.154 ✓ | C5: base_lot 0.05 → only 3 grid levels {0.04, 0.05, 0.06} |
| Rin | 0.112 ✓ | 0.086 / 0.084 ✗ | C6: `0.30 × h1_swing` clipped at max 30 — mean SL 29.18 is pinned at the ceiling; the structural signal is saturated away |
| Chigiri | ✓ | ✓ | — (untouched) |
| Nagi | **0.000** ✗ | **0.000** ✗ | No provenance: `atr_pips` never stamped (evaluator falls back to constant 30.0) and `regime_fit` hardcoded 0.5; conviction range 0.91–0.94 |
| Barou | 0.068 ✗ / 0.118 ✓ | 0.154 ✓ | C5: conviction_gain 1.0 on a narrow conviction range |

Reo is structurally waived (§11.1).

## 2. Mechanisms (doctrine-motivated; NOT a CV-target search)

### 2.1 F19 — new shared building block: risk-normalised sizing

Doctrine §4.1a's F19 signature includes `sl_pips` precisely so sizing
can respond to trade structure; the current `conviction_scaled_lot_intent`
ignores it. New building block in `sim/core/lot_intent.py`:

```
risk_normalised_lot_intent(conviction, sl_pips, equity, regime_fit, *,
    base_lot, ref_sl_pips, conviction_pivot, conviction_gain,
    regime_fit_gain, max_lot_ceiling,
    sl_ratio_floor=0.5, sl_ratio_cap=2.0)

ratio = clip(ref_sl_pips / sl_pips, sl_ratio_floor, sl_ratio_cap)   # 1.0 if sl_pips <= 0
raw   = base_lot × ratio
        × (1 + conviction_gain × (conviction − conviction_pivot))
        × (1 + regime_fit_gain × (regime_fit − 0.5))
lot   = round_down_to_min_lot(clip(raw, MIN_LOT, max_lot_ceiling))
```

This is classic constant-risk sizing (equal dollar risk per unit stop
distance) expressed multiplicatively around each playstyle's doctrine
anchor stop, so it cannot Kelly-saturate at MIN_LOT on the $100 sandbox
(the Phase S failure mode). `ref_sl_pips` is each playstyle's §4.1a
doctrine-anchor SL — NOT a free parameter.

Playstyle table changes (doctrine §4.1a amendment; existing
conviction/pivot/gain/ceiling constants are carried over UNCHANGED —
the only change is the risk-normalisation factor and its doctrine
anchor):

| Playstyle | Change | ref_sl_pips (doctrine anchor) |
|---|---|---|
| conservative_metavision | conviction_scaled → risk_normalised | 40 ("SL ≈ 40") |
| rebel_tight | conviction_scaled → risk_normalised | 20 ("SL ≈ 20") |
| confluence_only | conviction_scaled → risk_normalised | 30 ("SL ≈ 30") |
| solo_king | conviction_scaled → risk_normalised | 30 ("SL ≈ 30") |
| analytical_precision | **unchanged** (C5 passes 0.112) | — |
| speed_momentum | **unchanged** (passes) | — |
| copier_hrp | **unchanged** (waived) | — |

Doctrine fit: metavision "sizes to the structure it sees"; the rebel's
tight stops earn proportionally larger size; the perfect trap takes
equal risk per trap; the king strikes with the same risk every time
(constant risk = varying lot with stop width). All four failing-C5
playstyles get the same structural mechanism rather than per-agent gain
tweaks.

### 2.2 F20 — two saturation fixes

- **conservative_metavision (Isagi):** replace the damped anchor
  `SL = clip(40 × (0.75 + 0.25 × ATR/40), 30, 50)` with full ATR
  proportionality `atr_scaled_risk_intent(atr_multiplier=1.3,
  payoff_ratio=1.5, sl_min=30, sl_max=50)`. At the panel-mean ATR of
  ~30 pips this yields SL ≈ 39 — the doctrine anchor "SL ≈ 40" is
  preserved; only the deliberate 0.25 damping (a Phase-E choice G7
  falsified) is removed. 1.3 is the multiplier already used by the
  confluence_only and copier playstyles, not a new number.
- **analytical_precision (Rin):** de-saturate the structural stop:
  `sl_swing_fraction 0.30 → 0.20`, `sl_pips_max 30 → 35` (min 15 and
  TP multipliers (2, 4, 6) unchanged). Motivation: §11.13 published
  mean SL = 29.18 vs ceiling 30 — the distribution is pinned; at the
  banked typical H4 20-bar swing of ~125–140 pips, 0.20 × swing ≈ 25–28
  restores the doctrine anchor "SL ≈ 25" INSIDE the band. This uses
  only already-published aggregate statistics, no fresh OOS
  interrogation.
- All other playstyle risk shapes **unchanged** (Bachira 0.154, Chigiri
  0.177, Nagi's formula is sound once its inputs are real — §2.3,
  Barou 0.154).

### 2.3 Nagi — provenance wiring (root-cause fix, no formula change)

Nagi has no bar access by design (his trigger IS the ledger), so his
proposals never carried `atr_pips` / `h1_swing_pips`, and
`regime_fit` was the 0.5 placeholder. Fix at the provenance layer:

1. Leader agents with bar access (Isagi, Bachira, Rin, Chigiri, Barou)
   additionally stamp `atr_pips` + `h1_swing_pips` into their Thought
   `coordinate.rationale` (they already stamp entry/stop/tp there —
   this extends the workspace read with the volatility context that
   F20 needs; doctrine §4.1a: the workspace carries the read).
2. Nagi's `intend()` borrows the leader's `atr_pips` / `h1_swing_pips`
   into his own proposal rationale (same borrow pattern as
   entry/stop/tp), so `source_atr_pips` / `source_h1_swing_pips` become
   real and varying.
3. Nagi's `regime_fit` placeholder is replaced by the Phase-S map
   applied to the borrowed ATR: `clip(0.5 × atr_pips / 30, 0.2, 0.8)`
   (`regime_fit_from_atr_pips`, the pips-domain twin of the existing
   `regime_fit_from_atr`).

No change to Nagi's F19/F20 formulas beyond §2.1's shared
risk-normalisation; the C6 shape (`atr_scaled`, mult 1.3, clip 20–40,
partial ladder) is untouched — it was never the problem, its inputs
were.

### 2.4 Trade-stream invariance (verified in recon)

F19/F20 are pure functions invoked by the C5/C6 evaluators on cached
`source_*` fields; the sandbox fill model uses fixed lots and
proposal-geometry stops. Nagi's regime_fit feeds no aggregator ranking
under phi41 (conviction-only) or arm4 (checked: only arm3
`same_direction_merge` reads regime_fit). Therefore THIS lever changes
no trade stream; only Phase Y does.

## 3. Pre-registered expectations & thresholds

Gate thresholds are unchanged (CV >= 0.10, G7 §3). Per-agent
predictions, falsifiable:

| Agent | C5 expected | C6 expected |
|---|---|---|
| Isagi | >= 0.10 (SL variation now feeds size) | >= 0.10 (full ATR proportionality) |
| Bachira | >= 0.10 (more grid levels via SL ratio) | already passes; must NOT regress below 0.10 |
| Rin | already passes; untouched | >= 0.10 (de-pinned from ceiling) |
| Nagi | > 0 and targeted >= 0.10 (real regime_fit + SL variation) | > 0 and targeted >= 0.10 (real ATR) — **re-gate only** (needs fresh stamps) |
| Barou | >= 0.10 under arm4; phi41 depends on Phase Y trade mix | must stay >= 0.10 |
| Chigiri | untouched, must stay >= 0.10 | untouched, must stay >= 0.10 |

## 4. Evaluation plan

1. **Pre-check (one pass, banked caches):** recompute C5/C6 for
   Isagi/Bachira/Rin/Chigiri/Barou through the NEW primitives on the
   §11.13 cached `source_*` fields (identical inputs the re-gate will
   reproduce for unchanged trade streams). Nagi is NOT evaluable here
   (his fix requires freshly stamped provenance). No new OOS touch —
   these caches are already-banked evidence. The pre-check is binding:
   if a §3 prediction fails, that failure is REPORTED and the constants
   stay frozen (no iterate-and-recheck).
2. **Verdict-bearing numbers:** the §11.15 re-gate C5/C6 columns.

## 5. Stop rules / anti-leakage

1. All constants above are frozen at this commit. Any post-pre-check
   change is a fresh protocol (attempt #2, multiplicity noted).
2. No CV-target search: the mechanisms are structural (risk
   normalisation, de-saturation, provenance) with constants tied to
   doctrine anchors or existing shipped values, chosen before any
   evaluation.
3. If the pre-check shows a REGRESSION of a passing agent below 0.10,
   that is a hard failure of this lever for that agent — reported, not
   patched.

## 6. Artifacts

- Implementation + tests committed before the pre-check runs.
- Pre-check report: `reviews/dispersion_r2_precheck.md`.
- Final numbers: §11.15 gate table. Doctrine §4.1a amendment note
  appended to `06-blue-lock-doctrine.md`.
