"""Generate twice with the same seed and compare checksums."""
import argparse, json, shutil
from pathlib import Path
from .generate import generate

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="reproducibility")
    ap.add_argument("--telemetry",type=int,default=1000)
    ap.add_argument("--seed",type=int,default=20261022)
    a=ap.parse_args()
    root=Path(a.out)
    for name in ("run_a","run_b"):
        target=root/name
        if target.exists(): shutil.rmtree(target)
        generate(target,seed=a.seed,telemetry_n=a.telemetry)
    ca=json.loads((root/"run_a"/"checksums.json").read_text())
    cb=json.loads((root/"run_b"/"checksums.json").read_text())
    # SQLite file timestamps/page metadata may differ across runs; compare deterministic CSV/JSON outputs.
    stable={k for k in ca if k.endswith((".csv",".json")) and k!="checksums.json"}
    mismatches=[k for k in sorted(stable) if ca.get(k)!=cb.get(k)]
    result={"seed":a.seed,"telemetry_count":a.telemetry,"compared_files":len(stable),"reproducible":not mismatches,"mismatches":mismatches}
    (root/"reproducibility_report.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if not mismatches else 1)
if __name__=="__main__": main()
