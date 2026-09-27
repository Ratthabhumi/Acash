# ACASH GitHub Protection & Repository Ruleset Design

**Document:** `docs/governance/preobs_audit_20260928/GITHUB_PROTECTION_DESIGN.md`  
**Evaluation Scope:** Pre-Observation Governance Audit & Post-Observation Hardening Plan  
**Target Repository:** `Ratthabhumi/Acash`  
**Current Main SHA Pin:** `d9608c0a2353bd5ed41943e5fb893ef9648089d2`  
**Audit Date:** 2026-09-28  
**Governance Authority:** `docs/governance/OPERATOR_DECISION_CHARTER_V1.md` (e787cda) — Principles 5, 8, 10

---

## 1. Executive Summary

This architecture design evaluates current GitHub repository protection for `Ratthabhumi/Acash` and establishes a minimal, staged protection rollout.

### Current Technical State (Verified Empirical Facts):
1. **GitHub Workflows:** `.github/workflows/` does **not** exist on canonical `main` (`d9608c0a...`). No GitHub Actions runners are currently configured.
2. **Branch Protection / Rulesets:** Neither classic branch protection rules nor modern GitHub Repository Rulesets are currently active on `main`.
3. **Enforcement State:** Direct pushes, force pushes, and branch deletions are technically unblocked at the remote repository layer (governed solely by operator discipline and local pre-commit checks).
4. **Required Status Checks:** Zero status checks currently exist on `main`.

### Architectural Mandate:
Enabling "Required Status Checks" in GitHub Rulesets when no workflow exists or before a workflow has completed a verified run will **lock all Pull Request merges permanently** ([GitHub Docs](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)). Furthermore, enabling every available ruleset feature (such as mandatory commit signing or strict linear history) introduces severe operational friction without threat model justification.

Therefore, protection rollout is divided into:
- **Phase A (Immediate Post-Observation):** Safe baseline protection (block force-push, block deletion, require PR before `main` mutation). Zero CI dependency.
- **Phase B (Subsequent CI Integration):** Implement minimal, deterministic CI workflows, verify successful execution on non-`main` branches, and then bind required status checks with exact check names.

---

## 2. Threat Model & Mechanism Evaluation

| Protection Feature | GitHub Mechanism | Threat Addressed | Operational Friction / Risk | Recommendation | Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Block Force Push** | `non_fast_forward: block` | Accidental history rewrite, dropping sealed manifests, clobbering commits. | **Low:** Legitimate workflow never requires force-pushing `main`. | **PHASE A (MANDATORY)** | Essential invariant to preserve audit trails and immutable lineage. |
| **Block Branch Deletion** | `deletion: block` | Accidental deletion of `main` via git CLI or web UI. | **Zero:** `main` must never be deleted. | **PHASE A (MANDATORY)** | Zero friction, prevents catastrophic repository loss. |
| **Require Pull Request** | `pull_request: required` | Direct accidental `git push origin main` bypassing review and testing. | **Low:** Requires opening a PR and merging through UI or GitHub CLI. | **PHASE A (MANDATORY)** | Ensures every change to `main` has a recorded PR context and review record. |
| **Admin Bypass** | `bypass_actors: [Repository Admin]` | Deadlock if automated checks fail, emergency patch required during market anomaly. | **Low:** Explicit emergency escape hatch for repository owner. | **PHASE A (MANDATORY)** | As an operator-driven project, the human operator must retain sovereign emergency override authority. |
| **Required Status Checks** | `required_status_checks` | Merging broken tests or broken typechecks into `main`. | **CRITICAL (if premature):** If enabled before CI runs exist, merges are hard-blocked. | **PHASE B (STAGED)** | Must only be enabled AFTER `.github/workflows/ci.yml` is merged and proven green. |
| **Strict Up-to-Date Merge** | `strict_required_status_checks_policy` | Integration drift (PR tested against old base, breaks on merge). | **Medium:** Requires re-running CI whenever another PR merges. | **DEFER (Phase C)** | Low PR volume makes strict mode an unnecessary merge bottleneck. |
| **Signed Commits** | `required_signatures: true` | Impersonation of commit author by unauthorized contributor. | **HIGH:** Requires GPG/SSH key setup on every operator/agent machine; breaks automated tooling and local commits without keys. | **REJECT / DEFER** | ACASH is a private/single-operator repository. The threat is not committer impersonation, but unverified scientific code. |
| **Require Linear History** | `required_linear_history: true` | Merge commit clutter in git log. | **Medium:** Restricts merge styles to squash or rebase. | **OPTIONAL (Phase B)** | Beneficial for clean git log, but secondary to safety. |

