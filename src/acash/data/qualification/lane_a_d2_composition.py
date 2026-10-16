"""D2 offline composition: reservation -> fake dispatch -> evidence (OFFLINE ONLY).

The smallest missing integration contract: it composes ALREADY-REVIEWED
pieces end-to-end without duplicating them —
- PR #32 ``ReservationJournal``: the SOLE pre-dispatch reservation
  authority (per-attempt sequence, fsync-before-return, poison on
  sync failure, no append after close is enforced by single use here);
- PR #32 ``CanaryBudget``: the SOLE operation/byte budget (no second
  ledger is introduced);
- M1.8.1 ``DurableAttemptJournal``: run lifecycle + evidence attachment
  only (never a second reservation authority);
- M1.8.1 ``store_raw_evidence`` / ``verify_evidence_pair``: immutable
  raw/receipt persistence and admissibility classification;
- M1.7 canonical request identity via the plan's digests.

Byte semantics (explicit): the caller-supplied ``payload_fn`` produces the
SYNTHETIC response bytes whose length MUST equal the fake page's
``nbytes`` (mismatch fails closed). These are decoded-content-equivalent
test bytes, never wire bytes; the raw-vs-decoded contract for real
dispatch remains a separate D3 gate (see PR #37).

No real HTTP, no credentials, no approval verifier, no entitlement.
A run that cannot prove every receipt ADMISSIBLE is never reported
COMPLETE: incomplete pairs fail the run closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Tuple

from acash.core.domain.exceptions import DataContractError
from acash.data.qualification.lane_a_canary import (
    CANARY_FEEDS,
    CanaryBudget,
    CanaryPage,
    CanaryPlan,
    ReservationJournal,
    STOP_OUTCOMES,
    _first_page_digest,
    audit_reservation_history,
    canonical_scope_digest,
    canary_planned_requests,
    continuation_digest,
)
from acash.data.qualification.lane_a_transport import (
    DurableAttemptJournal,
    store_raw_evidence,
    verify_evidence_pair,
)

PayloadFn = Callable[[str, str, CanaryPage], bytes]


@dataclass(frozen=True)
class D2EvidenceReceipt:
    """Evidence linkage for one settled attempt (synthetic bytes)."""

    seq: int
    evidence_name: str
    content_sha256: str
    receipt_sha256: str
    byte_count: int


@dataclass
class D2ComposedResult:
    """Offline composed-run outcome (synthetic verdict, never market evidence)."""

    verdict: str
    operations_used: int
    bytes_observed: int
    run_id: str
    receipts: List[D2EvidenceReceipt] = field(default_factory=list)
    dispatches: List[str] = field(default_factory=list)


def validate_plan_binding(
    plan: CanaryPlan, authority_ref: str, runtime_sha: str, now_utc: str
) -> None:
    """Validate plan/authority/runtime consistency BEFORE any run artifacts.

    Rejects: empty or non-canonical requests, feed mismatch, digest
    mismatch (recomputed over the actual requests), authority/runtime
    identity mismatch, and out-of-window approval. Direct-constructed
    plans that bypass CanaryPlan.build() fail here, never at dispatch.
    Structural equality never proves genuine human approval.
    """
    if not isinstance(plan.requests, tuple) or not plan.requests:
        raise DataContractError("D2_EMPTY_PLAN: no canonical requests bound.")
    if plan.feed not in CANARY_FEEDS:
        raise DataContractError(f"D2_PLAN_BAD_FEED: {plan.feed!r}.")
    expected_requests = canary_planned_requests(plan.feed)
    if tuple(plan.requests) != expected_requests:
        raise DataContractError(
            "D2_PLAN_REQUESTS_NOT_CANONICAL: requests differ from the "
            "M1.7-planned canonical set for this feed."
        )
    expected_digest = canonical_scope_digest(
        list(plan.requests),
        plan.approval.max_operations,
        plan.approval.max_bytes,
    )
    if expected_digest != plan.scope_digest or plan.scope_digest != plan.approval.scope_digest:
        raise DataContractError("D2_PLAN_SCOPE_DIGEST_MISMATCH.")
    if authority_ref != plan.approval.approval_ref:
        raise DataContractError("D2_AUTHORITY_REF_MISMATCH.")
    if runtime_sha != plan.approval.runtime_sha or runtime_sha != plan.runtime_sha:
        raise DataContractError("D2_RUNTIME_SHA_MISMATCH.")
    if not plan.approval.is_within_window(now_utc):
        raise DataContractError("D2_APPROVAL_WINDOW_INVALID.")


def verify_evidence_lineage(
    evidence_root: Path,
    journal: ReservationJournal,
    expected: List[Tuple[int, str, str]],
) -> None:
    """Verify the full request -> reservation -> evidence lineage.

    Each expected (seq, request_digest, evidence_name) must satisfy: a
    matching reserved record in the audited journal history, a settled
    outcome for that seq, an ADMISSIBLE raw/receipt pair, and receipt
    metadata binding the same request digest. Anything else fails closed.
    """
    import json

    records = journal.read_reservations()
    settled = audit_reservation_history(records)
    reserved = {
        int(r["seq"]): str(r["request_digest"])
        for r in records
        if r.get("event") == "reserved"
    }
    run_dir = journal._file.parent  # noqa: SLF001 — same-package composition
    run_id = run_dir.name
    for seq, digest, name in expected:
        if reserved.get(seq) != digest:
            raise DataContractError(
                f"D2_LINEAGE_RESERVATION_MISMATCH: seq {seq}."
            )
        if seq not in settled:
            raise DataContractError(
                f"D2_LINEAGE_UNSETTLED: seq {seq}."
            )
        if settled.get(seq) != "OK":
            raise DataContractError(
                f"D2_LINEAGE_SETTLEMENT_NOT_OK: seq {seq} settled as {settled.get(seq)!r}."
            )
        if verify_evidence_pair(root=evidence_root, run_id=run_id, name=name) != "ADMISSIBLE":
            raise DataContractError(
                f"D2_LINEAGE_NOT_ADMISSIBLE: {name}."
            )
        try:
            receipt = json.loads(
                (run_dir / f"{name}.receipt.json").read_bytes().decode("utf-8")
            )
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            raise DataContractError(
                f"D2_LINEAGE_RECEIPT_CORRUPT: {name}."
            ) from exc
        metadata = receipt.get("metadata") if isinstance(receipt, dict) else None
        if not isinstance(metadata, dict) or metadata.get("request_digest") != digest:
            raise DataContractError(
                f"D2_LINEAGE_RECEIPT_BINDING_MISMATCH: {name}."
            )
        feed = metadata.get("feed")
        if not isinstance(feed, str) or feed not in CANARY_FEEDS:
            raise DataContractError(
                f"D2_LINEAGE_RECEIPT_BAD_FEED: {name}."
            )
        req_idx = metadata.get("request_index")
        if not isinstance(req_idx, int) or isinstance(req_idx, bool) or req_idx < 0:
            raise DataContractError(
                f"D2_LINEAGE_RECEIPT_BAD_REQUEST_INDEX: {name}."
            )


def run_d2_composition(
    plan: CanaryPlan,
    transport: Any,
    evidence_root: Path,
    run_id: str,
    authority_ref: str,
    runtime_sha: str,
    created_at_utc: str,
    payload_fn: PayloadFn,
) -> D2ComposedResult:
    """Compose reserve -> fake dispatch -> settle -> evidence, fail-closed.

    Every dispatch is reserved first; every settled attempt persists one
    immutable evidence pair; the run verifies full lineage for all pairs
    and closes the lifecycle journal COMPLETE only then, ABORTED for
    handled halt outcomes. Any other exception escapes WITHOUT closing:
    the run stays INTERRUPTED (never COMPLETE), non-resumable under the
    same run id. Any breach stops the run with no retry and no recovery.
    """
    validate_plan_binding(plan, authority_ref, runtime_sha, created_at_utc)
    lifecycle = DurableAttemptJournal.create_run(
        root=evidence_root,
        run_id=run_id,
        authority_ref=authority_ref,
        runtime_sha=runtime_sha,
        created_at_utc=created_at_utc,
    )
    # Single path authority stays in lane_a_transport: the run directory is
    # read from the created lifecycle journal, never reconstructed here.
    run_dir = lifecycle._run_dir  # noqa: SLF001 — same-package composition
    journal = ReservationJournal.create(run_dir)
    budget = CanaryBudget(plan.approval.max_operations, plan.approval.max_bytes)
    seq = 0
    seen_chain_tokens: set[Tuple[int, str]] = set()
    receipts: List[D2EvidenceReceipt] = []
    dispatches: List[str] = []
    seq_to_digest: dict[int, str] = {}
    pending: List[Tuple[int, str]] = [
        (index, "") for index, _ in plan.request_digests()
    ]
    halted_outcome: str | None = None
    while pending:
        index, token = pending.pop(0)
        request = plan.requests[index]
        if token == "":
            request_digest = _first_page_digest(request)
        else:
            request_digest = continuation_digest(request, token)
        seq += 1
        budget.reserve_operation()
        journal.reserve(seq, request_digest)
        seq_to_digest[seq] = request_digest
        page = transport.get(request_digest, token)
        if not isinstance(page, CanaryPage):
            raise DataContractError(
                f"D2_TRANSPORT_BAD_PAGE: {type(page).__name__}."
            )
        payload = payload_fn(request_digest, token, page)
        if not isinstance(payload, (bytes, bytearray)) or len(payload) != page.nbytes:
            raise DataContractError(
                "D2_PAYLOAD_BYTE_MISMATCH: synthetic payload must equal "
                "the page's declared nbytes exactly."
            )
        dispatches.append(f"{request_digest}:{token}")
        budget.observe_bytes(page.nbytes)
        if page.outcome in STOP_OUTCOMES:
            journal.settle(seq, page.outcome)
            halted_outcome = page.outcome
            budget.halt(page.outcome)
            break
        journal.settle(seq, page.outcome)
        evidence_name = f"seq_{seq:04d}"
        receipt = store_raw_evidence(
            root=evidence_root,
            run_id=run_dir.name,
            name=evidence_name,
            payload=bytes(payload),
            metadata={
                "feed": plan.feed,
                "request_index": index,
                "request_digest": request_digest,
            },
        )
        receipts.append(
            D2EvidenceReceipt(
                seq=seq,
                evidence_name=evidence_name,
                content_sha256=str(receipt["content_sha256"]),
                receipt_sha256=str(receipt["receipt_sha256"]),
                byte_count=int(receipt["byte_count"]),
            )
        )
        if page.next_token:
            chain_key = (index, page.next_token)
            if chain_key in seen_chain_tokens:
                raise DataContractError(
                    f"D2_PAGE_TOKEN_CYCLE: {page.next_token!r} already "
                    "produced in this request chain."
                )
            seen_chain_tokens.add(chain_key)
            pending.append((index, page.next_token))
    expected = [
        (receipt_entry.seq, seq_to_digest[receipt_entry.seq], receipt_entry.evidence_name)
        for receipt_entry in receipts
    ]
    verify_evidence_lineage(evidence_root, journal, expected)
    if halted_outcome is not None:
        lifecycle.close_run(status="ABORTED", completed_at_utc=created_at_utc)
        return D2ComposedResult(
            verdict="HALTED_" + halted_outcome,
            operations_used=seq,
            bytes_observed=budget.bytes_observed,
            run_id=run_dir.name,
            receipts=receipts,
            dispatches=dispatches,
        )
    lifecycle.close_run(status="COMPLETE", completed_at_utc=created_at_utc)
    return D2ComposedResult(
        verdict="TRANSPORT_PAGINATION_COMPLETE",
        operations_used=seq,
        bytes_observed=budget.bytes_observed,
        run_id=run_dir.name,
        receipts=receipts,
        dispatches=dispatches,
    )
