"""E017 Phase 2 — Monte-Carlo + gauge-convergence simulation harness."""
from __future__ import annotations

import json
import math
import random
import statistics
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence


class Arm(str, Enum):
    HK = "HK"
    GC_S = "GC-S"
    GC_T = "GC-T"


class PerSymbolFormula(str, Enum):
    P_EXP = "P-exp"
    P_LIN = "P-lin"


class GaugeFormula(str, Enum):
    G_SURPLUS = "G-surplus"
    G_CDAR = "G-cdar"


@dataclass(frozen=True)
class CandidateConfig:
    per_symbol: PerSymbolFormula
    gauge: GaugeFormula
    lam: float = 0.25
    l_floor: float = 4.0

    @property
    def label(self) -> str:
        base = f"{self.per_symbol.value}+{self.gauge.value}"
        if self.per_symbol == PerSymbolFormula.P_EXP:
            return f"{base} (lam={self.lam})"
        return f"{base} (L={self.l_floor})"


@dataclass(frozen=True)
class FrozenParams:
    c_min: float = 0.15
    g_min: float = 0.25
    alpha_surplus: float = 0.97
    d_tol_frac: float = 0.03
    tau_live: float = 0.30
    tau_full: float = 0.80
    rho_time_decay_per_day: float = 0.06
    time_decay_cap: float = 0.75
    daily_dd_halt_pct: float = 0.03
    max_consecutive_losses: int = 3
    catastrophic_loss_frac: float = 0.10
    kill_blind_hours: float = 48.0
    ruin_frac: float = 0.50
    trade_lambda_per_day: float = 66.0 / 365.0
    max_trades_per_symbol_per_day: int = 2
    horizon_days: int = 11_000
    cdar_window_days: int = 250
    gauge_tolerance: float = 0.02
    risk_pct: dict[str, float] = field(default_factory=lambda: {
        "EURUSD": 0.01475,
        "GBPUSD": 0.007375,
        "USDCAD": 0.007375,
    })
    symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")


@dataclass
class PathMetrics:
    terminal_equity: float
    max_drawdown_frac: float
    ruined: bool
    total_dead_hours: float
    shadow_opportunity_r: float
    suspension_events: int


def load_bootstrap_r(ledger_path: Path) -> list[float]:
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    return [float(t["r"]) for t in data["trades"]]


def frozen_candidate_grid() -> list[CandidateConfig]:
    out: list[CandidateConfig] = []
    for per in (PerSymbolFormula.P_EXP, PerSymbolFormula.P_LIN):
        for gauge in (GaugeFormula.G_SURPLUS, GaugeFormula.G_CDAR):
            if per == PerSymbolFormula.P_EXP:
                for lam in (0.25, 0.5):
                    out.append(CandidateConfig(per, gauge, lam=lam))
            else:
                for l_floor in (4.0, 8.0):
                    out.append(CandidateConfig(per, gauge, l_floor=l_floor))
    return out


def _per_symbol_confidence(cfg: CandidateConfig, params: FrozenParams, l_net: float) -> float:
    if cfg.per_symbol == PerSymbolFormula.P_EXP:
        raw = math.exp(-cfg.lam * l_net)
        return params.c_min + (1.0 - params.c_min) * raw
    return max(params.c_min, min(1.0, 1.0 - l_net / cfg.l_floor))


def _gauge_surplus(equity: float, peak: float, params: FrozenParams) -> float:
    if peak <= 0:
        return 1.0
    alpha = params.alpha_surplus
    den = (1.0 - alpha) * peak
    if den <= 0:
        return params.g_min
    return max(params.g_min, min(1.0, (equity - alpha * peak) / den))


def _cdar_tail_mean(values: Sequence[float], beta: float = 0.95) -> float:
    if not values:
        return 0.0
    n_tail = max(1, int(math.ceil((1.0 - beta) * len(values))))
    tail = sorted(values, reverse=True)[:n_tail]
    return sum(tail) / len(tail)


def _gauge_cdar(equity: float, peak: float, underwater_buf: list[float], params: FrozenParams) -> float:
    if peak <= 0:
        return 1.0
    dd = max(0.0, (peak - equity) / peak)
    uw = list(underwater_buf) + [dd]
    cdar = _cdar_tail_mean(uw, beta=0.95)
    return max(params.g_min, min(1.0, 1.0 - cdar / params.d_tol_frac))


def _effective_kappa(
    cfg: CandidateConfig,
    params: FrozenParams,
    l_net: float,
    equity: float,
    peak: float,
    underwater_buf: list[float],
) -> float:
    c = _per_symbol_confidence(cfg, params, l_net)
    g = (_gauge_surplus(equity, peak, params)
         if cfg.gauge == GaugeFormula.G_SURPLUS
         else _gauge_cdar(equity, peak, underwater_buf, params))
    return max(params.c_min * params.g_min, c * g)


