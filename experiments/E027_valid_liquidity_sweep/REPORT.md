# E027 — Report: valid-liquidity sweep reversal (BOS-qualified)

**Verdict: STOPPED-DEAD at Stage 1 (2026-07-28).** 0 of 4 pre-registered
cells alive; the §6 Stage-1 stop rule fired; Stages 2–3 did not run.

- Pre-registration commit: `cdb7a01` (2026-07-28, `main`)
- Harness + §7 A1 amendment commit: `6722012`
- Stage-1 registry: `output/E027_valid_liquidity_sweep/stage1_EURUSD_screen_2026-07-28_1716.jsonl`
- Stop files: `output/E027_valid_liquidity_sweep/stage{2,3}_E027_stop.json`

---

## 1. What was tested

The externally-sourced rule "a swept swing low is only valid liquidity
if the leg out of it broke the swing high it came from" (mirror for
highs), operationalised as a conditional MFE split *within* the sweep
universe: mean post-sweep directional MFE (ATR units, 20-bar horizon)
of BOS-qualified (valid) vs non-qualified (invalid) sweeps.
Hour-stratified label-shuffle permutation, `n_perm` 5,000, effect floor
+0.10 ATR, BH-FDR α = 0.05 across 4 EURUSD cells (H1/H4 × side),
screen window 2015-01-01 → 2021-12-31.

## 2. Stage-1 registry (EURUSD 2015–2021, seed 27)

| Cell | n | n_valid | n_invalid | valid share | MFE valid | MFE invalid | **diff** | p | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H1 sellside | 1,057 | 415 | 642 | 39.3 % | 2.438 | 2.731 | **−0.293** | 0.799 | dead |
| H1 buyside | 1,119 | 463 | 656 | 41.4 % | 2.443 | 2.733 | **−0.289** | 0.553 | dead |
| H4 sellside | 258 | 122 | 136 | 47.3 % | 2.576 | 3.142 | **−0.566** | 0.958 | dead |
| H4 buyside | 278 | 110 | 168 | 39.6 % | 2.296 | 2.645 | **−0.349** | 0.891 | dead |

All four cells were adequately powered (both classes ≥ 100). The test
was one-sided for valid > invalid; the observed sign is **uniformly
negative** — BOS-qualified sweeps reacted *worse* than non-qualified
ones on every cell, by −0.29 to −0.57 ATR.

Secondary baselines (reported, not gating): vs hour-matched
random-time controls, valid-sweep excess MFE is +0.05 / +0.12 ATR on
H1 and **−0.19 / −0.23 ATR on H4**; invalid-sweep excess is +0.06 to
+0.63 ATR. Neither class shows the E001-style gate-worthy edge, and
whatever excess exists sits in the *invalid* class.

## 3. Interpretation

1. **The folk rule is dead in this operationalisation.** The claimed
   qualification does not enrich post-sweep reactions; it selects the
   weaker half. One plausible mechanism: a "valid" low requires price
   to have already rallied through the origin high and come all the
   way back down to sweep the low — that round trip is itself evidence
   of downward initiative at sweep time, whereas "invalid"
   consolidation lows get swept in flag-like pauses that resolve with
   the bounce the detector hypothesises.
2. This closes **this definition**, not the folk concept (E001 §6
   language). Any different validity formalisation (e.g. the
   immediate-leg variant declared out of scope in §7) needs a new ID.
3. **Production consequences: none to change.** The v1/v2 agents do
   not use sweep logic (E001 eliminated the marginal version; live
   strategy is `zone_d1_against`). Standing consequence: any proposed
   M001 striker or v1 candidate premised on "valid liquidity" is
   blocked by this registry entry.

## 4. Discipline notes

- Both stop files emitted; stopping reported with the same prominence
  as a survivor would have been.
- Data use: EURUSD H1+H4 2015–2021 screen consumed (documented 5th/7th
  uses, see `DATA_LEDGER.md`); confirm and cross-pair slices **not
  consumed** (stopped before Stages 2–3). E010's sealed reservation
  untouched.
- One amendment (§7 A1, network-free loader), committed before any
  statistic was scored.
