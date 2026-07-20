# AMENDMENT 2026-07-20 — AC.0 methodology switched from banked-telemetry OLS to fresh-compute per-movable-agent walk-forward regression

- **Authorised:** 2026-07-20 by user (session log 2026-07-20).
- **Amends:** `PROTOCOL.md` §5 AC.0 (panel + regression input source) and
  §12 sequencing (inserts new *Step 3b — AC.0 recompute*). §11 file
  footprint gains the AC.0-v2 output family. §10 kill conditions gain
  two zero-trades sentinels.
- **Untouched:** §3 (canon → mechanism mapping, playstyle × character
  priors), §4 (pair-character feature vector definitions + `pair_character.json`
  freeze), §5 pass criterion (still ≥2/3 movables with |β| CI lower > 0
  AND ≥1 direction-respected pair), §5.1 additivity flag (UNION), §5.2
  AC.2 criteria, §6 statistic (bootstrap 95% percentile CI, n=10,000,
  window-level resample), §7 harness extension (already landed as
  commit `3e0f611`), §8 panel definition, §9 pre-mortems.
- **Amendment rule invoked:** `PROTOCOL.md` §13 (binding pre-reg,
  amendments require a new file, no in-place edits after commit) and
  `docs/methodology/07-research-standards.md` §11 (methodology
  changes must be pre-registered before the amended metric is scored).
- **Cautionary artefacts preserved:** the original `results/ac0_regression.json`
  and `results/ac0_verdict.md` remain on-disk as the sealed record of
  the banked-telemetry attempt (per §13 and doctrine "nothing deleted").
  The AC.0-v2 outputs land at new paths (see §7 below); no overwriting.

---

## 1. Trigger — why the pre-registered AC.0 is mathematically inaccessible

AC.0 as originally locked (`PROTOCOL.md` §5 AC.0) regresses banked
`g7retry1-phi41` per-agent per-pair mean-TQS against the §4 pair-
character feature vector. The AC.0 fire on 2026-07-20 (commit
`61920b4`, results in `results/ac0_verdict.md` §5a and
`results/ac0_regression.json`) produced a structural failure — not a
signal failure. The §9 pre-mortem anticipated "AC.0 low power at n=5
pairs"; the realised banked panel is n=3 pairs and per-movable-agent
unique-x collapses further:

| Movable agent  | `.symbols` at replay time | Symbols in banked telemetry | Unique x-values per feature | OLS β well-defined? |
|---|---|---:|---:|---|
| `chigiri_hyoma`   | EURUSD, GBPUSD                     | EURUSD, GBPUSD | 2 | yes (n=14) |
| `itoshi_rin`      | EURUSD only (v1 default)           | EURUSD          | 1 | **no — CI undefined** |
| `kunigami_rensuke`| retired per G7 §11.12 (0 proposals)| —               | 0 | **no — no rows** |

The Chigiri regression that IS defined is degenerate on a different
axis: R² = 0.1643 identical across all four features, because a
2-group ANOVA on the same 14 observations yields the same explained
variance whichever feature is used as the x-axis (all four features
partition the 14 rows the same way — EURUSD vs GBPUSD). See
`results/ac0_regression.json` `movable_agents.chigiri_hyoma.features`
for the four identical R²s.

The §5 pass criterion requires ≥2 of {Chigiri, Rin, Kunigami} to
produce a non-degenerate regression with bootstrap 95% CI lower on
|β| > 0. With one defined β and two undefined, the pass criterion
cannot be evaluated on its own terms. The fail-branch verdict shipped
in `results/ac0_verdict.md` is the honest reading of the pre-reg's own
§5 language.

## 2. What changes — AC.0 reformulation (AC.0-v2)

**Old (banked, sealed):** one regression against the banked
`g7retry1-phi41` telemetry; per-movable coverage constrained by the
`.symbols` those agents shipped with at replay time.

