# V37A fixed-THB funding — frozen before execution

Owner authorized implementation after PR67; verified main
`499a3a751e22c46d0a2ac22bf7d8a35247630512`, post-merge CI 40384005612 SUCCESS.
The [machine-readable freeze](evidence/v37a_frozen_study_20261027.json) binds the
five existing input/snapshot digests and all five existing V36 result-file digests.
No new acquisition or external Research Sprint correction is permitted.

Twenty primary cells: VOO/BND 60/40, initial USD1,000, monthly THB
1,000/3,000/5,000/10,000, cadence 1/3/6/12 saving events (16 cells), plus
four monthly zero-fee/spread controls. Use the existing 2016–2025 window and
119 monthly events. Cent rounding remains explicit even in THB controls.
Base sender fee THB400, hypothetical spread 0.5%, intermediary USD0, delay0.
Seven one-at-a-time sensitivities on THB3,000/quarterly: sender250/550,
intermediary15, delay1/3 sessions, whole shares, literal R2F fractional pricing.
No parameter/grid changes after observing outcomes; no best-future-cadence claim.

Same-date/prior H.10 observation-date convention is inherited from V36.
It is a retrospective FX scenario: original release-time availability and retail
execution rates are unverified, so this is NOT a PIT-qualified executable funding
policy. No future-dated observation may be selected. Session arrival precedes
deployment under the existing engine policy; unpaid receivables remain unspendable.

Preserve the legacy USD wrapper and its F0 exact-USD bypass; THB controls use
the ordinary cadence1 remittance path, not a fabricated USD bypass. For remitting
modes, equivalent dated THB schedules must reproduce legacy USD plans exactly.
Principal cash/transit partitions reconcile exactly; only existing V36
`DECIMAL_DIVISION_TOLERANCE=1e-18` may handle reassociation of Decimal division
in USD attribution identities. It is not a cash floor or correction.

Acceptance: targeted adversarial and metamorphic tests before scenario execution;
V36 full output bytes unchanged and its 80 V35 comparison cells checked;
two V37A runs with identical canonical output digests; full hermetic tests,
strict MyPy, final-diff review and exact-head PR CI. Bind results to configuration,
inputs and implementation source digests; retain raw data/output outside public Git.
Report broker/household identities, fees, cash exposure, transit, THB XIRR and TWR.
The 60/40 grid does not require BIL; its unresolved cash-in-lieu guard must remain.

This is LOCAL_EXPLORATORY engineering. D5 NOT_ADMITTED; Lane A/B UNISSUED;
capital USD0.00; NO_REAL_ORDERS=true. No new hypothesis, DSR/PBO, paper/live
order, remittance, subscription, deployment or production activation.
Implementation PR requires a separate merge decision. Rollback is a scoped revert
of this extension, preserving old datasets/results and failed-run evidence.
