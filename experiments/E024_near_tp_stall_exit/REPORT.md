# E024 — Near-TP stall exit (stage 1) — REPORT

**Verdict:** `dead` · **Stage 2:** cancelled per PROTOCOL §6 stop rule · **Date:** 2026-07-20

- Pre-registration: [`PROTOCOL.md`](./PROTOCOL.md)
- Full numeric artefact: [`../../programs/E024/results.json`](../../programs/E024/results.json)
- Data plane: [`../../programs/_shared/counterfactual_replay/SPEC.md`](../../programs/_shared/counterfactual_replay/SPEC.md) (PRE-0)
- Stop notice: [`STOP_NOTICE.md`](./STOP_NOTICE.md)

## §1 Verdict summary

Zero of the **24 stage-1 arms × 3 symbols = 72 (arm, symbol) cells** meet
the `alive` criteria of PROTOCOL §6. All 72 cells produce a **negative
pooled ΔSharpe with the 95 % bootstrap CI upper bound below zero**;
BH-FDR at α = 0.10 (applied per-symbol across the 24-arm family per
PROTOCOL §5.4) rejects H0 in the direction of *degradation* for the
overwhelming majority of arms — the stall detector significantly hurts
per-trade R-Sharpe on this trade population.

**Verdict counts** (per symbol × per verdict):

| Symbol | `alive` | `parked_low_yield` | `parked_false_positive_heavy` | `dead` |
|---|---:|---:|---:|---:|
| EURUSD | 0 | 0 | 0 | 24 |
| GBPUSD | 0 | 0 | 0 | 24 |
| USDCAD | 0 | 0 | 0 | 24 |
| **Study** | **0** | **0** | **0** | **72** |

The stop rule from PROTOCOL §6 fires: **keep the deployed 1.5R fixed TP
without a stall overlay; write `STOP_NOTICE.md`; do not run stage 2; do
not extend the 24-arm grid; do not promote any secondary metric to
primary post hoc.**

Note the important detail on `parked_false_positive_heavy`: PROTOCOL §6
defines this label only for arms that would *otherwise* satisfy the
`alive` gate (CI-LB > 0 AND ≥ 4/5 folds positive AND joint Stouffer
p < 0.05 AND BH-FDR reject) but whose Δ P(false positive) > 0.5. **No
arm reaches the "otherwise alive" bar,** so no arm can be
`parked_false_positive_heavy`. The false-positive story is real and
substantial (§4), but under the pre-registered label semantics it is
subsumed under `dead`.

## §2 Headline numbers — per-symbol pooled ΔSharpe (n_symbol × 24 arms)

Baseline pooled Sharpe per symbol (null-rule, matches E020 baseline):

| Symbol | n_trades | Sharpe_base | tail_base (worst 10 %) |
|---|---:|---:|---:|
| EURUSD | 737 | 0.287 | −2.00 |
| GBPUSD | 944 | 0.265 | −2.00 |
| USDCAD | 707 | 0.281 | −1.89 |

Per-symbol ΔSharpe **range across the 24-arm grid**:

| Symbol | best ΔSharpe (least negative) | worst ΔSharpe | range width |
|---|---:|---:|---:|
| EURUSD | −0.0852 (`a1.30_S5_any_of_1-4_s3600`) | −0.0936 (`a1.40_S2_h1_range`) | 0.008 |
| GBPUSD | −0.0839 (`a1.30_S2_h1_range`) | −0.0948 (`a1.30_S1_wallclock_s900`) | 0.011 |
| USDCAD | −0.1327 (`a1.30_S5_any_of_1-4_s3600`) | −0.1448 (`a1.45_S4_bar_stall_h1`) | 0.012 |

