"""Shared statistical primitives: permutation p-value and BH-FDR."""
from __future__ import annotations

import numpy as np


def _permutation_pvalue(a: np.ndarray, b: np.ndarray, n_perm: int,
                        rng: np.random.Generator) -> float:
    """One-sided p for mean(a) > mean(b) under label exchange."""
    observed = a.mean() - b.mean()
    pooled = np.concatenate([a, b])
    n_a = len(a)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        if pooled[:n_a].mean() - pooled[n_a:].mean() >= observed:
            count += 1
    return (count + 1) / (n_perm + 1)


def benjamini_hochberg(pvals: list[float], alpha: float = 0.05) -> list[bool]:
    """BH-FDR: returns a True/False flag per p-value (True = significant)."""
    m = len(pvals)
    if m == 0:
        return []
    order = np.argsort(pvals)
    flags = [False] * m
    max_k = -1
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= alpha * rank / m:
            max_k = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= max_k:
            flags[idx] = True
    return flags
