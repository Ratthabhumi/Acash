"""End-to-end qualification engine for historical SIP data qualification."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import uuid

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.client import (
    AlpacaAccessDeniedError,
    AlpacaAuthenticationError,
    AlpacaHistoricalSipClient,
    SipRetrievalResult,
)
from acash.data.qualification.guard import FifteenMinuteAccessGuard, ProtectedWindowViolationError
from acash.data.qualification.manifest import (
    build_sip_provenance_manifest,
    save_evidence_package,
    serialize_manifest_to_json,
)
from acash.data.qualification.models import (
    HistoricalSipBar,
    MarketDataFeed,
    PriceAdjustment,
    ProvenanceBasis,
    QualificationCheckStatus,
    QualityFinding,
    QualitySeverity,
    SipProvenanceManifest,
    SourceQualificationReport,
    SourceQualificationStatus,
    VwapAuthorityStatus,
)
from acash.data.qualification.session import VerifiedSessionSchedule
from acash.data.qualification.validator import HistoricalBarValidator


class HistoricalSipQualificationEngine:
    """Coordinates contract checks, network retrieval, data validation, and manifest generation."""

    def __init__(
        self,
        client: Optional[AlpacaHistoricalSipClient] = None,
        validator: Optional[HistoricalBarValidator] = None,
        guard: Optional[FifteenMinuteAccessGuard] = None,
    ) -> None:
        self.guard = guard or FifteenMinuteAccessGuard()
        self.client = client or AlpacaHistoricalSipClient(guard=self.guard)
        self.validator = validator or HistoricalBarValidator()

    def run_qualification(
        self,
        symbol: str,
        start_utc: datetime,
        end_utc: datetime,
        verified_schedules: Optional[Dict[date, VerifiedSessionSchedule]] = None,
        output_dir: Optional[Path] = None,
        manifest_id: Optional[str] = None,
        asof: Optional[str] = None,
    ) -> SourceQualificationReport:
        """Run complete source qualification workflow.

        Args:
            symbol: Ticker symbol (e.g. 'SPY').
            start_utc: Start boundary in UTC.
            end_utc: End boundary in UTC.
            verified_schedules: Optional certified session schedules.
            output_dir: Optional local directory to save the JSON manifest outside git.
            manifest_id: Optional custom manifest ID.
            asof: Optional symbol mapping as-of date (YYYY-MM-DD).

        Returns:
            SourceQualificationReport with decomposed sub-statuses and frozen manifest.
        """
        mid = manifest_id or f"SIP-QUAL-{symbol.upper()}-{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(timezone.utc).isoformat()
        start_str = start_utc.astimezone(timezone.utc).isoformat()
        end_str = end_utc.astimezone(timezone.utc).isoformat()

        req_status = QualificationCheckStatus.UNVERIFIED
        net_status = QualificationCheckStatus.UNVERIFIED
        integ_status = QualificationCheckStatus.UNVERIFIED
        prov_status = QualificationCheckStatus.UNVERIFIED

        findings: List[QualityFinding] = []
        bars: List[HistoricalSipBar] = []
        failure_reason: Optional[str] = None

        # 1. Evaluate Request Contract & Guard
        try:
            self.guard.validate_requested_end(end_utc)
            req_status = QualificationCheckStatus.PASS
        except ProtectedWindowViolationError as e:
            req_status = QualificationCheckStatus.FAIL
            failure_reason = f"Request contract violation: {e}"
            return self._build_terminal_report(
                manifest_id=mid,
                symbol=symbol,
                start_str=start_str,
                end_str=end_str,
                retrieval_ts=now_str,
                req_status=req_status,
                net_status=net_status,
                integ_status=integ_status,
                prov_status=prov_status,
                overall_status=SourceQualificationStatus.REJECTED,
                vwap_status=VwapAuthorityStatus.UNVERIFIED,
                findings=findings,
                bars=[],
                pages_metadata=[],
                pages_raw_bytes=[],
                feed_provenance="UNVERIFIED",
                failure_reason=failure_reason,
                output_dir=output_dir,
                asof=asof,
            )

        # 2. Network Retrieval
        retrieval: Optional[SipRetrievalResult] = None
        try:
            retrieval = self.client.fetch_historical_bars(
                symbol=symbol,
                start_utc=start_utc,
                end_utc=end_utc,
                feed=MarketDataFeed.SIP,
                adjustment=PriceAdjustment.RAW,
                timeframe="1Min",
                asof=asof,
            )
            net_status = QualificationCheckStatus.PASS
            bars = retrieval.bars
        except (AlpacaAuthenticationError, AlpacaAccessDeniedError) as e:
            net_status = QualificationCheckStatus.BLOCKED
            failure_reason = f"Access blocked: {e}"
            return self._build_terminal_report(
                manifest_id=mid,
                symbol=symbol,
                start_str=start_str,
                end_str=end_str,
                retrieval_ts=now_str,
                req_status=req_status,
                net_status=net_status,
                integ_status=integ_status,
                prov_status=prov_status,
                overall_status=SourceQualificationStatus.BLOCKED,
                vwap_status=VwapAuthorityStatus.UNVERIFIED,
                findings=findings,
                bars=[],
                pages_metadata=[],
                pages_raw_bytes=[],
                feed_provenance="UNVERIFIED",
                failure_reason=failure_reason,
                output_dir=output_dir,
                asof=asof,
            )
        except Exception as e:
            net_status = QualificationCheckStatus.FAIL
            failure_reason = f"Network or contract fetch failure: {e}"
            return self._build_terminal_report(
                manifest_id=mid,
                symbol=symbol,
                start_str=start_str,
                end_str=end_str,
                retrieval_ts=now_str,
                req_status=req_status,
                net_status=net_status,
                integ_status=integ_status,
                prov_status=prov_status,
                overall_status=SourceQualificationStatus.REJECTED,
                vwap_status=VwapAuthorityStatus.UNVERIFIED,
                findings=findings,
                bars=[],
                pages_metadata=[],
                pages_raw_bytes=[],
                feed_provenance="UNVERIFIED",
                failure_reason=failure_reason,
                output_dir=output_dir,
                asof=asof,
            )

        # 3. Data Integrity & Validation
        findings = self.validator.validate_bars(bars, verified_schedules=verified_schedules)
        if self.validator.has_blocking_errors(findings):
            integ_status = QualificationCheckStatus.FAIL
            failure_reason = "Data integrity checks failed with blocking errors."
        else:
            integ_status = QualificationCheckStatus.PASS

        # 4. Provider Provenance Check
        feed_provenance = retrieval.feed_response_provenance
        if feed_provenance == "FEED_CONFIRMED_IN_HEADER":
            prov_basis = ProvenanceBasis.RESPONSE_EXPLICIT
            prov_status = QualificationCheckStatus.PASS
        elif (
            retrieval.feed_requested == "sip"
            and retrieval.http_status_code == 200
            and req_status == QualificationCheckStatus.PASS
            and net_status == QualificationCheckStatus.PASS
            and integ_status == QualificationCheckStatus.PASS
        ):
            prov_basis = ProvenanceBasis.DOCUMENTED_API_CONTRACT
            prov_status = QualificationCheckStatus.PASS
        else:
            prov_basis = ProvenanceBasis.UNVERIFIED
            prov_status = QualificationCheckStatus.UNVERIFIED

        # 5. Determine Overall Qualification Status (Strict Ceiling Enforced)
        # DATA_SOURCE_TECHNICALLY_QUALIFIED requires ALL 4 to be PASS:
        # req_status == PASS, net_status == PASS, integ_status == PASS, prov_status == PASS
        if (
            req_status == QualificationCheckStatus.PASS
            and net_status == QualificationCheckStatus.PASS
            and integ_status == QualificationCheckStatus.PASS
        ):
            if prov_status == QualificationCheckStatus.PASS:
                overall_status = SourceQualificationStatus.DATA_SOURCE_TECHNICALLY_QUALIFIED
                vwap_status = VwapAuthorityStatus.QUALIFIED
            else:
                # Ceiling: cannot claim DATA_SOURCE_TECHNICALLY_QUALIFIED if provider provenance is not PASS
                overall_status = SourceQualificationStatus.CONTRACT_VERIFIED
                vwap_status = VwapAuthorityStatus.UNVERIFIED
        else:
            overall_status = SourceQualificationStatus.REJECTED
            vwap_status = VwapAuthorityStatus.UNVERIFIED

        warning_strings = [
            f"[{f.rule.value}] {f.message}" for f in findings if f.severity != QualitySeverity.ERROR
        ]

        manifest = build_sip_provenance_manifest(
            manifest_id=mid,
            symbol=symbol,
            feed_requested="sip",
            feed_response_provenance=feed_provenance,
            provenance_basis=prov_basis,
            timeframe="1Min",
            adjustment="raw",
            asof=asof,
            requested_start_utc=start_str,
            requested_end_utc=end_str,
            retrieval_timestamp_utc=now_str,
            pages_metadata=retrieval.pages_metadata,
            pages_raw_bytes=retrieval.pages_raw_bytes,
            bars=bars,
            source_qualification_status=overall_status,
            vwap_authority_status=vwap_status,
            warnings=warning_strings,
            failure_reason=failure_reason,
        )

        if output_dir is not None:
            evidence_dir = output_dir / mid
            save_evidence_package(
                evidence_dir=evidence_dir,
                manifest=manifest,
                pages_raw_bytes=retrieval.pages_raw_bytes,
            )

        return SourceQualificationReport(
            request_contract_status=req_status,
            network_access_status=net_status,
            data_integrity_status=integ_status,
            provider_provenance_status=prov_status,
            overall_status=overall_status,
            vwap_authority_status=vwap_status,
            manifest=manifest,
            findings=findings,
            bars_count=len(bars),
        )

    def _build_terminal_report(
        self,
        manifest_id: str,
        symbol: str,
        start_str: str,
        end_str: str,
        retrieval_ts: str,
        req_status: QualificationCheckStatus,
        net_status: QualificationCheckStatus,
        integ_status: QualificationCheckStatus,
        prov_status: QualificationCheckStatus,
        overall_status: SourceQualificationStatus,
        vwap_status: VwapAuthorityStatus,
        findings: List[QualityFinding],
        bars: List[HistoricalSipBar],
        pages_metadata: Sequence[Any],
        pages_raw_bytes: Sequence[bytes],
        feed_provenance: str,
        failure_reason: Optional[str],
        output_dir: Optional[Path],
        asof: Optional[str] = None,
        prov_basis: ProvenanceBasis = ProvenanceBasis.UNVERIFIED,
    ) -> SourceQualificationReport:
        manifest = build_sip_provenance_manifest(
            manifest_id=manifest_id,
            symbol=symbol,
            feed_requested="sip",
            feed_response_provenance=feed_provenance,
            provenance_basis=prov_basis,
            timeframe="1Min",
            adjustment="raw",
            asof=asof,
            requested_start_utc=start_str,
            requested_end_utc=end_str,
            retrieval_timestamp_utc=retrieval_ts,
            pages_metadata=pages_metadata,
            pages_raw_bytes=pages_raw_bytes,
            bars=bars,
            source_qualification_status=overall_status,
            vwap_authority_status=vwap_status,
            warnings=[],
            failure_reason=failure_reason,
        )
        if output_dir is not None:
            evidence_dir = output_dir / manifest_id
            if pages_raw_bytes and len(pages_raw_bytes) == len(pages_metadata):
                save_evidence_package(
                    evidence_dir=evidence_dir,
                    manifest=manifest,
                    pages_raw_bytes=pages_raw_bytes,
                )
            else:
                evidence_dir.mkdir(parents=True, exist_ok=True)
                manifest_path = evidence_dir / "manifest.json"
                manifest_path.write_text(serialize_manifest_to_json(manifest), encoding="utf-8")

        return SourceQualificationReport(
            request_contract_status=req_status,
            network_access_status=net_status,
            data_integrity_status=integ_status,
            provider_provenance_status=prov_status,
            overall_status=overall_status,
            vwap_authority_status=vwap_status,
            manifest=manifest,
            findings=findings,
            bars_count=len(bars),
        )
