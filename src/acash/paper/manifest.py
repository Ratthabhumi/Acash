"""ACASH Paper Trading — Paper Session Manifest.

PaperSessionManifest seals a complete paper trading session with:
- Cryptographic lineage (git commit, config hash, strategy version)
- Environment metadata
- Journal integrity status
- Reconciliation status
- Final portfolio state
- Explicit PAPER ONLY / NO REAL ORDERS labeling

The manifest MUST be:
1. Generated at session END (not mid-session)
2. Hash-sealed against the final journal state
3. Stored permanently for audit

This manifest does NOT constitute:
- Strategy validation
- Statistical qualification
- Capital authorization
- Any change to MACRO-001 governance
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acash.core.domain.exceptions import DataContractError
from acash.core.serialization import CanonicalConfigSerializer


# ---------------------------------------------------------------------------
# PaperMode — explicit mode labeling
# ---------------------------------------------------------------------------


class PaperMode:
    """Explicit constants for paper mode labeling."""

    PAPER_ONLY = "PAPER_ONLY"
    NO_REAL_ORDERS = "NO_REAL_ORDERS"
    SIMULATED_FILLS = "SIMULATED_FILLS"
    GOVERNANCE_LABEL = "PAPER_TRADING_INFRASTRUCTURE_TEST"


# ---------------------------------------------------------------------------
# PaperSessionManifest
# ---------------------------------------------------------------------------


class PaperSessionManifest(BaseModel):
    """Immutable sealed manifest for a completed paper trading session.

    This document attests:
    - PAPER ONLY — no real orders were placed
    - All events are simulated
    - Cryptographic lineage of strategy, config, and journal
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    session_id: str = Field(description="Paper trading session identifier.")
    manifest_id: str = Field(description="Unique identifier for this manifest.")

    # EXPLICIT PAPER LABELING
    mode: str = Field(
        default=PaperMode.PAPER_ONLY,
        description="MUST be 'PAPER_ONLY'. Any non-paper value is rejected.",
    )
    no_real_orders: bool = Field(
        default=True,
        description="MUST be True. Attests no real broker orders were placed.",
    )
    simulated_fills_only: bool = Field(
        default=True,
        description="MUST be True. Attests all fills are simulated.",
    )
    governance_label: str = Field(
        default=PaperMode.GOVERNANCE_LABEL,
        description="Governance classification label.",
    )

    # Strategy provenance
    strategy_id: str = Field(description="Strategy identifier used in this session.")
    strategy_version: str = Field(description="Strategy semantic version.")
    is_infrastructure_test_strategy: bool = Field(
        description="True if strategy is INFRASTRUCTURE_TEST_STRATEGY_ONLY."
    )

    # Cryptographic lineage
    git_commit: str = Field(description="Repository git commit SHA at session start.")
    config_hash: str = Field(description="SHA-256 of merged runtime + cost model configuration.")
    strategy_config_hash: str = Field(description="SHA-256 of strategy-specific configuration.")
    journal_final_hash: str = Field(
        description="SHA-256 hash of the last committed journal event (chain tip)."
    )

    # Market data
    data_source: str = Field(description="Market data feed classification.")
    instrument_universe: List[str] = Field(description="List of instruments traded.")
    market_domain: str = Field(description="Market domain (e.g., TRADITIONAL_FX, EQUITY).")

    # Fill / Risk model
    fill_model_version: str = Field(description="Fill/execution cost model version.")
    risk_model_version: str = Field(description="Risk model version.")

    # Timing
    start_time_utc: datetime = Field(description="Session start time (UTC).")
    end_time_utc: datetime = Field(description="Session end time (UTC).")

    # Counts
    total_event_count: int = Field(ge=0, description="Total events in journal.")
    total_warning_count: int = Field(ge=0, description="Total warning events.")
    total_error_count: int = Field(ge=0, description="Total error events.")
    total_trade_count: int = Field(ge=0, description="Total simulated trades.")
    total_order_count: int = Field(ge=0, description="Total orders submitted.")
    total_rejected_order_count: int = Field(ge=0, description="Total orders rejected.")

    # Final state (summary — structured payload)
    final_portfolio_summary: Dict[str, Any] = Field(
        description="Summary of final portfolio state (cash, equity, positions, P&L)."
    )
    final_reconciliation_status: str = Field(
        description="Final reconciliation status (PASS / FAIL / PARTIAL)."
    )
    journal_integrity_status: str = Field(
        description="Final journal integrity check status (PASS / FAIL / NOT_CHECKED)."
    )

    # Manifest integrity
    manifest_hash: str = Field(
        description="SHA-256 of this manifest's canonical fields (excluding manifest_hash itself)."
    )
    sealed_at_utc: datetime = Field(description="UTC timestamp when manifest was sealed.")

    @field_validator("mode")
    @classmethod
    def validate_paper_mode(cls, v: str) -> str:
        if v != PaperMode.PAPER_ONLY:
            raise DataContractError(
                f"PaperSessionManifest: mode must be 'PAPER_ONLY', got: {v!r}. "
                "Live mode is NOT permitted in this manifest type."
            )
        return v

    @model_validator(mode="after")
    def validate_paper_assertions(self) -> "PaperSessionManifest":
        if not self.no_real_orders:
            raise DataContractError(
                "PaperSessionManifest: no_real_orders must be True."
            )
        if not self.simulated_fills_only:
            raise DataContractError(
                "PaperSessionManifest: simulated_fills_only must be True."
            )
        if self.end_time_utc <= self.start_time_utc:
            raise DataContractError(
                "PaperSessionManifest: end_time_utc must be after start_time_utc."
            )
        return self

    @staticmethod
    def compute_manifest_hash(
        session_id: str,
        manifest_id: str,
        strategy_id: str,
        strategy_version: str,
        git_commit: str,
        config_hash: str,
        journal_final_hash: str,
        start_time_utc: datetime,
        end_time_utc: datetime,
        total_event_count: int,
        final_reconciliation_status: str,
        journal_integrity_status: str,
    ) -> str:
        """Compute the canonical hash for this manifest."""
        canonical = {
            "session_id": session_id,
            "manifest_id": manifest_id,
            "strategy_id": strategy_id,
            "strategy_version": strategy_version,
            "git_commit": git_commit,
            "config_hash": config_hash,
            "journal_final_hash": journal_final_hash,
            "start_time_utc": start_time_utc.isoformat(),
            "end_time_utc": end_time_utc.isoformat(),
            "total_event_count": total_event_count,
            "final_reconciliation_status": final_reconciliation_status,
            "journal_integrity_status": journal_integrity_status,
            "mode": PaperMode.PAPER_ONLY,
            "no_real_orders": True,
        }
        canonical_bytes = CanonicalConfigSerializer.to_canonical_json(
            canonical
        ).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @classmethod
    def seal(
        cls,
        *,
        session_id: str,
        manifest_id: str,
        strategy_id: str,
        strategy_version: str,
        is_infrastructure_test_strategy: bool,
        git_commit: str,
        config_hash: str,
        strategy_config_hash: str,
        journal_final_hash: str,
        data_source: str,
        instrument_universe: List[str],
        market_domain: str,
        fill_model_version: str,
        risk_model_version: str,
        start_time_utc: datetime,
        end_time_utc: datetime,
        total_event_count: int,
        total_warning_count: int,
        total_error_count: int,
        total_trade_count: int,
        total_order_count: int,
        total_rejected_order_count: int,
        final_portfolio_summary: Dict[str, Any],
        final_reconciliation_status: str,
        journal_integrity_status: str,
    ) -> "PaperSessionManifest":
        """Seal a paper trading session manifest.

        This is the ONLY authorized constructor for PaperSessionManifest.
        """
        now_utc = datetime.now(timezone.utc)

        manifest_hash = cls.compute_manifest_hash(
            session_id=session_id,
            manifest_id=manifest_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            git_commit=git_commit,
            config_hash=config_hash,
            journal_final_hash=journal_final_hash,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            total_event_count=total_event_count,
            final_reconciliation_status=final_reconciliation_status,
            journal_integrity_status=journal_integrity_status,
        )

        return cls(
            session_id=session_id,
            manifest_id=manifest_id,
            mode=PaperMode.PAPER_ONLY,
            no_real_orders=True,
            simulated_fills_only=True,
            governance_label=PaperMode.GOVERNANCE_LABEL,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            is_infrastructure_test_strategy=is_infrastructure_test_strategy,
            git_commit=git_commit,
            config_hash=config_hash,
            strategy_config_hash=strategy_config_hash,
            journal_final_hash=journal_final_hash,
            data_source=data_source,
            instrument_universe=list(instrument_universe),
            market_domain=market_domain,
            fill_model_version=fill_model_version,
            risk_model_version=risk_model_version,
            start_time_utc=start_time_utc,
            end_time_utc=end_time_utc,
            total_event_count=total_event_count,
            total_warning_count=total_warning_count,
            total_error_count=total_error_count,
            total_trade_count=total_trade_count,
            total_order_count=total_order_count,
            total_rejected_order_count=total_rejected_order_count,
            final_portfolio_summary=final_portfolio_summary,
            final_reconciliation_status=final_reconciliation_status,
            journal_integrity_status=journal_integrity_status,
            manifest_hash=manifest_hash,
            sealed_at_utc=now_utc,
        )
