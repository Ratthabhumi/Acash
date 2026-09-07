"""Unit tests for Phase 14 Slice 3 deterministic feature discovery engine.

Test priorities (AGENTS.md Rule 14):
- Happy path: deterministic proposals with causal certification.
- Boundary: max_features caps; request field bounds.
- Malformed: empty variables; extra fields forbidden.
- Contradictory/Adversarial: no leakage, zero authority methods, duplicate canonical forms.
- Permutation: variable-order-free determinism where structurally required.
- Numerical stability / golden reference: proposal fields match canonical invariants exactly.
"""

import re
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from acash.research.ai.features import (
    CausalAstValidator,
    FeatureDiscoveryEngine,
    FeatureDiscoveryRequest,
    canonical_form,
)
from acash.research.ai.schema import AIFeatureProposal

FEATURE_ID_RE = re.compile(r"^AI-FEAT-[0-9a-fA-F]{8,32}$")
PROVENANCE_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SLUG_RE = re.compile(r"^[a-z0-9_]{3,32}$")


@pytest.fixture
def engine() -> FeatureDiscoveryEngine:
    return FeatureDiscoveryEngine()


def test_discovery_emits_validated_causal_proposals(
    engine: FeatureDiscoveryEngine,
) -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume"),
        target_phenomenon="order flow inventory reversion",
        max_features=8,
        max_expression_depth=2,
    )
    proposals = engine.discover(request)
    assert 1 <= len(proposals) <= 8
    for proposal in proposals:
        assert isinstance(proposal, AIFeatureProposal)
        assert proposal.is_strictly_causal is True
        assert proposal.lookahead_terms_detected == 0
        assert proposal.point_in_time_verified is True
        assert FEATURE_ID_RE.match(proposal.feature_id)
        assert SLUG_RE.match(proposal.feature_name)
        assert PROVENANCE_RE.match(proposal.provenance_hash)
        assert proposal.mathematical_formula == canonical_form(proposal.mathematical_formula)


def test_discovery_is_deterministic_across_runs(
    engine: FeatureDiscoveryEngine,
) -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume"),
        target_phenomenon="order flow inventory reversion",
        max_features=8,
    )
    first = engine.discover(request)
    second = engine.discover(request)
    assert first == second
    assert [p.feature_id for p in first] == [p.feature_id for p in second]


def test_discovery_deterministic_across_engine_instances() -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume"),
        target_phenomenon="order flow inventory reversion",
    )
    a = FeatureDiscoveryEngine().discover(request)
    b = FeatureDiscoveryEngine().discover(request)
    assert a == b


def test_discovery_respects_max_features_cap(engine: FeatureDiscoveryEngine) -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume", "open", "high", "low"),
        target_phenomenon="extension overload exhaustion",
        max_features=3,
    )
    assert len(engine.discover(request)) == 3


def test_discovery_no_duplicate_canonical_forms(engine: FeatureDiscoveryEngine) -> None:
    """Every emitted formula must be canonical-distinct (operator-equivalence dedup)."""
    request = FeatureDiscoveryRequest(
        base_variables=("close", "volume"),
        target_phenomenon="inventory reversion pressure",
        max_features=50,
    )
    formulas = [p.mathematical_formula for p in engine.discover(request)]
    assert len(formulas) == len(set(formulas))


def test_discovery_every_proposal_revalidates_as_causal(
    engine: FeatureDiscoveryEngine,
) -> None:
    validator = CausalAstValidator()
    request = FeatureDiscoveryRequest(
        base_variables=("bid", "ask"),
        target_phenomenon="cross section spread squeeze",
        max_features=50,
    )
    for proposal in engine.discover(request):
        result = validator.validate_expression(
            proposal.mathematical_formula, ("bid", "ask")
        )
        assert result.point_in_time_verified is True
        assert result.lookahead_terms_detected == 0


