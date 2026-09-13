# ACASH agent workflow and source map

This is a navigation and working-procedure document. It grants no research,
deployment, data acquisition, paper, live, or capital authority. Paths in commands
are relative to the repository root. Read only the records relevant to the task.

## Start from evidence

1. Read [AGENTS.md](../../AGENTS.md), applicable nested instructions, current user
   scope, and Git state, including staged and unstaged changes.
2. Classify the work: AUDIT (read-only), PLAN (prepare a bounded change), IMPLEMENT
   (authorized scope), VERIFY (executed checks), REPORT (evidence and limitations).
   These are working conventions, not invented Codex configuration modes.
3. Follow the source map below to inspect raw records, code, tests, and config.
   Determine decision ID, authority, scope, date, and explicit supersession.
   A newer summary does not silently override a ratified decision.
4. For a governed transition, distinguish permission to prepare code/evidence
   from permission to execute the transition. Honor established authorization;
   ask only for a missing, specific decision immediately before dependent action.
5. Keep historical records intact. Record unresolved contradictions with both
   references; do not choose the permissive interpretation or fabricate a seal.

## Source map

| Topic | Primary records and implementation | Verification entry points |
|---|---|---|
| D17/D18, MACRO-001 | [Binding worksheet](../phase14/cand_free_macro_001_human_binding_worksheet.md), [decision surface](../phase14/cand_free_macro_001_human_specification_decision_surface.md), [data authority gap register](../phase14/macro_001_data_authority_gap_register.md), [D18 specification](../phase14/macro_001_d18_manifest_specification.md). A gap register/surface reports or proposes; it is not itself a new ratification. | Inspect the binding records and the exact source/manifest artifacts; source availability is not source authority. |
| MEC-0013 | [Intake, section 14 archival closure](../phase14/mec_0013_orb_research_intake.md), [audit](../phase14/mec_0013_orb_research_audit.md), [readiness checklist](../phase14/mec_0013_orb_readiness_checklist.md) | Verify MEC-0013-D01, scope, candidate standing and any explicit supersession. |
| Research lineage | [Research doctrine](../phase14/research_doctrine.md), [research registry](../phase14/free_data_research_registry.md), [readiness planes](../../src/acash/core/readiness_planes.py), [canonical serialization](../../src/acash/core/serialization.py) | [Golden math references](../../tests/unit/research/test_golden_math_reference.py), [golden numerical references](../../tests/unit/validation/test_golden_numerical_reference.py), [serialization tests](../../tests/unit/test_serialization.py). Follow quantity-specific callers before proposing helpers. |
| Feed and recovery | [O1 human decision](../../E3.6-HUMAN-DECISIONS.md), [feed adapter](../../src/acash/paper/feed.py), [session supervisor](../../src/acash/paper/session.py), [health events](../../src/acash/paper/health.py) | [Feed observability tests](../../tests/unit/paper/test_feed_observability.py), [feed tests](../../tests/unit/paper/test_paper_e35_real_alpha_feed.py), [mocked integration tests](../../tests/integration/test_phase14_e35_real_feed_integration.py) |
| Flight recorder | [Session manifest](../../src/acash/paper/manifest.py), [journal](../../src/acash/paper/journal.py), [runner](../../src/acash/paper/runner.py), [replay](../../src/acash/paper/replay.py), [reconciliation](../../src/acash/paper/reconcile.py), [window](../../src/acash/paper/window.py) | [Recorder tests](../../tests/unit/paper/test_paper_e3_flight_recorder.py), [window tests](../../tests/unit/paper/test_paper_e36_window.py), [backup/restore tests](../../tests/unit/paper/test_paper_ws10_backup_restore.py) |
| G7/S11 | [RATIF-E36-G7-SOAK-20260912](../../E3.6-HUMAN-RATIFICATION-G7-SOAK.md), [O1-O7 decisions](../../E3.6-HUMAN-DECISIONS.md), [historical design](../../E3.6-DESIGN.md) | Actual session/window evidence plus host/container/telemetry records. Unit tests alone cannot establish a soak PASS. |
| Deployment/security | [Dockerfile](../../docker/Dockerfile), [window/interlock](../../src/acash/paper/window.py), [readiness planes](../../src/acash/core/readiness_planes.py), [configuration](../../configs/base.yaml) | [Gate B readiness tests](../../tests/unit/gate_b/test_gate_b_readiness.py) and window tests. HomeLab configuration/runtime must be obtained separately for deployment claims. |
| Dashboard | [Dashboard boundary guide](../research-dashboard/README.md), [package manifest](../../dashboard/package.json), [Vite configuration](../../dashboard/vite.config.ts), [mock data](../../dashboard/src/services/mockData.ts) | [Dashboard contract tests](../../dashboard/test/contract.test.mjs). Dashboard port 3002; preserve the separate Grafana service at 3000 unless explicitly scoped otherwise. |