The Δ Sharpe cost is **remarkably uniform across the grid** — every arm
lands in a ~0.01-wide band below zero. As with E020, this is a
diagnostic: the mechanism's fundamental interaction with the deployed
cell is the problem, not the specific `activation_R`, `stall_secs`, or
`signal` family. USDCAD is uniformly ~0.05 worse than EURUSD/GBPUSD
because USDCAD's path resolution is 100 % H4 fallback (SPEC §1
amended), which makes the stall detector coarser and more prone to
firing before intra-H4 recovery — see §5.

Selected representative arms (full detail in
[`results.json`](../../programs/E024/results.json)):

| arm | EURUSD ΔSharpe (CI) | GBPUSD ΔSharpe (CI) | USDCAD ΔSharpe (CI) |
|---|---|---|---|
| `a1.30_S1_wallclock_s3600` | −0.086 [−0.140, −0.036] | −0.090 [−0.140, −0.042] | −0.141 [−0.200, −0.085] |
| `a1.40_S1_wallclock_s3600` | −0.091 [−0.144, −0.042] | −0.091 [−0.141, −0.043] | −0.144 [−0.202, −0.089] |
| `a1.45_S1_wallclock_s3600` **(anchor)** | −0.092 [−0.146, −0.043] | −0.090 [−0.140, −0.043] | −0.144 [−0.203, −0.089] |
| `a1.45_S4_bar_stall_h1` | −0.092 [−0.145, −0.043] | −0.088 [−0.138, −0.041] | −0.145 [−0.203, −0.090] |
| `a1.45_S5_any_of_1-4_s3600` | −0.092 [−0.146, −0.043] | −0.089 [−0.139, −0.042] | −0.137 [−0.196, −0.082] |

## §3 Fire-rate table

Fraction of trades where the arm actually caused an exit (i.e. the
alt-exit `exit_reason` was `e024_stall_exit`, ties with hard SL
excluded). Baseline never fires, so this equals Δ P(fire).

| signal ↓ / activation_R → | 1.30 | 1.40 | 1.45 |
|---|:---:|:---:|:---:|
| S1_wallclock s=900   | E .217 / G .177 / U .061 | E .113 / G .100 / U .034 | E .060 / G .058 / U .020 |
| S1_wallclock s=1800  | E .168 / G .141 / U .061 | E .079 / G .073 / U .034 | E .039 / G .039 / U .020 |
| S1_wallclock s=3600  | E .128 / G .117 / U .061 | E .060 / G .060 / U .034 | E .029 / G .030 / U .020 |
| S1_wallclock s=14400 | E .069 / G .072 / U .061 | E .030 / G .035 / U .034 | E .014 / G .017 / U .020 |
| S2_h1_range          | E .091 / G .052 / U .023 | E .048 / G .033 / U .020 | E .027 / G .017 / U .017 |
| S3_h1_reversal       | E .094 / G .106 / U .102 | E .050 / G .068 / U .072 | E .026 / G .042 / U .059 |
| S4_bar_stall_h1      | E .073 / G .059 / U .038 | E .034 / G .031 / U .023 | E .016 / G .014 / U .014 |
| S5_any_of_1-4        | E .145 / G .138 / U .113 | E .077 / G .089 / U .076 | E .045 / G .057 / U .065 |

E = EURUSD, G = GBPUSD, U = USDCAD. Fire rates fall monotonically with
higher `activation_R` (stricter arming) and with longer S1 `stall_secs`
(more patient timer). S3_h1_reversal has the highest fire rate at
`a=1.45` because a single sub-3-pip H1 close is a low-bar event; S1 with
`s=14400` (4 h) has the lowest rate — activation must persist for a
full H4 bar before triggering.

## §4 Δ P(false positive) — the mechanism

