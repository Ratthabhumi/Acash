"""Research Manifest, Lineage Hashing, and Storage Engine (Phase 4).

Strictly enforces:
- Deterministic cryptographic hashing of HypothesisSpecification, ResearchSearchRecord, and Result artifacts.
- Atomic saving and loading of ResearchManifest.
- Blind OOS lifecycle validation.
"""

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Union, cast

from acash.data.schema import DataContractError
from acash.research.schema import (
    HypothesisSpecification,
    OosExposureState,
    ResearchManifest,
    ResearchSearchRecord,
)


def calculate_hypothesis_spec_sha256(spec: HypothesisSpecification) -> str:
    """Calculate deterministic SHA-256 fingerprint for a HypothesisSpecification."""
    json_str = spec.to_canonical_json()
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


def calculate_research_search_record_sha256(record: ResearchSearchRecord) -> str:
    """Calculate deterministic SHA-256 fingerprint for a ResearchSearchRecord."""
    json_str = record.to_canonical_json()
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()


class ResearchGovernanceLedger:
    """Durable ledger tracking OOS exposure state machine and research trial history."""

    def __init__(self, ledger_dir: Union[str, Path] = "data/manifests/research") -> None:
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_file = self.ledger_dir / "governance_ledger.json"
        self._init_ledger()

    def _init_ledger(self) -> None:
        if not self.ledger_file.exists():
            self._write_records({})

    def _read_records(self) -> Dict[str, Dict[str, Any]]:
        if not self.ledger_file.exists():
            return {}
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            return cast(Dict[str, Dict[str, Any]], json.load(f))


    def _write_records(self, records: Dict[str, Dict[str, Any]]) -> None:
        tmp_file = self.ledger_dir / f".tmp_ledger_{os.getpid()}.json"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, self.ledger_file)

    def get_oos_state(self, hypothesis_id: str) -> OosExposureState:
        records = self._read_records()
        if hypothesis_id not in records:
            return OosExposureState.UNEXPOSED
        return OosExposureState(records[hypothesis_id]["oos_state"])

    def record_oos_evaluation(
        self,
        hypothesis_id: str,
        search_record: ResearchSearchRecord,
        manifest_id: str,
    ) -> OosExposureState:
        records = self._read_records()
        current_state = OosExposureState(records.get(hypothesis_id, {}).get("oos_state", OosExposureState.UNEXPOSED.value))

        if current_state == OosExposureState.EVALUATED_LOCKED:
            records[hypothesis_id]["oos_state"] = OosExposureState.EXHAUSTED.value
            records[hypothesis_id]["exhausted_at_utc"] = datetime.now(timezone.utc).isoformat()
            self._write_records(records)
            raise DataContractError(
                f"Hypothesis '{hypothesis_id}' has already been evaluated against OOS (Manifest: {records[hypothesis_id].get('manifest_id')}). "
                f"Attempted re-evaluation violates blind OOS discipline. State is now EXHAUSTED."
            )
        elif current_state == OosExposureState.EXHAUSTED:
            raise DataContractError(
                f"Hypothesis '{hypothesis_id}' is permanently EXHAUSTED from previous unauthorized OOS re-evaluations."
            )

        records[hypothesis_id] = {
            "hypothesis_id": hypothesis_id,
            "oos_state": OosExposureState.EVALUATED_LOCKED.value,
            "first_evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
            "manifest_id": manifest_id,
            "search_record_hash": calculate_research_search_record_sha256(search_record),
            "total_effective_trials": search_record.total_effective_trials,
        }
        self._write_records(records)
        return OosExposureState.EVALUATED_LOCKED


class ResearchManifestEngine:
    """Manages storage and provenance validation of research manifests."""

    def __init__(self, manifests_dir: Union[str, Path] = "data/manifests/research") -> None:
        self.manifests_dir = Path(manifests_dir)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)
        self.governance_ledger = ResearchGovernanceLedger(ledger_dir=self.manifests_dir)

    def get_manifest_path(self, manifest_id: str) -> Path:
        """Derive canonical manifest file path."""
        norm_id = manifest_id.replace("/", "-").lower()
        return self.manifests_dir / f"research_manifest_{norm_id}.json"

    def save_research_manifest(self, manifest: ResearchManifest) -> Path:
        """Save a ResearchManifest atomically using temp file + fsync + os.replace."""
        target_path = self.get_manifest_path(manifest.manifest_id)
        temp_path = target_path.parent / f".tmp_{manifest.manifest_id}_{os.getpid()}.json"

        manifest_data = manifest.model_dump(mode="json")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, target_path)
        return target_path

    def load_research_manifest(self, manifest_id: str) -> Optional[ResearchManifest]:
        """Load an existing ResearchManifest."""
        target_path = self.get_manifest_path(manifest_id)
        if not target_path.exists():
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ResearchManifest.model_validate(data)

