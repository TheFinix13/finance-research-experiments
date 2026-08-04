# Phase AK-2 — Reo striker mode: do his mirror picks carry expectancy? (pre-registration)

Registered: 2026-08-04, BEFORE execution. Charter: D148 (user
direction: "in the NEL, Reo started to do things without Nagi… if
he's better off as a striker, that's a bonus — if it's provable; two
modes is okay"). Phase AK established Reo's mirror is a quality
throttle on Nagi. AK-2 asks the independent question: if Reo's
mirror THOUGHTS had been executed as TRADES, what expectancy would
they have carried?

## Question class (declared)

DESIGN/mechanism readout on the mined 2019–2023 window — Reo's
mirror selection has never been scored as trades anywhere, but the
underlying window is heavily consumed, so ANY positive readout here
is a candidate signal only. Promotion to a real two-mode charter
requires later confirmation on sealed or live data. No edge claim is
made from this study alone.

## Method

ONE replay (2019-01-01 → 2023-12-31, H4, causal semantics, deployed
roster incl. Reo, `aggregator_arm="phi41"`) with `A5ReoV1.observe`
wrapped to tee every mirror Thought (coordinate != None) to
`mirrors.jsonl`. Then a deterministic counterfactual execution of
each mirror using the LEADER's preserved trade plan
(`leader_rationale.entry/stop/take_profit`, mirror direction):

- Fill: first bar strictly after the mirror timestamp whose range
  touches entry, within 6 bars (Reo's TTL). No fill in 6 bars → no
  trade (recorded as unfilled).
- Exit: walk forward until stop or TP is touched; if BOTH inside one
  bar, count the STOP (conservative). Hard timeout 60 bars → exit at
  that bar's close.
- One virtual position per mirror; no risk caps, no interaction with
  the squad (this measures selection quality, not portfolio fit).
- R = signed (exit−entry)/(entry−stop); pips via standard pip size.

## Readouts (declared before execution)

1. n mirrors, fill rate, n executed.
2. KPI set (win rate, PF, mean R, total R) overall, per symbol, and
   per mirrored leader (`mirroring:<agent_id>` tag).
3. The comparison that decides "is his selection adding anything":
   mirror-trade mean R vs the SAME leaders' actual executed-trade
   mean R in the same window (Phase AF per-agent table). Reo's picks
   beating his leaders' base rate = selection skill; matching it =
   he's a passthrough; below it = his lag/humility costs money.

## Verdict bands (candidate-signal only, no promotion from this study)

- `striker_candidate`: n ≥ 40, PF ≥ 1.15, mean R ≥ +0.05, AND mean R
  exceeds the leaders' pooled mean R by ≥ +0.05. → charter a sealed/
  live confirmation before any roster change.
- `passthrough`: KPIs within ±0.05 mean R of leaders' pooled base.
- `lag_cost`: mean R below leaders' base by > 0.05 → striker mode
  dead; Reo stays filter-only.
- n < 40 executed → `underpowered`, reported, no verdict.

## Outputs

`results/mirrors.jsonl`, `results/striker_kpis.json`, `REPORT.md`.
