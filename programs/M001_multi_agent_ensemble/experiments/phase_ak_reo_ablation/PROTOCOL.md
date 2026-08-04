# Phase AK — Reo ablation: does the mirror earn the slot? (pre-registration)

Registered: 2026-08-04, BEFORE the ablation replay executed. Charter:
product I029 resolution (Reo v1 never trades BY DESIGN — his
`intend()` returns None; he exists to lift one peer thought above
Nagi's 0.7 confluence floor) + the roster's own defeat-trigger
("v1 ΔInfo ≤ 0 → Reo is cut"), which has never been measured.

## Question (mechanism, not edge)

H-AK1: removing Reo from the roster collapses Nagi's confluence fire
count. This is a STRUCTURAL/ablation question about an existing
mechanism — it claims no new trading edge, so re-using the seen
2019–2023 in-sample window is legitimate and declared: we are
measuring plumbing on a fixed tape, not selecting a strategy.

## Arms

- **WITH-Reo baseline:** Phase AF `is_cell_30_0.0` raw tape
  (2019-01-01 → 2023-12-31, deployed configs, engine code unchanged
  since — verified no `agent/` commits between AF and AK). Nagi
  baseline: n=27, PF 1.267, mean R +0.222, +142.1 pips.
- **NO-Reo ablation:** ONE replay, identical window/configs/code,
  `reo_mikage` removed from `roster.proposers` after `build_roster()`
  (he has no `prepare()`; nothing else changes).

## Verdict bands (declared before execution; judged on Nagi's n_trades)

| Nagi n without Reo vs 27 | Verdict |
|---|---|
| ≤ 13 (−50% or more) | `reo_essential` — the mirror is load-bearing; keep, scoreboard exemption stands |
| 14–21 (−22% to −50%) | `reo_contributing` — keep, note magnitude |
| 22–32 (±20%) | `reo_inert` — defeat-trigger evidence: the slot is not earning; recommend cut or Reo v2 redesign (trailing-TQS leader tracker per canon) |
| ≥ 33 (+22% or more) | `reo_obstructive` — the mirror is actively crowding Nagi; recommend cut |

Context metrics (reported, not judged): Nagi KPIs, squad KPIs,
proposal counts per agent. Single-replay caveat rides along: AJ-2
registered that thin-n per-cell KPIs are path-sensitive; n-count
bands above are deliberately coarse (±20%) for that reason.

## Outputs

`results/ablation_no_reo.json` + REPORT.md with the verdict and the
roster recommendation (user decides any cut — NEL due process).
