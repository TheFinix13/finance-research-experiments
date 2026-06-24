"""JSONL + parquet loaders for the Phi2.5 dashboard.

All loaders return placeholder data when no run is available so the
six panels render the surface end-to-end even before the first
replay run lands.

Caching: `@st.cache_data` keyed on (path, mtime, size) per the
research-standards section 8 immutability rule (JSONLs are append-only,
not mutable, so mtime+size is a sound cache key).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

# Default run root — the engine writes here per `engine.write_run_artefacts`.
DEFAULT_RUN_ROOT = Path(__file__).resolve().parents[2] / "output"


def _file_cache_key(path: Path) -> tuple[str, int, int]:
    """(path, mtime_ns, size_bytes) — append-only cache key."""
    s = path.stat() if path.exists() else None
    return (str(path), int(s.st_mtime_ns) if s else 0, int(s.st_size) if s else 0)


def _load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file (one JSON object per line). Empty list if missing."""
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Placeholder fixture data (Phi2.5 — renders the surface before any run)
# ---------------------------------------------------------------------------

_PLACEHOLDER_AGENTS = [
    ("isagi_yoichi",   "Isagi",   0.60, "TBD", "starter"),
    ("nagi_seishiro",  "Nagi",    0.45, "TBD", "benched"),
    ("barou_shoei",    "Barou",   1.00, "TBD", "starter"),
    ("kunigami_rensuke", "Kunigami", 0.00, "TBD", "sub"),
]


def _placeholder_league_table() -> pd.DataFrame:
    rows = []
    for agent_id, canon, ego, tier, verdict in _PLACEHOLDER_AGENTS:
        rows.append({
            "agent_id": agent_id,
            "canon_player": canon,
            "tier": tier,
            "tqs_median": 0.0,
            "tqs_iqr": 0.0,
            "ir_vs_squad": 0.0,
            "delta_info": 0.0,
            "delta_info_ci_low": 0.0,
            "delta_info_ci_high": 0.0,
            "pain_ratio": 0.0,
            "tqs_trending": 0.0,
            "tqs_chop": 0.0,
            "tqs_vol_spike": 0.0,
            "tqs_news": 0.0,
            "last_verdict": verdict,
            "proposals_24h": 0,
        })
    return pd.DataFrame(rows)


def _placeholder_thoughts() -> pd.DataFrame:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    rows = []
    for i, (agent_id, canon, *_) in enumerate(_PLACEHOLDER_AGENTS):
        rows.append({
            "thought_id": f"{agent_id}:placeholder:{i}",
            "agent_id": agent_id,
            "canon_player": canon,
            "tick_id": i,
            "timestamp": (now - timedelta(minutes=i)).isoformat(),
            "symbol": "EURUSD",
            "narrative": (
                f"[placeholder] {canon} observation-only tick — Phi3 lands "
                "the real strategy logic."
            ),
            "tags": ["phi2_placeholder", f"canon:{canon.lower()}"],
            "confidence_in_thought": 0.0,
            "has_coordinate": False,
            "references": [],
        })
    return pd.DataFrame(rows)


def _placeholder_chemical_reactions() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "tick_id", "timestamp", "symbol", "agent_a", "agent_b",
        "trigger_type", "combined_conviction", "size_multiplier", "realised_tqs",
    ])


def _placeholder_scoreboard() -> pd.DataFrame:
    return pd.DataFrame([
        {"opponent": "Kaiser",        "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": 0.0, "counter": 0.0, "loki_distance": None, "gate_verdict": "SHOULD-approach"},
        {"opponent": "Loki",          "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": 0.0, "counter": 0.0, "loki_distance": 1.0,  "gate_verdict": "MUST-stay-distant"},
        {"opponent": "Median",        "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": None, "counter": None, "loki_distance": None, "gate_verdict": "MUST-beat"},
        {"opponent": "Random",        "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": None, "counter": None, "loki_distance": None, "gate_verdict": "MUST-beat"},
        {"opponent": "Sae-frozen",    "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": None, "counter": None, "loki_distance": None, "gate_verdict": "MUST-beat"},
        {"opponent": "Sae-composite", "mean_tqs": 0.0, "pnl_hh_gap": 0.0, "coverage": None, "counter": None, "loki_distance": None, "gate_verdict": "MUST-beat"},
    ])


def _placeholder_sentinel_state() -> dict:
    return {
        "equity": 100.0,
        "margin_level_pct": 999.0,
        "open_positions": 0,
        "per_trade_risk_cap_pct": 5.0,
        "loss_streak": 0,
        "risk_scale": 1.0,
        "r5_active": False,
        "trigger_log_24h": [],
    }


def _placeholder_intents() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "intent_id", "tick_id", "timestamp", "symbol", "direction",
        "entry", "stop", "size",
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_runs(run_root: Path | None = None) -> list[Path]:
    root = Path(run_root or DEFAULT_RUN_ROOT)
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir()])


def load_thoughts(run_dir: Path | None = None) -> pd.DataFrame:
    if run_dir is None:
        return _placeholder_thoughts()
    rows = _load_jsonl(Path(run_dir) / "thoughts.jsonl")
    if not rows:
        return _placeholder_thoughts()
    df = pd.DataFrame(rows)
    df["canon_player"] = df["agent_id"].map(
        {a[0]: a[1] for a in _PLACEHOLDER_AGENTS}
    ).fillna(df["agent_id"])
    df["has_coordinate"] = df["coordinate"].notna() if "coordinate" in df else False
    return df


def load_proposals(run_dir: Path | None = None) -> pd.DataFrame:
    if run_dir is None:
        return pd.DataFrame(columns=[
            "agent_id", "tick_id", "timestamp", "symbol", "direction",
            "entry", "stop", "conviction", "regime_fit",
        ])
    rows = _load_jsonl(Path(run_dir) / "proposals.jsonl")
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "agent_id", "tick_id", "timestamp", "symbol", "direction",
        "entry", "stop", "conviction", "regime_fit",
    ])


def load_intents(run_dir: Path | None = None) -> pd.DataFrame:
    if run_dir is None:
        return _placeholder_intents()
    rows = _load_jsonl(Path(run_dir) / "intents.jsonl")
    return pd.DataFrame(rows) if rows else _placeholder_intents()


def load_sentinel_log(run_dir: Path | None = None) -> pd.DataFrame:
    if run_dir is None:
        return pd.DataFrame(columns=[
            "tick_id", "timestamp", "intent_id", "allowed", "rule", "reason",
        ])
    rows = _load_jsonl(Path(run_dir) / "sentinel_log.jsonl")
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "tick_id", "timestamp", "intent_id", "allowed", "rule", "reason",
    ])


def load_league_table(run_dir: Path | None = None) -> pd.DataFrame:
    """Phi2.5 returns placeholder rows; Phi3 wires per-agent KPI joins."""
    return _placeholder_league_table()


def load_chemical_reactions(run_dir: Path | None = None) -> pd.DataFrame:
    if run_dir is None:
        return _placeholder_chemical_reactions()
    rows = _load_jsonl(Path(run_dir) / "chemical_reactions.jsonl")
    return pd.DataFrame(rows) if rows else _placeholder_chemical_reactions()


def load_scoreboard(run_dir: Path | None = None) -> pd.DataFrame:
    return _placeholder_scoreboard()


def load_sentinel_state(run_dir: Path | None = None) -> dict:
    return _placeholder_sentinel_state()
