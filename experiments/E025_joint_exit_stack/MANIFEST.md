| Field | Value |
|---|---|
| ID | E025 |
| Short name | Joint exit-stack Pareto validation |
| Pre-registration commit | (see git log) |
| Status | **`cancelled_dependency_failed` (2026-07-20)** — all four upstream studies (E020/E021/E022/E024) landed `dead`. Zero-alive-upstream is a deterministic cancellation per PROTOCOL §4a. Phase 2 not run; Phase 3 not authorised. See [`STOP_NOTICE.md`](./STOP_NOTICE.md). |
| Study type | composability / safety-net (not a new mechanism) |
| Primary artefacts | `PROTOCOL.md`, `results.json` (placeholder until Phase 2), `STOP_NOTICE.md` (if `dead`/`cancelled_dependency_failed`) |
| Compositions | π0 (baseline) · π1 = A (E022) · π2 = A+B (+E021) · π3 = A+B+C (+E020) · π4 = A+B+C+D (+E024) |
| Upstream arm hyperparameters | TBD — filled from E020/E021/E022/E024 verdicts before Phase 2 |
| Primary metric | Δ Sharpe of per-trade R sequence (paired bootstrap-95 % CI, seed 42, resamples 5000, per-fold + pooled) |
| Secondary guardrails | tail-mean R (worst 10 %), mean R, max consec-loss streak, P(R < −1.0R) — see §4 for caps |
| Selection-inflation control | Deflated Sharpe against family size 57 (12+9+12+24 upstream arms) |
| Verdict gate | Pareto dominance on Δ Sharpe + all secondaries + OOS-only sensitivity + bar-granularity sensitivity |
| Phase 3 gate | production `ExitManager` module wiring proceeds ONLY on `alive` verdict here, plus ≥2 weeks paper-mode observation |
| Dependencies | E020, E021, E022, E024 verdicts must all be registered before Phase 2 kickoff |
| Key references | bailey2016pbo, chekhlov2005drawdown, stouffer1949american, sharpe1994, kaminski2014stop; also E017, E019, E013 (in-repo) |

## Verdict

**`cancelled_dependency_failed`** — 2026-07-20.

Per PROTOCOL §4a, "Zero `alive`: E025 is `cancelled_dependency_failed`.
No stack ships." Upstream results at commit-time:

| Study | Verdict | Commit |
|---|---|---|
| E020 (MFE ratchet) | `dead` | `7e1a3e7` |
| E021 (partial exit) | `dead` | `343b512` |
| E022 (structure TP snap) | `dead` | `dbe398c` |
| E024 (near-TP stall exit stage-1) | `dead` | `93f4887` |
| **E025 gate** | **cancelled** | this commit |

Zero upstream arms crossed the `alive` bar, so no arm hyperparameters
can be plugged into the composition ordering `π1..π4`. There is
nothing to stack — E025 does not run Phase 2, does not launch its
composition sweep, does not spend from its family-size-57 selection
budget, does not open a `DATA_LEDGER.md` row.

The deployed `all_on` cell (wick_proof + be_migration + plg + fixed
1.5R TP) stays as-is. Phase 3 (production `ExitManager` wiring in
`agent/live/exit_manager.py`) is not authorised. The
`LiveConfig.partial_exits = False` and `LiveConfig.exit_manager_enabled
= False` defaults stay.

**What the four upstream deads collectively say about the exit-side
question.** E020 and E024 die by opposite mechanisms — E020's
MFE-ratchet chops runners (P(reach 1R) collapses by up to 22 pp under
the tightest arm); E024's near-TP stall detector eats 60–91 % of
clean TPs across every one of its 72 (arm, symbol) cells. E021's
partial-exit mechanic works exactly as PROTOCOL §3 predicted (tail
cap +1R, variance drop, give-back rescue +7–18 pp) but the mean-R
cost on the 47–63 % of trades that cross the trigger dominates.
E022's TP-snap actually raises P(TP fills) by up to +3.48 pp — the
one mechanism whose sanity gate PASSED across all 12 arms — but the
per-winner R give-up dominates the fill-rate gain by a factor of ~5.
Structurally, the deployed cell's 1.5R fixed TP is priced correctly
by E004 walk-forward and E005 cross-pair sealed; any exit-side rule
that either narrows the TP band, tightens the stop earlier, or
closes early inside the near-TP zone is a Sharpe loss on this cell.

**Not shipping E025 is a legitimate result**, not a failure to
execute. The composability safety net did its job: it caught the
"no upstream mechanism cleared its own bar" case before any
integration code got written. A future exit-side campaign would
need a genuinely new mechanism (e.g. E023 post-BE structure trail,
which is unrelated to the four here) or a redesigned baseline cell
(different `target_rr` from a fresh walk-forward), not another
iteration on the E020–E024 grid.

No `STOP_NOTICE.md` follow-up actions. E025 stays pre-registered on
main for lineage; if a future exit-side study lands `alive`, it
would need a NEW pre-registration (E025-successor or fresh ID), not
an amendment.
