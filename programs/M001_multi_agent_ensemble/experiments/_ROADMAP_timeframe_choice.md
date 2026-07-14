# ROADMAP — per-agent timeframe choice (v2 arc, post-G7-pass)

- **Status:** PLAN ONLY (2026-07-14). No protocol, no compute, no code.
  Registered so the v2 arc has a costed, data-audited slot for the
  user's directive: *agents deciding on the cadence suiting their
  playstyle — M15 for a speedster, D1 for a patient striker.*
- **Slot in the arc:** this is a **v2 architectural upgrade**, gated on
  a G7 v1 checkpoint PASS (doctrine §3.11.5: v1 must be earned on the
  shared H4 schedule first; a timeframe change is a WEAPON/cadence
  change, i.e. a minor-version bump per agent, each with its own
  pre-registered phase). It is explicitly NOT a v1 item and NOT a
  rescue lever for a failing gate — cadence changes confound every
  chemistry criterion (C2/C3 compare same-tick slot behaviour), so
  they only make sense once the v1 chemistry baseline is banked.

## 1. What exists today (data audit, 2026-07-14)

Cache: `multi-pair-trading-agent/data/parquet/` (read-only from this
repo via PYTHONPATH; the lab never writes there).

| Panel | EURUSD | GBPUSD | USDCAD |
|---|---|---|---|
| D1 | ✅ 2014→2026 | ✅ 2014→2026 | ✅ 2014→2026 |
| H4 (home TF today) | ✅ 2014→2026 | ✅ 2014→2026 | ✅ 2014→2026 |
| H1 | ✅ 2015→2026-06 | ⚠️ 2015→**2021-12 only** | ❌ absent |
| M15 | ✅ 2015→2026-05 (284k bars) | ⚠️ 2015→**2021-12 only** (174k) | ❌ absent |
| M5 | ✅ EURUSD only | ❌ | ❌ |

**Gaps to close before any M15/H1 phase can cover the G7 OOS panel
(2019–2025, 7 rolling windows):**

1. GBPUSD M15 + H1 extensions 2022→2025 (Dukascopy fetch; the sim
   already has `test_dukascopy_fetch.py` / prep tooling patterns).
2. USDCAD M15 + H1 full history 2015→2025 (new fetch).
3. A `DATA_LEDGER.md` row per new panel (source, span, gap policy)
   BEFORE first analytical use — standing lab rule.

Rough sizes: M15 ≈ 25k bars/pair/year → ~275k bars per pair for
2015–2025; H1 a quarter of that. Storage is trivial; fetch time and
gap-audit are the real cost (~an evening per pair including checks).

## 2. What a per-agent timeframe phase looks like (when its turn comes)

One agent at a time, one pre-registered phase each (same discipline as
Phase Y/Z/AA/AB — protocol committed before results, single OOS
evaluation, stop-on-fail):

1. **Candidate declaration from canon, not from search.** The phase
   protocol names ONE target cadence per agent, doctrine-derived
   (e.g. Chigiri `speed_momentum` → M15 ignition scan with H4
   confirmation; Barou `solo_king` → D1 patience with H4 execution;
   Isagi/Bachira zone family stays H4). No cadence grid-search — a
   grid over TFs × agents is a multiplicity bomb.
2. **Harness prerequisite (the actual engineering):** today the squad
   driver walks ONE H4 tick stream and every agent observes/intends on
   the same barrier; C2/C3/LOO and the slot mutex are defined on that
   shared tick. Mixed cadences need a multi-rate tick scheduler
   (M15 sub-ticks between H4 barriers, D1 super-ticks), a look-ahead
   guard per rate, and a re-statement of "same-tick slot contention"
   for cross-rate proposals. This is a sim/core change with its own
   tests, shipped BEFORE any agent phase, evaluated for neutrality
   (an all-H4 squad replayed through the new scheduler must reproduce
   the sealed caches byte-for-byte).
3. **Per-phase evaluation:** the agent's own C1 (on its new cadence)
   plus the full squad chemistry battery at the H4 anchor (C2/C3 vs
   peers unchanged), both aggregator arms, one OOS pass, tagged.
   Success criteria locked per phase; a cadence change that helps the
   agent but dirties a peer's C3 fails.
4. **Versioning:** each adopted cadence bumps the agent's minor
   version (doctrine §3.11.5) and updates the roster + doctrine
   annotations.

Suggested order (later date may revise): Chigiri (M15 is his canon
home per roster §3.4 — v1 shipped H4 only to align with the squad
schedule), then Nagi (finisher may want faster confirmation ticks),
then Barou (D1 patience). Zone family (Isagi/Bachira/Rin) last or
never — their locked cells are H4-native.

## 3. Preconditions checklist (all must be true before phase 1)

- [ ] G7 v1 checkpoint gate PASS banked (squad verdict, §11.x).
- [ ] GBPUSD M15/H1 2022–2025 + USDCAD M15/H1 2015–2025 fetched,
      gap-audited, DATA_LEDGER rows added.
- [ ] Multi-rate tick scheduler shipped + byte-identical H4 replay
      proof committed.
- [ ] Per-agent phase protocol pre-registered (one agent, one cadence,
      locked criteria) and committed before compute.

*This file is a roadmap, not a registration: nothing here consumes an
OOS look, and none of it constrains the G7 third-attempt campaign.*
