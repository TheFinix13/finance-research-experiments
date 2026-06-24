# 08 — Dashboard Spec (Streamlit v0)

**Status:** `DRAFT v0.1` — 2026-06-24. v0.2-era new doc; landed
together with the doctrine v0.2 amendments. Owns the human-facing
surface of the M001 ensemble: panel inventory, verdict translation,
data-plane bindings, auth, and the implementation skeleton.

---

## §1. Purpose

The dashboard is the **human surface** for the ensemble:

- Renders the Thought Ledger, Proposal Bus, and trade journal so the
  human can audit any decision.
- Renders per-agent KPIs (TQS, IR, ΔInfo, Pain Ratio, regime-conditional
  buckets) so the human can see who is earning their weight.
- Renders the chemical-reaction graph so the human can see which
  agents resonate productively.
- Renders the F14 adversarial scoreboard (Kaiser / Loki / Median /
  Random / Sae-frozen + Sae-composite) so the human can see whether
  the squad is beating the cohort the doctrine commits it to beat.
- Renders the Sentinel state so the human can see what is currently
  blocking trades and why.

The dashboard is **read-only at Φ2.5**. No buttons that emit orders.
No buttons that change agent parameters. Pure observability.

Trajectory pinned to `07-research-standards.md` §8:

- **Φ2.5 (now):** Streamlit running locally, reads JSONL + parquet
  directly, no autorefresh.
- **Φ4 (fusion sweep):** Streamlit + autorefresh, reads from the
  SQLite shadow index built on top of the JSONL.
- **Φ6+ (live shadow):** either small React/Svelte frontend on
  WebSocket + FastAPI sidecar, *or* Grafana on the SQL store. Single
  choice when we get there.

---

## §2. Panel inventory

Six panels for v0. Each panel has a defined data source, refresh
cadence, filter set, and rendering primitive. The implementation
skeleton (§7) wires each panel to its source.

### §2.1 League table — per-agent KPIs

The headline panel. One row per agent in the active roster.

**Columns:**

| Column | Source | Notes |
|---|---|---|
| Agent (icon + canon player) | `roster.yaml` | Canon role icon for at-a-glance identity (Isagi, Bachira, …) |
| Tier (T1 / T2 / T3) | `kpis/<agent_id>/<week>.json:tier` | Computed from F17 ΔInfo; coloured pill |
| TQS (pooled median, IQR) | F12 in `04-quant-foundations.md`; per-trade journal | Sortable; default sort key |
| IR vs squad | F12-derived; squad TQS time-series regressed on this agent's | Effectively the F-information-ratio-form ego from doctrine §3.1.b |
| ΔInfo (point + 95% CI) | F17 in `04-quant-foundations.md` | Below-zero coloured red |
| Pain Ratio | TQS / max-DD over trailing window | Sortable secondary metric |
| Regime buckets (4 sparklines) | F18 regime-conditional KPI vectors | Tiny inline TQS-by-regime sparkline so the bucket-dominance story is visible without a click |
| Last verdict | Internal four-tier registry | Translated to Blue Lock UI vocabulary per §3 |
| Recent proposals (24h) | Proposal Bus JSONL | Rate cap from Sentinel R3 (3/day) flagged when exceeded |

**Refresh cadence:** on user interaction (Φ2.5); autorefresh every
60 s at Φ4.

**Filters:** by tier, by regime-bucket dominance, by verdict.

### §2.2 Live thought feed

The Thought Ledger rendered as a chronological feed.

**Row content per Thought:**

- Timestamp + tick_id
- Agent badge (icon + tier pill)
- Symbol
- Narrative text (1–3 sentences)
- Tag chips (one chip per tag in `Thought.tags`)
- Confidence bar (`Thought.confidence_in_thought`)
- Optional coordinate preview (mini-chart band if `Thought.coordinate
  is not None`)
- References (clickable link to each parent Thought via
  `Thought.references`)

**Filters:** by agent, by tag, by symbol, by date range, by
confidence floor, by "has coordinate" / "observation only".

**Refresh cadence:** on user interaction (Φ2.5).

**Data source:** `output/<run>/thought_ledger/<agent_id>/<UTC-date>.jsonl`
(per `07-research-standards.md` §8).

### §2.3 Chemical-reaction graph

A network plot showing which agent-pairs (and triples) have
reacted recently. v0.2 chemical-reactions fire on either Coordinate
overlap (F13) OR Thought-tag resonance (F11 v0.4 extension); the
graph renders both kinds.

