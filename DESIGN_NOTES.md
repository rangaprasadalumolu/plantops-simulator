# Design notes and walkthrough

## Scope
A fully synthetic, deterministic prototype for anomaly detection and scenario simulation. It is a demonstration dataset and rule engine, not a production OT control system.

## Decisions and trade-offs
- **Synthetic-only data:** avoids licensing and confidentiality concerns and makes regeneration deterministic.
- **Seeded `random.Random`:** provides reproducible variation while keeping scale configurable.
- **Separate ground truth:** telemetry features do not carry the injected `issue_type`; evaluation labels are exported separately.
- **Isolated negative fixtures:** deliberately invalid topology/configuration and boundary violations are stored in `edge_cases.csv`, not mixed into valid baseline entities.
- **Append-only events:** `state_events.csv` records changes instead of overwriting previous states.
- **SQLite plus CSV/JSON:** SQLite gives reviewers relational constraints; CSV/JSON are portable for inspection and analysis.
- **Rule-based alarms:** deterministic and explainable thresholds make expected decisions auditable; thresholds are illustrative and require engineering calibration for real equipment.
- **Graph topology:** pipes form a ring within each facility to guarantee connectedness, with additional edges for variation.

## Important limitations to disclose
- The physics model is approximate, not a validated hydraulic solver.
- Current detection rules are simple thresholds; correlated process dynamics, sensor drift, transient response, and uncertainty are simplified.
- The bridge tables are populated from pipe endpoints, but generic node IDs are not enforced as SQL foreign keys because the model uses three component tables. Application-level topology validation checks the endpoints.
- A production-grade extension should normalize a shared `Node` table, add explicit scenario/configuration entities, use transactions and migrations, and add calibrated pump curves plus hydraulic simulation.
- Baseline mass balance fields are simplified features rather than a complete multi-node conservation solver.
- Candidate should run tests and inspect the full 100,000-row output before claiming successful verification.

## Walkthrough outline
1. Show master tables and deterministic ID naming.
2. Explain how the facility-local ring topology is constructed and checked.
3. Inspect pump curve coefficients, tank capacity, valve state, sensor units, and telemetry timestamps.
4. Compare telemetry features with separate ground truth labels.
5. Show alarms and evidence JSON, then inspect edge-case fixtures.
6. Run validation and reproducibility commands; explain each metric.
7. Discuss limitations and the path to a shared node model and calibrated physics.

## Suggested next improvements
- Add a normalized `nodes` table and enforce both pipe endpoint foreign keys in SQLite.
- Model scenario assignment explicitly in `scenario_events` instead of relying on telemetry sequence position.
- Add a genuine mass-balance model at each node and derive the balance-error metric from incoming/outgoing pipe flows.
- Add lifecycle transition validation and event replay tests.
- Add CI to run unit tests, validation, and reproducibility checks on every push.
