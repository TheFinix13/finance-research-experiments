# E019 — Risk-adjusted confidence recovery (redesign of the parked E017)

**Status:** PRE-REGISTERED (DRAFT for approval) 2026-07-14 · **Date to freeze on approval:** _(fill on sign-off)_

> **This is a design document.** No code is built or run under E019 tonight.
> The deliverable is a pre-registration the user can approve in the morning.
> Follow [`PROTOCOL_DISCIPLINE.md`](../../PROTOCOL_DISCIPLINE.md); register in
> [`EXPERIMENTS.md`](../../EXPERIMENTS.md); literature in
> [`../../reviews/refs.bib`](../../reviews/refs.bib).

---

## §0 Why E019 exists — the E017 post-mortem in one paragraph

E017 pre-registered a graduated-confidence cooldown (Arm GC-S) against a
binary kill-switch (Arm HK) and produced an **honest negative**
(`parked_capital_cost`, see [`../E017_confidence_gated_cooldown/STOP_NOTICE.md`](../E017_confidence_gated_cooldown/STOP_NOTICE.md)).
The mechanism did exactly what a risk overlay should: it eliminated the
blind dead time (median 0 h vs 6,500 h) and crushed drawdown (median max DD
**2.5 % vs 16.9 %**). It **failed the pre-registered Pareto gate** on one
leg only — **median terminal equity** — because GC-S spends much of its life
in reduced/shadow mode and therefore forgoes the compounding that the
binary baseline captures when the bootstrapped ledger edge is positive
(~$1,020 flat vs a compounding HK path).

**The central methodological error E019 corrects:** E017's gate scored a
*risk mechanism* on **raw terminal equity**, a *level* metric that
structurally rewards staying maximally deployed and compounding. Under a
positive-edge ledger, a level metric guarantees that any overlay which
trades some upside for drawdown control loses — regardless of how good its
risk profile is. Judging a brake by how fast the car goes is the wrong
yardstick. E019 re-registers the study around **risk-adjusted** success
metrics (return per unit of drawdown / volatility) on which a flat-but-safe
recovery curve can legitimately win, and redesigns the recovery function to
optimise that objective directly.

---

## §1 The baseline has changed since E017 — re-baseline explicitly

E017's HK baseline modelled a `kill.txt` that **persists 48 h until a human
deletes it** (a conservative shrink of the observed 50.9 h / 92.4 h
episodes). **That is no longer production behaviour.** On 2026-07-14 a
daily-DD-halt **self-recovery** landed in `multi-pair-trading-agent`
(pending human review before the live VM): a *clean* daily-DD auto-kill
(reason `Auto-kill: Daily DD halt …`) now **auto-clears at the next UTC day
rollover** — aligned with `RiskManager.on_new_day` resetting `halted_today`
— because the 3 % limit is literally a per-day budget. Manual kills and
non-DD safety halts stay sticky, and a thrash guard escalates to a sticky
halt after **3 consecutive DD-halt days**.

E019's baseline is therefore **AK** (auto-clearing kill), *not* the old
48 h-blind HK. This matters: the shipped fix already captures most of the
raw dead-time reduction E017 attributed to graduated confidence. E019's
value proposition narrows to a sharper, fairer question:

> **Given that a plain kill switch already re-arms at the daily rollover,
> does keeping the agent _live-but-reduced_ (graduated confidence) through
> the halt day and tapering risk back on demonstrated recovery deliver
> materially better _risk-adjusted_ returns than simply going blind until
> midnight?**

Answering that requires a risk-adjusted yardstick (§3) and a recovery
function tuned to it (§4) — the two things E017 lacked.

---

## §2 Hypotheses (operational)

Notation carries over from E017 §3 (per-symbol confidence `c_s ∈ [C_min,1]`,
account gauge `g ∈ [g_min,1]`, effective confidence `κ_s = c_s·g`, real risk
tapered by `κ_s` between `τ_live` and `τ_full`).

