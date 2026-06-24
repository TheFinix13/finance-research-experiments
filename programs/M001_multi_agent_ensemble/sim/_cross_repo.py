"""Cross-repo import contract for the M001 simulator.

Phi3+ wraps the production `zone_d1_against` cell (lives in the
*production repo* `multi-pair-trading-agent`) as A1 Isagi v1. The lab repo
must never modify or copy production code (`06-blue-lock-doctrine.md`
section 7 commitment #1; `09-experiment-architecture.md` section 1.3
binding rule).

This module provides a single helper, `ensure_production_repo_on_path`,
that prepends the production repo path to `sys.path` if it isn't already
importable. The path resolution order is:

1. The `M001_PRODUCTION_REPO` environment variable, if set.
2. The default Mac/Linux dev path
   `~/Documents/GitHub/multi-pair-trading-agent`.

If neither location contains an importable `agent.alphas.concepts.zone_alpha`,
the helper raises a `ProductionRepoMissing` error with an actionable
message naming both the missing import and the contract for fixing it.
The error message intentionally instructs the user to set the env var or
extend `PYTHONPATH`; it never tries to recreate or copy production code.

Use:

```python
from programs.M001_multi_agent_ensemble.sim._cross_repo import (
    ensure_production_repo_on_path,
)

ensure_production_repo_on_path()
from agent.alphas.concepts.zone_alpha import SupplyDemandAlpha
```
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# Default location on the dev machine.  Override by exporting
# ``M001_PRODUCTION_REPO=/path/to/multi-pair-trading-agent`` in the
# environment that drives the simulator.
_DEFAULT_PRODUCTION_REPO = (
    Path.home() / "Documents" / "GitHub" / "multi-pair-trading-agent"
)

_REQUIRED_MODULE = "agent.alphas.concepts.zone_alpha"

_ERROR_TEMPLATE = """\
M001 Phi3 cross-repo import contract failed.

Could not import `{module}` from the production repo.

The simulator wraps the production `zone_d1_against` cell as A1 Isagi v1
(doctrine 06 section 1.1, architecture 03 section 7). Lab code is NEVER
allowed to recreate or copy that cell -- it must be imported from the
production repo.

Tried: {tried}

Fix:
  1. Set the env var: export M001_PRODUCTION_REPO=/abs/path/to/multi-pair-trading-agent
  2. OR add the production repo to PYTHONPATH:
       PYTHONPATH=../multi-pair-trading-agent:. python ...
  3. Verify the module exists at <repo>/agent/alphas/concepts/zone_alpha.py
"""


class ProductionRepoMissing(ImportError):
    """Raised when `agent.alphas.concepts.zone_alpha` cannot be imported."""


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    env = os.environ.get("M001_PRODUCTION_REPO")
    if env:
        paths.append(Path(env).expanduser().resolve())
    if _DEFAULT_PRODUCTION_REPO not in paths:
        paths.append(_DEFAULT_PRODUCTION_REPO)
    return paths


def _module_already_importable() -> bool:
    try:
        importlib.import_module(_REQUIRED_MODULE)
        return True
    except Exception:
        return False


def ensure_production_repo_on_path() -> Path:
    """Make sure `agent.alphas.concepts.zone_alpha` is importable.

    Returns the resolved production-repo root that was placed on
    `sys.path`. Raises `ProductionRepoMissing` if no candidate path
    contains the production module.

    Idempotent: subsequent calls are no-ops once the module is importable.
    """
    if _module_already_importable():
        env = os.environ.get("M001_PRODUCTION_REPO")
        if env:
            return Path(env).expanduser().resolve()
        return _DEFAULT_PRODUCTION_REPO

    tried: list[str] = []
    for root in _candidate_paths():
        tried.append(str(root))
        if not root.exists():
            continue
        marker = root / "agent" / "alphas" / "concepts" / "zone_alpha.py"
        if not marker.exists():
            continue
        as_str = str(root)
        if as_str not in sys.path:
            sys.path.insert(0, as_str)
        # Drop any stale partial-import cache, then re-test.
        for cached in list(sys.modules):
            if cached.startswith("agent."):
                del sys.modules[cached]
        if _module_already_importable():
            return root

    raise ProductionRepoMissing(
        _ERROR_TEMPLATE.format(
            module=_REQUIRED_MODULE,
            tried=", ".join(tried) or "(no candidate paths)",
        )
    )


def production_repo_available() -> bool:
    """Return True iff `ensure_production_repo_on_path` would succeed.

    Useful for tests that should skip when the production repo isn't
    on the dev machine (CI runners, fresh clones).
    """
    try:
        ensure_production_repo_on_path()
        return True
    except ProductionRepoMissing:
        return False