**Δ P(false positive)** (§5.3 secondary #6): fraction of arm-fires
whose baseline `exit_reason == "tp"`. This is the rate at which the
arm eats a clean take-profit that the deployed cell would have booked.

**Every arm on every symbol exceeds 60 % false-positive rate. Most
exceed 75 %.**

| signal ↓ / activation_R → | 1.30 | 1.40 | 1.45 |
|---|:---:|:---:|:---:|
| S1_wallclock s=900   | E .838 / G .826 / U .698 | E .892 / G .840 / U .708 | E .909 / G .873 / U .714 |
| S1_wallclock s=1800  | E .790 / G .789 / U .698 | E .845 / G .797 / U .708 | E .862 / G .838 / U .714 |
| S1_wallclock s=3600  | E .745 / G .754 / U .698 | E .795 / G .772 / U .708 | E .809 / G .786 / U .714 |
| S1_wallclock s=14400 | E .667 / G .676 / U .698 | E .727 / G .697 / U .708 | E .700 / G .688 / U .714 |
| S2_h1_range          | E .761 / G .735 / U .750 | E .886 / G .806 / U .857 | E .900 / G .812 / U .833 |
| S3_h1_reversal       | E .696 / G .780 / U .833 | E .784 / G .828 / U .863 | E .842 / G .875 / U .881 |
| S4_bar_stall_h1      | E .685 / G .696 / U .630 | E .760 / G .724 / U .688 | E .750 / G .692 / U .700 |
| S5_any_of_1-4        | E .766 / G .792 / U .825 | E .842 / G .845 / U .852 | E .879 / G .889 / U .891 |

**Every single cell in this table exceeds the 50 % `parked_false_positive_heavy`
threshold from PROTOCOL §6 (H3).** If any arm had satisfied the `alive`
criteria on ΔSharpe, it would have been auto-downgraded to
`parked_false_positive_heavy`. As it happens, no arm reached that gate,
so all 72 cells resolve to `dead` — but the FP table is the primary
mechanism story regardless of the label.

Higher `activation_R` (later arm) makes the FP problem WORSE, not
better — at `activation_R = 1.45`, S1 fires far less often but nearly
every fire is on a trade that would have TP'd anyway. This is
consistent with the population geometry: **among near-miss trades
(mfe_r ≥ 1.45), clean-TP outcomes outnumber give-backs by ~44:1**
(§5.5) — so any trigger that fires in the near-miss zone is
overwhelmingly likely to fire on an eventual TP.

## §5 Mechanism finding — what the detector did to the R distribution

The stall detector's effect on the per-trade R distribution is
consistent across every arm:

- **Left-tail improvement.** Tail-mean R (worst 10 %) moves from
  −2.00 (EURUSD/GBPUSD baseline) or −1.89 (USDCAD baseline) to a hard
  ceiling of ≈ **−1.00 R** on every arm. This is because when the
  detector fires, it closes at market at MFE — even a firing on a
  trade that would have hit SL still books a positive R (activation ≥
  1.30R − round-trip cost ≈ +1.0 R at close-at-market on the firing
  bar). The tail cap is real.
- **Right-tail destruction.** Δ mean R on the near-miss cohort
  (`mfe_r ≥ activation_R`) is uniformly negative in the range
  **−0.43 to −0.55 R**. For the anchor arm on GBPUSD, the near-miss
  cohort's mean R goes from **+1.357 (baseline) to +0.849 (arm)**,
  a −0.508 R hit across 537 trades. That aggregate loss
  (~273 R) dwarfs the tail-cap gain (~15 R saved on the ~30 trades
  the arm actually rescued).
- **Δ P(worse-than-stall-trigger).** Of fires where the arm closed
  the trade at R_stall, the fraction whose baseline path ended
  **worse** than R_stall is only **~25–35 %** across arms. In other
  words, the "how often did the give-back actually happen after the
  arm fired" secondary answers ~30 % — the other ~70 % of fires
  either rode the trade higher (usually to TP) or recovered.

The net picture: the stall detector **swaps a modest per-trade
tail-cap gain for a large per-trade runner-choke loss**. Every arm
gives back more on the win side than it saves on the loss side,
because the near-miss cohort is dominated (~44:1 in the strict
`[1.45, 1.50]` MFE band) by clean-TP outcomes.

This is structurally the same failure mode as E020 ("dead" — MFE
ratchet trailing stop) but with a different geometry: E020 chopped
mid-trade runners by monotonically tightening a stop; E024 chops
near-TP runners by closing at market. Both die on the deployed cell's
1.5R TP because the deployed cell's TP is already close enough to a
near-miss that any "clip early" mechanism cannibalises more TPs than
it saves give-backs.

## §5.5 Worked examples on the motivating GBPUSD trades

**Important scope note.** PROTOCOL §5.5 declares Case A (GBPUSD ticket
**2969136564**, entry 2026-07-17) and Case B (GBPUSD ticket
**2966547972**, entry 2026-07-15) as illustrative n = 1 cases; both
tickets are from **live-agent July 2026**, which is *outside* the
PRE-0 counterfactual window (2015-01-01 → 2025-12-01, per SPEC §2).
Neither trade appears in the PRE-0 GBPUSD ledger, so **neither can be
literally replayed under this study**. The PROTOCOL was pre-registered
in advance of PRE-0's window being confirmed to end at Dec-2025 for
this study slice; the intent (per PROTOCOL §5.5) is descriptive, not
statistical — E017's 2026-07-08 replay set the precedent.

What we do report:

**Case A — the "good miss" (GBPUSD short 2969136564, live-agent
2026-07-17).** Under the anchor arm
`(activation_R = 1.45, S1_wallclock, stall_secs = 3600, exit_action = close_at_market)`
the analytical trace declared in PROTOCOL §5.5 gives:

1. MFE crosses 1.45R (≈ 77.4 pips) Friday UTC → detector arms.
2. MFE peaks 79.1 pips (≈ 1.49R); `mfe_ts` captured.
3. Price stalls; `now − mfe_ts` grows past 3600 s.
4. Rule fires: close at market ≈ 1.34300 → **+76 pips ≈ +1.43R** vs
   the actual open-position unrealised **≈ +0.80R** four days later
   (state.json `last_profit` +$4.26 at 1.34634 = 42.6 pips × $0.10/pip).

In population-level terms, this trade — had it been in the PRE-0 window
— is the **~30 %** case of a fire where R_stall > R_baseline (§4 Δ P
worse-than-stall-trigger ≈ 0.30). On this ticket the arm looks like a
win.

**Case B — the "clean TP" false-positive check (GBPUSD short 2966547972,
live-agent 2026-07-15).** PROTOCOL §5.5 declared branches B1 (rule does
NOT fire, TP preserved) and B2 (rule DOES fire, TP eaten → FP). Since
this ticket is out-of-window we cannot compute the specific branch, but
**we can resolve it at population level for the same anchor arm on
GBPUSD**:

- Anchor arm on GBPUSD: **28 fires** across 944 trades.
- Of those 28 fires: **22 (78.6 %) were on trades whose baseline
  `exit_reason == "tp"`** — the pre-registered "branch B2" outcome.
- Only **6 (21.4 %)** fires landed on give-backs the arm "saved".

The **modal outcome of the anchor arm on GBPUSD is branch B2**: the
rule fires on a trade that would have hit TP anyway. A specific ticket
2966547972 would land in this ~78.6 % majority with high prior
probability, matching the false-positive concern H3 was written to
guard against.

**Confirming the mechanism on PRE-0's in-window analogues** (2015–2025
GBPUSD only, near-miss cohort `mfe_r ∈ [1.45, 1.50]`):

