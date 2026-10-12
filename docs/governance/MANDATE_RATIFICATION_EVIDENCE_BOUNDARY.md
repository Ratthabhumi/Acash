# Mandate Ratification Evidence Boundary (M1.6)

**Status:** `BOUNDARY_DOCUMENTED` — design only, no new enforcement infrastructure.
**Scope:** `PASSIVE_CORE` mandate approval in `PortfolioGovernanceGate`.

## 1. What the gate proves

Registry **membership** with exact-match semantics:
- `mandate_status == "MANDATE_RATIFIED"` **and**
- `ratified_mandate_registry` is non-empty **and**
- `owner_mandate_id` is an exact element of the registry.

Empty registries fail closed (`MANDATE_UNVERIFIED_IN_REGISTRY`); prefix,
case-variant, padded, and superstring IDs fail closed. Pinned by adversarial
tests in `tests/unit/portfolio/test_governance_gate.py`.

## 2. What the gate does NOT prove (residual risk, explicit)

Both `mandate_status` and every `ratified_mandate_registry` entry are
**caller-provided**. A caller that mints its own ID and lists it in its own
registry passes the membership check. Membership is therefore necessary but
**insufficient** proof of human operator ratification.

No canonical owner-ratification record exists in the repository today against
which the gate could independently resolve an ID, and this milestone does not
invent cryptographic attestation architecture to pretend otherwise.

## 3. Containment (why this ships anyway)

1. Simulation proposals must remain explicitly labeled `SIMULATION_PROPOSAL`;
   drafts (`MANDATE_DRAFT`) are rejected for allocation authority.
2. Real-capital execution is blocked independently and unconditionally:
   `REAL_CAPITAL_AUTHORITY = $0.00`, `NO_REAL_ORDERS = true`. No broker-order
   side effects exist on any gate path.
3. Any future elevation of a registry entry to trusted evidence requires a
   separately ratified amendment binding IDs to operator-signed records —
   recorded here as an open item, not as implemented behavior.

## 4. Open item

`EVIDENCE-CONTRACT-MANDATE-01`: design a minimal verified mandate record
resolvable through existing governance/evidence infrastructure (no new
cryptographic architecture without explicit authorization). Until ratified,
executable approval remains registry-scoped only.
