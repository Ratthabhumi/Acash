"""Offline Scope -> D5-candidate acquisition harness (httpx.MockTransport ONLY).

Composes existing reviewed pieces without duplicating them:

- D5 request identity (``expected_d5_request_sha256``) and D5 qualification
  (``evaluate_d5_real_admission``);
- ``CanaryBudget`` (operation/byte budget) and ``ReservationJournal``
  (reserve-before-dispatch, no refund);
- ``DurableAttemptJournal`` lifecycle, ``store_raw_evidence`` and
  ``verify_evidence_pair`` (create-once raw/receipt pairs);
- D3 V2 strict identity streaming (``read_identity_capped_v2``) under one
  run-wide ``StreamingByteCap``;
- ``check_request_allowlist`` and the D3 budget simulation (planning floor).

Only synthetic fixture authorities are accepted and the sealed output is a
``SYNTHETIC_PIPELINE_PROOF``: a successful run proves pipeline mechanics, not
market history, PIT evidence, rights, or acquisition authority. Any failure
propagates without closing the run, leaving it INTERRUPTED (never COMPLETE);
the run id cannot be reused. No retry, no fallback feed, no budget refund.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping

import httpx

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.d3_budget_simulation import (
    BudgetScenario,
    simulate_bars_budget,
)
from acash.data.qualification.lane_a_canary import CanaryBudget, ReservationJournal
from acash.data.qualification.lane_a_d1_safety import StreamingByteCap
from acash.data.qualification.lane_a_d3_streaming import read_identity_capped_v2
from acash.data.qualification.lane_a_transport import (
    ALLOWED_HOSTS,
    ALLOWED_PATHS,
    JOURNAL_DIRNAME,
    DurableAttemptJournal,
    check_request_allowlist,
    store_raw_evidence,
    verify_evidence_pair,
)
from acash.data.qualification.lane_b_d5_rehearsal import (
    D5AdmissionAuthority,
    D5AdmissionResult,
    D5AuthorityProvenance,
    D5DividendRecord,
    D5EvidenceLevel,
    D5InputOrigin,
    D5RawPage,
    D5RealInputBundle,
    evaluate_d5_real_admission,
    expected_d5_request_sha256,
)
from acash.core.serialization import CanonicalConfigSerializer

HARNESS_SCHEMA = "ACASH_D5_OFFLINE_HARNESS_V1"
HARNESS_LABEL = "SYNTHETIC_VERIFICATION_NOT_MARKET_HISTORY"
D5_HARNESS_LIMIT = 1000
D5_HARNESS_ADJUSTMENTS: tuple[str, ...] = ("raw", "split")
_STOP_STATUS = {401: "HTTP_401", 403: "HTTP_403", 429: "HTTP_429"}
_PLANNING_FLOOR = BudgetScenario("PLANNING_FLOOR", D5_HARNESS_LIMIT, 1, 0, 0)


def _sha256_json(document: Mapping[str, Any]) -> str:
    canonical = CanonicalConfigSerializer.to_canonical_json(dict(document))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class D5HarnessScope:
    """Frozen synthetic acquisition scope; ``asof`` must be an explicit date."""

    authority: D5AdmissionAuthority
    asof: date
    dividends: tuple[D5DividendRecord, ...]
    expected_ex_dates: Mapping[str, tuple[date, ...]]

    def __post_init__(self) -> None:
        if self.authority.provenance is not D5AuthorityProvenance.TEST_FIXTURE:
            raise DataContractError(
                "D5_HARNESS_REAL_AUTHORITY_REFUSED: the offline harness accepts "
                "only TEST_FIXTURE authorities."
            )
        if tuple(self.authority.adjustments) != D5_HARNESS_ADJUSTMENTS:
            raise DataContractError(
                f"D5_HARNESS_ADJUSTMENTS_NOT_FROZEN: {self.authority.adjustments!r}."
            )
        if not isinstance(self.asof, date) or isinstance(self.asof, datetime):
            raise DataContractError(
                "D5_HARNESS_ASOF_NOT_FROZEN: asof must be an explicit calendar date."
            )
        if self.asof < self.authority.end_date:
            raise DataContractError("D5_HARNESS_ASOF_BEFORE_SCOPE_END.")

    def digest(self) -> str:
        return _sha256_json(
            {
                "schema": HARNESS_SCHEMA,
                "authority_sha256": self.authority.digest(),
                "asof": self.asof.isoformat(),
                "limit": D5_HARNESS_LIMIT,
                "adjustments": list(D5_HARNESS_ADJUSTMENTS),
            }
        )


@dataclass(frozen=True)
class D5HarnessReceipt:
    seq: int
    evidence_name: str
    adjustment: str
    page_index: int
    request_sha256: str
    url_sha256: str
    content_sha256: str
    receipt_sha256: str
    byte_count: int


@dataclass(frozen=True)
class D5HarnessResult:
    run_id: str
    scope_sha256: str
    planned_min_requests: int
    operations_used: int
    bytes_observed: int
    receipts: tuple[D5HarnessReceipt, ...]
    admission: D5AdmissionResult
    manifest: Mapping[str, Any]
    manifest_sha256: str


def build_d5_request(
    scope: D5HarnessScope, adjustment: str, page_token: str | None
) -> httpx.Request:
    """Frozen, credential-free request for one page (identity encoding only)."""
    authority = scope.authority
    params: list[tuple[str, str | int | float | bool | None]] = [
        ("symbols", ",".join(authority.symbols)),
        ("timeframe", authority.timeframe),
        ("start", authority.start_date.isoformat()),
        ("end", authority.end_date.isoformat()),
        ("adjustment", adjustment),
        ("feed", authority.feed),
        ("asof", scope.asof.isoformat()),
        ("sort", "asc"),
        ("limit", str(D5_HARNESS_LIMIT)),
    ]
    if page_token is not None:
        params.append(("page_token", page_token))
    request = httpx.Request(
        "GET",
        f"https://{ALLOWED_HOSTS[0]}{ALLOWED_PATHS[0]}",
        params=params,
        headers={"accept-encoding": "identity"},
    )
    check_request_allowlist(request.url.host, request.method, request.url.path)
    return request


def _parse_next_token(body: bytes) -> str | None:
    try:
        document = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise DataContractError("D5_HARNESS_MALFORMED_PAGE: body is not UTF-8 JSON.") from exc
    if not isinstance(document, dict) or "bars" not in document or "next_page_token" not in document:
        raise DataContractError("D5_HARNESS_MALFORMED_PAGE: missing bars/next_page_token.")
    token = document["next_page_token"]
    if token is not None and (not isinstance(token, str) or not token):
        raise DataContractError("D5_HARNESS_MALFORMED_PAGE: bad next_page_token.")
    return token


def run_d5_offline_harness(
    scope: D5HarnessScope,
    transport: httpx.MockTransport,
    *,
    evidence_root: Path,
    run_id: str,
    runtime_sha: str,
    created_at_utc: str,
) -> D5HarnessResult:
    """Run Scope -> reservation -> mock HTTP -> receipts -> D5 candidate, fail-closed."""
    if type(transport) is not httpx.MockTransport:
        raise DataContractError(
            "D5_HARNESS_NETWORK_REFUSED: only httpx.MockTransport is permitted."
        )
    authority = scope.authority
    planned = simulate_bars_budget(
        symbols=authority.symbols,
        start=authority.start_date,
        end=authority.end_date,
        adjustments=D5_HARNESS_ADJUSTMENTS,
        scenario=_PLANNING_FLOOR,
        max_http_requests=authority.max_http_requests,
        max_observed_bytes=authority.max_observed_bytes,
    )
    if not planned.within_request_ceiling:
        raise DataContractError(
            f"D5_HARNESS_BUDGET_INSUFFICIENT: at least {planned.requests} requests "
            f"needed at limit={D5_HARNESS_LIMIT}; authority allows "
            f"{authority.max_http_requests}."
        )
    scope_sha = scope.digest()
    lifecycle = DurableAttemptJournal.create_run(
        root=evidence_root,
        run_id=run_id,
        authority_ref=authority.authority_ref,
        runtime_sha=runtime_sha,
        created_at_utc=created_at_utc,
    )
    run_dir = lifecycle._run_dir  # noqa: SLF001 — same-package composition
    journal = ReservationJournal.create(run_dir)
    budget = CanaryBudget(authority.max_http_requests, authority.max_observed_bytes)
    cap = StreamingByteCap(authority.max_observed_bytes)
    pages: list[D5RawPage] = []
    receipts: list[D5HarnessReceipt] = []
    seq = 0
    with httpx.Client(transport=transport, follow_redirects=False) as client:
        for adjustment in D5_HARNESS_ADJUSTMENTS:
            token: str | None = None
            seen_tokens: set[str] = set()
            page_index = 0
            while True:
                request_sha = expected_d5_request_sha256(authority, adjustment, token)
                seq += 1
                budget.reserve_operation()
                journal.reserve(seq, request_sha)
                request = build_d5_request(scope, adjustment, token)
                response = client.send(request, stream=True)
                try:
                    if response.status_code in _STOP_STATUS:
                        journal.settle(seq, _STOP_STATUS[response.status_code])
                        budget.halt(_STOP_STATUS[response.status_code])
                        raise DataContractError(
                            f"D5_HARNESS_HALTED_{_STOP_STATUS[response.status_code]}."
                        )
                    if response.status_code != 200:
                        raise DataContractError(
                            f"D5_HARNESS_UNEXPECTED_STATUS: {response.status_code}."
                        )
                    body, content_sha = read_identity_capped_v2(response, cap)
                finally:
                    response.close()
                budget.observe_bytes(len(body))
                journal.settle(seq, "OK")
                next_token = _parse_next_token(body)
                evidence_name = f"seq_{seq:04d}"
                stored = store_raw_evidence(
                    root=evidence_root,
                    run_id=run_dir.name,
                    name=evidence_name,
                    payload=body,
                    metadata={
                        "feed": authority.feed,
                        "timeframe": authority.timeframe,
                        "adjustment": adjustment,
                        "symbols": ",".join(authority.symbols),
                        "page_index": page_index,
                        "request_index": seq,
                        "byte_count": len(body),
                        "request_digest": request_sha,
                        "note": f"asof={scope.asof.isoformat()};scope={scope_sha}",
                    },
                )
                if stored["content_sha256"] != content_sha:
                    raise DataContractError("D5_HARNESS_RECEIPT_DIGEST_MISMATCH.")
                receipts.append(
                    D5HarnessReceipt(
                        seq=seq,
                        evidence_name=evidence_name,
                        adjustment=adjustment,
                        page_index=page_index,
                        request_sha256=request_sha,
                        url_sha256=hashlib.sha256(str(request.url).encode("utf-8")).hexdigest(),
                        content_sha256=content_sha,
                        receipt_sha256=str(stored["receipt_sha256"]),
                        byte_count=len(body),
                    )
                )
                pages.append(
                    D5RawPage(
                        adjustment=adjustment,
                        page_index=page_index,
                        page_token=token,
                        next_page_token=next_token,
                        request_sha256=request_sha,
                        content_sha256=content_sha,
                        raw_bytes=body,
                    )
                )
                if next_token is None:
                    break
                if next_token in seen_tokens or next_token == token:
                    raise DataContractError(
                        f"D5_HARNESS_PAGE_TOKEN_CYCLE: {adjustment} chain repeats a token."
                    )
                seen_tokens.add(next_token)
                token = next_token
                page_index += 1
    for receipt in receipts:
        if verify_evidence_pair(evidence_root, run_dir.name, receipt.evidence_name) != "ADMISSIBLE":
            raise DataContractError(f"D5_HARNESS_RECEIPT_NOT_ADMISSIBLE: {receipt.evidence_name}.")
    lifecycle.close_run(status="COMPLETE", completed_at_utc=created_at_utc)
    admission = _qualify(scope, tuple(pages), created_at_utc)
    manifest: dict[str, Any] = {
        "schema": HARNESS_SCHEMA,
        "label": HARNESS_LABEL,
        "run_id": run_dir.name,
        "scope_sha256": scope_sha,
        "asof": scope.asof.isoformat(),
        "limit": D5_HARNESS_LIMIT,
        "adjustments": list(D5_HARNESS_ADJUSTMENTS),
        "planned_min_requests": planned.requests,
        "operations_used": seq,
        "bytes_observed": budget.bytes_observed,
        "receipts": [
            {
                "seq": r.seq,
                "adjustment": r.adjustment,
                "page_index": r.page_index,
                "request_sha256": r.request_sha256,
                "url_sha256": r.url_sha256,
                "content_sha256": r.content_sha256,
                "receipt_sha256": r.receipt_sha256,
                "byte_count": r.byte_count,
            }
            for r in receipts
        ],
        "d5_verdict": admission.verdict.value,
        "d5_blockers": list(admission.blockers),
        "dataset_sha256": admission.dataset_sha256,
        "composite_sha256": admission.composite_sha256,
        "real_data_admitted": False,
    }
    return D5HarnessResult(
        run_id=run_dir.name,
        scope_sha256=scope_sha,
        planned_min_requests=planned.requests,
        operations_used=seq,
        bytes_observed=budget.bytes_observed,
        receipts=tuple(receipts),
        admission=admission,
        manifest=manifest,
        manifest_sha256=_sha256_json(manifest),
    )


def _qualify(
    scope: D5HarnessScope, pages: tuple[D5RawPage, ...], created_at_utc: str
) -> D5AdmissionResult:
    bundle = D5RealInputBundle(
        authority=scope.authority,
        origin=D5InputOrigin.SYNTHETIC_FIXTURE,
        pages=pages,
        dividends=scope.dividends,
        expected_ex_dates=scope.expected_ex_dates,
        claimed_level=D5EvidenceLevel.SYNTHETIC_PIPELINE_PROOF,
        pit_vintage_known=all(record.pit_vintage_known for record in scope.dividends),
    )
    return evaluate_d5_real_admission(bundle, now_utc=datetime.fromisoformat(created_at_utc))


def replay_d5_harness_run(
    scope: D5HarnessScope, result: D5HarnessResult, *, evidence_root: Path, created_at_utc: str
) -> D5AdmissionResult:
    """Rebuild the D5 candidate from stored evidence only and require identical seals."""
    run_dir = evidence_root / JOURNAL_DIRNAME / result.run_id
    pages: list[D5RawPage] = []
    previous: dict[str, str | None] = {}
    for receipt in result.receipts:
        if verify_evidence_pair(evidence_root, result.run_id, receipt.evidence_name) != "ADMISSIBLE":
            raise DataContractError(f"D5_HARNESS_REPLAY_NOT_ADMISSIBLE: {receipt.evidence_name}.")
        body = (run_dir / f"{receipt.evidence_name}.bin").read_bytes()
        if hashlib.sha256(body).hexdigest() != receipt.content_sha256:
            raise DataContractError(f"D5_HARNESS_REPLAY_DIGEST_MISMATCH: {receipt.evidence_name}.")
        token = previous.get(receipt.adjustment)
        next_token = _parse_next_token(body)
        pages.append(
            D5RawPage(
                adjustment=receipt.adjustment,
                page_index=receipt.page_index,
                page_token=token,
                next_page_token=next_token,
                request_sha256=receipt.request_sha256,
                content_sha256=receipt.content_sha256,
                raw_bytes=body,
            )
        )
        previous[receipt.adjustment] = next_token
    replayed = _qualify(scope, tuple(pages), created_at_utc)
    if (replayed.dataset_sha256, replayed.composite_sha256) != (
        result.admission.dataset_sha256,
        result.admission.composite_sha256,
    ):
        raise DataContractError("D5_HARNESS_REPLAY_SEAL_MISMATCH.")
    return replayed


__all__ = [
    "D5_HARNESS_ADJUSTMENTS",
    "D5_HARNESS_LIMIT",
    "D5HarnessReceipt",
    "D5HarnessResult",
    "D5HarnessScope",
    "HARNESS_LABEL",
    "HARNESS_SCHEMA",
    "build_d5_request",
    "replay_d5_harness_run",
    "run_d5_offline_harness",
]