| Outcome | Count | Ratio |
|---|---:|---:|
| Near-miss give-back (`exit_reason` ∈ {`sl_panic`, `sl_close`}) | 12 | 1× |
| Clean-TP (`exit_reason == "tp"`, `mfe_r ≥ 1.45`) | 525 | ≈ 44× |

Clean-TP outcomes outnumber near-miss give-backs ~44:1 in this exact
MFE bucket. This is the population-level reason the anchor arm
posts −0.090 ΔSharpe on GBPUSD despite the motivating case A being
real — the give-back exists, it's just very rare relative to the TPs
the arm chops.

## §6 Path-resolution audit (PROTOCOL §4.1 fidelity flag)

Per-fold, per-symbol path resolution histogram (rows sum to n_fold;
"unassigned" = trades before fold 1's 2017-01-01 start, kept in the
per-symbol pooled analysis but not in any per-fold Sharpe pass):

| Fold | EURUSD | GBPUSD | USDCAD |
|---|---|---|---|
| fold1 (2017-2018) | M5: 163 | M15: 211 | H4: 134 |
| fold2 (2019-2020) | M5: 105 | M15: 167 | H4: 125 |
| fold3 (2021-2022) | M5: 161 | M15: 74; **H4: 101** | H4: 109 |
| fold4 (2023-2024H1) | M5: 75 | **H4: 94** | H4: 83 |
| fold5 (2024H2-2025) | M5: 69 | **H4: 81** | H4: 72 |
| unassigned (2015-2016) | M5: 164 | M15: 216 | H4: 184 |

