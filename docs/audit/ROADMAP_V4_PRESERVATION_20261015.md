# Roadmap v4 — Preservation & Legacy Reference Compatibility

**AS OF:** 2026-10-15 (Asia/Bangkok). Documentation change only; no research, acquisition, paper/live or capital authority.

## Chosen base and immutable bytes

| Snapshot | Commit | Git blob | Bytes / SHA-256 |
| --- | --- | --- | --- |
| Canonical main before this task | `250bf0304d763cb86f961ca26b5c5771421a23ab` | `3b122652ccc1f80076220b5e16717b2e1ae3495d` | 65127 / `5015e6b74b663a9e80ad6b9b1e46d67e501cc024ee4ca0d3dc36fd65670960b3` |
| Chosen stacked base, PR #36 | `87e1176adb2f9541773b4b3d87c479691f5e11d2` | `68317f3841778f93dd4874cbfbbe2ecfc254027f` | 65099 / `a4dcb34f79d6556916fad2510d657b3384e525db18e27b726beaa784cdd9d117` |

[Exact archived source](../ROADMAP_v3.7.0_87e1176_ARCHIVE.md) contains the **723-line** chosen-base blob byte-for-byte. The pasted checkpoint said 724 lines; Git blob `splitlines()` yields 723, which is the measurement used here. The main and stacked-base blobs differ only in PR #36's reviewed scope-label correction. No archive banner or newline normalization was inserted into the snapshot. Relative links retain their original directory depth; dated delivery content in the archive is superseded history, not a second active plan.

[Active roadmap](../ROADMAP.md) replaces only the top delivery presentation and retains every byte from `## ACASH CURRENT NORTH-STAR (2026-09-11)` to EOF, including Phase 0–23 titles/statuses, architectural proposals, acceptance criteria, historical test/CI claims, evidence links, runbooks and proprietary license. Earlier introductory wording and the former D0–D6 plan remain exactly recoverable in the full archive/base blob. No sealed/ratified source record, source code, tests, manifest, dataset or authority record is changed.

## Fixed-line compatibility map

A byte-exact archive by itself does not preserve old line semantics at a changed path. The following **11 occurrences** were found by scanning every tracked UTF-8-decodable file before editing for `docs/ROADMAP.md:<line>` and `<line-range>`, including historical chat exports. All occur in the three protected Phase 13 records below. Their lines were traced with `git blame --porcelain -L n,n 87e1176adb2f9541773b4b3d87c479691f5e11d2 -- <source>` to the authoring commit:

`8fe34dc24c0fc9343e30ec36398b7e0db73a408d`

The target roadmap at that commit is blob:

`1fa82ddd9594b100c65f3d2d8116c709a6922f4f`

| Unchanged citing record / source line | Legacy target | Frozen target meaning |
| --- | --- | --- |
| [phase13_step5_evidence_acceptance.md](../phase13/phase13_step5_evidence_acceptance.md), line 15 | `docs/ROADMAP.md:136-139` | Immediate Next Action: complete soak; audit telemetry, memory, ledger and crash recovery; then Step 6 |
| [phase13_step5_evidence_acceptance.md](../phase13/phase13_step5_evidence_acceptance.md), line 57 | `docs/ROADMAP.md:380` | Step 5 (24-Hour Unattended Soak) |
| [phase13_step6_full_audit_report.md](../phase13/phase13_step6_full_audit_report.md), line 15 | `docs/ROADMAP.md:381` | Step 6 (Telemetry Audit) |
| [phase13_step6_full_audit_report.md](../phase13/phase13_step6_full_audit_report.md), line 58 | `docs/ROADMAP.md:382` | Step 7 (Continuous Paper Readiness) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 15 | `docs/ROADMAP.md:382` | Step 7 (Continuous Paper Readiness) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 29 | `docs/ROADMAP.md:376` | Step 1 (Implementation & Safety Envelopes) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 30 | `docs/ROADMAP.md:377` | Step 2 (Code & Unit Audit) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 31 | `docs/ROADMAP.md:378` | Step 3 (Integration Testing) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 32 | `docs/ROADMAP.md:379` | Step 4 (Restart & Recovery) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 36 | `docs/ROADMAP.md:382` | Step 7 (Continuous Paper Readiness) |
| [phase13_step7_paper_readiness_review.md](../phase13/phase13_step7_paper_readiness_review.md), line 42 | `docs/ROADMAP.md:388` | STRAT-MOM-MULTI-HORIZON-V1 NOT QUALIFIED / TERMINALLY FALSIFIED |

