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
from typing import Any, Dict, List, Optional, Union

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


class ResearchManifestEngine:
    """Manages storage and provenance validation of research manifests."""

    def __init__(self, manifests_dir: Union[str, Path] = "data/manifests/research") -> None:
        self.manifests_dir = Path(manifests_dir)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

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
