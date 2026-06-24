"""Panel §2.4 — human-vs-squad scoreboard."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


def render(run_dir=None) -> None:
    st.subheader("§2.4 Squad vs human + Sae scoreboard")
    st.caption(
        "Falsification question: does the squad beat the human + Sae cohort? "
        "(09 §1.9 — disconfirms if 12-week rolling TQS below Kaiser *and* "
        "Sae.)"
    )

    df = loader.load_scoreboard(run_dir)
    if df.empty:
        st.info("No opponent submissions yet.")
        return
    st.dataframe(df, hide_index=True, use_container_width=True)
    st.caption(
        "Loki-distance must stay ≥ 0.40 (`07-research-standards.md` §4.2) "
        "— behaviourally distant from the adversary's worst habit, not "
        "trying to beat it on PnL."
    )
