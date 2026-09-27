# Operator Charter audit v1 — advisory design and use

## Authority and purpose

This is an implementation of a bounded **assessment**, not a new governance
authority, empirical admission gate, observation interlock, or capital mandate.
The user authorized additive documentation/tests/audit tooling on an isolated
branch. No authorization was given to change main, homelab, timers/services,
HYP_011 execution, prospective state, data acquisition, paper/live or capital.

- Canonical base: `d9608c0a2353bd5ed41943e5fb893ef9648089d2`.
- Normative source: [Operator Decision Charter v1 at its exact commit](https://github.com/Ratthabhumi/Acash/blob/e787cda941a1f6fc008ba06282dfee7321c60f3f/docs/governance/OPERATOR_DECISION_CHARTER_V1.md).
- Normative commit: `e787cda941a1f6fc008ba06282dfee7321c60f3f`.
- Normative Git blob: `45bd426d7079f1a34fdf441c6fc8b8d3f48970b3`.

The Charter remains on its own branch. It is not merged, copied into main, or
silently revised by this tool. Its section 1 gives precedence to stronger formal
controls; section 10 grants zero empirical authority. Git object IDs establish
which text was used, not scientific validity or human ratification.

## Manual, offline invocation

Use a **separate local clone**, with the two pinned commits already available:

```text
python -B tools/audit/operator_charter_audit.py --repo .
python -B -m unittest discover -s tools/audit/tests -v
```

Only Python's standard library and local Git are required. No ACASH module is
imported. No dependency is added to the application. No network, market provider,
broker, service, scheduler, workflow, registry or prospective engine is called.
The script writes JSON to stdout only. If saving a report, choose a location
outside runtime/state directories. Never deploy this tool to the active homelab
as part of this task.

The tool lives under `tools/audit/` because the existing Gate B software hash
in `src/acash/gate_b/manifest.py` includes `src/`, `tools/governance/`,
`pyproject.toml` and `uv.lock`. All four new files are outside that scope.
The hash definition and its inputs remain unchanged.

There is deliberately no installation, CI workflow, pre-commit hook, systemd
unit, scheduled job, required status check, runtime import or auto-remediation.
Do not connect its output or exit status to Observation #0001. Adding such a
connection would be a separate scope change requiring review and authorization.

## Evidence contract and checks

| Check | Primary evidence | Charter | Meaning and limits |
|---|---|---|---|
| `BASE_LINEAGE` | Local Git merge base | 1, 4, 10 | HEAD descends from the pinned base; no ref-name substitution. |
| `NORMATIVE_SOURCE` | Pinned commit tree and exact Charter blob | 1, 8, 10 | Uses immutable Charter identity; a changed worktree copy is not normative. |
| `COMMITTED_SCOPE` | All base and HEAD tree entries, including modes and object IDs | 4, 5, 10 | Every pre-existing tracked file must remain identical. Only the four explicitly listed audit files may be added. A new workflow is also out of scope. |
| `WORKTREE_SCOPE` | Staged, unstaged and nonignored untracked path differences | 4, 5, 10 | Detects pending runtime edits, including staged changes reversed only in the worktree. Audit-only pending files are disclosed. |
| `INDEX_VISIBILITY` | Index assume-unchanged/skip-worktree flags | 3, 4.7 | Hidden tracked changes cannot be treated as a verified worktree. |
| `LOCAL_PIN:*` | Local main and origin/main refs | 4, 10 | Cached/local pin only; never represented as a fresh GitHub observation. |
| `AUTHORITY:*` | HEAD activation binding and reconciliation manifests | 4.8, 4.9, 10 | Exact field types/values: paper=false, live=false, capital="0.00", no_real_orders=true. Missing/ambiguous records stay unknown. |
| `SIMULATED_ACCOUNTING` | Reconciliation's starting AUM | 4.9, 5.G, 10 | The sealed "100000.00" is simulated accounting, never capital authority. |
| `SNAPSHOT_STABILITY` | Before/after local Git snapshots | 3, 4.7 | Detects observed concurrent checkout changes. This is not an atomic snapshot of external systems. |

The two authority records are
`docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_BINDING.json` and
`docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_RECONCILIATION.json`.
They are sealed repository records, not evidence of today's completed session
count. Their `prospective_session_count=0` must not be reported as live state.

The additive allowlist is exactly:

1. `tools/audit/operator_charter_audit.py`
2. `tools/audit/tests/test_operator_charter_audit.py`
3. `docs/governance/OPERATOR_CHARTER_AUDIT_V1.md`
4. `docs/governance/OPERATOR_CHARTER_AUDIT_IMPLEMENTATION_RECORD.md`

This is a scoped v1 assessment of this change, not a reusable broad permission
to edit anything under docs or tools. Expansion of the allowlist is a deliberate
reviewed revision. JSON formatting here is a report transport, not a competing
ACASH canonical serializer, manifest seal or empirical hash authority.

## Fail-closed assessment, advisory runtime behavior

- `VERIFIED`: only the named, narrowly evidenced repository check is established.
- `UNKNOWN`: unavailable, ambiguous or uninspected evidence; never a permission.
- `BLOCKED`: the **assessment** found a concrete conflict with the scoped contract.
  It does not stop, block or modify an observation process.
- `NOT_AUTHORIZED`: this audit grants no empirical, paper, live or capital action.

Overall assessment is `BLOCKED` when any concrete blocker exists; otherwise it is
`UNKNOWN`. It cannot issue an overall PASS because contextual/human/host checks
remain unresolved. Findings include Charter sections, evidence references and
details. Exit 0 means a report was produced (even with BLOCKED findings); exit 2
means required collection failed or CLI usage was invalid. Neither status is an
observation gate or authorization signal. Read the JSON assessment, not exit 0,
when interpreting governance findings.

Strict JSON parsing rejects duplicate keys, malformed objects and NaN/Infinity.
Booleans cannot be replaced by integers or strings; simulated money cannot fill
the capital field. Missing commits/ref/manifest evidence never defaults to green.
The collection uses read-only Git commands with optional locks, replacement
objects, lazy fetching and fsmonitor disabled; caller GIT_* redirection is cleared.
Global/system Git configuration is excluded for reproducibility. Repository ignore
rules still apply; global ignore rules do not hide unexpected additions. Git stderr
diagnostics make collection unverified instead of being silently suppressed.

## Required human/context review — always explicit UNKNOWN here

| Review | Evidence needed before making the relevant decision |
|---|---|
| FOMO/status/sunk cost/urgency; opposite-result counterfactual | The actual decision, rationale, alternatives and evidence. Do not diagnose motives from keyword scans. |
| Evidence before scale; intake and trial history | Scoped primary research records, complete trial count K, costs/execution assumptions and appropriate outside feedback. Software tests do not prove scientific validity. |
| Sealed rules and post-outcome changes | Applicable human decisions, timing of outcome access, and explicit supersession. Do not select new thresholds or rescue a failed hypothesis. |
| Downside, reversibility, scope and privacy | The proposed action and its real consequences, bounded objective, appropriate reviewer and sanitized evidence. |
| GitHub and deployed Observation #0001 | Separately collected fresh remote refs/protection evidence and separately authorized read-only host evidence. This tool obtains neither. |

Do not load private financial balances or personal biographies into reports.
Report conflicts and propose a reversible scoped alternative; do not infer
authorization from a human-review checkbox or a profitable result.

The earlier conversational S2 concern is **not adjudicated here**. The pinned
base inspected for this implementation did not supply a verified S2 decision
record for that claim. No contiguous-session semantics, thresholds or gates are
changed. Any S2 review needs its actual source and separate additive governance.
Likewise, branch protection is neither enabled nor declared unnecessary here.

## Limitations and validation boundary

Run the reviewed tool from a trusted isolated clone. This is not a sandbox for
hostile Git configuration, a proof of its own future source integrity, a secret
scanner, or a replacement for independent code review. Tree comparison establishes
final content identity, not that every intermediate historical decision was valid.
Ignored files, external services, submodule contents, runtime state, environment
and concurrent edits outside the observed snapshots are not certified. Missing
host evidence prevents claiming a healthy/successful Observation #0001 run.

Adversarial tests use temporary synthetic repositories, not production objects or
runtime. They cover tracked/staged/untracked drift, deletion/rename, unexpected
CI coupling, authority confusion, malformed evidence, pin mismatch, hidden index
flags, caller Git redirection, concurrent changes, exit behavior and byte-for-byte
non-mutation of fixture repository/index/ignored prospective state.

## Verification Ledger

- Implementation Status: COMPLETE (manual advisory tool and tests).
- Contract Enforcement: STRICT FAIL-CLOSED assessment; runtime effect NONE.
- Mathematical Authority: N/A; no scientific or empirical claim.
- Local Test Suite / MyPy / Remote CI: see the implementation record for executed results.
- Methodological Caveats: repository evidence only; human, remote and host facts remain UNKNOWN.
