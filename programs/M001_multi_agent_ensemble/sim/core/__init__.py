"""Deterministic replay kernel for the M001 ensemble.

Submodules:
    types       — Thought, AgentProposal, OrderIntent, Coordinate, MarketState
    ledger      — ThoughtLedger interface + Full/Redacted/Frozen/Synthetic
    striker     — BlueLockStriker Protocol + BaseStriker ABC
    engine      — replay tick loop
    seed        — deterministic seed derivation
    friction    — spread/slippage/latency/partial-fill/reject model
    sentinel    — R1-R5 hard rules + external triggers
    aggregator  — minimal Phi2.5 stub (highest conviction wins)
"""
