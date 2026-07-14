# AI Context — finance research experiments (updated 2026-07-14, G7 v1 checkpoint gate FIRED: **FAIL 1/7**, no v2 authorisation)

## 2026-07-14 — G7 v1 checkpoint gate FINAL verdict: FAIL (1/7 agents)

Commits `5d5c1d1` (final-verdict evaluator + 36 tests, BEFORE any gate
run) then the verdict commit. Full sim suite 796 pass / 6 skip.

**Zero new replay compute** — all six criteria were computed from the
banked caches. Verified first that the kunigami-retirement baseline is
byte-identical (per-agent n/TQS) to the post-V baseline AND to
post-V `lo1_kunigami_rensuke`, so the post-V lo1 caches are
current-code-valid for phi41; arm4 used the §11.6 B caches directly.

New `sim/scoring/run_g7_final_verdict.py` implements PROTOCOL §3's
LOCKED letter (OOS-only; C1 mean≥0.30 + window≥0.20 in ≥5/7 +
bootstrap CI low > 0.25; C2 bootstrap-CI-gated leave-one-out lift;
C3 per-window 4-of-7 at 50%; C4 panel-wide publish/read; C5/C6
panel-wide CV; §11.1 waivers; §11.12 7-agent roster; seed 42, n=10k).

**Verdict-bearing run = phi41** (protocol §4 pins the Φ4.1 aggregator;
predates Arm 4 adoption, never amended — tension noted in §11.13, and
an **arm4 companion** was evaluated alongside):

| Agent | phi41 | arm4 | blockers (phi41) |
|---|---|---|---|
| isagi | `111100` | `101100` | C5 0.086 / C6 0.083 |
| bachira | `110101` | `110111` | C3 0/7 clean (Barou dup artifact), C5 0.089 |
| rin | `111110` | `111110` | C6 0.086 |
| chigiri | `001111` | `001111` | C1 0.267, C2 |
| reo | `W11WWW` ✅ | `W11WWW` ✅ | — (only 6/6 pass) |
| nagi | `101100` | `101100` | C2; C5=C6=0.000 exactly |
| barou | `001101` | `101111` | C1 CI 0.247≤0.25 @n=62; C2; C5 |

**Both arms FAIL (1/7 < 5).** Arm 4 moves real needles (Barou → 5/6,
Bachira worst C3 window 0.97→0.62) but not the verdict. Bachira's C3
applied AS PRE-REGISTERED — the duplication-aware C3 v2 stays parked.
Per doctrine §3.11.5: **no v2 arc authorised**. Graduation toward live
paper mode is the USER's decision; the pre-condition is NOT met.

On disk: PROTOCOL §11.13 (full record + cache-reuse justification),
`reviews/g7_v1_checkpoint_final_g7final-{phi41,arm4}.{md,json}`,
EXPERIMENTS.md "M001 program gates" row.

Natural next levers (need fresh pre-reg, do NOT start unasked):
(1) C3 v2 distinctness-aware definition (Bachira), (2) F19/F20
dispersion amplification round 2 (five agents at 0.068–0.089 vs 0.10;
Nagi constant-lot root cause), (3) Barou volume floor (n=62 OOS under
phi41 makes his C1 CI unstable; arm4 already fixes it).

## 2026-07-06 night (2) — Phase X-kunigami Wild Card gate: AMBIGUOUS, mechanic inert over OOS

Commits `5769f9f` (gate implementation + 12 tests BEFORE compute),
`c55575a` (locked-criteria analyzer, committed mid-run before results),
then the verdict commit. Full suite 760 pass / 6 skip.

Gate per locked protocol: trip DD >= 25% of running peak on the $100
+$1/pip full-panel curve, release <= 12.5%, veto all admissions while
tripped (journalled `kunigami_wildcard_dd_gate`), exits untouched.
Flags: `_drive_squad_replay(kunigami_wildcard_gate=...)`, harness
`--kunigami-gate`. Pure helper `kunigami_gate_step` unit-tested.

**Verdict: AMBIGUOUS** (`reviews/kunigate_arm4_verdict.{md,json}`,
gated `kunigate-arm4` vs baseline `phi5-arm4-post-kunigami`, ~23 min,
heartbeat clean). Gate tripped twice, 9 vetoes — ALL in Feb 2015,
four years before the first OOS window. Every OOS number byte-identical
to baseline (7,272 vs 7,273 trades, TQS 0.3643, worst DD 169.8%).

**Root cause (POSTMORTEM.md §3):** additive fixed-lot pnl vs
multiplicative DD trigger. The squad nets ~55,000 pips over the panel,
so by 2019 the running peak is in the thousands and a 25% relative DD
needs thousands of pips — unreachable. The Φ5 §11.5 "every window
breaches 25%" evidence was measured on per-window curves RESET to
$100; mechanic and statistic silently used different conventions.
Kunigami stays retired-with-R5; `wildcard_defender` label NOT granted.
Any v2 (rolling-base or dollar-trip) needs a fresh pre-registration —
parked. Note: production sizes risk as % of equity (adaptive lots),
where peak-relative gating stays sensitive — sandbox convention is
the distorting factor, worth carrying into live-agent risk design.

---

## 2026-07-06 night — Phase W-barou v1.2: HALT, premise false, structural finding

Commits `4749f13` (pre-reg + mechanic BEFORE compute) → results commit.
Two pre-registered protocols landed: `phase_w_barou/PROTOCOL_v1.2.md`
(H2 continuation-entry, Bachira-anchored stop, `--barou-v12` flag, OFF
by default) and `phase_x_kunigami_wildcard/PROTOCOL.md` (Wild Card DD
gate: trip 25%/release 12.5%, design-only, compute sequenced next).

**v1.2 verdict: HALT per §5 stop rule** (`reviews/wbarou12_verdict.json`).
The anchor fired on **0/4,576** eligible proposals because Bachira's
stops are byte-identical to Barou's on every shared USDCAD tick —
both wrap the SAME `SupplyDemandAlpha(htf_align=None, target_rr=1.5)`.
`rebel_tight` describes conviction mechanics, not geometry. Both runs
byte-identical to control (squad 0.3643, Barou 567/1,280, 55.7%);
zero contamination, heartbeat clean.

