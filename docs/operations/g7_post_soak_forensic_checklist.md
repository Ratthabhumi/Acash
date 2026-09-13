# Gate 7 / Stage S11 Post-Soak Forensic Audit Checklist & Runbook

**Document ID:** `docs/operations/g7_post_soak_forensic_checklist.md`  
**STATUS: NON-GOVERNING**  
**AUTHORITY: NONE**  
**EMPIRICAL AUTHORIZATION: NONE**  
**BACKTEST AUTHORIZATION: NONE**  
**PAPER AUTHORIZATION: NONE**  
**LIVE AUTHORIZATION: NONE**  
**EXECUTION AUTHORIZATION: READ-ONLY POST-SOAK ONLY**  
**Target Environment:** Homelab SRE & Evidence Substrate  
**Canonical Governance Context:** `AGENTS.md`, `scripts/automation/execute_g7_soak.sh`, `scripts/automation/verify_g7_evidence.sh`, `scripts/automation/g7.sh`

---

> [!CAUTION]
> ### STRICT READ-ONLY POST-SOAK INVARIANTS
> - **DO NOT EXECUTE WHILE SOAK IS ACTIVE:** This checklist is designed for use **strictly after** the active Gate 7 (G7) soak run has terminated. Running these commands against an active soak risks perturbing socket telemetry, timing, and evidence generation.
> - **STRICT FAIL-CLOSED READ-ONLY INSPECTION:** All inspection commands are strictly read-only. Never restart containers, never stop containers, never reload Docker, never remove evidence, and never alter file modes (`chmod` / `chown`).
> - **NON-RETROACTIVITY OF CODE PATCHES:** A source-code patch committed after process start does not retroactively change already-running shell state, already-resolved variables, or historical monitoring behavior. Runtime evidence and harness validity must be evaluated separately.
> - **CANONICAL DISTINCTION TRINITY:**
>   $$\text{Physical Runtime Continuity} \neq \text{Canonical Harness Validity} \neq \text{Human Acceptance}$$
> - **NO AUTO-RATIFICATION:** S11 cannot be automatically closed, and G7 cannot be automatically ratified by automated scripts or this checklist. Human Governance ratification is strictly required.

---

## 1. Executive Summary & Objective

Gate 7 (`G7`) and Stage 11 (`S11`) validate the operational resilience, continuous feed stability, session journaling, and cryptographic evidence sealing of the ACASH execution runtime under a continuous 6-hour soak test.

The objective of this forensic checklist is to:
1. Provide a rigorous, step-by-step, read-only audit protocol to verify soak evidence immediately upon completion.
2. Formulate explicit criteria distinguishing physical container continuity from harness session-binding correctness.
3. Diagnose potential host-filesystem unreadability using permission-safe containerized tooling without mutating file ownership.
4. Deliver an unambiguous, categorical forensic verdict scorecard for Human Governance review.

---

## 2. Forensic Inspection Workflow Overview

The post-soak audit proceeds through eight discrete verification gates:

```text
  [ 1. Container Identity & Process Lifecycle ]
                      │
                      ▼
  [ 2. Duration & Continuity Verification ]
                      │
                      ▼
  [ 3. Authoritative Event & Disconnect Ledger ]
                      │
                      ▼
  [ 4. Market Data Bar Monotonicity & Cadence ]
                      │
                      ▼
  [ 5. Cryptographic Evidence Sealing & Integrity ]
                      │
                      ▼
  [ 6. Security, Isolation & Least-Privilege Audit ]
                      │
                      ▼
  [ 7. Harness Session Binding Audit ]
                      │
                      ▼
  [ 8. Forensic Verdict Scorecard & S11 Gate ]
```

---

## 3. Section-by-Section Forensic Audit Protocol

### 3.1 Container Identity & Environment Audit
Record the exact container runtime parameters from the host Docker daemon:

