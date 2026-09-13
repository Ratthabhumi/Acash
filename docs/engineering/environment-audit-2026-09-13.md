# MEW / ACASH engineering environment audit — 2026-09-13

The bootstrap findings below preserve the initial audit snapshot. The authorized
follow-up at the end records the subsequent fixes and supersedes the baseline
test/typecheck status; it does not amend governance or historical phase records.

## Scope and evidence basis

**AUTHORIZATION:** The bootstrap request authorizes capability/repository discovery
followed by repository instructions and useful skills. It does not authorize
commit, push, PR creation, deployment, feed resume, empirical research, hypothesis
creation, trading, capital changes or alteration of historical governance.

**FACT:** The capability and repository audit completed before the first repository
edit. Starting checkout: `main` at `b3e950e`, tracking `origin/main`, ahead by one
local commit; tracked and untracked working tree clean. This comparison uses the
local tracking ref; no fetch or remote-parity claim was made. The preceding commit
is `b057d12`; the leading commit adds feed diagnostics/recovery observability.

**EVIDENCE:** Executed Git status/branch/log/diff checks, raw repository files
linked below, installed skill definitions, a narrowly filtered local Codex config,
CLI version checks, tool inventory and the official manual fetched on this date.
No credential values were copied into this report. No standalone MEW master
handoff was supplied or found by the targeted handoff inventory; the supplied
working profile and existing repository handoffs were used with that limitation.

## Phase 0 capability inventory

| Capability | Status / evidence | How it helps | Limitations |
|---|---|---|---|
| Model | Session identifies Codex based on GPT-6; local configured default is `gpt-6-astra`, reasoning `high` | Coding, analysis, tool orchestration | A config default does not prove the exact backend snapshot or effective setting for every task; no intelligence upgrade was performed. |
| Reasoning/coding | Read/write tools, patching, search, terminal, web, artifact tools, browser control and bounded agent collaboration are exposed | Evidence-led implementation and verification | Capability is not a correctness guarantee. No subagents or extra model runs used for this bootstrap. |
| Repository tools | Git 2.50.0.windows.1, `rg`, file reads and patching executed | Inspect state and make reviewable changes | Sandbox controls sensitive paths, `.git`, `.agents` and `.codex`; no blind overwrite or remote mutation. |
| Shell/runtime | Windows PowerShell; Python 3.14.3, uv 0.11.2, Node 24.14.1 verified | Python/TypeScript checks and local automation | Network and writes outside allowed roots require the applicable tool approval. WSL/Linux host operation was not exercised. |
| GitHub | `gh` 2.89.0; successful read-only auth check outside sandbox; repository remote configured | Authorized repository and CI inspection through CLI | Initial sandbox auth result was invalid; successful keyring check outside sandbox superseded that diagnosis. No GitHub connector exposed, no remote writes or CI-run query performed. |
| Skills | Installed `skill-creator` and `openai-docs` files read; supplied catalog includes Azure, artifacts and other workflows. Final local `skills/list` discovers all 8 new skills as enabled, repo scope. | Focused repository procedures with progressive loading | Repo `.agents/skills/` is the documented discovery mechanism. Personal/system skills also exist. Registry discovery is distinct from this running task's UI refresh or behavioral evaluation. |
| Instructions | Root [AGENTS.md](../../AGENTS.md) exists; no nested tracked AGENTS/override or repo skills/config found in initial inventory | Durable conventions and authority boundaries | Global Codex AGENTS file exists but is empty. Root guidance cannot replace runtime enforcement. |
| Project configuration | [pyproject.toml](../../pyproject.toml), [uv.lock](../../uv.lock), [configs](../../configs), [Dockerfile](../../docker/Dockerfile), [dashboard/package.json](../../dashboard/package.json), [Vite config](../../dashboard/vite.config.ts) | Actual stack, dependencies and verification commands | No repository `.codex/config.toml` or tracked GitHub Actions workflow found. No compose deployment configuration found in this checkout. |
| Existing agent configuration | Ignored `.kilo/`, `.omc/`, `.vscode/`; [Antigravity guidance](../../ANTIGRAVITY_GEMINI_3.7_FLASH.md); global Codex defaults/features/plugins/MCP entries inspected narrowly | Locate previous context and detect stale assumptions | Other tools' files are not automatically Codex instruction mechanisms. `.omc/project-memory.json` contains stale counts and `ruff check`, which is not established in pyproject. Left untouched. |
| Persistent context | Repository files, scoped skills, app task history tools and local memory storage exist | Reproducible handoff and continuity | Memory presence is not proof of its current contents/activation or a governance authority. No global memory/database rewrite, hook or automation added. |
| MCP/connectors | App task/file/automation tools, Node REPL, document-session tools, Sites, plugin management, browser control, web and image/artifact capabilities exposed | Existing tools cover local work and selected external/artifact tasks | Installed/catalogued/callable/authenticated are separate states. Available artifact-session or Sites tools do not prove an account/document session is connected. Recommended plugins are not installed capabilities. |
| Tests/typecheck/build | pytest and strict MyPy configured; dashboard test/typecheck/build scripts; Hatchling package build config | Existing verification without inventing new tooling | No root lint command/dependency configured. Docker CLI 29.4.3 exists; daemon, images and homelab state unverified. |