**The finding (POSTMORTEM_v1.2.md §3):** Bachira→Barou "cannibalisation"
is literal strategy duplication. The lo1 "recovered" +713 trades are
the same trades relabelled. Consequences: (1) Bachira's C3 FAIL is a
duplication artifact — a C3 v2 (distinctness-aware) definition would
likely flip the squad Role Registry to PASS; (2) the R1/R6 blocks on
Barou are the risk system correctly refusing to double a duplicate
position; (3) no aggregator/geometry mechanic can help — only true
agent-level differentiation (parked: "Phase Y-barou v2 weapon
differentiation", do NOT start without discussion).

**Next compute:** ~~Phase X-kunigami Wild Card gate~~ → executed and
closed AMBIGUOUS (see block above). Parked: C3 v2 definition amendment.

---

# Previous header (2026-07-06 20:00 UTC): ARM 4 ADOPTED as G7-era default aggregator + chemistry re-baselined under Arm 4 (Bachira→Barou cannibalisation 84%→55.7%, Nagi finisher role confirmed)

## 2026-07-06 evening — Phase 5 CLOSED: Arm 4 adopted + lo1 chemistry re-baseline

Commits `cb163d4` (§11.6 adoption + pre-registration BEFORE compute) and
the §11.7 results commit. User signed off Arm 4 adoption 2026-07-06.

**Arm 4 (multi-position K=2) is the default aggregator for ALL G7-era
squad work.** Rationale is roster-health, NOT TQS (§11.5 NULLs stand).
Code default in `_drive_squad_replay` stays `phi41` for sealed-replay
byte-compat — harness invocations must pass `--aggregator-arm arm4`.

**Chemistry re-baseline under Arm 4 (§11.6 B pre-registered, §11.7
results):** 7 parallel lo1 replays (~40 min wall-clock total, heartbeat
clean), aggregated against the `phi5-arm4-post-kunigami` baseline
(7,273 trades @ 0.3643). Canonical verdict files:
`reviews/g7_{leave_one_out,role_registry}_verdict_phi5-arm4.{md,json}`
— these SUPERSEDE the post-V (phi41) verdicts for all future roster and
evolution decisions (post-V stays sealed as the Phase-3 record).

Headlines vs phi41-era Phase 3:
- **Bachira→Barou cannibalisation 84% → 55.7%** (Barou 567 present /
  1,280 absent — byte-matches the §11.5 one-off diagnostic). Still a
  C3 FAIL but only 5.7 pts over the 50% threshold; residual is now an
  AGENT-level problem → routed to Phase W-barou v1.2 H2
  (continuation-entry under Arm 4), success criterion = drop below 50%.
- **Nagi finisher role CONFIRMED under Arm 4**: C7 passes, 3 lifting
  peers (Bachira +0.1806, Rin +0.0624, Reo +0.0504). Retained C7+C8.
- Rin/Chigiri regain volume (436/437 trades, 6.0% share each); Barou
  passes C9 at 7.8%. All 7 active agents retained except the Bachira
  C3 flag (he is NOT removed: 48.8% of squad trades, Nagi's primary
  lifter, passes C2/C8/C9 — measurement, not gate, per §11.6 B).
- Kunigami rows in the new verdicts are artefacts of his §12.1
  retirement (no lo1 cache by design) — no action.

New harness flags on `run_g7_leave_one_out`: `--aggregator-arm`,
`--retire-kunigami`, `--no-aggregate` (parallel per-agent lo1 compute).
60/60 related tests pass.

**Next up:** Phase W-barou v1.2 H2 (continuation-entry, pre-register
against the 55.7% number) and Kunigami Wild Card drawdown gate — both
design against Arm 4. Arm 5 stays deferred.

---

## 2026-07-06 — Kunigami retirement executed + Phi5 Arm 3/4 re-sim verdict

Commits `7d27ce8` (pre-registration + wiring, BEFORE compute) and
`666d87a` (results). Full suite 740 pass / 4 skip.

**Kunigami RETIRED (G7 §11.12, user signed Option A).** Roster is now
7 agents (isagi, bachira, rin, chigiri, reo, nagi, barou). His R5
anti-tilt Sentinel side channel is retained (matches the measured lo1
config). C8 v2 rejected as non-informative. **Wild Card return path
pre-registered:** he comes back post-Φ5 as an aggregator-side drawdown
gate (canon: Wild Card → steals goals / defends), NOT a workspace
publisher. Implementation = `--retire-kunigami` roster flag, constants
retained for old-cache compatibility.

**Φ5 aggregator wiring landed** (`_drive_squad_replay(aggregator_arm=
"phi41"|"arm3"|"arm4")`, sealed default byte-identical). Walk-forward
caches now persist `proposals_all.jsonl` + `proposals_rejected.jsonl`
(post-V gap fixed; one 32-min re-run burned on a `to_jsonable` name
bug). Pre-run protocol fix locked in §11.4 D: Arm 4's 1% risk cap is
unsatisfiable at fixed-lot scale (median position risks $27.50 on
$100); amended to 50%-of-equity combined cap BEFORE running.

**Φ5 re-sim verdict (§11.5, `reviews/phi5_resim_verdict.md`):**

| run | n trades | median-of-window TQS | Δ vs control | verdict |
|---|---:|---:|---:|---|
| control post-kunigami (phi41) | 5604 | 0.3618 | — | baseline; byte-identical to post-V per-agent |
| Arm 3 same-direction merge | 5653 | 0.3617 | −0.0001 | NULL; 56.5% trades merged, Barou solo attribution → 0 (wrong lever) |
| Arm 4 multi-position K=2 | 7273 | 0.3643 | +0.0025 | NULL on TQS, **fixes starvation** |
| Arm 1 HRP (post-hoc) | — | 0.3549 | −0.0069 | REGRESS |
| Arm 2 TQS-floor (post-hoc) | — | 0.3643 | +0.0025 | NULL |

Key Arm 4 numbers: Barou 153→567 trades (×3.7) at HIGHER TQS
(0.3469→0.3944); Bachira-absent cannibalisation 528%→126%; squad
+30% trades; same-bar-stop rate 18.8% (clears the 30% redundancy
pre-mortem); no arm-caused DD (control worst-window DD 1.82× exceeds
both arms — sandbox fixed-lot curve was never DD-controlled).

**Interpretation:** squad-level TQS is aggregator-invariant — proposal
quality binds it, not routing. No arm is canonised on the G6-inherited
locked statistic (honest NULL). BUT Arm 4 resolves the exact per-agent
starvation pathology that nullified Phase V-b and Phase W-barou v1.1.

**~~PENDING USER SIGN-OFF~~ → SIGNED OFF same day (see section above):**
adopt Arm 4 as default G7-era aggregator on
roster-health grounds (§11.5 recommendation). If adopted: Phase
W-barou v1.2 H2 unblocks, Kunigami Wild Card gate designs against
Arm 4, Arm 5 stays deferred (no evidence-backed components besides
Arm 4 alone).

New tooling: `scripts/analyze_phi5_resim.py` (locked statistic +
bootstrap CI + diagnostics), `scripts/run_arm4_lo1_bachira.py`
(cannibalisation diagnostic), `sim/tests/test_aggregator_arm_wiring.py`.

---

## 2026-07-03 morning — Phase 3 verdict + Role Registry v1 + Phase W-barou v1.1 NULL

Five commits (`314cca4`, `3c1ce7d`, `d81bd46`, `a9706e5`) landed in this
session, plus two hotfix commits (`21f8522`, `884985e`) for the C2/C3
aggregator.

**Verdict summary:**

| Deliverable | Status | Commit | Numbers |
|---|:---:|---|---|
| Phase 3 C2/C3 verdict on-disk | ✅ | `314cca4` | 8/8 replays; Bachira C3 fail (84.1% cannibalisation on Barou) |
| Role Registry v1 (C7/C8/C9 + role labels + retention) | ✅ | `3c1ce7d` | Nagi = finisher retained; Kunigami = retirement candidate (only one) |
| Kunigami retirement decision doc | ✅ | `d81bd46` | Options A/B/C, recommend A. Awaits user sign-off. |
| Phase W-barou v1.1 code + tests | ✅ | `d81bd46` | H1 lands, H2 deferred to Phi5 Arm 4 |
| walk-forward-post-W verdict | ✅ **NULL** | `a9706e5` | byte-identical to post-V; §11.11 postmortem |

Full sim test suite: **726 pass / 4 skipped** at commit `a9706e5`.

Phase 3 C2/C3 compute completed (all 8 replays, ~16h wall-clock vs
~32h estimate). Two aggregator hotfixes shipped: TQS schema
(`21f8522`) + strongest-lift picker (`884985e`). Final verdict on
disk committed `314cca4`.

### Role Registry v1 (`3c1ce7d`) — companion test to G7 v1

`experiments/G7_role_registry_v1/PROTOCOL.md` pre-registered new
criteria C7 (incoming chemistry), C8 (workspace-signal impact via
v1 proxy), C9 (trade-volume floor), plus role labels and retention
rule. Post-V verdict (`reviews/g7_role_registry_verdict_post-V.md`):

- **Nagi** → `finisher, workspace_catalyst` — RETAINED. 3 peers
  lift him (Bachira +0.1979, Rin +0.0886, Reo +0.0719 TQS). Blue-
  Lock star-finisher intuition validated on real data.
- **Kunigami** → `retirement_candidate` — NOT RETAINED. C8
  workspace_impact = 0.0 exactly (no peer moves when Kunigami is
  removed). Only agent flagged for retirement.
- **Barou** → `workspace_catalyst` — RETAINED on single thin axis
  (C8=151.3 eps). Motivates Phase W-barou to broaden his footprint.
- **Bachira** → `chemistry_catalyst, workspace_catalyst` but NOT
  RETAINED under strict retention rule (C3 fail via 84.1% Barou
  cannibalisation). Aggregator-level issue, not agent-level —
  addressable via Phi5 Arm 3/4.

C8 v1 uses peer-delta magnitude proxy because true F22c
`interpreted_signal_family` citation counts are NOT persisted in
post-V artifacts (see PROTOCOL §12 amendment note). Cleanly
separates Reo (245 eps, real gatekeeper) from Kunigami (0.0 eps,
dead-weight publisher). Kunigami decision doc drafted
(`DECISION_kunigami.md`) laying out Options A retire /
B re-evolve / C wait for C8 v2 — recommends A pending sign-off.

Also fixed two data-availability bugs in `compute_c7` /
`compute_c8_proxy` discovered during test authoring (missing lo1
caches were being treated as "peer stats went to zero", producing
false positives). Both functions now skip peers with no lo1 cache
and mark the entire agent as unmeasurable if their own lo1 cache
is missing. 15 new tests locked in the behaviour.

### Phase W-barou v1.1 (`d81bd46`) — H1 lone-conviction claim

Blue-Lock evolution for Barou (Rin Phase T-evolve precedent).
`experiments/phase_w_barou/PROTOCOL.md` pre-registers H1 (LANDED)
+ H2 (DEFERRED to v1.2 pending Phi5 Arm 4 multi-position support).

H1 mechanic in `sim/agents/a07_barou.py`:

- Read Bachira's latest same-symbol thought via `latest_by_agent`.
- If Bachira DIDN'T publish, or published OPPOSITE direction →
  Barou's read is genuinely solo, apply
  `BAROU_V1_1_LONE_CONVICTION_LIFT = 0.10` (mirrors Rin's
  LONE_READ_LIFT exactly).
- If Bachira SAME direction → H1 skips, existing devour path
  handles it unchanged. Guarantees post-W vs post-V isolates
  H1 contribution.
- H1 stacks orthogonally on devour lift (both fire → both applied,
  capped at 1.0).

Locked acceptance test (§5): LAND if `n_trades ≥ 250 AND
mean_tqs ≥ 0.34 AND bachira_barou_cannibalisation ≤ 0.60`.
REVERT if `n_trades < 100 OR mean_tqs < 0.30`. AMBIGUOUS → no
auto-land.

5 new tests locked H1 behaviour (fires when no bachira, fires when
opposite, skips when same-dir, defaults when workspace unavailable,
stacks with devour). Full sim suite: **726 pass, 4 skipped**.

### Phase W-barou v1.1 verdict — NULL RESULT (`a9706e5`)

walk-forward-post-W completed 2026-07-03 09:47 UTC (53 min wall-clock,
heartbeat healthy throughout — recovered from an initial nohup&
launch that silently died; re-launched via Shell backgrounding to
success).

Trade-level outcomes are BYTE-IDENTICAL to post-V. Every per-agent
n_trades and mean_TQS matches to four decimal places:

    isagi     1923/0.3568 (V) → 1923/0.3568 (W) : delta 0/+0.0000
    bachira   2542/0.4026        2542/0.4026     : delta 0/+0.0000
    rin        421/0.3940         421/0.3940     : delta 0/+0.0000
    chigiri    430/0.2585         430/0.2585     : delta 0/+0.0000
    nagi       135/0.4313         135/0.4313     : delta 0/+0.0000
    barou      153/0.3469         153/0.3469     : delta 0/+0.0000
    squad     5604/-              5604/-         : delta 0/+0.0000

Same 336707 thoughts, 28842 proposals, byte-identical workspace_counts.

Per PROTOCOL §5 thresholds → AMBIGUOUS zone (barou n_trades 153 above
REVERT floor of 100 but below LAND floor of 250; mean_tqs 0.347 above
both floors but LAND requires ALL three including cannibalisation).

Root cause (same as Phase V-b sec 11.9-postmortem): H1 fires ONLY on
ticks where Bachira did NOT compete. Those are the ticks where Barou
was ALREADY winning R6 as sole proposer -- +0.10 conviction changes
nothing. Ticks where Barou is BLOCKED (Bachira same-direction same-
slot) fall through H1's SKIP branch, leaving devour to handle them,
which post-V already showed doesn't work.

Formal root cause: **aggregator single-slot mutex, not agent
conviction.** Cannot be fixed at the agent level.

Resolution:
* Leave H1 code in place as DIAGNOSTIC-ONLY. Rationale fields
  (barou_lone_conviction_claim, barou_v1_1_bachira_read_present,
  barou_v1_1_bachira_same_direction, _yield_reason) feed Phi5 Arm
  3/4 pre-registration.
* Do NOT ship Phase W-barou-v1.2 at agent-conviction level.
* Escalate to Phi5 Arm 3 (same-direction merge) as primary
  intervention, Arm 4 (multi-position) as fallback.

G7 v1 PROTOCOL amended with sec 11.10 (Role Registry v1 landing) and
sec 11.11 (Phase W-barou null result).

### What is next (blocked)

**Kunigami retirement decision** -- awaits user sign-off on
`experiments/G7_role_registry_v1/DECISION_kunigami.md` (Options A
retire [recommended] / B re-evolve / C wait for C8 v2). Recommended
action: Option A + amendment sec 11.12 + regenerate walk-forward-post-
kunigami-retirement (baseline for Phi5 Arm 3/4 re-sim).

**Phi5 Arm 3/4/5 walk-forward** -- BLOCKED on engineering work:
1. Aggregator wiring in _drive_squad_replay to accept an aggregator
   parameter (currently hard-wired to Phi4.1).
2. Fresh walk-forward-post-V-with-proposals output (current cache
   only saves trades.jsonl, not proposals.jsonl -- Phi5 Arms 1/2
   post-hoc gates need the wider proposal universe).
3. Pre-registration amendment locking Phi5 arm order-of-run against
   the post-V + post-W numbers (must be locked BEFORE new numbers
   are known).

This is next-session work; the Phi5 arm modules themselves are
already implemented (`sim/core/aggregator_arms/{hrp,tqs_floor,
same_direction_merge,multi_position,combined}.py`) but not yet
wired into a fresh walk-forward driver.

**True F22c citation counts (C8 v2)** -- needs intents.jsonl
persistence in run_phi4_squad_gate.py + re-run walk-forward-post-V.
See Role Registry v1 PROTOCOL sec 12 amendment note. Only critical
if Kunigami retirement is questioned on the v1 proxy.

**Phase 7 player scouting reports** -- still blocked on Phi5 verdict.

---

## Earlier: 2026-07-03 04:07 UTC (superseded — kept for lineage)

## 2026-07-03 evening — Phase 6c halt + Phase 5 scaffold + Phase V-iterate template

Session-fill work while Phase 3 C2/C3 compute grinds in background
(pid 27370, replay 1/8 at 95% at write time). Four atomic commits
land things that DO NOT depend on the C2/C3 verdict; things that do
are held on disk. Heartbeat monitor rule tightened to
`alwaysApply=true` across all three linked repos.

### 6c HALTED (`bf461ad`) — DK freeserv endpoint deprecated

Attempted the 2007-2026 backfill against
`https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events`
and discovered the endpoint has been retired for anonymous
consumption. All six URL variants probed (v1 get_calendar_events,
v2 get_events, v3 no-jsonp, v4 events/calendar, v5 countries=,
v6 bare) return 403 (default UA) or 204 with `text/html`
Content-Type (browser UA). The live DK calendar page now iframes
`https://widgets.dukascopy.com/en/economic-calendar` — a modern
Angular SPA whose calendar API is served via lazy chunks not
addressable by static grep.

`STOP_NOTICE.md` documents the six-variant probe table, relaunch
prerequisites (headless-browser reverse of the widget, or switch
primary to FF / TE), and the do-NOT list. Zero artifacts written
to `data/news_calendar/DK/`. Phase 6c is `HALTED-DK-ENDPOINT-
DEPRECATED` pending Phase 6a-v2 (fresh fetcher against a working
endpoint).

**Silver lining that DID land:** the endpoint discovery only became
possible after fixing an SSL cert-verify failure that was blocking
every request. macOS framework Python doesn't trust system keychain
roots; certifi-backed context added to
`sim/regime/dukascopy_fetch.py::_default_urllib_transport`. Real
fix, keeps the fetcher useful the moment a v2 endpoint is chosen.
44 dukascopy-fetch tests remain green.

### Phase 5 shadow-HRP input builder (`bafd01b`) — 35 new tests

Ships the input-transformation side of the Phi5 Arm 1 re-sim under
Amendment §11.3 (arm mechanic unchanged, only input distribution).
Compute-side re-sim (Phase 6e) still waits on Phase 3 per §11.3
follow-up ordering.

New module `sim/core/aggregator_arms/hrp_shadow_inputs.py`:

- `WindowBoundary` + `ShadowHrpMetric` (tqs / pnl_pips / r_multiple).
- `_entry_to_datetime`: coerces `ShadowTradeRecord.entry_time`
  (typed Any) to native datetime; accepts datetime / pandas
  Timestamp / ISO string; silent-drops malformed.
- `bucket_shadow_by_agent_window`: linear-scan bucketing (windows
  O(10) for M001 panels).
- `per_agent_window_means_from_shadow`: dict[agent -> chronological
  list[float]], empty windows SKIPPED (not zero-filled) since
  `compute_hrp_weights` right-aligns.
- `per_agent_shadow_trade_counts`: totals ALL shadow trades per
  agent regardless of rejection_reason.
- `compute_hrp_weights_from_shadow`: thin composition. All HRP
  tuning kwargs (min_trades_per_agent, shrinkage, weight_cap,
  jitter, max_condition_number) pass through verbatim so Phi5
  protocol §3.2 locked parameters stay frozen.

Statistical-honesty guard: module docstring calls out the known
upward bias in shadow returns (no R6 concentration cap, no R4
correlation cap per `shadow_ledger.py`). Bias correction is
caller-side, not implicit.

35 new tests: entry-time coercion (6), metric extraction (5),
bucketing (6), window-means (6), trade counts (3), composition
kwarg propagation (8), wire-not-mechanic equivalence (1). Full sim
suite: **701 pass / 4 skip** (was 666, +35).

### Phase V-iterate pre-reg TEMPLATE (`fc91571`)

Locks the design frame BEFORE Phase 3 numbers exist so no
retro-fitting is possible. `experiments/phase_v_iterate/PROTOCOL.md`
enumerates all four candidate mechanics from G7 §11.9-postmortem:

| Arm | Mechanic | C2/C3-gated precondition |
|-----|----------|--------------------------|
| A | Per-tick conviction +0.10 lift | C2 pass with Δ ≥ 0.020 |
| B | Symbol-conditional slot reservation | C2 pass + 2 peers ≥ 0.40 red |
| C | Peer-YIELD (Rin analogue) | C2 pass + 0-1 peers ≥ 0.20 |
| D | Concede (no code change) | C2 fail |

Each arm has full mechanic spec (implementation surface, guard,
risk). §11 amendment discipline preserved — no in-place threshold
retuning; a picked-arm FAIL requires a NEW pre-registration.
Numbers table has explicit TBD cells for C2/C3 fill-in. Status
`template-pending-c2c3` promotes to `pre-registered` only when
Phase 3 lands and exactly ONE arm is selected.

### Heartbeat monitor rule → alwaysApply=true (`957df49` + `2982e74` + brain-box `6625324`)

User directive 2026-07-03: standard rule across every workspace.
Flipped `alwaysApply: false` → `true` and added a non-negotiable
preamble. Default is "wire the monitor"; skipping requires an
inline written justification. Two operational details encoded:

- Follow the pipe/shell chain to get the actual interpreter PID
  (not the wrapping `zsh -c … | tee`).
- After launch, wait one sample interval (~30-60s) and read the
  log tail before ending the turn — a broken monitor wire that
  produces no samples is the same failure mode as no monitor.

Mirrored to both workspace repos (`finance-research-experiments`,
`multi-pair-trading-agent`) and the brain-box canonical rule.

## 2026-07-03 — Phase 3: C2/C3 leave-one-out compute LAUNCHED (running)

The pre-registered Phase 3 gate criteria (C2 positive-sum chemistry +
C3 non-cannibalising slot behaviour) that have been stubbed as
"pending" in every G7 verdict since Phase R now have a real compute
harness driving them. Job kicked off ~03:31 UTC on 2026-07-03, ETA
~5.6 h wall-clock (8 sequential leave-one-out replays over the 2015-
2025 EURUSD/GBPUSD/USDCAD panel, ~42 min each). Heartbeat monitor
v2.1 active on the Python interpreter PID with 60 s sampling,
20 % CPU floor, 6-sample stall gate, 30-sample no-output gate.

**Committed now (`589aae7`, does not depend on results):**

`sim/scoring/run_g7_leave_one_out.py` — leave-one-out compute runner
+ C2/C3 aggregator. Runs 8 replays sequentially with each agent
removed from the proposer list (kept as config/state holders for
isagi/barou/kunigami where needed), dumps `trades.jsonl` +
`shadow.jsonl` + `workspace_counts.json` per lo1 for crash recovery,
then aggregates against the walk-forward-post-V baseline cache to
compute per-peer delta stats + C2/C3 verdicts + audit-grade md+json
emitters.

Aggregator math:
- `_per_agent_stats`: n_trades over ALL trades; mean_tqs over trades
  with a valid numeric tqs so partial writes don't bias the mean.
- `_compute_reduction_ratio`: `(lo1_n - baseline_n) / lo1_n` --
  fraction by which a peer's trade count grew when the excluded
  agent was absent. Positive ⇒ cannibalisation.
- `compute_c2_c3`: C2 pass = ∃ peer where baseline strictly better
  than lo1 by ≥ 0.005 tqs or ≥ 1 trade (either metric qualifies);
  C3 pass = worst per-peer reduction ratio ≤ 0.5.
- `aggregate_from_disk`: composes baseline + lo1 caches into full
  verdict; missing lo1 caches leave verdict `pending` (never
  auto-pass).

CLI: `--tag post-V --out-dir ... --baseline-cache-dir ...
--exclude <agent_id> [repeatable] --aggregate-only --include-
baseline -v/-vv`.

**Tests: 26 new** (`test_run_g7_leave_one_out.py`) covering the
math + emitters + CLI (compute side runs against real bars and is
exercised by the actual job). Full sim suite: **666 pass / 4
skipped**.

Statistical-honesty guard: C2/C3 are DIAGNOSTIC criteria; they fill
in pending G7 stubs but never authorise a code change on their own.
The runner cannot "promote" any agent, only score.

**Deliverables when compute lands (~08:00 UTC):**
- `reviews/g7_leave_one_out_post-V/lo1_<agent>/…` × 8 (trades cache).
- `reviews/g7_c2_c3_verdict_post-V.{md,json}` (verdict + per-peer
  delta tables).
- Amended G7 verdict registry row filling in C2/C3 for post-V (also
  the F22 baseline row, since same panel + same baseline).

## 2026-07-03 — Phase 6b: news-calendar backfill CLI + writer LANDED

Commit `1b6848c`. Composes the Phase 6a Dukascopy fetcher into the
partitioned parquet writer + SHA256 manifest builder pre-registered
in the news calendar contract (`data/news_calendar/README.md`
sec 3). CLI `scripts/backfill_news_calendar.py --source dukascopy
--start ... --end ... --currencies USD,EUR,... --out-root ...
--dry-run`. 31 new tests covering DF conversion / partition write /
SHA256 / manifest / CLI. Full run against live DK deferred to Phase
6c (~1 h compute, needs network — parked pending user go-ahead
after C2/C3 lands).

## 2026-07-03 — Phase 6a: Dukascopy freeserv HTTP fetcher LANDED

News-calendar Phase 6 was un-deferred after the Phase V null result
freed the sequence. Phase 6a ships the D-Q1 primary source live-HTTP
fetcher (spec §1.4) with all 44 tests CI-clean via injected fake
transport (D-Q8 preserved).

**New module `sim/regime/dukascopy_fetch.py`.** Real fetcher for
`https://freeserv.dukascopy.com/2.0/index.php?path=events/get_events`
with:
- URL builder (epoch-ms UTC, group=news, currencies csv, importance
  normalised).
- JSONP unwrap (accepts `cb({...})`, `cb({...});`, or bare JSON).
- Event normaliser mapping DK importance strings + numeric IDs +
  epoch-ms/ISO timestamps to Phase M canonical row schema.
- `iter_chunks` per-day chunker + rate limiter (500 ms polite gap,
  injectable time source for tests).
- Exponential-backoff retry on 5xx / 408 / 425 / 429, single-shot on
  other 4xx per Dukascopy's TOS-neighbourly behaviour.
- `DukascopyFetchStats` telemetry dataclass consumed by the manifest
  writer (Phase 6b).

**Adapter wire.** `DukascopyAdapter()` with no `fetcher=` now
delegates to `default_dukascopy_fetcher` (lazy-imported so the
urllib pull-in doesn't fire unless the adapter is used with
defaults). Injected `fetcher=` still takes precedence -- test
fixtures unchanged, CI still 100% network-free.

**Tests: 44 new** (`test_dukascopy_fetch.py`) covering:
- URL builder shape + validation edge cases (naive dt, end < start,
  bad importance, empty currencies).
- JSONP unwrap shapes (standard wrap, trailing semicolon, whitespace,
  callback drift, plain JSON fallback, bare list, empty/malformed
  bodies).
- Event normaliser (full row, case-insensitive importance, numeric
  importance, unrecognised importance dropped with warning, missing
  required fields, ISO timestamp, all-day null timestamp, stringy
  actual with unit extraction).
- Chunk iterator (1-day, multi-day, truncated last chunk, invalid
  chunk_days).
- Rate limiter (no-sleep first call, sleep for the deficit,
  no-sleep when gap already large).
- End-to-end `fetch_events` (single chunk, multi-chunk accumulation,
  bare-list payload, 5xx-then-success retry, retry exhaustion,
  4xx not retried, 429 retried, malformed body, dropped
  unrecognised importance).
- `DukascopyAdapter` default-fetcher delegation + injected-fetcher
  precedence.
- `default_dukascopy_fetcher` wrapper argument forwarding.

Sim suite: 609 passed / 4 skipped (+44 Phase 6a tests, +1 updated
existing test).

**What's next (Phase 6b):** `scripts/backfill_news_calendar.py` CLI
composing DK fetcher → parquet writer → manifest with SHA256. Then
Phase 6c is the compute-session job actually running the ~1-hour
2007-2026 backfill against live Dukascopy.

## 2026-07-02 evening → 2026-07-03 — Phase V-a + V-b NULL RESULT, reverted

**Verdict:** REVERT. Both Chigiri regime-specialist (V-a) and Barou
solo-king clarification (V-b) failed their pre-registered acceptance
criteria on walk-forward-post-V. Per PROTOCOL §11.9 honesty guards,
the active mechanic (rationale stamps `_effective_tier=1`) was
surgically reverted; aggregator plumbing + diagnostic ratios retained
as regression scaffolding + audit surface for a future V-iterate.

**Delta comparison (post-F22 → post-V, exact from JSONs):**

| Agent   | N_shadow | N_flips | Δ_post-F22 | Δ_post-V | Target      | Verdict |
|---------|---------:|--------:|-----------:|---------:|:------------|---------|
| Chigiri | 992      | +1      | +0.04887   | +0.05085 | ≤ +0.02     | FAIL (moved WRONG way) |
| Barou   | 4576     | 0       | +0.01488   | +0.01488 | ≤ 0.0       | FAIL (no movement)     |
| Rin     | 1494     | ~0      | −0.14622   | −0.14693 | (guard)     | ✓ robust               |
| Isagi   | 6571     | 0       | +0.00507   | +0.00507 | (no-sfx)    | ✓ no side-effect       |

**Root cause.** The rationale-flagged effective-tier promotion
neutralises TIER_BIAS (0.05) but the raw conviction gap between
Chigiri/Barou and Isagi averages 0.08-0.12 on the very ticks where
they compete. Removing 0.05 does not close the gap; Isagi still wins.
Also the specialist double-hurdle (`mag/atr>=1.5 AND atr/median>=1.5`)
restricts firing to ~5% of Chigiri's bars, and on those bars Isagi's
metavision peaks together with Chigiri's breakout. Zero routing
mobility.

**Retained** (regression scaffold + audit surface for future
V-iterate):
- `_effective_tier` helper + `_EFFECTIVE_TIER_RATIONALE_KEY` in
  `run_phi4_squad_gate.py` (regime-neutral, no side-effect without
  active stamp).
- Chigiri's `mag_atr_ratio`, `atr_expansion_ratio`, and
  `chigiri_regime_specialist` boolean in rationale (audit).
- Barou's `barou_solo_king_specialist` boolean in rationale.
- All aggregator-side tests in `test_phase_v_regime_specialist.py`
  (docstring updated).

**Reverted** (per statistical honesty guard):
- `_effective_tier=1` stamp in `a04_chigiri.py::intend`.
- `_effective_tier=1` stamp in `a07_barou.py::intend`.
- Agent-level tests now assert the tier override is ABSENT + a new
  regression guard `test_specialist_bit_is_diagnostic_not_routing`
  in Barou's suite.

**Next-mechanic hypotheses** (parked, do NOT implement without fresh
pre-registration):
- **Option A — per-tick conviction LIFT** (raw +0.10, not just neutralise
  tier bias). Risk: over-firing.
- **Option B — symbol-conditional slot reservation** (aggregator-side).
- **Option C — Phase T-evolve-style peer-YIELD** (analogous to Rin's
  proven v1.1 mechanic).
- **Option D — concede.** Recommended first step: measure C2/C3
  leave-one-out (~32h) to see if Chigiri/Barou contribute counterfactual
  alpha at all. If not, their crowding is a canon-consistent feature.

Full postmortem in G7 PROTOCOL §11.9-postmortem. Sim suite: 565
passed / 4 skipped (+1 new regression guard test).

## 2026-07-02 afternoon — F22 workspace-richness upgrade (three commits)

Three named gaps in the F21 reasoning workspace closed together as F22
(a/b/c). Each commit ships a fix + unit tests; the trio is validated
by an end-to-end synthetic-panel replay proving inference accuracy.

**F22a (73f67fc) — Thought richness.** New ``ThoughtRead`` frozen
dataclass on ``Thought.read``: signal_family, direction_bias,
regime_read, expected_stop_pips, expected_r, driving_evidence.
Canonical ``SignalFamily`` literal covers every roster agent
(metavision / pattern_rebel / precision / breakout / adaptive_copy /
confluence / solo_king / risk_watch / unknown). All 8 agents' observe()
main-path populates read; abstentions keep read=None so the workspace
filter excludes them. WorkspaceSnapshot gained ``signal_family=...``
first-class filter on read_for and peer_thoughts. Pip helpers
consolidated in provenance_pips.py.

**F22c (0d3c78f) — Interpretation record.** New ``YieldReason`` frozen
dataclass + ``IntentDecision = AgentProposal | YieldReason | None``
widened union. BlueLockStriker.intend protocol updated. Rin's Phase
T-evolve yield now emits YieldReason(reason=
"isagi_would_lift_metavision", peer_ids_read=(...), evidence={...})
with full audit-trail payload. Driver appends every YieldReason to
SquadRunOutput.yields; silent legacy Nones remain silent.

**F22b (aeb5770) — Tick-barrier snapshot.** Doctrine sec 3.8 forbids
look-ahead reads, not same-tick reads at the barrier. New
``ReasoningWorkspace.snapshot_at_barrier`` with rule tick_id <=
current_tick (was <). Future ticks still refused. Driver swapped in
``_drive_squad_replay``. Rin's Phase T-evolve now reads Isagi's
tick-T metavision instead of stale tick-T-1.

**F22 E2E proof (aeb5770).** 2-agent (Isagi + Rin) synthetic-panel
replay scores three empirical guarantees:
- G1 (F22a semantic): 100% of signal-path Thoughts have structured read.
- G2 (F22b same-tick): 4/4 metavision-yields paired with a same-tick
  same-direction Isagi Thought.
- G3 (F22c inference accuracy): 4/4 = 100.0% -- Rin's metavision-yield
  inference matched Isagi's actual proposal direction on every scorable
  tick.

Full sim suite: 551 passed, 4 skipped. Zero regressions across F22.

Doctrine 06 sec 4.1d amendment landed with all three fixes documented
together.

**walk-forward-post-F22 verdict (2026-07-02 13:43): F22 is pure
observability.** Same 5,604 total trades, same per-window counts
(441/419/505/539/453/358/360), identical Isagi + Rin + Barou +
Nagi splits, 9-trade reshuffle at the Bachira/Chigiri R6 boundary.
Rin's Phase T-evolve delta stays at -0.146 (unchanged from post-TU)
-- proving her yield rule is robust to the 1-tick peer-read lag.
The workspace-richness upgrade delivered exactly what its design
promised: richer AUDIT surface, zero behavior drift.

**Post-F22 delta table (locked baseline for Phase V):**

| Agent   | tqs_acc | tqs_rej | Δ (rej-acc) |
|---------|---------|---------|-------------|
| Isagi   | 0.300   | 0.305   | +0.005      |
| Bachira | 0.320   | 0.307   | −0.013      |
| Rin     | 0.337   | 0.191   | **−0.146**  |
| Chigiri | 0.241   | 0.290   | **+0.049** (worsened by +0.005) |
| Nagi    | 0.300   | n/a     | n/a         |
| Barou   | 0.302   | 0.317   | **+0.015** (unchanged) |

**Phase V outcome (2026-07-03):** BOTH V-a and V-b returned NULL
RESULTS on walk-forward-post-V and were reverted per honesty guard.
See top-of-file postmortem for full delta analysis + root cause +
next-mechanic hypotheses. Recommendation: concede + measure C2/C3
before designing another mechanic.

## 2026-07-02 — Phase T-evolve walk-forward result: PASS

Rin v1.1 walk-forward-post-TU delta = **−0.146** vs. the ≤ −0.05
threshold in doctrine §4.1c. Roster locked to `v1.1 confirmed`.

**Two-column verdict:**

| Agent   | v1.0 acc/rej | v1.0 delta | v1.1 acc/rej | v1.1 delta |
|---------|--------------|------------|--------------|------------|
| Rin     | 0 / 1494     | n/a        | 966 / 528    | **−0.146** ✓ |
| Isagi   | 6024 / 547   | −0.049     | 5075 / 1496  | +0.005 |
| Chigiri | 827 / 165    | +0.021     | 810 / 182    | +0.044 |
| Barou   | 454 / 4122   | +0.015     | 454 / 4122   | +0.015 |

Rin now has higher accepted TQS (0.337) than Isagi (0.300). Total
squad trades 5,761 → 5,604 (net −157). Canon: Neo-Egoist Rin acts on
her own reads without waiting for peer confluence.

Baseline locked as `74fca72`. walk-forward-post-TU verdict lands
in the next commit alongside roster + ai_context updates.

## 2026-07-01 night — Phase T-evolve: Rin v1.1 peer-yield-and-lift

**Not a retirement — a mechanic evolution.** In canon, Rin and
Isagi evolve off each other; retiring Rin was rejected by the user.
Instead Rin gains a peer-yield-and-lift mechanic that lets her
score where Isagi *can't*:

- **Yield rule.** In `intend()`, if Rin sees `peer_agree_count >= 1
  and peer_disagree_count == 0` on the same symbol, Isagi's
  metavision lift will fire → Rin returns None. She cedes.
- **Lone-read lift.** Otherwise (peers disagree or all quiet),
  Rin adds `RIN_V1_LONE_READ_LIFT = +0.10` on top of her precision
  lift. Total conviction reaches 0.90; decisively beats Isagi's
  base 0.65 on ticks where his metavision doesn't fire.

Committed as `9fac80b`. Sim suite 503 passed / 4 skipped (+3
Phase T-evolve tests).

**Amendments landed:**
- Doctrine §4.1c — Phase T-evolve mechanic + delta-sign acceptance
  test (Rin's Phase U shadow delta must be ≤ −0.05 for v1.1 to
  clear).
- G7 PROTOCOL §11.8 — wiring + revert protocol.
- Roster: Rin row updated to `v1.1 implemented`.

**Compute in flight:** walk-forward-post-U (Phase U wiring, Rin
still v1.0 because the Python process imported at start-up) is
running. When done, walk-forward-post-TU (Rin v1.1) is launched.
Two-column side-by-side is required per §07-research-standards.

## 2026-07-01 night — Phase U: Shadow ledger + Blue-Lock scouting attribution

Phase U ships the "scouting record" that lets us reason about
Rin/Isagi crowding-out honestly. Every proposal (accepted or
rejected) is now optionally re-run through the fill/exit engine in
isolation, producing a `ShadowTradeRecord` in
`sim/scoring/shadow_ledger.py`. Aggregated per-agent, the ledger
reports **shadow-TQS-when-accepted** vs **shadow-TQS-when-rejected**
plus their delta — that delta is the routing-quality signal.

**Reading the delta:**
- Delta ≤ −0.10 → aggregator picks winners; crowding-out is a
  design feature.
- Delta ~ 0 → routing is random with respect to trade quality;
  agent's alpha is real but sidelined; Phase T-style evolution
  warranted.
- Delta ≥ +0.10 → routing bug; rejected proposals were the better
  trades.

**Blue-Lock canon frame** is now doctrine §4.1b: scouts credit
players who READ plays that ended in goals, not just those who
scored. Rin doesn't retire — she and Isagi evolve off each other,
canon.

**2024 OOS dry-run seed data:**

| Agent | N shadow | TQS acc | TQS rej | Δ | Reading |
|---|---:|---:|---:|---:|---|
| Isagi | 1177 | 0.324 | 0.249 | −0.075 | aggregator picks winners |
| Bachira | 2772 | 0.330 | 0.327 | −0.003 | tie-break random for her |
| Rin | 211 | n/a | 0.254 | n/a | 0 accepted -- crowded out |
| Chigiri | 154 | 0.188 | 0.253 | **+0.065** | rejected > accepted (routing bug) |
| Nagi | 135 | 0.282 | n/a | n/a | all his fire (0 rejected) |
| Barou | 905 | 0.288 | 0.315 | +0.027 | mild routing bug |

**Also per-trade research-grade quality metrics** (Kaufman-Sweeney
entry_efficiency, exit_efficiency, Almgren-Chriss friction_ratio)
are stamped on every ShadowTradeRecord and aggregated to per-agent
means alongside TQS. Full walk-forward rerun with Phase U wiring is
the next compute job.

**Amendments landed:**
- Doctrine `06-blue-lock-doctrine.md` §4.1b — Phase U shadow
  ledger, alpha-attribution signals, diagnostic-only guarantee,
  research-grade quality metrics, Blue-Lock canon frame.
- G7 PROTOCOL §11.7 — Phase U wiring + accepted-vs-rejected delta
  interpretation + systematic-bias notes.
- `sim/scoring/shadow_ledger.py` — new module (30 unit tests pass).
- `sim/scoring/run_phi4_squad_gate.py` — `use_shadow_ledger` flag on
  `_drive_squad_replay`, `SquadRunOutput.shadow_trades` field.
- `sim/scoring/run_g7_v1_checkpoint_gate.py` — shadow aggregation +
  markdown/JSON emission in both dry-run and walk-forward modes.
- `sim/scoring/run_isagi_phi3_gate.py` — `TradeRecord.source_tick_id`
  added for shadow<->executed pairing.

**Also this session:** `brain-box/meta/tools/monitor_compute_jobs.py`
v2.1 resilience fix. Root-caused the silent monitor death that let
Phase R + Phase S walk-forward runs proceed with only `session_start`
in the JSONL. Cause: `_ps_sample` caught only
`CalledProcessError`; sandboxed `ps` failures raise `OSError` which
killed the monitor silently. Fix: broaden exception surface, add
`os.kill(pid, 0)` aliveness fallback, wrap main loop in
try/except, ignore degraded samples in STALLED classifier. Full
history entry in `agents/heartbeat-monitor.md`. Committed as
`brain-box@91e8ced`.

Sim suite: 528 passed / 4 skipped (+30 Phase U shadow ledger tests).

## 2026-07-01 night — Phase S: F19 variance amplification + Isagi breakthrough

Second full-panel walk-forward rerun of the day, with F19 variance
fixes on top of Phase N/O/P: 5,761 trades across 7 windows.
Verdict `walk-forward-post-NPOS`:
`programs/M001_multi_agent_ensemble/reviews/g7_v1_checkpoint_verdict_walk-forward-post-NPOS.md`.

**Isagi flipped to C1 PASS 7/7 windows** (mean TQS 0.357 vs 0.322 in
Phase R, first clean C1 pass ever for Isagi). Mechanism: metavision
peer-alignment lift (+0.05 for 1 peer confluence, +0.10 for 2+) turns
his flat `sig.conviction = 0.65` into a range 0.60..0.75 that actually
tracks setup quality, and `regime_fit_from_atr` gives him per-bar
regime variance.

**C5 barrier finally cracking** — Chigiri 0.096, Bachira 0.087, Isagi
0.076, Barou 0.049 (all up from 0 or near-zero in Phase R). Three are
one hair below the 0.10 threshold; a small `regime_fit_gain` widening
in their playstyles would push them across.

**Rin regressed to 0 trades.** Not a bug -- structural crowding-out
mirroring what Isagi/Barou suffered pre-Phase-N. Rin's proposal set
is a strict subset of Isagi's (both wrap `SupplyDemandAlpha`, Rin
adds a stop-tightness filter on top). Post-Phase-S Isagi's metavision
lift beats Rin's precision lift at the aggregator (tier tiebreak).
Rin needs a Phase T mechanic that fires when Isagi DOESN'T, not a
tighter filter on top of the same signal. Candidate: peer-
disagreement trader.

