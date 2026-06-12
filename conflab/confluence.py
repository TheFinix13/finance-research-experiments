"""Cross-timeframe clustering of levels into scored confluence bands."""
from __future__ import annotations

from dataclasses import dataclass, field

from conflab.levels import Level

# Higher timeframes carry more weight in the density score: a D1 zone edge
# means more than an H1 swing. Unknown TFs default to 1.0.
TF_WEIGHTS = {"D1": 2.0, "H4": 1.5, "H1": 1.0, "M15": 0.75}


@dataclass
class ConfluenceBand:
    low: float
    high: float
    members: list[Level] = field(default_factory=list)

    @property
    def center(self) -> float:
        return (self.low + self.high) / 2

    @property
    def n_members(self) -> int:
        return len(self.members)

    @property
    def n_sources(self) -> int:
        return len({m.source for m in self.members})

    @property
    def n_timeframes(self) -> int:
        return len({m.timeframe for m in self.members})

    @property
    def score(self) -> float:
        """Density score: source-weighted sum scaled by TF weight, with a
        multiplier for genuinely multi-source and multi-TF overlap. A band of
        five EMAs scores far below a band of one zone edge + one swing + one
        trendline across two TFs."""
        base = sum(m.weight * TF_WEIGHTS.get(m.timeframe, 1.0)
                   for m in self.members)
        return round(base * (1 + 0.5 * (self.n_sources - 1))
                     * (1 + 0.5 * (self.n_timeframes - 1)), 3)

    def sources_summary(self) -> str:
        parts = [f"{m.timeframe}:{m.source}" for m in self.members]
        return ", ".join(sorted(set(parts)))

    def to_dict(self) -> dict:
        return {
            "low": self.low, "high": self.high, "center": self.center,
            "score": self.score, "n_members": self.n_members,
            "n_sources": self.n_sources, "n_timeframes": self.n_timeframes,
            "members": [m.to_dict() for m in self.members],
        }


def cluster_levels(levels: list[Level], tolerance: float) -> list[ConfluenceBand]:
    """Greedy 1-D clustering: sort by price and grow a band while the next
    level stays within ``tolerance`` of the band's FIRST member (a diameter
    cap, so no band is ever wider than ``tolerance``). Chaining on
    neighbour-distance instead would daisy-chain a dense level continuum
    into one meaningless mega-band. ``tolerance`` is in price units (callers
    usually pass k×ATR of the highest timeframe)."""
    if not levels or tolerance <= 0:
        return []
    ordered = sorted(levels, key=lambda lv: lv.price)
    bands: list[ConfluenceBand] = []
    current = [ordered[0]]
    for lv in ordered[1:]:
        if lv.price - current[0].price <= tolerance:
            current.append(lv)
        else:
            bands.append(_make_band(current))
            current = [lv]
    bands.append(_make_band(current))
    return bands


def _make_band(members: list[Level]) -> ConfluenceBand:
    prices = [m.price for m in members]
    return ConfluenceBand(low=min(prices), high=max(prices),
                          members=list(members))


def top_bands(bands: list[ConfluenceBand], min_members: int = 2,
              limit: int = 10) -> list[ConfluenceBand]:
    """The bands worth drawing: at least ``min_members`` overlapping levels,
    ranked by score."""
    qualified = [b for b in bands if b.n_members >= min_members]
    return sorted(qualified, key=lambda b: -b.score)[:limit]
