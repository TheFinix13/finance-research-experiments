"""Panel §2.5 — Sentinel state board."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


def render(run_dir=None) -> None:
    st.subheader("§2.5 Sentinel state")
    st.caption(
        "Falsification question: are hard rules enforced? "
        "(09 §1.9 — disconfirms if any R1–R5 violation is logged without "
        "a block.)"
    )

    state = loader.load_sentinel_state(run_dir)
    c1, c2, c3 = st.columns(3)
    c1.metric("Equity ($)", f"{state['equity']:.2f}")
    c2.metric("Margin level (%)", f"{state['margin_level_pct']:.1f}")
    c3.metric("Open positions", state["open_positions"])
    c4, c5, c6 = st.columns(3)
    c4.metric("Per-trade risk cap", f"{state['per_trade_risk_cap_pct']:.1f}%")
    c5.metric("Loss streak", state["loss_streak"])
    c6.metric("Risk scale", f"{state['risk_scale']:.2f}x")

    st.markdown("**Trigger log (last 24h)**")
    log_df = loader.load_sentinel_log(run_dir)
    if log_df.empty:
        st.info("No Sentinel triggers in the window.")
        return
    st.dataframe(log_df.tail(50), hide_index=True, use_container_width=True)
