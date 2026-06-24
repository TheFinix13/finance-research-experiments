"""Regime classifier disagreement labelling tool — Streamlit v0.

Run with::

    PYTHONPATH=../multi-pair-trading-agent:. \
      ../multi-pair-trading-agent/.venv/bin/streamlit run \
      programs/M001_multi_agent_ensemble/sim/regime/label_disagreements.py

Takes ~15 minutes for 30 anchors. Output is human-validated regime
labels for the Φ3 gate. See `sim/regime/README.md` for the G4 gate
context — this tool exists to convert the 30 sampled disagreements
between the rule-based heuristic and the trained classifier into a
*ground-truth* label slice the macro F1 can be re-computed against.

Surface contract (sticks to doctrine: Streamlit is the v0 surface):

1. Loads `disagreements_for_review.csv` (30 anchors × 51 context bars).
2. Per anchor: anchor metadata, OHLC candlestick context, the two
   automated labels side-by-side, a radio for the human verdict, and
   an optional `why` note.
3. Persists every emitted label to `labeled_disagreements.csv`
   (append-only; re-labelling the same anchor requires explicit
   confirmation so the audit trail stays intact).
4. At the end, prints aggregate human-vs-classifier and
   human-vs-rule macro F1 + per-class breakdown.
5. On "Finalise", writes `regime_validation_human_2024_eurusd_h4.json`
   with the same schema as `validation_2024_eurusd_h4.json` plus
   `labeled_by` / `labeled_at` fields.

The tool deliberately does **not** mutate the classifier or the
heuristic. It only adds a third opinion (the human) so the next
re-eval can score classifier-vs-human and rule-vs-human in parallel
without re-running the validator end-to-end.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DISAGREEMENTS_CSV = THIS_DIR / "disagreements_for_review.csv"
LABELS_CSV = THIS_DIR / "labeled_disagreements.csv"
HUMAN_VALIDATION_JSON = THIS_DIR / "regime_validation_human_2024_eurusd_h4.json"
SOURCE_VALIDATION_JSON = THIS_DIR / "validation_2024_eurusd_h4.json"

# Regime taxonomy + the human-only "skip" / "unknown" exits. Order
# matters: it's the order the radio renders + the order the per-class
# breakdown renders in.
REGIMES: tuple[str, ...] = ("trending", "chop", "vol_spike", "news")
HUMAN_CHOICES: tuple[str, ...] = (*REGIMES, "unknown", "skip")

# Match `sim/regime/validate_real.py` G4 weak-gate.
WEAK_GATE_AGREEMENT_F1 = 0.50


# ---------------------------------------------------------------------------
# Data loading helpers (pure; tested in `sim/tests/test_label_disagreements.py`)
# ---------------------------------------------------------------------------

def load_disagreements(csv_path: Path = DISAGREEMENTS_CSV) -> pd.DataFrame:
    """Read the long-format disagreements CSV.

    Schema (see `validate_real.py:sample_disagreements`):

        sample_idx, anchor_ts, weak_label, predicted_label,
        offset, ts, open, high, low, close, volume

    Returns the raw long-format frame. The Streamlit app pivots it
    per anchor via `iter_anchors`.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"disagreements CSV not found at {csv_path}; "
            "run `validate_real.py` first to sample disagreements"
        )
    df = pd.read_csv(csv_path)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["anchor_ts"] = pd.to_datetime(df["anchor_ts"], utc=True)
    return df


def iter_anchors(df: pd.DataFrame) -> list[dict]:
    """Group the long-format CSV into one record per disagreement anchor.

    Each record carries the anchor metadata, the rule/classifier
    labels, and the 51-bar OHLC frame ordered by timestamp. The
    OHLC frame has a `DatetimeIndex` so mplfinance can render it
    directly.
    """
    records: list[dict] = []
    for sample_idx, group in df.groupby("sample_idx", sort=True):
        anchor = group.loc[group["offset"] == 0]
        if anchor.empty:
            continue
        anchor_row = anchor.iloc[0]
        ohlc = (
            group[["ts", "open", "high", "low", "close", "volume"]]
            .sort_values("ts")
            .set_index("ts")
        )
        ohlc.index.name = "Date"  # mplfinance expects 'Date' as index name
        records.append({
            "sample_idx": int(sample_idx),
            "anchor_ts": anchor_row["anchor_ts"],
            "rule_label": str(anchor_row["weak_label"]),
            "classifier_label": str(anchor_row["predicted_label"]),
            "ohlc": ohlc,
        })
    return records


