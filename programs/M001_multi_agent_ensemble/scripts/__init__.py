"""M001 program scripts — CLIs run from the repo root.

This package holds standalone scripts that drive long-running, often
out-of-process workflows (VM-side calibration, dataset ingestion,
etc.). They are importable from tests so the structural plumbing is
covered, but they all have a working `if __name__ == "__main__"` so
they remain runnable as scripts on Windows / Linux / Mac.
"""