- **Target Container Name:** `acash-staging` (or session-specific override)
- **Fields to Extract:**
  - `container_id`: Full 64-character SHA-256 container ID.
  - `image_id`: Full image digest.
  - `image_tag`: Local image tag (e.g. `acash:e36-ws10-staging`).
  - `container_started_at`: Exact ISO-8601 start timestamp (`.State.StartedAt`).
  - `container_finished_at`: Exact ISO-8601 finish timestamp (`.State.FinishedAt`).
  - `exit_code`: Final process exit code (`.State.ExitCode`).
  - `restart_count`: Number of unexpected container restarts (`.RestartCount`).
  - `oom_killed`: Kernel out-of-memory kill flag (`.State.OOMKilled`).
  - `pid`: Host process PID.
  - `git_commit_pi`: Git commit of `Pi_Personal-Infrastructure` at launch.
  - `git_commit_acash`: Git commit of `Acash` runtime image at launch.

#### Read-Only Inspection Command:
```bash
docker inspect acash-staging --format '{{json .}}' | python3 -c '
import json, sys
data = json.load(sys.stdin)
state = data["State"]
cfg = data["Config"]
host_cfg = data["HostConfig"]
print("=== CONTAINER IDENTITY ===")
print(f"Container ID:     {data[\"Id\"]}")
print(f"Image ID:         {data[\"Image\"]}")
print(f"Image Tag:        {cfg.get(\"Image\", \"N/A\")}")
print(f"StartedAt:        {state.get(\"StartedAt\")}")
print(f"FinishedAt:       {state.get(\"FinishedAt\")}")
print(f"ExitCode:         {state.get(\"ExitCode\")}")
print(f"RestartCount:     {data.get(\"RestartCount\", 0)}")
print(f"OOMKilled:        {state.get(\"OOMKilled\", False)}")
print(f"User:             {cfg.get(\"User\", \"N/A\")}")
print(f"RestartPolicy:    {host_cfg.get(\"RestartPolicy\", {}).get(\"Name\", \"N/A\")}")
'
```

---

### 3.2 Duration & Continuity Verification
Verify that the soak satisfies the minimum continuous operational duration without interruption.

> [!IMPORTANT]
> **DISCRETE DURATION METRICS:** The auditor must distinguish between four separate time intervals that are not automatically identical:
> 1. **Container Runtime Duration:** Wall-clock delta between container start and container stop.
> 2. **Session Journal Duration:** Delta between `SESSION_STARTED` and final journal event.
> 3. **Market Bar Coverage:** Delta between first received M1 bar timestamp and last received M1 bar.
> 4. **Harness Timer Duration:** Elapsed time recorded by the host `execute_g7_soak.sh` wrapper script.

- **Canonical Minimum Requirement:** $\ge 21,600$ continuous seconds ($6.00$ hours).
- **Restart Invariant:** `RestartCount == 0`. Any container restart resets the continuous clock to zero.

#### Read-Only Duration Calculation Command:
```bash
python3 -c '
from datetime import datetime
started_str = "<CONTAINER_STARTED_AT>" # e.g. 2026-09-13T02:51:17.123456Z
finished_str = "<CONTAINER_FINISHED_AT>"
t0 = datetime.fromisoformat(started_str.replace("Z", "+00:00"))
t1 = datetime.fromisoformat(finished_str.replace("Z", "+00:00")) if finished_str != "0001-01-01T00:00:00Z" else datetime.now(t0.tzinfo)
elapsed = (t1 - t0).total_seconds()
print(f"Continuous Wall-Clock Seconds: {elapsed:.2f} s ({elapsed/3600:.3f} h)")
assert elapsed >= 21600.0, f"Duration violation: {elapsed} < 21600s"
'
```

---

### 3.3 Authoritative Event & Disconnect Ledger
The session journal (`.journal.jsonl`) is the single source of truth for runtime events.

- **Required Event Checks:**
  - First event must be `SESSION_STARTED` with matching `session_id`.
  - Count total `FEED_CONNECTED` events.
  - Count total `FEED_DISCONNECTED` events.
  - If `FEED_DISCONNECTED` occurs:
    - Extract exact timestamps of all disconnects.
    - Check whether disconnect was resolved by operator recovery or resulted in terminal disconnect.
    - Verify that no auto-reconnect occurred (must remain fail-closed).
  - Terminal state must be clean shutdown or active wait (not unexpected socket crash).

