# Shared counterfactual-replay harness — SPEC (PRE-0)

**Status:** SPEC · **Date:** 2026-07-20 · **Consumers:** E020, E021, E023, E024, E025

## Purpose

E020 (MFE ratchet), E021 (partial exit at 1R), E023 (post-BE structure
trail), E024 (near-TP stall exit), and E025 (joint stack) all ask a
question of the form: "if we had applied rule R to every historical
trade of the deployed `zone_d1_against` cell, would the pnl distribution
have been better than the actual observed outcomes?" That question is a
**bar-by-bar replay** of each trade with an alternative exit rule applied.

The existing `programs/E017/data/trade_ledger_EURUSD_H4.json`
(regenerated read-only from the E013 `all_on` harness) has only
`entry_time / exit_time / stop_pips / pnl_pips / r / exit_reason` — no
intra-trade path, no MFE, no MAE. Every consumer study above needs the
intra-trade path to evaluate its alternative exit; without it there is
no counterfactual.

PRE-0 is the shared data-plane extension: **extend the ledger export to
emit intra-trade OHLC + MFE/MAE + timestamps for all three deployed
symbols (EURUSD, GBPUSD, USDCAD) on the H4 all-session cell**, then
publish one loader utility every consumer study imports.

## What PRE-0 delivers

1. `programs/_shared/counterfactual_replay/export_ledger_with_paths.py` —
   extends the E017 exporter. Given a symbol and TF, emits one JSONL
   file per trade under
   `programs/_shared/counterfactual_replay/data/{symbol}_{tf}_paths.jsonl`
   with schema §1.
2. `programs/_shared/counterfactual_replay/replay.py` — loader +
   deterministic per-trade replay engine. Consumer studies register a
   `RuleFn(trade, current_bar) -> ExitAction | None` and get back a
   modified trade ledger `results.json`.
3. `programs/_shared/counterfactual_replay/tests/` — unit tests
   asserting invariants (§4).

## §1 Per-trade schema (JSONL, one trade per line)

```jsonc
{
  "trade_id": "EURUSD_H4_00042",          // stable id: symbol_tf_index
  "symbol": "EURUSD",                     // "EURUSD" | "GBPUSD" | "USDCAD"
  "tf": "H4",
  "direction": "long",                    // "long" | "short"
  "entry_time": "2015-02-17T08:00:00+00:00",
  "entry": 1.13245,                       // fill price (locked from prod-matching harness)
  "stop": 1.12963,                        // catastrophic SL (original, entry-time)
  "soft_stop": 1.13034,                   // panic SL (original, entry-time)
  "take_profit": 1.13668,                 // TP (1.5R above/below entry)
  "stop_pips": 28.2,                      // entry - stop in pips
  "tp_pips": 42.3,                        // = 1.5 * stop_pips (locked cell property)
  "r": 1.5,                               // realised R (from base ledger)
  "pnl_pips": 42.3,
  "exit_time": "2015-02-17T20:00:00+00:00",
  "exit_price": 1.13668,
  "exit_reason": "tp",                    // as recorded in base ledger

  // *** New fields added by PRE-0 ***
  "mfe_pips": 42.3,                       // max favorable excursion (pips)
  "mae_pips": 4.1,                        // max adverse excursion (pips)
  "mfe_ts": "2015-02-17T20:00:00+00:00",  // timestamp of MFE peak
  "mae_ts": "2015-02-17T08:15:00+00:00",  // timestamp of MAE trough
  "mfe_r": 1.5,                           // mfe_pips / stop_pips (signed pos)
  "mae_r": 0.145,                         // mae_pips / stop_pips (signed pos)
  "path_m5": [                            // M5 OHLC between entry_time and exit_time (inclusive)
    {"ts": "2015-02-17T08:05:00+00:00", "o": 1.13245, "h": 1.13260, "l": 1.13210, "c": 1.13240},
    // ... one row per M5 bar until exit_time ...
  ],
  "path_h1": [                            // H1 OHLC (subset, for coarse-grained studies)
    {"ts": "2015-02-17T09:00:00+00:00", "o": 1.13240, "h": 1.13380, "l": 1.13235, "c": 1.13360},
    // ...
  ],
  "target_ladder": [                      // if available from production journal; else omit
    {"price": 1.13780, "r_multiple": 1.9, "source": "daily_level", "detail": "PDH"},
    // ...
  ]
}
```

### Field derivation rules (deterministic, tested)

- `mfe_pips` = max favorable move from entry across the intra-trade OHLC
  path, in pips. For a long: `max(bar.high - entry) * pip_factor` over
  every bar in `path_m5` between `entry_time` and `exit_time`.
- `mae_pips` = max adverse move from entry across the same path.
- `mfe_ts` = timestamp of the M5 bar whose high (long) or low (short)
  produced the MFE; **if ties, the earliest bar wins** (deterministic).
- `path_m5` uses the same M5 OHLC source as the E017 harness. If M5 not
  available for a date range, the path degrades to `path_h4` bars and
  the record carries `"path_resolution": "H4"` with `mfe_pips/mae_pips`
  computed from H4 highs/lows (lower fidelity — flagged, not silently
  dropped).
- `target_ladder` is only included when the production near-miss vault
  or ladder journal has an entry for that trade; otherwise omitted.
  (Historical trades from 2015-2025 will have this field mostly absent;
  2026-onward trades will have it. Studies must not require it.)

## §2 Symbols and window

- **Symbols:** EURUSD, GBPUSD, USDCAD (all three deployed cells, per user
  scope decision 2026-07-20).
