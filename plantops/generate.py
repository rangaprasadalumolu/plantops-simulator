"""Generate reproducible synthetic plant data and relational seed outputs."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, random, sqlite3
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .rules import *

GENERATOR_VERSION = "1.0.0"
BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

DATA_DICTIONARY = [
("Facility","facility_id","string","required","FAC-NNN","n/a","unique","Matches ^FAC-[0-9]{3}$"),
("Facility","name","string","required","non-empty","n/a","unique","Trimmed non-empty name"),
("Facility","region","string","required","synthetic region","n/a","no","Allowed synthetic region"),
("Facility","lifecycle_state","enum","required","active|maintenance|retired","n/a","no","Valid lifecycle state"),
("Pump","pump_id","string","required","PUMP-NNN","n/a","unique","Matches ^PUMP-[0-9]{3}$"),
("Pump","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("Pump","rated_flow_lps","float","required","> 0","L/s","no","Positive nominal flow"),
("Pump","rated_head_kpa","float","required","> 0","kPa","no","Positive nominal head"),
("Pump","curve_a","float","required","> 0","kPa","no","Nominal curve head = a - b*flow^2"),
("Pump","curve_b","float","required","> 0","kPa/(L/s)^2","no","Positive curve coefficient"),
("Tank","tank_id","string","required","TANK-NNN","n/a","unique","Matches ^TANK-[0-9]{3}$"),
("Tank","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("Tank","capacity_l","float","required","> 0","L","no","Positive capacity"),
("Tank","initial_level_pct","float","required","0..100","%","no","Within capacity"),
("Valve","valve_id","string","required","VALVE-NNN","n/a","unique","Matches ^VALVE-[0-9]{3}$"),
("Valve","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("Valve","valve_type","enum","required","gate|ball|butterfly","n/a","no","Allowed enum"),
("Valve","nominal_state","enum","required","open|closed|throttled","n/a","no","Allowed enum"),
("Pipe","pipe_id","string","required","PIPE-NNN","n/a","unique","Valid source and destination nodes"),
("Pipe","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("Pipe","from_node_id","string","required","component ID","n/a","no","Must exist in same facility"),
("Pipe","to_node_id","string","required","component ID","n/a","no","Must exist and differ from source"),
("Pipe","diameter_mm","float","required","> 0","mm","no","Positive diameter"),
("Pipe","length_m","float","required","> 0","m","no","Positive length"),
("Sensor","sensor_id","string","required","SNS-NNN","n/a","unique","Matches ^SNS-[0-9]{3}$"),
("Sensor","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("Sensor","signal_type","enum","required","flow|pressure|tank_level","n/a","no","Allowed enum"),
("Sensor","unit","enum","required","L/s|kPa|%","varies","no","Consistent with signal type"),
("Telemetry","telemetry_id","string","required","TEL-NNNNNN","n/a","unique","Unique deterministic ID"),
("Telemetry","sensor_id","string","required","SNS-NNN","n/a","no","FK sensors.sensor_id"),
("Telemetry","timestamp","datetime","required","ISO-8601 UTC","UTC","no","Monotonic by sensor"),
("Telemetry","value","float","required","finite number","signal unit","no","Plausibility checked"),
("Telemetry","quality","enum","required","good|suspect|bad","n/a","no","Allowed enum"),
("OperatingMode","mode_id","string","required","MODE-NNN","n/a","unique","Unique deterministic ID"),
("OperatingMode","facility_id","string","required","FAC-NNN","n/a","no","FK facilities.facility_id"),
("OperatingMode","mode_name","enum","required","startup|normal|shutdown|maintenance","n/a","no","Allowed enum"),
("Alarm","alarm_id","string","required","ALM-NNNNNN","n/a","unique","Unique deterministic ID"),
("Alarm","rule_code","enum","required","LEAK|BLOCKAGE|PUMP_DEGRADATION|SENSOR_FAULT","n/a","no","Derived from rule"),
("Alarm","severity","enum","required","info|warning|critical","n/a","no","Derived from rule"),
("SimulationRun","simulation_id","string","required","SIM-YYYY-NNNNNN","n/a","unique","Immutable run ID"),
("SimulationRun","seed","integer","required","integer","n/a","no","Fixed seed recorded"),
("SimulationRun","config_json","json","required","valid JSON","n/a","no","Must parse and include input config"),
("SimulationRun","status","enum","required","completed|failed|exception","n/a","no","Valid lifecycle state"),
]

def write_csv(path: Path, rows, fields=None):
    rows = list(rows)
    if fields is None:
        fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def checksum(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def generate(out: Path, seed=20261022, facilities_n=3, pumps_n=20, tanks_n=30, valves_n=60, telemetry_n=100000):
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    facilities = [{"facility_id":f"FAC-{i+1:03d}","name":f"Fluid Facility {i+1:03d}",
        "region":["north","central","south"][i%3],"lifecycle_state":"active",
        "effective_from":"2026-01-01T00:00:00Z","effective_to":""} for i in range(facilities_n)]
    def facility_for(i): return facilities[i % len(facilities)]["facility_id"]
    pumps=[]
    for i in range(pumps_n):
        rated= rng.uniform(35,100)
        pumps.append({"pump_id":f"PUMP-{i+1:03d}","facility_id":facility_for(i),
          "name":f"Transfer Pump {i+1:03d}","rated_flow_lps":round(rated,3),
          "rated_head_kpa":round(rng.uniform(300,650),3),"curve_a":round(rng.uniform(450,800),3),
          "curve_b":round(rng.uniform(.015,.06),5),"lifecycle_state":"active",
          "effective_from":"2026-01-01T00:00:00Z","effective_to":""})
    tanks=[]
    for i in range(tanks_n):
        tanks.append({"tank_id":f"TANK-{i+1:03d}","facility_id":facility_for(i),
          "name":f"Buffer Tank {i+1:03d}","capacity_l":round(rng.uniform(10000,80000),2),
          "initial_level_pct":round(rng.uniform(20,80),2),"lifecycle_state":"active",
          "effective_from":"2026-01-01T00:00:00Z","effective_to":""})
    valves=[]
    for i in range(valves_n):
        valves.append({"valve_id":f"VALVE-{i+1:03d}","facility_id":facility_for(i),
          "name":f"Control Valve {i+1:03d}","valve_type":rng.choice(["gate","ball","butterfly"]),
          "nominal_state":rng.choices(["open","closed","throttled"],[.78,.08,.14])[0],
          "lifecycle_state":"active","effective_from":"2026-01-01T00:00:00Z","effective_to":""})
    nodes=[]
    for group, idkey in [(pumps,"pump_id"),(tanks,"tank_id"),(valves,"valve_id")]:
        nodes.extend({"node_id":x[idkey],"facility_id":x["facility_id"],"node_type":idkey.split("_")[0]} for x in group)
    by_fac=defaultdict(list)
    for n in nodes: by_fac[n["facility_id"]].append(n)
    pipes=[]
    for fac in facilities:
        ns=by_fac[fac["facility_id"]]
        # A ring ensures connected topology in each facility; additional edges add meaningful variation.
        if len(ns)>1:
            edges=[(ns[i],ns[(i+1)%len(ns)]) for i in range(len(ns))]
            extra=max(1,len(ns)//4)
            for j in range(extra):
                a=ns[rng.randrange(len(ns))]; b=ns[rng.randrange(len(ns))]
                if a["node_id"] != b["node_id"]: edges.append((a,b))
            for a,b in edges:
                pipes.append({"pipe_id":f"PIPE-{len(pipes)+1:03d}","facility_id":fac["facility_id"],
                    "from_node_id":a["node_id"],"to_node_id":b["node_id"],
                    "diameter_mm":round(rng.uniform(40,250),2),"length_m":round(rng.uniform(5,300),2),
                    "status":"active","effective_from":"2026-01-01T00:00:00Z","effective_to":""})
    sensors=[]
    for i in range(max(1, pumps_n + tanks_n + valves_n)):
        signal=["flow","pressure","tank_level"][i%3]
        entity=(pumps+tanks+valves)[i%len(pumps+tanks+valves)]
        idkey=next(k for k in ("pump_id","tank_id","valve_id") if k in entity)
        sensors.append({"sensor_id":f"SNS-{i+1:03d}","facility_id":entity["facility_id"],
          "signal_type":signal,"unit":{"flow":"L/s","pressure":"kPa","tank_level":"%"}[signal],
          "entity_id":entity[idkey],"calibration_state":"valid","lifecycle_state":"active",
          "effective_from":"2026-01-01T00:00:00Z","effective_to":""})
    modes=[]
    for i, fac in enumerate(facilities):
        for j, name in enumerate(["startup","normal","shutdown","maintenance"]):
            modes.append({"mode_id":f"MODE-{len(modes)+1:03d}","facility_id":fac["facility_id"],
              "mode_name":name,"allowed_next_modes":{"startup":"normal","normal":"shutdown",
              "shutdown":"maintenance","maintenance":"startup"}[name],"effective_from":"2026-01-01T00:00:00Z"})
    sim_id="SIM-2026-000001"
    config={"seed":seed,"generator_version":GENERATOR_VERSION,"telemetry_count":telemetry_n,
      "facilities":facilities_n,"pumps":pumps_n,"tanks":tanks_n,"valves":valves_n,
      "scenario_policy":"deterministic periodic scenario assignment","units":{"flow":"L/s","pressure":"kPa","tank_level":"%"}}
    sim_runs=[{"simulation_id":sim_id,"seed":seed,"config_json":json.dumps(config,sort_keys=True),
      "assumptions":"Synthetic steady-state approximations; anomaly scenarios are rule-labelled.",
      "started_at":"2026-10-22T00:00:00Z","completed_at":"2026-10-22T00:00:10Z",
      "status":"completed","outcome_json":json.dumps({"requested_telemetry":telemetry_n},sort_keys=True)}]
    telemetry=[]
    ground_truth=[]
    alarms=[]
    state_events=[]
    sensor_by_type=defaultdict(list)
    for s in sensors: sensor_by_type[s["signal_type"]].append(s)
    scenarios=["normal","normal","normal","leak","blockage","pump_degradation","sensor_fault"]
    for i in range(telemetry_n):
        s=sensors[i%len(sensors)]
        scenario=scenarios[(i//3)%len(scenarios)]
        t=BASE_TIME+timedelta(seconds=i*5)
        if s["signal_type"]=="flow":
            expected=rng.uniform(15, min(110, FLOW_MAX_LPS))
            value=expected
            if scenario=="leak": value=expected*rng.uniform(.55,.72)
            elif scenario=="blockage": value=expected*rng.uniform(.35,.65)
            elif scenario=="pump_degradation": value=expected*rng.uniform(.55,.78)
            elif scenario=="sensor_fault": value=expected*2.8
            unit="L/s"
        elif s["signal_type"]=="pressure":
            value=rng.uniform(180,520)
            if scenario=="blockage": value=rng.uniform(660,820)
            elif scenario=="sensor_fault": value=-abs(value)
            unit="kPa"
        else:
            value=rng.uniform(15,88)
            if scenario=="sensor_fault": value=100.5
            unit="%"
        quality="bad" if scenario=="sensor_fault" else ("suspect" if scenario in ("leak","blockage","pump_degradation") else "good")
        expected_flow=round(value if s["signal_type"]=="flow" else rng.uniform(20,90),3)
        observed_flow=round(value if s["signal_type"]=="flow" else expected_flow,3)
        balance_error=round(abs(expected_flow-observed_flow)/max(expected_flow,1),5)
        row={"telemetry_id":f"TEL-{i+1:06d}","simulation_id":sim_id,"facility_id":s["facility_id"],
          "sensor_id":s["sensor_id"],"signal_type":s["signal_type"],"timestamp":t.isoformat().replace("+00:00","Z"),
          "value":round(value,4),"unit":unit,"quality":quality,"expected_flow_lps":expected_flow,
          "observed_flow_lps":observed_flow,"mass_balance_error_ratio":balance_error}
        telemetry.append(row)
        # Labels are produced from scenario injection plus rule checks, not independent random draws.
        detected=None
        if s["signal_type"]=="flow" and scenario=="leak" and value < expected* (1-MASS_BALANCE_TOLERANCE): detected="LEAK"
        elif s["signal_type"]=="pressure" and scenario=="blockage" and value>PRESSURE_HIGH_KPA: detected="BLOCKAGE"
        elif s["signal_type"]=="flow" and scenario=="pump_degradation" and value/expected < PUMP_DEGRADATION_FLOW_RATIO: detected="PUMP_DEGRADATION"
        elif scenario=="sensor_fault" and (value<0 or value>100 or quality=="bad"): detected="SENSOR_FAULT"
        if scenario!="normal":
            gt={"telemetry_id":row["telemetry_id"],"scenario_id":f"SCN-{(i//3)+1:06d}",
              "issue_type":scenario,"ground_truth_label":detected or scenario.upper(),
              "expected_decision":"inspect_sensor" if scenario=="sensor_fault" else "investigate_process",
              "rule_detected":bool(detected),"rule_code":detected or ""}
            ground_truth.append(gt)
        if detected:
            alarms.append({"alarm_id":f"ALM-{len(alarms)+1:06d}","simulation_id":sim_id,
              "telemetry_id":row["telemetry_id"],"sensor_id":s["sensor_id"],"facility_id":s["facility_id"],
              "rule_code":detected,"severity":"critical" if detected in ("LEAK","BLOCKAGE") else "warning",
              "created_at":row["timestamp"],"status":"open","evidence_json":json.dumps({"value":row["value"],"unit":unit})})
        if i < min(100,telemetry_n) and i%10==0:
            state_events.append({"event_id":f"EVT-{len(state_events)+1:06d}","entity_id":s["sensor_id"],
              "entity_type":"Sensor","event_type":"calibration_check","old_state":"unknown","new_state":s["calibration_state"],
              "event_time":row["timestamp"],"actor":"system","reason":"synthetic initial state audit"})
    edge_cases=[
      {"case_id":"EDGE-001","issue_type":"invalid_pipe_node","record_json":json.dumps({"pipe_id":"PIPE-EDGE-001","from_node_id":"NODE-MISSING","to_node_id":nodes[0]["node_id"]}),"expected_result":"reject_fk","ground_truth":"invalid_topology"},
      {"case_id":"EDGE-002","issue_type":"tank_level_over_capacity","record_json":json.dumps({"tank_id":tanks[0]["tank_id"],"level_pct":105.0,"capacity_pct":100.0}),"expected_result":"raise_capacity_validation","ground_truth":"tank_over_capacity"},
      {"case_id":"EDGE-003","issue_type":"mass_balance_violation","record_json":json.dumps({"expected_flow_lps":100.0,"observed_flow_lps":60.0,"tolerance":MASS_BALANCE_TOLERANCE}),"expected_result":"raise_balance_alarm","ground_truth":"flow_conservation_violation"},
      {"case_id":"EDGE-004","issue_type":"missing_simulation_configuration","record_json":json.dumps({"simulation_id":"SIM-EDGE-000004","config_json":None}),"expected_result":"reject_run","ground_truth":"missing_input_configuration"},
      {"case_id":"EDGE-005","issue_type":"sensor_fault_mislabelled_as_process_fault","record_json":json.dumps({"sensor_id":sensors[-1]["sensor_id"],"sensor_quality":"bad","claimed_label":"LEAK"}),"expected_result":"classify_sensor_fault_first","ground_truth":"label_mismatch"}
    ]
    # Export flat files.
    tables={"facilities":facilities,"pumps":pumps,"tanks":tanks,"valves":valves,"pipes":pipes,
      "sensors":sensors,"operating_modes":modes,"telemetry":telemetry,"alarms":alarms,
      "simulation_runs":sim_runs,"ground_truth":ground_truth,"edge_cases":edge_cases,"state_events":state_events}
    for name, rows in tables.items():
        default_fields = {
          "ground_truth":["telemetry_id","scenario_id","issue_type","ground_truth_label","expected_decision","rule_detected","rule_code"],
          "edge_cases":["case_id","issue_type","record_json","expected_result","ground_truth"],
          "alarms":["alarm_id","simulation_id","telemetry_id","sensor_id","facility_id","rule_code","severity","created_at","status","evidence_json"]
        }
        write_csv(out/f"{name}.csv", rows, default_fields.get(name))
    (out/"ground_truth.json").write_text(json.dumps(ground_truth,indent=2),encoding="utf-8")
    write_csv(out/"data_dictionary.csv",[dict(entity=e,field=f,type=t,required=r,allowed_values=a,unit=u,unique=un,validation=v) for e,f,t,r,a,u,un,v in DATA_DICTIONARY])
    manifest={"provenance":"fully synthetic; no external data used","generator_version":GENERATOR_VERSION,
      "seed":seed,"generated_at_utc":"2026-10-22T00:00:00Z","config":config,
      "transformations":["deterministic IDs","synthetic nominal operating values","scenario injection after baseline generation","rule-derived alarms and labels"]}
    (out/"source_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    # Relational SQLite database with primary/foreign keys and bridge tables.
    db=sqlite3.connect(out/"plantops.sqlite")
    db.execute("PRAGMA foreign_keys=ON")
    schema = """
    CREATE TABLE facilities(facility_id TEXT PRIMARY KEY,name TEXT UNIQUE NOT NULL,region TEXT NOT NULL,lifecycle_state TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT);
    CREATE TABLE pumps(pump_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),name TEXT NOT NULL,rated_flow_lps REAL NOT NULL CHECK(rated_flow_lps>0),rated_head_kpa REAL NOT NULL CHECK(rated_head_kpa>0),curve_a REAL NOT NULL,curve_b REAL NOT NULL,lifecycle_state TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT);
    CREATE TABLE tanks(tank_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),name TEXT NOT NULL,capacity_l REAL NOT NULL CHECK(capacity_l>0),initial_level_pct REAL NOT NULL CHECK(initial_level_pct BETWEEN 0 AND 100),lifecycle_state TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT);
    CREATE TABLE valves(valve_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),name TEXT NOT NULL,valve_type TEXT NOT NULL CHECK(valve_type IN ('gate','ball','butterfly')),nominal_state TEXT NOT NULL CHECK(nominal_state IN ('open','closed','throttled')),lifecycle_state TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT);
    CREATE TABLE pipes(pipe_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),from_node_id TEXT NOT NULL,to_node_id TEXT NOT NULL,diameter_mm REAL NOT NULL,length_m REAL NOT NULL,status TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT,CHECK(from_node_id<>to_node_id));
    CREATE TABLE sensors(sensor_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),signal_type TEXT NOT NULL CHECK(signal_type IN ('flow','pressure','tank_level')),unit TEXT NOT NULL,entity_id TEXT NOT NULL,calibration_state TEXT NOT NULL,lifecycle_state TEXT NOT NULL,effective_from TEXT NOT NULL,effective_to TEXT);
    CREATE TABLE operating_modes(mode_id TEXT PRIMARY KEY,facility_id TEXT NOT NULL REFERENCES facilities(facility_id),mode_name TEXT NOT NULL,allowed_next_modes TEXT NOT NULL,effective_from TEXT NOT NULL);
    CREATE TABLE simulation_runs(simulation_id TEXT PRIMARY KEY,seed INTEGER NOT NULL,config_json TEXT NOT NULL,assumptions TEXT NOT NULL,started_at TEXT NOT NULL,completed_at TEXT NOT NULL,status TEXT NOT NULL,outcome_json TEXT NOT NULL,CHECK(completed_at>=started_at));
    CREATE TABLE telemetry(telemetry_id TEXT PRIMARY KEY,simulation_id TEXT NOT NULL REFERENCES simulation_runs(simulation_id),facility_id TEXT NOT NULL REFERENCES facilities(facility_id),sensor_id TEXT NOT NULL REFERENCES sensors(sensor_id),signal_type TEXT NOT NULL,timestamp TEXT NOT NULL,value REAL NOT NULL,unit TEXT NOT NULL,quality TEXT NOT NULL,expected_flow_lps REAL,observed_flow_lps REAL,mass_balance_error_ratio REAL);
    CREATE TABLE alarms(alarm_id TEXT PRIMARY KEY,simulation_id TEXT NOT NULL REFERENCES simulation_runs(simulation_id),telemetry_id TEXT NOT NULL REFERENCES telemetry(telemetry_id),sensor_id TEXT NOT NULL REFERENCES sensors(sensor_id),facility_id TEXT NOT NULL REFERENCES facilities(facility_id),rule_code TEXT NOT NULL,severity TEXT NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL,evidence_json TEXT NOT NULL);
    CREATE TABLE state_events(event_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,entity_type TEXT NOT NULL,event_type TEXT NOT NULL,old_state TEXT,new_state TEXT NOT NULL,event_time TEXT NOT NULL,actor TEXT NOT NULL,reason TEXT NOT NULL);
    CREATE TABLE pump_pipe(pump_id TEXT REFERENCES pumps(pump_id),pipe_id TEXT REFERENCES pipes(pipe_id),PRIMARY KEY(pump_id,pipe_id));
    CREATE TABLE tank_pipe(tank_id TEXT REFERENCES tanks(tank_id),pipe_id TEXT REFERENCES pipes(pipe_id),PRIMARY KEY(tank_id,pipe_id));
    CREATE TABLE valve_pipe(valve_id TEXT REFERENCES valves(valve_id),pipe_id TEXT REFERENCES pipes(pipe_id),PRIMARY KEY(valve_id,pipe_id));
    """
    db.executescript(schema)
    insert_order = ["facilities","pumps","tanks","valves","pipes","sensors","operating_modes","simulation_runs","telemetry","alarms","state_events"]
    for name in insert_order:
        rows = tables[name]
        if name in ("ground_truth","edge_cases"): continue
        if not rows: continue
        cols=list(rows[0].keys())
        # Existing normalized schema is loaded table-by-table; columns shared with schema are inserted.
        actual=[r[1] for r in db.execute(f"PRAGMA table_info({name})").fetchall()]
        use=[c for c in cols if c in actual]
        if use:
            db.executemany(f"INSERT INTO {name} ({','.join(use)}) VALUES ({','.join('?' for _ in use)})",
                [[r.get(c) for c in use] for r in rows])
    # Populate bridge tables based on endpoints.
    for p in pipes:
        for pump in pumps:
            if pump["pump_id"] in (p["from_node_id"],p["to_node_id"]): db.execute("INSERT OR IGNORE INTO pump_pipe VALUES (?,?)",(pump["pump_id"],p["pipe_id"]))
        for tank in tanks:
            if tank["tank_id"] in (p["from_node_id"],p["to_node_id"]): db.execute("INSERT OR IGNORE INTO tank_pipe VALUES (?,?)",(tank["tank_id"],p["pipe_id"]))
        for valve in valves:
            if valve["valve_id"] in (p["from_node_id"],p["to_node_id"]): db.execute("INSERT OR IGNORE INTO valve_pipe VALUES (?,?)",(valve["valve_id"],p["pipe_id"]))
    db.commit()
    fk_errors=list(db.execute("PRAGMA foreign_key_check"))
    db.close()
    # Validate records and calculate metrics.
    ids={name:{r[next(k for k in r if k.endswith("_id") and k not in ("from_node_id","to_node_id"))] for r in rows} for name,rows in tables.items() if rows and name not in ("ground_truth","edge_cases")}
    checks={
      "primary_keys_unique":all(len(v)==len(tables[k]) for k,v in ids.items()),
      "facility_foreign_keys_valid":all(x["facility_id"] in {f["facility_id"] for f in facilities} for key in ("pumps","tanks","valves","pipes","sensors","operating_modes") for x in tables[key]),
      "pipe_endpoints_valid":all(p["from_node_id"] in {n["node_id"] for n in nodes} and p["to_node_id"] in {n["node_id"] for n in nodes} for p in pipes),
      "pipe_endpoints_distinct":all(p["from_node_id"]!=p["to_node_id"] for p in pipes),
      "tank_levels_within_capacity":all(0<=float(t["initial_level_pct"])<=100 for t in tanks),
      "telemetry_count_exact":len(telemetry)==telemetry_n,
      "simulation_config_present":all(bool(json.loads(x["config_json"])) for x in sim_runs),
      "alarm_references_valid":all(a["telemetry_id"] in {t["telemetry_id"] for t in telemetry} for a in alarms),
      "sqlite_foreign_key_check_clean":len(fk_errors)==0,
      "ground_truth_separate":not any("issue_type" in r for r in telemetry),
      "scenario_coverage":set(x["issue_type"] for x in ground_truth).issuperset({"leak","blockage","pump_degradation","sensor_fault"}) if telemetry_n>=len(sensors)*4 else True,
    }
    # Connectivity check per facility (undirected topology).
    connectivity={}
    for fac in facilities:
        ns=[n["node_id"] for n in nodes if n["facility_id"]==fac["facility_id"]]
        adj=defaultdict(set)
        for p in pipes:
            if p["facility_id"]==fac["facility_id"]:
                adj[p["from_node_id"]].add(p["to_node_id"]); adj[p["to_node_id"]].add(p["from_node_id"])
        seen=set()
        if ns:
            q=[ns[0]]
            while q:
                cur=q.pop()
                if cur not in seen:
                    seen.add(cur); q.extend(adj[cur]-seen)
        connectivity[fac["facility_id"]]=len(seen)==len(ns)
    checks["topology_connected_per_facility"]=all(connectivity.values())
    metrics={"telemetry_points":len(telemetry),"alarms":len(alarms),"ground_truth_cases":len(ground_truth),
      "alarm_rate":round(len(alarms)/max(1,len(telemetry)),5),
      "scenario_counts":{k:sum(1 for x in ground_truth if x["issue_type"]==k) for k in SCENARIO_TYPES},
      "detection_rate_on_labelled_anomalies":round(sum(1 for x in ground_truth if x["rule_detected"])/max(1,len(ground_truth)),5),
      "facility_topology_connected":connectivity,"sqlite_foreign_key_errors":len(fk_errors)}
    report={"seed":seed,"config":config,"checks":checks,"all_checks_pass":all(checks.values()),"metrics":metrics,
      "edge_case_count":len(edge_cases),"edge_cases_are_isolated_fixtures":True}
    (out/"validation_summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    # Checksums exclude themselves to avoid self-reference.
    sums={p.name:checksum(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!="checksums.json"}
    (out/"checksums.json").write_text(json.dumps(sums,indent=2),encoding="utf-8")
    if not report["all_checks_pass"]:
        raise RuntimeError("Validation failed: "+json.dumps({k:v for k,v in checks.items() if not v}))
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",default="data")
    ap.add_argument("--seed",type=int,default=20261022)
    ap.add_argument("--facilities",type=int,default=3)
    ap.add_argument("--pumps",type=int,default=20)
    ap.add_argument("--tanks",type=int,default=30)
    ap.add_argument("--valves",type=int,default=60)
    ap.add_argument("--telemetry",type=int,default=100000)
    a=ap.parse_args()
    report=generate(Path(a.out),a.seed,a.facilities,a.pumps,a.tanks,a.valves,a.telemetry)
    print(json.dumps({"output":str(Path(a.out).resolve()),"all_checks_pass":report["all_checks_pass"],"metrics":report["metrics"]},indent=2))
if __name__=="__main__": main()
