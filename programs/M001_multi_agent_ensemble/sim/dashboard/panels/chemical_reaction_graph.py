"""Panel §2.3 — chemical-reaction graph."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


def render(run_dir=None) -> None:
    st.subheader("§2.3 Chemical-reaction graph")
    st.caption(
        "Falsification question: do confluence boosts predict TQS uplift? "
        "(09 §1.9 — disconfirms if reacted trades have TQS <= non-reacted "
        "with overlapping CI.)"
    )

    df = loader.load_chemical_reactions(run_dir)
    if df.empty:
        st.info(
            "No chemical reactions logged yet. F11 (coordinate overlap) "
            "or F11 v0.4 (thought-resonance) triggers haven't fired in this "
            "run window."
        )
        st.caption(
            "Phi2.5 renders the panel surface; Phi3 lands the network plot "
            "(networkx / pyvis) once the Aggregator wires the "
            "`chemical_reactions.jsonl` stream."
        )
        return

    st.dataframe(df.head(50), hide_index=True, use_container_width=True)
    # Lightweight matrix view of agent-pair co-occurrence as a placeholder
    # graph until Phi3 lands the proper network visualisation.
    if {"agent_a", "agent_b"} <= set(df.columns):
        counts = (
            df.groupby(["agent_a", "agent_b"])
            .size()
            .reset_index(name="reactions")
            .sort_values("reactions", ascending=False)
            .head(20)
        )
        st.markdown("**Top reacting pairs (last window)**")
        st.dataframe(counts, hide_index=True, use_container_width=True)
