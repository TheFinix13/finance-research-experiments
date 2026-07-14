"""Lever D -- C2 finisher clause tests (2026-07-14, ADVISORY).

Pre-registration: `experiments/c2_finisher_clause/PROTOCOL.md` sec 3.
Asserts:

  (a) the clause requires >= 2 statistically-qualified incoming lifts
      (1 is not enough);
  (b) non-eligible playstyles never get the clause;
  (c) verdict-bearing outputs (bit vectors + squad verdict) are
      byte-identical with the flag on or off;
  (d) the advisory squad count uses the clause pass for eligible
      agents only.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from programs.M001_multi_agent_ensemble.sim.scoring import (
    run_g7_final_verdict as fv,
)
from programs.M001_multi_agent_ensemble.sim.scoring.run_g7_v1_checkpoint_gate import (
    CriterionResult,
    _g7_windows,
)
from programs.M001_multi_agent_ensemble.sim.tests.test_run_g7_final_verdict import (
    FakeAgent,
    _trade,
    _write_jsonl,
)

WINDOWS = _g7_windows()
N_WINDOWS = len(WINDOWS)


def _c2_result(qualifying_peers: list[str]) -> CriterionResult:
    return CriterionResult(
        passed=bool(qualifying_peers), statistic=0.0, threshold=0.0,
        evidence={"qualifying_peers": qualifying_peers, "per_peer": {}},
    )


# ---------------------------------------------------------------------------
# Pure clause function
# ---------------------------------------------------------------------------

class TestEvaluateC2FinisherClause:
    def test_two_incoming_lifts_pass(self):
        c2 = {
            "bachira_meguru": _c2_result(["nagi_seishiro"]),
            "itoshi_rin": _c2_result(["nagi_seishiro"]),
            "nagi_seishiro": _c2_result([]),
        }
        block = fv.evaluate_c2_finisher_clause(
            "nagi_seishiro", playstyle="confluence_only",
            c2_by_excluded=c2,
        )
        assert block["eligible"] is True
        assert block["n_incoming_lifts"] == 2
        assert block["incoming_lifting_peers"] == [
            "bachira_meguru", "itoshi_rin",
        ]
        assert block["clause_pass"] is True
        assert block["status"] == "advisory"

    def test_one_incoming_lift_is_not_enough(self):
        c2 = {
            "bachira_meguru": _c2_result(["nagi_seishiro"]),
            "itoshi_rin": _c2_result(["isagi_yoichi"]),
            "nagi_seishiro": _c2_result([]),
        }
        block = fv.evaluate_c2_finisher_clause(
            "nagi_seishiro", playstyle="confluence_only",
            c2_by_excluded=c2,
        )
        assert block["n_incoming_lifts"] == 1
        assert block["clause_pass"] is False

    def test_non_eligible_playstyle_never_gets_clause(self):
        c2 = {
            "bachira_meguru": _c2_result(["barou_shoei"]),
            "itoshi_rin": _c2_result(["barou_shoei"]),
            "barou_shoei": _c2_result([]),
        }
        block = fv.evaluate_c2_finisher_clause(
            "barou_shoei", playstyle="solo_king", c2_by_excluded=c2,
        )
        assert block["eligible"] is False
        assert block["clause_pass"] is False
        assert block["n_incoming_lifts"] == 0

    def test_own_c2_result_is_ignored(self):
        # A (pathological) self-listing must not count as incoming.
        c2 = {
            "nagi_seishiro": _c2_result(["nagi_seishiro"]),
            "bachira_meguru": _c2_result(["nagi_seishiro"]),
        }
        block = fv.evaluate_c2_finisher_clause(
            "nagi_seishiro", playstyle="confluence_only",
            c2_by_excluded=c2,
        )
        assert block["n_incoming_lifts"] == 1
        assert block["clause_pass"] is False


# ---------------------------------------------------------------------------
# End-to-end: flag invariance + advisory squad count
# ---------------------------------------------------------------------------

@pytest.fixture()
def finisher_caches(tmp_path: Path):
    """Synthetic caches where Nagi fails verdict-bearing C2 (removing
    him changes nothing for peers) but receives TWO incoming lifts
    (removing Bachira or Rin halves Nagi's trade count)."""
    roster = fv.G7_FINAL_ROSTER
    traders = [a for a in roster if a != "reo_mikage"]
    lifters = ("bachira_meguru", "itoshi_rin")

    def _rows(agent_counts: dict[str, int]) -> list[dict]:
        rows: list[dict] = []
        for aid, per_window in agent_counts.items():
            for w in range(N_WINDOWS):
                for j in range(per_window):
                    rows.append(_trade(
                        aid, 0.42, w,
                        conviction=0.5 + 0.08 * (j % 6),
                        sl_pips=20.0 + 5.0 * (j % 6),
                        atr_pips=15.0 + 6.0 * (j % 6),
                    ))
        return rows

    base_counts = {a: 6 for a in traders}
    base_counts["nagi_seishiro"] = 8
    baseline_dir = tmp_path / "baseline_cache"
    _write_jsonl(baseline_dir / "trades.jsonl", _rows(base_counts))
    (baseline_dir / "workspace_counts.json").write_text(json.dumps({
        "publish": {a: 100 for a in roster},
        "read": {a: 50 for a in traders},
    }))

    lo1_dir = tmp_path / "g7_leave_one_out_finisher"
    for excluded in roster:
        counts = {a: 6 for a in traders if a != excluded}
        if excluded != "nagi_seishiro":
            # Nagi keeps 8/window unless a LIFTER is removed -- then his
            # confluence volume halves (incoming lift, CI-clean).
            counts["nagi_seishiro"] = 4 if excluded in lifters else 8
        if excluded not in ("nagi_seishiro", *lifters):
            # Everyone else's removal ALSO lifts some peer via TQS so
            # their own C2 passes (keeps the fixture focused on Nagi).
            pass
        rows = _rows(counts)
        if excluded not in lifters and excluded != "nagi_seishiro":
            # Degrade one peer's TQS without the excluded agent so C2
            # passes for the excluded agent via the TQS route.
            victim = next(a for a in traders if a not in (excluded,))
            rows = [
                {**r, "tqs_components": {"tqs": 0.30}}
                if r["agent_id"] == victim else r
                for r in rows
            ]
        _write_jsonl(lo1_dir / f"lo1_{excluded}" / "trades.jsonl", rows)

    agents = {a: FakeAgent(a) for a in roster}
    agents["nagi_seishiro"].playstyle = "confluence_only"
    return baseline_dir, tmp_path, agents


class TestFinisherClauseE2E:
    def _run(self, caches, *, clause: bool, tag: str):
        baseline_dir, lo1_root, agents = caches
        return fv.run_final_verdict(
            baseline_cache_dir=baseline_dir,
            lo1_root=lo1_root, lo1_tag="finisher",
            arm="phi41", tag=tag, out_dir=None,
            n_boot=300, agents_by_id=agents,
            c2_finisher_clause=clause,
        )

    def test_verdict_bearing_outputs_identical_with_flag(
        self, finisher_caches,
    ):
        r_off = self._run(finisher_caches, clause=False, tag="off")
        r_on = self._run(finisher_caches, clause=True, tag="on")
        assert r_off.verdict == r_on.verdict
        assert r_off.n_agents_passing == r_on.n_agents_passing
        for aid in fv.G7_FINAL_ROSTER:
            assert (
                r_off.per_agent[aid].bit_vector
                == r_on.per_agent[aid].bit_vector
            )
        assert r_off.advisory_c2_finisher is None
        assert r_on.advisory_c2_finisher is not None

    def test_advisory_block_and_squad_count(self, finisher_caches):
        r = self._run(finisher_caches, clause=True, tag="adv")
        nagi = r.per_agent["nagi_seishiro"]
        # Verdict-bearing C2 fails for Nagi (his removal changes
        # nothing for peers)...
        assert not nagi.criteria[2].passed
        # ...but the advisory clause passes with the two lifters.
        block = r.advisory_c2_finisher["nagi_seishiro"]
        assert block["clause_pass"] is True
        assert set(block["incoming_lifting_peers"]) == {
            "bachira_meguru", "itoshi_rin",
        }
        # Advisory squad count = verdict-bearing count + Nagi iff C2
        # was his only failure.
        fails = [
            i for i in range(1, 7)
            if not nagi.criteria[i].passed
        ]
        expected = r.n_agents_passing + (1 if fails == [2] else 0)
        assert r.advisory_n_agents_passing_with_clause == expected

    def test_only_eligible_agents_in_advisory_block(self, finisher_caches):
        r = self._run(finisher_caches, clause=True, tag="elig")
        assert set(r.advisory_c2_finisher.keys()) == {"nagi_seishiro"}