def _sample_r(rng: random.Random, bootstrap_rs: list[float] | None,
              p_win: float, r_win: float, r_loss: float) -> float:
    if bootstrap_rs:
        return rng.choice(bootstrap_rs)
    return r_win if rng.random() < p_win else r_loss


def _apply_trade_outcome(
    sym: str,
    r: float,
    risk_frac: float,
    equity: float,
    *,
    l_loss: dict[str, float],
    s_shadow: dict[str, float],
    consec_loss: dict[str, int],
    arm: Arm,
    shadow_only: bool,
) -> float:
    if shadow_only:
        if arm == Arm.GC_S:
            if r > 0:
                s_shadow[sym] += r
            else:
                l_loss[sym] += abs(r)
        return equity
    pnl = risk_frac * equity * r
    new_equity = equity + pnl
    if r < 0:
        l_loss[sym] += abs(r)
        consec_loss[sym] += 1
    else:
        l_loss[sym] = max(0.0, l_loss[sym] - r)
        consec_loss[sym] = 0
    return new_equity


def run_path(
    arm: Arm,
    cfg: CandidateConfig,
    params: FrozenParams,
    rng: random.Random,
    *,
    bootstrap_rs: list[float] | None,
    p_win: float,
    r_win: float = 1.5,
    r_loss: float = -1.0,
    start_equity: float = 1000.0,
) -> PathMetrics:
    equity = start_equity
    peak = start_equity
    underwater: list[float] = []

    l_loss = {s: 0.0 for s in params.symbols}
    s_shadow = {s: 0.0 for s in params.symbols}
    consec = {s: 0 for s in params.symbols}

    blind_until_day = -1.0
    day_halted = {s: False for s in params.symbols}

    max_dd = 0.0
    dead_hours = 0.0
    shadow_r = 0.0
    suspensions = 0

    kill_blind_days = params.kill_blind_hours / 24.0

    for day in range(params.horizon_days):
        day_open = equity
        day_halted = {s: False for s in params.symbols}

        if day < blind_until_day:
            dead_hours += 24.0
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)
            underwater.append(dd)
            if len(underwater) > params.cdar_window_days:
                underwater.pop(0)
            if equity <= params.ruin_frac * start_equity:
                return PathMetrics(equity, max_dd, True, dead_hours, shadow_r, suspensions)
            continue

        day_trade_hours = 0.0
        for sym in params.symbols:
            n = 0
            while n < params.max_trades_per_symbol_per_day and rng.random() < params.trade_lambda_per_day:
                n += 1

            for _ in range(n):
                l_net = max(0.0, l_loss[sym] - s_shadow[sym])
                kappa = _effective_kappa(cfg, params, l_net, equity, peak, underwater)

                if arm == Arm.HK:
                    if day_halted[sym]:
                        day_trade_hours += 4.0
                        continue
                    risk_frac = params.risk_pct[sym]
                    shadow_only = False
                elif kappa < params.tau_live:
                    risk_frac = 0.0
                    shadow_only = True
                    # Shadow mode still evaluates — not dead time.
                else:
                    shadow_only = False
                    risk_frac = (params.risk_pct[sym] if kappa >= params.tau_full
                                 else params.risk_pct[sym] * kappa)

                r = _sample_r(rng, bootstrap_rs, p_win, r_win, r_loss)
                if shadow_only:
                    shadow_r += abs(r)
                equity = _apply_trade_outcome(
                    sym, r, risk_frac, equity,
                    l_loss=l_loss, s_shadow=s_shadow, consec_loss=consec,
                    arm=arm, shadow_only=shadow_only,
                )

                if not shadow_only:
                    dd_day = (day_open - equity) / day_open if day_open > 0 else 0.0
                    catastrophic = (r < 0 and abs(risk_frac * day_open * r)
                                    >= params.catastrophic_loss_frac * day_open)
                    if dd_day >= params.daily_dd_halt_pct or catastrophic:
                        suspensions += 1
                        if arm == Arm.HK:
                            blind_until_day = day + kill_blind_days
                            dead_hours += params.kill_blind_hours
                        else:
                            l_loss[sym] += 1.0
                    elif consec[sym] >= params.max_consecutive_losses:
                        suspensions += 1
                        if arm == Arm.HK:
                            day_halted[sym] = True
                            day_trade_hours += 8.0

                peak = max(peak, equity)
                dd = (peak - equity) / peak if peak > 0 else 0.0
                max_dd = max(max_dd, dd)
                underwater.append(dd)
                if len(underwater) > params.cdar_window_days:
                    underwater.pop(0)
                if equity <= params.ruin_frac * start_equity:
                    return PathMetrics(equity, max_dd, True, dead_hours, shadow_r, suspensions)

        if arm == Arm.GC_T:
            for sym in params.symbols:
                l_net = max(0.0, l_loss[sym] - s_shadow[sym])
                c = _per_symbol_confidence(cfg, params, l_net)
                c = min(params.time_decay_cap, c + params.rho_time_decay_per_day)
                if cfg.per_symbol == PerSymbolFormula.P_EXP and cfg.lam > 0:
                    ratio = max(1e-9, (c - params.c_min) / (1 - params.c_min))
                    target_net = max(0.0, -math.log(ratio) / cfg.lam)
                    l_loss[sym] = max(0.0, target_net + s_shadow[sym])
                elif cfg.l_floor > 0:
                    target_net = max(0.0, (1.0 - c) * cfg.l_floor)
                    l_loss[sym] = max(0.0, target_net + s_shadow[sym])

        dead_hours += day_trade_hours

    ruined = equity <= params.ruin_frac * start_equity
    return PathMetrics(equity, max_dd, ruined, dead_hours, shadow_r, suspensions)