#### Permission-Safe Read-Only Command:
```bash
# Execute within read-only container mount to bypass host permission boundaries
STORAGE_ROOT="/data/docker/acash/sessions"
ACASH_IMAGE="acash:e36-ws10-staging"
SESSION_ID="<SESSION_ID>"

docker run --rm \
    --user 10001:10001 \
    -v "${STORAGE_ROOT}:${STORAGE_ROOT}:ro" \
    --entrypoint python \
    "${ACASH_IMAGE}" \
    -c '
import sys, json

session_id = sys.argv[1]
journal_path = f"/data/docker/acash/sessions/{session_id}.journal.jsonl"

events = []
feed_connected = 0
feed_disconnected = 0
disconnect_log = []

with open(journal_path, "r", encoding="utf-8") as f:
    for line_idx, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception as e:
            print(f"[CORRUPT] Malformed JSON line {line_idx}: {e}")
            sys.exit(1)
        
        etype = ev.get("event_type")
        events.append(etype)
        if etype == "FEED_CONNECTED":
            feed_connected += 1
        elif etype == "FEED_DISCONNECTED":
            feed_disconnected += 1
            disconnect_log.append(ev)

print(f"Total Events:          {len(events)}")
print(f"FEED_CONNECTED Count:  {feed_connected}")
print(f"FEED_DISCONNECTED:     {feed_disconnected}")
if disconnect_log:
    print("=== DISCONNECT CHRONOLOGY ===")
    for d in disconnect_log:
        print(f"  Time: {d.get(\"event_time_utc\") or d.get(\"recorded_at_utc\")}, Reason: {d.get(\"payload\", {}).get(\"reason\", \"N/A\")}")
' "${SESSION_ID}"
```

---

### 3.4 Market Data Bar Monotonicity & Gap Semantics
Audit all M1 bars recorded during the session for timestamp ordering, duplication, and missing windows.

- **Metrics to Compute:**
  - `total_bars`: Count of discrete M1 klines ingested.
  - `first_bar_utc` & `last_bar_utc`: First and last bar timestamps.
  - `duplicate_timestamps`: Count of duplicate bar timestamps (must be 0).
  - `out_of_order_bars`: Count of non-monotonic timestamps (must be 0).
  - `unexpected_gaps`: Minutes where no bar was emitted during active feed connection.
  - `largest_gap_minutes`: Maximum duration between consecutive bars.

> [!NOTE]
> **GAP SEMANTICS INVARIANT:** For M1 feeds, a missing minute is not automatically an engine defect. In thin instruments or illiquid periods, zero trades produce zero bars. However, for `BTCUSDT` on Binance, trading occurs in 100% of minutes under normal operation. Any gap $\ge 2$ minutes must be cross-checked against exchange maintenance records or socket disconnect events.

#### Permission-Safe Read-Only Command:
```bash
docker run --rm \
    --user 10001:10001 \
    -v "${STORAGE_ROOT}:${STORAGE_ROOT}:ro" \
    --entrypoint python \
    "${ACASH_IMAGE}" \
    -c '
import sys, json
from datetime import datetime

session_id = sys.argv[1]
journal_path = f"/data/docker/acash/sessions/{session_id}.journal.jsonl"

bar_times = []
with open(journal_path, "r", encoding="utf-8") as f:
    for line in f:
        ev = json.loads(line)
        if ev.get("event_type") == "BAR_INGESTED":
            t_str = ev.get("payload", {}).get("timestamp_utc") or ev.get("event_time_utc")
            if t_str:
                bar_times.append(datetime.fromisoformat(t_str.replace("Z", "+00:00")))

print(f"Total Bars Ingested: {len(bar_times)}")
if bar_times:
    print(f"First Bar UTC:       {bar_times[0]}")
    print(f"Last Bar UTC:        {bar_times[-1]}")
    
    dups = len(bar_times) - len(set(bar_times))
    print(f"Duplicate Bars:      {dups}")
    
    out_of_order = sum(1 for i in range(len(bar_times)-1) if bar_times[i] >= bar_times[i+1])
    print(f"Out-of-Order Bars:   {out_of_order}")
' "${SESSION_ID}"
```

---

### 3.5 Cryptographic Evidence Sealing & Hash Integrity
Gate G7 produces three mandatory evidence artifacts:
1. `${SESSION_ID}.journal.jsonl`: Authoritative event stream.
2. `${SESSION_ID}.manifest.json`: Execution manifest with SHA-256 hashes.
3. `${SESSION_ID}.snapshot.json`: Terminal state snapshot.