The [research handoff](../SESSION_HANDOFF.md) and
[E3.6 handoff](../../E3.6-SESSION-HANDOFF.md) help locate records. Verify their
checkpoint claims against the current checkout and scoped decisions. Do not run
their suggested continuation commands automatically.

## Select a focused skill

| Request | Skill |
|---|---|
| Audit governance, HYP/R1/data authority, authorization or gate changes | [acash-governance](../../.agents/skills/acash-governance/SKILL.md) |
| Establish checkout state, inspect a diff, prepare change control | [acash-repository-audit](../../.agents/skills/acash-repository-audit/SKILL.md) |
| Trace a research claim, return series, trial count or manifest provenance | [acash-evidence-lineage](../../.agents/skills/acash-evidence-lineage/SKILL.md) |
| Audit a recorded simulated session, journal, replay or manifest | [acash-paper-flight-recorder](../../.agents/skills/acash-paper-flight-recorder/SKILL.md) |
| Diagnose a feed failure, timeout, recovery or missing bars | [acash-feed-resilience](../../.agents/skills/acash-feed-resilience/SKILL.md) |
| `audit G7`, assess S11 soak evidence | [acash-g7-s11-validation](../../.agents/skills/acash-g7-s11-validation/SKILL.md) |
| Reproduce a defect and implement a bounded regression fix | [acash-surgical-debugging](../../.agents/skills/acash-surgical-debugging/SKILL.md) |
| Audit credential handling, fail-closed execution or deployment exposure | [acash-security-fail-closed](../../.agents/skills/acash-security-fail-closed/SKILL.md) |

## Verification and continuity

Use the existing root verification requirements without weakening them. Start
with targeted checks relevant to the touched contract, then run `uv run pytest`
and `uv run mypy src/ tests/` for quantitative, architectural, or audit findings.
Existing golden references are implementation checks; they do not prove the
literature was independently revalidated. For dashboard changes, run `npm test`,
`npm run typecheck`, and `npm run build` from `dashboard/` (Windows can use
`npm.cmd`). No repository-wide lint command is established by `pyproject.toml`;
do not adopt a stale agent-memory command as a requirement.

Use fixture/mocked tests for local verification. Do not turn a test request into
market-data ingestion, an operational soak, broker activity, or a governed
empirical run. Inspect scripts before executing unfamiliar verification commands.
If a check cannot run, preserve its exact command, failure class, exit status and
limitation; a dependency/sandbox failure is not evidence that product code passed.
Classify warnings explicitly. Keep raw local logs outside tracked evidence unless
their publication is requested and safe.

Before finishing, inspect every new file as well as `git diff`, staged changes,
`git diff --check`, and final status. Include intended files, verification and a
proposed commit message; only commit/push/PR when explicitly authorized.

For continuity, retain task scope, baseline commit, exact modified paths, executed
checks, unresolved issues and required authority in the task report. Do not
rewrite a historical handoff to make it current or use personal memory as a
governance database. This repo records MEW's preference for direct answers,
minimal changes, root-cause evidence, reproducibility and secure operations;
personal interest in a framework is not evidence that ACASH uses it.
