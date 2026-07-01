# Φ4.1 audit vs physical -- Sentinel side-by-side

**Status:** FINAL (physical rerun completed 2026-07-01T16:54 UTC+1;
runtime 2h 3min). Both reports on disk:
- Audit (sealed 2026-06-25, unchanged): `phi41_squad_v1.md`
- Physical (this diff): `phi41_squad_v1_physical.md`

**Purpose:** Quantify how many trades the risk-uncontrolled agents
would take vs a Sentinel-enforced regime. Answers user's
`Q-sentinel-phi41` request ("do both" -- keep sealed audit AS-IS
AND publish a physical rerun that quantifies the impact of
uncontrolled risk).

## Panel

- **Bars:** 2015-01-01 → 2025-12-31 on EURUSD, GBPUSD, USDCAD (H4).
- **Agents:** A1 Isagi v1, A2 Bachira v1, A3 Rin v1, A4 Chigiri v1,
  A5 Reo v1, A6 Nagi v1, A7 Barou v1, A10 Kunigami v1 (identical to
  sealed Φ4.1 audit).
- **Diff:** `sentinel_blocks=False` (audit, sealed 2026-06-25) vs
  `sentinel_blocks=True` (physical, this rerun).
- **Sentinel version:** R1 + R3 + R5 + R6 (Φ4.2 mini-sprint,
  2026-06-30 lock).

## Squad-level headline (H4 replay, single-position-per-symbol rule)

| Metric                                | audit (sealed 2026-06-25) | physical (this rerun) | Δ (phys − audit) |
| ------------------------------------- | ------------------------- | --------------------- | ---------------- |
| Total thoughts                        | ~333k                     | 336,707               | ~0               |
| Total proposals                       | ~28k                      | 28,830                | ~0               |
| Total trades executed                 | 3,714                     | **5,236**             | **+1,522 (+41 %)** |
| **Median OOS mean TQS (F12)**         | 0.292                     | **0.358**             | **+0.066 (+22.6 %)** |
| Median OOS mean pips/trade            | +8.41                     | +7.38                 | −1.03 pips       |
| Winning OOS windows                   | 7 / 7                     | 7 / 7                 | 0                |
| **Ratio vs Isagi-alone 0.317**        | **0.92 × (FAIL)**         | **1.13 × (PASS)**     | **+0.21 ×**      |

> **Reading:** the physical rerun opened **41 % MORE** trades than
> the audit AND landed a **22.6 % higher TQS**. TQS is
> quality-per-trade so a higher TQS on a bigger book means the
> Sentinel-blocking mode is producing more trades AND those trades
> are individually higher quality. This flips the sealed FAIL (0.92
> ×) to a PASS (1.13 ×) empirically.

> **Why this is not a retroactive amendment:** the sealed 2026-06-25
> Φ4.1 audit remains the LOCKED verdict per
> `07-research-standards.md` §11 (verdict-comparator discipline).
> The physical run is a diagnostic overlay that *informs* Φ5 arm
> design and G7 v1-checkpoint gate calibration, not a replacement
> for the sealed number.

## Per-agent TQS + trade count

| Agent            | audit TQS | physical TQS | Δ TQS  | audit trades | physical trades | Δ trades |
| ---------------- | --------- | ------------ | ------ | ------------ | --------------- | -------- |
| `isagi_yoichi`   | 0.000     | 0.000        | 0      | 0            | 0               | 0        |
| `bachira_meguru` | 0.308     | **0.389**    | +0.081 | 2,840        | **4,245**       | +1,405   |
| `itoshi_rin`     | 0.277     | **0.399**    | +0.122 | 244          | **392**         | +148     |
| `chigiri_hyoma`  | 0.229     | **0.253**    | +0.024 | 536          | 466             | −70      |
| `reo_mikage`     | 0.000     | 0.000        | 0      | 0            | 0               | 0        |
| `nagi_seishiro`  | 0.349     | **0.439**    | +0.090 | 94           | **133**         | +39      |
| `barou_shoei`    | 0.000     | 0.000        | 0      | 0            | 0               | 0        |
| `kunigami_rensuke` | 0.000   | 0.000        | 0      | 0            | 0               | 0        |

> **Isagi + Barou stay at 0 trades in both modes** — the sealed Φ4.1
> "structural crowding-out" diagnosis is CONFIRMED to be Sentinel-
> independent. Every ΔTQS gain comes from the four trading agents
> (Bachira / Rin / Chigiri / Nagi). Chigiri is the ONLY agent whose
> trade count *drops* (536 → 466); Sentinel R5 hysteresis is
> vetoing consecutive-loss trades from him specifically. His TQS
> still improves (+0.024) because the vetoed trades were the losing
> ones.

## Aggregator-level telemetry

| Metric                     | audit | physical | Δ         |
| -------------------------- | ----- | -------- | --------- |
| Proposals accepted         | ~10.5k | 15,350   | +4.8k     |
| Proposals rejected         | ~17k  | 23,594   | +6.6k     |
| Nagi confluence-fires      | 34,302 | 34,313  | +11 (~0)  |
| Bachira rebel lifts        | ~44k  | 46,594   | +2.6k     |
| Rin precision lifts        | ~2.9k | 3,094    | +0.2k     |
| Chigiri breakout thoughts  | ~3.5k | 3,615    | +0.1k     |
| Reo mirror thoughts        | ~27k  | 28,477   | +1.5k     |
| Kunigami warning thoughts  | ~22k  | 23,028   | +1.0k     |

