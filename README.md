# PlantOps Simulator

A reproducible synthetic industrial-fluid network simulator for pumps, tanks, valves, pipes, sensors, telemetry, alarms, operating modes, and simulation runs.

## Features

- Creates master data before dependent records: 3 facilities, 20 pumps, 30 tanks, 60 valves, pipes, sensors, operating modes.
- Deterministic IDs (`FAC-001`, `PUMP-001`, `TANK-001`, `VALVE-001`, `SNS-001`, `SIM-2026-000001`) and fixed seed (`20261022`).
- Generates 100,000 telemetry points by default (flow, pressure, tank level) with timestamped readings.
- Builds a facility-scoped topology graph, nominal pump curves, tank capacities, valve states, and approximate flow/mass-balance calculations.
- Injects labelled leak, blockage, pump-degradation, and sensor-fault scenarios after a valid baseline is generated.
- Derives alarms and ground truth from documented rules; ground truth is exported separately and is not included in telemetry feature columns.
- Includes explicit negative/exception cases in `edge_cases.csv`.
- Exports CSV, JSON summary, SQLite seed database, data dictionary, validation report, checksums, and a source manifest.
- Reproducibility check runs the generator twice and compares output checksums.

## Requirements

- Python 3.10+
- No third-party dependencies required.

## Quick start

```bash
python -m plantops.generate --out data --seed 20261022
```

Default output volume is the required full dataset. For a quick starter run:

```bash
python -m plantops.generate --out starter_data --seed 20261022 \
  --facilities 3 --pumps 20 --tanks 30 --valves 60 --telemetry 1000
```

Run validation:

```bash
python -m plantops.validate --data data
```

Run a reproducibility check (generates two small datasets to keep it fast):

```bash
python -m plantops.reproducibility --out reproducibility --telemetry 1000
```

Optional custom scale can be passed to the generator. Pump/tank/valve counts are distributed across facilities; components always reference a valid facility. Pipes connect valid nodes in the normal topology. Deliberately invalid references are isolated in `edge_cases.csv` so they cannot corrupt core tables.

## Output files

| File | Purpose |
|---|---|
| `facilities.csv` | Facility master data |
| `pumps.csv` | Pump specs and nominal curve coefficients |
| `tanks.csv` | Tank capacity and initial level |
| `valves.csv` | Valve type, nominal state, effective dates |
| `pipes.csv` | Pipe endpoints, diameter, length, status |
| `sensors.csv` | Sensor type, units, location and calibration state |
| `operating_modes.csv` | Mode definitions and permitted transitions |
| `telemetry.csv` | Time-series readings and associated entity IDs |
| `alarms.csv` | Rule-derived alarm records |
| `simulation_runs.csv` | Configuration, assumptions, outcomes, timestamps |
| `ground_truth.csv` / `.json` | Scenario labels and expected decisions, separate from model inputs |
| `edge_cases.csv` | Explicit negative scenarios with expected validation outcomes |
| `plantops.sqlite` | Relational seed database |
| `data_dictionary.csv` | Field types, required status, allowed values, units, uniqueness and validation rules |
| `validation_summary.json` | PK/FK, enums, topology, arithmetic, lifecycle and duplicate checks |
| `source_manifest.json` | Synthetic provenance, generator version, seed and transformations |
| `checksums.json` | SHA-256 checksums of generated files |

## Detection rules

- **Leak:** flow discrepancy at a monitored segment exceeds configured mass-balance tolerance.
- **Blockage:** observed flow is below 70% of expected flow while upstream pressure rises.
- **Pump degradation:** measured flow is below 80% of the nominal pump curve prediction under comparable operating conditions.
- **Sensor fault:** implausible value, frozen repeated values, or calibration state failure. A sensor fault is not automatically labelled as a process fault.
- **Tank over-capacity:** level exceeds capacity; only used as a deliberate negative test case, not silently inserted into baseline tank master data.
- **Invalid topology:** pipe endpoint absent from the node registry; deliberately kept in exception fixtures.
- **Missing simulation configuration:** simulation output without a configuration reference; deliberately kept in exception fixtures.

All thresholds are configurable constants in `plantops/rules.py`. These are synthetic demonstration rules, not safety-certified industrial controls.

## Relational model and cardinality

- Facility 1:N Pump, Tank, Valve, Pipe, Sensor, OperatingMode, SimulationRun.
- Pipe N:1 upstream node and N:1 downstream node, where a node is a Pump, Tank, or Valve. Endpoints must be valid and distinct.
- Facility 1:N Telemetry; Sensor 1:N Telemetry; Telemetry optionally references a pump, tank, valve or pipe depending on signal context.
- Facility 1:N Alarm; Alarm optionally references a sensor, telemetry point, and simulation run.
- SimulationRun 1:N Telemetry and 1:N Alarm.
- Pump N:M Pipe through `pump_pipe`; Tank N:M Pipe through `tank_pipe`; Valve N:M Pipe through `valve_pipe`.
- State changes are append-only `state_events`; records use `effective_from` / `effective_to` where applicable.
- Core entity IDs are primary keys; all references are foreign keys in SQLite. The event/telemetry tables retain historical records rather than overwriting state.

## Validation

The validator checks:
- primary-key uniqueness and duplicate records;
- foreign-key integrity and exact ID consistency;
- enumerated values and units;
- pipe endpoint validity and graph connectivity per facility;
- tank capacity boundaries in baseline data;
- timestamp ordering and lifecycle transitions;
- derived alarm consistency and telemetry arithmetic;
- missing configuration and invalid-node exception fixtures are correctly labelled.

## Lawful provenance

All data is synthetic and generated locally. No external or confidential data is used. The manifest records this provenance and the generator version.

## Public GitHub submission

Create a public repository on GitHub, then from this project directory run:

```bash
git init
git add .
git commit -m "Build PlantOps synthetic simulator"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/plantops-simulator.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Verify repository visibility is **Public** and the README appears on the repository landing page.
