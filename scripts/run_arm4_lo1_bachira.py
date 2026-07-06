"""One-off: leave-one-out (Bachira removed) under Phi5 Arm 4.

Purpose (phi5_aggregator PROTOCOL §11.4 C mandatory diagnostics):
recompute the G7 C3 Bachira->Barou cannibalisation ratio under the
Arm 4 multi-position aggregator. Post-V (phi41 aggregator) measured
84.1% -- Barou traded 84.1% more when Bachira was absent. If Arm 4
gives Barou his own slot while Bachira is present, the ratio should
collapse.

Roster: post-kunigami-retirement 7-agent roster MINUS bachira_meguru
(6 proposers). Kunigami instance retained for the Sentinel R5 side
channel, matching every other post-retirement run.

Output cache: reviews/g7_replay_cache_phi5-arm4-lo1-bachira/
"""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from programs.M001_multi_agent_ensemble.sim.core.ledger import FullLedger
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_leave_one_out import (
    _instantiate_all_agents,
    _prepare_agents,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    G7_PANEL_END,
    G7_PANEL_START,
    SYMBOLS_G7,
    _load_production_bars,
    ensure_production_repo_on_path,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    _drive_squad_replay,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s -- %(message)s",
)
log = logging.getLogger("arm4_lo1_bachira")


def main() -> int:
    ensure_production_repo_on_path()
    bars_by_symbol = {}
    for sym in SYMBOLS_G7:
        bars_by_symbol[sym] = _load_production_bars(
            sym, G7_PANEL_START, G7_PANEL_END,
        )
        log.info("Loaded %d %s bars", len(bars_by_symbol[sym]), sym)

    all_agents, isagi, barou, kunigami = _instantiate_all_agents()
    _prepare_agents(all_agents, bars_by_symbol)
    excluded = {"bachira_meguru", "kunigami_rensuke"}
    agents_for_run = [a for a in all_agents if a.agent_id not in excluded]
    log.info("Roster: %s", [a.agent_id for a in agents_for_run])

    ledger = FullLedger()
    out = _drive_squad_replay(
        agents=agents_for_run,
        isagi=isagi, barou=barou, kunigami=kunigami,
        bars_by_symbol=bars_by_symbol,
        ledger=ledger,
        sentinel_blocks=True,
        use_workspace=True,
        use_shadow_ledger=False,   # not needed for the C3 count
        aggregator_arm="arm4",
    )

    cache_dir = (
        REPO_ROOT / "programs/M001_multi_agent_ensemble/reviews"
        / "g7_replay_cache_phi5-arm4-lo1-bachira"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    with (cache_dir / "trades.jsonl").open("w", encoding="utf-8") as fh:
        for t in out.trades:
            fh.write(json.dumps(asdict(t), default=str) + "\n")
    (cache_dir / "workspace_counts.json").write_text(json.dumps({
        "publish": dict(out.workspace_publish_counts),
        "read": dict(out.workspace_read_counts),
        "n_thoughts": len(out.thoughts),
        "n_proposals": len(out.proposals_all),
    }, indent=2), encoding="utf-8")
    log.info(
        "done: %d trades, %d proposals -> %s",
        len(out.trades), len(out.proposals_all), cache_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
