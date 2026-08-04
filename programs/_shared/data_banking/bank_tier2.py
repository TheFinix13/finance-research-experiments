"""Tier-2 field banking (D148): download H4+D1 history for the
instrument universe the squad has never touched, into the research
repo's OWN parquet store (data/parquet_tier2/). Standalone on
dukascopy-python — deliberately does NOT touch the v1 agent repo's
loader or cache.

Usage:
    python bank_tier2.py [--group crosses|metals|energy|indices|crypto|all]

DATA_LEDGER note: possession is not consumption. Full 2015->present
history is banked, but per DATA_LEDGER rule 4 the 2023->present slice
of every Tier-1/Tier-2 field is SEALED: design work may only read
pre-2023; each seal opens once, by pre-registered protocol.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import dukascopy_python as duka
from dukascopy_python import instruments as ins

OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "parquet_tier2"

GROUPS: dict[str, dict[str, object]] = {
    "crosses": {
        "EURGBP": ins.INSTRUMENT_FX_CROSSES_EUR_GBP,
        "EURJPY": ins.INSTRUMENT_FX_CROSSES_EUR_JPY,
        "GBPJPY": ins.INSTRUMENT_FX_CROSSES_GBP_JPY,
        "EURCHF": ins.INSTRUMENT_FX_CROSSES_EUR_CHF,
        "EURAUD": ins.INSTRUMENT_FX_CROSSES_EUR_AUD,
        "AUDJPY": ins.INSTRUMENT_FX_CROSSES_AUD_JPY,
        "CADJPY": ins.INSTRUMENT_FX_CROSSES_CAD_JPY,
        "AUDNZD": ins.INSTRUMENT_FX_CROSSES_AUD_NZD,
        "GBPCHF": ins.INSTRUMENT_FX_CROSSES_GBP_CHF,
        "NZDJPY": ins.INSTRUMENT_FX_CROSSES_NZD_JPY,
    },
    "metals": {
        "XAUUSD": ins.INSTRUMENT_FX_METALS_XAU_USD,
        "XAGUSD": ins.INSTRUMENT_FX_METALS_XAG_USD,
    },
    "energy": {
        "USOIL": ins.INSTRUMENT_CMD_ENERGY_E_LIGHT,   # WTI
        "UKOIL": ins.INSTRUMENT_CMD_ENERGY_E_BRENT,
        "NATGAS": ins.INSTRUMENT_CMD_ENERGY_GAS_CMD_USD,
    },
    "indices": {
        "USTEC": ins.INSTRUMENT_IDX_AMERICA_E_NQ_100,
        "US500": ins.INSTRUMENT_IDX_AMERICA_E_SANDP_500,
        "US30": ins.INSTRUMENT_IDX_AMERICA_E_D_J_IND,
        "DE40": ins.INSTRUMENT_IDX_EUROPE_E_DAAX,
        "UK100": ins.INSTRUMENT_IDX_EUROPE_E_FUTSEE_100,
        "JP225": ins.INSTRUMENT_IDX_ASIA_E_N225JAP,
    },
    "crypto": {
        "BTCUSD": ins.INSTRUMENT_VCCY_BTC_USD,
    },
}

INTERVALS = {"H4": duka.INTERVAL_HOUR_4, "D1": duka.INTERVAL_DAY_1}
START = datetime(2015, 1, 1, tzinfo=timezone.utc)


def bank(symbol: str, instrument: object) -> dict:
    row: dict[str, object] = {"symbol": symbol}
    end = datetime.now(timezone.utc)
    for tf_name, interval in INTERVALS.items():
        out = OUT_DIR / f"{symbol}_{tf_name}.parquet"
        if out.exists():
            row[tf_name] = "exists, skipped"
            continue
        df = duka.fetch(
            instrument=instrument, interval=interval,
            offer_side=duka.OFFER_SIDE_BID,
            start=START, end=end, max_retries=3,
        )
        if df is None or df.empty:
            row[tf_name] = "EMPTY"
            continue
        df.columns = [c.lower() for c in df.columns]
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        df.index.name = "time"
        if "volume" not in df.columns:
            df["volume"] = 0
        df = df[["open", "high", "low", "close", "volume"]]
        df.to_parquet(out)
        row[tf_name] = f"{len(df)} bars {df.index[0].date()} -> {df.index[-1].date()}"
        print(f"{symbol} {tf_name}: {row[tf_name]}", flush=True)
        time.sleep(2)  # be polite to the public datafeed
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="all", choices=[*GROUPS, "all"])
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    groups = GROUPS if args.group == "all" else {args.group: GROUPS[args.group]}
    manifest = []
    for gname, symbols in groups.items():
        for sym, instrument in symbols.items():
            print(f"=== {gname}/{sym} ===", flush=True)
            try:
                manifest.append(bank(sym, instrument))
            except Exception as exc:  # noqa: BLE001 - keep banking the rest
                print(f"{sym} FAILED: {exc}", flush=True)
                manifest.append({"symbol": sym, "error": str(exc)})
    (OUT_DIR / "BANKING_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    print("banking complete", flush=True)


if __name__ == "__main__":
    main()
