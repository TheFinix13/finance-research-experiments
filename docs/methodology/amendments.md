# Methodology: pre-MFE protocol amendments

**Status:** binding template · **Canonical example:** E007 amendment 6.2

## When amendments are allowed

A locked protocol parameter may change **only before** the affected
outcome metric is scored on claim-bearing data, OR the amendment must be
explicitly labelled post-hoc and non-claiming.

## Recipe (E007 amendment 6.2)

1. **Diagnostic touches no outcomes.** Count-only or structural checks
   on screen-split data — never MFE, hit rate, or p-values used for
   claims.
2. **One-shot relaxation.** Smallest parameter change that fixes
   infeasibility (E007: `max_retrace_frac` 0.30 → 0.50 — first value
   crossing n_gate=30 per cell).
3. **Cautionary file preserved.** Original strict run kept alongside
   canonical run (`output/test_b/stage1_*_cautionary.jsonl` pattern).
4. **Unit tests pin strict setting.** Code remains configurable; tests
   keep synthetic fixtures on the tightest pre-reg value.
5. **Commit before amended analysis.** Amendment subsection in
   `PROTOCOL.md` with date, rationale, audit guarantees.
6. **No further sweeps.** If the amended run still fails, report
   `parked_insufficient_n` or stop — do not iterate parameters toward
   significance.

## E006 parallel (v2.1 hour-matched controls)

Same pattern: diagnostic identified confound → amendment pre-MFE on
screen split → uniform-control registry preserved as cautionary record.

Soft caveat: screen data used twice (uniform then hour-matched). Leakage
is small (diagnostic never scored MFE; confirm/sealed untouched) but
disclosed in E006 REPORT.

## Checklist for new experiments

- [ ] Amendment subsection appended under `## Amendments`
- [ ] Dedicated commit before amended run
- [ ] Cautionary artefact path documented in MANIFEST
- [ ] REPORT states which registry is canonical

## References

- E007 protocol §6 (`experiments/E007_impulse_origin_bounce/PROTOCOL.md`)
- E006 protocol amendment v2.1
- [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md) §5