These frozen lines were read and matched to each citing record's stated topic. No authoring-target mismatch was found among these 11 occurrences. This is reference-resolution evidence, not a re-audit of historical runtime outcomes. The protected citing records are unchanged.

To resolve a legacy line, use its authoring commit above, **not today's line number**:

```text
git show 8fe34dc24c0fc9343e30ec36398b7e0db73a408d:docs/ROADMAP.md
git rev-parse 8fe34dc24c0fc9343e30ec36398b7e0db73a408d:docs/ROADMAP.md
```

For the v3.7.0 checkpoint's line semantics, use the chosen-base commit/blob in the first table. The archive preserves that checkpoint's lines, not the earlier Phase 13 line positions. Existing unversioned historical links remain historically scoped; they must not be interpreted as current approval.

## Link and anchor impact

The active historical suffix remains at its original relative path, so its relative file targets and heading text retain their meaning; line numbers necessarily move. Existing archived links keep their original `docs/` directory context. No protected citation is rewritten to a new line number.

The obsolete active-section anchors are retained as compatibility markers below the active roadmap's history boundary; they lead to the preservation notice and exact archive, not competing delivery instructions. New navigation uses explicit stable anchors. Full tracked-text inbound references are inventoried locally; newly introduced file links and active section anchors are checked, and existing link defects are reported separately. This does not assert that all historical links or external websites are valid forever.

## Executed local documentation checks

- Staged archive equality and Git blob identity: PASS. Active-roadmap historical-suffix equality: PASS. One active H1 and exactly ten detailed stage headings: PASS.
- Full tracked-text scan: 1283 UTF-8-decodable files, 332 lines mentioning roadmap references; 11 fixed-line citations mapped above; no checkpoint blob-hash binding found. This covers committed text, not ignored datasets or off-repository consumers.
- New/active navigation check: 104 newly introduced and 107 inherited relative-link occurrences checked; no new path/anchor error or inbound roadmap-fragment error found in the scan. Markdown table column checks passed. These are local structural checks, not an external-link availability guarantee.

- Complete active roadmap (109 relative file-link occurrences) and archive (18): no missing file targets.
- `git diff --cached --check` exits 2 for ten archived lines with the original two-space Markdown hard breaks. Classified EXPECTED PRESERVED CONTENT; no source bytes normalized. The same check excluding the byte-exact archive passes.

## Verification boundary and scope

- Documentation-only scope: root README, documentation hub, roadmap, exact archive, this preservation map and the Research handoff.
- Verify archive equality against `git show 87e1176adb2f9541773b4b3d87c479691f5e11d2:docs/ROADMAP.md`; SHA-256 and Git blob must match the table before and after staging.
- Verify active roadmap historical suffix equals the original suffix byte-for-byte and all original phase headings survive.
- Check one active H1, D1–D10 stage names, legacy D0–D9 mapping, Markdown table columns, new relative paths/anchors, inbound roadmap anchors and `git diff --check` (preserved Markdown hard breaks separately classified).
- No local quantitative suite or MyPy rerun is implied by documentation checks. CI runs the configured T1 Python matrix and MyPy; report exact run outcomes independently.
- Historical scientific/economic outcomes are verified as recorded claims from committed reports/manifests. No protected data was read, no dataset hash was independently recomputed, no historical run was replayed and no contemporary host/account state was audited.
- Research questions are handed off for official-source verification; no new external market-data, fee or tax fact is asserted by the handoff.

### Verification Ledger

- Implementation Status: COMPLETE (documentation and preservation artifacts)
- Contract Enforcement: N/A (runtime unchanged; authority boundaries explicitly retained)
- Mathematical Authority: N/A (no formulation change)
- Local Test Suite: NOT RUN (documentation verification is separate)
- Type Checker (MyPy): NOT RUN locally
- Remote CI Status: PENDING at preparation; consult the delivered PR for exact final run state
- Methodological Caveats: historical record text is not fresh runtime evidence; fixed lines resolve only at their documented versions; no new-scope admission or authority issued.