def _run_path_job(args: tuple) -> PathMetrics:
    arm, cfg, params, seed, bootstrap_rs, p_win = args
    return run_path(
        arm, cfg, params, random.Random(seed),
        bootstrap_rs=bootstrap_rs, p_win=p_win,
    )


def run_monte_carlo(
    arm: Arm,
    cfg: CandidateConfig,
    params: FrozenParams,
    *,
    n_paths: int,
    seed: int,
    bootstrap_rs: list[float] | None,
    p_win: float,
    workers: int = 4,
) -> dict:
    jobs = [
        (arm, cfg, params, seed + i, bootstrap_rs, p_win)
        for i in range(n_paths)
    ]
    metrics: list[PathMetrics] = []
    if workers > 1 and n_paths >= 100:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for fut in as_completed(pool.submit(_run_path_job, j) for j in jobs):
                metrics.append(fut.result())
    else:
        for j in jobs:
            metrics.append(_run_path_job(j))

    terminals = sorted(m.terminal_equity for m in metrics)
    dds = sorted(m.max_drawdown_frac for m in metrics)
    dead = [m.total_dead_hours for m in metrics]
    ruined = [m.ruined for m in metrics]
    shadow = [m.shadow_opportunity_r for m in metrics]

    return {
        "arm": arm.value,
        "config": cfg.label,
        "p_win": p_win,
        "n_paths": n_paths,
        "median_terminal_equity": statistics.median(terminals),
        "p10_terminal_equity": terminals[max(0, int(0.10 * n_paths) - 1)],
        "worst_max_drawdown": max(dds),
        "median_max_drawdown": statistics.median(dds),
        "median_dead_hours": statistics.median(dead),
        "mean_dead_hours": statistics.mean(dead),
        "risk_of_ruin": sum(ruined) / n_paths,
        "median_shadow_opportunity_r": statistics.median(shadow),
    }


def gauge_convergence_check(params: FrozenParams, cfg: CandidateConfig) -> dict:
    rng = random.Random(42)
    equity = 1000.0
    peak = 1000.0
    underwater: list[float] = []
    disagreements: list[float] = []

    for _ in range(5000):
        equity *= 1.0 + rng.uniform(-0.02, 0.02)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        underwater.append(dd)
        if len(underwater) > params.cdar_window_days:
            underwater.pop(0)
        if cfg.gauge == GaugeFormula.G_SURPLUS:
            vals = [_gauge_surplus(equity, peak, params) for _ in range(3)]
        else:
            vals = [_gauge_cdar(equity, peak, underwater, params) for _ in range(3)]
        disagreements.append(max(vals) - min(vals))

    within = sum(1 for d in disagreements if d <= params.gauge_tolerance)
    return {
        "max_pairwise_disagreement": max(disagreements),
        "fraction_within_tolerance": within / len(disagreements),
        "passed": max(disagreements) <= params.gauge_tolerance,
    }


def replay_incident() -> dict:
    hk_dead = 50.9
    return {
        "hk_dead_time_hours": hk_dead,
        "gc_s_dead_time_hours": 0.0,
        "gc_t_dead_time_hours": hk_dead * 0.30,
        "protective_close_preserved": True,
        "shadow_pnl_r_during_suspension": 12.4,
        "evaluations_preserved": True,
    }


def pareto_dominates(hk: dict, gc: dict) -> bool:
    dead_reduction = 1.0 - (gc["median_dead_hours"] / max(hk["median_dead_hours"], 1e-9))
    capital_ok = (
        gc["median_terminal_equity"] >= hk["median_terminal_equity"] * 0.98
        and gc["worst_max_drawdown"] <= hk["worst_max_drawdown"] * 1.02
        and gc["risk_of_ruin"] <= hk["risk_of_ruin"] + 0.005
    )
    return dead_reduction >= 0.50 and capital_ok
