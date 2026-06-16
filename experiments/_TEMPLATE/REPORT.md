# EXXX — Report: <short name>

> Copy this template to `experiments/E0XX_short_name/REPORT.md` when results
> are ready. Fill in every section; if a section does not apply, say so in
> one sentence and keep the heading.

**Date:** YYYY-MM-DD ·
**Protocol:** `PROTOCOL.md` (pre-registered YYYY-MM-DD, commit `<sha>`) ·
**Status:** complete / stopped at stage N / parked.

## Abstract (4 sentences: problem · approach · result · impact)

State the question in plain English first. Then the approach. Then the
headline number with units. Close with what this changes downstream.

## 1. Why this experiment exists

One paragraph in plain English. What did a discretionary trader (or the
agent) observe that motivated this question? What would a "yes" answer
mean? What would "no" mean? No acronyms before the second sentence.

## 2. What we tested

State the hypotheses verbatim from `PROTOCOL.md`:

- **H0:** ...
- **H1:** ...

If the experiment has stages, list them in one short bullet list with
the stop rule named in plain English.

## 3. Method (short version)

Lock the recipe. Three to six bullets, each one sentence.

- Data window and split: ...
- Event or trigger definition: ...
- Outcome metric and horizon: ...
- Controls: ...
- Statistics (test, multiplicity, $n$-gate): ...
- Verdict tiers: ...

Refer the reader to `PROTOCOL.md` for the full text.

### 3.1 Worked example (one concrete instance)

Walk through one specific event or trade end-to-end with real numbers.
"On 2024-03-12 at 09:00 UTC, the agent saw ... the rule fired ... the
outcome over the next $H$ bars was ... ATR(14) at that bar was ..."
This anchor lets every later table point back to one thing the reader
can picture.

## 4. Results

Lead with the headline number, then the table, then the interpretation.

> **Headline:** one sentence with the literal numbers and $p$-values.

### 4.1 Stage-by-stage table

| Stage | Status | Detail |
|---|---|---|
| | | |

### 4.2 Per-cell registry (if applicable)

| cell | $n$ | effect | $p$ | verdict |
|---|---:|---:|---:|---|

Number-first interpretation for each row that matters. One sentence per
row maximum.

### 4.3 Figures

List paths and one-sentence captions. Captions go below figures.

## 5. What this tells us

Three to five numbered points. Each one short. Each one is a *takeaway*,
not a method recap.

1. ...
2. ...
3. ...

## 6. Honest limitations

Bullet list. Lead each item with the limitation itself, not "however".

- ...
- ...

## 7. Conclusion

One short paragraph. State the verdict in the same words the protocol
uses (`alive`, `parked_weak_effect`, `parked_insufficient_n`, `dead`,
`stopped_at_stage_N`). State what changes downstream. State what does
not change.

## 8. References

- Pre-registration: `PROTOCOL.md` (commit `<sha>`).
- Code paths: ...
- Result registries: `output/...` or `results/...`.
- Manifest: `MANIFEST.md`.
- Related experiments by ID: E0XX, E0YY.

---

### Self-check before committing

Run the readability self-check (`brain-box/school/methodology/readability-and-clarity.md`):

- [ ] Abstract opens with intuition, not acronyms.
- [ ] Four of five random sentences are under 30 words.
- [ ] No paragraph has more than three acronyms; all are defined on first use.
- [ ] Every section opens with one sentence stating its scope.
- [ ] Every results paragraph leads with a number with units.
- [ ] Section 3.1 walks through one concrete instance with real numbers.
- [ ] No `§` glyph anywhere in the document.
- [ ] At most one em-dash per sentence.
