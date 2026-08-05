# Methodology — squad-context vs isolation (binding)

Adopted 2026-08-05 after Phase AN: six of seven survey-nominated cells
that looked strong in **squad-context** surveys (AL/AM) failed the
**isolation** floors. Rin:USDJPY collapsed from survey PF 1.212 to
isolation PF 0.924 (0/5 starts). The gap is not a bug — it is two
different scientific questions.

## The two questions (keep both)

| lens | question | what it measures | when to use |
|---|---|---|---|
| **Isolation** | Does this weapon have positive after-cost expectancy alone? | The agent's signal + geometry + exits, with no peer filtering | Weapon validation, balance patches, field-fit claims, promotion floors |
| **Squad context** | Does this agent earn its roster slot in the deployed ensemble? | Weapon + contests + sentinel slots + Karasu/Kunigami + peer chemistry | Deployment candidacy, NEL HP scoring, "does the team get better with them?" |

**Isolation is the weapon's truth. Squad context is the deployment's truth.**
Neither replaces the other. A cell that only works in squad context is a
*team chemistry* finding, not a *weapon edge* — and must be labelled as such.
A cell that only works in isolation may still fail on the pitch if peers
crowd it out.

## Why surveys inflate (mechanism)

In a full-roster replay the aggregator / sentinel / risk caps reject a
fraction of each agent's proposals. Those rejected fills are often the
toxic tail. Isolation lets the agent fire the whole proposal set, so KPIs
drop when the weapon's unfiltered flow is weak. Phase AN's Rin:USDJPY
case: ~120 extra isolation trades vs the survey were net-negative.

## Binding research rules

1. **Nomination (survey) may stay squad-context** — cheap screen, declared
   exploratory. Report must say `squad_context`.
2. **Chartered follow-up / promotion floors MUST be isolation** for any
   weapon or field-fit claim (AN standard). Multi-start K=5 + honest costs
   still apply per `METHODOLOGY_thin_sample_replays.md`.
3. **Deployment pre-flight MUST include one squad-context replay** of the
   same window (or live/paper tape) after isolation PASS — to check the
   agent is not starved or crowding a proven peer. This is a *slot* check,
   not a re-judgment of the weapon floor.
4. **Do not retune floors to make squad and isolation agree.** If they
   disagree, report both numbers. Prefer changing the player (or the
   roster composition), never the test.
5. **Ablations (AK-style)** stay mechanism studies: they may re-use tape
   and may be squad-context by design (they ask about peer contribution).

## Practical workflow

```
survey (squad, exploratory)
    → nominate cells
isolation multi-start + sealed (weapon claim)
    → PASS?
        YES → squad-context pre-flight + paper/live tape
        NO  → autopsy → one-mechanism patch → new pre-reg (isolation again)
```

## What we will NOT do

- Treat a squad-context PF as proof the weapon is ready.
- Drop isolation because "they play as a team" — teams need players with
  real weapons; chemistry is a second measurement.
- Run endless dual grids on every cell. Isolation first; squad only for
  nominees that already pass isolation (or for explicit chemistry studies).