- **H0 (null).** Graduated risk-adjusted recovery (Arm **GR-S**) does **not**
  improve on the auto-clearing kill baseline (**AK**) on the pre-registered
  **primary risk-adjusted metric** (§3), across the frozen grid — i.e. the
  extra machinery buys no better return-per-unit-risk than the free daily
  rollover already provides.

- **H1 (alt).** **GR-S** delivers **statistically superior risk-adjusted
  performance** than **AK** — its primary-metric bootstrap CI lower bound
  exceeds AK's point estimate — **while not degrading** worst-path max
  drawdown or empirical risk-of-ruin, robust across both data-generating
  processes and both correlation settings; and on the 2026-07-08 incident
  replay it keeps evaluating/tapering through the halt day without ever
  re-opening risk before the protective close's intent is satisfied.

- **H2 (parsimony).** If **GR-S ≈ GR-T** (time-decay recovery, no shadow
  ledger) on the primary metric, the shadow-recovery machinery earns no
  keep: verdict caps at `parked_shadow_adds_nothing`; prefer the simpler
  time-decay variant or the plain AK baseline.

- **H3 (baseline-sufficiency, new).** If **AK ≈ GR-S** on the primary metric
  AND AK already meets the operational dead-time bar, the shipped auto-clear
  is declared *sufficient* and no graduated overlay ships
  (`parked_baseline_sufficient`). This is a **first-class acceptable
  outcome**: the cheap fix winning is a good result, and E019 must be able
  to conclude it.

---

## §3 Primary metric redesign (the core contribution)

### §3.1 Why terminal equity is the wrong yardstick (formal)

