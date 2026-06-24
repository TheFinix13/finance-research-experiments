"""Panel §2.6 — per-trade explainability (drill-in)."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


def render(run_dir=None) -> None:
    st.subheader("§2.6 Per-trade explainability")
    st.caption(
        "Falsification question: can we replay this trade from artefacts? "
        "(09 §1.9 — disconfirms if any Thought, Proposal, or manifest "
        "join is missing on `trade_id`.)"
    )

    intents = loader.load_intents(run_dir)
    if intents.empty:
        st.info(
            "No trade intents in this run. The aggregator emits intents "
            "only when an agent's `intend()` produces a Proposal."
        )
        return

    choice = st.selectbox(
        "Pick a trade to explain",
        intents["intent_id"].tolist(),
    )
    if not choice:
        return
    row = intents[intents["intent_id"] == choice].iloc[0]
    st.markdown(
        f"**`{row['symbol']}` · `{row['direction']}` · entry {row['entry']} "
        f"· stop {row['stop']} · size {row['size']}**"
    )

    # Join: contributing thoughts.
    thoughts = loader.load_thoughts(run_dir)
    if "contributing_thought_ids" in row and len(row["contributing_thought_ids"]):
        ids = set(row["contributing_thought_ids"])
        children = thoughts[thoughts["thought_id"].isin(ids)] if not thoughts.empty else thoughts
        st.markdown("**Contributing Thoughts**")
        if not children.empty:
            st.dataframe(
                children[[
                    "tick_id", "agent_id", "narrative", "confidence_in_thought",
                ]],
                hide_index=True,
                use_container_width=True,
            )

    # Join: Sentinel decisions for this intent.
    sentinel = loader.load_sentinel_log(run_dir)
    rel = sentinel[sentinel["intent_id"] == choice] if not sentinel.empty else sentinel
    st.markdown("**Sentinel checks (R1–R5 + external)**")
    if rel.empty:
        st.caption("No Sentinel log rows for this intent (allowed by all checks).")
    else:
        st.dataframe(rel, hide_index=True, use_container_width=True)