**New (fresh compute):** one walk-forward **per movable agent**, with
THAT agent's `.symbols` widened to the full extended panel (EURUSD,
GBPUSD, USDCAD, AUDUSD, NZDUSD, and — conditional on the cache pull —
USDJPY, USDCHF). Every other agent stays at their v1 doctrine defaults
in every run. Kunigami is un-retired ONLY inside his own run (as an
active proposer/publisher); in Chigiri's and Rin's runs he stays R5
side-channel only, matching the retired-Kunigami baseline the g7retry1
verdicts were computed against.

The three fresh walk-forwards produce three trade ledgers, from which
per-movable-agent per-pair per-window mean-TQS is extracted. Those
extractions become the AC.0-v2 regression input.

**Explicit invariant:** the fresh-compute runs replace banked
telemetry ONLY for AC.0-v2's regression input. `g7retry1-phi41`
remains the canonical sealed baseline for every other purpose (G7
verdict registry, Phase AB/AA/Z audits, `reviews/g7_leave_one_out_verdict_phi5-arm4.md`).
AC.0-v2 fresh runs must not be repurposed as new G7 baselines under
any circumstances — that would be a separate pre-reg.

## 3. What stays locked (§3, §4, §5, §6 unchanged)

- **§3 canon → mechanism mapping and directional priors:** untouched.
  Chigiri `speed_momentum` → positive β on `max_session_impulse`,
  negative on `d1_chop_fraction`; Rin `analytical_precision` →
  negative β on `h4_atr_percentile`; Kunigami `defensive` → positive β
  on `d1_chop_fraction`. Same `PRELOCKED_DIRECTIONS` map as
  `run_ac0_regression.py`.
- **§4 pair-character feature vector:** unchanged, and `pair_character.json`
  remains FROZEN. AC.0-v2 must NOT recompute or refresh it — the
  frozen values are the x-axis; only the y-axis (mean-TQS) is
  re-measured on fresh telemetry.
- **§5 pass criterion (both conditions):** unchanged. ≥2 of
  {Chigiri, Rin, Kunigami} with a feature whose bootstrap 95% CI lower
  on |β| > 0, AND ≥1 passing (agent, feature) pair respecting the §3
  pre-locked direction.
- **§5.1 additivity flag:** UNION — unchanged.
- **§5.2 AC.2 success criteria:** unchanged (arms don't fire until
  AC.0-v2 passes AND AC.1 fires).
- **§6 statistic:** OLS β + percentile bootstrap 95% CI, n_boot =
  10,000, window-level resample (K = 7 rolling windows). Unchanged.

## 4. New compute cost estimate

- 3 movable agents × 1 walk-forward each on the extended panel.
- Wall-clock estimate per movable: ~30–90 min at aggregator
  `phi41` on the 5-pair (or 7-pair post-cache-pull) panel, based on
  observed g7retry1 timings (~40 min on 3 pairs).
- Total: ~2–5 h wall-clock, sequential.
- **Heartbeat monitor is MANDATORY** per repo `heartbeat-monitor` rule
  (any compute job ≥ 10 min or emitting no stdout for most of the run).

The three runs are independent; a compute-session worker MAY run them
in parallel if wall-clock savings matter and RAM permits. Each run
must emit its own crash-recovery cache under `out_dir/ac0_compute/<agent>_walkforward_cache/`
(the existing `run_g7_walk_forward` pattern of dumping `trades.jsonl`
immediately post-replay applies).

## 5. Dependency chain — USDJPY / USDCHF cache pull

The USDJPY + USDCHF cache pull (§12.1 of the original PROTOCOL,
running on the Windows/MT5 VM via `scripts/refresh_cache.py`) remains
a **hard prerequisite** for the fully-scoped AC.0-v2. Without the
pull, AC.0-v2 fires on 5 pairs (EURUSD/GBPUSD/USDCAD/AUDUSD/NZDUSD)
— still a strict improvement over the banked 3-pair collapse (unique-
x jumps from 2/1/0 to 5/5/5 for the three movables), but it reduces
statistical power.