Let an arm produce a return series with mean excess return `μ` and a
drawdown functional `DD(·)`. A risk overlay is, by definition, a map that
lowers `DD` at some cost to `μ`. Ranking arms by terminal equity
`E_T ≈ E_0·exp(Σ r_t)` is monotone in `μ` and **ignores `DD` entirely**;
so under any positive-edge generator the un-overlaid arm wins by
construction (E017's exact failure mode). The decision-relevant question for
a *risk* mechanism is the **trade-off ratio** `μ / DD` (or `μ / σ`), not the
level `μ`. This is the standard rationale for Sharpe- and drawdown-ratio
evaluation of risk-management rules [@chekhlov2005drawdown; @busseti2016kelly].

### §3.2 Pre-registered primary metric

**PRIMARY: CDaR-adjusted return** — annualised (per-horizon) return divided
by **Conditional Drawdown-at-Risk** at β = 0.95:

```
RaC_β = AnnRet / CDaR_β(underwater curve),    β = 0.95
```

CDaR is the mean of the worst `(1−β)` tail of the underwater (peak-to-trough)
curve [@chekhlov2005drawdown]; it penalises *sustained/deep* drawdowns
rather than a one-tick blip, is coherent, and is already the gauge basis in
E017 §3 (G-cdar) — so the study is internally consistent. `RaC_β` is a
return-per-unit-of-tail-drawdown ratio: a flat-but-safe recovery curve with
small denominator can win even with a modest numerator.

**Rationale that this specific choice fixes E017's gate failure.** E017's
gate demanded terminal-equity parity (level). `RaC_β` is scale-free in the
level of `μ`: an arm that gives up, say, 40 % of the numerator but cuts the
denominator by 85 % (2.5 % vs 16.9 % — E017's own measured DD gap) scores
**~3.8× higher**, so the mechanism's real value becomes *visible and
rankable* instead of being erased by the compounding baseline.

### §3.3 Pre-registered secondary / corroborating metrics

Reported for every arm with bootstrap-95 % CIs; used for robustness and the
Pareto reasoning, **not** as the primary decision variable:

1. **Calmar** = AnnRet / |max drawdown| — the classic drawdown ratio; a
   cross-check on `RaC_β` using the single worst trough (Young-style
   drawdown ratio — see §8 references-to-add).
2. **Sharpe** = mean(excess r) / sd(r), annualised — volatility-based
   risk-adjustment cross-check (Sharpe-style; see §8).
3. **Worst-path max drawdown** and **empirical risk-of-ruin**
   `P(E ≤ 0.5·E_0)` — the capital-preservation *floor* (a candidate cannot
   win the primary while breaching these; see §6 guardrail).
4. **Operational:** time-to-resume (bars/hours) and **opportunity cost**
   (count + net R of trades that would have fired during suspension) —
   carried from E017 §1 so AK's already-good dead-time can be credited.

**Decision rule uses ONE primary (`RaC_β`).** Secondaries are guardrails and
context; they cannot be swapped in post hoc to manufacture a win
(anti-cherry-pick discipline, §7).

---

## §4 Redesigned recovery function (frozen candidates)

E017's recovery raised confidence symmetrically in the *same loss metric*
that lowered it. E019 redesigns recovery to be driven by **demonstrated
risk-adjusted progress**, so the taper-back rate is tied to the objective
being scored (removes the E017 mismatch where recovery speed and the success
metric were unrelated).

Let `Ŝ_s` be a **rolling realised/shadow risk-adjusted score** since the
suspension anchor (rolling CDaR-adjusted return over the post-halt window,
computed from shadow trades while reduced and real trades after resume).
Recovery raises `c_s` as a function of `Ŝ_s`:

| ID | Recovery law | Grounding |
|---|---|---|
| **R-riskadj** | `c_s ← C_min + (1−C_min)·clip(Ŝ_s / S_target, 0, 1)` | Re-arm in proportion to demonstrated return-per-drawdown; `S_target` = the score at which full confidence is restored. Ties recovery to the scored objective. [@chekhlov2005drawdown] |
| **R-kelly** | `c_s ← C_min + (1−C_min)·clip(f*_s / f_max, 0, 1)`, with `f*_s` a risk-constrained-Kelly fraction estimated from the post-anchor (shadow+real) R-distribution | Recovery = current risk-optimal exposure under a drawdown-probability constraint; principled single-parameter growth/drawdown trade-off. [@busseti2016kelly; @kelly1956] |

Both are **continuous**, **floored at `C_min > 0`** (never fully off), and
**monotone** in demonstrated progress. Account gauge `g` and effective
confidence `κ_s = c_s·g` are **unchanged from E017 §3** (G-surplus /
G-cdar) — E019 only redesigns the *per-symbol recovery law* and the
*success metric*, keeping everything else frozen so the comparison isolates
those two changes.

**Frozen candidate matrix (Phase 2 evaluates exactly these — no continuous
tuning):** recovery ∈ {R-riskadj, R-kelly} × gauge ∈ {G-surplus, G-cdar}
= 4 configurations, each run as **GR-S** (shadow-demonstrated recovery) and
**GR-T** (time-decay control), against the single **AK** baseline.

---

## §5 Locked parameters (frozen at approval)

| Knob | Value(s) | Rationale |
|---|---|---|
| `C_min` per-symbol floor | 0.15 | Carried from E017 §4 (reduce, don't zero). |
| `g_min` gauge floor | 0.25 | Carried from E017 §4. |
| `β` (CDaR tail, primary metric + G-cdar) | 0.95 | CVaR-family convention; single β for metric and gauge to avoid a hidden second knob. |
| `S_target` (R-riskadj full-restore score) | {1.0, 2.0} `RaC` units | Two settings only; frozen. No third added post hoc. |
| `f_max` (R-kelly cap) | 1.0 (full Kelly ceiling; real risk still capped by `max_trade_risk_pct`) | Kelly fraction normaliser. |
| `τ_live`, `τ_full` | 0.30, 0.80 | Carried from E017 §4 (tapered resume band). |
| `ρ` (GR-T time-decay) | 0.06 / day, capped so decay alone tops out at `κ = τ_full − 0.05` | Carried from E017 §4/A1 — isolates the shadow effect for H2. |
| **AK baseline** | daily-DD auto-kill clears at next UTC rollover; thrash-escalate after **3** consecutive DD-halt days; manual/non-DD kills sticky | **Mirrors the 2026-07-14 shipped code exactly** (see §1). Sensitivity: also run a legacy 48 h-blind HK for continuity with E017. |
| Ruin threshold | 0.50·E_0 | Carried from E017. |
| MC paths `N` | 10,000 | Powered for tail (CDaR, ruin) estimates. |
| MC horizon | 11,000 days/path (≈2,000 trade-events/symbol) | Carried from E017 §7 A1. |
| Symbols | EURUSD, GBPUSD, USDCAD on ONE shared account | Production topology. |
| Data-generating processes | (a) bootstrap of the E013 production-matching ledger (`programs/E017/data/trade_ledger_EURUSD_H4.json`, 737 trades, hit-rate 0.5577); (b) synthetic Bernoulli `p_win ∈ {0.40, 0.55}`, `R_win=+1.5`, `R_loss=−1.0` | Two DGPs so the verdict is not an artefact of one; identical to E017 for comparability. |
| Cross-symbol correlation | ρ ∈ {0.0, 0.5} | Carried from E017. |
| Seed | 42 | Convention. |
| Bootstrap resamples | 5,000 | Convention. |

**No parameter above is tuned during Phase 2.** Phase 2 selects only among
the discrete frozen candidate set.

---

## §6 Success criteria and stop/kill conditions (locked before results)

Mapping to the four-tier registry in `PROTOCOL_DISCIPLINE.md` §4 (labels
extended with study-specific `parked_*` reasons, per E017 precedent):

- **`alive` → advance to Phase 3 (production wiring, separately gated)** iff,
  for at least one frozen §4 configuration, **all** hold:
  1. **Primary:** GR-S beats AK on `RaC_β` — GR-S bootstrap-95 % CI lower
     bound **>** AK point estimate — robust across **both** DGPs and **both**
     correlation settings; **AND**
  2. **Capital-preservation guardrail (must not breach):** GR-S worst-path
     max drawdown ≤ AK (within noise) **and** risk-of-ruin ≤ AK; **AND**
  3. **Operational guardrail:** GR-S time-to-resume no worse than AK's
     rollover behaviour (GR-S must not be *slower* to full risk than simply
     waiting for midnight); **AND**
  4. **Gauge convergence** (E017 §4a, ≤ ε_gauge = 0.02) still passes; **AND**
  5. **Replay:** on the 2026-07-08 incident, GR-S preserves the protective
     close and improves the risk-adjusted outcome descriptively.
- **`parked_baseline_sufficient`** (H3) — AK ≈ GR-S on `RaC_β`: the shipped
  auto-clear is enough; do not add graduated machinery. **Acceptable win.**
- **`parked_shadow_adds_nothing`** (H2) — GR-S ≈ GR-T on `RaC_β`.
- **`parked_capital_cost`** — GR-S wins `RaC_β` but breaches a
  capital/operational guardrail (§6.2/6.3). Redesign required.
- **`dead` / STOP (keep AK, write `STOP_NOTICE.md`)** — GR-S does not beat
  AK on `RaC_β`, or degrades a guardrail, or the gauge check fails. Phase 3
  does not proceed.

**Stop rule (pre-declared).** If **0** configurations are `alive` at the end
of Phase 2, STOP: keep the shipped AK auto-clear as the production risk
overlay and write `STOP_NOTICE.md`. Do not open a Phase 2b or extend the
grid.

---

## §7 Anti-overfit / no-post-freeze-retuning discipline

1. **Single pre-registered primary** (`RaC_β`). Secondary metrics are
   guardrails/context and may **not** be promoted to primary post hoc to
   rescue a losing candidate.
2. **Frozen discrete grid** (§4/§5): 4 configs × {GR-S, GR-T}. **No
   continuous tuning, no post-freeze grid extension, no new candidate law
   added after approval** (`PROTOCOL_DISCIPLINE.md` §5).
3. **Multiplicity accounting.** With 8 arm-configs tested against AK on one
   primary, report Benjamini–Hochberg FDR across the family
   [@benjamini1995controlling] and the selection context of any winner
   (search width) so a reader can judge inflation [@harvey2016cross].
   Report the **Probability of Backtest Overfitting** and a
   **deflated** risk-adjusted statistic for the selected config
   [@bailey2016pbo; @bailey2014deflated].
4. **Two DGPs × two correlations** must **all** agree for `alive` — a win on
   one generator only is `parked_weak_effect`.
5. **Negative/null results are reported**, never buried: a `STOP_NOTICE.md`
   is written on `dead` / any `parked_*` (E012/E015/E016/E017 convention;
   pre-registration ethos [@nosek2018preregistration]).
6. **Metric pre-commitment against gaming.** `RaC_β`, β, `S_target`, and all
   §5 constants are frozen at approval; the winning-config edge is reported
   with its full CI, not a point estimate.

---

## §8 Separation, data ledger, references

- **Does this touch the trading agent?** **No.** E019 Phase 1 is documents.
  Phase 2 (if approved) builds a sim harness under `programs/E019/` reusing
  the E017 engine (`programs/E017/confidence_sim.py`) read-only where
  possible. Phase 3 (production wiring) is a **separate, gated** deliverable
  in `multi-pair-trading-agent`, contingent on an `alive` verdict — and note
  the **daily-DD auto-clear already shipped** is the AK baseline, not an
  E019 deliverable.
- **Data ledger.** Same posture as E017 §9: MC uses synthetic + bootstrap of
  the deployed-cell R-distribution (summary reuse of the E013 ledger); the
  2026-07-08 incident replay is a one-off descriptive case study (n = 1),
  **not** an FDR family member on market bars. No sealed `(pair, TF, split)`
  slice consumed for a statistical claim; a `planned` row is added to
  `DATA_LEDGER.md` when Phase 2 starts.
- **Prior-use note.** E019 reuses the E017 MC panel design and ledger; this
  is a **re-analysis under a new pre-registered metric**, disclosed as such
  (no fresh sealed data), so it is not double-dipping a sealed slice.

**Existing references (in `reviews/refs.bib`):** `chekhlov2005drawdown`
(CDaR, primary metric), `busseti2016kelly` + `kelly1956` (R-kelly recovery),
`grossman1993drawdowns` + `klass2005grossmanzhou` (G-surplus gauge),
`maillard2010erc` (shared-account risk budgeting), `chen2024darkside` +
`subrahmanyam1994circuit` (halt/circuit-breaker destabilisation caveats),
`bailey2016pbo` + `bailey2014deflated` (overfitting/deflation),
`benjamini1995controlling` + `harvey2016cross` (multiplicity),
`nosek2018preregistration` (pre-registration ethos), `chan2009quantitative`
(drawdown throttle).

**References to ADD to `reviews/refs.bib` before the E019 REPORT** (not
added here to avoid a concurrent-write race on the shared bib — flagged for
the coordinator): a Sharpe-ratio source (`sharpe1966`/`sharpe1994`) and a
drawdown-ratio / Calmar source (`young1991` and/or
`magdon2004maximumdrawdown`). These back the §3.3 secondary metrics; the
primary (`RaC_β`) is already covered by `chekhlov2005drawdown`.

---

## §9 Cross-references

- Parked predecessor: [`../E017_confidence_gated_cooldown/`](../E017_confidence_gated_cooldown/)
  (`PROTOCOL.md`, `REPORT.md`, `STOP_NOTICE.md`, `results.json`).
- Shipped baseline (AK): `multi-pair-trading-agent` daily-DD auto-clear
  (2026-07-14, pending human review) — `agent/live/monitor.py`
  (`_maybe_auto_clear_dd_halt`), `agent/risk/manager.py`
  (`evaluate_dd_halt_rollover`, thrash guard), `agent/utils.py`
  (`is_daily_dd_auto_kill`, `kill_file_creation_utc_date`),
  `agent/live/signal_loop.py` (recovery-state persistence + heartbeat).
- Harness to reuse (read-only): [`../../programs/E017/`](../../programs/E017/).

---

**Pre-registration commit:** _(hash after approval + push)_
