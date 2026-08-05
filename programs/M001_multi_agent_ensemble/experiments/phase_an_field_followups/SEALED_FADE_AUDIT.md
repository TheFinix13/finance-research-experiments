# AN-3 sealed fade audit — thin sample vs genuine decay

**Cell:** `AN-3:chigiri_hyoma:XAGUSD`  
**Cost:** 1x honest RT = 2.5 field-pips (deducted from `pnl_pips`; R = (pnl−cost)/`source_sl_pips`)  
**Burn-in:** 92 days (same as `summarize_phase_an.py`)  
**Window:** sealed starts 2023-01-01, 2023-04-01, 2023-07-01, 2023-10-01, 2024-01-01; end 2026-05-31  
**Script:** `sealed_fade_audit.py` → also writes `results/sealed_fade_audit.json`

## VERDICT: `thin_sample_artifact`

Critical cut PASS: full-path 2024+ stays PF>1 / meanR>0, and calendar 2024 itself is still strong (not a dead year). The lone 2024-01 start loss is burn-in + nested-subset path noise (it drops most of excellent 2024-H1). Separate note: 2025 is weak on small n — forward risk, not the sealed multi-start fail.

### Numbers that decide it

| slice (full path start=2023-01) | n | WR | PF @1x | mean R @1x | pips @1x |
|---|---:|---:|---:|---:|---:|
| overall | 72 | 51.4% | 1.27 | +0.1980 | +329.2 |
| calendar 2023 | 26 | 57.7% | 1.659 | +0.3476 | +229.0 |
| calendar 2024+ | 46 | 47.8% | 1.115 | +0.1135 | +100.2 |
| calendar 2024 | 28 | 57.1% | 1.498 | +0.3410 | +217.2 |
| calendar 2025 | 18 | 33.3% | 0.732 | -0.2405 | -117.0 |
| start 2024-01 path (alone) | 37 | 43.2% | 0.941 | +0.0044 | -47.0 |

Critical cut: **2024+ trades on the FULL 2023-01 path** (n=46, PF=1.115, meanR=+0.1135) stay positive — and **calendar 2024 alone** is still strong (n=28, PF=1.498, meanR=+0.3410), matching 2023 (n=26, PF=1.659, meanR=+0.3476). 2025 is the soft year (n=18, PF=0.732, meanR=-0.2405).

## 1. Schema / tape notes

Trades live at `results/AN-3/XAGUSD/sealed/start_<k>/trades.jsonl`.
Relevant fields: `entry_time`, `pnl_pips`, `source_sl_pips`, `r_multiple` (pre-cost), `direction`, `entry`.
Raw tape counts include a few pre-cutoff entries; KPIs here match the sealed summary by discarding `entry_time < start+92d`.

## 2. Full-path calendar buckets (start_0 = 2023-01)

### By calendar year

```
2023: n= 26  WR= 57.7%  PF= 1.659  meanR=+0.3476  pips=  +229.0
2024: n= 28  WR= 57.1%  PF= 1.498  meanR=+0.3410  pips=  +217.2
2025: n= 18  WR= 33.3%  PF= 0.732  meanR=-0.2405  pips=  -117.0
```

### By half-year

```
2023-H1: n=  4  WR= 50.0%  PF= 1.041  meanR=+0.1602  pips=    +2.8
2023-H2: n= 22  WR= 59.1%  PF= 1.812  meanR=+0.3817  pips=  +226.2
2024-H1: n= 17  WR= 70.6%  PF= 3.182  meanR=+0.6686  pips=  +326.6
2024-H2: n= 11  WR= 36.4%  PF= 0.619  meanR=-0.1652  pips=  -109.4
2025-H1: n=  9  WR= 22.2%  PF= 0.387  meanR=-0.5240  pips=  -148.7
2025-H2: n=  9  WR= 44.4%  PF= 1.163  meanR=+0.0430  pips=   +31.7
```

## 3. Rolling 20-trade KPIs (full 2023-01 path, 1x cost)

- Windows: 53 (end entries 2023-11-16T16:00:00+00:00 → 2025-09-25T12:00:00+00:00)
- Median mean R, first half of windows: 0.5257
- Median mean R, last half of windows: 0.0478
- % windows with PF < 1: 26.4% (last half: 51.9%)
- % windows with mean R ≤ 0: 24.5% (last half: 48.1%)