Amendments this session:
- Doctrine `06-blue-lock-doctrine.md` §3.10a — structural-falsifier
  waiver class extended from Reo to include Kunigami.
- G7 PROTOCOL §11.1-11.6 — dated amendments for Kunigami waiver +
  Phase N aggregator + Phase O F21 reads + Phase P provenance-pips +
  Barou devour + Phase S F19 variance.
- `sim/core/provenance_pips.py` — added `regime_fit_from_atr` +
  `isagi_metavision_lift` helpers, 5 new tests.
- `sim/core/lot_intent.py` — `analytical_precision` and
  `confluence_only` playstyles switched off `kelly_lot_intent` (which
  saturated at MIN_LOT floor on the $100 sandbox) onto
  `conviction_scaled_lot_intent` at playstyle-tuned parameters.
- `sim/agents/a01_isagi.py` — metavision lift wired, regime_fit
  dynamic, final_conviction reported in rationale.
- 5 agents (Isagi/Bachira/Rin/Chigiri/Barou) now compute
  `regime_fit = regime_fit_from_atr(prep.bars, i)` instead of the
  0.5 placeholder.

Sim suite: 479 passed / 4 skipped (+10 tests this Phase S: 5
regime_fit_from_atr + 5 isagi_metavision_lift).

## 2026-07-01 late evening — Phase R: full-panel G7 walk-forward rerun COMPLETE

