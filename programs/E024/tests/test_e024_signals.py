"""E024 stall-signal unit tests.

Coverage per the deliverables checklist:

- ``test_s1_wallclock_never_fires_below_activation`` — MFE < activation_R
  throughout ⇒ rule returns None on every bar.
- ``test_s1_wallclock_fires_after_stall_secs`` — MFE plateau after
  activation ⇒ rule fires at the correct bar (the first bar whose
  ``bar.time − mfe_ts`` crosses ``stall_secs``).
- ``test_s3_reversal_direction_symmetric_short`` — S3 detector on a
  short mirrors the long behaviour (E ↔ min, cross-back becomes
  cross-up).
- ``test_s4_bar_stall_resets_on_new_mfe`` — MFE extends on the 2nd of
  three post-activation H1 buckets ⇒ counter resets, no fire.
- ``test_false_positive_labeling`` — arm fires on a trade whose
  original exit_reason was "tp" ⇒ counted as false positive by the
  diagnostic computed inside the sweep.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[3]))  # repo root

from programs._shared.counterfactual_replay.replay import (  # noqa: E402
    PIP,
    PRIORITY_E024_STALL,
    Bar,
    TradeRecord,
    replay,
)
from programs.E024.stall_signals import (  # noqa: E402
    SIGNAL_S1,
    SIGNAL_S3,
    SIGNAL_S4,
    E024StallRule,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _bars_at(times: list[datetime], ohlc: list[tuple[float, float, float, float]]) -> list[Bar]:
    assert len(times) == len(ohlc)
    return [
        Bar(time=t, open=o, high=h, low=l, close=c)
        for t, (o, h, l, c) in zip(times, ohlc)
    ]


def _make_synthetic_trade(
    direction: str,
    entry: float,
    stop_pips: float,
    path: list[Bar],
    exit_reason: str = "path_end",
    exit_price: float | None = None,
    tp_r: float = 1.5,
) -> TradeRecord:
    """Build a TradeRecord from a synthetic path. MFE/MAE are derived
    (matches the exporter's deterministic rule).

    ``tp_r`` overrides the 1.5R default so signal-under-test paths can
    exceed activation without ever crossing TP (which would end the trade
    before the stall detector had a chance to fire)."""
    d = +1 if direction == "long" else -1
    take_profit = entry + d * tp_r * stop_pips * PIP
    soft_stop = entry - d * stop_pips * PIP

    # Compute MFE/MAE/mfe_ts from the path (SPEC §1 derivation).
    mfe_pips = 0.0
    mae_pips = 0.0
    mfe_ts = path[0].time
    mae_ts = path[0].time
    for b in path:
        fav = (b.high - entry) / PIP if d == +1 else (entry - b.low) / PIP
        adv = (entry - b.low) / PIP if d == +1 else (b.high - entry) / PIP
        if fav > mfe_pips:
            mfe_pips, mfe_ts = fav, b.time
        if adv > mae_pips:
            mae_pips, mae_ts = adv, b.time

    if exit_price is None:
        exit_price = take_profit if exit_reason == "tp" else path[-1].close
    pnl_pips = d * (exit_price - entry) / PIP
    r = pnl_pips / stop_pips if stop_pips > 0 else 0.0

    return TradeRecord(
        trade_id="SYN_H4_00000",
        symbol="EURUSD",
        tf="H4",
        direction=direction,
        entry_time=path[0].time,
        entry=entry,
        stop=soft_stop,
        soft_stop=soft_stop,
        take_profit=take_profit,
        stop_pips=stop_pips,
        tp_pips=tp_r * stop_pips,
        r=r,
        pnl_pips=pnl_pips,
        exit_time=path[-1].time,
        exit_price=exit_price,
        exit_reason=exit_reason,
        mfe_pips=mfe_pips,
        mae_pips=mae_pips,
        mfe_ts=mfe_ts,
        mae_ts=mae_ts,
        mfe_r=mfe_pips / stop_pips,
        mae_r=mae_pips / stop_pips,
        path=path,
        path_resolution="M5",
    )


# ---------------------------------------------------------------------------
# S1 tests.
# ---------------------------------------------------------------------------

def test_s1_wallclock_never_fires_below_activation() -> None:
    """MFE stays below activation_R for the entire trade ⇒ rule never fires."""
    entry = 1.1000
    stop_pips = 20.0
    # Long. MFE reaches at most +10 pips (0.5R) — below activation 1.30R.
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)
    times = [t0 + timedelta(minutes=5 * i) for i in range(60)]  # 5 h of M5 bars
    ohlc = [
        (entry, entry + 10 * PIP, entry - 5 * PIP, entry + 5 * PIP)
        for _ in range(60)
    ]
    path = _bars_at(times, ohlc)
    trade = _make_synthetic_trade("long", entry, stop_pips, path,
                                   exit_reason="path_end",
                                   exit_price=entry + 5 * PIP)

    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S1, stall_secs=900.0)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is None, (
        f"S1 should not fire when MFE never crosses activation, but fired: {rule.fired_details}"
    )
    # Alt exit falls back to the original (SPEC §4 fall-through).
    assert alt.exit_reason == trade.exit_reason


def test_s1_wallclock_fires_after_stall_secs() -> None:
    """Long trade with MFE peaking at bar 4, plateau ≥ stall_secs, arm fires
    before TP is crossed.

    Geometry: stop_pips = 20, TP at 5R (100 pips) — wide enough that the
    MFE plateau at +40 pips never crosses TP. This isolates the S1 timer
    behaviour from the exit-priority interaction with TP."""
    entry = 1.1000
    stop_pips = 20.0
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)
    times = [t0 + timedelta(minutes=5 * i) for i in range(30)]

    ohlc: list[tuple[float, float, float, float]] = []
    for i in range(30):
        if i <= 4:
            fav = 8.0 * (i + 1)  # +8, +16, +24, +32, +40
        else:
            fav = 25.0  # plateau, does not exceed prior MFE 40 pips
        h = entry + fav * PIP
        c = entry + (fav - 3.0) * PIP
        # BE migration fires the bar AFTER MFE crosses 1.0R = 20 pips (bar 2).
        # From bar 3 onward the BE stop is at ``entry``; keep low ≥ entry so
        # BE doesn't snipe the trade before the S1 timer expires.
        l = (entry - 5.0 * PIP) if i < 2 else (entry + 15.0 * PIP)
        ohlc.append((entry, h, l, c))
    path = _bars_at(times, ohlc)
    trade = _make_synthetic_trade("long", entry, stop_pips, path,
                                   exit_reason="path_end", tp_r=5.0)

    # MFE peak at bar 4 (fav = 40 pips → mfe_pips = 40 at 08:20).
    # mfe_ts sticks at 08:20. First bar where bar.time − mfe_ts ≥ 3600 s = 60 min:
    # 08:20 + 60 min = 09:20 = t0 + 80 min → bar 16.
    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S1, stall_secs=3600.0)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is not None, "S1 should fire after plateau exceeds stall_secs"
    assert rule.fired_details.sub_signal == "S1"
    assert rule.fired_details.bar_index == 16, (
        f"Expected fire at bar 16 (60 min after mfe_ts at bar 4), got {rule.fired_details.bar_index}"
    )
    assert rule.fired_details.elapsed_since_mfe_ts >= 3600.0
    assert alt.exit_reason == PRIORITY_E024_STALL


# ---------------------------------------------------------------------------
# S3 tests.
# ---------------------------------------------------------------------------

def test_s3_reversal_direction_symmetric_short() -> None:
    """For a short, S3 fires when the newest H1 close ≥ min(prior 3 closes) + 3 pips.

    Build a synthetic short with H1 closes {1.29970, 1.29960, 1.29950, 1.29985}.
    Latest close 1.29985; prior 3 min = 1.29950. Reversal by 1.29985 − 1.29950
    = 35 pips-e5 = 3.5 pips ≥ 3.0 pips ⇒ fires.
    """
    entry = 1.3000
    stop_pips = 30.0
    # Build a path with 5 H1 buckets. Each bucket is 12 M5 bars ending at :55.
    # For simplicity, use one bar per H1 bucket (H1 path resolution).
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)  # bucket 08:00
    # Bar 0 covers 08:00 bucket — MFE must reach activation_R=1.30 → 39 pips.
    # High for a short = "adverse", low = "favourable".
    bars: list[Bar] = []
    # 08:00 bucket — MFE 40 pips (low = entry − 40p). Sets mfe_ts at 08:00.
    bars.append(Bar(time=t0, open=entry, high=entry + 3 * PIP,
                    low=entry - 40 * PIP, close=1.29970))
    # 09:00 bucket — small chop, MFE unchanged.
    bars.append(Bar(time=t0 + timedelta(hours=1), open=1.29970,
                    high=1.29985, low=1.29960, close=1.29960))
    # 10:00 bucket — small chop.
    bars.append(Bar(time=t0 + timedelta(hours=2), open=1.29960,
                    high=1.29975, low=1.29940, close=1.29950))
    # 11:00 bucket — reversal close ≥ prior 3-min + 3p.
    # Prior 3 closes are {1.29970, 1.29960, 1.29950}. Min = 1.29950.
    # We need close ≥ 1.29950 + 3 pips = 1.29980. Use 1.29985.
    bars.append(Bar(time=t0 + timedelta(hours=3), open=1.29950,
                    high=1.29990, low=1.29945, close=1.29985))
    # 12:00 bucket — one extra bar so the 11:00 bucket's completion is DETECTED.
    bars.append(Bar(time=t0 + timedelta(hours=4), open=1.29985,
                    high=1.29990, low=1.29970, close=1.29975))

    trade = _make_synthetic_trade("short", entry, stop_pips, bars,
                                   exit_reason="path_end", tp_r=5.0)

    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S3, stall_secs=None)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is not None, "S3 should fire on the 4th H1 completion for a short"
    assert rule.fired_details.sub_signal == "S3"
    assert alt.exit_reason == PRIORITY_E024_STALL


# ---------------------------------------------------------------------------
# S4 tests.
# ---------------------------------------------------------------------------

def test_s4_bar_stall_resets_on_new_mfe() -> None:
    """S4 needs 3 consecutive completed H1 bars after activation without a
    new MFE extension. If bar 2 (of 3) extends MFE, the counter resets to 0
    and S4 does NOT fire.

    Long. Activation reached in bucket 1. Bucket 2 does NOT extend MFE
    (no-extend count = 1). Bucket 3 DOES extend MFE (counter resets to 0).
    Bucket 4 does NOT extend (count = 1). Bucket 5 does NOT extend (count = 2).
    Trade ends before count reaches 3.
    """
    entry = 1.1000
    stop_pips = 20.0
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)
    bars: list[Bar] = []
    # Bucket 08:00 — MFE 30 pips (1.50R activation).
    bars.append(Bar(time=t0, open=entry, high=entry + 30 * PIP,
                    low=entry - 5 * PIP, close=entry + 25 * PIP))
    # Bucket 09:00 — no new high, MFE unchanged. no_extend = 1.
    bars.append(Bar(time=t0 + timedelta(hours=1), open=entry + 25 * PIP,
                    high=entry + 28 * PIP, low=entry + 15 * PIP,
                    close=entry + 20 * PIP))
    # Bucket 10:00 — NEW HIGH 35 pips. Counter resets to 0.
    bars.append(Bar(time=t0 + timedelta(hours=2), open=entry + 20 * PIP,
                    high=entry + 35 * PIP, low=entry + 18 * PIP,
                    close=entry + 30 * PIP))
    # Bucket 11:00 — no new high. count = 1.
    bars.append(Bar(time=t0 + timedelta(hours=3), open=entry + 30 * PIP,
                    high=entry + 33 * PIP, low=entry + 20 * PIP,
                    close=entry + 25 * PIP))
    # Bucket 12:00 — no new high. count = 2.
    bars.append(Bar(time=t0 + timedelta(hours=4), open=entry + 25 * PIP,
                    high=entry + 32 * PIP, low=entry + 18 * PIP,
                    close=entry + 23 * PIP))
    # A trailing bar so bucket 12:00 completes.
    bars.append(Bar(time=t0 + timedelta(hours=5), open=entry + 23 * PIP,
                    high=entry + 25 * PIP, low=entry + 15 * PIP,
                    close=entry + 20 * PIP))

    trade = _make_synthetic_trade("long", entry, stop_pips, bars,
                                   exit_reason="path_end", tp_r=5.0)

    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S4, stall_secs=None)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is None, (
        f"S4 should NOT fire when MFE extends in the middle bucket, "
        f"but fired at {rule.fired_details}"
    )
    assert alt.exit_reason == trade.exit_reason


def test_s4_bar_stall_fires_on_3rd_flat_bucket() -> None:
    """Companion positive-side test for S4: 3 consecutive flat buckets ⇒ fires."""
    entry = 1.1000
    stop_pips = 20.0
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)
    bars: list[Bar] = []
    bars.append(Bar(time=t0, open=entry, high=entry + 30 * PIP,
                    low=entry - 5 * PIP, close=entry + 25 * PIP))
    for hr in range(1, 5):
        # No new highs; MFE plateaus.
        bars.append(Bar(
            time=t0 + timedelta(hours=hr),
            open=entry + 25 * PIP,
            high=entry + 28 * PIP,
            low=entry + 15 * PIP,
            close=entry + 20 * PIP,
        ))
    trade = _make_synthetic_trade("long", entry, stop_pips, bars,
                                   exit_reason="path_end", tp_r=5.0)
    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S4, stall_secs=None)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is not None, "S4 should fire after 3 consecutive flat H1 buckets"
    assert rule.fired_details.sub_signal == "S4"
    assert alt.exit_reason == PRIORITY_E024_STALL


# ---------------------------------------------------------------------------
# False-positive labelling.
# ---------------------------------------------------------------------------

def test_false_positive_labeling() -> None:
    """Crafted trade whose original ``exit_reason == "tp"`` and whose path
    lets the S1 stall detector fire BEFORE the TP bar. This mirrors the
    sweep's Δ P(false positive) diagnostic: an arm-fire on a clean-TP
    baseline is counted as a false positive.

    Geometry care: once MFE ≥ 1.0R the engine's BE migration (SPEC §4
    invariant) sets the stop to entry on the next bar, so all subsequent
    bars must keep ``low > entry`` or the trade will exit at BE before
    the arm has a chance to fire. Post-plateau bars therefore hold
    ``low = entry + 15 pips`` (well above BE)."""
    entry = 1.1000
    stop_pips = 20.0
    # TP at entry + 1.5R = entry + 30 pips = 1.10300.
    t0 = datetime(2020, 1, 1, 8, 0, tzinfo=UTC)

    ohlc: list[tuple[float, float, float, float]] = []
    times: list[datetime] = []
    # Use activation_r = 1.30 (robustly clear of 1.45 FP-boundary near TP).
    # Bars 0-3 ramp to +27 pips (mfe_r = 1.35). Bars 4-30 plateau at high = +25.
    # Bar 31 crosses TP at high = +31 pips. Between bar 3 (mfe_ts=08:15) and
    # TP at bar 31 (10:35), our S1 fires at 09:15 (bar 15).
    for i in range(31):
        times.append(t0 + timedelta(minutes=5 * i))
        if i == 0:
            fav = 8.0
            low_off = -5.0
        elif i == 1:
            fav = 16.0
            low_off = 0.0
        elif i == 2:
            fav = 22.0
            low_off = 10.0
        elif i == 3:
            fav = 27.0  # mfe_r = 27/20 = 1.35 ≥ 1.30 activation
            low_off = 15.0
        else:
            fav = 25.0  # plateau, below MFE 27; mfe_ts sticks at bar 3
            low_off = 15.0  # above BE stop (entry) so BE doesn't snipe
        ohlc.append((entry, entry + fav * PIP, entry + low_off * PIP, entry + (fav - 5) * PIP))
    # Bar 31 — TP hit (high crosses 1.10300).
    times.append(t0 + timedelta(minutes=5 * 31))
    ohlc.append((entry + 20 * PIP, entry + 31 * PIP, entry + 15 * PIP, entry + 30 * PIP))
    path = _bars_at(times, ohlc)

    trade = _make_synthetic_trade(
        "long", entry, stop_pips, path,
        exit_reason="tp",
        exit_price=entry + 30 * PIP,
    )

    # S1 with stall_secs = 3600 → fires at bar 3 + 12 = bar 15 (60 min after
    # mfe_ts at bar 3 = 08:15 → fire at 09:15). This is BEFORE the TP-bar
    # at 10:35 (bar 31), so the alt-exit becomes stall and the baseline's
    # "tp" outcome is pre-empted — the false-positive case.
    rule = E024StallRule(activation_r=1.30, signal=SIGNAL_S1, stall_secs=3600.0)
    rule.reset()
    alt = replay(trade, rule=rule)
    assert rule.fired_details is not None, "S1 should fire during the plateau"
    assert alt.exit_reason == PRIORITY_E024_STALL, (
        f"Expected stall exit, got {alt.exit_reason} (baseline had a TP that "
        f"our rule pre-empted — this is the false-positive case)"
    )

    is_false_positive = (
        alt.exit_reason == PRIORITY_E024_STALL
        and trade.exit_reason == "tp"
    )
    assert is_false_positive is True, (
        "A trade whose baseline exit_reason == 'tp' but whose arm-replay "
        "exit_reason == PRIORITY_E024_STALL must count as a false positive."
    )