- **Timeframe:** H4 (deployed cell).
- **Alpha / toggles:** `zone_d1_against` with `all_on` (wick_proof +
  be_migration + plg) — same production-matching harness E017 pinned.
- **Full window:** 2015-01-01 → 2025-12-01 (matches E017 §7 §A1).
- **Expected trade counts:** EURUSD 737 (locked from E017 hit-rate 0.5577
  reconciliation); GBPUSD and USDCAD to be generated fresh — will publish
  actual counts + hit-rates in `data/{symbol}_{tf}_paths.jsonl` header.

## §3 Walk-forward split (mirrors E004)

Consumer studies inherit the same 5-fold walk-forward split as the
deployed cell's E004 validation (documented in
[`experiments/E004_walk_forward/PROTOCOL.md`](../../../experiments/E004_walk_forward/)):

| Fold | Train (fit rule) | Test (score rule) |
|---|---|---|
| 1 | 2015-01 → 2016-12 | 2017-01 → 2018-12 |
| 2 | 2015-01 → 2018-12 | 2019-01 → 2020-12 |
| 3 | 2015-01 → 2020-12 | 2021-01 → 2022-12 |
| 4 | 2015-01 → 2022-12 | 2023-01 → 2024-06 |
| 5 | 2015-01 → 2024-06 | 2024-07 → 2025-12 |

Consumer studies choose their arm hyperparameters on the train slice of
each fold and score on the test slice. **No test-slice leakage.**

## §4 Replay engine contract (deterministic)

```python
@dataclass
class ExitAction:
    kind: Literal["close_at", "adjust_stop", "adjust_tp", "partial_close"]
    price: float | None = None        # for close_at, adjust_stop, adjust_tp
    fraction: float | None = None     # for partial_close (0..1)
    reason: str = ""                  # for the exit_reason log

RuleFn = Callable[[TradeState, Bar], ExitAction | None]

def replay(
    trade: TradeRecord,
    rule: RuleFn,
    tf_grid: Literal["M5", "H1", "H4"] = "M5",
    interaction_hierarchy: list[str] | None = None,
) -> AltTradeRecord:
    ...
```

**Invariants (unit-tested):**
1. `replay(trade, null_rule) == trade` — with no active rule, the replay
   reproduces the original trade byte-for-byte on `exit_time`, `exit_price`,
   `pnl_pips`, `r`, `exit_reason`, `mfe_pips`, `mae_pips`.
2. **Stop authority monotonicity** — a rule may only tighten a stop, never
   loosen it. If a rule returns `adjust_stop(price=X)` and `X` is looser
   than the current effective stop, the action is dropped with a warning.
3. **Exit-priority ordering** — on any bar, if multiple rules fire, the
   priority is (highest → lowest):
   `hard_catastrophic_SL → hard_soft_SL → E024_stall_exit →
   E021_partial_close → broker_TP_hit → E020_MFE_ratchet_stop →
   E023_structure_trail`. This mirrors what the live agent's
   `ExitManager` must implement.
4. **No look-ahead** — a rule's decision on bar `i` may only use bars
   `≤ i` (validated by a mutation test in the harness).
5. **Determinism** — for a fixed trade + rule + seed, output is identical
   across runs.

## §5 Test plan

- `test_export_shapes.py` — every trade emits schema §1, no missing keys.
- `test_mfe_mae_recovery.py` — for a synthetic trade with a known
  price path, MFE/MAE/MFE_ts/MAE_ts match hand-computed values.
- `test_null_rule_invariant.py` — invariant §4.1.
- `test_stop_monotonicity.py` — invariant §4.2.
- `test_exit_priority.py` — invariant §4.3 (three rules firing on same bar
  → highest-priority wins).
- `test_no_lookahead.py` — mutating bar `i+1` never changes decision at
  bar `i`.
- `test_determinism.py` — invariant §4.5.

## §6 Output artifact

`programs/_shared/counterfactual_replay/data/{EURUSD,GBPUSD,USDCAD}_H4_paths.jsonl`

One line per trade, gzip-compressed sidecars optional. Header line (first
line, prefixed `# meta: `) carries symbol, TF, generator commit, count,
window bounds, hit-rate.

## §7 What each consumer study reuses

| Study | Uses from PRE-0 |
|---|---|
| E020 MFE ratchet | `mfe_pips`, `mfe_ts`, `path_m5` (to walk MFE forward and detect stop hits) |
| E021 Partial exit at 1R | `path_m5` (to find the first bar that hits `entry ± partial_R × stop_pips`) |
| E022 Structure TP snap | Only `target_ladder` field (order-placement study, no path replay needed); if absent, uses `programs/_shared/level_detector.py` to compute levels from bar-level OHLC around entry time |
| E023 Post-BE structure trail | `path_h1`, `path_m5`, plus `target_ladder` for structure anchors |
| E024 Near-TP stall exit | `mfe_pips`, `mfe_ts`, `path_m5` (for wall-clock stall detection), `path_h1` (for bar-based stall arms) |
| E025 Joint stack | All of the above simultaneously, via `replay()` with the multi-rule ordering (§4.3) |

## §8 Delivery order

1. **Day 1:** Extend `programs/E017/data/trade_ledger_EURUSD_H4.json`
   generator to emit path schema §1 for EURUSD. Land unit tests.
2. **Day 2:** Generate GBPUSD_H4_paths.jsonl and USDCAD_H4_paths.jsonl
   using the same production-matching harness (E013 `all_on`).
3. **Day 3:** Publish `replay.py` engine + invariant tests. Ready for
   consumer studies to import.

PRE-0 has no verdict of its own — it is infrastructure. Consumer study
protocols reference this SPEC by path.