- **Verification Invariants:**
  - All three files must exist and have non-zero size (`-s`).
  - `manifest.json` must contain `journal_sha256` matching the exact hash of `${SESSION_ID}.journal.jsonl`.
  - `snapshot.json` must contain `manifest_sha256` matching the hash of `${SESSION_ID}.manifest.json`.
  - Session IDs across all three files must be byte-for-byte identical.
  - File permissions must conform to non-root least privilege (`10001:10001`, mode `0644` or `0640`).

> [!CAUTION]
> **LEAST-PRIVILEGE PERMISSION DISCIPLINE:** If host commands return permission denied when reading evidence, classify this status as **`HOST UNREADABLE`**, NOT as missing. Never execute `chmod` or `chown` against production or soak storage. Use the containerized read-only inspection pattern.

#### Permission-Safe Verification Command:
```bash
docker run --rm \
    --user 10001:10001 \
    -v "${STORAGE_ROOT}:${STORAGE_ROOT}:ro" \
    --entrypoint python \
    "${ACASH_IMAGE}" \
    -c '
import sys, os, json, hashlib

session_id = sys.argv[1]
root = "/data/docker/acash/sessions"
j_path = os.path.join(root, f"{session_id}.journal.jsonl")
m_path = os.path.join(root, f"{session_id}.manifest.json")
s_path = os.path.join(root, f"{session_id}.snapshot.json")

for p, name in [(j_path, "Journal"), (m_path, "Manifest"), (s_path, "Snapshot")]:
    if not os.path.isfile(p):
        print(f"[FAIL] {name} missing: {p}")
        sys.exit(1)
    if os.path.getsize(p) == 0:
        print(f"[FAIL] {name} is empty: {p}")
        sys.exit(1)

with open(j_path, "rb") as f:
    j_hash = hashlib.sha256(f.read()).hexdigest()

with open(m_path, "r", encoding="utf-8") as f:
    m_data = json.load(f)

with open(s_path, "r", encoding="utf-8") as f:
    s_data = json.load(f)

print("=== CRYPTOGRAPHIC INTEGRITY ===")
print(f"Calculated Journal SHA-256: {j_hash}")
print(f"Manifest Journal SHA-256:   {m_data.get(\"journal_sha256\", \"MISSING\")}")
assert j_hash == m_data.get("journal_sha256"), "Journal SHA-256 mismatch!"

with open(m_path, "rb") as f:
    m_hash = hashlib.sha256(f.read()).hexdigest()

print(f"Calculated Manifest SHA-256:{m_hash}")
print(f"Snapshot Manifest SHA-256:  {s_data.get(\"manifest_sha256\", \"MISSING\")}")
assert m_hash == s_data.get("manifest_sha256"), "Manifest SHA-256 mismatch!"

assert m_data.get("session_id") == session_id, "Manifest session_id mismatch!"
assert s_data.get("session_id") == session_id, "Snapshot session_id mismatch!"
print("RESULT: ALL CRYPTOGRAPHIC SEALS VALID.")
' "${SESSION_ID}"
```

---

### 3.6 Security & Governance Boundary Audit
Verify that the runtime executed within strict sandboxed limits:

- `NO_REAL_ORDERS == true` (enforced in environment & configuration).
- `capital == $0.00` (synthetic paper state only; zero trading capital).
- `paper_authorized == false` (operational soak only; not paper trading).
- `live_locked == true` (execution completely disabled).
- `operator_only_recovery == true` (zero autonomous reconnect attempts).
- Security options: verify `no-new-privileges:true`.
- Exposed ports: verify zero public ports published (`.NetworkSettings.Ports` empty or localhost only).
- Read-only root filesystem: verify container isolation.

---

### 3.7 Harness Session Binding Audit
Audit whether the host harness correctly bound to the runtime session ID.