**Nodes:** agents. Size = recent (7-day) emit-rate of triggering
artefact (Coordinate or Thought with `confidence_in_thought ≥ 0.7`).
Colour = current tier.

**Edges:** chemical-reaction events. Width = reaction count over
trailing window. Colour = trigger type (coordinate-overlap = blue;
tag-resonance = orange; both = green).

**Hover:** edge tooltip lists the most recent N reactions on this
pair with their `tick_id`, symbol, fused conviction (F11), and
realised TQS (if the trade has resolved).

**Refresh cadence:** on user interaction (Φ2.5).

**Data source:** chemical-reaction events written to
`output/<run>/chemical_reactions.jsonl` by the Aggregator.

### §2.4 Human-vs-squad scoreboard

The F14 head-to-head rendering. One row per opponent over the
trailing 12-week window (the rolling-season window).

**Columns:**

| Column | Opponent | Source |
|---|---|---|
| TQS (mean) | Kaiser, Loki, Median, Random, Sae-frozen, Sae-composite | F14 + F16; `opponents/<opp>.jsonl` |
| PnL_HH gap | mean squad TQS − mean opponent TQS | F14 M1 |
| Coverage | for Kaiser/Loki only | F14 M2 |
| Counter | for Kaiser/Loki only | F14 M3 (reported, not gated) |
| Loki-distance | for Loki only | `07-research-standards.md` §4.2 (must stay ≥ 0.40) |
| Gate verdict | per opponent | MUST-beat / SHOULD-approach / MUST-stay-distant |

The "Sae" row is rendered twice: **Sae-frozen** (heritage floor, per
research-standards §4.2) and **Sae-composite** (F16). The dashboard
must beat both.

**Refresh cadence:** weekly (on opponent submission); on user
interaction in-between.

**Data source:** `opponents/<opponent_id>.jsonl` + the squad's
trade journal.

### §2.5 Sentinel state

Live state of the Sentinel. Rendered as a status board.

**Top row (current state):**

- Current equity ($)
- Margin level (%)
- Open positions (count + per-position TQS-in-progress)
- Current per-trade risk cap (R1 floor reminder: ~5 % equity)
- Loss-streak status (count of consecutive losses; R5 dampener
  countdown if active)
- Risk-scale multiplier currently applied (1.00 unless R5 active)

**Trigger log (recent 24h):**

| Rule | When | What blocked | Why |
|---|---|---|---|
| R1 | timestamp | OrderIntent payload (agent_id, symbol, direction, intended_size, SL_distance) | "SL distance × 0.01 lot = $X > 5 % equity = $Y" |
| R2 | timestamp | rounding event (intended fractional lot, rounded discrete lot) | "0.017 lot rounded down to 0.01 (rule R2)" |
| R3 | timestamp | agent + proposal count | "Agent X emitted N=4 proposals today, > 3/day threshold" |
| R4 | timestamp | agent + intended-weight | "Agent X would have received 42 % of risk budget; capped at 40 %" |
| R5 | timestamp | trigger event | "3 consecutive losses on (agent_id, symbol); 50 % risk scale for next 24h" |
| §4.2 external | timestamp | trigger | ρ-jump / spread / calendar / DXY (per doctrine §4.2) |

**Refresh cadence:** every tick (Φ2.5 reloads on interaction; Φ4+
autorefresh).

**Data source:** `output/<run>/sentinel_log.jsonl`.

### §2.6 Per-trade explainability

Drill-in panel for any `trade_id`. The most important panel for
human audit.

**For any OrderIntent / closed trade:**

- The contributing Thoughts (per-agent, sorted by `tick_id`), with
  full narrative text and tag chips.
- The Coordinate(s) that were active at trigger time, with overlap
  scores (F13).
- The Chemical Reactions that fired (which agents, trigger type,
  combined conviction F11, size multiplier).
- The Aggregator's fused decision (the OrderIntent), with the
  per-rule trace (rule 1 / 2 / 3 from `03-architecture-v0-sketch.md`
  §5).
- The Sentinel checks (R1–R5 + §4.2 triggers) the OrderIntent
  passed through, in order.
- The realised trade (entry, exits per ladder rung, MFE/MAE, hold
  time, TQS components).
- A vertical timeline rendering the above as a story: observation →
  intention → fusion → Sentinel → execution → outcome.

