"""Offline advisory assessment. Never import or invoke the ACASH runtime.

Run manually with python -B tools/audit/operator_charter_audit.py --repo .
JSON is written only to stdout. Findings never grant authority or gate a service.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any

BASE = "d9608c0a2353bd5ed41943e5fb893ef9648089d2"
CHARTER = "e787cda941a1f6fc008ba06282dfee7321c60f3f"
CHARTER_PATH = "docs/governance/OPERATOR_DECISION_CHARTER_V1.md"
CHARTER_BLOB = "45bd426d7079f1a34fdf441c6fc8b8d3f48970b3"
ADDITIONS = frozenset({
    "tools/audit/operator_charter_audit.py",
    "tools/audit/tests/test_operator_charter_audit.py",
    "docs/governance/OPERATOR_CHARTER_AUDIT_V1.md",
    "docs/governance/OPERATOR_CHARTER_AUDIT_IMPLEMENTATION_RECORD.md",
})
MANIFESTS = (
    "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_BINDING.json",
    "docs/phase14/manifests/HYP_011_PROSPECTIVE_SHADOW_ACTIVATION_RECONCILIATION.json",
)


class EvidenceUnavailable(Exception):
    """Missing or invalid evidence cannot become a successful assessment."""


@dataclass(frozen=True)
class Finding:
    check: str
    state: str
    charter_sections: str
    evidence: str
    detail: str


class Git:
    """Only local read commands; disable lazy fetching, replacements and fsmonitor."""

    def __init__(self, repo: Path) -> None:
        self.repo = repo

    def read(self, *args: str) -> str:
        if not args or args[0] not in {
            "rev-parse", "ls-tree", "show", "diff", "ls-files", "merge-base",
        }:
            raise EvidenceUnavailable("Non-read Git command refused")
        env = dict(os.environ)
        # Caller Git environment must not silently redirect evidence to another repo.
        for key in list(env):
            if key.startswith("GIT_"):
                del env[key]
        env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1",
                   GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0",
                   GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        try:
            result = subprocess.run(
                ["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
                 "-C", str(self.repo), *args],
                capture_output=True, check=False, timeout=30, env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EvidenceUnavailable(f"Git {args[0]} unavailable") from exc
        if result.returncode:
            raise EvidenceUnavailable(f"Git {args[0]} failed (exit {result.returncode})")
        if result.stderr.strip():
            raise EvidenceUnavailable(f"Git {args[0]} emitted diagnostics; collection unverified")
        try:
            return result.stdout.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceUnavailable("Non-UTF-8 Git evidence") from exc

    def tree(self, commit: str) -> dict[str, str]:
        entries = self.read("ls-tree", "-r", "-z", commit).split("\0")
        return {entry.split("\t", 1)[1]: entry.split("\t", 1)[0]
                for entry in entries if entry}

    def snapshot(self) -> tuple[str, str, str, str, str]:
        # Includes staged, unstaged and nonignored untracked paths, not their data.
        # Ignored state/cache/data is deliberately not opened or certified.
        return (
            self.read("rev-parse", "HEAD").strip(),
            self.read("ls-files", "--stage", "-z"),
            self.read("diff", "--no-ext-diff", "--no-textconv", "--raw",
                      "--no-abbrev", "--no-renames", "HEAD", "--"),
            self.read("diff", "--no-ext-diff", "--no-textconv", "--raw",
                      "--no-abbrev", "--no-renames", "--"),
            self.read("ls-files", "--others", "--exclude-standard", "-z"),
        )


def strict_object(text: str) -> dict[str, Any]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON constant: {value}")

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("Manifest must be an object")
    return value


def authority_state(manifest: dict[str, Any]) -> tuple[str, str]:
    expected: dict[str, Any] = {"paper": False, "live": False,
                                "capital": "0.00", "no_real_orders": True}
    if any(key not in manifest for key in expected):
        return "UNKNOWN", "Required authority field missing"
    if any(type(manifest[key]) is not type(value) or manifest[key] != value
           for key, value in expected.items()):
        return "BLOCKED", "Authority fields contradict the pinned zero-authority contract"
    return "VERIFIED", "Record states paper=false, live=false, capital=0.00, no_real_orders=true"


def report(findings: list[Finding], head: str | None) -> dict[str, Any]:
    states = {finding.state for finding in findings}
    return {
        "schema_version": 1,
        "mode": "ADVISORY_AUDIT_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "canonical_base": BASE,
        "normative_source": {"commit": CHARTER, "path": CHARTER_PATH, "blob": CHARTER_BLOB},
        "assessed_head": head,
        "assessment": "BLOCKED" if "BLOCKED" in states else "UNKNOWN",
        "assessment_scope": "LOCAL_REPOSITORY_RECORDS_ONLY",
        "runtime_effect": "NONE",
        "authority_granted": {"empirical": "NOT_AUTHORIZED", "paper": "NOT_AUTHORIZED",
                              "live": "NOT_AUTHORIZED", "capital": "NOT_AUTHORIZED"},
        "findings": [asdict(finding) for finding in findings],
    }


def assess(repo: Path) -> dict[str, Any]:
    git = Git(repo)
    findings: list[Finding] = []
    head: str | None = None

    def add(check: str, state: str, sections: str, evidence: str, detail: str) -> None:
        findings.append(Finding(check, state, sections, evidence, detail))

    try:
        before = git.snapshot()
        head = before[0]
        base_tree = git.tree(BASE)
        head_tree = git.tree(head)
        ancestor = git.read("merge-base", BASE, head).strip()
        add("BASE_LINEAGE", "VERIFIED" if ancestor == BASE else "BLOCKED", "1,4,10",
            f"{BASE}..{head}", "HEAD must descend from the exact canonical base")
        charter_tree = git.tree(CHARTER)
        charter_entry = charter_tree.get(CHARTER_PATH, "")
        add("NORMATIVE_SOURCE", "VERIFIED" if charter_entry == f"100644 blob {CHARTER_BLOB}"
            else "BLOCKED", "1,8,10", f"{CHARTER}:{CHARTER_PATH}",
            "Exact Charter blob required; no worktree copy or branch-name substitution")

        changed_existing = sorted(path for path, entry in base_tree.items()
                                  if head_tree.get(path) != entry)
        extra = sorted(set(head_tree) - set(base_tree) - ADDITIONS)
        missing_required = sorted(ADDITIONS - set(head_tree))
        add("COMMITTED_SCOPE",
            "BLOCKED" if changed_existing or extra or missing_required else "VERIFIED",
            "4,5,10", f"Git trees {BASE}..{head}",
            json.dumps({"changed_or_deleted_existing": changed_existing,
                        "unexpected_additions": extra,
                        "missing_required_additions": missing_required}))

        dirty: set[str] = set()
        for args in (("--cached", "HEAD"), ("HEAD",), ()):
            dirty.update(filter(None, git.read(
                "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
                "--ignore-submodules=none", "--name-only", "-z", *args, "--",
            ).split("\0")))
        untracked = set(filter(None, before[4].split("\0")))
        violations = sorted((dirty | untracked) - ADDITIONS)
        add("WORKTREE_SCOPE", "BLOCKED" if violations else "VERIFIED", "4,5,10",
            "index + tracked working tree + nonignored untracked paths",
            json.dumps({"unexpected_paths": violations,
                        "audit_files_pending": sorted((dirty | untracked) & ADDITIONS),
                        "ignored_runtime_state": "NOT_INSPECTED"}))

        hidden = sorted(entry[2:] for entry in git.read("ls-files", "-v", "-z").split("\0")
                        if entry and (entry[0].islower() or entry[0] == "S"))
        add("INDEX_VISIBILITY", "BLOCKED" if hidden else "VERIFIED", "3,4.7",
            "git ls-files -v", json.dumps({"assume_unchanged_or_skip_worktree": hidden}))

        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            try:
                value = git.read("rev-parse", "--verify", ref).strip()
                add("LOCAL_PIN:" + ref, "VERIFIED" if value == BASE else "BLOCKED",
                    "4,10", ref, value + "; local/cached evidence only")
            except EvidenceUnavailable:
                add("LOCAL_PIN:" + ref, "UNKNOWN", "4,10", ref, "Local ref unavailable")

        for path in MANIFESTS:
            try:
                manifest = strict_object(git.read("show", f"{head}:{path}"))
                state, detail = authority_state(manifest)
                add("AUTHORITY:" + path, state, "4.8,4.9,10", f"{head}:{path}", detail)
                if "prospective_starting_aum" in manifest:
                    simulated = manifest["prospective_starting_aum"]
                    add("SIMULATED_ACCOUNTING", "VERIFIED" if type(simulated) is str
                        and simulated == "100000.00" else "BLOCKED", "4.9,5.G,10",
                        f"{head}:{path}", "Pinned simulated AUM is not real capital or authority")
            except (EvidenceUnavailable, ValueError):
                add("AUTHORITY:" + path, "UNKNOWN", "4,10", f"{head}:{path}",
                    "Missing, malformed or ambiguous manifest")
        if git.snapshot() != before:
            add("SNAPSHOT_STABILITY", "UNKNOWN", "3,4.7", "local Git snapshot",
                "Concurrent checkout change detected; rerun in a quiescent isolated clone")
        else:
            add("SNAPSHOT_STABILITY", "VERIFIED", "3,4.7", "local Git snapshot",
                "No observed Git snapshot change during collection; not an atomic host snapshot")
    except EvidenceUnavailable as exc:
        add("EVIDENCE_COLLECTION", "UNKNOWN", "4.7,6", "local Git object database", str(exc))

    # These deliberately cannot be cleared by keyword scans, a profitable result,
    # a caller-supplied boolean, or mechanically green repository checks.
    for check, sections, detail in (
        ("REMOTE_AND_HOST", "4,10", "Live GitHub refs/protection, homelab, timer/service and Observation #0001 runtime were not queried"),
        ("DECISION_MOTIVATION", "3,5.A,5.F,6", "Human review: FOMO, status, sunk cost, urgency, opposite-result counterfactual"),
        ("EVIDENCE_AND_SCALE", "2,3,4.1-4.6,6", "Human review: empirical lineage, all trials K, costs, intake, feedback and evidence before scaling"),
        ("SEALED_RULES", "4,5.B,5.C,8", "Human review: decision-specific sealed rules, post-outcome changes and explicit supersession; no S2 amendment here"),
        ("SCOPE_AND_REVERSIBILITY", "3,4.10,5.D,5.E,9", "Human review: one objective, downside, reversibility and privacy; no personal motivation inferred"),
    ):
        add(check, "UNKNOWN", sections, "Separate scoped primary evidence required", detail)
    return report(findings, head)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True,
                        help="Isolated local clone to inspect; never point at the active homelab")
    args = parser.parse_args(argv)
    result = assess(args.repo)
    print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    # A finding is a report, not a runtime interlock. 2 means collection failed.
    return 2 if any(f["check"] == "EVIDENCE_COLLECTION" for f in result["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