---

## 3. Staged Implementation Plan

### 3.1 Phase A: Safe Baseline Ruleset (Post-Observation #0001)

Immediately following the completion and audit of Observation #0001, configure a GitHub Repository Ruleset targeting the default branch `main`.

#### Ruleset Specification:
- **Ruleset Name:** `baseline-main-protection`
- **Target Branch:** Default branch (`main`)
- **Enforcement Status:** Active
- **Rules Configured:**
  - `Restrict deletions`: Checked (Enabled)
  - `Block force pushes`: Checked (Enabled)
  - `Require a pull request before merging`:
    - Required approvals: `0` (for single-operator self-review) or `1` (if peer review configured).
    - Dismiss stale pull request approvals when new commits are pushed: Checked.
    - Require review from Code Owners: Disabled.
  - `Require status checks to pass`: **DISABLED (unchecked)** until Phase B.
- **Bypass List:**
  - Roles: `Repository admin` (Bypass mode: `Always` or `For emergency fixes only`).

*Implementation Note:* This configuration guarantees that `origin/main` cannot be overwritten or accidentally destroyed, while allowing normal PR merge operations without risking workflow deadlocks.

---

### 3.2 Phase B: CI-Backed Verification Gates

Before turning on Required Status Checks, create `.github/workflows/ci.yml` with deterministic, fast, zero-network verification jobs.

#### CI Workflow Design Principles:
1. **Zero External Network Dependencies:** No live exchange calls, no external API queries.
2. **Deterministic & Fast (< 3 minutes):** Fail fast on static analysis and unit regressions.
3. **Partitioned Checks:**
   - **Job 1: Static Governance & Types (`governance-typecheck`)**
     - Runs `uv run mypy src/ tests/ tools/`
     - Runs `git diff --check`
   - **Job 2: Unit & Golden Mathematical Suites (`unit-math-suite`)**
     - Runs `uv run pytest tests/unit/validation/ tests/unit/research/ tests/unit/risk/ -q`
   - **Job 3: Operator Charter & Lineage Audits (`operator-charter-audit`)**
     - Runs `python -m tools.audit.operator_charter_audit`
4. **Conditional Matrix for Heavy Tests:**
   - Dashboard tests (`dashboard/test/**`) only run when files under `dashboard/**` change.
   - Long integration or MT5 simulation tests are gated to manual dispatch or scheduled nightlies, never blocking standard PR merges.

#### Activation Sequence for Phase B:
1. Commit `.github/workflows/ci.yml` to a feature branch.
2. Open a test PR to observe that GitHub Actions triggers and completes with green status.
3. Note the exact job names emitted by GitHub:
   - `governance-typecheck`
   - `unit-math-suite`
   - `operator-charter-audit`
4. In GitHub Repository Ruleset `baseline-main-protection`, edit the rules to enable `Require status checks to pass`:
   - Add exact check names: `governance-typecheck`, `unit-math-suite`, `operator-charter-audit`.
   - Set strict up-to-date requirement: `Disabled` (initially).

---

## 4. Emergency Bypass & Recovery Protocol

Under the Operator Charter, human operators retain sovereign authority over system state:
1. **Emergency Hotfix Authority:** In the event that an unhandled production bug requires an immediate patch during active trading/observation hours, the Repository Admin may bypass the PR ruleset using the Admin Bypass privilege.
2. **Audit Trail Mandate:** Any emergency bypass must be documented in `docs/governance/` within 24 hours, recording the commit SHA, the reason for bypass, and the regression tests executed offline.
3. **No Retrospective Policy Changes:** An emergency bypass does not retroactively change scientific thresholds or gate criteria.

---

## 5. Verification Ledger

- Audit State: COMPLETE
- Current Remote Protection: UNPROTECTED (Zero rulesets, zero branch protections, zero workflows)
- Phase A Readiness: READY for configuration post-Observation #0001
- Phase B Dependency: Requires `.github/workflows/ci.yml` implementation
- Critical Invariant: Strict prohibition against premature Required Status Checks preserved
