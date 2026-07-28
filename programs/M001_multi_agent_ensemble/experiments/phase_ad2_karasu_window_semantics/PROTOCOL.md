# Phase AD.2 — Karasu window anchor semantics (pre-registration DRAFT)

- **Registered:** 2026-07-28 (DRAFT — untracked working-tree file,
  standard M001 WIP pattern; commits wait for that session's declared
  research-repo branch). Parent study: Phase AD (news-defender,
  `phase_ad_karasu_news_defender/PROTOCOL.md`).
- **Program:** M001 multi-agent ensemble.
- **Authorization:** user 2026-07-28 ("proceed and start the
  research"), via trading-agent intake I020. Filed from the
  2026-07-28 weekly v2 review session in `multi-pair-trading-agent`.
- **Lever slot:** none yet — this is a **measurement/semantics
  study**, not a new lever. Stage 2, if reached, is a counterfactual
  re-scoring of an existing ledger, consuming no fresh OOS touch.

---

## 1. Problem (banked evidence)

`SquadEngine.on_bar` calls
`karasu.warning_active_at(as_of=bar.time, symbol)` where `bar.time`
is the H4 bar's **open** label (confirmed 2026-07-28 during the
trading-agent I018 grid investigation: live tape stamps 07:00 /
19:00 UTC are opens on the 03/07/11/15/19/23 grid; closes are
open + 4 h). The engine actually runs at bar close, and entries
execute after that. Karasu's ±15-min window therefore protects a
wall-clock moment ~4 h in the past at decision time.

**Concrete instance (live tape, 2026-07-24):** advisory "French
Flash Manufacturing PMI in +15 min" fired on the 07:00-open bar.
Relative to the open label the 07:15 UTC release was imminent;
relative to the real decision moment (~11:00 UTC) it was ~3 h 45 m
old. Symmetrically, a release at 11:10 UTC — 10 minutes before a
real entry — sits "4 h 10 m away" from the open label and is NOT
protected today.

**Candidate semantics:**

- **A (current / status quo):** `as_of` = bar-open label.
- **B (entry-anchored):** `as_of` = bar close (open + 4 h) — the
  moment the proposal is admitted and would enter.
- **C (forward window):** protect the upcoming holding window:
  entry moment plus a look-ahead horizon H (candidate H = 4 h, one
  holding bar). Superset of B.

**Prior FOR changing to B/C:** the stated purpose of R7 is to keep
strikers out of scheduled-release chop *around their entries*; A
demonstrably misses releases adjacent to the true entry moment.
**Prior AGAINST:** Phase AD's panel was run (and its AD1–AD3
verdict earned) under A; the ±15-min knob may be implicitly
compensating (a ±15-min window at open catches releases *inside*
the just-closed bar's first minutes, which correlate with elevated
close-time volatility). Semantics A may also be doing accidental
good work as a "the bar I'm reading contained a print, distrust it"
filter. This is why it's a study, not a bug fix.

## 1b. Pre-run amendment (2026-07-28, BEFORE any Stage 1 execution)

Recorded before the audit script was written or run. Three deviations
from the draft's assumed inputs, forced by what actually exists:

1. **Fixture substitution.** Phase AD §7 planned a full ForexFactory
   weekly snapshot; that artifact was never created (Phase AD's
   research harness never ran — the trading-agent implementation
   shipped, but no R7 walk-forward panel was executed). The only
   frozen calendar artifact is
   `data/news_calendar_frozen_2026-07-24.json` (Phase AE fixture:
   349 high-impact USD events, NFP/CPI/FOMC only, 2015–2025, primary
   sources). Stage 1 runs on it. Consequences, banked honestly:
   scope is high-impact USD only, so the ladder degenerates to
   block-vs-none (no Medium/SCALE outcomes), and measured
   disagreement is a LOWER BOUND on full-calendar disagreement
   (~2.7 events/month here vs the 4–8/month FF-High prior, before
   counting Medium).
2. **Panel substrate.** "The panel ledger" = the G7 §11.17 phi41
   physical panel artifacts
   (`reviews/phi41_squad_v1_physical_{proposals_all,trades}.jsonl`;
   EURUSD/GBPUSD/USDCAD, 2015-02..2025-12, 5,236 admitted trades).
   This ledger is R7-naive (R7 never ran on it), which is exactly
   what S2 needs: it counts how many actually-admitted entries WOULD
   have been gated differently under A vs B.
