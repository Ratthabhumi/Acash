# ACASH V38 — ChatGPT External Research Handoff

**Date**: 2026-10-30  
**Division of Responsibility**:
- **Codex (Engineering)**: Architecture, offline calculation core, deterministic fail-closed math, tests, CI, GitHub PR. *(Complete)*
- **ChatGPT (Research)**: External fee discovery, regulatory updates, broker promotional terms, and exchange spreads. *(Handed off below)*

---

## Priority Research Questions for ChatGPT

To convert the `LOWER_BOUND_ONLY` cost assessments into `ALL_IN_DOCUMENTED` numbers, the following specific primary-source data points are needed:

| ID | Platform | Research Topic | Current Status in Engine | Specific Evidence Needed |
| :---: | :--- | :--- | :--- | :--- |
| **RQ-01** | **Dime! Thailand** | Effective THB/USD Conversion Spread | Recorded as `UNKNOWN` (`DIME_FX_SPREAD`) | What is the exact FX markup/spread applied by Dime! (KKP) when converting THB to USD to buy US shares? (e.g. in bps or % relative to BOT / interbank mid-rate). |
| **RQ-02** | **Webull Thailand** | Effective THB/USD Conversion Spread | Recorded as `UNKNOWN` (`WEBULL_FX_SPREAD`) | What is Webull Thailand's FX markup/spread for automatic and manual currency conversion? |
| **RQ-03** | **Webull Thailand** | DCA Commission Conflict (0% vs 0.10%) | Modeled as `TERMS_CONFLICTING` | Does Webull Fixed DCA have a permanent 0% commission or is it a promotional discount? What is the official expiration date and qualifying condition according to official announcements? |
| **RQ-04** | **Dime! & Webull** | US ETF Availability & Fractional Eligibility | Modeled as `CONDITIONALLY_ELIGIBLE` | Are `VOO`, `BND`, `GLD`, and `BIL` all eligible for fractional share purchases in retail cash accounts on Dime! and Webull Thailand? |
| **RQ-05** | **Dime! & Webull** | Regulatory Pass-Through & Hidden Charges | Modeled as zero or unknown | Do Dime! and Webull Thailand pass through US SEC Section 31 fees ($0.0000278) or FINRA Trading Activity Fees (TAF) on sell orders or purchases? |
| **RQ-06** | **IBKR** | Thai Bank Direct Deposit Instructions | Modeled as `ACCOUNT_SPECIFIC_UNVERIFIED` | Does IBKR provide a local receiving bank account in Thailand or Singapore that avoids full US SWIFT intermediary deductions? |

---

## Instructions for ChatGPT
When researching the above:
1. Provide exact official URLs (e.g. from `dime.co.th`, `webull.co.th`, `bot.or.th`, `interactivebrokers.com`).
2. Cite publication dates and effective terms.
3. If an FX spread is floating/dynamic, provide observable sample spreads during Thai market hours vs US market hours.
4. Do not assume or extrapolate fees; if undisclosed, report as `STILL_UNKNOWN`.
