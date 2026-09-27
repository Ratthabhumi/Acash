"""Synthetic repositories only; no ACASH imports, credentials, market data or host access."""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import operator_charter_audit as audit


class ContractTests(unittest.TestCase):
    def test_exact_production_pins(self) -> None:
        self.assertEqual(audit.BASE, "d9608c0a2353bd5ed41943e5fb893ef9648089d2")
        self.assertEqual(audit.CHARTER, "e787cda941a1f6fc008ba06282dfee7321c60f3f")
        self.assertEqual(audit.CHARTER_BLOB, "45bd426d7079f1a34fdf441c6fc8b8d3f48970b3")

    def test_additions_stay_outside_gate_b_software_hash_scope(self) -> None:
        for path in audit.ADDITIONS:
            self.assertFalse(path.startswith(("src/", "tools/governance/")))
            self.assertNotIn(path, {"pyproject.toml", "uv.lock"})

    def test_authority_requires_exact_types_and_values(self) -> None:
        valid = dict(paper=False, live=False, capital="0.00", no_real_orders=True)
        self.assertEqual(audit.authority_state(valid)[0], "VERIFIED")
        for key, values in {
            "paper": [True, 0, "false", None], "live": [True, 0, "false"],
            "capital": [0, 0.0, "100000.00", "NaN", "Infinity"],
            "no_real_orders": [False, 1, "true"],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertEqual(audit.authority_state({**valid, key: value})[0], "BLOCKED")
            incomplete = valid.copy()
            del incomplete[key]
            self.assertEqual(audit.authority_state(incomplete)[0], "UNKNOWN")

    def test_ambiguous_json_rejected(self) -> None:
        for value in ['{"paper":true,"paper":false}', '{"x":NaN}',
                      '{"x":Infinity}', '[]', 'null', '{']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit.strict_object(value)

    def test_no_runtime_or_network_imports(self) -> None:
        source = Path(audit.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed = {"__future__", "argparse", "dataclasses", "datetime", "json",
                   "os", "pathlib", "subprocess", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(name.name in allowed for name in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)

    def test_mutating_git_command_refused(self) -> None:
        with self.assertRaises(audit.EvidenceUnavailable):
            audit.Git(Path(".")).read("fetch", "origin")

    def test_collection_failure_is_unknown_and_no_authority(self) -> None:
        with patch.object(audit.Git, "snapshot", side_effect=audit.EvidenceUnavailable("missing")):
            result = audit.assess(Path("."))
        self.assertEqual(result["assessment"], "UNKNOWN")
        self.assertEqual(set(result["authority_granted"].values()), {"NOT_AUTHORIZED"})

    def test_cli_collection_error_exits_two_with_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()) as out:
            code = audit.main(["--repo", directory])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["assessment"], "UNKNOWN")

    def test_cli_does_not_turn_blocked_assessment_into_interlock(self) -> None:
        fake = audit.report([audit.Finding("test", "BLOCKED", "4", "fixture", "drift")], None)
        with patch.object(audit, "assess", return_value=fake), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--repo", "."]), 0)


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.write("src/observation.py", "# sealed synthetic runtime\n")
        self.write(".gitignore", "var/\n")
        self.valid = dict(paper=False, live=False, capital="0.00", no_real_orders=True)
        for path in audit.MANIFESTS:
            self.write(path, json.dumps({**self.valid, "prospective_starting_aum": "100000.00"}))
        self.commit()
        base = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", base)
        self.git("switch", "-c", "charter-fixture")
        self.write(audit.CHARTER_PATH, "Synthetic normative fixture, not empirical authority.\n")
        self.commit()
        charter = self.git("rev-parse", "HEAD")
        blob = self.git("rev-parse", f"HEAD:{audit.CHARTER_PATH}")
        self.git("switch", "-c", "audit-fixture", base)
        for key, value in (("BASE", base), ("CHARTER", charter), ("CHARTER_BLOB", blob)):
            patcher = patch.object(audit, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def git(self, *args: str) -> str:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        result = subprocess.run(["git", "-C", str(self.repo), *args], env=env,
                                check=True, capture_output=True, text=True)
        return result.stdout.strip()

    def write(self, path: str, content: str) -> None:
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def commit(self) -> None:
        self.git("add", "--all")
        self.git("commit", "-m", "synthetic fixture", "--no-gpg-sign")

    def state(self, check: str) -> str:
        findings = audit.assess(self.repo)["findings"]
        return str(next(item["state"] for item in findings if item["check"] == check))

    def test_clean_scope_still_unknown_overall(self) -> None:
        result = audit.assess(self.repo)
        self.assertEqual(self.state("COMMITTED_SCOPE"), "VERIFIED")
        self.assertEqual(self.state("WORKTREE_SCOPE"), "VERIFIED")
        self.assertEqual(result["assessment"], "UNKNOWN")
        self.assertEqual(result["runtime_effect"], "NONE")

    def test_allowed_additions_pass_scope(self) -> None:
        for path in audit.ADDITIONS:
            self.write(path, "synthetic audit-only addition\n")
        self.assertEqual(self.state("WORKTREE_SCOPE"), "VERIFIED")
        self.commit()
        self.assertEqual(self.state("COMMITTED_SCOPE"), "VERIFIED")

    def test_committed_runtime_change_blocked(self) -> None:
        self.write("src/observation.py", "# unauthorized change\n")
        self.commit()
        self.assertEqual(self.state("COMMITTED_SCOPE"), "BLOCKED")

    def test_unstaged_runtime_change_blocked(self) -> None:
        self.write("src/observation.py", "# unauthorized change\n")
        self.assertEqual(self.state("WORKTREE_SCOPE"), "BLOCKED")

    def test_staged_change_hidden_by_worktree_restore_blocked(self) -> None:
        self.write("src/observation.py", "# staged change\n")
        self.git("add", "src/observation.py")
        self.write("src/observation.py", "# sealed synthetic runtime\n")
        self.assertEqual(self.state("WORKTREE_SCOPE"), "BLOCKED")

    def test_deleted_existing_file_blocked(self) -> None:
        self.git("rm", "src/observation.py")
        self.commit()
        self.assertEqual(self.state("COMMITTED_SCOPE"), "BLOCKED")

    def test_renamed_existing_file_blocked(self) -> None:
        self.git("mv", "src/observation.py", "src/renamed.py")
        self.commit()
        self.assertEqual(self.state("COMMITTED_SCOPE"), "BLOCKED")

    def test_new_workflow_blocked_even_without_runtime_change(self) -> None:
        self.write(".github/workflows/audit.yml", "name: unauthorized coupling\n")
        self.assertEqual(self.state("WORKTREE_SCOPE"), "BLOCKED")
        self.commit()
        self.assertEqual(self.state("COMMITTED_SCOPE"), "BLOCKED")

    def test_capital_confusion_and_authority_drift_blocked(self) -> None:
        self.write(audit.MANIFESTS[0], json.dumps({**self.valid, "capital": "100000.00"}))
        self.commit()
        self.assertEqual(self.state("AUTHORITY:" + audit.MANIFESTS[0]), "BLOCKED")

    def test_duplicate_manifest_key_unknown(self) -> None:
        self.write(audit.MANIFESTS[0], '{"paper":true,"paper":false}')
        self.commit()
        self.assertEqual(self.state("AUTHORITY:" + audit.MANIFESTS[0]), "UNKNOWN")

    def test_missing_authority_field_unknown(self) -> None:
        self.write(audit.MANIFESTS[0], '{}')
        self.commit()
        self.assertEqual(self.state("AUTHORITY:" + audit.MANIFESTS[0]), "UNKNOWN")

    def test_normative_blob_mismatch_blocked(self) -> None:
        with patch.object(audit, "CHARTER_BLOB", "0" * 40):
            self.assertEqual(self.state("NORMATIVE_SOURCE"), "BLOCKED")

    def test_missing_normative_object_unknown(self) -> None:
        with patch.object(audit, "CHARTER", "0" * 40):
            self.assertEqual(self.state("EVIDENCE_COLLECTION"), "UNKNOWN")

    def test_cached_main_drift_blocked(self) -> None:
        self.git("update-ref", "refs/remotes/origin/main", audit.CHARTER)
        self.assertEqual(self.state("LOCAL_PIN:refs/remotes/origin/main"), "BLOCKED")

    def test_assume_unchanged_cannot_hide_runtime_edit(self) -> None:
        self.git("update-index", "--assume-unchanged", "src/observation.py")
        self.write("src/observation.py", "# hidden mutation\n")
        self.assertEqual(self.state("INDEX_VISIBILITY"), "BLOCKED")

    def test_skip_worktree_cannot_hide_runtime_edit(self) -> None:
        self.git("update-index", "--skip-worktree", "src/observation.py")
        self.write("src/observation.py", "# hidden mutation\n")
        self.assertEqual(self.state("INDEX_VISIBILITY"), "BLOCKED")

    def test_caller_git_directory_cannot_redirect_audit(self) -> None:
        with patch.dict(os.environ, {"GIT_DIR": "nonexistent", "GIT_WORK_TREE": "nonexistent"}):
            self.assertEqual(self.state("COMMITTED_SCOPE"), "VERIFIED")

    def test_concurrent_change_not_certified(self) -> None:
        original = audit.Git.snapshot
        count = 0

        def unstable(instance: audit.Git) -> tuple[str, str, str, str, str]:
            nonlocal count
            count += 1
            value = original(instance)
            return value if count == 1 else (*value[:4], "changed")

        with patch.object(audit.Git, "snapshot", unstable):
            self.assertEqual(self.state("SNAPSHOT_STABILITY"), "UNKNOWN")

    def test_report_does_not_mutate_checkout_index_or_ignored_state(self) -> None:
        self.write("var/prospective/state.json", '{"observation_count":0}')
        def snapshot() -> dict[str, bytes]:
            return {str(path.relative_to(self.repo)): path.read_bytes()
                    for path in self.repo.rglob("*") if path.is_file()}
        before = snapshot()
        audit.assess(self.repo)
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