Full 11-year panel (2015-01-01 → 2025-12-31) walk-forward with the
Phase N+O+P wiring fixes live: **5,673 trades across 7 OOS windows**
(vs the 220-trade baseline pre-fix = **+2478 % activity**). Squad
verdict is still `FAIL / PARTIAL / PENDING` — no full 6/6 pass — but
every root cause moved in the intended direction.

Per-agent lift vs baseline (raw verdict:
`reviews/g7_v1_checkpoint_verdict_walk-forward-post-NPO.md`; narrative:
`reviews/2026-07-01_g7_walk_forward_baseline.md`):

| Agent | Bit vector | C1 | C4 | C6 |
|---|---|---|---|---|
| Isagi | `0??100` | 0.322 (3/7, +trades from 0) | 6571 | 0.073 |
| Bachira | `1??100` | 0.374 (7/7) | 14551 | **0.133 PASS** |
| Rin | `1??100` | **0.422 (6/7)** | 1494 | 0.086 |
| Chigiri | `0??100` | 0.265 fail | 992 | **0.155 PASS** |
| Reo | **`1??111`** (all C1/C4/C5/C6 waived) | — | — | — |
| Nagi | `1??100` | 0.392 (5/7) | 658 | 0.000 |
| Barou | `1??100` | **0.299 (5/7, +trades from 0)** | 4576 | 0.113 |
| Kunigami | **`1??111`** (all C1/C4/C5/C6 waived) | — | — | — |