**Recommendation (pre-registered here):** wait for the USDJPY / USDCHF
cache pull to land before firing AC.0-v2. If a compute worker is
authorised to fire before the pull completes, the 5-pair fire is
allowed but the verdict must explicitly state "partial panel (5/7
pairs)" and the outputs must land at `results/ac0_compute/<agent>_walkforward_5pair.json`
(distinct filename) so the 7-pair fire (once cache pull lands) can be
committed alongside as `_7pair.json` without collision.

## 6. Path-forward if AC.0-v2 also fails (honest kill)

If AC.0-v2 fails the same §5 pass criterion on the widened panel
(post-cache-pull, 7-pair), the study concludes with an honest negative
verdict: **pitch-terrain hypothesis is underpowered by panel size,
not refuted**. The verdict text must state that further testing
requires expanding the panel to **≥10 USD-quoted pairs** (adds
USDNOK / USDSEK / USDSGD / USDMXN as candidates for another cache-pull
campaign), with an accompanying data-plumbing cost estimate. This is
a valid negative outcome per `docs/methodology/07-research-standards.md`
§11 and does **NOT** license a third methodology switch — any third
attempt would need a fresh pre-registration and user re-authorisation.

Specifically forbidden as follow-ups after an AC.0-v2 FAIL:
- swapping OLS for a different regression family (mixed-effects,
  random-effects, weighted-by-trades) to "recover" a signal;
- dropping a movable agent from the pass criterion to shift the
  denominator from 3 to 2;
- redefining §4 features post-hoc.

Any of the above would be a §07-research-standards §11 violation.

## 7. New file footprint (§11 addition)

Preserving the §13 "nothing deleted" rule: the AC.0-v1 outputs stay,
and AC.0-v2 outputs land at NEW paths.

| Path | Content | Landed by |
|---|---|---|
| `results/ac0_compute/<agent_id>_walkforward.json` | Per-movable-agent fresh walk-forward telemetry: window bounds, per-(symbol, window) mean-TQS + trade count for the movable agent, run metadata (widened symbols, aggregator arm, roster composition). | `run_ac0_compute` |
| `results/ac0_compute/<agent_id>_walkforward.md`   | Human-readable summary of the above (per-window table + roster description + widened-symbols note). | `run_ac0_compute` |
| `results/ac0_compute/summary.json`                | Combined report across all three movables: symbols requested vs available, skipped pairs, per-agent output pointers. | `run_ac0_compute` |
| `results/ac0_regression_v2.json`                  | AC.0-v2 regression: β/CI/R² per movable × feature, computed on the fresh telemetry, joined with the frozen `pair_character.json`. Replaces `ac0_regression.json` for the amended methodology; old file preserved. | `regress_ac0` |
| `results/ac0_verdict_v2.md`                       | AC.0-v2 pass/fail narrative under §5 criterion. Replaces `ac0_verdict.md`; old file preserved. | `regress_ac0` |

Old files that MUST stay on-disk untouched:
- `results/ac0_regression.json`
- `results/ac0_verdict.md`
- `results/pair_character.json` (frozen inputs; AC.0-v2 reuses these
  verbatim — never recompute)
- `results/ac1_NOT_FIRED.md`, `results/ac2_DEFERRED.md`

## 8. New kill conditions (§10 additions)

- **Zero-trades-on-widened-pair sentinel.** Any Rin or Kunigami-un-
  retired walk-forward that emits **0 trades on any of AUDUSD /
  NZDUSD / USDJPY / USDCHF** (i.e. one of the newly-widened pairs
  where the movable agent's v1 default `.symbols` did NOT include the
  pair) is a DATA problem, not a signal — abort the AC.0-v2 fire,
  investigate the parquet cache or the agent's `prepare()` path for
  that symbol, and re-fire only after the zero-trades cause is
  identified. Zero trades on the widened pair does **not** count as a
  legitimate y = 0 mean-TQS observation for the regression.
  Chigiri is exempt on GBPUSD (already in his v1 defaults, non-zero
  trade counts observed in banked telemetry).
- **Roster-composition sentinel.** If any of the three fresh runs
  produces a per-movable trade ledger whose *proposer roster* differs
  from the intended composition (e.g. Kunigami appears as proposer in
  Chigiri's run, or Barou is missing from Rin's run), the run is
  invalid and must be discarded. The AC.0-v2 harness must assert
  roster composition at run start and record it in the per-movable
  JSON output for audit.
