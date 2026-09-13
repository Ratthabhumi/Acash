---
name: acash-repository-audit
description: Establish ACASH checkout state and review Git change scope before edits or commit preparation; use for repository audits, unexpected modifications and branch divergence.
---

# ACASH repository audit and change control

Read root `AGENTS.md`. Run from the repository root:

```text
git status --short --branch
git branch -vv
git log -5 --oneline
git diff --stat
git diff
git diff --cached
```

Use `rg --files` (include hidden instruction/config paths when relevant) and
`rg` to locate source, tests, governance and configuration. Read
`docs/engineering/agent-workflow.md` only for the needed source map.

- Capture the baseline commit, existing tracked/untracked work and tracking-ref
  freshness. Local `origin/main` is cached evidence; do not claim remote parity
  without a successful read of the remote. An audit does not authorize pull,
  merge, stash, rebase, reset or a branch switch.
- Preserve uncommitted work, especially governance files. Identify authorship or
  intent before touching overlapping changes; do not automatically discard them.
- Compare proposed scope against history, active decision records, implementation
  and tests. Flag accidental historical edits, unrelated changes and boundary
  creep. Stale `.omc/` memory and `.kilo/` configuration are not Codex authority.
- Before an explicitly authorized commit, review intended paths, untracked file
  contents, `git diff --check`, tests, typecheck and applicable builds. Check for
  secrets without printing their values. Stage explicit paths only after review.
- Never force push, rewrite history, blindly reset or discard work without the
  explicit authorization those actions require. No commit, push, PR or remote
  mutation follows automatically from implementation approval.

Report FACT, EVIDENCE, CHANGES, TESTS, RISKS, UNRESOLVED ITEMS, AUTHORIZATION STATUS
and NEXT STEP, followed by the root ledger. Include exact intended files and a
proposed commit message when preparing a change; label CI unverified unless an
actual matching run was inspected.