def read_existing_labels(path: Path = LABELS_CSV) -> pd.DataFrame:
    """Return the append-only label log, or an empty frame if absent."""
    if not path.exists():
        return pd.DataFrame(columns=[
            "sample_idx", "anchor_ts", "rule_label",
            "classifier_label", "human_label", "note", "labeled_at",
        ])
    df = pd.read_csv(path)
    if "anchor_ts" in df.columns:
        df["anchor_ts"] = pd.to_datetime(df["anchor_ts"], utc=True)
    return df


def latest_labels(df: pd.DataFrame) -> dict[int, str]:
    """Return `{sample_idx: most_recent_human_label}` from the audit log."""
    if df.empty:
        return {}
    sorted_df = df.sort_values("labeled_at")
    out: dict[int, str] = {}
    for _, row in sorted_df.iterrows():
        out[int(row["sample_idx"])] = str(row["human_label"])
    return out


def append_label(
    *,
    sample_idx: int,
    anchor_ts: pd.Timestamp,
    rule_label: str,
    classifier_label: str,
    human_label: str,
    note: str,
    path: Path = LABELS_CSV,
) -> None:
    """Append a single human-label row to `labeled_disagreements.csv`.

    Append-only by design — re-labelling the same anchor adds a new
    row with a later `labeled_at`, which `latest_labels` resolves to
    "most recent wins". The full history stays on disk so the audit
    trail is intact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "sample_idx": int(sample_idx),
        "anchor_ts": anchor_ts.isoformat() if hasattr(anchor_ts, "isoformat")
        else str(anchor_ts),
        "rule_label": str(rule_label),
        "classifier_label": str(classifier_label),
        "human_label": str(human_label),
        "note": str(note or ""),
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    }
    header = not path.exists()
    pd.DataFrame([row]).to_csv(
        path, mode="a", header=header, index=False, encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Aggregate metrics (pure)
# ---------------------------------------------------------------------------

def compute_aggregate(
    *,
    anchors: list[dict],
    labels_by_idx: dict[int, str],
) -> dict:
    """Compute human-vs-classifier and human-vs-rule macro F1 + per-class.

    Skipped / unknown rows are excluded from the F1 (they would bias
    the macro down for classes the human declined to vote on). The
    returned dict carries the exact same shape `validation_2024_*.json`
    uses so the JSON writer can drop it straight in.
    """
    from sklearn.metrics import classification_report, f1_score

    y_human: list[str] = []
    y_pred: list[str] = []
    y_rule: list[str] = []
    for rec in anchors:
        label = labels_by_idx.get(rec["sample_idx"])
        if label is None or label in ("skip", "unknown"):
            continue
        y_human.append(label)
        y_pred.append(rec["classifier_label"])
        y_rule.append(rec["rule_label"])

    n_scored = len(y_human)
    labels_list = list(REGIMES)

    if n_scored == 0:
        empty_report = {
            r: {"precision": 0.0, "recall": 0.0, "f1-score": 0.0, "support": 0}
            for r in REGIMES
        }
        return {
            "n_anchors_total": len(anchors),
            "n_labeled": int(sum(1 for v in labels_by_idx.values()
                                  if v not in ("skip", "unknown"))),
            "n_skipped": int(sum(1 for v in labels_by_idx.values()
                                  if v == "skip")),
            "n_scored": 0,
            "vs_classifier": {
                "agreement_f1_macro": 0.0,
                "per_class": _per_class_from_report(empty_report),
            },
            "vs_rule": {
                "agreement_f1_macro": 0.0,
                "per_class": _per_class_from_report(empty_report),
            },
        }

    f1_pred = float(
        f1_score(y_human, y_pred, labels=labels_list,
                 average="macro", zero_division=0)
    )
    f1_rule = float(
        f1_score(y_human, y_rule, labels=labels_list,
                 average="macro", zero_division=0)
    )
    report_pred = classification_report(
        y_human, y_pred, labels=labels_list,
        output_dict=True, zero_division=0,
    )
    report_rule = classification_report(
        y_human, y_rule, labels=labels_list,
        output_dict=True, zero_division=0,
    )

    return {
        "n_anchors_total": len(anchors),
        "n_labeled": int(sum(1 for v in labels_by_idx.values()
                              if v not in ("skip", "unknown"))),
        "n_skipped": int(sum(1 for v in labels_by_idx.values()
                              if v == "skip")),
        "n_scored": int(n_scored),
        "vs_classifier": {
            "agreement_f1_macro": f1_pred,
            "per_class": _per_class_from_report(report_pred),
        },
        "vs_rule": {
            "agreement_f1_macro": f1_rule,
            "per_class": _per_class_from_report(report_rule),
        },
    }


def _per_class_from_report(report: dict) -> dict:
    out: dict = {}
    for r in REGIMES:
        if r in report:
            out[r] = {
                "precision": float(report[r]["precision"]),
                "recall": float(report[r]["recall"]),
                "f1": float(report[r]["f1-score"]),
                "support": int(report[r]["support"]),
            }
        else:
            out[r] = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "support": 0}
    return out


def build_validation_json(
    *,
    aggregate: dict,
    anchors: list[dict],
    labels_by_idx: dict[int, str],
    source_json_path: Path = SOURCE_VALIDATION_JSON,
) -> dict:
    """Assemble the human-validation JSON in the same schema as the
    machine-validation file, plus `labeled_by` / `labeled_at`.

    The `manifest` block is inherited from `validation_2024_eurusd_h4.json`
    when present so window/seed/model provenance carries through. The
    `gate` block uses the same 0.50 weak threshold for direct comparison.
    """
    source_manifest: dict = {}
    if source_json_path.exists():
        try:
            source = json.loads(source_json_path.read_text(encoding="utf-8"))
            source_manifest = source.get("manifest", {})
        except (json.JSONDecodeError, OSError):
            source_manifest = {}

    now = datetime.now(timezone.utc).isoformat()
    labels_jsonable = {
        int(rec["sample_idx"]): {
            "anchor_ts": rec["anchor_ts"].isoformat()
            if hasattr(rec["anchor_ts"], "isoformat") else str(rec["anchor_ts"]),
            "rule_label": rec["rule_label"],
            "classifier_label": rec["classifier_label"],
            "human_label": labels_by_idx.get(rec["sample_idx"]),
        }
        for rec in anchors
    }

    f1_pred = aggregate["vs_classifier"]["agreement_f1_macro"]
    return {
        "labeled_by": "user",
        "labeled_at": now,
        "manifest": {
            **source_manifest,
            "_human_validation_note": (
                "Human-validated regime labels for the 30 disagreement "
                "anchors sampled by validate_real.py. F1 is computed "
                "human-vs-classifier (the gate-relevant metric) and "
                "human-vs-rule (sanity check)."
            ),
            "labeling_tool": "sim/regime/label_disagreements.py",
            "labeling_completed_at_utc": now,
        },
        "counts": {
            "n_anchors_total": int(aggregate["n_anchors_total"]),
            "n_labeled": int(aggregate["n_labeled"]),
            "n_skipped": int(aggregate["n_skipped"]),
            "n_scored": int(aggregate["n_scored"]),
        },
        "metrics": {
            "agreement_f1_macro_vs_classifier": float(f1_pred),
            "agreement_f1_macro_vs_rule": float(
                aggregate["vs_rule"]["agreement_f1_macro"]
            ),
            "per_class_vs_classifier": aggregate["vs_classifier"]["per_class"],
            "per_class_vs_rule": aggregate["vs_rule"]["per_class"],
        },
        "gate": {
            "threshold_agreement_f1": float(WEAK_GATE_AGREEMENT_F1),
            "pass": bool(f1_pred >= WEAK_GATE_AGREEMENT_F1),
            "note": (
                "Pass here means the classifier predictions on these "
                "30 disagreement anchors match the human verdict at "
                "macro F1 ≥ 0.50. This is still a 30-anchor sample, "
                "NOT the G4 ≥ 200-bar hand-labelled holdout — but it "
                "is the first ground-truth measurement available."
            ),
        },
        "labels": labels_jsonable,
    }


def write_validation_json(payload: dict, path: Path = HUMAN_VALIDATION_JSON) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Streamlit chart helpers (matplotlib path; mplfinance preferred when
# installed; falls back to st.line_chart when neither is available so the
# app still renders on minimal environments)
# ---------------------------------------------------------------------------

def render_candles(ohlc: pd.DataFrame, anchor_ts: pd.Timestamp) -> None:
    """Render a 51-bar candlestick chart with the anchor highlighted.

    Tries `mplfinance` first (best UX); falls back to a matplotlib OHLC
    plot, then to `st.line_chart` on the close series. The fallbacks
    keep the app usable on environments without the chart dependency.
    """
    try:
        import mplfinance as mpf  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore

        # Highlight the anchor bar with a vertical line.
        try:
            anchor_loc = ohlc.index.get_loc(anchor_ts)
        except KeyError:
            anchor_loc = len(ohlc) - 1
        addplots = []
        try:
            vline = dict(
                vlines=dict(vlines=[anchor_ts.to_pydatetime()],
                            linewidths=1.5, colors="red", alpha=0.6)
            )
        except AttributeError:
            vline = {}

        fig, _axlist = mpf.plot(
            ohlc,
            type="candle",
            style="yahoo",
            volume=False,
            returnfig=True,
            figsize=(11, 4.5),
            tight_layout=True,
            **vline,
        )
        st.pyplot(fig, clear_figure=True)
        plt.close(fig)
        st.caption(
            f"Anchor bar (red line) = bar {anchor_loc} of {len(ohlc) - 1}; "
            f"preceding 50 bars = OHLC context."
        )
        return
    except Exception as e:  # noqa: BLE001 — chart fallback path
        st.info(
            f"Candlestick renderer unavailable ({type(e).__name__}: {e}); "
            "falling back to line chart of close prices."
        )

    try:
        import matplotlib.pyplot as plt  # type: ignore

        fig, ax = plt.subplots(figsize=(11, 4.5))
        ax.plot(ohlc.index, ohlc["close"], color="steelblue")
        ax.axvline(anchor_ts, color="red", alpha=0.5, linewidth=1.5)
        ax.set_title("Close (red line = anchor)")
        ax.set_xlabel("ts")
        ax.set_ylabel("close")
        ax.grid(True, alpha=0.3)
        st.pyplot(fig, clear_figure=True)
        plt.close(fig)
    except Exception:  # noqa: BLE001 — last-resort fallback
        st.line_chart(ohlc[["close"]])


# ---------------------------------------------------------------------------
# Streamlit page (only invoked when run under `streamlit run`)
# ---------------------------------------------------------------------------

def _init_session_state(n_anchors: int) -> None:
    if "current_idx" not in st.session_state:
        st.session_state.current_idx = 0
    if "confirm_overwrite_for" not in st.session_state:
        st.session_state.confirm_overwrite_for = None
    if "n_anchors" not in st.session_state or st.session_state.n_anchors != n_anchors:
        st.session_state.n_anchors = n_anchors


def _go_prev() -> None:
    st.session_state.current_idx = max(0, st.session_state.current_idx - 1)
    st.session_state.confirm_overwrite_for = None


def _go_next() -> None:
    st.session_state.current_idx = min(
        st.session_state.n_anchors - 1, st.session_state.current_idx + 1
    )
    st.session_state.confirm_overwrite_for = None


def _render_label_card(rec: dict, existing_label: str | None) -> None:
    st.markdown(f"### Anchor {rec['sample_idx']} — {rec['anchor_ts']}")
    st.markdown(
        "Symbol: **EURUSD** &nbsp;·&nbsp; Timeframe: **H4** "
        f"&nbsp;·&nbsp; Anchor bar: `{rec['anchor_ts']}`"
    )
    render_candles(rec["ohlc"], rec["anchor_ts"])

    col_rule, col_clf = st.columns(2)
    with col_rule:
        st.markdown("**Rule (weak label) says:**")
        st.markdown(f"# `{rec['rule_label']}`")
    with col_clf:
        st.markdown("**Classifier says:**")
        st.markdown(f"# `{rec['classifier_label']}`")

    st.markdown("---")
    default_idx = (
        HUMAN_CHOICES.index(existing_label)
        if existing_label in HUMAN_CHOICES else 0
    )
    radio_key = f"label_radio_{rec['sample_idx']}"
    note_key = f"label_note_{rec['sample_idx']}"
    chosen = st.radio(
        "Your label",
        options=HUMAN_CHOICES,
        index=default_idx,
        key=radio_key,
        horizontal=True,
        help=(
            "trending / chop / vol_spike / news — the four canonical "
            "regimes. unknown = bar is genuinely ambiguous. skip = "
            "I'd rather come back to this one (excluded from F1)."
        ),
    )
    note = st.text_input(
        "Why (optional): a sentence on your mental model",
        key=note_key,
        max_chars=240,
    )

    # Save flow: append unless we already have a different label for
    # this anchor (then ask for explicit confirmation per the spec).
    confirm_target = st.session_state.confirm_overwrite_for
    needs_confirm = (
        existing_label is not None
        and existing_label != chosen
        and confirm_target != rec["sample_idx"]
    )

    col_a, col_b, col_c = st.columns([1, 1, 4])
    with col_a:
        prev_clicked = st.button(
            "⟵ Previous", on_click=_go_prev,
            disabled=st.session_state.current_idx == 0,
        )
    with col_b:
        next_clicked = st.button(
            "Next ⟶", on_click=_go_next,
            disabled=st.session_state.current_idx
            == st.session_state.n_anchors - 1,
        )
    with col_c:
        save_clicked = st.button(
            "💾 Save label",
            help="Append this row to labeled_disagreements.csv",
        )

    # Suppress unused-var lints — the on_click handlers do the work.
    _ = prev_clicked, next_clicked

    if save_clicked:
        if needs_confirm:
            st.session_state.confirm_overwrite_for = rec["sample_idx"]
            st.warning(
                f"You already labelled anchor {rec['sample_idx']} as "
                f"`{existing_label}`. Click **Save label** again to "
                "overwrite with the new value (history kept in the CSV)."
            )
        else:
            append_label(
                sample_idx=rec["sample_idx"],
                anchor_ts=rec["anchor_ts"],
                rule_label=rec["rule_label"],
                classifier_label=rec["classifier_label"],
                human_label=chosen,
                note=note,
            )
            st.success(
                f"Saved anchor {rec['sample_idx']} = `{chosen}`. "
                f"({LABELS_CSV.name})"
            )
            st.session_state.confirm_overwrite_for = None


def _render_aggregate(anchors: list[dict], labels_by_idx: dict[int, str]) -> None:
    st.markdown("## Aggregate")
    if not labels_by_idx:
        st.info("No labels saved yet. Walk through the anchors above first.")
        return
    aggregate = compute_aggregate(anchors=anchors, labels_by_idx=labels_by_idx)
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(
            "Human-vs-classifier macro F1",
            f"{aggregate['vs_classifier']['agreement_f1_macro']:.3f}",
            help=(
                "This is the gate-relevant number — does the classifier "
                "agree with the human on the bars where the rule and "
                "the classifier disagreed."
            ),
        )
    with col_b:
        st.metric(
            "Human-vs-rule macro F1 (sanity check)",
            f"{aggregate['vs_rule']['agreement_f1_macro']:.3f}",
            help="Sanity check — how well the heuristic itself matches the human.",
        )

    st.markdown("### Per-class F1")
    rows = []
    for r in REGIMES:
        rows.append({
            "regime": r,
            "vs_classifier_f1": round(
                aggregate["vs_classifier"]["per_class"][r]["f1"], 3
            ),
            "vs_classifier_support": aggregate["vs_classifier"]
            ["per_class"][r]["support"],
            "vs_rule_f1": round(aggregate["vs_rule"]["per_class"][r]["f1"], 3),
            "vs_rule_support": aggregate["vs_rule"]["per_class"][r]["support"],
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    st.markdown(
        f"Labelled `{aggregate['n_labeled']}/{aggregate['n_anchors_total']}` "
        f"anchors · skipped `{aggregate['n_skipped']}` · scored "
        f"`{aggregate['n_scored']}` (skip + unknown excluded from F1)."
    )

    if st.button("Finalise → write `regime_validation_human_2024_eurusd_h4.json`"):
        payload = build_validation_json(
            aggregate=aggregate,
            anchors=anchors,
            labels_by_idx=labels_by_idx,
        )
        out_path = write_validation_json(payload)
        st.success(
            f"Wrote {out_path.name}. Append this to git when ready:\n\n"
            f"`git add {out_path.relative_to(REPO_ROOT)} "
            f"{LABELS_CSV.relative_to(REPO_ROOT)}`"
        )


def main() -> None:
    st.set_page_config(
        page_title="M001 — regime disagreement labelling",
        layout="wide",
    )
    st.title("Regime disagreement labelling")
    st.caption(
        "30 sampled disagreements between the rule-based heuristic and "
        "the trained classifier. Takes ~15 minutes; output is the "
        "human-validated label slice for the Φ3 G4 gate. See "
        "`sim/regime/README.md` for context."
    )

    df = load_disagreements()
    anchors = iter_anchors(df)
    if not anchors:
        st.error(
            "No anchors found in disagreements_for_review.csv — re-run "
            "`validate_real.py` first."
        )
        return

    _init_session_state(len(anchors))
    labels_df = read_existing_labels()
    labels_by_idx = latest_labels(labels_df)

    # --- Progress bar + sidebar nav ---
    idx = st.session_state.current_idx
    st.progress(
        (idx + 1) / len(anchors),
        text=f"{idx + 1} of {len(anchors)}",
    )

    with st.sidebar:
        st.markdown("### Progress")
        st.markdown(
            f"**Labelled:** {len(labels_by_idx)} / {len(anchors)}"
        )
        st.markdown(
            f"**Skipped:** "
            f"{sum(1 for v in labels_by_idx.values() if v == 'skip')}"
        )
        st.markdown("---")
        jump = st.number_input(
            "Jump to anchor",
            min_value=0,
            max_value=len(anchors) - 1,
            value=idx,
            step=1,
        )
        if st.button("Go"):
            st.session_state.current_idx = int(jump)
            st.session_state.confirm_overwrite_for = None
        st.markdown("---")
        st.markdown(
            f"Labels CSV: `{LABELS_CSV.relative_to(REPO_ROOT)}`\n\n"
            f"Output JSON: `{HUMAN_VALIDATION_JSON.relative_to(REPO_ROOT)}`"
        )

    rec = anchors[idx]
    existing = labels_by_idx.get(rec["sample_idx"])
    _render_label_card(rec, existing)

    st.markdown("---")
    _render_aggregate(anchors, labels_by_idx)


# Streamlit invokes `main` implicitly via the script run; keep an
# explicit guard so `python label_disagreements.py` (without
# streamlit) still reports a sensible error.
if __name__ == "__main__":  # pragma: no cover — exercised by Streamlit
    main()
else:
    # Streamlit runs the module top-level, so trigger main here too.
    # The `__name__` is "__main__" under `streamlit run` so this only
    # fires for unusual import shapes; cheap belt-and-braces.
    pass
