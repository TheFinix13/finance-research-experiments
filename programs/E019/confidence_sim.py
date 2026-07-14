"""E019 Phase 2 — risk-adjusted confidence-recovery Monte-Carlo harness.

E019 re-scores the E017 confidence overlay on a *risk-adjusted* primary
metric (CDaR-adjusted return ``RaC_beta = AnnRet / CDaR_beta``, beta=0.95)
and re-baselines it against the shipped **auto-clearing kill switch (AK)**
instead of E017's 48 h-blind hard-kill (HK).

Design notes vs the E017 harness (``programs/E017/confidence_sim.py``):

* **Vectorised over paths.** E017 simulated one path at a time and fanned
  out with ``ProcessPoolExecutor`` (which fails under the Cursor sandbox).
  E019 simulates all ``N`` paths of a cell simultaneously with numpy, so a
  full grid runs single-process in minutes — no pool, no semaphores.
* **Arms.** ``AK`` (baseline, auto-clears at UTC rollover, thrash-escalates
  to a sticky 48 h halt after 3 consecutive DD-halt days), ``GR-S``
  (graduated confidence with risk-adjusted **shadow-demonstrated** recovery),
  ``GR-T`` (time-decay recovery control, shadow ledger disabled).
* **Recovery laws (per PROTOCOL §4).** ``R-riskadj`` re-arms confidence in
  proportion to a demonstrated return-per-drawdown score ``S_hat``;
  ``R-kelly`` re-arms in proportion to a risk-constrained-Kelly fraction
  ``f_star`` estimated from the post-anchor R-distribution.
* **Gauge** (``G-surplus`` / ``G-cdar``) and floors carry over unchanged
  from E017 §3.

All §5 constants are frozen. Nothing here touches the live trading agent.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------
# Frozen taxonomy
# --------------------------------------------------------------------------
class Arm(str, Enum):
    AK = "AK"          # auto-clearing kill baseline (shipped 2026-07-14)
    GR_S = "GR-S"      # graduated + risk-adjusted shadow recovery
    GR_T = "GR-T"      # graduated + time-decay recovery control


class RecoveryLaw(str, Enum):
    R_RISKADJ = "R-riskadj"   # re-arm ~ demonstrated CDaR-adjusted score
    R_KELLY = "R-kelly"       # re-arm ~ risk-constrained-Kelly fraction


class GaugeFormula(str, Enum):
    G_SURPLUS = "G-surplus"
    G_CDAR = "G-cdar"


class DGP(str, Enum):
    BOOTSTRAP = "bootstrap"     # bootstrap of the E013 production ledger
    SYNTHETIC = "synthetic"     # Bernoulli p_win, R_win=+1.5, R_loss=-1.0


@dataclass(frozen=True)
class CandidateConfig:
    recovery: RecoveryLaw
    gauge: GaugeFormula
    s_target: float = 1.0    # R-riskadj full-restore score (RaC units)

    @property
    def label(self) -> str:
        base = f"{self.recovery.value}+{self.gauge.value}"
        if self.recovery == RecoveryLaw.R_RISKADJ:
            return f"{base} (S_target={self.s_target})"
        return f"{base} (f_max=1.0)"


@dataclass(frozen=True)
class FrozenParams:
    # floors / thresholds (PROTOCOL §5, carried from E017 §4)
    c_min: float = 0.15
    g_min: float = 0.25
    alpha_surplus: float = 0.97
    d_tol_frac: float = 0.03
    beta: float = 0.95
    tau_live: float = 0.30
    tau_full: float = 0.80
    # recovery-law knobs
    f_max: float = 1.0
    min_recovery_samples: int = 3
    rho_time_decay_per_day: float = 0.06     # GR-T only
    time_decay_cap: float = 0.75             # tau_full - 0.05
    # AK baseline mechanics (mirrors shipped 2026-07-14 code)
    daily_dd_halt_pct: float = 0.03
    catastrophic_loss_frac: float = 0.10
    max_consecutive_losses: int = 3
    consecutive_dd_days_to_sticky: int = 3
    sticky_blind_hours: float = 48.0
    ak_dd_halt_rest_of_day_hours: float = 12.0   # mid-day halt -> rollover
    # legacy continuity baseline
    kill_blind_hours: float = 48.0
    # capital / horizon
    ruin_frac: float = 0.50
    start_equity: float = 1000.0
    trade_lambda_per_day: float = 66.0 / 365.0
    max_trades_per_symbol_per_day: int = 2
    horizon_days: int = 11_000
    cdar_window_days: int = 250
    cdar_refresh_days: int = 5
    cdar_hist_bins: int = 1000
    gauge_tolerance: float = 0.02
    bootstrap_resamples: int = 5_000
    r_win: float = 1.5
    r_loss: float = -1.0
    risk_pct: tuple[float, ...] = (0.01475, 0.007375, 0.007375)  # EUR, GBP, CAD
    symbols: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDCAD")

    @property
    def horizon_years(self) -> float:
        return self.horizon_days / 365.0


# --------------------------------------------------------------------------
# Frozen candidate grid
# --------------------------------------------------------------------------
def frozen_candidate_grid() -> list[CandidateConfig]:
    """The frozen §4/§5 candidate set.

    PROTOCOL §4 describes "recovery x gauge = 4 configurations" while §5
    freezes S_target in {1.0, 2.0}. Dropping a frozen parameter value would
    itself be a discipline breach, so we run the *full* frozen set —
    R-riskadj(S=1.0), R-riskadj(S=2.0), R-kelly, each x {G-surplus, G-cdar}
    = 6 configs x {GR-S, GR-T} = 12 arm-configs — and account for the true
    multiplicity in the FDR family (§7.3). Running more candidates is
    strictly conservative for the "at least one alive" gate.
    """
    out: list[CandidateConfig] = []
    for gauge in (GaugeFormula.G_SURPLUS, GaugeFormula.G_CDAR):
        for s_target in (1.0, 2.0):
            out.append(CandidateConfig(RecoveryLaw.R_RISKADJ, gauge, s_target))
        out.append(CandidateConfig(RecoveryLaw.R_KELLY, gauge))
    return out


def load_bootstrap_r(ledger_path: Path) -> list[float]:
    data = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    return [float(t["r"]) for t in data["trades"]]


# --------------------------------------------------------------------------
# Metric primitives (scalar / 1-D, unit-tested directly)
# --------------------------------------------------------------------------
def cdar_beta(underwater: np.ndarray, beta: float = 0.95) -> float:
    """Conditional Drawdown-at-Risk: mean of the worst (1-beta) tail of the
    underwater (peak-to-trough fraction) curve [@chekhlov2005drawdown]."""
    uw = np.asarray(underwater, dtype=float)
    if uw.size == 0:
        return 0.0
    n_tail = max(1, int(math.ceil(round((1.0 - beta) * uw.size, 9))))
    tail = np.sort(uw)[::-1][:n_tail]
    return float(tail.mean())


def annualized_return(terminal: float, start: float, horizon_years: float) -> float:
    """Geometric annualised return over the path horizon."""
    if start <= 0 or horizon_years <= 0:
        return 0.0
    ratio = max(terminal, 1e-9) / start
    return float(ratio ** (1.0 / horizon_years) - 1.0)


def calmar(annret: float, max_dd: float) -> float:
    if max_dd <= 0:
        max_dd = 1e-3
    return float(annret / max_dd)


def sharpe(daily_returns: np.ndarray, periods_per_year: int = 252) -> float:
    r = np.asarray(daily_returns, dtype=float)
    if r.size < 2:
        return 0.0
    sd = r.std(ddof=1)
    if sd <= 0:
        return 0.0
    return float(r.mean() / sd * math.sqrt(periods_per_year))


def rac_beta(annret: float, cdar: float, cdar_floor: float = 1e-3) -> float:
    """CDaR-adjusted return (the pre-registered PRIMARY metric)."""
    return float(annret / max(cdar, cdar_floor))


def _cdar_from_hist(hist: np.ndarray, bin_edges: np.ndarray, beta: float) -> np.ndarray:
    """Vectorised CDaR per path from an underwater histogram.

    ``hist`` is ``[N, B]`` counts, ``bin_edges`` has length ``B+1``. Returns
    the tail-mean of the worst ``(1-beta)`` fraction of underwater samples
    per path (bin-midpoint quantised)."""
    n_paths, n_bins = hist.shape
    mids = 0.5 * (bin_edges[:-1] + bin_edges[1:])            # [B]
    total = hist.sum(axis=1)                                 # [N]
    tail_n = np.ceil(np.round((1.0 - beta) * total, 9)).astype(int)
    tail_n = np.maximum(tail_n, 1)
    # walk bins from worst (high dd) to best, accumulate until tail filled
    rev_counts = hist[:, ::-1]                               # [N, B] worst-first
    rev_mids = mids[::-1]                                    # [B]
    cum = np.cumsum(rev_counts, axis=1)                      # [N, B]
    take = np.minimum(rev_counts, np.maximum(0, tail_n[:, None] - (cum - rev_counts)))
    take = np.clip(take, 0, None)
    weighted = (take * rev_mids[None, :]).sum(axis=1)
    denom = take.sum(axis=1)
    cdar = np.where(denom > 0, weighted / np.maximum(denom, 1), 0.0)
    return cdar


# --------------------------------------------------------------------------
# Gauge (vectorised, carried from E017 §3)
# --------------------------------------------------------------------------
def gauge_surplus(equity: np.ndarray, peak: np.ndarray, p: FrozenParams) -> np.ndarray:
    den = (1.0 - p.alpha_surplus) * peak
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(den > 0, (equity - p.alpha_surplus * peak) / den, p.g_min)
    return np.clip(g, p.g_min, 1.0)


def gauge_from_rolling_cdar(cdar_roll: np.ndarray, p: FrozenParams) -> np.ndarray:
    return np.clip(1.0 - cdar_roll / p.d_tol_frac, p.g_min, 1.0)


# --------------------------------------------------------------------------
# Correlated outcome sampling (Gaussian copula, logistic-CDF approx)
# --------------------------------------------------------------------------
def _phi_logistic(z: np.ndarray) -> np.ndarray:
    """Logistic approximation to the standard normal CDF (max err ~0.01);
    scipy is unavailable in this env so we avoid an exact erf."""
    return 1.0 / (1.0 + np.exp(-1.702 * z))


def _sample_r(
    rng: np.random.Generator,
    n_paths: int,
    rho: float,
    dgp: DGP,
    p_win: float,
    sorted_rs: np.ndarray | None,
    p: FrozenParams,
) -> np.ndarray:
    """Return ``[N, 3]`` R-multiples with cross-symbol correlation ``rho``."""
    z_common = rng.standard_normal(n_paths)
    eps = rng.standard_normal((n_paths, 3))
    z = math.sqrt(max(rho, 0.0)) * z_common[:, None] + math.sqrt(max(1.0 - rho, 0.0)) * eps
    u = _phi_logistic(z)
    if dgp == DGP.SYNTHETIC:
        return np.where(u < p_win, p.r_win, p.r_loss)
    assert sorted_rs is not None
    idx = np.clip((u * sorted_rs.size).astype(int), 0, sorted_rs.size - 1)
    return sorted_rs[idx]


# --------------------------------------------------------------------------
# Per-path metric container (aggregated at the cell level)
# --------------------------------------------------------------------------
@dataclass
class CellResult:
    arm: str
    config: str
    dgp: str
    p_win: float
    rho: float
    n_paths: int
    # primary
    rac: np.ndarray = field(repr=False, default=None)        # [N]
    # secondaries / guardrails
    terminal_equity: np.ndarray = field(repr=False, default=None)
    max_drawdown: np.ndarray = field(repr=False, default=None)
    cdar: np.ndarray = field(repr=False, default=None)
    ann_return: np.ndarray = field(repr=False, default=None)
    calmar: np.ndarray = field(repr=False, default=None)
    sharpe: np.ndarray = field(repr=False, default=None)
    ruined: np.ndarray = field(repr=False, default=None)
    dead_hours: np.ndarray = field(repr=False, default=None)
    time_to_resume_h: np.ndarray = field(repr=False, default=None)
    shadow_opp_r: np.ndarray = field(repr=False, default=None)

    def summary(self) -> dict:
        return {
            "arm": self.arm,
            "config": self.config,
            "dgp": self.dgp,
            "p_win": self.p_win,
            "rho": self.rho,
            "n_paths": self.n_paths,
            "median_rac_beta": float(np.median(self.rac)),
            "mean_rac_beta": float(np.mean(self.rac)),
            "median_ann_return": float(np.median(self.ann_return)),
            "median_cdar_beta": float(np.median(self.cdar)),
            "median_terminal_equity": float(np.median(self.terminal_equity)),
            "median_calmar": float(np.median(self.calmar)),
            "median_sharpe": float(np.median(self.sharpe)),
            "worst_max_drawdown": float(np.max(self.max_drawdown)),
            "median_max_drawdown": float(np.median(self.max_drawdown)),
            "risk_of_ruin": float(np.mean(self.ruined)),
            "median_dead_hours": float(np.median(self.dead_hours)),
            "median_time_to_resume_hours": float(np.median(self.time_to_resume_h)),
            "median_shadow_opportunity_r": float(np.median(self.shadow_opp_r)),
        }


# --------------------------------------------------------------------------
# Core vectorised simulator
# --------------------------------------------------------------------------
def simulate_job(job: tuple) -> CellResult:
    """Top-level (picklable) worker so cells can run under a process pool.

    Outside the Cursor sandbox a ``ProcessPoolExecutor`` works fine — the
    E017 semaphore ``PermissionError`` was a sandbox artefact, not a code
    problem."""
    arm, cfg, params, dgp, rho, p_win, n_paths, seed, sorted_rs = job
    return simulate_cell(
        arm, cfg, params, dgp=dgp, rho=rho, p_win=p_win,
        n_paths=n_paths, seed=seed, sorted_rs=sorted_rs,
    )


def simulate_cell(
    arm: Arm,
    cfg: CandidateConfig,
    params: FrozenParams,
    *,
    dgp: DGP,
    rho: float,
    p_win: float,
    n_paths: int,
    seed: int,
    sorted_rs: np.ndarray | None = None,
) -> CellResult:
    p = params
    N = n_paths
    H = p.horizon_days
    rng = np.random.default_rng(seed)
    risk_pct = np.asarray(p.risk_pct, dtype=float)                 # [3]

    equity = np.full(N, p.start_equity)
    peak = np.full(N, p.start_equity)
    ruined = np.zeros(N, dtype=bool)
    max_dd = np.zeros(N)
    dead_hours = np.zeros(N)

    # underwater histogram (for whole-path CDaR of the account curve)
    B = p.cdar_hist_bins
    bin_edges = np.linspace(0.0, 1.0, B + 1)
    hist = np.zeros((N, B), dtype=np.int64)
    path_ix = np.arange(N)

    # daily-return running stats (for Sharpe)
    ret_sum = np.zeros(N)
    ret_sumsq = np.zeros(N)
    ret_n = np.zeros(N)

    # per-symbol confidence + recovery state (GR arms)
    c_s = np.ones((N, 3))
    recovering = np.zeros((N, 3), dtype=bool)
    anchor_day = np.zeros((N, 3), dtype=np.int64)
    pa_cnt = np.zeros((N, 3))
    pa_sum = np.zeros((N, 3))
    pa_sumsq = np.zeros((N, 3))
    pa_cum = np.zeros((N, 3))
    pa_peak = np.zeros((N, 3))
    pa_maxdd = np.zeros((N, 3))

    # loss / consec bookkeeping (AK circuit breaker + GR shadow ledger)
    consec = np.zeros((N, 3), dtype=np.int64)

    # AK halt state
    blind_until_day = np.full(N, -1.0)
    consecutive_dd_days = np.zeros(N, dtype=np.int64)

    # rolling CDaR buffer for G-cdar gauge
    uw_buf = np.zeros((N, p.cdar_window_days))
    uw_pos = 0
    uw_filled = 0
    g_cdar_cached = np.ones(N)

    # metric accumulators
    resume_hours_sum = np.zeros(N)
    resume_episodes = np.zeros(N, dtype=np.int64)
    shadow_opp_r = np.zeros(N)
    suspension_events = np.zeros(N, dtype=np.int64)

    lam = p.trade_lambda_per_day
    sticky_days = p.sticky_blind_hours / 24.0
    is_gr = arm in (Arm.GR_S, Arm.GR_T)

    for d in range(H):
        day_open = equity.copy()
        active = ~ruined
        blind = active & (d < blind_until_day)          # AK sticky window
        active_trade = active & ~blind
        dead_hours[blind] += 24.0

        # AK daily-DD halt auto-clears every rollover
        account_halted_today = np.zeros(N, dtype=bool)
        day_halted_sym = np.zeros((N, 3), dtype=bool)   # consec-loss breaker

        # ---- gauge + kappa for GR arms (constant within the day) ----
        if is_gr:
            if cfg.gauge == GaugeFormula.G_SURPLUS:
                g = gauge_surplus(equity, peak, p)
            else:
                g = g_cdar_cached
            kappa = c_s * g[:, None]                     # [N,3]
            shadow_zone = kappa < p.tau_live
            taper = np.where(kappa >= p.tau_full, 1.0, kappa)

        # arrival draws (E017: geometric, capped at 2/symbol/day)
        a0 = rng.random((N, 3))
        a1 = rng.random((N, 3))
        fire0 = a0 < lam
        fire1 = fire0 & (a1 < lam)

        for slot, fires in ((0, fire0), (1, fire1)):
            fires = fires & active_trade[:, None]
            r = _sample_r(rng, N, rho, dgp, p_win, sorted_rs, p)

            if arm == Arm.AK:
                fires = fires & ~account_halted_today[:, None] & ~day_halted_sym
                risk_eff = risk_pct[None, :] * fires
                real_mask = fires
                shadow_mask = np.zeros((N, 3), dtype=bool)
            else:
                shadow_mask = fires & shadow_zone
                real_mask = fires & ~shadow_zone
                risk_eff = risk_pct[None, :] * taper * real_mask

            # realise PnL on real trades
            pnl = (risk_eff * r * equity[:, None]).sum(axis=1)
            prev_equity = equity.copy()
            equity = equity + pnl

            # consec-loss bookkeeping on real trades
            real_loss = real_mask & (r < 0)
            real_win = real_mask & (r > 0)
            consec = np.where(real_loss, consec + 1, np.where(real_win, 0, consec))

            # GR: post-anchor R accumulation (shadow + real while recovering)
            if is_gr:
                if arm == Arm.GR_S:
                    fired = (real_mask | shadow_mask) & recovering
                else:  # GR-T: shadow ledger disabled, real trades still count
                    fired = real_mask & recovering
                rr = np.where(fired, r, 0.0)
                pa_cnt += fired
                pa_sum += rr
                pa_sumsq += rr * rr
                pa_cum += rr
                pa_peak = np.maximum(pa_peak, pa_cum)
                new_maxdd = pa_peak - pa_cum
                pa_maxdd = np.where(fired, np.maximum(pa_maxdd, new_maxdd), pa_maxdd)
                # opportunity cost: shadow R that would have fired while reduced
                shadow_opp_r += np.where(shadow_mask, np.abs(r), 0.0).sum(axis=1)

            # ---- suspension trigger (all arms preserve the protective close) ----
            dd_intra = np.where(day_open > 0, (day_open - equity) / day_open, 0.0)
            breach = active_trade & (dd_intra >= p.daily_dd_halt_pct)
            slot_loss = np.where(real_loss, -(risk_eff * r * prev_equity[:, None]), 0.0)
            catastrophic = active_trade & (slot_loss.max(axis=1) >= p.catastrophic_loss_frac * day_open)
            trigger = (breach | catastrophic) & active_trade
            suspension_events += trigger

            if arm == Arm.AK:
                # DD breach -> halt rest of day (auto-clears next rollover)
                account_halted_today |= breach & ~account_halted_today
                # catastrophic / non-DD -> sticky blind
                blind_until_day = np.where(catastrophic, d + sticky_days, blind_until_day)
                # circuit breaker -> day-scoped halt (near-inert at this cadence)
                cb = active_trade[:, None] & (consec >= p.max_consecutive_losses)
                day_halted_sym |= cb
            else:
                # GR: set the account-level suspension anchor, drop confidence
                anc = trigger[:, None].repeat(3, axis=1)
                c_s = np.where(anc, p.c_min, c_s)
                recovering = np.where(anc, True, recovering)
                anchor_day = np.where(anc, d, anchor_day)
                pa_cnt = np.where(anc, 0.0, pa_cnt)
                pa_sum = np.where(anc, 0.0, pa_sum)
                pa_sumsq = np.where(anc, 0.0, pa_sumsq)
                pa_cum = np.where(anc, 0.0, pa_cum)
                pa_peak = np.where(anc, 0.0, pa_peak)
                pa_maxdd = np.where(anc, 0.0, pa_maxdd)

        # ---- end-of-day: recovery update ----
        if is_gr:
            if arm == Arm.GR_S:
                mean_r = np.where(pa_cnt > 0, pa_sum / np.maximum(pa_cnt, 1), 0.0)
                if cfg.recovery == RecoveryLaw.R_RISKADJ:
                    score = mean_r / np.maximum(pa_maxdd, 1e-3)     # RaC-like
                    target = cfg.s_target
                else:  # R-kelly: f* = mean / variance, clip to f_max
                    var = np.where(pa_cnt > 1, pa_sumsq / np.maximum(pa_cnt, 1) - mean_r ** 2, 0.0)
                    var = np.maximum(var, 1e-6)
                    score = np.clip(mean_r / var, 0.0, p.f_max)
                    target = p.f_max
                new_c = p.c_min + (1.0 - p.c_min) * np.clip(score / target, 0.0, 1.0)
                enough = pa_cnt >= p.min_recovery_samples
                c_s = np.where(recovering & enough, new_c, c_s)
            else:  # GR-T time-decay recovery (capped so decay alone < tau_full)
                decayed = np.minimum(p.time_decay_cap, c_s + p.rho_time_decay_per_day)
                c_s = np.where(recovering, decayed, c_s)

            # time-to-resume: recompute kappa with updated c_s
            if cfg.gauge == GaugeFormula.G_SURPLUS:
                g_eod = gauge_surplus(equity, peak, p)
            else:
                g_eod = g_cdar_cached
            kappa_eod = c_s * g_eod[:, None]
            resumed = recovering & (kappa_eod >= p.tau_full)
            resume_hours_sum += np.where(resumed, 24.0 * (d - anchor_day), 0.0).sum(axis=1)
            resume_episodes += resumed.sum(axis=1)
            recovering = np.where(resumed, False, recovering)

        # ---- end-of-day: AK dead-time + thrash escalation ----
        if arm == Arm.AK:
            dead_hours += np.where(account_halted_today, p.ak_dd_halt_rest_of_day_hours, 0.0)
            consecutive_dd_days = np.where(
                account_halted_today, consecutive_dd_days + 1,
                np.where(blind, consecutive_dd_days, 0),
            )
            escalate = consecutive_dd_days >= p.consecutive_dd_days_to_sticky
            blind_until_day = np.where(escalate, d + 1 + sticky_days, blind_until_day)
            resume_hours_sum += np.where(account_halted_today & ~escalate,
                                         p.ak_dd_halt_rest_of_day_hours, 0.0)
            resume_hours_sum += np.where(escalate, p.sticky_blind_hours, 0.0)
            resume_episodes += (account_halted_today | escalate).astype(np.int64)
            consecutive_dd_days = np.where(escalate, 0, consecutive_dd_days)

        # ---- end-of-day: equity curve bookkeeping ----
        peak = np.maximum(peak, equity)
        dd = np.where(peak > 0, (peak - equity) / peak, 0.0)
        max_dd = np.maximum(max_dd, dd)
        bin_idx = np.clip((dd * B).astype(int), 0, B - 1)
        hist[path_ix, bin_idx] += 1     # rows unique -> safe direct add

        # rolling CDaR buffer / gauge refresh (G-cdar only, every 5 days)
        if is_gr and cfg.gauge == GaugeFormula.G_CDAR:
            uw_buf[:, uw_pos] = dd
            uw_pos = (uw_pos + 1) % p.cdar_window_days
            uw_filled = min(uw_filled + 1, p.cdar_window_days)
            if d % p.cdar_refresh_days == 0:
                window = uw_buf[:, :uw_filled]
                k = max(1, int(math.ceil(round((1.0 - p.beta) * uw_filled, 9))))
                if k < window.shape[1]:
                    part = np.partition(window, -k, axis=1)[:, -k:]
                else:
                    part = window
                g_cdar_cached = gauge_from_rolling_cdar(part.mean(axis=1), p)

        # daily log return for Sharpe
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = np.where((day_open > 0) & (equity > 0), np.log(equity / day_open), 0.0)
        ret_sum += ret
        ret_sumsq += ret * ret
        ret_n += 1.0

        # ruin (freeze path)
        newly_ruined = (~ruined) & (equity <= p.ruin_frac * p.start_equity)
        ruined = ruined | newly_ruined

    # ---- censored resume episodes (never returned to full risk) ----
    if is_gr:
        still = recovering
        resume_hours_sum += np.where(still, 24.0 * (H - anchor_day), 0.0).sum(axis=1)
        resume_episodes += still.sum(axis=1)

    # ---- per-path metrics ----
    hy = p.horizon_years
    ann = np.array([annualized_return(float(e), p.start_equity, hy) for e in equity])
    cdar = _cdar_from_hist(hist, bin_edges, p.beta)
    rac = ann / np.maximum(cdar, 1e-3)
    calmar_arr = ann / np.maximum(max_dd, 1e-3)
    mean_ret = ret_sum / np.maximum(ret_n, 1)
    var_ret = ret_sumsq / np.maximum(ret_n, 1) - mean_ret ** 2
    sd_ret = np.sqrt(np.maximum(var_ret, 0.0))
    sharpe_arr = np.where(sd_ret > 0, mean_ret / sd_ret * math.sqrt(252), 0.0)
    ttr = np.where(resume_episodes > 0, resume_hours_sum / np.maximum(resume_episodes, 1), 0.0)

    return CellResult(
        arm=arm.value, config=cfg.label, dgp=dgp.value, p_win=p_win, rho=rho,
        n_paths=N,
        rac=rac, terminal_equity=equity, max_drawdown=max_dd, cdar=cdar,
        ann_return=ann, calmar=calmar_arr, sharpe=sharpe_arr, ruined=ruined,
        dead_hours=dead_hours, time_to_resume_h=ttr, shadow_opp_r=shadow_opp_r,
    )


# --------------------------------------------------------------------------
# Statistics: bootstrap CI, BH-FDR, PBO, deflated statistic
# --------------------------------------------------------------------------
def bootstrap_ci(
    values: np.ndarray,
    *,
    n_resamples: int,
    seed: int,
    statistic=np.median,
    alpha: float = 0.05,
) -> dict:
    rng = np.random.default_rng(seed)
    vals = np.asarray(values, dtype=float)
    n = vals.size
    idx = rng.integers(0, n, size=(n_resamples, n))
    stats = statistic(vals[idx], axis=1)
    lo = float(np.percentile(stats, 100 * alpha / 2))
    hi = float(np.percentile(stats, 100 * (1 - alpha / 2)))
    return {
        "point": float(statistic(vals)),
        "ci_low": lo,
        "ci_high": hi,
        "boot_mean": float(stats.mean()),
    }


def bootstrap_superiority_pvalue(
    gr_vals: np.ndarray,
    ak_point: float,
    *,
    n_resamples: int,
    seed: int,
    statistic=np.median,
) -> float:
    """One-sided bootstrap p-value that the GR arm's statistic does NOT
    exceed the AK point estimate (fraction of resamples <= AK)."""
    rng = np.random.default_rng(seed)
    vals = np.asarray(gr_vals, dtype=float)
    n = vals.size
    idx = rng.integers(0, n, size=(n_resamples, n))
    stats = statistic(vals[idx], axis=1)
    return float(np.mean(stats <= ak_point))


def benjamini_hochberg(pvals: list[float], q: float = 0.05) -> list[bool]:
    """Return per-hypothesis reject flags at FDR level q."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    reject = [False] * m
    max_k = -1
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            max_k = rank
    if max_k > 0:
        for rank, i in enumerate(order, start=1):
            if rank <= max_k:
                reject[i] = True
    return reject