> [!IMPORTANT]
> **HARNESS RESOLUTION CONTRACT:**
> - Record the `SESSION_ID` resolved by the host harness at launch.
> - Record the actual runtime `SESSION_ID` generated by the container.
> - Record the target `SESSION_ID` queried by `g7.sh status` during monitoring.
> - Record the `SESSION_ID` targeted by `verify_g7_evidence.sh` at completion.
> 
> **Classification Rules:**
> - `BOUND_CORRECTLY`: Harness resolved ID $\equiv$ Container ID $\equiv$ Journal ID $\equiv$ Verifier ID.
> - `MISMATCHED`: Harness targeted a different session ID than the container generated.
> - `UNRESOLVED`: Harness defaulted to `unknown` or empty string during execution.
> - `UNAVAILABLE`: Host filesystem permissions prevented harness from reading session artifacts.

---

## 4. Discrete Forensic Verdict Scorecard

The final post-soak audit must render explicit, independent verdicts across six dimensions. No dimension may be omitted or assumed:

| Audit Dimension | Permitted Verdicts | Criteria for PASS / ELIGIBLE | Current Audit Verdict |
| :--- | :--- | :--- | :--- |
| **1. Runtime Continuity** | `PASS` / `FAIL` / `UNRESOLVED` | Continuous duration $\ge 21,600$s; `RestartCount == 0`; `OOMKilled == false`; zero crashes. | `[PENDING RUN COMPLETION]` |
| **2. Feed Continuity** | `PASS` / `FAIL` / `UNRESOLVED` | Zero unrecovered disconnects; terminal feed state connected or cleanly completed; cadence verified. | `[PENDING RUN COMPLETION]` |
| **3. Evidence Integrity** | `PASS` / `FAIL` / `UNRESOLVED` | Journal, Manifest, Snapshot non-empty; chained SHA-256 hashes verify; non-root permissions. | `[PENDING RUN COMPLETION]` |
| **4. Harness Session Binding** | `PASS` / `FAIL` / `UNRESOLVED` | Harness resolved and tracked the exact active runtime session ID throughout execution. | `[PENDING RUN COMPLETION]` |
| **5. Canonical Eligibility** | `ELIGIBLE` / `NOT ELIGIBLE` / `REQUIRES HUMAN RATIFICATION` | Dimensions 1–4 are `PASS` and zero governance boundary violations observed. | `[REQUIRES HUMAN RATIFICATION]` |
| **6. Stage 11 (S11) Gate** | `CLOSED` / `OPEN` / `NOT DETERMINED` | Requires formal Human Governance ratification sign-off. Cannot be auto-closed. | `[OPEN — PENDING AUDIT]` |

---

## 5. Post-Forensic Action Decision Tree

```text
Did Runtime Continuity PASS?
  ├── NO  ──> FAIL: Discard run; investigate crash logs; schedule fresh G7 soak.
  └── YES
       │
       ▼
Did Evidence Integrity PASS (Chained SHA-256 valid)?
  ├── NO  ──> FAIL: Evidence corrupted; investigate filesystem / storage driver.
  └── YES
       │
       ▼
Was Harness Session Binding BOUND_CORRECTLY?
  ├── NO (MISMATCHED / UNRESOLVED due to host-readability defect):
  │     ├── Physical evidence is intact and continuous.
  │     ├── Harness monitoring was impaired by host permission boundary.
  │     └── Classification: SALVAGEABLE EVIDENCE / REQUIRES HUMAN RATIFICATION.
  │           (Human governance reviews physical journal to decide if run is ratified).
  └── YES
        │
        ▼
Did Feed Continuity PASS without unrecovered drops?
  ├── NO  ──> FAIL: Feed failure; investigate network gateway or exchange throttle.
  └── YES ──> ALL OPERATIONAL GATES SATISFIED ──> Submit to Human Governance for S11 Ratification.
```

---

### Verification Ledger
- Implementation Status: COMPLETE (Post-soak forensic checklist & runbook)
- Contract Enforcement: STRICT FAIL-CLOSED (Read-only inspection only; zero mutation; zero auto-closing of S11)
- Mathematical & SRE Authority: CANONICAL SPEC (Aligned with `execute_g7_soak.sh` and `verify_g7_evidence.sh`)
- Local Test Suite: NOT RUN (Documentation-only deliverable)
- Type Checker (MyPy): NOT RUN (Documentation-only deliverable)
- Remote CI Status: NOT APPLICABLE
- Methodological Caveats: Checklist must only be executed post-soak. Do not probe active runtime.
