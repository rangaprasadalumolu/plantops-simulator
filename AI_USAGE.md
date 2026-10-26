# AI assistance disclosure

This project was prepared with assistance from ChatGPT. The user should review and personalize this disclosure before submission.

## Where AI accelerated work
- Translating the written requirements into a structured implementation plan and repository layout.
- Drafting synthetic data-generation code, schema documentation, validation checks, README, and test scaffolding.
- Identifying expected edge cases and reproducibility checks.

## What the candidate must personally review and validate
- Run the commands in README.md in their own environment.
- Review the schema, anomaly thresholds, synthetic assumptions, and SQL constraints.
- Inspect validation output and fix any issues before submission.
- Be prepared to explain every design choice and limitation in a walkthrough.
- Add genuine development commits and do not claim tests or repository publication that have not actually happened.

## Prompt history
The main user prompt requested an end-to-end synthetic industrial-fluid simulator with:
- Facility/Pump/Tank/Valve/Pipe master data and dependent records;
- a connected topology, nominal pump curves, tank capacity, valve states, flow/pressure/level telemetry and approximate mass balance;
- labelled leak, blockage, pump-degradation, and sensor-fault scenarios;
- traceable state events, relational keys/cardinalities, separate ground truth, and negative fixtures;
- 3 facilities, 20 pumps, 30 tanks, 60 valves and 100,000 telemetry points;
- fixed-seed reproducibility, CSV/JSON/SQL exports, data dictionary, README, manifest and validation report;
- a public GitHub repository.

The candidate also supplied the YottaFlex AI Candidate Project Submission Guidelines PDF. Its one-page guideline requires executable code and run/verification instructions, a public GitHub repository with meaningful commits, prompt history and honest AI-use disclosure, and visible reasoning about assumptions, decisions, trade-offs, tests, limitations, and evidence of correctness.