- **EURUSD** is 100 % M5 across all folds (matches SPEC §1 amended
  paragraph).
- **GBPUSD** is 100 % M15 through 2020 and shifts to majority-H4 for
  fold3 (54 % H4) and 100 % H4 for fold4-5 — this is the SPEC §1
  amended note about GBPUSD's post-2021 M15 cache gap.
- **USDCAD** is 100 % H4 across all folds — the SPEC §1 note about
  "no intraday cache available locally".

**Low-fidelity arms** — H1-based signals (S2, S3, S4, S5) on any H4
path bar degrade to H4-bar granularity per PROTOCOL §4.1 last row
("H4 fallback flagged, not silently dropped"). Per the fidelity flag
we ship in `results.json` (`low_fidelity_flag`), 12/24 arms are flagged
low-fidelity on **GBPUSD** (fold3-5) and **all 12 non-S1 arms** are
flagged low-fidelity on **USDCAD** (all folds). EURUSD carries no
low-fidelity flag on any arm — all H1-based signals are reconstructed
from M5 buckets on EURUSD.

The USDCAD-uniformly-worse ΔSharpe (−0.13 to −0.14 vs −0.08 to −0.09
for EURUSD/GBPUSD) partly reflects this fidelity degradation. But
even the M5-only EURUSD symbol is uniformly negative: the mechanism
issue is **not** primarily a fidelity artefact.

## §7 Method-audit notes

- **Stouffer's Z convention (documented in `results.json`).**
  `z_i = sign(Δ_i) · Φ⁻¹(1 − p_i / 2)`;
  `Z = Σ w_i · z_i / √Σ w_i²`; `w_i = √n_fold`;
  `joint_p = 2 · (1 − Φ(|Z|))`. Fisher's combined χ² p is reported
  as sensitivity for every arm; both agree on rejection direction
  across all 72 (arm, symbol) cells.
- **BH-FDR per-symbol** (PROTOCOL §5.4). Each symbol's 24-arm family
  is corrected independently. On EURUSD 22/24 arms cross BH-FDR
  rejection (in the wrong direction); on GBPUSD 24/24; on USDCAD
  24/24. This means the rejection is in the direction of degradation
  — i.e. every symbol has statistically significant evidence that the
  stall exit is worse than baseline, not better.
