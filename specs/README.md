# Frozen specification

Before any `mode="test"` analysis:

1. Write `frozen_spec.yaml` (primary hypothesis, event windows, RV definition, estimators, decision rules).
2. Record its SHA-256 in `data/checksums.txt`.
3. Set `SPEC_REGISTERED=yes` in the environment.

Until then, `utils.load_panel(..., mode="test")` raises `PermissionError`.