**Residual: C5 (F19 lot dispersion) universally 0-0.05.** Wiring is
live and inputs vary, but the actual conviction→lot map produced by
`agent_lot_intent()` is too flat — trades cluster near the min-lot
clamp. Amplifying the playstyle bands is Phase S (parameter tuning,
not wiring).

**Amendments landed with this Phase R:**

- Doctrine §3.10a — structural-falsifier waiver class extended from
  Reo to include Kunigami (defensive-observer canon role, publish-only).
- G7 PROTOCOL §11.1–11.5 — dated amendments covering the Kunigami
  waiver, the Phase N aggregator tier-anchor, Phase O F21 workspace
  reads for 5 agents, Phase P provenance-pips helper, and the Barou
  devour bump.
- `run_g7_v1_checkpoint_gate.py` walk-forward CLI auto-overrides the
  dry-run panel defaults (2023-2024) to G7 defaults (2015-2025) when
  the caller passes `--mode walk-forward` — fixed a launch-time bug
  where the first Phase-R rerun produced 0 windows.

Research workshop for the M001 multi-agent ensemble AND for the six single-
alpha studies gating live-agent improvements (E011-E016). Production
execution lives in `multi-pair-trading-agent`; lab experiments never
auto-change live params. Parquet cache:
`PYTHONPATH=../multi-pair-trading-agent:.` (no duplicate data).
Index: `EXPERIMENTS.md` · Rules: `PROTOCOL_DISCIPLINE.md` · M001 program:
`programs/M001_multi_agent_ensemble/` (branch `multi-agent-ensemble`).

