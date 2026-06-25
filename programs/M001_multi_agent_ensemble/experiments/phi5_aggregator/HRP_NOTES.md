# HRP port notes — Arm 1 of Φ5 aggregator selection experiment

**Source:** `/Users/the1finix/Documents/GitHub/multi-pair-trading-agent/agent/alphas/allocator.py`
**Target:** `programs/M001_multi_agent_ensemble/sim/core/aggregator/hrp.py` (NEW)
**Audit classification:** `KEEP-AND-INHERIT` per `docs/audits/2026-06-24_unclear_resolutions.md`
**Estimated LoC:** ~150 (production is 113; M001 port adds TQS adapter + simulator API contract = ~40 extra)

---

## What the production allocator does

`agent/alphas/allocator.py` exports `allocate(streams, *, min_days=20, shrinkage=0.2)` returning an `AllocationResult` with per-alpha weights. The mechanic:

1. **Daily P&L grid:** sum `pnl_pips` per calendar exit-day per alpha (`daily_returns()`).
2. **Eligibility filter:** alphas with < `min_days` days of trading history excluded (drop, not down-weight).
3. **Shared-day matrix:** `mat[alpha, day]` with zero-fill for non-trading days.
4. **Mean-variance tangency weights:** `w ∝ Σ⁻¹ μ` where `μ` is per-alpha mean daily return and `Σ` is the covariance matrix.
5. **Ledoit-Wolf-style shrinkage toward diagonal:** `Σ_s = (1-shrinkage) * Σ + shrinkage * diag(Σ)` (with shrinkage=0.2). Plus jitter `1e-9 * I` on the diagonal for numerical solve stability.
6. **Long-only clip + normalise:** `w = max(w, 0)`, then `w /= w.sum()`. Fallback if `w.sum() == 0`: equal-weight on positive-edge alphas (`mu > 0`).
7. **Reports:** ensemble vs best-single Sharpe, correlation matrix, included/excluded alphas.

Production scales returns by `ANNUALISATION = sqrt(252)` for Sharpe reporting — this is irrelevant to the M001 port because M001 reports TQS, not Sharpe.

---

## What needs to change for M001

### Input contract

| Production | M001 |
|---|---|
| `streams: dict[alpha_name -> list[Trade]]` (Trade dataclass with `pnl_pips`, `exit_time`, `is_open`) | `streams: dict[agent_id -> list[ScoredTrade]]` (ScoredTrade has `tqs: float`, `exit_ts: datetime`, `pnl_pips: float`, attribution fields) |
| Aggregation grain: calendar day | Aggregation grain: OOS-window (n=7 for the Φ5 panel) |
| Score axis: pip P&L | Score axis: TQS (F12) — pip P&L tracked alongside as a sanity diagnostic |

### Output contract

Production returns weights in `AllocationResult`. The M001 aggregator needs the weights consumed at PROPOSAL time, not POST-trade — so the port wraps `allocate()` with a stateful adapter that:

1. Calls `allocate()` on the running OOS-window history at the start of each window.
2. Caches the resulting per-agent weights for the duration of that window.
3. At each tick, when an agent emits a Proposal, the aggregator multiplies the proposal's `risk_pct` by the agent's weight (or sets `risk_pct = base_risk * weight[agent]`).
4. At window roll-over, weights re-fit on the now-extended history.

### Numerical adaptations

- **Min-trades guard.** Production uses `min_days = 20`. The Φ4.1 panel has Rin (94 trades, ~70 trading days) and Nagi (94 trades, ~70 trading days). M001 raises this to `min_trades_per_agent = 30` per the protocol (different unit: trades, not days). Excluded agents do not receive a weight; they default to the equal-weight pool floor.
- **Weight cap.** Production has no max-weight cap. M001 adds `weight_cap = 0.5` (no agent gets > 50% of risk budget) to prevent a single positive-TQS agent from dominating early in the panel.
- **Fallback path.** Production falls back to equal-weight on positive-edge alphas. M001 inherits this. If all agents have zero or negative TQS in the window, fallback to fully-equal-weight (matches production's `np.ones / n` final fallback).
- **Score series:** production computes `daily_returns()` from trade pip P&L. M001 substitutes `per_window_tqs[agent]` (one scalar per OOS window, not a daily series) — the covariance is then over agents × windows (n_windows = 7). With 7 observations per agent, covariance is *very* unstable. Mitigation: shrinkage stays at 0.2 but jitter rises to `1e-7 * I` (vs prod's `1e-9`) — empirical dampening on small-n covariance.

### Tests to port + extend

Production has tests at `tests/test_allocator.py` (verify by `git ls-files | grep test_allocator`). Port:
- `test_allocate_smoke` — equal streams produce equal weights
- `test_allocate_correlated_alphas_downweighted` — two highly-correlated alphas should each get less than half the weight a single alpha would get
- `test_allocate_negative_edge_excluded` — alpha with negative mean return gets zero weight
- `test_allocate_min_days_excludes_short_streams` — alphas below threshold excluded
- `test_allocate_long_only` — no negative weights returned

NEW tests for the M001 adapter:
- `test_hrp_window_rollover` — weights re-fit at window boundaries, not within
- `test_hrp_min_trades_per_agent` — sub-30-trade agents excluded, fallback applies
- `test_hrp_weight_cap` — no agent receives > 0.5 weight even if pure tangency would allocate more
- `test_hrp_zero_total_tqs_fallback` — all-negative-TQS window returns equal weights, never NaN
- `test_hrp_phi41_replay` — replay Φ4.1 trades through HRP adapter; weights should down-weight Bachira (mean TQS 0.299) relative to Nagi (mean TQS 0.349) given equal n
- `test_hrp_singleton_window` — window with only 1 trading agent returns weight = 1.0 for that agent (degenerate covariance handled)

---

## Dependencies

Production imports: `numpy`, `dataclasses`, `collections`, `datetime`. All already in M001 `pyproject.toml`. **No new dependencies required for the port.**

Optional: scipy for `pinv` if `np.linalg.solve` continues to fail after shrinkage + jitter. Not anticipated in the small-n M001 case but worth keeping handy.

---

## Open implementation questions for tomorrow's worker

1. **Weight series vs window-snapshot.** Production aggregates daily; M001 aggregates per-OOS-window. Should the HRP weights be re-fit at every OOS window roll, or every IS+OOS slide (i.e. weekly)? Recommended: per-OOS-window roll (matches Φ4.1 walk-forward cadence).
2. **Same-side correlation handling.** If two agents both fire trades in the same direction on the same day, do they contribute as one observation or two to the covariance? Recommended: two observations (preserves trade-level signal). Note in the report.
3. **Fallback stickiness.** When the fallback equal-weight path triggers, does the next window inherit the fallback or attempt tangency again? Recommended: attempt tangency every window (no inheritance); fallback is a per-window state.
4. **TQS or pips for the covariance axis?** Protocol locks TQS. Sanity check: also compute the pip-axis covariance for a journalled comparison. If they substantially disagree on weights, that's a finding worth flagging.

---

## Cross-references

- Source: `agent/alphas/allocator.py` (production)
- Audit: `docs/audits/2026-06-24_unclear_resolutions.md` §allocator.py — KEEP-AND-INHERIT
- Doctrine: `06-blue-lock-doctrine.md` §3.1 Capital Allocator
- Foundations: `04-quant-foundations.md` F12 TQS (the score axis)
- Protocol: this folder's `PROTOCOL.md` Arm 1 spec
