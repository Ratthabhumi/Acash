# Owner wealth ledger: external cash and broker observations

Two evidence types were added. Neither is a bank API reading, and neither may change a broker
valuation.

## External cash (owner-declared)

`data/private/external_accounts.json` (git-ignored, private) holds accounts that live **outside**
the brokerage. Each row records:

`account_ref` · institution · owner label · balance · currency · precision (`EXACT` / `APPROXIMATE`)
· evidence (`OWNER_DECLARED` / `OWNER_ESTIMATE`) · liquidity (`WITHDRAWABLE` / `SPENDING`) ·
reserve eligibility · inclusion scope · observation timestamp · effective date.

Rules enforced by the loader:

- A declared balance must be exact; an approximate balance must be an owner estimate. There is no
  path that turns an estimate into a verified balance.
- A missing screenshot is not a reason to refuse an owner declaration, and an owner declaration is
  never presented as a bank observation.
- Duplicate account refs, negative balances and unknown enum values fail closed.
- External cash is `WEALTH_ONLY`: it never enters the broker NAV, settled cash, brokerage P&L or the
  `DIME_SECURITIES` reconciliation. It may enter the consolidated wealth figure, which is labelled
  `MIXED_EVIDENCE_MIXED_TIME` because the observation times differ.
- Three numbers stay distinct: **actual external cash**, the **owner's external-cash target**, and
  the **expense-derived emergency-reserve requirement**. The reserve target is not reduced to
  match the cash target, and the cash target is not treated as a balance.

## Broker-displayed observation

`data/private/broker_observations.json` records what a broker app displayed at one moment
(`BROKER_DISPLAYED_OBSERVATION`), with category totals and the displayed total. The loader rejects
an arithmetic mismatch, a duplicate timestamp and a non-observation evidence label. Recording is
append-only and idempotent by observation id.

A comparison against an ACASH valuation is `SAME_TIME_COMPARABLE` only when the valuation date
equals the observation date; otherwise it is `TIME_MISALIGNED` and the note states that the gap can
be market movement or FX timing — never proof of a missing transaction. No balancing cash, trade or
FX adjustment is created from an observation.

## Where it surfaces

`GET /api/upi/wealth` (loopback, session-authenticated, ODR-001 gated, read-only) returns the
external-cash summary, the latest observation summary, the comparison status and the consolidated
wealth figure. The Portfolio → ตรวจสอบข้อมูล tab renders it with Thai labels and keeps the broker
value and external cash visually separate.

## Capacity correction

The capacity input previously held the owner's external-cash **target** in the current-reserve
field. The input now holds the actual declared cash; the target lives in the external-cash registry.
The emergency-reserve requirement remains expense-derived and unchanged, so a shortfall stays a
shortfall until the underlying cash actually changes.

## Broker cash: only visible accounts

The broker app shows Dime! Save, Dime! USD and Dime! FCD. There is no separately confirmed
"Securities Cash" account, so none is modelled. `DIME_SECURITIES` remains an investment-account
container that legitimately holds settled-cash lines in the historical statement; that is a PPDS
reference, not a fourth cash account.

`cash_breakdown()` explains a broker cash category from the visible accounts only. When the visible
THB equivalents do not add up to the displayed category total, the remainder is reported as
`UNEXPLAINED_RESIDUAL` and is never assigned to an account, to FCD, or to buying power. A component
without a THB equivalent makes the result `PARTIAL_COMPONENTS_NOT_VALUED` instead of guessing.

A later screenshot with a different FX equivalent is a separate observation; it is never combined
with an earlier total as if both were taken at the same moment.
