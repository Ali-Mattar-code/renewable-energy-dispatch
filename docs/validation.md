# Validation record

## Automated invariants

The test suite verifies:

- representative load equals 9,000 kWh/day × 365 days;
- adding the outage day preserves 365 annual day-weights;
- hourly supply equals load, charging, export and curtailment;
- annual biogas generation cannot exceed feedstock energy;
- disabled technologies receive zero capacity;
- the resilient design serves the modelled outage;
- outage-window inputs are bounded and the fixed-design envelope reports complete, physically bounded results;
- component CAPEX reconciles to total CAPEX;
- financial outputs are finite and emissions reduction remains bounded.

GitHub Actions runs linting, tests and a complete reference reproduction on every push and pull request.

## Solver

SciPy’s HiGHS linear-programming interface solves the joint capacity and dispatch problem. The reference case terminates with an optimal status. Machine-readable solver status is recorded in `results/reference/summary.json`.

## Interpretation tests

The technology comparison is deliberately retained. Under the flat tariff and without an outage requirement, the least-cost full-hybrid solution may select zero battery capacity. When the six-hour evening resilience requirement is activated, storage becomes part of the optimal design. This confirms that the battery is selected by a stated system need rather than forced into the output.

The post-design outage envelope then searches for counterexamples rather than assuming the design event generalises. Its ten-hour August evening case exposes a real service shortfall, which is retained in the committed results instead of being hidden by the successful six-hour design case.

## Remaining validation before real use

- 8,760-hour measured load and weather simulation
- component degradation and availability distributions
- electrical load-flow, short-circuit and protection studies
- digester process design and feedstock laboratory results
- vendor performance curves and minimum generator loading
- stochastic outages and forecast error
- full lifecycle emissions and project-finance review
