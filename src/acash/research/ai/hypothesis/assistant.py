"""Phase 14 S2 AI hypothesis assistant (strictly UNVALIDATED_PROPOSAL output).

The assistant:
- generates a proposal via the injected ``ILLMProvider`` under the G-4 guard
- propagates deterministic provider usage/telemetry to the caller
- NEVER creates HYP_003, NEVER registers a hypothesis, NEVER invokes any gate,
  NEVER creates R1, NEVER touches trading/capital/broker state.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Callable, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from decimal import Decimal

from acash.research.ai.enums import CandidateStatus
from acash.research.ai.hypothesis.prompts import (
    PROMPT_TEMPLATE_SHA256,
    build_hypothesis_prompt,
)
from acash.research.ai.provider.base import (
    ILLMProvider,
    InvalidProviderResponseError,
    LLMGenerationConfig,
    RunBudgetSession,
    RunBudgetSnapshot,
    TokenUsage,
)
from acash.research.ai.schema import AIHypothesisProposal
from acash.research.schema import ExpectedDirection, InvalidationCriteria

_REQUIRED_KEYS: Tuple[str, ...] = (
    "economic_rationale",
    "market_microstructure_mechanism",
    "invalidation_conditions",
    "target_symbol",
    "target_timeframe",
    "feature_dependencies",
    "expected_direction",
    "target_horizons",
    "proposed_invalidation_criteria",
)
_DIRECTION_VALUES: Tuple[str, ...] = ("LONG", "SHORT", "DISPERSION")


class AssistantResult(BaseModel):
    """Deterministic assistant output: proposal + provider usage + budget snapshot."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal: AIHypothesisProposal
    usage: TokenUsage
    budget: RunBudgetSnapshot


class AIHypothesisAssistant:
    """Proposal-only generator. Output is ALWAYS an ``AIHypothesisProposal`` with
    ``proposal_status == UNVALIDATED_PROPOSAL`` (enforced at the type level)."""

    def __init__(
        self,
        provider: ILLMProvider,
        *,
        config: Optional[LLMGenerationConfig] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self._provider: ILLMProvider = provider
        self._config: LLMGenerationConfig = (
            config if config is not None else LLMGenerationConfig()
        )
        self._clock: Callable[[], datetime] = (
            clock if clock is not None else lambda: datetime.now(timezone.utc)
        )

    @property
    def config(self) -> LLMGenerationConfig:
        return self._config

    def generate_hypothesis(
        self,
        *,
        symbol: str,
        timeframe: str,
        economic_context: str,
        source_metadata_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        budget: Optional[RunBudgetSession] = None,
    ) -> AssistantResult:
        session = budget if budget is not None else RunBudgetSession()
        prompt = build_hypothesis_prompt(
            symbol=symbol,
            timeframe=timeframe,
            economic_context=economic_context,
        )
        provider_response = self._provider.generate(self._config, prompt, session)
        proposal = self._parse_proposal(
            raw_response=provider_response.raw_response,
            proposal_id=proposal_id,
            source_metadata_id=source_metadata_id,
        )
        if proposal.proposal_status != CandidateStatus.UNVALIDATED_PROPOSAL:
            raise InvalidProviderResponseError(
                "Assistant produced a non-UNVALIDATED_PROPOSAL status; refused."
            )
        return AssistantResult(
            proposal=proposal,
            usage=provider_response.usage,
            budget=session.snapshot(),
        )

    def _parse_proposal(
        self,
        *,
        raw_response: str,
        proposal_id: Optional[str],
        source_metadata_id: Optional[str],
    ) -> AIHypothesisProposal:
        try:
            payload: object = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise InvalidProviderResponseError(
                f"Assistant provider returned non-JSON output: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise InvalidProviderResponseError("Assistant provider output is not a JSON object.")
        missing = [k for k in _REQUIRED_KEYS if k not in payload]
        if missing:
            raise InvalidProviderResponseError(
                f"Assistant provider output missing required keys: {missing}."
            )
        expected_direction_raw = payload["expected_direction"]
        if expected_direction_raw not in _DIRECTION_VALUES:
            raise InvalidProviderResponseError(
                f"Invalid expected_direction: {expected_direction_raw!r}."
            )
        generated_at_utc = self._clock().isoformat()
        raw_response_sha256 = hashlib.sha256(raw_response.encode("utf-8")).hexdigest()
        default_id = f"AI-HYP-{raw_response_sha256[:16]}"
        try:
            proposal = AIHypothesisProposal(
                proposal_id=proposal_id if proposal_id is not None else default_id,
                economic_rationale=str(payload["economic_rationale"]),
                market_microstructure_mechanism=str(payload["market_microstructure_mechanism"]),
                invalidation_conditions=_as_string_tuple(payload["invalidation_conditions"], "invalidation_conditions"),
                target_symbol=str(payload["target_symbol"]),
                target_timeframe=str(payload["target_timeframe"]),
                feature_dependencies=_as_string_tuple(payload["feature_dependencies"], "feature_dependencies"),
                expected_direction=ExpectedDirection(str(expected_direction_raw)),
                target_horizons=_as_int_tuple(payload["target_horizons"], "target_horizons"),
                proposed_invalidation_criteria=_as_invalidation_criteria(
                    payload["proposed_invalidation_criteria"]
                ),
                source_metadata_id=source_metadata_id,
                llm_provider=self._provider.provider_name,
                llm_model_id=self._provider.model_id,
                prompt_template_sha256=PROMPT_TEMPLATE_SHA256,
                temperature=self._config.temperature,
                seed=self._config.seed,
                generated_at_utc=generated_at_utc,
                raw_response_sha256=raw_response_sha256,
            )
        except Exception as exc:
            raise InvalidProviderResponseError(
                f"Assistant provider output violated the proposal schema: {exc}"
            ) from exc
        return proposal


def _as_string_tuple(raw: object, name: str) -> Tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise InvalidProviderResponseError(f"{name} must be a non-empty array.")
    return tuple(str(item) for item in raw)


def _as_int_tuple(raw: object, name: str) -> Tuple[int, ...]:
    if not isinstance(raw, list) or not raw:
        raise InvalidProviderResponseError(f"{name} must be a non-empty array.")
    try:
        return tuple(int(item) for item in raw)
    except (TypeError, ValueError) as exc:
        raise InvalidProviderResponseError(f"{name} must contain integers.") from exc


def _as_invalidation_criteria(raw: object) -> InvalidationCriteria:
    if not isinstance(raw, dict):
        raise InvalidProviderResponseError(
            "proposed_invalidation_criteria must be a JSON object."
        )
    try:
        return InvalidationCriteria(
            min_in_sample_rank_ic=_as_decimal(raw, "min_in_sample_rank_ic"),
            min_hac_t_stat=_as_decimal(raw, "min_hac_t_stat"),
            max_feature_autocorrelation=_as_decimal(raw, "max_feature_autocorrelation"),
            min_cost_adjusted_spread_ratio=_as_decimal(raw, "min_cost_adjusted_spread_ratio"),
        )
    except Exception as exc:
        raise InvalidProviderResponseError(
            f"proposed_invalidation_criteria is malformed: {exc}"
        ) from exc


def _as_decimal(raw: dict[str, object], key: str) -> Decimal:
    value = raw.get(key)
    if value is None:
        raise InvalidProviderResponseError(f"Missing invalidation criterion: {key}.")
    return Decimal(str(value))