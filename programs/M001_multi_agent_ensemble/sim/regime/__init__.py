"""Regime classifier — four classes: trending / chop / vol_spike / news.

Phi2.5 prerequisite (Phi2 -> Phi3 gate G4): holdout F1 >= 0.75 on the
hand-labelled validation set, per `09-experiment-architecture.md`
section 1.5. Foundations F18 in `04-quant-foundations.md` defines the
regime taxonomy and the priority rule (`news > vol_spike > trending >
chop`).

Model artefact: `sim/regime/model_v1.pkl`. Reproducibility manifest
sits next to it as `model_v1.manifest.json` per research-standards
section 5.2.
"""
from .classifier import (  # noqa: F401
    REGIMES,
    RegimeClassifier,
    RegimeLabel,
    extract_features,
)

# Phase M -- news calendar adapter (2026-07-01).
# The ``news_calendar`` submodule owns the Φ5 historical adapter; the
# ``news_windowing`` submodule owns the per-agent TF window helper.
# Both are re-exported here so callers can do
# ``from programs.M001_multi_agent_ensemble.sim import regime`` and
# reach ``regime.news_calendar.load_news_events``.
from . import news_calendar  # noqa: F401
from . import news_calendar_sources  # noqa: F401
from . import news_windowing  # noqa: F401
