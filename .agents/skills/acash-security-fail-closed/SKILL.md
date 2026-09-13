---
name: acash-security-fail-closed
description: Audit ACASH credential handling, execution safety and infrastructure exposure; use for fail-closed security reviews and potential broker or production activation paths.
---

# ACASH security and fail-closed boundaries

Read root `AGENTS.md` and the deployment/security and feed rows in
`docs/engineering/agent-workflow.md`. Inspect the actual execution/configuration
path relevant to the request; do not launch services to discover their safety.

- Track canonical capital authority independently from simulated fixture cash or
  dashboard reference notional. Preserve $0.00 canonical capital and
  `NO_REAL_ORDERS=true`; a paper label, broker library or test fixture is not
  authorization to dispatch an external order.
- Inspect credential ingress, logging and redaction, default endpoints, subprocess
  argument construction, unsafe automation, network exposure, privileges, Docker
  socket mounts and accidental production activation where the task reaches them.
  Report evidence rather than assuming safe deployment from a source comment.
- If credentials appear, prevent further disclosure and redact derived reports.
  Preserve incident evidence securely; do not paste secrets, overwrite original
  logs, rewrite Git history, rotate credentials or modify external accounts as
  an unrequested side effect. Report exposure and the required containment action.
- Verify fail-closed transitions using existing readiness/window/feed contracts
  and focused tests. Respect the OPEN deployment interlock's abort-all behavior,
  fixed UID census guard and operator-only feed recovery. Error handling cannot
  silently restore health, admit bars or enable orders.
- Distinguish Dockerfile/config evidence from actual HomeLab deployment state.
  Runtime secrets, compose configuration, container/network state and operator
  authority require their own evidence. An audit is not permission to change
  firewall rules, expose ports, mount sockets or contact a broker.

Report finding, affected boundary, sanitized evidence, impact, containment and
minimal remediation. Classify warnings as defects, dependency compatibility debt,
expected behavior or accepted risk; state what remains unverified. End with the
root verification ledger. This workflow does not substitute for runtime security
controls or authorize a production transition.
