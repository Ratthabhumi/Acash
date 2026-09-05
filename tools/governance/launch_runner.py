"""Tier 2: Authenticated Pre-Execution Launcher for Gate B Runner.

Strictly adheres to:
- Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10 Section 3)
- Invariants: Pre-Execution Attestation, Python Isolated Mode (-I -s -E), Anti-Hijacking
- Enforcement: Halts immediately if launcher, interpreter, dependencies, or codebase is modified.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import List, Optional

from acash.gate_b.exceptions import PreExecutionIntegrityError
from acash.gate_b.manifest import (
    ReleaseManifest,
    compute_acash_release_tree_v1,
    compute_acash_runtime_env_v1,
)


class AuthenticatedLauncher:
    """Pre-execution integrity verifier and isolated Python launcher."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def verify_pre_execution_environment(
        self,
        manifest_path: Optional[Path] = None,
        verify_tree: bool = True,
        verify_runtime: bool = True,
    ) -> ReleaseManifest:
        """Verify release manifest against physical artifacts prior to runner invocation."""
        # 0. Assert clean anti-hijacking environment (Pre-execution fail-closed)
        if "PYTHONPATH" in os.environ and os.environ.get("ACASH_ALLOW_PYTHONPATH_FOR_TEST") != "1":
            raise PreExecutionIntegrityError("PYTHONPATH_INJECTION_DETECTED: PYTHONPATH environment variable prohibited")

        manifest_file = manifest_path or (self.repo_root / "release_manifest.json")
        if not manifest_file.exists():
            raise PreExecutionIntegrityError(f"RELEASE_MANIFEST_MISSING: {manifest_file}")

        try:
            manifest = ReleaseManifest.model_validate_json(manifest_file.read_bytes())
        except Exception as exc:
            raise PreExecutionIntegrityError(f"RELEASE_MANIFEST_MALFORMED: {exc}") from exc

        # 1. Assert launcher artifact integrity
        launcher_file = self.repo_root / "tools" / "governance" / "launch_runner.py"
        if launcher_file.exists():
            calc_launcher_sha = hashlib.sha256(launcher_file.read_bytes()).hexdigest()
            if calc_launcher_sha != manifest.launcher_artifact_sha256:
                raise PreExecutionIntegrityError(
                    f"LAUNCHER_ARTIFACT_TAMPERED: calculated {calc_launcher_sha} vs expected {manifest.launcher_artifact_sha256}"
                )

        # 2. Assert python interpreter integrity
        python_exe = Path(sys.executable).resolve()
        if python_exe.exists():
            calc_py_sha = hashlib.sha256(python_exe.read_bytes()).hexdigest()
            if calc_py_sha != manifest.python_interpreter_sha256:
                raise PreExecutionIntegrityError(
                    f"PYTHON_INTERPRETER_TAMPERED: calculated {calc_py_sha} vs expected {manifest.python_interpreter_sha256}"
                )

        # 3. Assert codebase tree integrity (ACASH-RELEASE-TREE-V1)
        if verify_tree:
            calc_tree_digest, _ = compute_acash_release_tree_v1(self.repo_root)
            if calc_tree_digest != manifest.executable_tree_digest:
                raise PreExecutionIntegrityError(
                    f"EXECUTABLE_TREE_DIGEST_MISMATCH: calculated {calc_tree_digest} vs expected {manifest.executable_tree_digest}"
                )

        # 4. Assert runtime dependencies integrity (ACASH-RUNTIME-ENV-V1)
        if verify_runtime:
            venv_site_packages = self.repo_root / ".venv" / "Lib" / "site-packages"
            if venv_site_packages.exists():
                calc_runtime_digest, _ = compute_acash_runtime_env_v1(venv_site_packages)
                if calc_runtime_digest != manifest.runtime_dependencies_tree_digest:
                    raise PreExecutionIntegrityError(
                        f"RUNTIME_DEPENDENCIES_DIGEST_MISMATCH: calculated {calc_runtime_digest} vs expected {manifest.runtime_dependencies_tree_digest}"
                    )

        return manifest

    def launch_runner_isolated(self, runner_args: List[str]) -> int:
        """Spawn the verify-only runner in strict Python Isolated Mode (-I -s -E)."""
        runner_script = (self.repo_root / "src" / "acash" / "gate_b" / "runner.py").resolve()
        if not runner_script.exists():
            raise PreExecutionIntegrityError(f"RUNNER_SCRIPT_NOT_FOUND: {runner_script}")

        cmd = [
            sys.executable,
            "-I",  # Isolated mode: implies -E and -s; ignores PYTHONPATH and removes CWD from sys.path
            "-s",  # Don't add user site directory to sys.path
            "-E",  # Ignore all PYTHON* environment variables
            str(runner_script),
        ] + runner_args

        # Execute runner under isolated child process
        result = subprocess.run(cmd, cwd=str(self.repo_root))
        return result.returncode


def main() -> None:
    """CLI entrypoint for authenticated launcher."""
    repo_root = Path.cwd()
    launcher = AuthenticatedLauncher(repo_root)

    # Pre-execution attestation
    launcher.verify_pre_execution_environment()

    # Pass all remaining arguments to runner
    runner_args = sys.argv[1:]
    exit_code = launcher.launch_runner_isolated(runner_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
