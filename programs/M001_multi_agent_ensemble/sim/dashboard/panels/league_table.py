"""Panel §2.1 — per-agent league table."""
from __future__ import annotations

import streamlit as st

from programs.M001_multi_agent_ensemble.sim.dashboard.data import loader


VERDICT_PALETTE = {
    "starter": "#27ae60",
    "sub":     "#f1c40f",
    "benched": "#7f8c8d",
    "cut":     "#c0392b",
}


def render(run_dir=None) -> None:
    st.subheader("§2.1 League table")
    st.caption(
        "Falsification question: does agent *i* earn its weight on TQS? "
        "(09 §1.9 — TQS median <= 0 with CI excluding positive ΔInfo "
        "disconfirms.)"
    )

    df = loader.load_league_table(run_dir)
    if df.empty:
        st.info("No agents in the active roster. Check `sim/roster/mvp_phi4.yaml`.")
        return

    show = df.copy()
    show["TQS (median ± IQR)"] = show.apply(
        lambda r: f"{r['tqs_median']:.2f} ± {r['tqs_iqr']:.2f}", axis=1
    )
    show["ΔInfo (95% CI)"] = show.apply(
        lambda r: (
            f"{r['delta_info']:+.3f} "
            f"[{r['delta_info_ci_low']:+.3f}, {r['delta_info_ci_high']:+.3f}]"
        ),
        axis=1,
    )
    show["Regime buckets (TQS)"] = show.apply(
        lambda r: (
            f"T={r['tqs_trending']:+.2f}  "
            f"C={r['tqs_chop']:+.2f}  "
            f"V={r['tqs_vol_spike']:+.2f}  "
            f"N={r['tqs_news']:+.2f}"
        ),
        axis=1,
    )

    cols = [
        "agent_id", "canon_player", "tier",
        "TQS (median ± IQR)", "ir_vs_squad", "ΔInfo (95% CI)",
        "pain_ratio", "Regime buckets (TQS)", "last_verdict", "proposals_24h",
    ]
    st.dataframe(show[cols], hide_index=True, use_container_width=True)

    with st.expander("Verdict vocabulary (08 §3)"):
        st.write(
            "Internal four-tier registry -> Blue Lock UI vocabulary:\n"
            "* `alive` -> `starter`\n"
            "* `parked_weak_effect` -> `sub`\n"
            "* `parked_insufficient_n` -> `benched`\n"
            "* `dead` -> `cut`"
        )