## 2026-07-01 evening — Phase N + O + P wiring fixes shipped

Post-G7-walk-forward-baseline diagnosis identified three orthogonal
wiring gaps causing FAIL/PARTIAL/PENDING. All three fixed and smoke-
verified in one session:

- **Phase N — Aggregator tier-anchor + slot-fallback + Barou lift.**
  Added `agent_tier: int = 2` to `AgentProposal`; sort key changed to
  `(-adjusted_conviction, agent_tier, agent_id)` with
  `TIER_BIAS = 0.05` so Isagi wins same-conviction tiebreaks over
  tier-2 peers. Aggregator now exposes `ranked_by_symbol` and the
  sentinel loop cedes a blocked winner's slot to the next-ranked
  proposal. Barou devour lift 0.10 → 0.20 and Isagi-disagreement floor
  0.7 → 0.5. **Result: Isagi 0 → 25 trades, Barou 0 → 8 trades on the
  2024 OOS single-window smoke.**
- **Phase O — F21 workspace reads wired into 5 agents.** Isagi
  (metavision peer scan), Rin (Isagi frame alignment), Chigiri (Isagi
  momentum confluence), Nagi (workspace peer count mirror), Barou
  (Isagi USDCAD direction). Each now carries an explicit
  `workspace: WorkspaceSnapshot | None = None` kwarg and calls
  `snapshot.peer_thoughts(...)` or `snapshot.latest_by_agent(...)`.
  **Result: C4 chemistry lit for every non-Bachira/non-Reo/non-Kunigami
  proposer — 1177 (Isagi), 211 (Rin), 154 (Chigiri), 135 (Nagi), 905
  (Barou), Bachira 2772 in the single window.**