Per-window series is in `results/sealed_fade_audit.json` under `rolling_20.windows`.

## 4. Cross-start overlap

Identity key = `(entry_time, direction, round(entry, 6))`.

### Later starts vs earliest (2023-01) post-burn-in set

| start | n | shared w/ 2023-01 | unique vs 2023-01 | % subset of 2023-01 |
|---|---:|---:|---:|---:|
| 2023-04-01 | 68 | 68 | 0 | 100.0% |
| 2023-07-01 | 60 | 60 | 0 | 100.0% |
| 2023-10-01 | 46 | 46 | 0 | 100.0% |
| 2024-01-01 | 37 | 37 | 0 | 100.0% |

### Incremental trades vs union of earlier starts

| start | n | already in earlier starts | new vs earlier |
|---|---:|---:|---:|
| 2023-01-01 | 72 | 0 | 72 |
| 2023-04-01 | 68 | 68 | 0 |
| 2023-07-01 | 60 | 60 | 0 |
| 2023-10-01 | 46 | 46 | 0 |
| 2024-01-01 | 37 | 37 | 0 |

Union of all starts: n=72.

2024-01 path: **100.0%** of its trades also appear on the 2023-01 full path (post each path's own burn-in).
Later starts are **exact nested subsets** of earlier starts' post-burn-in trades (0 unique trades on any later start). The 2024-01 path is a short, late slice of the same opportunity set, not an independent regime sample.

### Same-window identity check

Full-path trades with `entry_time >= 2024-01-01 + 92d` (= burn-in cutoff of the 2024-01 start): n=37, PF=0.941, meanR=+0.0044, pips=-47.0.
These KPIs are **identical** to the 2024-01 start alone — squad-state differences across starts did not create a different trade set; only the calendar window did.

## 5. Per-start sealed KPIs @1x (reproduced)

```
2023-01-01: n= 72  WR= 51.4%  PF=  1.27  meanR=+0.1980  pips=  +329.2
2023-04-01: n= 68  WR= 51.5%  PF= 1.284  meanR=+0.2002  pips=  +326.4
2023-07-01: n= 60  WR= 51.7%  PF= 1.313  meanR=+0.2070  pips=  +319.5
2023-10-01: n= 46  WR= 47.8%  PF= 1.115  meanR=+0.1135  pips=  +100.2
2024-01-01: n= 37  WR= 43.2%  PF= 0.941  meanR=+0.0044  pips=   -47.0
```

## Interpretation

### Why the verdict is `thin_sample_artifact`

1. **Critical cut:** on the continuous 2023-01 tape, 2024+ trades remain positive after 1x cost (n=46, PF=1.115, meanR=+0.1135).
2. **Calendar 2024 is not dead:** full-path 2024 alone is n=28, PF=1.498, meanR=+0.3410 — essentially as strong as 2023. The sealed 'fade' is **not** 'edge died when 2024 began'.
3. **Nested subsets:** every later start's post-burn-in trades are a 100% subset of the 2023-01 set. No unique 2024-01 opportunities exist.
4. **Burn-in amputates the best half-year:** 2024-H1 on the full path is the sealed peak (PF 3.182, meanR +0.67, n=17). The 2024-01 start's 92-day burn-in ends ~2024-04-02, so that path systematically drops most of that peak and retains 2024-H2 + 2025 (the weak half-years). Same-window filter on the full path reproduces the 2024-01 KPIs exactly.

### Separate caveat (does not flip the verdict)

From **2024-H2 onward** the full path *does* weaken: 2024-H2 PF 0.619 (n=11), 2025 PF 0.732 / meanR −0.24 (n=18), and rolling-20 last-half windows are PF<1 about half the time. That is real late-window softness on small n — a paper-loop risk flag — but it is **not** what makes the 2024-01 start the only sealed loser. That specific multi-start pattern is explained by burn-in + nested short window.

Deployment implication: do **not** treat the single losing start as proof the edge died in 2024. Keep paper-loop / live tape as the forward arbiter, especially given 2025 softness.

---
*Generated by `sealed_fade_audit.py`.*
