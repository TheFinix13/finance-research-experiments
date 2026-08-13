# Phase AO — v1 tape review ("big brother review")

Status: **REGISTERED 2026-08-13** (descriptive/observational program,
weekly cadence; commit hash recorded below once pushed). No review has
been computed at registration time.

Follows `07-research-standards.md` and the squad/isolation doctrine
(`METHODOLOGY_squad_vs_isolation.md`).

---

## §0 What this is (and is deliberately not)

Each week, v1's live trades — losses first, wins too — are replayed as
a question to the squad: *given the same week of bars, what did you
propose on this symbol at this time, and did Sentinel let it
through?* The output is a **corrections ledger**: per v1 trade, what
the squad would have done differently (skipped, opposed, sized/exited
differently), whether that counterfactual would actually have helped,
and what it costs when it wouldn't have.

**Hard doctrine (locked):**

1. **Observation only. No live coupling, ever, under this phase.**
   The squad is shadow-only and ungated (G7 has NO passing verdict);
   letting it veto or modify v1's live orders would wire an
   unvalidated system into the validated one. Phase AO produces
   documents, not signals.
2. **Descriptive, not inferential.** Weekly n is tiny (v1 takes ~2–6
   trades/week). The ledger reports counts and paired deltas with no
   p-values and no claims. If an accumulated pattern ever looks
   actionable (e.g. "Sentinel R1 would have skipped 80 % of v1's
   losses over 12 weeks"), promoting it into either agent requires
   its own pre-registered study (E0xx for v1 changes, a phase gate
   for squad changes). The ledger is hypothesis-generating fuel,
   nothing more.
3. **Symmetric honesty.** Every "the squad would have saved this
   loss" is reported next to "the squad would have forfeited this
   win". The headline number is the NET advice value, not the saves.

## §1 Data plane (all read-only)

| Input | Source | Notes |
|---|---|---|
| v1 trades | `data/journal/live/YYYY-MM-DD.jsonl` day files from the live VM (or the weekly-report bundle) | `trade_entry`/`trade_exit` events joined by ticket; carries conviction, lot, R, MAE/MFE, exit_reason, attribution |
| Squad counterfactual (mode M1, primary) | the squad live-shadow tape for the SAME week: `squad_live/{proposals_all,proposals_rejected,trades}.jsonl` | the squad already ran on the same feed — its tape IS the counterfactual; zero replay compute |
| Squad counterfactual (mode M2, backfill) | a windowed replay via the existing M001 driver (`sim/scoring/run_phi41_gate.py` machinery) writing the same three files | only for weeks predating the live shadow loop or config-changed re-reviews; the replay config (arm, roster, seed window) must be recorded in the ledger header |

Timestamp alignment: v1 entries are intra-bar fills; squad actions are
H4-close-driven. A v1 trade and a squad action match if their H4 bar
opens are within `match_window_bars` (default 1) of each other on the
same symbol.

## §2 Per-trade verdicts (locked vocabulary)

- `agreed_and_filled` — squad shadow-filled the same direction in
  window. Compare outcomes and efficiency: ΔR, hold hours, MFE
  capture (realised R / MFE R), risk taken.
- `agreed_blocked` — a same-direction proposal existed but Sentinel
  or the duel tackled it (rule + verbatim reason recorded). Implied
  advice: *skip*.
- `agreed_unfilled` — same-direction proposal, no fill and no
  recorded block (e.g. lost aggregation silently, slot full).
- `opposed` — squad proposed (or filled) the OPPOSITE direction in
  window; if filled, the opposite trade's R is the counterfactual.
- `no_opinion` — no squad proposal on the symbol in window. Big
  brother saw nothing; explicitly NOT evidence against the trade.

Counterfactual ΔR per trade: for skip-type verdicts
(`agreed_blocked`, `opposed` without fill) Δ = −(v1 R); for
`agreed_and_filled` Δ = squad R − v1 R; for `opposed` with fill
Δ = squad R − v1 R; `no_opinion` and `agreed_unfilled` contribute 0
to advice value (no advice was on tape).

Win-review fields (every v1 win, independent of squad verdict):
hold hours, MFE capture ratio, gave-back R, MAE R — the "efficiency,
speed, lot size" lens; teaching notes are deterministic templates
from recorded fields only (no LLM, no invention).

## §3 Weekly outputs

`results/<window>/corrections_ledger.jsonl` (one row per v1 closed
trade) + `results/<window>/REVIEW.md` (human digest: verdict table,
losses-avoided vs wins-forfeited, NET advice R, per-trade teaching
notes, and a standing "patterns worth a pre-reg" section that may
stay empty for months).

## §4 Stop/kill conditions

- If either tape is incomplete for the window (feed gap, VM outage),
  affected trades are marked `tape_gap` and excluded from advice
  totals — never guessed.
- The phase itself has no pass/fail gate; it is retired if 12
  consecutive weekly reviews produce zero hypothesis-generating
  patterns (recorded honestly as "big brother had nothing to teach").

## §5 Cross-references

- Squad/isolation doctrine: squad-context KPIs do not transfer to
  isolation (Phase AN lesson) — a corrections ledger is squad-context
  evidence and inherits that caveat.
- E033 (research `main`): news-blackout pre-reg — Phase AO ledgers
  double as a live-tape check on its verdict (news-window losses
  should show up as `agreed_blocked` weeks if Karasu R7 is doing its
  job).
- Harness: `tape_review.py` (this directory), stdlib-only, unit
  tests in `test_tape_review.py`.

---

**Registration commit:** _(hash after push)_
