# News calendar archive — local cache

**Status (2026-07-01):** `DEFERRED-BEYOND-G7`. This skeleton (README +
`.gitignore`) was scaffolded 2026-07-01 as the first sub-task of the
news-calendar wiring workstream (Phase 5/7 of the 2026-06-30 sprint plan).
Later the same day the user re-scoped priorities: the v1/v2 reframe
per `06-blue-lock-doctrine.md` v0.5 §3.11.5 makes squad-chemistry
(F19/F20/F21 + G7 v1-checkpoint gate) the current blocker, not news
regime tagging. This folder therefore stays as **intent documentation
only** — no fetch scripts, no data — until G7 clears. Once the squad is
at v1, the fetch harness described below lands as `Phase X` in a
subsequent session. Preserved rather than deleted per
`07-research-standards.md` §3 (nothing is deleted from history).

**Format:** Parquet (snappy compression), partitioned by year and currency.

**Provenance:** External economic-calendar sources. Layout + fetch policy
pre-registered in [`../../specs/news_calendar_wiring.md`](../../specs/news_calendar_wiring.md)
(and the decision-tree companion, `news_calendar_wiring_DECISION_TREE.md`).

## Data-commit policy (D-Q4)

The data files are **not** committed to git. Only the fetch scripts +
`_manifest.json` files are. Each user / CI runner re-derives the local
cache from the source themselves via:

```bash
python programs/M001_multi_agent_ensemble/scripts/backfill_news_calendar.py \
    --start 2010-01-01 --end 2026-01-01 \
    --currencies USD,EUR,GBP,JPY,CAD,AUD,NZD,CHF \
    --sources DK,FF,FRED \
    --out programs/M001_multi_agent_ensemble/data/news_calendar/
```

**Why not commit the data:**

- Primary source (Dukascopy) TOS permits local caching but restricts
  redistribution.
- Fallback source (ForexFactory community archive) is TOS-grey; local
  caching only.
- FRED is public-domain but our archive mixes FRED with DK/FF, so the
  aggregate cannot be redistributed cleanly.
- Manifest + script + tests are sufficient for reproducibility (each
  reproducer runs the fetch under their own TOS acceptance).

## Folder layout

```text
data/news_calendar/
├── DK/                          # Dukascopy freeserv JSON (PRIMARY, D-Q1)
│   ├── _manifest.json           # SHA256 of every parquet + backfill metadata
│   ├── 2010/USD.parquet         # per-year per-currency partitions
│   ├── 2010/EUR.parquet
│   └── ...
├── FF/                          # ForexFactory community archive (FALLBACK, D-Q2)
│   ├── _manifest.json
│   └── <year>/<currency>.parquet
├── FRED/                        # US FRED release dates (CROSS-CHECK, D-Q2)
│   ├── _manifest.json
│   └── <year>/USD.parquet
├── _dedup_audit.parquet         # Discarded duplicates (for repro)
├── _holidays.parquet            # Holiday / Non-Economic entries (FF only)
└── _unified.parquet             # Optional dedup-merged single-file view
```

## Source precedence at load time (§3.3 spec)

Dedup key: `(timestamp ± 60s, currency, normalised(event))`.
Precedence when multiple sources cover the same event: **`DK > FF > FRED`**.

## Cost, D-Q3 answer, D-Q7 answer

- **Cost:** $0/month steady state (all free sources).
- **Backfill window:** default `--start 2010-01-01` (matches production
  parquet cache earliest bar); use `--start 2007-01-01` for the
  historical-research bonus band (adds ~3 years, ~10 MB on disk, known
  2008-2009 value-revision gaps documented in manifest caveats).

## Regenerating the archive locally

```bash
# Primary fetch (Dukascopy, ~1 hour for full 2010-2026)
python programs/M001_multi_agent_ensemble/scripts/backfill_news_calendar.py \
    --sources DK

# Incremental daily update (cron)
python programs/M001_multi_agent_ensemble/scripts/update_news_calendar.py

# Verify with FRED cross-check
python programs/M001_multi_agent_ensemble/scripts/audit_news_calendar.py
```

## Reproducibility manifest

Every source's `_manifest.json` records: source URL, parser version
(git-sha at write time), backfill range, per-file SHA256, total event
count, run count. Manifests are committed; the parquet data is not.

## References

- Spec: [`../../specs/news_calendar_wiring.md`](../../specs/news_calendar_wiring.md)
- Decision tree: [`../../specs/news_calendar_wiring_DECISION_TREE.md`](../../specs/news_calendar_wiring_DECISION_TREE.md)
- Regime redesign motivation: [`../../reviews/regime_redesign_2026-06-24.md`](../../reviews/regime_redesign_2026-06-24.md) §3.2 / §5.6
- Verdict-comparator discipline: [`../../07-research-standards.md`](../../07-research-standards.md) §11
