"""Context-alpha decomposition: Rin:USDJPY, survey (squad) vs AN-1
isolation. Read-only mechanism question on consumed tapes (declared):
which trades did squad context delete, were they systematically the
losers, and which mechanism deleted them?

Survey tape: phase_al_tier1_field_survey results/raw/survey_postfix
(full roster, 2015-01 -> 2022-12). Isolation tape: AN-1 design
start_0 (Rin only, same window). Same engine commit, same bars ->
identical signal at identical entry_time; the difference IS the
squad context. Burn-in 92d applied to both. Costs 1x = 1.0 pip RT.

    python context_alpha_rin_usdjpy.py
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SURVEY = (HERE.parent / "phase_al_tier1_field_survey" / "results"
          / "raw" / "survey_postfix")
ISO = HERE / "results" / "AN-1" / "USDJPY" / "design" / "start_0"
AGENT = "itoshi_rin"
SYMBOL = "USDJPY"
COST = 1.0
CUTOFF = datetime(2015, 1, 1, tzinfo=timezone.utc) + timedelta(days=92)


def load_trades(path: Path) -> dict[str, dict]:
    out = {}
    for line in (path / "trades.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        t = json.loads(line)
        if t["agent_id"] != AGENT or t["symbol"] != SYMBOL:
            continue
        if datetime.fromisoformat(t["entry_time"]) >= CUTOFF:
            out[t["entry_time"]] = t
    return out


def kpis(trades) -> dict:
    trades = list(trades)
    n = len(trades)
    if not n:
        return {"n": 0}
    pnls = [(t["pnl_pips"] or 0.0) - COST for t in trades]
    wins = [p for p in pnls if p > 0]
    gl = -sum(p for p in pnls if p <= 0)
    rs = [((t["pnl_pips"] or 0.0) - COST) / t["source_sl_pips"]
          for t in trades if (t.get("source_sl_pips") or 0) > 0]
    return {"n": n, "win_rate": round(len(wins) / n, 3),
            "pf": round(sum(wins) / gl, 3) if gl > 0 else 99.0,
            "mean_r": round(sum(rs) / len(rs), 4) if rs else None,
            "total_pips": round(sum(pnls), 1)}


def main() -> None:
    survey = load_trades(SURVEY)
    iso = load_trades(ISO)

    common = sorted(set(survey) & set(iso))
    deleted = sorted(set(iso) - set(survey))       # squad removed these
    squad_only = sorted(set(survey) - set(iso))    # state-divergence extras

    report = {
        "survey_all": kpis(survey.values()),
        "isolation_all": kpis(iso.values()),
        "filled_in_both": kpis(iso[k] for k in common),
        "deleted_by_squad_context": kpis(iso[k] for k in deleted),
        "squad_only_extras": kpis(survey[k] for k in squad_only),
    }

    # Mechanism attribution: Rin USDJPY rejections in the survey tape.
    reasons = Counter()
    for line in (SURVEY / "proposals_rejected.jsonl").read_text().splitlines():
        if not line.strip():
            continue
        p = json.loads(line)
        if p.get("symbol") != SYMBOL:
            continue
        who = p.get("loser_agent_id") or p.get("winner_agent_id")
        if who != AGENT:
            continue
        r = p.get("rejection_reason", "?")
        if r == "contest_loss" or p.get("winner_agent_id") not in (AGENT, None):
            r = f"contest_lost_to_{p.get('winner_agent_id')}"
        reasons[r] += 1
    report["survey_rejection_reasons_rin_usdjpy"] = dict(reasons.most_common())

    out = HERE / "results" / "context_alpha_rin_usdjpy.json"
    out.write_text(json.dumps(report, indent=2))
    for k, v in report.items():
        print(f"{k}: {v}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