The [official skill documentation](https://learn.chatgpt.com/docs/build-skills)
documents repository `.agents/skills` discovery and progressive loading.
[AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
documents layered instruction discovery. These mechanisms were checked in the
fresh official Codex manual, not inferred from another agent's conventions.

## Repository and authority findings

| Classification | Finding and evidence | Risk / disposition |
|---|---|---|
| FACT — record verified | [O1-O7](../../E3.6-HUMAN-DECISIONS.md) approves Option A for implementation scope; O1 requires operator-only resume and no auto recovery. `src/acash/paper/session.py` records recovery attempts and halts on feed connection failure. | Skills route to the decision and supervisor, not an assumed retry policy. No operational resume performed. |
| FACT — record verified | [RATIF-E36-G7-SOAK-20260912](../../E3.6-HUMAN-RATIFICATION-G7-SOAK.md) explicitly amends 72h to 6 continuous hours and retains integrity, restart, memory, observability and security criteria. | G7 audit != G7 PASS. Actual host/run artifacts were not examined; no soak acceptance claim. |
| FACT — record verified | [MEC-0013 intake section 14](../phase14/mec_0013_orb_research_intake.md) records MEC-0013-D01 Option C ratified, ARCHIVED, NOT PROMOTED and no empirical/paper authority. | Preserve archival state; no candidate or hypothesis creation. |
| FACT — bounded | [D17 gap register lines 115-118](../phase14/macro_001_data_authority_gap_register.md) reports D17/D18 OPEN / GROUP C, D17-E ratified, D18 dependency-blocked, HYP_003 absent and empirical/backtest unauthorized. [E3.6 decisions](../../E3.6-HUMAN-DECISIONS.md) preserves D17-E HOLD. | This verifies recorded restrictive standing, not independent human-signature authentication. The register explicitly disclaims ratification authority; do not claim all Group C bindings are complete from the supplied phrase "Group C human-ratified". |
| FACT — context conflict | [Research handoff](../SESSION_HANDOFF.md) contains both a pending human decision block and later D17-E-ratified continuation text. [E3.6 handoff](../../E3.6-SESSION-HANDOFF.md) refers to an older commit/checkpoint and deployment state. | Handoffs are navigation aids. Do not silently edit them or treat historical snapshots as current runtime truth. |
| FACT — recorded lock | The G7 ratification and E3.6 decisions preserve HYP_003 NOT CREATED, R1 NOT STARTED, backtest LOCKED, paper NOT AUTHORIZED, live LOCKED, canonical $0 and no real orders. [Readiness planes](../../src/acash/core/readiness_planes.py) separates authority dimensions. | This task did not audit every historical hypothesis artifact or runtime process. HYP_001/002 files and all research/execution code remain unchanged. |
| FACT — implementation inspected | Dashboard package is React/Vite/TypeScript/Tailwind/Lucide. Vite explicitly uses port 3002 and strictPort. [Mock data](../../dashboard/src/services/mockData.ts) and [contract tests](../../dashboard/test/contract.test.mjs) distinguish demo data, synthetic strategy and authorization. | Demonstration metrics are not research evidence. No UI or Grafana modification; actual Grafana runtime/port binding not inspected. |
| INFERENCE | Persistent, source-linked workflows reduce repeated rediscovery and stale-context risk. | Benefit is a design rationale, not a measured improvement in model intelligence or guaranteed behavior. |

MEW's broader stack interests (FastAPI, SQLAlchemy, PostgreSQL/pgvector, Next.js,
Ubuntu/WSL2, networking, security and homelab) are preferences supplied in the
request. They are not all ACASH dependencies and were not installed or introduced.

## Implemented design and exact intended files

Eight ACASH-specific skills cover the ten requested domains. Repository audit
includes Git change control; surgical debugging includes root-cause analysis.
Their descriptions have narrow triggers and default implicit discovery is
preserved. Each is instruction-only; no extra scripts, dependencies, plugins,
model settings, hooks or recurring jobs are needed for these workflows.

1. `AGENTS.md` — append session start, authority, change control and workflow routing; preserve all existing mathematical and verification rules.
2. `docs/engineering/agent-workflow.md` — maintained source map, skill routing, verification and continuity procedure.
3. `docs/engineering/environment-audit-2026-09-13.md` — this dated, non-authoritative audit and verification record.
4. `.agents/skills/acash-governance/SKILL.md`
5. `.agents/skills/acash-repository-audit/SKILL.md`
6. `.agents/skills/acash-evidence-lineage/SKILL.md`
7. `.agents/skills/acash-paper-flight-recorder/SKILL.md`
8. `.agents/skills/acash-feed-resilience/SKILL.md`
9. `.agents/skills/acash-g7-s11-validation/SKILL.md`
10. `.agents/skills/acash-surgical-debugging/SKILL.md`
11. `.agents/skills/acash-security-fail-closed/SKILL.md`

Do not add generic "be smart", motivational, broad coding, or redundant Git skills;
do not duplicate existing Azure/artifact skills or add plugins without a concrete
missing capability. No invented `.codex/skills` repository discovery convention
or copied master prompt is introduced.

Temporary preparation files and raw check logs live in ignored `scratch/`.
They are not proposed commit contents or sealed ACASH research evidence.

## Skill quality review

The following is a manual adversarial review of the instructions, not an executed
independent agent evaluation or a guarantee of future skill behavior.

| Scenario | Procedure found in the created instructions | Review result |
|---|---|---|
| "Make HYP_003 and run it" | Governance skill requires the scoped inception/data/empirical authority and prepares a decision surface before a blocked mutation. | Boundary explicitly covered. |
| Profitable backtest | Governance/evidence skills separate metrics, qualification and paper/live authority. | No automatic promotion. |
| Feed disconnect | Feed skill routes to O1, preserves halt and requires explicit operator resume. | No automatic reconnect. |
| Failing test | Surgical skill reproduces the cause and prohibits weakening acceptance criteria. | Root-cause requirement covered. |
| Profitable mock dashboard | Evidence skill keeps MOCK-RESEARCH-001 in the demo evidence class. | No research admission. |
| Uncommitted governance file | Repository skill preserves work and resolves overlapping intent first. | No overwrite/stash/reset shortcut. |
| Large refactor when one-file fix works | Surgical skill compares the narrow option while respecting an explicitly requested broader scope. | Minimality without overriding user intent. |
| Credentials in logs | Security/feed skills redact derived output, contain disclosure, preserve evidence and distinguish rotation/history changes from authorized scope. | No secret reproduction or silent evidence rewrite. |

## Verification results

| Check | Executed result | Interpretation |
|---|---|---|
| Skill structural validator | All 8 pass the installed `skill-creator/scripts/quick_validate.py`. Prepared and installed bytes match by SHA-256. | Frontmatter, naming and scaffold checks; not a behavioral guarantee. |
| Actual Codex discovery | Codex Desktop/CLI 0.153.4 app-server, `skills/list` with this repository cwd and `forceReload=true`: all 8 names, `scope=repo`, `enabled=true`, correct local paths, no discovery errors. | Verified actual discovery, not merely folder creation. Probe used initialize/list only, no task/turn creation or model inference; the process was terminated after the check. |
| Targeted Python selection | Golden numerical/math references, `tests/unit/paper`, and the mocked real-feed integration selection: 186 tests; all 186 also individually verified PASSED in the full-suite log. | Covers the code cited by the skills; mathematical literature was not independently re-audited. |
| Full repository suite | `uv run pytest`: **2231 passed, 1 failed, 1 skipped, 4 warnings**, exit 1, 189.65s. | Full suite is not green. The unchanged launcher test fails; see below. |
| MyPy | `uv run mypy src/ tests/`: **27 errors in 3 files**, 411 source files checked, exit 1. Same diagnostics captured with the existing venv's `python -m mypy src/ tests/`. | Baseline type errors remain; no type suppressions or source/test changes introduced. |
| Dashboard | `npm.cmd test`: **5 passed**; `npm.cmd run typecheck`: clean; `npm.cmd run build`: successful after sandbox escalation, 1587 modules transformed. | Existing dashboard scripts exercised. No dashboard source or configuration change. |
| Scope/portability | Original AGENTS content preserved, 44 lines appended; eight new skill files plus two new documents. Local references, prepared/final bytes and intended-file scope checked; `git diff --check` passes; no staged changes. | 11 intended files. Source, tests, configs, dependencies and historical decision/phase records unchanged. |

**Unresolved baseline test failure:**
`tests/unit/execution/test_paper_launcher.py:109`,
`test_powershell_launcher_help_and_missing_vault`. The raw traceback shows
`UnicodeDecodeError` in the subprocess stdout reader using `cp1252` (byte `0x9d`),
then `TypeError` because `res_help.stdout` is `None`. Source uses
`subprocess.run(..., capture_output=True, text=True)` without explicit encoding.
This establishes the observed decode-failure path; it does not establish the
correct producer encoding or justify a speculative patch. The script's
`-ShowHelp` branch exits before credential loading. No fix is included in this
instructions-only scope.

**Unresolved baseline MyPy errors:**

- `tests/unit/paper/test_paper_e3_flight_recorder.py:633` and `:634`: 12 argument
  errors from forwarding `dict[str, object]` into the typed manifest seal method.
- `tests/unit/paper/test_paper_e36_window.py:573`, `:575`, `:577`: missing return
  annotation and two `object` argument-type mismatches (3 errors).
- `tests/unit/paper/test_paper_ws10_backup_restore.py:57` and fixture/test
  signatures through line 308: missing annotations (12 errors).

**Warning and environment classification:**

- Two `Pandas4Warning` occurrences during Nautilus `engine.run()` about deprecated
  `Timestamp.utcnow`: dependency compatibility debt; no suppression added.
- One Pydantic serialization warning for `margin_mode='INVALID_MODE'`: expected
  adversarial-test behavior. Source deliberately bypasses validation to inject
  that malformed value before checking fail-closed reconciliation.
- One `PytestUnhandledThreadExceptionWarning`: actionable launcher-test encoding
  defect described above, not harmless noise.
- One skipped B23.2 host application-control test: unverified environment-specific
  coverage. The test skips when the DeviceGuard query is unavailable or UMCI is
  not enforced; this log does not establish which skip branch applied. No claim
  that host application control is verified.
- MyPy note for unused `nautilus_trader.*` override: configuration/dependency
  maintenance debt; left unchanged.
- Git global-ignore access warning and initial `gh auth status` failure in the
  sandbox: environment limitation. Outside-sandbox read-only checks confirmed a
  clean starting checkout and valid GitHub keyring authentication.
- uv default-cache initialization and initial dashboard esbuild parent-directory
  access failures: sandbox/tool environment limitations; approved retries used.
  No permission policy or project tooling was weakened.
- Git LF-to-CRLF warning for the edited AGENTS file: expected configured Windows
  line-ending conversion; original text preserved, whitespace checks pass.
- Codex discovery emitted a warning that the remote featured-plugin cache could
  not warm: external discovery-cache limitation, separate from the successful
  local skill listing. No plugin installed or removed; no account connection
  inferred from it. Docker version probing also could not read the Docker config
  inside the sandbox; only CLI presence/version is verified, not daemon access.

Raw local evidence: `scratch/agent-bootstrap-pytest.log`,
`scratch/agent-bootstrap-mypy.log`, `scratch/agent-bootstrap-discovery.json` and
`scratch/agent-bootstrap-discovery.stderr.log`. These are local audit aids, not
portable committed test evidence or canonical ACASH manifests.

## Recommended workflow and remaining boundaries

Open the ACASH project and request `audit G7`, `ตรวจ feed resilience`, a repository
audit or a bounded defect fix. Root instructions route to the focused skill/source
map. Explicit `$acash-g7-s11-validation` or `$acash-feed-resilience` can select a
skill when needed. If the app's skill list has not refreshed, restart/reopen the
task environment as documented; do not assume a running task reloaded root AGENTS.

For governed mutations, first produce the exact proposed change/evidence and
identify the missing authority; apply only an established scope-specific approval.
Keep independent infrastructure/research/paper/live boundaries visible in reports.
Actual homelab deployment, fresh remote CI, current G7 run acceptance and empirical
research validity remain outside this bootstrap's verified scope.

**PROPOSAL:** Commit message, only if later explicitly authorized:
`chore(agents): add ACASH governance-aware repository workflows and skills`

**AUTHORIZATION STATUS:** No commit, push, PR, research transition, deployment,
feed resume, broker operation or capital change performed by this bootstrap.

### Bootstrap Verification Ledger (before follow-up)

- Implementation Status: COMPLETE (repository instructions, 8 skills and audit delivered; baseline check failures remain explicitly open).
- Contract Enforcement: STRICT FAIL-CLOSED instructions preserved; no runtime contract changed.
- Mathematical Authority: N/A — engineering workflow specification; no mathematical formulation changed or newly certified.
- Local Test Suite: EXECUTED, NOT GREEN — 2231 passed, 1 failed, 1 skipped; targeted selection 186 passed; dashboard 5 passed.
- Type Checker (MyPy): executed; 27 baseline errors in 3 files, 411 source files checked; not clean.
- Remote CI Status: NOT AVAILABLE — no matching remote run inspected.
- Methodological Caveats: Static instruction review and local checks do not prove model behavior, soak acceptance, statistical validity or future profitability.

## Authorized verification repairs — 2026-09-13

The user subsequently authorized inspection and repair of the outstanding
verification issues. Four test files changed; the earlier bootstrap work remains
intact. No production source, launcher script, configuration, dependency,
governance decision or acceptance threshold changed.

- `tests/unit/execution/test_paper_launcher.py`: inspect captured help output as
  bytes for the existing ASCII contract markers, avoiding locale-dependent
  decoding of unrelated localized text. Preserve the successful exit assertion
  and bound subprocess duration. Add a separate missing-vault regression using
  an isolated empty profile; assert exit 1 and the missing-credential diagnostic.
  No real vault, credential or broker access is required.
- `tests/unit/paper/test_paper_e36_window.py`: represent mutable metrics state as
  typed closure variables and annotate the collector as `MetricsRegistry`; retain
  both HTTP assertions before and after changing the state.
- `tests/unit/paper/test_paper_e3_flight_recorder.py`: use a typed local fixture
  factory calling the existing canonical seal method with explicit arguments;
  retain the two independent seal calls and deterministic-hash assertion.
- `tests/unit/paper/test_paper_ws10_backup_restore.py`: annotate the backup tuple
  fixture and its consumers using the actual `Path, Path, AcashBackupManifest`
  contract. No `Any`, casts, ignores, suppressions or weakened assertions added.

Executed verification:

- Targeted launcher, paper and both golden-reference suites: **186 passed**.
- `uv run pytest -ra`: **2233 passed, 1 skipped, 3 warnings**, exit 0, 91.41s.
- `uv run mypy src/ tests/`: **411 source files clean**, exit 0.
- Reviewed all four test diffs and ran `git diff --check`: passed.

The skip now has an observed reason: UMCI status is `0` (Off), so B23.2 host
application-control enforcement remains unverified on this development host.
Do not enable host policy or claim enforcement merely to remove the skip.
Remaining warnings are the two Nautilus/Pandas deprecations (dependency
compatibility debt) and the deliberately malformed MT5 enum serialization warning
(expected adversarial-test behavior). MyPy's unused `nautilus_trader.*` override
note remains configuration maintenance debt. No warnings were suppressed.

Raw local logs: `scratch/engineering-fix-targeted.log`,
`scratch/engineering-fix-full.log`, `scratch/engineering-fix-mypy.log`.
Proposed repair commit message, only if explicitly authorized:
`test: fix Windows launcher capture and type paper fixtures`.
No commit, push, PR, deployment or trading transition performed.

### Verification Ledger

- Implementation Status: COMPLETE — bootstrap and authorized verification repairs.
- Contract Enforcement: STRICT FAIL-CLOSED preserved; missing-vault regression added.
- Mathematical Authority: N/A — no formula changed; existing golden references executed.
- Local Test Suite: VERIFIED — 2233 passed, 1 skipped; 186 targeted passed.
- Type Checker (MyPy): VERIFIED — 411 source files clean.
- Remote CI Status: NOT AVAILABLE — no remote run inspected or new commit published.
- Methodological Caveats: B23.2 requires an enforcement host; remaining warnings classified above. Local tests do not establish G7 acceptance, empirical qualification or trading authority.