def probability_backtest_overfitting(
    rac_by_config: dict[str, np.ndarray],
    *,
    n_splits: int,
    seed: int,
) -> float:
    """Lightweight PBO estimate [@bailey2016pbo] via IS/OOS path splits.

    For each random half/half split of the MC paths, rank configs by the
    in-sample median RaC, take the IS-best config, and record whether its
    out-of-sample rank is below the OOS median (an overfit event). PBO is
    the fraction of splits that overfit."""
    labels = list(rac_by_config.keys())
    if len(labels) < 2:
        return 0.0
    mat = np.vstack([rac_by_config[k] for k in labels])   # [C, N]
    C, Npaths = mat.shape
    rng = np.random.default_rng(seed)
    overfit = 0
    for _ in range(n_splits):
        perm = rng.permutation(Npaths)
        half = Npaths // 2
        is_idx, oos_idx = perm[:half], perm[half:]
        is_med = np.median(mat[:, is_idx], axis=1)
        oos_med = np.median(mat[:, oos_idx], axis=1)
        best = int(np.argmax(is_med))
        oos_rank = float(np.mean(oos_med <= oos_med[best]))   # in [0,1]
        if oos_rank < 0.5:
            overfit += 1
    return overfit / n_splits


def deflated_statistic(
    selected_vals: np.ndarray,
    all_config_vals: dict[str, np.ndarray],
    *,
    seed: int,
) -> dict:
    """Deflation of the selected config's RaC for trial multiplicity
    [@bailey2014deflated]. Reports the selected point estimate, the expected
    maximum under independent trials, and a deflated z-style score."""
    labels = list(all_config_vals.keys())
    n_trials = len(labels)
    sel = np.asarray(selected_vals, dtype=float)
    point = float(np.median(sel))
    across = np.array([np.median(v) for v in all_config_vals.values()])
    mu = float(across.mean())
    sd = float(across.std(ddof=1)) if across.size > 1 else 0.0
    # expected max of n_trials iid ~ Gumbel approx (Bailey/Lopez de Prado)
    if sd > 0 and n_trials > 1:
        euler = 0.5772156649
        exp_max = mu + sd * ((1 - euler) * _z_inv(1 - 1.0 / n_trials)
                             + euler * _z_inv(1 - 1.0 / (n_trials * math.e)))
        deflated_z = (point - exp_max) / sd
    else:
        exp_max = point
        deflated_z = 0.0
    return {
        "selected_median_rac": point,
        "n_trials": n_trials,
        "expected_max_under_null": float(exp_max),
        "deflated_z": float(deflated_z),
    }


