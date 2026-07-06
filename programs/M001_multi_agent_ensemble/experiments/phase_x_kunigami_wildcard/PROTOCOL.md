# Phase X-kunigami — Wild Card drawdown gate (pre-registered DESIGN)

**Status:** PRE-REGISTERED DESIGN (2026-07-06 evening). Implementation and compute are explicitly NOT part of this session — they are sequenced AFTER the Phase W-barou v1.2 verdict so the gate is measured against whichever baseline is canonical at that point (one experiment in flight at a time; no confounded baselines).
**Origin:** `../G7_role_registry_v1/DECISION_kunigami.md` Option B3 (the pre-registered Wild Card return path recorded at retirement sign-off, 2026-07-06) + G7 v1 PROTOCOL §11.12.
**Aggregator context:** designed against Φ5 **Arm 4** (multi-position K=2), the adopted G7-era default (`../phi5_aggregator/PROTOCOL.md` §11.6).

---

## 1. Canon and role statement

Kunigami v1 (workspace publisher) retired with C8 = 0.0 measured downstream effect. Canon arc: eliminated → **Wild Card** → returns leaner, stealing goals and defending. The return role is therefore NOT a publisher and NOT a proposer: he becomes an **aggregator-side defender** — a squad-equity drawdown gate that vetoes NEW admissions while the squad is bleeding. His Sentinel R5 loss-streak side channel (per-agent anti-tilt) stays as-is; the gate is squad-level and complementary, not a duplicate.

## 2. Mechanic (locked design)

Lives in `_drive_squad_replay` at the admission stage (same insertion point as the Arm 4 slot checks), behind an explicit flag (`kunigami_wildcard_gate=True`, harness `--kunigami-gate`). Default OFF — all sealed caches stay byte-identical.

- Maintain a running sandbox equity curve from closed-trade `pnl_pips` (fixed-lot: 1 pip = $1 at the sandbox's 0.1 lot on $100 equity — same dollar convention as R1/R6).
- Track running peak equity. Drawdown = (peak − equity) / peak.
- **Gate trips at DD ≥ 25%** — the pre-existing Φ5 §6 stop-rule bound; not a new number.
- **Gate releases at DD ≤ 12.5%** (half the trip level; hysteresis prevents flapping).
- While tripped: ALL new admissions are vetoed and journalled to `proposals_rejected.jsonl` with `rejection_reason="kunigami_wildcard_dd_gate"`. Open positions are managed normally (exits untouched) — Kunigami defends, he does not liquidate.

Locked constants: `KUNIGAMI_GATE_TRIP_DD = 0.25`, `KUNIGAMI_GATE_RELEASE_DD = 0.125`. No tuning after this pre-registration; any change is a new amendment.

## 3. Empirical motivation (locked)

Φ5 §11.5 journalled that the fixed-lot $100 sandbox equity curve breaches 25% DD in EVERY window including control (worst window 1.82× control) — the curve has never been drawdown-controlled. The gate is the first mechanic whose PRIMARY statistic is drawdown, not TQS.

## 4. Runs (to be executed post-W-barou-v1.2, heartbeat mandatory)

1. Gated walk-forward, tag `kunigate-arm4`, vs the then-canonical Arm 4 baseline (identical env/panel, 7-agent roster, `--aggregator-arm arm4 --retire-kunigami --kunigami-gate`).

## 5. Verdict rules (locked)

- **LAND** iff: worst-window max DD reduced by ≥ 20% relative vs baseline; AND squad median-of-window-mean TQS ≥ baseline − 0.005; AND squad trade count ≥ 60% of baseline.
- **REVERT** if trade count < 40% of baseline (gate starves the squad) OR TQS drops > 0.010.
- **AMBIGUOUS** → postmortem, no retune of trip/release levels.
- Stop rule: halt if the gate never trips across all windows (mechanic untestable on this panel — journal and close as NOT-MEASURABLE, do not lower the trip level to force a result).

## 6. Register-row

Kunigami's roster status after a LAND would be `wildcard_defender` (aggregator-side, non-proposing, non-publishing) — a new role label requiring a Role Registry v1 amendment at landing time.
