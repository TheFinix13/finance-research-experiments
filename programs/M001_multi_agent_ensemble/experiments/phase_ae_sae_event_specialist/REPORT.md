# Phase AE — Sae Itoshi event specialist (campaign REPORT)

**Written:** 2026-07-24 (UTC).
**Program:** M001 multi-agent ensemble.
**Branch:** `multi-agent-ensemble` (research repo). No port to the
trading repo recommended — verdict FAIL (§1).
**Pre-registration:** `PROTOCOL.md` (drafted 2026-07-20, LOCKED
2026-07-24 with §0 pre-run factual amendments, commit `dfe5ce1`,
BEFORE any arm ran).
**Verdict file:** `../../reviews/phase_ae_verdict.md` ·
**Evaluation JSON:** `results/phase_ae_evaluation.json`.

---

## 1. Topline

**FAIL.** Sae v1 (event-specialist striker: fade rejection wicks /
ride retained impulses on high-impact USD prints, M15, EURUSD-only)
clears the volume floor but decisively misses the quality bar:

- **AE1 PASS** — 54 OOS trades (locked floor ≥ 30); 87 on the full
  2015-2025 panel. 100% calendar-gated: every trade maps to a frozen
  NFP/CPI/FOMC event.
- **AE2 FAIL** — OOS mean TQS **0.097** vs locked floor 0.30;
  bootstrap 95% CI **[0.042, 0.162]** (n=10,000, seed=42, percentile)
  vs locked CI-lower floor 0.20. Not close on either clause.
- **AE3** — fade 12/54 (22.2%, mean TQS 0.122, mean −4.18 pips),
  ride 42/54 (77.8%, mean TQS 0.089, mean −8.52 pips). Both ≥ 20%,
  so no mechanic parked — both simply lose.
