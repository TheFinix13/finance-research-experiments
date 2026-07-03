# Phase W-barou — pre-registered protocol

**Status:** PRE-REGISTERED (2026-07-03 07:45 UTC)
**Governing amendment path:** `../G7_v1_checkpoint_gate/PROTOCOL.md` §11.11 (new subsection added on landing).
**Companion:** `../G7_role_registry_v1/PROTOCOL.md` (Barou's C2 fail + C8 single-axis retention motivates this phase).
**Blue Lock precedent:** Phase T-evolve for Rin (`../G7_v1_checkpoint_gate/PROTOCOL.md` §11.8) — same shape, adapted to Barou's canon.

---

## 1. Hypothesis

**H1 (lone-conviction claim):** when the F21 workspace snapshot at Barou's decision barrier contains NO Bachira same-direction proposal on Barou's symbol, Barou's own proposal has HIGHER expected TQS than his post-V baseline of 0.347 because his read is a genuine solo-conviction opportunity rather than an aggregator-second-place submission.

**H2 (continuation-entry offset) — DEFERRED to v1.2:** the original H2 idea was for Barou to publish a delayed entry (2–3 pips beyond Bachira's trigger) when Bachira had claimed the slot. On analysis, this depends on multi-position aggregator support (Φ5 Arm 4) — the current Φ4.1 aggregator applies single-position-per-symbol mutex regardless of entry offset, so an offset entry from Barou still loses the R6 tournament to Bachira's higher-TQS proposal. Deferring H2 to a Phase W-barou-v1.2 amendment AFTER Φ5 Arm 4 lands.

For Phase W-barou v1.1, we implement H1 only. The Bachira-competition branch defaults to `default_no_workspace_signal` behaviour (existing devour mechanic unchanged), which is what post-V measures. This gives a CLEAN pre-post comparison: any positive delta on walk-forward-post-W vs walk-forward-post-V comes ONLY from H1's lone-conviction lift.

The Blue-Lock-shaped evolution is: Barou v1.1 carves his own niche around Bachira's "trickster" via H1. Full parity with Rin's Phase T-evolve (lone-read lift only, no continuation-entry mechanic in Rin's v1.1 either).

---

## 2. Empirical motivation (post-V numbers, locked)

Baseline from `../../reviews/g7_leave_one_out_verdict_post-V.md` + `../../reviews/g7_role_registry_verdict_post-V.md`:

- **Barou baseline (post-V):** 153 trades, mean TQS 0.347, volume share 2.7%.
- **Barou Role Registry v1:** C2 FAIL (best peer lift 0.502× epsilon), C7 FAIL (no peer lifts him), C8 PASS at 151.3 epsilon-units (single retained axis), C9 FAIL (2.7% < 5% floor).
- **Bachira→Barou cannibalisation:** when Bachira is excluded, Barou gains +808 trades (84.1% reduction ratio — currently the ONLY C3 failure in the squad). Bachira's slot dominance is the direct cause of Barou's under-trading.
- **Phase V-b null result:** the `devour_applied` tier promotion (Phase V-b, §11.9-postmortem) promoted Barou to effective Tier-1 ONLY when Bachira had already published. That gave Barou a conviction lift on the exact ticks where Bachira's proposal had higher TQS — Barou lost the R6 tournament anyway. Root cause diagnosed as "conviction gap too wide".
- **Corollary:** the fix is NOT to compete on the same slot at higher conviction. The fix is to occupy a DIFFERENT slot. That is what H1/H2 formalise.

**Blue Lock parallel:** Rin's Phase T-evolve (§11.8) yielded when Isagi's metavision fired and got a lone-read lift when it didn't. Phase W-barou is the same mechanic shape adapted to Barou's canon: yield the crowded slot, claim the lone one, and stagger a continuation entry when there IS competition. Same 3-branch structure, different agent, different signal_family.

---

## 3. The two amendments (H1 + H2)

Both amendments live inside `sim/agents/a07_barou.py`. Both read the F21 workspace snapshot at the tick barrier (`snapshot_at_barrier` from F22b). Both stamp diagnostic fields on `proposal.rationale` for post-hoc attribution.

### H1 — Lone-conviction claim (v1.1 landing)

```python
# In A7BarouV1.intend() -- after computing base conviction and reading
# Isagi via latest_by_agent (existing plumbing).
bachira_same_dir = False
bachira_read_present = False
if workspace is not None:
    latest_by_agent = workspace.latest_by_agent(symbol=market.symbol)
    bachira_t = latest_by_agent.get("bachira_meguru")
    if bachira_t is not None and bachira_t.coordinate is not None:
        bachira_dir = str(bachira_t.coordinate.direction_bias)
        if bachira_dir in ("long", "short"):
            bachira_read_present = True
            bachira_same_dir = (bachira_dir == direction)

if bachira_read_present and not bachira_same_dir:
    # Bachira read the OPPOSITE direction -- Barou's read is a genuine
    # counter-conviction opportunity, treated same as lone-conviction.
    lone_conviction_active = True
elif not bachira_read_present:
    # Bachira did not publish any same-symbol thought this bar --
    # Barou's read is genuinely solo.
    lone_conviction_active = True
else:
    # bachira_same_dir=True -- Barou and Bachira agree on direction.
    # Existing devour mechanic still applies (no H1 lift stacked on top).
    lone_conviction_active = False

if lone_conviction_active:
    lift = BAROU_V1_1_LONE_CONVICTION_LIFT  # locked constant 0.10
    conviction = min(BAROU_V1_1_CONV_CAP, conviction + lift)
    yield_reason = "peer_did_not_read_this_setup"
else:
    lift = 0.0
    yield_reason = "peer_claimed_slot_no_lift"
```

**Locked constants:**

- `BAROU_V1_1_LONE_CONVICTION_LIFT = 0.10` (mirrors Rin's `RIN_V1_LONE_READ_LIFT` in §11.8 verbatim -- same shape).
- `BAROU_V1_1_CONV_CAP = 1.0` (matches `BAROU_V1_CONV_CAP` -- existing cap preserved).

**Interaction with existing devour mechanic:** the H1 lone-conviction lift is applied ON TOP OF the devour lift when both fire (Bachira did not read same-direction AND Isagi disagreed with a strong-enough conviction). Total lift caps at `BAROU_V1_1_CONV_CAP = 1.0` so no unbounded runaway. Bachira same-direction cases fall through to the default path, i.e. no H1 lift; existing devour behaviour is unchanged. This means walk-forward-post-W vs walk-forward-post-V isolates ONLY H1's contribution.

### H2 — Continuation-entry offset (DEFERRED to v1.2 pending Φ5 Arm 4)

Deferred per §1 (see hypothesis discussion). Placeholder for the v1.2 amendment:

```python
# NOT IMPLEMENTED in v1.1. Requires Phi5 Arm 4 multi-position aggregator
# support so an offset-entry proposal is not filtered out by the
# single-position-per-symbol mutex of the current Phi4.1 aggregator.
```

---

## 4. Rationale trail (audit-grade)

The following fields MUST be stamped on `proposal.rationale` for every Barou intent that runs through the new mechanic (whether H1, H2, or default path fires). Purpose: post-hoc attribution of which branch produced which trade, for the acceptance test in §5.

- `barou_lone_conviction_claim: bool` (True iff H1 fired)
- `barou_lone_conviction_lift_applied: float` (0.0 if branch skipped, `BAROU_V1_1_LONE_CONVICTION_LIFT` if H1 fired)
- `barou_v1_1_bachira_read_present: bool`
- `barou_v1_1_bachira_same_direction: bool`
- `_yield_reason: str` — one of `"peer_did_not_read_this_setup"` (H1 fired), `"peer_claimed_slot_no_lift"` (Bachira same-dir path), or `"workspace_unavailable"` (F22b snapshot missing at the decision barrier).
- `barou_workspace_snapshot_ok: bool` — whether the workspace snapshot was available at the decision barrier.

---

## 5. Empirical acceptance test (locked pre-run)

Measured on walk-forward-post-W (a fresh 3-symbol × 2015-2025 walk-forward with Barou v1.1 wired in, everything else unchanged from post-V).

Primary statistics (Barou-specific):

- **`Barou_n_trades_post_W`** — Barou's baseline trade count in the walk-forward-post-W run.
- **`Barou_mean_tqs_post_W`** — Barou's baseline mean TQS in the walk-forward-post-W run.
- **`Barou_volume_share_post_W`** — Barou's fraction of squad trades.
- **`Barou_c2_pass_post_W`** — does Barou clear the ε=0.005 outgoing chemistry threshold on any peer? (Role Registry v1 §3.)
- **`Barou_c7_pass_post_W`** — do ≥ 2 peers lift Barou's TQS by ≥ 0.02?
- **`Bachira_barou_cannibalisation_ratio_post_W`** — the C3 reduction ratio (Barou trade count when bachira is EXCLUDED, vs baseline). Post-V is 84.1%. A successful Phase W-barou brings this down materially.

Secondary statistics (squad-level, non-decisive):

- Squad mean TQS.
- Squad trade count.
- Kunigami retention (Phase W-barou should not have any effect on Kunigami; if it does, that's a bug — flag it).

Verdict rules (pre-registered):

- **REVERT to v1.0** if `Barou_n_trades_post_W < 100` (Phase W-barou destroyed his trades; the new mechanic is worse than the old) OR if `Barou_mean_tqs_post_W < 0.30` (new mechanic degrades quality significantly).
- **LAND as v1.1** if `Barou_n_trades_post_W ≥ 250` AND `Barou_mean_tqs_post_W ≥ 0.34` AND `Bachira_barou_cannibalisation_ratio_post_W ≤ 0.60` (still fails C3 threshold of 0.5 but material improvement over 0.841).
- **AMBIGUOUS ZONE** (any combination between the two boundaries above) → write a §5-postmortem, propose either a Phase W-barou-v1.2 iteration OR route the remaining problem to Phi5 Arm 3/4 (multi-position aggregator). No auto-land.

**No parameter tuning after this pre-registration.** If the numbers land in the AMBIGUOUS zone, we do NOT re-tune `BAROU_V1_1_LONE_CONVICTION_LIFT`, `BAROU_V1_1_CONTINUATION_OFFSET_PIPS`, or the imbalance normalisation. Any such change is a §11.X amendment requiring its own pre-registration.

---

## 6. Rin-parallel guardrail

To ensure Phase W-barou has not inadvertently degraded Rin's Phase T-evolve behaviour (both agents now emit `_yield_reason` on similar branches), the post-W walk-forward must show Rin's TQS ≥ 0.36 (within 0.03 of her post-V baseline 0.394) and trade count ≥ 350. If either regresses, that is a Rin-side bug, not a Phase W-barou success — flag before landing.

---

## 7. Panel

Reuse the G7 v1 panel (3 symbols, H4 bars, 2015-01-01 → 2025-12-31, 7 rolling OOS windows). No panel expansion for Phase W. Sentinel physically blocking (`sentinel_blocks=True`). R6 active for multi-position candidates — the H2 continuation-entry branch specifically depends on R6 accepting Barou's offset entry as a distinct setup from Bachira's original.

---

## 8. Compute footprint

Single walk-forward-post-W run (~40 min on the M001 panel, mirrors walk-forward-post-V). Heartbeat monitor MUST be active for the duration (per `heartbeat-monitor.mdc` alwaysApply=true rule). No leave-one-out re-run required; Role Registry v1 numbers are re-derived from the new baseline cache post-hoc via `--aggregate-only`.

---

## 9. Stop rules

- Halt immediately if walk-forward-post-W produces < 500 total squad trades (indicates a structural break, not a routing change).
- Halt immediately if the F22b `snapshot_at_barrier` returns None on > 20% of Barou's decision barriers (indicates workspace plumbing bug, not H1/H2 outcome).
- Halt immediately if the compute process's heartbeat log shows > 10 min gap (per heartbeat-monitor.mdc §hang guidance).

---

## 10. Cross-references

- **§11.5 (2026-07-01)** — Barou devour bump. Explicitly SUPERSEDED by H2 continuation-entry offset. The devour lift + observation floor constants stay in the code for backward compatibility but the primary decision path becomes H1/H2.
- **§11.8 (2026-07-01 evening)** — Phase T-evolve (Rin). Direct precedent for H1's `_yield_reason` field and lone-read lift shape.
- **§11.9-postmortem (2026-07-02)** — Phase V-a + V-b null result. The root-cause diagnosis "conviction gap too wide" motivates Phase W-barou's design choice to occupy a DIFFERENT slot rather than compete on the same one at higher conviction.

---

## 11. Verdict registry row (to be added post-run)

To be appended to `programs/M001_multi_agent_ensemble/reviews/verdict_registry.md` after walk-forward-post-W lands:

```
| phase | agent | mechanic | walk-forward tag | n_trades | mean_tqs | c2 | c7 | c3_bachira | verdict |
|-------|-------|----------|------------------|---------:|---------:|:--:|:--:|:----------:|---------|
| W-barou | barou_shoei | v1.1 lone+continuation | post-W | ? | ? | ?  | ?  | ?          | pending |
```

`?` will be filled in from the post-W numbers.

---

## 12. Amendment procedure

Same as G7 v1 §11. Any §11.X-postmortem-style landing (null result → revert) will preserve this pre-registration + the raw numbers in an audit block, mirroring the Phase V-b postmortem format.