- **Fold-positivity distribution.** No arm on any symbol achieves
  even 3/5 folds with positive point estimate. The maximum observed
  is 1/5 folds positive (a handful of arms on EURUSD's fold5). This
  disqualifies the `parked_low_yield` label as defined in PROTOCOL §6
  ("positive point estimate but CI includes 0, OR positive-in-only-
  3-folds"). Zero positive-point-estimate arms exist — `dead` is the
  only remaining label.
- **Frozen seed (42) and 5000 resamples.** Bootstrap deterministic.
  Rerunning reproduces `results.json` byte-for-byte modulo the
  `generated_at` and `generator_commit` timestamps.

## §8 Stage-2 authorisation

**Stage 2 is CANCELLED.** PROTOCOL §5.4 stage-2 gating is deterministic:
"If stage 1 produces **0** such arms [alive], stage 2 is cancelled and
the study stops." Zero of 72 cells reach the alive bar; stage 2 does
not run. No `(activation_R, signal[, stall_secs])` triple is carried
forward to stage 2.

If a single arm on a single symbol had been `alive`, PROTOCOL §6's
per-symbol survival clause would have authorised stage 2 on that
(arm, symbol) — but this scenario did not obtain.

## §9 What this DOES tell the campaign

E024 has given the exit-management campaign a second cheap, honest,
population-level negative result. Downstream implications:

1. **E020 (dead) and E024 (dead) triangulate the same finding on
   different mechanisms.** E020 attacked the "give-back after MFE"
   problem via continuous MFE-tightening (runner-choke pathology).
   E024 attacked it via near-TP failure-to-extend (false-positive
   pathology). Both die on the same deployed-cell geometry: the 1.5R
   TP is close enough to the near-miss zone that any "clip early"
   mechanism cannibalises more clean TPs than it saves give-backs.
2. **The Sharpe cost is uniform across E024's 24-arm frozen grid.**
   As with E020, the near-uniformity across `activation_R`,
   `stall_secs`, and signal families is diagnostic. Grid-fiddling
   after this verdict would be a post-hoc extension of the search
   width — forbidden under PROTOCOL §6 and `PROTOCOL_DISCIPLINE.md`
   §5.
3. **E021 (partial exit at R milestone) and E023 (post-BE structure
   trail) are structurally different.** E021 books a *partial* fill,
   leaving the runner intact — the runner-choke pathology does not
   apply symmetrically. E023 anchors on structure, not on MFE, so the
   near-miss FP pathology does not directly transfer. Both remain
   worth running under fresh pre-registrations.
4. **The user-flagged "good miss" pattern is real but rare.** The
   n = 1 GBPUSD 2969136564 case exists and would (per PROTOCOL §5.5)
   have been rescued by the anchor arm. But at population scale in
   PRE-0's window, similar near-miss give-backs occur ≤ 3 % of the
   time in the `mfe_r ∈ [1.45, 1.50]` band. Even a detector with a
   perfect give-back true-positive rate would need Δ P(FP) below
   ~10 % to move ΔSharpe positive on this cell — and no detector in
   the pre-registered family comes anywhere close.

## §10 Reproducibility

```bash
cd finance-research-experiments
PYTHONPATH=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent:.:scripts \
    /Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python \
    programs/E024/run_e024_validation.py \
    --output programs/E024/results.json
```

Wall-clock ≈ 39 seconds on the same laptop as the E020 run.
Deterministic (bootstrap seed 42, 5000 resamples, frozen 24-arm grid).
Reproducing requires PRE-0 path ledgers under
`programs/_shared/counterfactual_replay/data/` (regenerable via the
exporter — see `programs/_shared/counterfactual_replay/README.md`).

Unit tests for the five stall detectors:

```bash
PYTHONPATH=/Users/the1finix/Documents/GitHub/multi-pair-trading-agent:.:scripts \
    /Users/the1finix/Documents/GitHub/multi-pair-trading-agent/.venv/bin/python \
    -m pytest programs/E024/tests/test_e024_signals.py -v
```

All 6 tests pass (5 signal cases from the deliverables checklist + one
positive-side companion for S4).

Full numeric detail (per-fold ΔSharpe with CIs, per-arm joint Stouffer
+ Fisher p-values, BH-FDR flags, per-arm fire diagnostics, per-arm
sub-signal firing histograms, near-miss cohort metrics, path-resolution
audit, per-arm verdicts) is in
[`programs/E024/results.json`](../../programs/E024/results.json).
