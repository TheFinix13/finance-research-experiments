# M001 multi-agent ensemble — convenience shortcuts.
#
# Targets are thin wrappers around the canonical invocations documented
# in `programs/M001_multi_agent_ensemble/sim/README.md`. They exist so
# the operator does not have to retype the PYTHONPATH preamble for the
# tools they will run most often.
#
# Override the venv binaries by setting PY/STREAMLIT on the make line:
#   make label-regime PY=/custom/path/to/python
#

# Cross-repo path: the production parquet cache, conflab indicators,
# and Φ3 wrapper imports live in the sibling repo. Set
# `M001_PRODUCTION_REPO=...` to point elsewhere.
PROD_REPO ?= ../multi-pair-trading-agent
PY        ?= $(PROD_REPO)/.venv/bin/python
STREAMLIT ?= $(PROD_REPO)/.venv/bin/streamlit
PYPATH    := PYTHONPATH=$(PROD_REPO):.

LABEL_TOOL := programs/M001_multi_agent_ensemble/sim/regime/label_disagreements.py
VM_CALIBRATE := programs/M001_multi_agent_ensemble/scripts/vm_calibrate_friction.py

.PHONY: help label-regime vm-calibrate vm-calibrate-dry test test-sim

help:
	@echo "M001 convenience targets:"
	@echo "  make label-regime       Launch the Φ3 regime disagreement labelling Streamlit app"
	@echo "  make vm-calibrate       Run VM-side friction calibration (writes JSON)"
	@echo "  make vm-calibrate-dry   Run VM-side friction calibration in --dry-run mode"
	@echo "  make test-sim           Run the M001 simulator test suite"
	@echo ""
	@echo "Overrides: PY=$(PY) STREAMLIT=$(STREAMLIT) PROD_REPO=$(PROD_REPO)"

label-regime:
	$(PYPATH) $(STREAMLIT) run $(LABEL_TOOL)

vm-calibrate:
	$(PYPATH) $(PY) $(VM_CALIBRATE)

vm-calibrate-dry:
	$(PYPATH) $(PY) $(VM_CALIBRATE) --dry-run

test-sim:
	$(PYPATH) $(PY) -m pytest programs/M001_multi_agent_ensemble/sim/tests/ -q
