"""Panel §2.2 — live thought feed."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


def render(run_dir=None) -> None:
    st.subheader("§2.2 Live thought feed")
    st.caption(
        "Falsification question: is the ledger free of look-ahead? "
        "(09 §1.9 — disconfirms if any Thought references a bar index > "
        "current `decision_horizon`.)"
    )

    df = loader.load_thoughts(run_dir)
    if df.empty:
        st.info("No thoughts journalled yet. Run a replay first.")
        return

    # Sidebar-style filters (rendered inline for v0).
    with st.expander("Filters", expanded=False):
        agents = st.multiselect(
            "Agents", sorted(df["agent_id"].unique()), default=None
        )
        only_with_coord = st.checkbox("Only thoughts with a Coordinate", False)

    view = df.copy()
    if agents:
        view = view[view["agent_id"].isin(agents)]
    if only_with_coord and "has_coordinate" in view:
        view = view[view["has_coordinate"]]

    view = view.sort_values("tick_id", ascending=False).head(50)

    for _, row in view.iterrows():
        tags = ", ".join(f"`{t}`" for t in (row.get("tags") or []))
        conf_pct = float(row.get("confidence_in_thought", 0.0))
        with st.container(border=True):
            st.markdown(
                f"**{row.get('canon_player', row['agent_id'])}** · "
                f"`{row['symbol']}` · tick `{row['tick_id']}` · "
                f"{row['timestamp']}"
            )
            st.write(row["narrative"])
            st.progress(min(1.0, conf_pct), text=f"Confidence: {conf_pct:.2f}")
            if tags:
                st.caption(f"Tags: {tags}")
            if row.get("has_coordinate"):
                st.caption("Coordinate attached (mini-chart in Phi3).")
            if row.get("references"):
                st.caption(f"References: {', '.join(row['references'][:3])}")
