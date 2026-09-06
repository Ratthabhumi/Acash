"""Unit and Invariant Tests for Phase 8.5 Step R3: In-Sample Search Trial Census & Screening.

Strictly verifies:
- R1 hypothesis integrity and immutable cryptographic lineage.
- SearchTrialLedger sealed state, 9/9 trial census completeness, and ledger digest match.
- In-sample data isolation (bars 0 to 5,999 strictly; bars >= 6,000 unexposed).
- Return series cryptographic integrity (SHA-256 match for all 9 trials).
- Canonical p-value single authority and p_value_input_hash binding.
- Anti-HARKing: All 9 trials evaluated honestly against pre-registered invalidation criteria.
"""

from decimal import Decimal
import json
from pathlib import Path
import numpy as np
import pytest
import pyarrow.parquet as pq

from acash.research.manifest import calculate_hypothesis_spec_sha256
from acash.research.schema import HypothesisSpecification
from acash.validation.gate import _compute_canonical_series_sha256
from acash.validation.schema import (
    SearchTrialLedger,
    SearchTrialRecord,
    SharpeSpace,
)


@pytest.fixture
def sealed_r3_ledger() -> SearchTrialLedger:
    """Load and validate the sealed Step R3 SearchTrialLedger."""
    ledger_path = Path("data/manifests/research/search_trial_ledger_HYP_TSMOM_EURUSD_001.json")
    assert ledger_path.exists(), f"Ledger file not found at {ledger_path}"

    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ledger = SearchTrialLedger.model_validate(data)
    return ledger


def test_r3_upstream_hypothesis_integrity() -> None:
    """Verify that R3 is bound to the genuine, unmodified R1 hypothesis."""
    hyp_path = Path("docs/phase8.5/hypotheses/HYP_TSMOM_EURUSD_001.json")
    with open(hyp_path, "r", encoding="utf-8") as f:
        hyp_data = json.load(f)

    spec = HypothesisSpecification.model_validate(hyp_data)
    digest = calculate_hypothesis_spec_sha256(spec)
    expected_digest = "5afb92d7175721872d51ab82b2ebaaaa353c2d21bcbbd596e8bf1a3c52de0ef4"
    assert digest == expected_digest, f"Hypothesis digest mismatch: {digest} != {expected_digest}"


def test_r3_ledger_sealing_and_digest(sealed_r3_ledger: SearchTrialLedger) -> None:
    """Verify that SearchTrialLedger is sealed and its cryptographic digest is mathematically exact."""
    assert sealed_r3_ledger.is_sealed is True
    assert sealed_r3_ledger.sealed_at_utc is not None
    assert sealed_r3_ledger.ledger_digest is not None

    recomputed_digest = sealed_r3_ledger.compute_ledger_digest()
    assert sealed_r3_ledger.ledger_digest == recomputed_digest, (
        f"Sealed ledger digest mismatch: stored {sealed_r3_ledger.ledger_digest} != recomputed {recomputed_digest}"
    )


def test_r3_complete_9_trial_census(sealed_r3_ledger: SearchTrialLedger) -> None:
    """Verify that the ledger contains the exact 9 pre-registered lookback trials (no additions, no omissions)."""
    expected_lookbacks = [2, 3, 5, 8, 13, 21, 34, 55, 89]
    assert len(sealed_r3_ledger.trials) == 9

    ledger_lookbacks = [t.parameters["lookback_bars"] for t in sealed_r3_ledger.trials]
    assert ledger_lookbacks == expected_lookbacks

    trial_ids = [t.trial_id for t in sealed_r3_ledger.trials]
    expected_ids = [f"trial_tsmom_eurusd_m5_l{L:02d}" for L in expected_lookbacks]
    assert trial_ids == expected_ids


def test_r3_data_isolation_in_sample_strictly(sealed_r3_ledger: SearchTrialLedger) -> None:
    """Verify that trial returns are derived strictly from in-sample bars (length <= 6,000)."""
    trials_dir = Path("data/parquet/research/trials")
    assert trials_dir.exists()

    for trial in sealed_r3_ledger.trials:
        ret_path = trials_dir / f"returns_{trial.trial_id}.parquet"
        assert ret_path.exists(), f"Return series parquet not found for {trial.trial_id}"

        table = pq.read_table(ret_path)
        # Returns must have at most 6000 - L rows
        L = trial.parameters["lookback_bars"]
        expected_rows = 6000 - 1 - L
        assert table.num_rows == expected_rows, f"Trial {trial.trial_id} row count {table.num_rows} != {expected_rows}"

        # Verify timestamp bounds: max timestamp must be strictly <= 2026-08-17 23:40 UTC
        ts = table["timestamp_utc"].to_pylist()
        assert ts[0].isoformat() >= "2026-07-20T03:40:00+00:00"
        assert ts[-1].isoformat() <= "2026-08-17T23:40:00+00:00"



def test_r3_return_series_sha256_integrity(sealed_r3_ledger: SearchTrialLedger) -> None:
    """Verify bit-for-bit SHA-256 match between stored trial return hashes and actual series data."""
    trials_dir = Path("data/parquet/research/trials")

    for trial in sealed_r3_ledger.trials:
        ret_path = trials_dir / f"returns_{trial.trial_id}.parquet"
        table = pq.read_table(ret_path)

        returns_dec = [Decimal(str(v)) for v in table["strategy_return"].to_pylist()]
        recomputed_hash = _compute_canonical_series_sha256(returns_dec)

        assert trial.in_sample_return_series_sha256 == recomputed_hash, (
            f"Trial {trial.trial_id} return hash mismatch: stored {trial.in_sample_return_series_sha256} != recomputed {recomputed_hash}"
        )


def test_r3_canonical_p_value_and_input_hash_binding(sealed_r3_ledger: SearchTrialLedger) -> None:
    """Verify that canonical p-values and p_value_input_hash are verified and mathematically bound."""
    for trial in sealed_r3_ledger.trials:
        expected_p_hash = SearchTrialRecord.compute_p_value_input_hash(
            return_series_sha256=trial.in_sample_return_series_sha256,
            config_sha256=trial.config_sha256,
            p_value=trial.p_value,
            p_value_method=trial.p_value_method,
        )
        assert trial.p_value_input_hash == expected_p_hash, (
            f"Trial {trial.trial_id} p_value_input_hash mismatch!"
        )


def test_r3_anti_harking_census_accounting() -> None:
    """Verify that all 9 trials are documented in the census manifest and none were pruned."""
    census_manifest_path = Path("data/manifests/research/manifest_census_HYP_TSMOM_EURUSD_001.json")
    assert census_manifest_path.exists()

    with open(census_manifest_path, "r", encoding="utf-8") as f:
        census = json.load(f)

    assert census["search_space"]["nominal_trials_k"] == 9
    assert census["search_space"]["effective_trials_k"] == 9
    assert len(census["census_trials"]) == 9
    assert census["ledger_summary"]["total_trials"] == 9

    # Confirm all 9 trials are accounted for
    for item in census["census_trials"]:
        assert item["falsification_verdict"] in ["PASS", "FALSIFIED"]
        # Empirical truth: for EURUSD M5, all short lookbacks exhibit negative Rank IC
        assert item["h1_metrics"]["spearman_rank_ic"] < 0.025
        assert item["falsification_verdict"] == "FALSIFIED"
