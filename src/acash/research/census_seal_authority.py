"""Minimum D6 sealing-owner infrastructure (human-ratified).

The production orchestration / sealing owner is the SOLE authority permitted to seal the
authoritative `SearchTrialLedger` census. Research components (notably the Evidence Bridge)
MAY construct trial records and assemble open ledgers, but MUST NOT seal them. The sealed
census is cryptographically immutable (`is_sealed`, `ledger_digest`) and the frozen
pre-registration K anchor (`ResearchInceptionProposal.planned_trial_count`) is enforced at
sealing time when supplied.

No production orchestrator exists in this repository (Production Orchestration = ABSENT).
Until an orchestrator is integrated, `SearchTrialCensusSealAuthority` itself is the designated
owner acting on behalf of production orchestration; any future orchestrator MUST seal through
this exact gateway so the single-authority invariant is preserved.
"""

from typing import Optional

from acash.core.domain.exceptions import DataContractError
from acash.validation.schema import SearchTrialLedger


class SearchTrialCensusSealAuthority:
    """Sole sanctioned gateway sealing the authoritative D6 trial census.

    This is the ONLY caller permitted to seal the authoritative census. The Evidence Bridge and
    other research components construct trial records and open ledgers but MUST NOT invoke
    `SearchTrialLedger.seal` directly.
    """

    DESIGNATED_OWNER_ID = "ACASH_D6_CENSUS_AUTHORITY"

    @staticmethod
    def seal_census(
        ledger: SearchTrialLedger,
        *,
        expected_k: Optional[int] = None,
        sealed_at_utc: Optional[str] = None,
    ) -> SearchTrialLedger:
        """Seal an authoritative census, binding the frozen pre-registration K anchor when provided.

        Raises:
            DataContractError: if `expected_k` is provided and does not equal `len(census.trials)`
                (the frozen census size MUST equal the planned trial count), or if the ledger was
                already sealed by a different owner.
        """
        if expected_k is not None:
            if ledger.total_trials != expected_k:
                raise DataContractError(
                    f"Census '{ledger.ledger_id}' K={ledger.total_trials} does not match the pre-registered "
                    f"planned_trial_count K={expected_k}. The frozen census size must equal the planned K "
                    f"anchor; census K never shrinks and no trial may be appended post-registration."
                )

        sealed = ledger.seal(
            sealed_at_utc=sealed_at_utc,
            sealing_owner=SearchTrialCensusSealAuthority.DESIGNATED_OWNER_ID,
        )
        if sealed.sealed_by_owner != SearchTrialCensusSealAuthority.DESIGNATED_OWNER_ID:
            raise DataContractError(
                f"Census '{ledger.ledger_id}' sealing owner attestation mismatch: recorded "
                f"'{sealed.sealed_by_owner}' != designated '{SearchTrialCensusSealAuthority.DESIGNATED_OWNER_ID}'."
            )
        return sealed