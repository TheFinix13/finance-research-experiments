# Phase AK-2 report — Reo striker mode

Executed 2026-08-04, protocol committed (`f524abc`) before execution.
One replay 2019–2023 (squad trade count 1796 — exactly reproduces the
AF baseline, good replication), 13,187 mirror thoughts captured;
8,788 carried no leader trade plan (leader thoughts without full
entry/stop/tp rationale), 1,141 expired unfilled, **3,258 executed**
counterfactually per the declared fill/exit model.

## Verdict (pre-registered bands): `passthrough`

| Readout | Value |
|---|---|
| Overall mirror KPIs | n=3258, win 38.5%, PF 0.94, mean R −0.039 |
| Leaders' pooled base (same window) | mean R −0.03 |
| Difference | −0.009 → inside the ±0.05 passthrough band |

Reo's selection, taken as a whole, neither adds nor destroys value
relative to what his leaders already produce: he is a faithful
mirror. No striker charter from this readout.

## Per-leader split (declared readout #2 — hypothesis generators only)

| Mirrored leader | n | PF | mean R |
|---|---|---|---|
| bachira_meguru | 2770 | 0.916 | −0.056 |
| **chigiri_hyoma** | **307** | **1.259** | **+0.098** |
| itoshi_rin | 117 | 0.849 | −0.043 |
| barou_shoei | 64 | 0.998 | +0.010 |

Three observations, all subgroup-level on a mined window (candidate
signals, not claims):

1. **85% of Reo's executed mirrors are Bachira** — the mirror
   follows the loudest voice, and Bachira's junk-heavy flow drags
   the whole readout to his base rate. Any future Reo v2 needs
   leader weighting, not just a conviction floor.
2. **The Chigiri subset is positive.** Chigiri is net-negative as a
   player, yet the trades where his conviction cleared Reo's 0.60
   floor carried PF 1.26 / +0.098 mean R over 307 executions. His
   HIGH-CONVICTION core appears sound; his losses likely live in the
   low-conviction tail. This directly supports Chigiri v1.1
   candidate (c) revert-and-narrow (raise his own entry gate) and
   must be cross-checked against the independent loss autopsy.
3. **Rin mirrors lose money while Rin wins.** Mirroring costs a bar
   of lag plus a humility-shortened window; for a zone-touch weapon
   the entry timing IS the edge. Lag destroys Rin-derived value —
   another reason Rin stays frozen and un-mirrored.

## Disposition

- Striker mode: not chartered (passthrough).
- Chigiri conviction-subset finding: forwarded to the Chigiri v1.1
  autopsy as a pre-declared candidate; any exploitation gets its own
  protocol on design fields with sealed confirmation.
- Reo remains filter-only (Phase AK Option A), NEL-exempt.