- **AE4 PASS** — no incumbent regression: Isagi/Bachira/Rin/Nagi/Barou
  deltas exactly 0.000; Chigiri +0.001 (503 → 501 trades, the only
  two H4 trades displaced by Sae's M15 book in 11 years); Reo 0 trades
  in both arms (long-standing baseline behaviour).

PASS required AE1 ∧ AE2 ∧ AE4 → **FAIL**. `sae_enabled` stays False
in production; nothing arms for the Aug 7 NFP.

Trade-level failure signature: 25 TP / 62 SL = 28.7% win rate at a
fixed 1.5R target (breakeven 40%), mean −4.16 pips/trade over 87
trades. Per-window OOS mean TQS: 0.245, 0.064, 0.096, 0.266, 0.088,
0.000, 0.073 — uniformly poor, no rescueable regime.

---

## 2. What was run

### 2.1 Arms

Both arms: §11.17 panel (2015-01-01 → 2025-12-31, 7 walk-forward
windows, 4-yr IS / 1-yr OOS), symbols EURUSD/GBPUSD/USDCAD,
g7retry2-shaped roster (7 proposers, Kunigami retired to Sentinel R5
side channel), phi41 aggregator, sentinel_blocks=True, workspace ON,
R7 absent by construction (PROTOCOL §0 amendment 5).

| Arm | Tag | Sae | Trades | Proposals | Wall-clock |
|---|---|---|---:|---:|---|
| Baseline | `ae-baseline` | off | 5,128 | 19,917 | ~23 min |
| Treatment | `ae-treatment` | on (M15 event ticks) | 5,208 | 20,107 | ~24 min |

Results: `results/results_ae-{baseline,treatment}.json`; crash-proof
per-trade dumps in `results/ae_replay_cache_*/`; heartbeat log
`../../reviews/compute_heartbeat.log` (both runs monitored; both
healthy 84-100% CPU throughout).

### 2.2 Harness (all additive, committed before the arms)

- `sim/agents/a09_sae.py` — research-sim port of the trading repo's
  `agent/squad/agents/a09_sae.py` (branch `next-gen`, commit
  `a26eba8`). **Mechanics and `SaeConfig` values are verbatim**; the
  only divergences are harness plumbing (sim types, frozen-calendar
  loader instead of live cache, `home_tf="M15"`, `workspace=` kwarg
  accepted), each flagged in the module docstring.
- `sim/scoring/run_phase_ae_compute.py` — `_drive_squad_replay_ae`,
  a phi41-specialised copy of the sealed `_drive_squad_replay` that
  injects Sae's M15 event ticks (T+15/T+30 per event) into the H4
  replay in strict wall-clock order; Sae trades open/manage on M15
  bars and share the per-symbol single-position slot with the H4 book
  in both directions.
- `experiments/.../evaluate_phase_ae.py` — one-shot AE1-AE4 scorer,
  committed before any arm ran.
- Tests: `sim/tests/test_a09_sae_sim.py` (13 mechanic/guard tests) and
  `sim/tests/test_phase_ae_harness.py` (tick builder + the
  load-bearing **baseline equivalence test**: AE driver with
  `sae=None` reproduces `_drive_squad_replay` trade-for-trade on a
  real 2-year EURUSD slice). 14 fast + 1 slow, all green pre-run.

### 2.3 Data provenance

- **Calendar fixture:** `data/news_calendar_frozen_2026-07-24.json` —
  349 high-impact USD events 2015-2025 (131 NFP + 131 CPI + 87 FOMC
  statements), sha256
  `cfd186021ea87a5acba4f672250519d89fb8657c11473a73621bcc78c0ee3134`.
  Sources: BLS Employment Situation + CPI official release schedules
  via pinned Internet Archive snapshots (later-snapshot-supersedes
  rule handles the Oct-Nov 2025 shutdown reschedules: 11 NFP + 11 CPI
  in calendar 2025) + federalreserve.gov FOMC calendars
  (notation-vote/unscheduled/cancelled excluded rule-based; 7
  statements in 2020). Builder: `build_calendar_fixture.py`. Frozen
  2026-07-24, never refetched.
- **M15 bars:** trading-repo parquet cache (read-only),
  `EURUSD_M15.parquet`, 284,277 rows, 2015-01-01 22:00 →
  2026-05-27 12:45 UTC; 274,218 bars inside the panel.
- **H4 bars:** same cache as every prior G7 campaign (17,7xx bars per
  symbol).

---

## 3. Incidents (full disclosure)

1. **Aborted first treatment launch (no results computed).** The first
   treatment process was killed by shell teardown ~10 s after launch
   (nohup under a sandboxed shell); died during agent prepare, before
   the replay loop. Relaunched as a persistent background shell.
2. **Read-only-coupling violation, caught and fixed.** The original
   M15 loader used the production `BarLoader.get(refresh=False)`,
   whose head-gap auto-backfill silently opened a Dukascopy network
   fetch (panel start 00:00 precedes the cache's first bar at 22:00)
   and touched `EURUSD_M15.parquet`'s mtime. The run was killed within
   ~5 minutes; the cache was verified undamaged (row count, coverage
   window and gap structure identical to pre-run recon). Fix: the
   loader now reads the parquet directly via pandas — no network path
   exists (commit `766326a`). No arm that produced results ever used
   fetched data; both scored arms ran entirely on the frozen cache.
3. **Monitor mis-pinned once** to the shell wrapper PID instead of the
   python PID (cosmetic heartbeat noise, ~3 samples); re-pointed.

None of these touch the evaluation: the protocol was locked before any
arm, the evaluator was committed before any arm, and both scored arms
ran on identical frozen inputs.

---

## 4. Limitations

1. **Calendar is a conservative subset** (NFP + CPI + FOMC ≈ 2.7
   events/month vs the ForexFactory-High ~4-8/month prior). A denser
   calendar would raise trade count, not TQS — the quality failure is
   about post-event M15 predictability, not sample size (CI upper
   bound 0.162 is still below both floors).
2. **Single symbol.** EURUSD-only per SaeConfig v1; no claim about
   USD events traded via other pairs.
3. **Fixed 1.5R bracket, market-typical fills.** Next-M15-bar-open
   entry, no slippage/spread-widening model. Real NFP spreads are
   catastrophically wider — live results would be WORSE than sim, which
   only strengthens the FAIL.
4. **TQS quality bar** is the g7retry2 house metric; a pure-pips
   evaluation would not change the verdict (mean pips negative).
5. Sae never proposed on H4 ticks (M15-only by design), so this says
   nothing about event-day H4 behaviour.

---

## 5. Consequences

- `sae_enabled=False` stays in production; the Aug 7 NFP arming
  decision is moot.
- The hour-13 bleed evidence now reads "avoidable, not tradable" —
  Phase AD Karasu (defensive blocking) remains the only live lever on
  event windows.
- Sae v2, if ever, needs a fresh pre-registration with different
  mechanics; v1's fade/ride + 1.5R are spent and may not be retuned
  against this panel.
