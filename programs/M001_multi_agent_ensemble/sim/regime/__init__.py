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