def test_discovery_pair_dependent_and_independent_both_survive(
    engine: FeatureDiscoveryEngine,
) -> None:
    """imbalance(.) and its algebraic (a-b)/(a+b) twin are canonical-distinct survivors."""
    request = FeatureDiscoveryRequest(
        base_variables=("bid", "ask"),
        target_phenomenon="microstructure pressure",
        max_features=50,
    )
    formulas = [p.mathematical_formula for p in engine.discover(request)]
    assert any("imbalance(" in f for f in formulas)
    assert any("/(" in f for f in formulas)


def test_discovery_request_validation_bounds() -> None:
    with pytest.raises(ValidationError):
        FeatureDiscoveryRequest(base_variables=(), target_phenomenon="x")
    with pytest.raises(ValidationError):
        FeatureDiscoveryRequest(
            base_variables=("close",),
            target_phenomenon="x",
            max_features=0,
        )
    with pytest.raises(ValidationError):
        FeatureDiscoveryRequest(
            base_variables=("close",),
            target_phenomenon="x",
            max_features=51,
        )
    with pytest.raises(ValidationError):
        FeatureDiscoveryRequest(
            base_variables=("close",),
            target_phenomenon="x",
            max_expression_depth=0,
        )
    extra_fields: Dict[str, Any] = {"extra_field": "forbidden"}
    with pytest.raises(ValidationError):
        FeatureDiscoveryRequest(
            base_variables=("close",),
            target_phenomenon="x",
            **extra_fields,
        )


def test_discovery_proposal_has_zero_authority_methods(
    engine: FeatureDiscoveryEngine,
) -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close",),
        target_phenomenon="whole session inventory wave",
        max_features=5,
    )
    for proposal in engine.discover(request):
        for method in (
            "authorize_trading",
            "allocate_capital",
            "override_quarantine",
            "execute_backtest",
            "register",
            "to_hypothesis_specification",
        ):
            assert not hasattr(proposal, method), f"proposal leaked authority method: {method}"


def test_discovery_proposals_are_immutable(engine: FeatureDiscoveryEngine) -> None:
    request = FeatureDiscoveryRequest(
        base_variables=("close",),
        target_phenomenon="intraday reversion universe",
        max_features=1,
    )
    proposal = engine.discover(request)[0]
    with pytest.raises(ValidationError):
        proposal.mathematical_formula = "abs(close)"
    with pytest.raises(ValidationError):
        proposal.point_in_time_verified = False


def test_discovery_target_varies_feature_ids_but_not_formulas(
    engine: FeatureDiscoveryEngine,
) -> None:
    """Different target phenomena reseed feature provenance but preserve the formula set."""
    request = FeatureDiscoveryRequest(
        base_variables=("close",),
        target_phenomenon="opening auction pressure",
        max_features=50,
    )
    tuples_a = engine.discover(request)
    request_b = FeatureDiscoveryRequest(
        base_variables=("close",),
        target_phenomenon="closing auction pressure",
        max_features=50,
    )
    tuples_b = engine.discover(request_b)
    assert [p.feature_id for p in tuples_a] != [p.feature_id for p in tuples_b]
    assert [p.mathematical_formula for p in tuples_a] == [
        p.mathematical_formula for p in tuples_b
    ]


def test_discovery_module_does_not_reach_frozen_core() -> None:
    """Feature discovery must import only research/core, never frozen execution namespaces."""
    import importlib
    import inspect

    forbidden_tops = {
        "backtest",
        "execution",
        "portfolio",
        "account",
        "strategy",
        "broker",
        "mt5",
        "cli",
        "acash_governance",
    }
    module = importlib.import_module("acash.research.ai.features.discovery")
    for obj in vars(module).values():
        if inspect.ismodule(obj):
            full = obj.__name__
            if not full.startswith("acash."):
                continue
            top = full.split(".")[1]
            assert top not in forbidden_tops, f"discovery leaked frozen-core import: {full}"