This panel is what makes the late-fusion architecture **auditable**.
Without it, the doctrine's "every decision is reproducible from the
ledger" commitment is wishful thinking.

**Refresh cadence:** on user interaction (drill-in panel).

**Data source:** `trade_id` joins across Thought Ledger, Coordinates,
Chemical Reactions, Proposal Bus, Sentinel log, and trade journal.

---

## §3. Verdict vocabulary translation

The internal four-tier verdict registry from
`07-research-standards.md` §10.4 translates one-to-one to the Blue
Lock vocabulary for the human-facing dashboard. The mapping below is
the **single source of truth** for the rendering layer; any deviation
is a display bug.

| Internal (canonical evidence vocabulary) | Blue Lock (UI / human comms) | Meaning |
|---|---|---|
| `alive` | `starter` | In the deployment XI. The agent has earned a starting slot. |
| `parked_weak_effect` | `sub` | Bench, watching the ΔInfo trend; one swing away from being benched or recalled. |
| `parked_insufficient_n` | `benched` | No data yet to judge; held in reserve until n_trades crosses the floor. |
| `dead` | `cut` | Dropped from the roster; the doctrine asks: do not redeploy. |

The internal vocabulary is what the per-agent reviews under
`programs/M001_*/reviews/` write. The UI vocabulary is what the
human sees. The Aggregator and the F17/F14 harness consume the
internal vocabulary directly; only the rendering layer uses the
translation.

---

## §4. Tier display

Each agent's badge renders four pieces of context at a glance:

- **Canon role icon.** Per the roster (`05-agent-roster-v0.md` §3):
  Isagi metavision eye, Bachira mask, Rin sword, Chigiri lightning,
  Reo chameleon, Nagi yawn, Barou crown, Yukimiya glove, Aoshi
  berserker mark, Kunigami bandage. Custom SVG set under
  `dashboard/assets/`.
- **Tier pill (T1 / T2 / T3).** Coloured per tier. Tier 1 is reserved
  for non-agent consumers (dashboard / Aggregator / harness) so in
  practice agents show T2 (informed, reads ledger) or T3
  (information-isolated). TBD agents pre-F17 show a grey "TBD"
  pill.
- **Regime bucket dominance.** A small 4-cell grid coloured by F18
  bucket-dominance: green for the agent's strongest bucket, grey for
  others. Hover shows TQS per bucket.
- **Last verdict.** Per §3, the Blue Lock vocabulary.