3. **Grid.** The sim panel runs the midnight-anchored H4 grid
   (00/04/…/20 UTC; verified from trade entry hours). Confirmed
   mechanic: proposal `timestamp` = bar OPEN label, `entry_time` =
   open + 4 h (the close). So A anchors at `entry_time − 4 h`, B at
   `entry_time`. The live tape's 03/07/…/23 grid differs; Stage 1
   conclusions are grid-specific and this is noted in §6.
   Evaluation points for S1 = every H4 open label in the panel
   window, weekends excluded, × 3 panel symbols (all USD pairs, so
   USD events are relevant to every panel symbol).

## 2. Stage 1 — descriptive disagreement audit (cheap, decisive gate)

On the frozen calendar fixture (Phase AD §7 artifact) crossed with
the G7 §11.17 panel's evaluation timestamps (every H4 close, every
panel symbol):

- Compute the R7 ladder outcome (none / scale / block) under A, B,
  and C at every (symbol, close) point.
- **Metric S1: disagreement rate** = share of (symbol, close)
  points where A and B produce different ladder outcomes.
- **Metric S2: gated-trade overlap** = among the panel ledger's
  actual admitted proposals, the count whose admission decision
  would flip under B (and separately under C).

**Gate (locked):** if S1 < 1 % of evaluation points AND S2 = 0
flipped admissions, the question is moot at panel scale — record a
NULL verdict, close I020 with "no material divergence", stop.
Otherwise proceed to Stage 2.

## 3. Stage 2 — counterfactual replay (only if Stage 1 gate opens)

Re-score the existing Phase AD panel ledger with R7 decisions
recomputed under semantics B (and C as an audit column): identical
bars, identical proposals, identical seeds — only the admission
gate's `as_of` changes. This is ledger re-scoring, not a fresh
walk-forward, so it consumes no new OOS budget; but its verdict can
only *recommend* a semantics change, which would then need its own
Phase AD.3 pre-reg + fresh OOS touch before landing in the live
path.

**Success criteria (locked):**

- **AD2.1 (primary):** panel-wide worst-window drawdown under B is
  **≤** drawdown under A (B never worse), AND B removes at least
  one A-missed release-adjacent losing entry OR avoids at least one
  A-caused needless gating of a winning entry.
- **AD2.2 (no alpha cost):** anchor strikers' (Isagi, Bachira,
  Barou) mean TQS delta under B is **≥ −0.02** vs A.
- **AD2.3 (advisory sanity):** advisory publish rate under B stays
  ≥ 10/month (Phase AD's AD3 floor) — anchor change must not
  silence Karasu.

**Verdict:** RECOMMEND-B iff AD2.1 AND AD2.2 AND AD2.3; else
KEEP-A (with the failing criteria named). C is reported as an audit
column only in this phase; promoting C is a separate pre-reg.

## 4. Stop rules / anti-leakage

1. One Stage-2 evaluation. No tuning of the ±15-min width, ladder
   knobs, or look-ahead H against the same ledger — any such retune
   is a fresh pre-reg (Phase AD.3).
2. The live trading-agent path stays on semantics A until a
   RECOMMEND-B verdict is ratified by the user AND a Phase AD.3
   OOS confirmation passes. No silent live-path anchor change.
3. Stage 1 is purely descriptive and may not be re-run with
   modified gates after seeing results.

## 5. Artifacts

- Stage 1 audit table + Stage 2 (if run) re-scored ledger diff:
  `programs/M001_multi_agent_ensemble/reviews/phase_ad2_verdict.md`.
- Trading-agent linkage: intake I020, decision D130
  (`multi-pair-trading-agent/company/`).
- EXPERIMENTS.md + ai_context.md rows on completion.

## 6. Known limitations

- The frozen fixture lacks `actual` release values, so "the event
  was a non-event" audits (Phase AD's AD4) remain out of scope.
- H4-only: on lower timeframes the open-vs-close gap shrinks and A
  vs B may converge; conclusions here are H4-panel-specific.
- Stage 2 re-scoring assumes proposal generation is independent of
  R7 (true today: Karasu never proposes, R7 acts only at
  admission), so flipping admissions does not alter the upstream
  proposal stream.
