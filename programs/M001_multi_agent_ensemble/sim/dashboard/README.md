# M001 dashboard — Streamlit v0

Read-only observability surface for the M001 ensemble. Panel inventory
and falsification map live in
`programs/M001_multi_agent_ensemble/08-dashboard-spec.md`.

## Run

```bash
PYTHONPATH=../multi-pair-trading-agent:. \
  ../multi-pair-trading-agent/.venv/bin/streamlit run \
  programs/M001_multi_agent_ensemble/sim/dashboard/app.py \
  --server.address 127.0.0.1 --server.port 8501
```

Default port: **8501**. The server binds to `127.0.0.1` per
research-standards §6 (loopback-only at Phi2.5).

Open `http://127.0.0.1:8501` in a browser.

## Panels

Six panels per `08-dashboard-spec.md` §2:

1. **League table** — per-agent TQS / ΔInfo / regime buckets.
2. **Thought feed** — append-only Ledger renderer.
3. **Chemical reactions** — F11 / F13 + thought-resonance trigger graph.
4. **Squad vs human** — Kaiser / Loki / Median / Random / Sae-frozen /
   Sae-composite head-to-head.
5. **Sentinel state** — R1–R5 + external shocks board.
6. **Per-trade explainability** — drill-in over a `trade_id`.

Each panel renders with **placeholder data** if no replay run is
present, so the surface is exercisable end-to-end before the first
real replay lands.

## Data plane

Reads JSONL files from `sim/output/<run>/` directly. The cache key is
`(path, mtime_ns, size_bytes)` per the Phi2.5 append-only assumption
(08 §5). When the SQLite shadow lands at Phi4, only the
`dashboard/data/loader.py` layer changes — the panel code is the same.