- **Phase P — Provenance-pips helper + Rin variable lift.** New
  `sim/core/provenance_pips.py` with `atr_pips_at` and
  `swing_pips_from_bars` (Wilder ATR + lookback-range swing). Every
  proposer with bar access now stamps `atr_pips` + `h1_swing_pips` on
  `proposal.rationale` via `stamp_provenance_pips(...)`. Rin's
  `PRECISION_LIFT` became a stop-tightness function (0.15 at floor →
  0.05 at 60 pips) so per-trade conviction varies. **Result: three C6
  passes (Bachira 0.18, Chigiri 0.19, Barou 0.16); Rin C6 = 0.088 (one
  hair short); Isagi C6 = 0.053. C5 largely unchanged because playstyle
  lot formulas still Kelly-saturate at MIN_LOT — needs follow-up.**

Smoke verdict (`reviews/g7_v1_checkpoint_verdict_dry-run-2024-post-NPO.md`,
75 seconds runtime on 2024 OOS single window):

| Agent | Pre-fix (walk-forward-baseline mean) | Post-fix (2024 dry-run) |
|---|---|---|
| Isagi | 0 trades / C1=0.000 / C4=0 | **25 trades** / C1=0.227 / **C4=1177** |
| Bachira | C1=0.375 / C4=14551 / C6=0 | C1=0.339 / C4=2772 / **C6=0.179 PASS** |
| Rin | C1=0.393 / C4=0 / C6=0 | **C1=0.531** / **C4=211** / C6=0.088 |
| Chigiri | **C1=0.268 fail** / C4=0 / C6=0 | **C1=0.311 PASS** / **C4=154** / **C6=0.192 PASS** |
| Nagi | C1=0.385 / C4=0 | C1=0.106 (single-window variance) / **C4=135** |
| Barou | 0 trades / C4=0 | **8 trades** / **C4=905** / **C6=0.160 PASS** |
| Kunigami | 0 by design | 0 by design (needs C1/C4/C5/C6 waiver) |
| Reo | waived C1/C4 | waived C1/C4 |

Sim suite: **469 passing + 4 skipped** (this session added 4 aggregator
tier-anchor + 9 provenance-pips + 2 slot-fallback = 15 new tests).

