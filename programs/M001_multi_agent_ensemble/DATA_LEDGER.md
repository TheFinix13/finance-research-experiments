# M001 data-consumption ledger — what has been seen, by what, when

Created 2026-08-04 in answer to the user's question: "how sure are you
that the data we are using and the experiments we are performing are
all new, and not just leakages or stale from prior experiments?"

The honest premise: **the underlying price data is NEVER new.** Every
M001 study replays the same banked H4 parquet (EURUSD/GBPUSD/USDCAD,
2015 → present, read-only from the agent repo's cache). Freshness is
a property of WINDOWS and QUESTIONS, not files. This ledger tracks
which windows have been consumed by which selection events, so
"validation" claims can be audited instead of remembered.

## Window-consumption registry (squad/M001 lane, FX H4)

| Window | Event | Study | Date | Consumption level |
|---|---|---|---|---|
| 2015-02→2015-03 | parity slice vs banked proposals | port parity | 2026-07 | fingerprinted (mechanism only) |
| 2019-01→2026-07 | FULL-WINDOW causal A/B (D139 audit) | causality audit | 2026-08-04 | **everything seen once** (unavoidable — the audit had to run on all data); all later studies carry this caveat |
| 2019-01→2023-12 | 8-cell sweep, per-agent argmax selection | Phase AF | 2026-08-04 | heavily mined (tuning window) |
| 2024-01→2026-07 | 3 validation replays (selected cells) | Phase AF | 2026-08-04 | opened 3× |
| 2015-01→2021-12 | 12-arm event study (IS) | Phase AG | 2026-08-04 | mined |
| 2022-01→2025-12 | AG sealed — **NEVER OPENED** | Phase AG | — | **pristine for AG-2** |
| 2011→2023 (FOMC dates) | 87-statement tone test | Phase AH | 2026-08-04 | mined (study dead) |
| 2019-01→2023-12 | 5 away cells | Phase AJ | 2026-08-04 | re-mined |
| 2015-01→2023-12 | 3 Barou cells (subset guard) | Phase AJ-2 | 2026-08-04 | mined; 2015–2018 was first-look for Barou cells, now seen |
| 2024-01→2026-07 | 1 validation replay (Barou:GBPUSD) | Phase AJ-2 | 2026-08-04 | opened again (4th total) |
| 2019-01→2023-12 | Reo ablation (mechanism, no edge claim) | Phase AK | 2026-08-04 | re-used, declared legitimate (plumbing question on fixed tape) |
| AUDUSD/NZDUSD/USDJPY/USDCHF H4 2015→2025 | pitch-assignment widening | Phase AC | 2026-07-20 | fingerprinted ONCE under pre-D138 LOOKAHEAD semantics (results void, but a selection process saw the data); also E005 (v1 lane) touched AUDUSD/NZDUSD. Cleaner than the main three, NOT virgin. |
| XAUUSD/XAGUSD/USOIL/USTEC (any TF) | — | never downloaded | — | **VIRGIN — the only truly unseen offline instruments** |

Also consumed OUTSIDE this lane but on shared data: v1 E0xx studies
(E001–E032) mined EURUSD/GBPUSD/USDCAD H4/H1/M15 extensively;
E029 consumed the sealed EURUSD 2025→2026-05 slice. v1 and M001 use
different signal machinery, so cross-lane leakage is indirect
(regime knowledge, not parameter fitting) — but it is not zero.

## Standing rules derived from this ledger

1. **The 2024-01→2026-07 FX H4 window is EXHAUSTED as a validation
   resource for the squad.** It has been opened 4 times and the D139
   audit saw it in full. Any future "validation pass" on it is
   second-look evidence at best and must say so. New edge claims on
   banked FX H4 need either the AG sealed 2022–2025 event-study
   reservation (event-conditioned questions only) or genuinely new
   data.
2. **Genuinely new evidence, in order of arrival:** (a) the LIVE tape
   accruing daily on the fixed causal runtime — never seen by any
   optimizer, the cleanest data we will ever have; (b) new data TYPES
   (MT5 calendar actual/forecast history — never used anywhere,
   blocked on one VM export); (c) new INSTRUMENTS (XAUUSD/XAGUSD/
   USOIL/USTEC — never downloaded, zero prior mining); (d) mechanism
   ablations (AK-style), which re-use tape legitimately because they
   claim no edge.
3. **Every new protocol must cite this ledger** in its contamination
   note and update the registry row when it opens a window.
4. **Pre-sealed windows (declared 2026-08-04, BEFORE any study
   touches these fields).** For AUDUSD, NZDUSD, USDJPY, USDCHF and
   for any newly banked instrument (XAUUSD/XAGUSD/USOIL/USTEC/FX
   crosses): the window **2023-01-01 → present is SEALED per field**.
   Design/tuning may use pre-2023 data only; each seal may be opened
   exactly ONCE, by a pre-registered protocol, for a single
   validation replay, and the open is recorded here. This is the
   "masking" that actually works — sealing ahead of first contact,
   like AG's 2022–2025 event reservation.
5. Cross-study multiplicity: floors are honest within each study, but
   2026-08-04 alone ran AF/AG/AH/AJ/AJ-2 against overlapping data.
   The more studies that touch a window, the higher the family-wise
   odds that SOMETHING passes by luck — which is why rule 1 exists
   and why live corroboration weeks are mandatory before any
   promotion reaches the pitch.
