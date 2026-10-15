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
    CanaryBudget,
    CanaryPage,
    CanaryPlan,
    ReservationJournal,
    STOP_OUTCOMES,
    _first_page_digest,
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
    immutable evidence pair; the run verifies ADMISSIBLE for all pairs and
    closes the lifecycle journal COMPLETE only then, ABORTED otherwise.
    Any breach (budget, digest, receipt, halt outcome) stops the run with
    no retry, no resume, and no silent recovery.
    """
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
            metadata={"feed": plan.feed, "request_index": index},
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
    for receipt_entry in receipts:
        state = verify_evidence_pair(
            root=evidence_root, run_id=run_dir.name, name=receipt_entry.evidence_name
        )
        if state != "ADMISSIBLE":
            raise DataContractError(
                f"D2_EVIDENCE_NOT_ADMISSIBLE: {receipt_entry.evidence_name} "
                f"classified {state}."
            )
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