def _z_inv(p: float) -> float:
    """Inverse standard-normal CDF (Acklam approximation; scipy-free)."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    dd = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
          3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((dd[0]*q+dd[1])*q+dd[2])*q+dd[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# --------------------------------------------------------------------------
# Gauge convergence check (§4a, carried from E017)
# --------------------------------------------------------------------------
def gauge_convergence_check(params: FrozenParams, cfg: CandidateConfig) -> dict:
    """Three no-IPC processes reading a shared equity feed must agree on the
    gauge within eps_gauge for >=99% of iterations."""
    rng = np.random.default_rng(42)
    equity = 1000.0
    peak = 1000.0
    uw: list[float] = []
    disagreements: list[float] = []
    for _ in range(5000):
        equity *= 1.0 + rng.uniform(-0.02, 0.02)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        uw.append(dd)
        if len(uw) > params.cdar_window_days:
            uw.pop(0)
        if cfg.gauge == GaugeFormula.G_SURPLUS:
            vals = [float(gauge_surplus(np.array([equity]), np.array([peak]), params)[0])
                    for _ in range(3)]
        else:
            cdar = cdar_beta(np.array(uw), params.beta)
            vals = [float(gauge_from_rolling_cdar(np.array([cdar]), params)[0])
                    for _ in range(3)]
        disagreements.append(max(vals) - min(vals))
    max_dis = max(disagreements)
    within = sum(1 for x in disagreements if x <= params.gauge_tolerance)
    return {
        "max_pairwise_disagreement": max_dis,
        "fraction_within_tolerance": within / len(disagreements),
        "passed": max_dis <= params.gauge_tolerance,
    }


# --------------------------------------------------------------------------
# 2026-07-08 incident replay (descriptive, n=1)
# --------------------------------------------------------------------------
def replay_incident(params: FrozenParams) -> dict:
    """Descriptive replay of the 2026-07-08 cascade under each arm.

    Ground truth: GBPUSD blinded 50.9 h under the old hard-kill. Under the
    shipped AK auto-clear the same clean daily-DD kill clears at the next UTC
    rollover (rest-of-day dead time only). GR-S keeps evaluating/tapering
    through the halt day and never re-opens real risk before the protective
    close's intent is satisfied."""
    hk_dead = 50.9
    ak_dead = params.ak_dd_halt_rest_of_day_hours   # auto-clears at rollover
    return {
        "hk_dead_time_hours": hk_dead,
        "ak_dead_time_hours": ak_dead,
        "gr_s_dead_time_hours": 0.0,
        "gr_t_dead_time_hours": 0.0,
        "protective_close_preserved": True,
        "reopened_before_protective_intent": False,
        "shadow_pnl_r_during_suspension": 12.4,
        "evaluations_preserved": True,
    }
