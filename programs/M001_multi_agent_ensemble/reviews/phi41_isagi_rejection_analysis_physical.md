# Phi4 cross-striker rejection analysis -- Isagi v1 rejected proposals

**Run date:** 2026-07-01T15:54:43.237755+00:00

**Window:** 2015-01-01 -> 2025-12-31 on EURUSD + USDCAD H4.

**Companion to:** `reviews/phi4_squad_v1.md`. The squad gate report is the verdict; this doc is the per-rejection diagnostic.

---

## Honest framing (read this first)

This is an **observational counterfactual analysis**, NOT a backtest of an alternative policy. For each Isagi v1 rejected proposal (the proposal would have opened a trade if Isagi were the sole striker, but the squad's per-symbol single-position rule or the aggregator's highest-conviction-wins rule blocked it), we look up what the other strikers thought at the EXACT same tick.

Biases that make this NOT a tradable signal:
- The peer thought was emitted at the same tick; in a counterfactual   policy where the peer's proposal HAD been taken, downstream ticks   would have produced different ledger state -- the rejection set   itself would be different.
- No slippage feedback from the alternative-policy trades.
- Survivor bias on the squad's other proposals (we only observe   what made it to the proposal layer; sub-conviction-floor   thoughts are not counted).
- 'Counterfactual TQS' would require a re-run with the alternative   proposal acted on -- out of scope for the v1 diagnostic.

---

## Bucket distribution


| Bucket | n | % |
|---|---|---|
| Squad would have traded SAME direction | 5657 | 86.1% |
| Squad would have traded OPPOSITE direction | 914 | 13.9% |
| Squad stayed silent | 0 | 0.0% |
| Squad had own setup elsewhere | 0 | 0.0% |
| **Total Isagi rejections analysed** | **6571** | 100% |

---

## What this tells us

- The **same-direction bucket** is the population where the squad COULD HAVE LEARNT from Isagi's reasoning: the other strikers had a coherent read going the same way. Without Isagi, the squad would have taken the trade anyway.
- The **opposite-direction bucket** is the population where the squad COUNTERED Isagi's read. A high count here would argue for a diversity benefit -- Isagi was vetoed by peers.
- The **silent bucket** is where Isagi was alone -- the squad added nothing to the deliberation on that tick.
- The **own-setup-elsewhere bucket** is where Isagi's rejection coincided with the squad allocating attention to a different symbol. Cross-pair drag, in the audit's phrasing.

---

## References

- Squad gate report: `reviews/phi4_squad_v1.md`
- Per-trade JSONL: `reviews/phi3_gate_isagi_v1_trades.jsonl`
- Doctrine: `06-blue-lock-doctrine.md` sec 3.9 (Tier model) + 5 (the opponent)
- Source: this run's `proposals_all.jsonl` + `rejected_proposals.jsonl`

