"""Phase X-kunigami Wild Card drawdown gate tests (PROTOCOL.md sec 2).

Covers the pure gate transition (`kunigami_gate_step`) and the locked
constants:

  1. Trip at DD >= 25% from peak, release only at DD <= 12.5%
     (hysteresis: between the two levels the gate holds state).
  2. Peak ratchets up with new equity highs; drawdown is always
     measured against the running peak, not the starting equity.
  3. Locked constants match the pre-registration (trip = the Phi5
     sec 6 stop-rule bound 0.25; release = half of that; 1 pip = $1
     at the sandbox's fixed 0.1 lot).
  4. Driver default keeps the gate OFF so every sealed cache stays
     byte-identical.
"""
from __future__ import annotations

import inspect

from programs.M001_multi_agent_ensemble.sim.scoring.run_phi4_squad_gate import (
    KUNIGAMI_GATE_DOLLARS_PER_PIP,
    KUNIGAMI_GATE_RELEASE_DD,
    KUNIGAMI_GATE_TRIP_DD,
    _drive_squad_replay,
    kunigami_gate_step,
)


class TestLockedConstants:

    def test_trip_is_phi5_stop_rule_bound(self):
        assert KUNIGAMI_GATE_TRIP_DD == 0.25

    def test_release_is_half_trip(self):
        assert KUNIGAMI_GATE_RELEASE_DD == 0.125

    def test_sandbox_pip_dollar_convention(self):
        # 0.1 lot x $10/pip/lot = $1/pip on the $100 sandbox.
        assert KUNIGAMI_GATE_DOLLARS_PER_PIP == 1.0


class TestGateTransitions:

    def test_no_trip_below_threshold(self):
        # $100 -> $76 is a 24% DD: still below the 25% trip level.
        equity, peak, tripped, dd, event = kunigami_gate_step(
            equity=100.0, peak=100.0, tripped=False, pnl_pips=-24.0,
        )
        assert (equity, peak) == (76.0, 100.0)
        assert tripped is False
        assert event is None
        assert dd == 0.24

    def test_trips_at_exactly_25_percent(self):
        equity, peak, tripped, dd, event = kunigami_gate_step(
            equity=100.0, peak=100.0, tripped=False, pnl_pips=-25.0,
        )
        assert tripped is True
        assert event == "trip"
        assert dd == 0.25

    def test_holds_tripped_in_hysteresis_band(self):
        # Recovery to 20% DD is inside the (12.5%, 25%) band: the gate
        # must HOLD tripped -- releasing here would be flapping.
        equity, peak, tripped, dd, event = kunigami_gate_step(
            equity=75.0, peak=100.0, tripped=True, pnl_pips=+5.0,
        )
        assert equity == 80.0
        assert tripped is True
        assert event is None

    def test_releases_at_or_below_release_level(self):
        # Recovery to 12.5% DD exactly: release fires.
        equity, peak, tripped, dd, event = kunigami_gate_step(
            equity=80.0, peak=100.0, tripped=True, pnl_pips=+7.5,
        )
        assert equity == 87.5
        assert tripped is False
        assert event == "release"
        assert dd == 0.125

    def test_holds_untripped_in_hysteresis_band(self):
        # 20% DD reached from above while NOT tripped: gate stays open
        # (only >= 25% trips it).
        _, _, tripped, _, event = kunigami_gate_step(
            equity=90.0, peak=100.0, tripped=False, pnl_pips=-10.0,
        )
        assert tripped is False
        assert event is None

    def test_peak_ratchets_on_new_high(self):
        equity, peak, tripped, dd, _ = kunigami_gate_step(
            equity=100.0, peak=100.0, tripped=False, pnl_pips=+20.0,
        )
        assert (equity, peak) == (120.0, 120.0)
        assert dd == 0.0
        # A subsequent 25% fall from the NEW peak trips even though
        # equity is still above the starting $100.
        equity, peak, tripped, dd, event = kunigami_gate_step(
            equity=equity, peak=peak, tripped=tripped, pnl_pips=-30.0,
        )
        assert equity == 90.0
        assert tripped is True
        assert event == "trip"

    def test_full_cycle_trip_then_release(self):
        equity, peak, tripped = 100.0, 100.0, False
        events = []
        for pnl in (-10.0, -20.0, +5.0, +15.0, +5.0):
            equity, peak, tripped, _, event = kunigami_gate_step(
                equity=equity, peak=peak, tripped=tripped, pnl_pips=pnl,
            )
            events.append(event)
        # -30 total trips at step 2; +5 (25% dd) holds; +15 (10% dd)
        # releases; final +5 stays open.
        assert events == [None, "trip", None, "release", None]
        assert tripped is False

    def test_negative_equity_reports_full_drawdown(self):
        # The phi41 control curve has breached far past -100% in past
        # windows; the gate must stay tripped there, not divide-by-zero.
        equity, peak, tripped, dd, _ = kunigami_gate_step(
            equity=10.0, peak=100.0, tripped=True, pnl_pips=-50.0,
        )
        assert equity == -40.0
        assert dd == 1.4
        assert tripped is True


class TestDriverDefaultOff:

    def test_gate_flag_defaults_false(self):
        # Sealed-cache guarantee: unless a caller explicitly opts in,
        # the replay driver never engages the gate.
        sig = inspect.signature(_drive_squad_replay)
        assert sig.parameters["kunigami_wildcard_gate"].default is False
