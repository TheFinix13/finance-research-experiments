# PRE-0 shared counterfactual-replay harness

Shared data plane + replay engine for the E020-E025 exit-management
campaign. Spec: [`SPEC.md`](./SPEC.md).

## What lives here

- `SPEC.md` — pre-registered contract (schema, invariants, delivery order).
  Amended 2026-07-20 to reflect the shipped per-trade resolution fallback.
- `export_ledger_with_paths.py` — extends `programs/E017/export_trade_ledger.py`
  to emit per-trade intraday OHLC paths + MFE/MAE + timestamps.
- `replay.py` — deterministic single-trade replay engine. Consumer
  studies register a `RuleFn(state, bar) -> ExitAction | None` and the
  engine walks each trade's intraday path applying the SPEC §4.3 exit
  priority and §4.2 stop monotonicity invariants.
- `tests/test_replay_invariants.py` — the SPEC §4 / §1 invariant tests
  (all 14 currently passing).
- `data/` — generated JSONL path ledgers. **Not tracked in git** (~34
  MB); regenerated on demand from the agent parquet cache. See
  regeneration section below.

## Regenerating the path ledgers

The ledgers depend on the agent parquet cache at
`../multi-pair-trading-agent/data/parquet/`. Given that cache, run:

```bash
cd finance-research-experiments
for sym in EURUSD GBPUSD USDCAD; do
    PYTHONPATH=../multi-pair-trading-agent:.:scripts \
        ../multi-pair-trading-agent/.venv/bin/python \
        programs/_shared/counterfactual_replay/export_ledger_with_paths.py \
        --symbol $sym
done
```

Wall-clock ≈ 30-60 s per symbol. Output:

```
programs/_shared/counterfactual_replay/data/EURUSD_H4_paths.jsonl  (24 MB)
programs/_shared/counterfactual_replay/data/GBPUSD_H4_paths.jsonl  ( 8 MB)
programs/_shared/counterfactual_replay/data/USDCAD_H4_paths.jsonl  (~1 MB)
```

## Verifying the ledgers reproduce the base cell

The null-rule invariant test runs the replay engine with `rule=None` over
every trade in every ledger and asserts byte-for-byte reproduction of the
base ledger's exit fields. Run:

```bash
../multi-pair-trading-agent/.venv/bin/python -m pytest \
    programs/_shared/counterfactual_replay/tests/test_replay_invariants.py -v
```

All 14 tests should pass, including the three parametrised
`test_null_rule_reproduces_base_ledger[{EURUSD,GBPUSD,USDCAD}]` cases.

## Base-ledger anchors (2026-07-20 generation, commit `bb00c9e`)

| Symbol | Trades | Hit-rate | Mean R | Path resolution histogram |
|---|---:|---:|---:|---|
| EURUSD | 737 | 0.5577 | 0.382 | M5: 737 |
| GBPUSD | 944 | 0.5561 | 0.359 | M15: 668, H4: 276 |
| USDCAD | 707 | 0.5446 | 0.369 | H4: 707 |

EURUSD reconciles exactly to the E017 anchor (`programs/E017/data/trade_ledger_EURUSD_H4.json`).
GBPUSD/USDCAD anchors are established fresh here (no prior ledger existed).

## Consumer study API

```python
from programs._shared.counterfactual_replay.replay import (
    load_paths_ledger, replay, replay_all,
    ExitAction, TradeState, Bar, RuleFn,
    PIP, BE_TRIGGER_R,
    PRIORITY_E020_RATCHET, PRIORITY_E021_PARTIAL,
    PRIORITY_E024_STALL, PRIORITY_TP,
)

meta, trades = load_paths_ledger("EURUSD")

def my_ratchet_rule(state: TradeState, bar: Bar) -> ExitAction | None:
    if state.mfe_r_so_far >= 1.2:                # activation_R = 1.2
        ratchet_price = (state.entry
                         + state.direction * 0.6 * state.mfe_pips_so_far * PIP)
        return ExitAction(kind="adjust_stop",
                          price=ratchet_price,
                          reason=PRIORITY_E020_RATCHET)
    return None

alts = replay_all(trades, rule=my_ratchet_rule)
# alts is list[AltTradeRecord]; each has .exit_time / .exit_price / .pnl_pips / .r
```

See individual study protocols (`experiments/E02x_*/PROTOCOL.md`) for
per-study rule shapes and arm grids.
