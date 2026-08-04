# Phase AH report — S3 FOMC statement tone (2026-08-04)

Protocol: `PROTOCOL.md` (registered before fetch/scoring).
Verdict: **dead** — the pre-registered dictionary ΔTone does not
predict post-statement EURUSD drift in-sample; the sealed 2022–2025
window was never opened.

## What ran

All 87 scheduled FOMC statements 2015–2025 fetched from
federalreserve.gov (0 fetch failures; raw HTML archived under
`data/statements/`). Apel–Grimaldi-style hawk/dove dictionary (terms
frozen in PROTOCOL.md), ΔTone = score minus previous statement's
score. Tested on the 2015–2021 IS half (54 statements, 42 usable
after excluding ΔTone = 0).

## Result (in-sample, 1h horizon = gating)

- Sign agreement with the hawkish→EURUSD-down hypothesis: **38.1%**
  (below coin flip; floor was ≥ 58%).
- Spearman ρ(ΔTone, 1h pips): **+0.144** (wrong sign; floor was
  ≤ −0.20), p = 0.36.
- 4h secondary: agreement 35.7%, ρ +0.20, p = 0.20 — same wrong-sign
  shape.

Not alive. If anything the point estimate runs OPPOSITE to the
textbook direction (hawkish shift ↦ EURUSD up within the hour),
consistent with buy-the-rumor/sell-the-fact positioning dominating
the mechanical tone read — but the estimate is not significant, so
no reverse-signal claim is made either.

## Incident disclosure

The first scoring run produced all-zero scores: the article-div
extraction regex truncated at the first nested `</div>`. Because
every score was zero, no outcome information was revealed before the
fix; the fix (score the whole stripped page; Fed boilerplate is
near-constant and cancels in ΔTone) touched HTML parsing only. The
frozen term lists were not edited at any point.

## Consequences for the D141 ladder

- **S4 (live press-conference listening) stays gated and unbuilt.**
  The presser pipeline's premise was that statement-text tone carries
  direction; on this evidence it does not (at least not via
  dictionaries). Building streaming transcription now would be
  engineering ahead of evidence.
- A successor study (Phase AH-2, fresh pre-registration) could test
  LLM-scored tone instead of dictionary counts — dictionaries are the
  weakest instrument in this family and a modern LLM rubric may
  genuinely read policy language better. That is the only S3 revival
  path worth chartering, and it must declare its rubric frozen before
  scoring.
- The Sae v2 critical path now runs through S1 (surprise data) and
  the Phase AG near-miss (large-impulse continuation), which measure
  the MARKET's reaction rather than trying to read the Fed's prose.
