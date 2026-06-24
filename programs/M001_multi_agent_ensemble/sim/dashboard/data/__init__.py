"""Dashboard data loaders.

Phi2.5 reads JSONL files directly from `output/<run>/...` per
`08-dashboard-spec.md` section 5. Phi4 migrates to a SQLite shadow
index; only this layer changes when that lands.
"""
