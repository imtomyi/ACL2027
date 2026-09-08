# Validation gap record

This run is retained as an append-only engineering record but is superseded for
readiness decisions. Several rare-event logistic estimators reached the original
5,000-iteration limit without meeting the overly strict `1e-9` convergence
tolerance. The route inventory and safety checks passed, but the original smoke
manifest did not include estimator convergence as a required completion check.

No manuscript or formal-experiment claim may use this run. A successor smoke
must use the updated policy tolerance and require every fitted estimator to be a
converged logistic model or an explicitly smoothed constant model.
