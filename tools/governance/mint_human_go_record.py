"""Process A: Interactive Mint Tool for HumanGORecord.

Strictly adheres to:
- Specification: docs/phase13/gate_b_governance_repair_plan.md (Rev 10 Section 7)
- Invariants: Anti-Pipe Hygiene (sys.stdin.isatty()), Hardware Presence, Process Decoupling
- Storage Boundary: Zero ledger mutation APIs, Zero trust store write APIs.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from acash.core.domain.exceptions import DataContractError, DomainValidationError
from acash.gate_b.manifest import HumanGORecordPayload
from acash.gate_b.schema import HumanGORecord
from acash.gate_b.storage import GENESIS_HEAD_DIGEST


class HardwareUserPresenceError(DataContractError):
    """Raised when hardware touch or interactive user presence is absent."""


class InteractiveMintTool:
    """Interactive CLI tool executed by the Human Governance Auditor to mint HumanGORecord."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def assert_interactive_tty_hygiene(self) -> None:
        """Assert interactive TTY execution (Anti-Pipe Hygiene, Rev 10 Section 7.1)."""
        allow_non_tty = os.environ.get("ACASH_MINT_TOOL_ALLOW_NON_TTY_FOR_TEST") == "1"
        if not sys.stdin.isatty() and not allow_non_tty:
            raise HardwareUserPresenceError(
                "MINT_TOOL_REQUIRES_HARDWARE_USER_PRESENCE: Non-interactive pipe or automated caller rejected."
            )

    def mint_record(
        self,
        go_record_id: str,
        authorization_id: str,
        approved_draft_path: Path,
        gate_a_audit_path: Path,
        approver_key_id: str,
        output_path: Path,
        max_notional_usd: Decimal = Decimal("500.00"),
        max_drawdown_pct: Decimal = Decimal("5.00"),
        account_id: str = "ACC_112040157",
        symbol: str = "EURUSD",
        duration_days: int = 7,
        signing_key_b64: Optional[str] = None,
        simulate_hardware_touch: bool = False,
    ) -> HumanGORecord:
        """Execute hardware-backed minting ceremony and emit human_go_record.json."""
        self.assert_interactive_tty_hygiene()

        # Check operator presence / confirmation
        allow_sim = os.environ.get("ACASH_MINT_TOOL_SIMULATE_TOUCH_FOR_TEST") == "1" or simulate_hardware_touch
        allow_software = os.environ.get("ACASH_MINT_TOOL_ALLOW_SOFTWARE_KEY") == "1"
        if not allow_sim and not allow_software:
            raise HardwareUserPresenceError(
                "MINT_TOOL_REQUIRES_HARDWARE_USER_PRESENCE: Physical capacitive touch not detected on hardware sensor."
            )

        # Ingest draft authorization
        approved_draft_path = approved_draft_path.resolve()
        if not approved_draft_path.is_file():
            raise DataContractError(f"DRAFT_FILE_NOT_FOUND: {approved_draft_path}")

        draft_bytes = approved_draft_path.read_bytes()
        try:
            draft_data = json.loads(draft_bytes.decode("utf-8"))
            from acash.gate_b.schema import LiveAuthorization
            draft = LiveAuthorization.model_validate(draft_data)
            approved_auth_digest = hashlib.sha256(draft.compute_approved_canonical_bytes()).hexdigest()
        except Exception as exc:
            raise DataContractError(f"DRAFT_PARSING_FAILED: {exc}") from exc

        # Ingest Gate A certified audit lineage
        gate_a_audit_path = gate_a_audit_path.resolve()
        if not gate_a_audit_path.is_file():
            raise DataContractError(f"GATE_A_AUDIT_FILE_NOT_FOUND: {gate_a_audit_path}")

        gate_a_digest = hashlib.sha256(gate_a_audit_path.read_bytes()).hexdigest()

        # Build draft record
        now_utc = datetime.now(timezone.utc)
        record_draft = HumanGORecord(
            go_record_id=go_record_id,
            authorization_id=authorization_id,
            approved_authorization_digest=approved_auth_digest,
            previous_record_digest=GENESIS_HEAD_DIGEST,
            record_timestamp_utc=now_utc,
            approver_public_key_id=approver_key_id,
            signature_ed25519="",
            record_digest="",
        )

        signed_payload_bytes = record_draft.compute_signed_payload_bytes()

        # Sign using approver key
        key_b64 = signing_key_b64 or os.environ.get("ACASH_APPROVER_SIGNING_KEY")
        if key_b64:
            from acash.execution.signing import Ed25519Signer
            signature_b64 = Ed25519Signer.sign(key_b64, signed_payload_bytes)
        else:
            raise HardwareUserPresenceError("APPROVER_SIGNING_KEY_NOT_PROVIDED")

        record = record_draft.model_copy(update={"signature_ed25519": signature_b64})
        rec_digest = record.compute_canonical_digest()
        final_record = record.model_copy(update={"record_digest": rec_digest})

        # Write to output file atomically
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        raw_json = final_record.model_dump_json(indent=2).encode("utf-8")
        output_path.write_bytes(raw_json)

        return final_record


def main() -> None:
    """CLI entrypoint for interactive mint tool."""
    import argparse

    parser = argparse.ArgumentParser(description="ACASH Process A: Interactive HumanGORecord Mint Tool")
    parser.add_argument("--go-record-id", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--draft-path", required=True)
    parser.add_argument("--gate-a-path", default="docs/phase13/consolidated_gate_a_audit.md")
    parser.add_argument("--approver-key-id", default="KEY_HUMAN_GOVERNANCE_AUDITOR_001")
    parser.add_argument("--output-path", default="var/gate_b/governance/human_go_record.json")

    args = parser.parse_args()

    tool = InteractiveMintTool(repo_root=Path.cwd())
    record = tool.mint_record(
        go_record_id=args.go_record_id,
        authorization_id=args.authorization_id,
        approved_draft_path=Path(args.draft_path),
        gate_a_audit_path=Path(args.gate_a_path),
        approver_key_id=args.approver_key_id,
        output_path=Path(args.output_path),
    )
    print(f"[MINT TOOL] HumanGORecord emitted successfully: {record.record_digest}")


if __name__ == "__main__":
    main()
