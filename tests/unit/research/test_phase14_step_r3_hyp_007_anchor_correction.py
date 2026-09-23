"""
Tests for HYP_007 R3 Anchor Lineage Correction (IMPLEMENTATION_CORRECTION_001).
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from acash.core.domain.exceptions import DataContractError
from acash.research.step_r3_hyp_007 import (
    DEFECTIVE_R3_COMMIT_SHA,
    DEFECTIVE_R3_DEFECT_CLASS,
    DEFECTIVE_R3_RESULT_PACKAGE_SHA256,
    get_previous_regular_close,
)
from acash.research.step_r3_hyp_007_metrics import EXCLUDED_SESSION_DATE


REPO_ROOT = Path(__file__).resolve().parents[3]


def _build_synthetic_continuous_closes() -> list[tuple[str, Decimal]]:
    return [
        ("2023-05-30", Decimal("420.00")),
        ("2023-05-31", Decimal("421.00")),
        ("2023-06-01", Decimal("422.00")),
        ("2023-06-02", Decimal("427.91")),
        ("2023-06-05", Decimal("427.10")),
        ("2023-06-06", Decimal("430.00")),
        ("2023-06-07", Decimal("432.00")),
    ]


def _build_early_close_continuous_closes() -> list[tuple[str, Decimal]]:
    return [
        ("2021-11-22", Decimal("468.00")),
        ("2021-11-23", Decimal("468.50")),
        ("2021-11-24", Decimal("469.37")),
        # 2021-11-26 early-close absent
        ("2021-11-29", Decimal("471.00")),
        ("2021-11-30", Decimal("472.00")),
    ]


class TestGetPreviousRegularClose:
    def test_returns_preceding_close_for_2023_06_06(self) -> None:
        closes = _build_synthetic_continuous_closes()
        result = get_previous_regular_close("2023-06-06", closes)
        assert result == Decimal("427.10"), (
            f"Expected 427.10 (2023-06-05) but got {result}. "
            "Defect: prior_14_sessions[-1] returns 427.91 (2023-06-02)."
        )

    def test_does_not_return_defective_close_427_91(self) -> None:
        closes = _build_synthetic_continuous_closes()
        result = get_previous_regular_close("2023-06-06", closes)
        assert result != Decimal("427.91"), (
            "Returned defective close 427.91 (2023-06-02) — IMPLEMENTATION_CORRECTION_001 defect."
        )

    def test_returns_correct_close_for_second_entry(self) -> None:
        closes = _build_synthetic_continuous_closes()
        result = get_previous_regular_close("2023-05-31", closes)
        assert result == Decimal("420.00")

    def test_raises_for_first_entry(self) -> None:
        closes = _build_synthetic_continuous_closes()
        with pytest.raises(DataContractError, match="first entry"):
            get_previous_regular_close("2023-05-30", closes)

    def test_raises_for_missing_session(self) -> None:
        closes = _build_synthetic_continuous_closes()
        with pytest.raises(DataContractError, match="not found in continuous daily-close lineage"):
            get_previous_regular_close("2099-01-01", closes)

    def test_2023_06_05_present_at_427_10_in_lineage(self) -> None:
        closes = _build_synthetic_continuous_closes()
        matching = [c for dt, c in closes if dt == "2023-06-05"]
        assert len(matching) == 1
        assert matching[0] == Decimal("427.10")

    def test_anchor_for_2023_06_07_is_2023_06_06_close(self) -> None:
        closes = _build_synthetic_continuous_closes()
        result = get_previous_regular_close("2023-06-07", closes)
        assert result == Decimal("430.00")

    def test_early_close_absent_from_continuous_lineage(self) -> None:
        closes = _build_early_close_continuous_closes()
        dates = [dt for dt, _ in closes]
        assert "2021-11-26" not in dates

    def test_early_close_follow_session_anchor_is_last_standard_session(self) -> None:
        closes = _build_early_close_continuous_closes()
        result = get_previous_regular_close("2021-11-29", closes)
        assert result == Decimal("469.37"), (
            f"Expected 469.37 (2021-11-24), got {result}"
        )


class TestNoiseAreaLineageInvariant:
    @pytest.fixture(autouse=True)
    def require_data(self) -> None:
        bars_path = REPO_ROOT / "data/hyp_007/m1_bars_qualified.parquet"
        if not bars_path.exists():
            pytest.skip("R2 Parquet data not available")

    def test_excluded_session_not_in_eligible_strategy_sessions(self) -> None:
        import pyarrow.parquet as pq
        bars_table = pq.read_table(REPO_ROOT / "data/hyp_007/m1_bars_qualified.parquet")
        sessions = set(bars_table.column("session_date").to_pylist())
        assert EXCLUDED_SESSION_DATE not in sessions

    def test_prior_14_for_2023_06_06_excludes_2023_06_05(self) -> None:
        import pyarrow.parquet as pq
        bars_table = pq.read_table(REPO_ROOT / "data/hyp_007/m1_bars_qualified.parquet")
        sessions = sorted(set(bars_table.column("session_date").to_pylist()))
        assert "2023-06-06" in sessions
        idx = sessions.index("2023-06-06")
        prior_14 = sessions[idx - 14 : idx]
        assert "2023-06-05" not in prior_14
        assert prior_14[-1] == "2023-06-02"

    def test_prior_14_last_is_defective_close_427_91(self) -> None:
        import pyarrow.parquet as pq
        bars_table = pq.read_table(REPO_ROOT / "data/hyp_007/m1_bars_qualified.parquet")
        pydict = {col: bars_table.column(col).to_pylist() for col in ["session_date", "close"]}
        bars_by_sess: dict[str, list[Decimal]] = {}
        for dt, c in zip(pydict["session_date"], pydict["close"]):
            bars_by_sess.setdefault(dt, []).append(Decimal(c))
        sessions = sorted(bars_by_sess.keys())
        idx = sessions.index("2023-06-06")
        prior_14 = sessions[idx - 14 : idx]
        defective_close = bars_by_sess[prior_14[-1]][-1]
        assert defective_close == Decimal("427.91")


class TestAdditiveSuperssesionArtifacts:
    @pytest.fixture(autouse=True)
    def require_corrected_artifacts(self) -> None:
        corrected_manifest = REPO_ROOT / "docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json"
        if not corrected_manifest.exists():
            pytest.skip("Corrected R3 artifacts not yet generated")

    def test_defective_original_manifest_still_exists(self) -> None:
        path = REPO_ROOT / "docs/phase14/manifests/manifest_r3_HYP_007.json"
        assert path.exists(), "Defective manifest deleted — immutability violation"

    def test_defective_terminal_decision_still_exists(self) -> None:
        path = REPO_ROOT / "docs/phase14/manifests/terminal_decision_HYP_007.json"
        assert path.exists()

    def test_defective_execution_report_still_exists(self) -> None:
        path = REPO_ROOT / "docs/research/MEC-0017-HYP-007-step-r3-execution-report.md"
        assert path.exists()

    def test_defective_dossier_still_exists(self) -> None:
        path = REPO_ROOT / "docs/phase14/hyp_007_terminal_m1_decision_dossier.md"
        assert path.exists()

    def test_corrected_manifest_has_supersedes_block(self) -> None:
        path = REPO_ROOT / "docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "supersedes" in data
        sup = data["supersedes"]
        assert sup["defective_commit_sha"] == DEFECTIVE_R3_COMMIT_SHA
        assert sup["defective_r3_result_package_sha256"] == DEFECTIVE_R3_RESULT_PACKAGE_SHA256
        assert sup["defective_terminal_decision_path"] == "docs/phase14/manifests/terminal_decision_HYP_007.json"
        assert sup["reason"] == DEFECTIVE_R3_DEFECT_CLASS

    def test_only_corrected_decision_marked_effective(self) -> None:
        corrected = REPO_ROOT / "docs/phase14/manifests/terminal_decision_HYP_007_CORRECTED_001.json"
        defective = REPO_ROOT / "docs/phase14/manifests/terminal_decision_HYP_007.json"
        corrected_data = json.loads(corrected.read_text(encoding="utf-8"))
        defective_data = json.loads(defective.read_text(encoding="utf-8"))
        assert corrected_data.get("effective_terminal_decision_after_correction") == "EFFECTIVE_AFTER_CORRECTION_001"
        assert "effective_terminal_decision_after_correction" not in defective_data

    def test_correction_manifest_immutable_artifacts_list(self) -> None:
        path = REPO_ROOT / "docs/phase14/manifests/HYP_007_R3_IMPLEMENTATION_CORRECTION_001.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        imm = data.get("immutable_defective_artifacts", {})
        assert "manifest_r3_HYP_007_json" in imm
        assert "terminal_decision_HYP_007_json" in imm
        assert "step_r3_execution_report_md" in imm
        assert "terminal_m1_decision_dossier_md" in imm

    def test_corrected_result_package_sha_differs_from_defective(self) -> None:
        corrected = REPO_ROOT / "docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json"
        data = json.loads(corrected.read_text(encoding="utf-8"))
        corrected_sha = data["scientific_result_digests"]["r3_result_package_sha256"]
        assert corrected_sha != DEFECTIVE_R3_RESULT_PACKAGE_SHA256

    def test_no_m2_access_in_corrected_manifest(self) -> None:
        path = REPO_ROOT / "docs/phase14/manifests/manifest_r3_HYP_007_CORRECTED_001.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["sample_boundary"]["m2_accessed"] is False
        assert data["governance_limits"]["m2_locked"] is True
