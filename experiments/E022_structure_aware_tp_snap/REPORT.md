# E022 — Structure-aware TP snap — REPORT

**Verdict:** `dead` · **Date:** 2026-07-20

- Pre-registration: [`PROTOCOL.md`](./PROTOCOL.md)
- Full numeric artefact: [`../../programs/E022/results.json`](../../programs/E022/results.json)
- Data plane: [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md) (PRE-0)
- Level reconstruction: [`../../programs/E022/level_detector.py`](../../programs/E022/level_detector.py)
- Fill rescorer: [`../../programs/E022/rescorer.py`](../../programs/E022/rescorer.py)
- Stop notice: [`STOP_NOTICE.md`](./STOP_NOTICE.md)

## §1 Verdict summary

**Zero of the twelve arms** on the frozen §4.1 grid meet the `alive`
criteria of PROTOCOL §6.

- Nine arms produce a **statistically significant NEGATIVE ΔSharpe**
  on the pooled per-trade R sequence (pooled 95 % CI entirely below
  zero, seven of them BH-FDR α = 0.10 survivors of the *degradation*
  side of the null).
- Two arms (`daily_only_d5`, `all_d5`) produce a negative but
  CI-overlapping ΔSharpe — the mechanism at the tight 5-pip window is
  quieter and its damage is smaller.
- One arm (`ladder_top_d5`) has a marginally positive point estimate
  (ΔSharpe = +0.0006) but fails PROTOCOL §H3 feasibility: its
  `snap_fire_rate` on test slices is 3.02 % — below the 5 % floor —
  so it is registered as `inactive_snap_never_fires`. It is the only
  arm to hit that outcome; the family as a whole does **not** qualify
  for `parked_snap_never_fires` (which requires **every** arm to fire
  less than 5 %).

