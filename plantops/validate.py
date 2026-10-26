"""Validate a generated data directory."""
import argparse, csv, json
from pathlib import Path

def validate(data: Path):
    report=json.loads((data/"validation_summary.json").read_text(encoding="utf-8"))
    errors=[]
    for filename in ("facilities.csv","pumps.csv","tanks.csv","valves.csv","pipes.csv","sensors.csv",
                     "operating_modes.csv","telemetry.csv","alarms.csv","simulation_runs.csv",
                     "ground_truth.csv","edge_cases.csv","data_dictionary.csv"):
        if not (data/filename).exists(): errors.append(f"missing file: {filename}")
    if not report.get("all_checks_pass"): errors.append("generator validation_summary reports failed checks")
    with (data/"telemetry.csv").open(newline="",encoding="utf-8") as f:
        count=sum(1 for _ in csv.DictReader(f))
    if count != report["metrics"]["telemetry_points"]: errors.append("telemetry row count mismatch")
    with (data/"ground_truth.csv").open(newline="",encoding="utf-8") as f:
        fields=csv.DictReader(f).fieldnames or []
    if "ground_truth_label" not in fields: errors.append("ground truth label missing")
    if "issue_type" in (csv.DictReader((data/"telemetry.csv").open(encoding="utf-8")).fieldnames or []):
        errors.append("ground-truth leakage into telemetry")
    return {"valid":not errors,"errors":errors,"telemetry_count":count,"metrics":report.get("metrics",{})}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",default="data")
    args=ap.parse_args()
    result=validate(Path(args.data))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result["valid"] else 1)
if __name__=="__main__": main()