Tap the badge → opens the per-agent panel (§2.6-style drill-in,
filtered to this agent's full history).

---

## §5. Data plane

The dashboard's data bindings track the Φ2.5 → Φ4 → Φ6+ trajectory
defined in `07-research-standards.md` §8 and replicated in
`03-architecture-v0-sketch.md` §11.

| Phase | Data source | Implementation |
|---|---|---|
| Φ2.5 (now) | JSONL files in `output/<run>/...` directly | Each panel reads the relevant JSONL(s) at page-render time; no caching beyond Streamlit's `@st.cache_data` on file-mtime keyed reads |
| Φ4 | SQLite shadow index rebuilt from JSONLs on demand | Each panel reads from SQLite via a thin SQLAlchemy session; autorefresh every 60 s |
| Φ6+ | WebSocket sidecar pushing new entries + FastAPI for historical reads | Either a React/Svelte rewrite, or a Grafana dashboards-as-code migration; the Φ2.5 Streamlit code is retired at this point |

JSONL append-only is the through-line. Streamlit panels at Φ2.5
must not assume any file is immutable across reads, but **must
assume any file is append-only** — entries do not get rewritten or
deleted. This shapes the caching strategy (`mtime + size` as the
cache key works; `mtime` alone does not).

---

## §6. Auth

Local-only in v0. No auth.

- The Streamlit server binds **only to `127.0.0.1`** (loopback) by
  default. Explicit configuration step required to bind to any
  other interface.
- No login screen, no token, no session management.
- Threat model: the laptop is the trust boundary. If someone else is
  on this laptop, the dashboard is the least of our worries.

Φ4+: when the dashboard hits the SQLite shadow on a shared dev box,
add HTTP Basic auth gated by a shared secret in a local env file.
Φ6+: when the dashboard goes to a real frontend, real auth (OIDC
or equivalent) is required. The decision lives in the Φ6 program
review.

---

## §7. Implementation skeleton

~200 LoC Streamlit app outline. Section-by-section sketch only —
this is a spec, not the implementation.

**File layout (Φ2.5):**

```
programs/M001_multi_agent_ensemble/sim/dashboard/
  app.py              # Streamlit entry point; ~50 LoC routing
  panels/
    league_table.py   # §2.1; ~40 LoC
    thought_feed.py   # §2.2; ~30 LoC
    chem_graph.py     # §2.3; ~40 LoC (networkx + pyvis or st_graph)
    scoreboard.py     # §2.4; ~30 LoC
    sentinel.py       # §2.5; ~25 LoC
    drill_in.py       # §2.6; ~50 LoC (the longest panel)
  readers/
    jsonl.py          # Φ2.5 JSONL readers with mtime-aware caching
    verdict.py        # §3 translation table; single function
  assets/
    canon_icons/      # one SVG per canon role (Isagi, Bachira, ...)
```

**`app.py` skeleton (sketch):**

```python
# pseudocode — not the final implementation
import streamlit as st
from panels import (
    league_table, thought_feed, chem_graph,
    scoreboard, sentinel as sentinel_panel, drill_in,
)

st.set_page_config(page_title="M001 Squad", layout="wide")

# Sidebar — global filters (date range, agent, symbol)
with st.sidebar:
    date_range = st.date_input("Date range", value=(default_start, today))
    agents = st.multiselect("Agents", options=load_roster())
    symbols = st.multiselect("Symbols", options=["EURUSD", "GBPUSD", "USDCAD"])

# Main — six panels via tabs
tabs = st.tabs([
    "League table", "Thought feed", "Chemical reactions",
    "Squad vs human", "Sentinel", "Per-trade",
])
with tabs[0]: league_table.render(date_range, agents, symbols)
with tabs[1]: thought_feed.render(date_range, agents, symbols)
with tabs[2]: chem_graph.render(date_range, agents, symbols)
with tabs[3]: scoreboard.render(date_range)
with tabs[4]: sentinel_panel.render()
with tabs[5]: drill_in.render(trade_id=st.session_state.get("trade_id"))
```

Each panel module exposes one `render(...)` function and one
private `_load(...)` data fetcher. The data fetcher is the only
place that touches the JSONL files at Φ2.5; the SQLite migration
at Φ4 only changes the `readers/` layer, not the panel layer.

**Tests (Φ2.5 minimum):**

- Each `readers/jsonl.py` function has a unit test on a fixture
  JSONL (10–50 rows).
- The §3 verdict translation is a pure-function test.
- No end-to-end dashboard test in Φ2.5 — Streamlit's testing story
  is weak and the dashboard is read-only. Smoke test = "load the
  page, no exceptions on a fresh `output/` with synthetic data."

**Out of scope for v0:**

- Authentication beyond loopback binding.
- Multi-user state.
- Long-running background jobs.
- Push notifications.
- Mobile / responsive layout (laptop-only).

All of the above land at Φ4 or Φ6+ per §5.

---

## §8. Cross-reference

| Dashboard surface | Closes |
|---|---|
| §2.1 League table | Doctrine §3.6 (per-agent KPIs); F12 / F17 / F18 from `04-quant-foundations.md` |
| §2.2 Thought feed | Doctrine §3.8 (Thought Ledger is the canonical evidence stream) |
| §2.3 Chemical-reaction graph | Doctrine §3.3 + F11 (v0.4 extension) + F13 |
| §2.4 Scoreboard | F14 (adversarial validation); standards §4.2 (five-baseline cohort + Frozen-Sae + Sae-composite from F16) |
| §2.5 Sentinel state | Doctrine §4.2 + §4.3; charter §7.3 |
| §2.6 Per-trade explainability | Doctrine commitment 1 (every decision is reproducible from the ledger); §3.8 references field; architecture §5 (Aggregator rules) |
| §3 verdict vocabulary | Standards §10.4 (hybrid verdict registry); the dashboard is the *translation* point between internal and human vocabularies |
| §4 tier display | Doctrine §3.9 (information tier) + §3.10 (canon vs tier) — the badge encodes both layers |
| §5 data plane | Standards §8 + architecture §11 — the dashboard is bound to the same JSONL → SQLite → WebSocket trajectory |
| §6 auth | Standards §3 push policy (local-only is the safe default); revisited at Φ6 |
| §7 skeleton | Architecture §10 (build order) — dashboard panels land in order matching the build order of the agents they render |
| Falsification map | `09-experiment-architecture.md` §1.9 — each panel must answer a disconfirming question |