- **Pair-character frozen-file drift sentinel.** If `pair_character.json`
  differs (by any field, for any pair) between the AC.0 fire and the
  AC.0-v2 regression, `regress_ac0` must refuse to run. The x-axis
  must be identical bytes.

## 9. Anti-post-hoc guards (unchanged, restated for clarity)

- The §3 directional prior map is FROZEN. No entry added / removed /
  flipped after this amendment file is committed.
- The §5 pass criterion (both conditions) is FROZEN. No relaxation
  from ≥2/3 to ≥1/3, no substitution of |β| CI lower with a p-value
  threshold, no re-scoping to "at least Chigiri passes".
- The §6 statistic (percentile bootstrap 95% CI, n_boot = 10,000,
  window-level resample, seed pinned) is FROZEN. Reproducibility is
  a locked test (see `test_regress_ac0.py::test_regress_ac0_bootstrap_reproducibility`).
- The §7 file paths (this section) are FROZEN. Renaming a `_v2` file
  post-fire to overwrite the `_v1` file would violate §13.
- No re-running of `run_ac0_compute` after `regress_ac0` has been
  fired on the outputs (would be selective sampling on the y-axis).
  If a re-run is genuinely needed (e.g. an environment bug), the old
  outputs must be preserved under a `_dropped` suffix and the reason
  written into `results/ac0_compute/RUN_LOG.md`.

## 10. Sequencing (§12 addition — insert Step 3b)

Original §12 sequence:
1. Cache pull (USDJPY + USDCHF).
2. Harness extension (landed, commit `3e0f611`).
3. AC.0 fire (banked telemetry) — **now FAILED and sealed.**
4. AC.1 fire, 5. AC.2 fire, 6. Verdict.

New sequence with AC.0-v2 slotted in:
1. Cache pull (unchanged; still a hard prereq for full 7-pair AC.0-v2).
2. Harness extension (unchanged; landed).
3. AC.0 fire (banked) — **SEALED FAIL; retained as record.**
3a. Amendment ratification (this file committed).
3b. **AC.0-v2 fresh-compute fire.** Runs `run_ac0_compute` (3 movable
    agent walk-forwards) + `regress_ac0` (regression + verdict). PASS
    gates AC.1; FAIL concludes study with negative verdict per §6 of
    this amendment.
4. AC.1 fire (unchanged; gated on AC.0-v2 PASS).
5. AC.2 fire (unchanged).
6. Verdict (unchanged).

## 11. Testing surface (locked with this amendment)

- `sim/tests/test_run_ac0_compute.py` covers: movable `.symbols`
  widening, missing-pair skipping, output schema, Kunigami un-
  retirement roster wiring, per-movable roster isolation.
- `sim/tests/test_regress_ac0.py` covers: synthetic positive-signal
  recovery (β within tolerance, direction respected, CI lower > 0),
  null-signal cleanliness (most features straddle 0), bootstrap
  reproducibility (same seed → identical bounds), pass-criterion
  arithmetic (2/3 → PASS, 1/3 → FAIL), and the direction gate
  (|β| CI passes but direction contradicts §3 → does NOT count).

## 12. What this amendment does NOT authorise

- Firing AC.0-v2 compute (a separate delegation).
- Modifying `pair_character.json`.
- Modifying `run_g7_v1_checkpoint_gate.py` beyond the harness
  extension already landed in commit `3e0f611`.
- Repurposing the fresh-compute AC.0-v2 telemetry as a new G7
  baseline or Phase-AB/AA/Z audit input.
- Any change to §3, §4, §5, §5.1, §5.2, §6 without a further
  amendment file.

---

**Status:** amendment ratified 2026-07-20; AC.0-v2 harness and
regression code shipped in the two commits following this file.
AC.0-v2 compute fire is a follow-up delegation, blocked on the
USDJPY/USDCHF cache pull per §5 above.
