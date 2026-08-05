# Context alpha — what squad context actually does to a cell's KPIs

Executed 2026-08-05, read-only mechanism study on consumed tapes
(declared; no selection, no retuning). Case: Rin:USDJPY, the starkest
survey-vs-isolation gap in Phase AN. Script:
`context_alpha_rin_usdjpy.py`; raw `results/context_alpha_rin_usdjpy.json`.

## The question (user's, 2026-08-05)

"Are you saying they need to run in squads to perform better instead
of solo? How do we measure/account for both cases?"

## Decomposition (same window 2015-04 -> 2022-12, same engine, 1x cost)

| slice | n | win% | PF | pips |
|---|---|---|---|---|
| survey (squad context), all | 331 | 32.6 | 1.200 | +1,765 |
| isolation, all | 466 | 29.2 | 0.929 | −1,391 |
| filled in BOTH | 174 | 32.8 | 1.189 | +850 |
| deleted by squad context | 292 | 27.1 | **0.851** | **−2,241** |
| squad-only extras (state divergence) | 157 | 32.5 | 1.211 | +915 |

The squad deleted 292 of Rin's 466 solo trades, and the deleted set
is systematically worse (PF 0.851 vs 1.189 kept; mean R −0.073 vs
+0.117 — roughly a 2-sigma split, suggestive but not conclusive on
this sample). Squad context was not noise: it was a partially
skillful censor of his flow.

## Which mechanism did the censoring

Rin:USDJPY rejections in the survey tape: `open_position_concurrency
_limit` 1,373; contests lost (Isagi 474, Barou 351, Nagi 215,
Chigiri 20) = 1,060; sentinel R1 444. The DOMINANT censor is the
position/slot throttle — signals fired while positions were already
open get dropped. Mechanistic reading: Rin's toxic trades cluster
(he re-fires into chop while a position is already working); the
throttle deletes clustered follow-up entries, which are exactly his
worst subset.

## Standing answers (methodology, adopted)

1. **"Do they perform better in squads?" — No.** The weapon is
   identical; the squad environment censors its trade flow, and on
   this tape the censoring helped. That help is FRAGILE: it depends
   on the current roster (who wins contests, who occupies slots).
   Bench one peer and the "edge" changes. A cell may not claim a
   roster slot on context alpha.
2. **Both measurements stay, with distinct roles.** Isolation = the
   promotion gate (intrinsic weapon expectancy; floors live here).
   Squad context = the deployment forecast (what the live roster
   would actually experience). Every future follow-up study reports
   BOTH, and the gap is named context alpha and attributed by
   mechanism (this script generalizes).
3. **Extract, don't worship, the emergent filter.** When context
   alpha is large and mechanically attributable (as here: the
   concurrency throttle), the fix is a balance patch that moves the
   filter INTO the weapon — e.g. a Rin v1.x self-cooldown /
   one-open-position gate, testable solo under fresh pre-reg. Then
   the agent carries its own discipline to any roster. Registered as
   a FUTURE patch candidate (not chartered today; Rin:USDJPY stays
   closed as judged).
4. No re-judgment of Phase AN: floors were declared on isolation and
   remain so. This study changes interpretation and future design,
   not verdicts.