Kunigami-waiver amendment (parallel to Reo's copier waiver) is the
last doctrine ticket before the full-panel G7 walk-forward rerun that
will produce the formal post-fix verdict.

## 2026-07-01 v1/v2 reframe — closed same day

User directive during Phase 6 completion: "each agent should operate on
equal versionings. isagi, rin, backira, kunigami should all have complete
version 1s that are all efficient in one way or the other or in their
playstyles before movign to creating a version 2." **v1 = squad-tested
checkpoint** (not initial implementation); **v2 = architectural upgrade
that trumps v1**. This retroactively reclassified 6 prior "v2" labels as
"v1 mechanic iterations" and introduced **G7 v1-checkpoint gate** as a
squad-level pre-condition on ANY v2 authorisation. Session shipped:

- **Doctrine v0.5 + roster v0.8:** preamble + §3.11.5 versioning
  discipline + §4.1a F19/F20/F21 primitives.
- **G7 pre-registered protocol** at
  `programs/M001_multi_agent_ensemble/experiments/G7_v1_checkpoint_gate/PROTOCOL.md`.
- **6 evolution-ledger RELABEL-2026-07-01 rows** (Barou / Bachira / Rin /
  Chigiri / Reo / Kunigami).
- **F19 `lot_intent` + F20 `risk_intent` + F21 `read_workspace`** as
  first-class BaseStriker primitives with playstyle dispatch. Fixed-lot
  = 0.1 is now the "unknown-playstyle default", not a global rule.
- **All 8 v1 agents wired** with playstyle + tier (Isagi tier-1
  conservative_metavision, Bachira rebel_tight, Rin analytical_precision,
  Chigiri speed_momentum, Reo copier_hrp, Nagi confluence_only, Barou
  solo_king, Kunigami defensive).
- **Engine threads F21 workspace snapshot** into `intend()` per tick;
  Bachira consumes Isagi peer confluence (+0.05 lift). All other agents
  absorb the kwarg via `**_kwargs` (silent, but participating in
  workspace publish).
- **G7 harness scaffold** at
  `sim/scoring/run_g7_v1_checkpoint_gate.py`: C1/C5/C6 computed live,
  C2/C3/C4 stubbed PENDING full 7-window batch run + workspace-threaded
  driver.
- **Sentinel Phi4.1 physical rerun COMPLETED (2026-07-01T16:54 UTC+1)**
  (`--sentinel-blocks --tag physical`, 2h 3min runtime): **squad TQS
  0.358 vs Isagi-alone 0.317, ratio 1.13x = PASS** (audit-mode was
  0.2922 TQS = 0.92x FAIL). Δ = +0.066 TQS (+22.6 % relative) AND
  +1,522 trades (+41 %) -- Sentinel enforcement flips the sealed FAIL
  to a PASS both by adding trades AND raising per-trade quality.
  Per-agent Δ: Bachira 0.308→0.389, Rin 0.277→0.399, Nagi 0.349→0.439,
  Chigiri 0.229→0.253 (fewer trades but higher quality). Isagi + Barou
  + Reo + Kunigami stay at 0 trades in both modes -- structural
  crowding-out is confirmed Sentinel-independent. Side-by-side report
  landed at `reviews/phi41_sentinel_sidebyside.md`. **Sealed audit
  verdict at 0.2922 TQS remains LOCKED** per §11 verdict-comparator
  discipline; physical run is a diagnostic overlay. Follow-up: parse
  the 15,350-event sentinel_log JSONL into per-rule R1/R3/R5/R6 counts.
- **Phase M news calendar scaffolding LANDED (2026-07-01 pm):** user
  authorised parallel scaffolding while G7 walk-forward compute job
  runs. Three new modules under `sim/regime/`
  (`news_calendar.py` -- Φ5 schema + adapter,
  `news_calendar_sources.py` -- DK/FF/FRED/TE fallback stubs,
  `news_windowing.py` -- per-agent TF windowing helper).
  `validate_real.load_news_calendar` rewritten as a 5-line proxy to
  the new adapter (spec §5.2). 3 committed parquet fixtures under
  `sim/tests/fixtures/news_calendar/` (dk_2024_sample 20 rows +
  ff_2024_sample 5 rows + dk_2024_USD 32 real events from BLS/Fed
  release schedules). 49 tests green. Live-HTTP fetch scripts
  (backfill/update/audit) deferred to next session -- adapter is
  usable today with any archive that follows the parquet layout.

**Statistical honesty flags:** no verdict retuning; all reclassifications
appended to `evolution_ledger.md` as new rows (never edits); G7 pre-reg
requires §11 amendment before any threshold change; 458 sim tests
passing + 4 slow skips (this session added 62 tests over the earlier
396 baseline: 49 news calendar + windowing + 13 workspace threading).

## 2026-07-01 research-pipeline sweep (E011-E016) — closed

| ID | Verdict | Registry |
|---|---|---|
| E011 small-stop subset expectancy | `stopped_at_stage_1` | Kills E012 |
| E012 pending-limit entry | `cancelled_dep_failed` | -- |
| E013 safety-layer contribution | `combined_alive` Δ+0.80 Sharpe; `wick_alive` Δ+0.75; BE `not_alive`; PLG `plg_earns_keep` (protocol's own label for "PLG is expensive") | `experiments/E013_.../REPORT.md` |
| E014 quality-score entry gate | `parked_low_yield` (12 % vol) | Kills E015 + E016 |
| E015 / E016 | `cancelled_dep_failed` | -- |

**Follow-up backlog:** PLG cooldown / streak-halt tuning (E017 pre-reg
required). Do NOT tweak `PostLossGuard` constants without a fresh
protocol.

## 1) What is built and working

**Lab Phase 1 (E001–E007) — closed.** Tag `lab-phase-1-closed`. E004
walk-forward 7/7 OOS (median +11.34 pips/trade) deployed. Audit:
`audits/2026-06-24_E001-E007_audit.md`.

**M001 — Φ3 PASS · Φ4 FAIL · Φ4.1 FAIL · doctrine v0.5 / roster v0.8.**

- **Φ3 v1 — A1 Isagi v1 wrapper PASS:** +11.04 pips/trade vs Sae +11.34
  (Δ −2.7 %, ±5 % band); 7/7 OOS positive.
- **Φ4 v1 — 4-agent squad FAIL @ 0.98× Isagi-alone TQS.**
- **Φ4.1 v1 — 8-agent squad FAIL @ 0.92×** (squad TQS 0.2922, Isagi 0.3175).
  Predicate starvation CONFIRMED + FIXED (Nagi 0 → 34,302 confluence-
  firing thoughts). Structural crowding-out uncovered — Isagi 0 trades,
  Barou 0 trades. `reviews/phi41_squad_v1{,_addendum,_crossstat_addendum}.md`.
- **Isagi v1→v2 arc FAIL** (2026-06-24). v1 canonical; v2 archived.
- **Regime redesign:** `vol_spike` + `news` RETIRED; live-classes-only
  macro F1 = 0.971.
- **Methodology lock:** `docs/methodology/gate_verdict_registry.md` v0.1;
  `07-research-standards.md` v0.4 §11.
- **Φ4.2 Sentinel R1–R6 wired** (audit-only in Φ4.1 replay; physical in
  Φ5 harness). Un-blocks Kunigami v2-mechanic + Φ5 Arm 4.
- **Φ5 aggregator PARTIAL VERDICT (2026-07-01):**
  - Arm 0 control 0.2922 (matches Φ4.1 exactly).
  - Arm 1 HRP 0.2941 (Δ+0.0019) — null post-hoc; needs variable lot sizes.
  - Arm 2 TQS floor 0.3109 (Δ+0.0187) — meaningful lift, misses
    Δ ≥ 0.020 by 0.0013.
  - Arms 3/4/5 REQUIRES_RESIM.
- **v1/v2 reframe (2026-07-01):** doctrine v0.5, roster v0.8, G7 gate
  pre-registered. F19/F20/F21 primitives on BaseStriker + all 8 agents.
  Engine threads workspace. Bachira consumes Isagi peer confluence.

**Architectural insight (Φ4.1 + Isagi v2 + Φ5 Arm 2 + v1/v2 reframe
converged):** the single-position-per-symbol queue with conviction-only
ranking is one lever; agent-side chemistry (F19/F20/F21) is the other.
The v1/v2 reframe formalises the mandate: prove squad chemistry via G7
before authorising any single-agent v2 arc.

Tests: **458 sim passing** + 4 slow skips (this session added 21 F21 +
48 F19/F20 + 34 wiring + 10 Bachira chemistry + 21 G7 criteria + 13
workspace threading + 49 news calendar / windowing = 196 new tests).

## 2) Key file paths

| Area | Files |
|---|---|
| Registry | `EXPERIMENTS.md`, `DATA_LEDGER.md`, `PROTOCOL_DISCIPLINE.md` |
| Methodology | `docs/methodology/*.md` |
| M001 doctrine | `programs/M001_multi_agent_ensemble/00`–`09` (v0.5) + `README.md` |
| M001 roster | `05-agent-roster-v0.md` (v0.8, includes §1.0 v1 checkpoint status) |
| M001 sim | `programs/M001_multi_agent_ensemble/sim/{core,regime,scoring,roster,agents,dashboard,tests}/` |
| M001 core primitives | `sim/core/{lot_intent,risk_intent,reasoning_workspace}.py` (F19/F20/F21) |
| M001 news calendar | `sim/regime/{news_calendar,news_calendar_sources,news_windowing}.py` + `sim/tests/fixtures/news_calendar/*.parquet` (Phase M scaffolding) |
| M001 agents | `sim/agents/a0{1..7,10}_*.py` (playstyle + tier wired) |
| M001 harnesses | `sim/scoring/run_isagi_phi3_gate.py` · `run_phi{4,41}_squad_gate.py` · `run_phi5_aggregator_gate.py` · `run_g7_v1_checkpoint_gate.py` (new) |
| M001 aggregator arms | `sim/core/aggregator_arms/*.py` |
| M001 Sentinel | `sim/core/sentinel.py` (R1-R6) + `sim/tests/test_sentinel_wired.py` |
| M001 reviews | `reviews/phi{3,4,41,5}_*.md` + `isagi_v2_arc.md` + `evolution_ledger.md` |
| M001 G7 pre-reg | `experiments/G7_v1_checkpoint_gate/PROTOCOL.md` |
| M001 v2 backlog | `reviews/v2_arc_backlog_resolution_{2026-06-25,round2_2026-06-30}.md` (both now "v1 mechanic iterations pending G7" per §3.11.5) |
| News calendar (DEFERRED beyond G7) | `data/news_calendar/README.md` + `specs/news_calendar_wiring{,_DECISION_TREE}.md` |
| E011-E016 protocols + reports | `experiments/E01[1-6]_.../PROTOCOL.md` + `E01{1,3,4}_.../REPORT.md` |

`PYTHONPATH=../multi-pair-trading-agent:. M001_PRODUCTION_REPO=../multi-pair-trading-agent ../multi-pair-trading-agent/.venv/bin/python -m pytest -q`

## 3) Next immediate goal

**Phase 6 v1/v2 reframe — DELIVERED this session.** All 8 phases (A–H)
of the 2026-07-01 plan shipped. Squad now has F19/F20/F21 primitives
wired end-to-end; G7 harness scaffolded with C1/C5/C6 live + C2/C3/C4
stubbed. Bachira-Isagi flagship chemistry landed with 10 contract tests.
Doctrine v0.5, roster v0.8, evolution ledger updated with 6 RELABEL rows.

**Next immediate goal — sequenced from Phase 3 running (2026-07-03 04:07 UTC):**

1. **Phase 3 C2/C3 leave-one-out compute (RUNNING, ETA ~08:30 UTC).**
   Job PID 27370 launched 03:31 UTC, replay 1/8 at 95%, ~4.7 h more
   wall-clock. Heartbeat monitor v2.1 active with 60 s sampling.
   When done: aggregate on disk → `reviews/g7_c2_c3_verdict_post-V.{md,json}`
   → amend G7 verdict registry rows for post-V + post-F22. THEN
   promote `experiments/phase_v_iterate/PROTOCOL.md` from
   `template-pending-c2c3` to `pre-registered` by filling in the
   TBD cells and picking exactly ONE arm per the mechanic-vs-
   precondition table (already locked in the template).
2. **Phase 6a-v2 news fetcher rewrite** (blocked, needs a
   working-endpoint discovery). Options in
   `data/news_calendar/STOP_NOTICE.md`: headless-browser reverse
   of widgets.dukascopy.com, or switch primary to FF
   (`nfs.faireconomy.media`) / TE (paid). The Phase 6b writer +
   manifest + CLI (`1b6848c`) will consume whatever new fetcher
   lands unchanged.
3. **Phase 5 Φ5 HRP compute-side re-sim (Phase 6e proper).** Input
   builder side landed (`bafd01b`); the actual walk-forward re-sim
   against F19-wired squad still waits on Phase 3 per Amendment
   §11.3 follow-up ordering.
4. **Phase V-iterate arm implementation + walk-forward-post-V-iterate.**
   Blocked on Phase 3 verdict — arm choice is deterministic from
   C2/C3 per the template's precondition table.
5. **Phase 7 player scouting reports.** Blocked on 3 + 4 completing.

**Backlog (needs pre-reg before touching any parameter):**

1. **Phase V-iterate** (if C2/C3 shows Chigiri/Barou contribute
   counterfactual alpha). Options A/B/C from postmortem; C
   (peer-YIELD analogous to Rin) is the cleanest analogue.
2. **PLG cooldown / streak-halt tuning** (E017 pre-reg required).
3. **E014 wider-grid amendment** (θ ∈ {20, 30, 40, 50}). Blocked by
   §Amendments discipline in `E014_.../PROTOCOL.md`.

**Backlog (needs pre-reg before touching any parameter):**

1. **PLG cooldown / streak-halt tuning** (E017 pre-reg required).
2. **E014 wider-grid amendment** (θ ∈ {20, 30, 40, 50}). Blocked by
   §Amendments discipline in `E014_.../PROTOCOL.md`.

**Un-deferred as of 2026-07-03:** News calendar wiring (Phase 6) is
now the highest-priority next task per Phase V postmortem sequencing
above.

**Still deferred beyond G7:**

1. **v2 agent implementations** (Barou hybrid, Bachira/Rin/Chigiri/Reo
   refinements). Reclassified as v1 mechanic iterations per §3.11.5;
   no v2 arc authorised until G7 PASS.

**Pending user-only ops (not delegatable):** hand-label ~30 regime
disagreements via `sim/regime/label_disagreements.py`; VM-side friction
calibration via `scripts/vm_calibrate_friction.py`.

**Parked (do NOT start without discussion):** A8 Yukimiya / A9 Aoshi
v1 builds (no telemetry; round-3 after G7); E009 cross-family;
`output/` reorganisation.

Honesty rules: `PROTOCOL_DISCIPLINE.md`. M001 gates: `09` §1.5. Verdict-
comparator discipline: `07-research-standards.md` §11. v1/v2 discipline:
`06-blue-lock-doctrine.md` §3.11.5.
