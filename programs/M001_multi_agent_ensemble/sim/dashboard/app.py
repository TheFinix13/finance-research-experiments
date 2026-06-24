"""M001 ensemble dashboard — Streamlit v0 entry point.

Run with:

    PYTHONPATH=../multi-pair-trading-agent:. \
      ../multi-pair-trading-agent/.venv/bin/streamlit run \
      programs/M001_multi_agent_ensemble/sim/dashboard/app.py

Phi2.5 binds to `127.0.0.1` only (research-standards §6 / 08 §6). All
six panels in `08-dashboard-spec.md` §2 render with placeholder data
if no replay run is on disk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make `programs.M001_multi_agent_ensemble.sim.*` imports work when
# streamlit launches this file directly.
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader  # noqa: E402
from programs.M001_multi_agent_ensemble.sim.dashboard.panels import (  # noqa: E402
    chemical_reaction_graph,
    league_table,
    scoreboard,
    sentinel_state,
    thought_feed,
    trade_explainer,
)


def main() -> None:
    st.set_page_config(
        page_title="M001 Squad — Phi2.5",
        layout="wide",
    )
    st.title("M001 multi-agent ensemble — Phi2.5 dashboard")
    st.caption(
        "Read-only at Phi2.5. Each panel answers a specific falsification "
        "question per `09-experiment-architecture.md` §1.9."
    )

    runs = loader.list_runs()
    with st.sidebar:
        st.header("Run selection")
        if runs:
            run_label = st.selectbox(
                "Replay run",
                options=["(placeholder data)"] + [r.name for r in runs],
                index=0,
            )
            if run_label == "(placeholder data)":
                run_dir = None
            else:
                run_dir = next(r for r in runs if r.name == run_label)
        else:
            run_dir = None
            st.info(
                "No replay runs found under "
                "`sim/output/`. Showing placeholder data so the panels "
                "render end-to-end."
            )
        st.divider()
        st.caption(
            "Streamlit binds to `127.0.0.1` only (07 §6 / 08 §6).\n\n"
            "Panel inventory: 08 §2."
        )

    tabs = st.tabs([
        "League table",
        "Thought feed",
        "Chemical reactions",
        "Squad vs human",
        "Sentinel",
        "Per-trade",
    ])
    with tabs[0]:
        league_table.render(run_dir)
    with tabs[1]:
        thought_feed.render(run_dir)
    with tabs[2]:
        chemical_reaction_graph.render(run_dir)
    with tabs[3]:
        scoreboard.render(run_dir)
    with tabs[4]:
        sentinel_state.render(run_dir)
    with tabs[5]:
        trade_explainer.render(run_dir)


main()