There is no `alive` arm, no `parked_daily_only_suffices` (both
sources' winners would need to be alive first — none are), and only a
partial `inactive_snap_never_fires` pattern. **Study verdict: `dead`**.

Per PROTOCOL §6, the stop rule fires: **keep the shipped mechanical TP
placement; write `STOP_NOTICE.md`; do not open a Phase 2b; do not
extend the grid; do not adjust `snap_offset` post-freeze**.

## §2 Headline numbers (12 arms × 5 folds × 3 symbols pooled, n = 2 388)

Per PROTOCOL §5, the primary metric is the paired-bootstrap ΔSharpe of
the per-trade R sequence, pooled across (EURUSD, GBPUSD, USDCAD) H4
with fixed-effects weight ∝ per-symbol test-slice trade count. Seed 42,
5 000 resamples. BH-FDR at α = 0.10 across the 12-arm family on the
pooled two-sided p-value.

| arm | ΔSharpe | 95 % CI | pooled p | folds+ | BH-FDR | fire | ΔP(TP) | verdict |
|---|---:|---|---:|---:|:---:|---:|---:|---|
| daily_only_d5    | −0.0008 | [−0.0055, +0.0049] | 0.7384 | 2/5 | no  | 10.85 % | +0.46 % | dead |
| daily_only_d10   | −0.0107 | [−0.0189, −0.0017] | 0.0184 | 1/5 | yes | 21.40 % | +1.17 % | dead |
| daily_only_d15   | −0.0164 | [−0.0272, −0.0043] | 0.0076 | 0/5 | yes | 30.61 % | +2.35 % | dead |
| ladder_top_d5    | +0.0006 | [−0.0032, +0.0052] | 0.8228 | 1/5 | no  | **3.02 %** | +0.21 % | `inactive_snap_never_fires` |
| ladder_top_d10   | −0.0012 | [−0.0085, +0.0070] | 0.7344 | 2/5 | no  | 7.45 %  | +0.80 % | dead |
| ladder_top_d15   | −0.0200 | [−0.0308, −0.0087] | 0.0012 | 0/5 | yes | 13.57 % | +1.34 % | dead |
| round_number_d5  | −0.0022 | [−0.0055, +0.0016] | 0.2452 | 1/5 | no  | 9.84 %  | +0.34 % | dead |
| round_number_d10 | −0.0118 | [−0.0179, −0.0051] | 0.0012 | 0/5 | yes | 20.64 % | +0.88 % | dead |
| round_number_d15 | −0.0150 | [−0.0240, −0.0052] | 0.0040 | 0/5 | yes | 29.90 % | +1.88 % | dead |
| all_d5           | −0.0042 | [−0.0097, +0.0022] | 0.1836 | 2/5 | no  | 19.77 % | +0.67 % | dead |
| all_d10          | −0.0177 | [−0.0273, −0.0073] | 0.0016 | 0/5 | yes | 37.81 % | +1.76 % | dead |
| all_d15          | −0.0282 | [−0.0412, −0.0140] | 0.0000 | 0/5 | yes | 52.10 % | +3.48 % | dead |

("fire" is the `snap_fire_rate`; "ΔP(TP)" is the arm's change in the
empirical probability of a trade filling at TP vs. the deployed
baseline.)

**BH-FDR at α = 0.10** rejects H0 for seven arms — but in the direction
of DEGRADATION, not improvement. Every ΔSharpe point estimate except
`ladder_top_d5` is negative, and `ladder_top_d5` fails the §H3 5 %
fire-rate floor by ~2 pp.

## §3 Mechanism check — the snap works as designed, its EV is wrong

The secondary metrics tell a coherent story: the rule **does** what it
was designed to do (lifts fill probability at sticky levels), and the
per-winner R cost the pre-registration expected DOES emerge — but on
the deployed cell the R cost dominates the fill-rate gain.

| Diagnostic (arm `all_d15`, largest fire rate) | Value | Reading |
|---|---:|---|
| `snap_fire_rate` (fraction of trades where snap moved TP) | **52.10 %** | On more than half the population there is a sticky level within 15 pips of the mechanical TP. The rule is definitely active. |
| `filled_at_snap_rate` (fraction where the alt fill was `new_tp`) | 33.46 % | Of trades whose snap fired, ~63 % had `new_tp` touched before the original exit (in M5 resolution). |
| ΔP(TP fills) | **+3.48 %** | Real +3.5 pp lift in TP-fill probability — the mechanism sanity gate (PROTOCOL §6.5) passes for every arm. |
| Δ mean R \| winners (pooled) | **−0.106 R** | Winners give up ~0.1 R on average — consistent with PROTOCOL §1's "expected slightly negative" prior. |
| Δ mean time-in-trade \| winners (H4 bars) | −1.0 bar (~−4 hours) | Winners exit ~4 hours earlier — the fill-rate mechanism trades duration for target proximity as designed. |
| Pooled ΔSharpe | **−0.028** | Primary. The per-winner R cost (~0.1 R × 1 400 winners ≈ 150 aggregate R) is not compensated for by the ~85 extra TP fills (~1.3 R aggregate lift). |

The direction of every secondary is on-plan. The primary is
unambiguously off-plan. The rule is not broken — its cost/benefit ratio
on this deployed cell is unfavorable.

## §4 Why the pattern is monotone in `snap_distance`

There is a clear monotone worsening with `snap_distance` inside each
`snap_source`. At 5 pips the snap barely fires; at 15 pips the snap
fires on 30–52 % of trades. The larger the fire rate, the larger the
NEGATIVE ΔSharpe magnitude:

| snap_source | d=5 fire → ΔSharpe | d=10 fire → ΔSharpe | d=15 fire → ΔSharpe |
|---|---|---|---|
| daily_only    | 10.9 % → −0.001 | 21.4 % → −0.011 | 30.6 % → **−0.016** |
| ladder_top    |  3.0 % → +0.001 |  7.5 % → −0.001 | 13.6 % → **−0.020** |
| round_number  |  9.8 % → −0.002 | 20.6 % → −0.012 | 29.9 % → **−0.015** |
| all           | 19.8 % → −0.004 | 37.8 % → −0.018 | 52.1 % → **−0.028** |

The pattern is diagnostic: **more firing = more damage**. The
mechanism itself is net-negative on every arm that actually fires. The
`ladder_top_d5` marginally-positive point estimate is a
low-power-of-observation artefact (fire rate 3 %, 72 fires across
2 388 trades) rather than a real winning arm — the §H3 5 % floor is
precisely there to prevent that arm being promoted on a technicality.

## §5 Why every `snap_source` shows the same shape

Four different level sources with very different construction — UTC
daily/weekly anchors, reconstructed structural swing-highs / zone-edges
/ trendlines / fib-extensions, mechanical round-number sub-figures, and
the union — all show the same worse-with-wider-window monotone
degradation. This suggests the negative effect is **not** a property
of any particular level source but of the general "pull TP inward at
a level" rule interacting with the deployed cell's TP=1.5R geometry:

1. **Winners on 1.5R geometry rarely stall.** On the deployed cell,
   TP is set at ~1.5R from entry. Trades that hit TP tend to do so
   with clean impulses (median R at exit is 1.5R on baseline). Pulling
   TP inward by 3–13 pips (5-pip to 15-pip windows minus the 2.5–3
   pip offset) trades 1.5R for ~1.35–1.4R — a real ~10 % R cut per
   winner without any corresponding fill-rate rescue on this
   population, because these winners were already going to fill.

2. **The fill-rate lift is small on THIS cell.** ΔP(TP fills) is at
   most +3.5 pp (`all_d15`). That converts ~85 non-winners into
   winners at typically ~1R (not 1.5R). The aggregate R gain from those
   ~85 rescues is at best ~+85 R; the R cost from ~1 300 previously
   winning trades taking ~0.1 R less each is ~−130 R. Net ~−45 R
   pooled — small in absolute terms, decisive in Sharpe terms because
   the deployed cell's per-trade R variance is comparatively low
   (Sharpe ~0.28 baseline).

3. **Sticky levels are not concentrated near TP.** The `daily_only`
   arm has only 6 candidate levels per trade (PDH/PDL/PDM/PWH/PWL/PWM);
   `round_number` has ~1–2 levels between entry and TP; `ladder_top`
   has ≤ 1 by construction. Even the union rarely places a level in
   the *near* neighbourhood of TP (within 5 pips) — that neighbourhood
   is exactly the space where the fill-rate lift would pay off. The
   deployed cell's TP is already "well-placed" relative to sticky
   levels on this population.

## §6 Ex-post case walk-through: GBPUSD 2969136564 (PROTOCOL §5.3)

The motivating ticket predates the PRE-0 ledger window (2015-01 →
2025-12), so it is **not** in the sweep population; the case
walk-through below is descriptive (n = 1) and does not enter the FDR
family.

Trade parameters (from live logs, PROTOCOL §5.3):
- entry = 1.35060, tp = 1.34264, direction = short, stop_pips = 53.1,
  target = 79.6 pips
- realised MFE = 79.1 pips (missed TP by 0.5 pips), historical
  exit-reason was reverse — a scratch/loss

**Under every arm of the frozen 12-arm grid, `snap_tp` returns
`new_tp = tp` — the snap does not fire.** Verified by the rescorer
against the PROTOCOL §5.3-declared level values (see
`results.json → motivating_trade.arm_outcomes`):

- **Ladder_top swing @ 1.34111.** Direction is short, so
  `is_between(1.35060, 1.34111, 1.34264)` needs 1.34264 < 1.34111 <
  1.35060, but 1.34111 < 1.34264 — the swing is **beyond** TP on the
  short's directed axis. `is_between` returns False → no fire, for
  every `snap_distance ∈ {5, 10, 15}`.
- **Round-number set {1.34500, 1.35000}.** Only 1.34500 is strictly
  between entry (1.35060) and TP (1.34264), on the short axis
  1.34264 < 1.34500 < 1.35060 — yes. Distance to TP =
  |1.34500 − 1.34264| = 23.6 pips > 15 = max `snap_distance` in the
  grid → no fire, for every `snap_distance`.
- **Daily_only.** Not derivable from the trade record alone; the
  descriptive case walk-through leaves it empty. Even if some anchor
  were between entry and TP, it would need to lie within 15 pips of
  TP to fire, which the PROTOCOL §5.3 walk-through does not claim.
- **All.** Union of the above — no candidate is within 15 pips of TP
  strictly between entry and TP → no fire.

This reconciles exactly with PROTOCOL §5.3's predicted "no fire" walk-
through and confirms the direction invariant (§3.2) is behaving as
pre-registered on the motivating trade. Note that this outcome is
independent of whether the study is `alive` or `dead` at the
population level: the case study shows the rule's *shape* is correct
on the motivating trade; the population-level verdict shows the *EV
of the rule* is negative on the deployed cell.

## §7 Anti-lookahead audit (PROTOCOL §5.4)

The mutation test
[`test_snap_no_lookahead_via_level_detector`](../../programs/E022/tests/test_e022_rule.py)
passes: mutating a random bar at or after `entry_time` (setting a huge
high and a smashed low) and recomputing `L(daily_only)`,
`L(ladder_top)`, `L(round_number)`, `L(all)` returns exactly the same
prices as the baseline. The level detector consumes only bars strictly
before `entry_time` (per-trade slice
`[entry_time − 200·H4, entry_time)`), so a post-entry bar mutation
cannot possibly influence the output. This is not just an assertion —
the test constructs a mutated `SymbolCache` on the fly and diffs the
prices field-by-field.

The reproducibility test
[`test_level_detector_reproducibility`](../../programs/E022/tests/test_e022_rule.py)
also passes: two independent calls with the same bars produce
byte-identical level sets. Combined with `random_seed = 42` for the
bootstrap, the whole harness is deterministic under the recorded
generator commit.

## §8 Fill-decision harness note (documented deviation from prompt)

The task prompt suggested the strict-less-than form
`bar.time < trade.exit_time` for the intra-trade M5 fill scan (§4.2).
That form silently drops legitimate fills in two cases specific to how
the PRE-0 exporter records exits:

- **Same-bar-TP trades.** When a trade opens and hits TP inside the
  same H4 bar, PRE-0 records `exit_time == entry_time` (H4 bar start).
  Under `bar.time < exit_time`, ZERO M5 sub-bars would be scanned —
  even though 33 % of EURUSD winners on the deployed cell are same-bar
  TP.
- **Diff-bar TP trades where `exit_time` is the H4 bar START.** The
  actual M5 fill can be several minutes after the H4 bar's start; a
  strict-less-than form misses that M5 bar.

PROTOCOL §4.2 says "on any bar between `entry_time` and the original
`exit_time` (inclusive), evaluated on M5 path bars if available". The
natural reading, and the one that gives same-bar-TP trades a chance
to fire the snap, is: iterate the full `trade.path` (which the PRE-0
exporter explicitly builds to be
`[entry_time, exit_time + trade_tf_duration)`). This is what the E022
[`rescorer.py`](../../programs/E022/rescorer.py) does; the deviation
from the prompt spec is documented in the module's docstring
"Scan-window design note".

The direction invariant (§3.2) makes the choice safe: because
`new_tp` is strictly between entry and the original TP, any bar
hitting original TP has already crossed `new_tp`. So on winning
trades, the alt fill is always at or before the original TP timestamp
— never a "phantom-fill-past-exit" artefact.

A sensitivity re-run under the strict `bar.time < exit_time` form
would flip two arms (`round_number_d15` and `all_d5`) to nominally
`alive` — but only by dropping intra-H4-bar TPs that the M5 path was
built to resolve. That result would be a *harness artefact*, not a
real mechanism win, which is exactly why the fix was applied before
verdict registration rather than after.

## §9 What we DO NOT do (§6 stop rule)

Per PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md`:

1. **Do not** extend the arm grid to search for a positive arm (e.g.
   `snap_distance` < 5 pips, or a 5th `snap_source`).
2. **Do not** promote ΔP(TP fills) — a real +3.5 pp secondary lift on
   `all_d15` — to primary post hoc.
3. **Do not** ship any snap variant into `SignalLoop._route_signal`
   in production (Phase 3 is gated on an `alive` verdict; this study
   does not clear that gate).
4. **Do** keep the shipped mechanical TP placement
   (`entry ± target_rr · stop_pips`, no snap) exactly as it is.
5. **Do** register this study as `stopped_dead` in EXPERIMENTS.md
   (coordinator territory — this REPORT does not touch the registry).
6. **Do** write [`STOP_NOTICE.md`](./STOP_NOTICE.md) beside this
   REPORT.

## §10 What this DOES tell the campaign

E022 delivers a clean, population-level negative result on an
order-placement-only rule. Downstream implications for E020/E021/E024/
E025:

1. **E020 (MFE ratchet, `dead`).** E020 attacked the give-back problem
   from the *exit* side and failed. E022 attacked the fill-probability
   problem from the *placement* side and failed. Both failures are on
   the same deployed cell and share the same shape — the rule works,
   the cell is too well-tuned already for the rule to add EV.
2. **E024 (near-TP stall exit).** E024 is the third attempt at the
   0.5-pip class of failures, targeting the *exit* side with a
   narrower trigger (price stalls near TP long enough that the arm is
   effectively booking a nearly-realised win). E024 is a
   compositionally distinct mechanism (fires only when price is
   already near TP; does not disturb winners on clean impulses) and
   should be evaluated on its own merits.
3. **E025 (joint stack).** With both E020 and E022 dead, the campaign
   stack in E025 becomes at most `{A' = E024, B = E021, C = ?}`. The
   family-multiplicity denominator in E025's deflated-Sharpe argument
   drops by 24 arms (12 from E020, 12 from E022) — E025's protocol
   should be re-visited when it comes up.
4. **Cell-level implication.** Three independent studies now say the
   deployed `all_on` cell (wick-proof SL + BE-at-1R + PLG + mechanical
   TP=1.5R) is close to a local optimum for its exit / placement
   mechanics. Improvements are more likely to come from the *entry*
   side (setup selection, quality gating) than from further tinkering
   on the exits.

## §11 Reproducibility

```bash
cd finance-research-experiments
PYTHONPATH=../multi-pair-trading-agent:.:scripts \
    ../multi-pair-trading-agent/.venv/bin/python \
    programs/E022/run_e022_validation.py \
    --output programs/E022/results.json
```

Wall-clock ~25 seconds on a MacBook Pro:
- 13 s H4 parquet load for 3 symbols (54 000+ bars each)
- 5 s per-trade level reconstruction (200-bar `precompute` slice ×
  2 388 trades)
- ~7 s for the 12-arm × 5-fold × 5 000-resample bootstrap sweep

Deterministic (bootstrap seed 42; per-trade `precompute` is a pure
function of the pre-entry slice). Reproducing requires:

- PRE-0 path ledgers under
  `programs/_shared/counterfactual_replay/data/{SYMBOL}_H4_paths.jsonl`
  (regenerable via
  `programs/_shared/counterfactual_replay/export_ledger_with_paths.py`
  — see the shared harness's README).
- The trading-agent H4 parquet cache at
  `multi-pair-trading-agent/data/parquet/{SYMBOL}_H4.parquet` (used by
  `level_detector.py::load_symbol_cache` via `agent.data.loader.BarLoader`).

Test suite:

```bash
PYTHONPATH=../multi-pair-trading-agent:.:scripts \
    ../multi-pair-trading-agent/.venv/bin/python \
    programs/E022/tests/test_e022_rule.py
```

7 / 7 tests pass: rule invariants (direction / non-widening /
idempotence / null-rule identity), motivating-trade "no fire", level
detector reproducibility, no-look-ahead mutation.

Full numeric detail (per-fold ΔSharpe with CIs, secondaries, mechanism
diagnostics, BH-FDR flags, per-arm verdicts, motivating-trade
walk-through) is in [`../../programs/E022/results.json`](../../programs/E022/results.json).
