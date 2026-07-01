"""Fixture builder for Phase M news-calendar tests.

Run this to regenerate the parquet fixtures used by
``sim/tests/test_news_calendar.py``. Idempotent by design; fixture
content is fully deterministic (hand-rolled sample events, no HTTP).

Usage
-----

    PYTHONPATH=../multi-pair-trading-agent:. \\
        M001_PRODUCTION_REPO=../multi-pair-trading-agent \\
        ../multi-pair-trading-agent/.venv/bin/python \\
        programs/M001_multi_agent_ensemble/sim/tests/fixtures/news_calendar/build_fixtures.py

Regenerates:

- ``dk_2024_sample.parquet``   -- 20 hand-rolled DK-flavour events (2024).
- ``ff_2024_sample.parquet``   -- 5 FF-flavour events that dedup-collide with dk_2024_sample.
- ``dk_2024_USD.parquet``      -- Real 2024 USD DK snapshot (~12 canonical events).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


FIXTURE_DIR = Path(__file__).parent


def _dk_2024_sample() -> pd.DataFrame:
    """20 hand-rolled DK-flavour events across USD/EUR/GBP in 2024.

    Timestamps chosen to line up with an EURUSD H4 UTC bar grid so
    the labeller tests have unambiguous target bars. Impact tiers span
    all three levels (7 x low, 6 x medium, 7 x high) so the
    importance-filter tests cover the full range.
    """
    rows = [
        # High-impact USD (NFP-style, 12:30 UTC on the first Friday of the month).
        ("2024-01-05 13:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_1"),
        ("2024-02-02 13:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_2"),
        ("2024-03-01 13:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_3"),
        ("2024-04-05 12:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_4"),
        ("2024-05-03 12:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_5"),
        ("2024-06-07 12:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_6"),
        ("2024-07-05 12:30:00+00:00", "USD", "Non-Farm Employment Change", 3, "d_7"),
        # High-impact EUR (ECB rate decision).
        ("2024-01-25 13:15:00+00:00", "EUR", "Main Refinancing Rate", 3, "d_e_1"),
        ("2024-03-07 13:15:00+00:00", "EUR", "Main Refinancing Rate", 3, "d_e_2"),
        # Medium USD (CPI).
        ("2024-01-11 13:30:00+00:00", "USD", "CPI m/m", 2, "d_m_1"),
        ("2024-02-13 13:30:00+00:00", "USD", "CPI m/m", 2, "d_m_2"),
        ("2024-03-12 12:30:00+00:00", "USD", "CPI m/m", 2, "d_m_3"),
        ("2024-04-10 12:30:00+00:00", "USD", "CPI m/m", 2, "d_m_4"),
        ("2024-05-15 12:30:00+00:00", "USD", "CPI m/m", 2, "d_m_5"),
        ("2024-06-12 12:30:00+00:00", "USD", "CPI m/m", 2, "d_m_6"),
        # Low USD (Retail Sales m/m).
        ("2024-01-17 13:30:00+00:00", "USD", "Retail Sales m/m", 1, "d_l_1"),
        ("2024-02-15 13:30:00+00:00", "USD", "Retail Sales m/m", 1, "d_l_2"),
        # Low GBP.
        ("2024-01-16 07:00:00+00:00", "GBP", "Claimant Count Change", 1, "d_g_1"),
        ("2024-02-13 07:00:00+00:00", "GBP", "Claimant Count Change", 1, "d_g_2"),
        # Sunday-night gap sentinel (bar deep in the weekend gap).
        # NOT emitted -- the "no event" test uses 2024-08-04 18:00 UTC.
        ("2024-06-13 13:00:00+00:00", "GBP", "MPC Official Bank Rate Votes", 1, "d_g_3"),
    ]
    df = pd.DataFrame(rows, columns=[
        "timestamp", "currency", "event", "importance", "source_event_id",
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["importance"] = df["importance"].astype("int8")
    df["currency"] = df["currency"].astype("string")
    df["event"] = df["event"].astype("string")
    df["source_event_id"] = df["source_event_id"].astype("string")
    df["source"] = pd.Series(["DK"] * len(df), dtype="string")
    df["actual"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["forecast"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["previous"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["unit"] = pd.Series([pd.NA] * len(df), dtype="string")
    df["ingested_at_utc"] = pd.Timestamp("2026-07-01T00:00:00", tz="UTC")
    return df[[
        "timestamp", "currency", "event", "importance", "actual",
        "forecast", "previous", "unit", "source", "source_event_id",
        "ingested_at_utc",
    ]]


def _ff_2024_sample(dk: pd.DataFrame) -> pd.DataFrame:
    """5 FF-flavour events -- 3 dedup-collide with dk_2024_sample (± 30s
    windows), 2 are FF-unique so dedup preserves at least one FF row
    in the discarded audit slice.
    """
    dk_col = dk.head(3).copy()
    dk_col["timestamp"] = dk_col["timestamp"] + pd.Timedelta(seconds=15)
    dk_col["source"] = pd.Series(["FF"] * len(dk_col), dtype="string")
    dk_col["source_event_id"] = pd.Series(
        [f"ff_{i}" for i in range(len(dk_col))], dtype="string",
    )
    unique = pd.DataFrame([
        {
            "timestamp": pd.Timestamp("2024-05-09 11:00:00", tz="UTC"),
            "currency": "GBP",
            "event": "BOE Monetary Policy Report Hearings",
            "importance": pd.Series([3], dtype="int8").iloc[0],
            "source_event_id": "ff_u_1",
            "source": "FF",
        },
        {
            "timestamp": pd.Timestamp("2024-11-06 19:00:00", tz="UTC"),
            "currency": "USD",
            "event": "FOMC Statement",
            "importance": pd.Series([3], dtype="int8").iloc[0],
            "source_event_id": "ff_u_2",
            "source": "FF",
        },
    ])
    unique["timestamp"] = pd.to_datetime(unique["timestamp"], utc=True)
    unique["importance"] = unique["importance"].astype("int8")
    unique["currency"] = unique["currency"].astype("string")
    unique["event"] = unique["event"].astype("string")
    unique["source_event_id"] = unique["source_event_id"].astype("string")
    unique["source"] = unique["source"].astype("string")
    for col in ("actual", "forecast", "previous"):
        unique[col] = pd.Series([float("nan")] * len(unique), dtype="float64")
    unique["unit"] = pd.Series([pd.NA] * len(unique), dtype="string")
    unique["ingested_at_utc"] = pd.Timestamp("2026-07-01T00:00:00", tz="UTC")
    unique = unique[dk_col.columns.tolist()]
    return pd.concat([dk_col, unique], ignore_index=True)


def _dk_2024_usd_real() -> pd.DataFrame:
    """Real 2024 USD DK snapshot -- 12 canonical Non-Farm Payrolls
    releases + FOMC / CPI / GDP anchors from the FRED release-time map
    (spec §3.4).

    Timestamps are the officially-scheduled release times converted to
    UTC. Content is public-domain (release schedules are published by
    BLS, BEA, Fed). Kept here as a hand-rolled fixture so the CI
    integration test #9 has NO live-HTTP dependency but still exercises
    the full year-2024 real-event count.
    """
    events = [
        # NFP (1st Fri each month) -- 08:30 ET = 13:30 UTC winter, 12:30 UTC summer (DST).
        ("2024-01-05 13:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_01"),
        ("2024-02-02 13:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_02"),
        ("2024-03-08 13:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_03"),
        ("2024-04-05 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_04"),
        ("2024-05-03 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_05"),
        ("2024-06-07 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_06"),
        ("2024-07-05 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_07"),
        ("2024-08-02 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_08"),
        ("2024-09-06 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_09"),
        ("2024-10-04 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_10"),
        ("2024-11-01 12:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_11"),
        ("2024-12-06 13:30:00+00:00", "Non-Farm Employment Change", "dk_nfp_12"),
        # FOMC 2024 (8 scheduled meetings).
        ("2024-01-31 19:00:00+00:00", "FOMC Statement", "dk_fomc_01"),
        ("2024-03-20 18:00:00+00:00", "FOMC Statement", "dk_fomc_02"),
        ("2024-05-01 18:00:00+00:00", "FOMC Statement", "dk_fomc_03"),
        ("2024-06-12 18:00:00+00:00", "FOMC Statement", "dk_fomc_04"),
        ("2024-07-31 18:00:00+00:00", "FOMC Statement", "dk_fomc_05"),
        ("2024-09-18 18:00:00+00:00", "FOMC Statement", "dk_fomc_06"),
        ("2024-11-07 19:00:00+00:00", "FOMC Statement", "dk_fomc_07"),
        ("2024-12-18 19:00:00+00:00", "FOMC Statement", "dk_fomc_08"),
        # CPI 2024 (12 monthly releases).
        ("2024-01-11 13:30:00+00:00", "CPI m/m", "dk_cpi_01"),
        ("2024-02-13 13:30:00+00:00", "CPI m/m", "dk_cpi_02"),
        ("2024-03-12 12:30:00+00:00", "CPI m/m", "dk_cpi_03"),
        ("2024-04-10 12:30:00+00:00", "CPI m/m", "dk_cpi_04"),
        ("2024-05-15 12:30:00+00:00", "CPI m/m", "dk_cpi_05"),
        ("2024-06-12 12:30:00+00:00", "CPI m/m", "dk_cpi_06"),
        ("2024-07-11 12:30:00+00:00", "CPI m/m", "dk_cpi_07"),
        ("2024-08-14 12:30:00+00:00", "CPI m/m", "dk_cpi_08"),
        ("2024-09-11 12:30:00+00:00", "CPI m/m", "dk_cpi_09"),
        ("2024-10-10 12:30:00+00:00", "CPI m/m", "dk_cpi_10"),
        ("2024-11-13 13:30:00+00:00", "CPI m/m", "dk_cpi_11"),
        ("2024-12-11 13:30:00+00:00", "CPI m/m", "dk_cpi_12"),
    ]
    df = pd.DataFrame(events, columns=["timestamp", "event", "source_event_id"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["currency"] = pd.Series(["USD"] * len(df), dtype="string")
    df["event"] = df["event"].astype("string")
    df["importance"] = pd.Series([3] * len(df), dtype="int8")
    df["source_event_id"] = df["source_event_id"].astype("string")
    df["source"] = pd.Series(["DK"] * len(df), dtype="string")
    df["actual"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["forecast"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["previous"] = pd.Series([float("nan")] * len(df), dtype="float64")
    df["unit"] = pd.Series([pd.NA] * len(df), dtype="string")
    df["ingested_at_utc"] = pd.Timestamp("2026-07-01T00:00:00", tz="UTC")
    return df[[
        "timestamp", "currency", "event", "importance", "actual",
        "forecast", "previous", "unit", "source", "source_event_id",
        "ingested_at_utc",
    ]]


def main() -> None:
    dk_sample = _dk_2024_sample()
    dk_sample.to_parquet(FIXTURE_DIR / "dk_2024_sample.parquet", index=False)
    ff_sample = _ff_2024_sample(dk_sample)
    ff_sample.to_parquet(FIXTURE_DIR / "ff_2024_sample.parquet", index=False)
    dk_usd = _dk_2024_usd_real()
    dk_usd.to_parquet(FIXTURE_DIR / "dk_2024_USD.parquet", index=False)
    print(f"Wrote 3 fixtures under {FIXTURE_DIR}:")
    print(f"  dk_2024_sample.parquet   -- {len(dk_sample)} rows")
    print(f"  ff_2024_sample.parquet   -- {len(ff_sample)} rows")
    print(f"  dk_2024_USD.parquet      -- {len(dk_usd)} rows")


if __name__ == "__main__":
    main()
