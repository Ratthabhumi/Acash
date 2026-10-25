# V32 — Personal Research Mode Decision (2026-10-25)

Recorded: 2026-10-25 (UTC+7 session), parent main `22337661471415378ff4be56215463e395b2520b`.
Decided by: repository owner, in the operator chat. This is a dated record of a chat
decision, **not** a cryptographically signed ratification.

## Decisions

1. **Simplify for single-user, noncommercial research.** Add a separate
   `LOCAL_EXPLORATORY` D6 mode (`src/acash/research/d6/local_exploratory.py`). It does
   not require an independent admitter, production Ed25519 keys, signed commits or a
   provider-rights registry.
2. **A1/A2 approved by the owner.** Hashes are bound in
   `docs/governance/V31_OWNER_DECISION_AND_EVIDENCE_REGISTRY_20261025.md`.
   - For LOCAL_EXPLORATORY runs the state is `OWNER_APPROVED_IN_CHAT`, which is
     sufficient.
   - For Verified Research it stays `OWNER_APPROVED_PENDING_FORMAL_ATTESTATION`.
3. **Data rights rule.** Use only sources and access methods whose terms permit
   personal noncommercial research. Keep files local; `/data/` is git-ignored. Do not
   redistribute. If a source's terms forbid storing or transforming its data, use a
   different source.

## Unchanged

- D5 production admission, `D5_ADMISSION_TRUST_ANCHORS = EMPTY`, Lane A/B = UNISSUED,
  and the Verified Research gates are unchanged.
- Local results are never labelled D5-admitted or PIT-verified.
- REAL_CAPITAL_AUTHORITY = USD 0.00. NO_REAL_ORDERS = true. No paper or live trading.

How to run the mode: `docs/research/D6_LOCAL_EXPLORATORY_HOWTO.md`.