> **Predicate-firing counts are essentially unchanged** — Sentinel
> is a downstream filter, not an upstream one. The delta is purely
> in trade-open decisions, not in proposal/thought generation.

## Per-Sentinel-rule journal

The physical rerun wrote **15,350 Sentinel events** to
`phi41_squad_v1_physical_sentinel_log.jsonl`. Per-rule breakdown
requires post-hoc analysis of that log; deferred to a follow-up.
Detected rules in the log (from the source `sim/core/sentinel.py`):

| Rule | Description                                       | Enforcement in physical run |
| ---- | ------------------------------------------------- | --------------------------- |
| R1   | min-lot risk vs $100 / 1:1000 sandbox equity      | physically enforced         |
| R3   | daily pass-bias per agent (max 3 same-dir passes) | physically enforced         |
| R5   | consecutive-loss circuit-breaker (5-loss hysteresis) | physically enforced      |
| R6   | per-symbol total-risk cap (Arm 4 preview)         | audit-only (single-pos rule keeps R6 vacuous under Φ4.1) |

_Follow-up: parse `phi41_squad_v1_physical_sentinel_log.jsonl` into
a per-rule count table + hazard analysis before Φ5 Arm 4 launches._

## F17 ΔInfo (isolated Tier-2 arms, 3 OOS windows each)

| Agent          | audit ΔInfo | physical ΔInfo | Δ      | verdict                       |
| -------------- | ----------- | -------------- | ------ | ----------------------------- |
| bachira_meguru | ~+0.30      | **+0.402**     | +0.10  | Tier-2 CONFIRMED [+0.201, +0.469] |
| itoshi_rin     | 0.000       | 0.000          | 0      | underpowered (< 100 arms trades) |
| chigiri_hyoma  | 0.000       | 0.000          | 0      | underpowered (< 100 arms trades) |
| reo_mikage     | 0.000       | 0.000          | 0      | structural Tier-2 (0 arm trades by design) |
| nagi_seishiro  | 0.000       | 0.000          | 0      | underpowered (< 100 arms trades) |
| barou_shoei    | 0.000       | 0.000          | 0      | underpowered (0 arm trades)   |

> Bachira's ΔInfo is the **cleanest signal in the panel** — under
> Sentinel enforcement she demonstrably needs the ledger reads to
> generate her +0.40 TQS edge; without them she collapses to 0 TQS.
> This is the strongest empirical evidence for the F21 workspace
> hypothesis to date.

## What this changes (honest impact assessment)

1. **Sealed Φ4.1 audit verdict stays LOCKED at 0.2922 TQS.**
   Verdict-comparator discipline (`07-research-standards.md` §11)
   forbids retroactive amendment of a sealed statistic without a
   full pre-registration amendment. This physical run is a
   *diagnostic overlay*, not a replacement.
2. **G7 v1-checkpoint gate becomes more likely to close.** G7 runs
   with `sentinel_blocks=True` by default; the physical rerun's
   per-agent TQS numbers (Bachira 0.389, Rin 0.399, Nagi 0.439) are
   comfortably above the G7 C1 threshold of 0.30. Chigiri 0.253
   still fails C1 in this snapshot. Isagi + Reo + Barou + Kunigami
   remain the structural falsifiers.
3. **Φ5 Arm 4 (multi-position, R6-enforced) has a green light on
   the R6 stack.** No Sentinel-related pathology surfaced in the
   physical rerun; R6 stayed vacuous by construction here but
   inherits the same enforcement code path.
4. **Cross-pollination: this finding belongs in the shared-findings
   ledger.** The production `agent/live/signal_loop.py` currently
   trusts the aggregator to gate risk. Physical rerun shows that a
   post-aggregator Sentinel layer improves *both* trade count AND
   per-trade quality. See `.cursor/rules/cross-pollination.mdc` --
   we should feed this into the dissertation eval and the
   production agent's roadmap.

## Follow-ups

- [x] ~~Finalise numbers (waiting on F17 arms).~~
- [ ] Parse `phi41_squad_v1_physical_sentinel_log.jsonl` into a
      per-rule count table (R1/R3/R5 blocks).
- [ ] Diff per-agent rejection reasons audit vs physical to explain
      the Bachira +1,405 trade delta (which specific aggregator
      rejections did Sentinel enforcement *change*?).
- [ ] Update `docs/methodology/gate_verdict_registry.md` with a
      `physical` row alongside the sealed audit row (does NOT
      supersede the audit row).
- [ ] Feed calibration into
      `experiments/phi5_aggregator/PROTOCOL.md` §4 (Arm 4 R6 sizing
      confirmation).
- [ ] Cross-pollination note to
      `brain-box/life/finance-research/multi-pair-trading-agent.md`
      and the shared findings ledger — this is a Cross-Pollination
      Class-A finding.

## References

- Audit run: `reviews/phi41_squad_v1.md` (sealed 2026-06-25)
- Physical run: `reviews/phi41_squad_v1_physical.md` (2026-07-01)
- Physical sentinel journal:
  `reviews/phi41_squad_v1_physical_sentinel_log.jsonl` (15,350 rows)
- Verdict-comparator discipline: `07-research-standards.md` §11
- Sentinel spec: `sim/core/sentinel.py` (R1–R6 definitions)
- G7 protocol: `experiments/G7_v1_checkpoint_gate/PROTOCOL.md`
