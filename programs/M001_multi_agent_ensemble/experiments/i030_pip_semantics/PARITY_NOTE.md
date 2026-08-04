# I030 pip-semantics fix — parity evidence (2026-08-04)

Product-repo commit `2650524` made every pip conversion in the squad
path symbol-aware (tables in `agent/squad/provenance_pips.py`).

## Parity method

`parity_replay.py` ran the deployed full roster (phi41 arm) over
2019-01-01 → 2019-12-31 on EURUSD/GBPUSD/USDCAD twice:

- `results/raw/parity_prefix/` — engine with the fix stashed (pre-fix
  code path).
- `results/raw/parity_postfix/` — engine with the fix applied.

## Result

`trades.jsonl`, `proposals_all.jsonl`, `proposals_rejected.jsonl`,
`events.jsonl` are **byte-identical** across the two runs (cmp -s).
346 trades, 1,839 proposals, 1,969 rejections each.

## The subtlety that made this non-trivial

A first draft converted price→pips by dividing by pip size everywhere.
Float division by 1e-4 differs from the legacy multiplication by 1e4
in the last ulp for ~30% of inputs, which showed up as ulp-level
drift in pnl_pips / conviction fields and a −0.999 vs −1.000
r_multiple change. The shipped fix keeps each call site's LEGACY
operation (sentinel/paper-broker sites multiply by `pips_per_unit_for`;
Rin/Barou stop-pips and the pnl recompute divide by `pip_size_for`)
so major-pair bit patterns are unchanged while JPY/metals/indices get
correct semantics.

Raw tapes retained locally (18 MB, gitignored); this note + the
harness are the committed record.
