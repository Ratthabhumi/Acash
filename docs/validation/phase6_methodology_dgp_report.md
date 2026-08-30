# ACASH Phase 6 Empirical DGP Benchmark Report

## 1. Experiment A: Zero-Alpha Null DGP (False Positive Rate)
- **Simulations**: 100 runs (T=500, M=10, Seed=42)
- **Observed Approval Rate**: `0.00%` (0/100)
- **Wilson 95% Confidence Interval**: `[0.00%, 3.70%]`
- **Verdict Distribution**: `{"REJECT_OVERFIT_DSR": 100}`

## 2. Experiment B: Correlated Search DGP (Hurdle Dynamics & PBO)
| Correlation $\rho$ | Empirical $\operatorname{Var}(\widehat{SR})$ | $SR_0$ Hurdle (Ann) | DSR Probability | PBO Estimate | PBO Rejection |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 0.00 | 0.579411 | 1.7327 | 49.76% | 0.3810 | REJECT |
| 0.50 | 0.547123 | 1.6837 | 52.52% | 0.3968 | REJECT |
| 0.85 | 0.128759 | 0.8168 | 90.17% | 0.4921 | REJECT |
| 0.95 | 0.056552 | 0.5413 | 95.37% | 0.4643 | REJECT |
| 0.99 | 0.007758 | 0.2005 | 98.48% | 0.4484 | REJECT |

## 3. Experiment C: Serial Dependence & HAC Robust Inference
| Scenario | Asymptotic Normal FPR | Wilson 95% CI | Inflation | HAC Newey-West FPR | HAC Wilson 95% CI |
| :--- | :---: | :---: | :---: | :---: | :---: |
| IID_Noise | 4.33% | [2.55%, 7.27%] | 0.87x | 4.00% | [2.30%, 6.86%] |
| AR1_phi_0.20 | 10.67% | [7.66%, 14.67%] | 2.13x | 6.33% | [4.09%, 9.68%] |
| AR1_phi_0.40 | 24.67% | [20.13%, 29.84%] | 4.93x | 9.00% | [6.26%, 12.78%] |
| Overlapping_H5 | 41.33% | [35.90%, 46.98%] | 8.27x | 10.67% | [7.66%, 14.67%] |
| Overlapping_H10 | 51.67% | [46.03%, 57.26%] | 10.33x | 8.67% | [5.98%, 12.40%] |

## 4. Experiment D: End-to-End Governance Admission Probability & Layer Decomposition

### Topology 1: Diverse Search Universe (1 True Alpha + 9 Exploratory Noise Models)
#### A. Marginal Layer Admission Rates
| True $SR$ | Joint $P(\text{PASS})$ | Wilson 95% CI | DSR Pass | Holm Pass | Haircut Pass | PBO Pass | OOS Pass | Robust Pass |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.00 | 0.00% | [0.00%, 1.88%] | 0.0% | 1.0% | 1.0% | 13.5% | 13.0% | 100.0% |
| 0.50 | 0.00% | [0.00%, 1.88%] | 0.0% | 1.0% | 5.5% | 18.5% | 34.5% | 100.0% |
| 1.00 | 0.50% | [0.09%, 2.78%] | 0.5% | 9.5% | 16.5% | 29.0% | 58.5% | 100.0% |
| 1.50 | 2.50% | [1.07%, 5.72%] | 3.5% | 22.0% | 36.5% | 41.0% | 71.5% | 100.0% |
| 2.00 | 6.50% | [3.84%, 10.80%] | 8.5% | 50.0% | 64.0% | 60.5% | 84.5% | 100.0% |
| 2.50 | 17.50% | [12.86%, 23.36%] | 21.5% | 71.5% | 81.5% | 77.0% | 90.0% | 100.0% |
| 3.00 | 33.50% | [27.32%, 40.30%] | 39.5% | 92.5% | 97.0% | 96.0% | 92.0% | 100.0% |

#### B. Sequential Conditional Admission Funnel $P(L_j \mid \bigcap_{i<j} L_i)$
| True $SR$ | $P(\text{DSR})$ | $P(\text{Holm} \mid \text{DSR})$ | $P(\text{Haircut} \mid \text{S2})$ | $P(\text{PBO} \mid \text{S3})$ | $P(\text{OOS} \mid \text{S4})$ | $P(\text{Joint} \mid \text{S5})$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.00 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 0.50 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 1.00 | 0.5% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 1.50 | 3.5% | 100.0% | 100.0% | 100.0% | 71.4% | 100.0% |
| 2.00 | 8.5% | 100.0% | 100.0% | 100.0% | 76.5% | 100.0% |
| 2.50 | 21.5% | 100.0% | 100.0% | 100.0% | 81.4% | 100.0% |
| 3.00 | 39.5% | 100.0% | 100.0% | 100.0% | 84.8% | 100.0% |

### Topology 2: Collinear Sweep Universe (1 Primary + 9 Correlated Perturbations $\rho=0.85$)
#### A. Marginal Layer Admission Rates
| True $SR$ | Joint $P(\text{PASS})$ | Wilson 95% CI | DSR Pass | Holm Pass | Haircut Pass | PBO Pass | OOS Pass | Robust Pass |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.00 | 0.00% | [0.00%, 1.88%] | 1.0% | 1.0% | 1.0% | 14.5% | 13.0% | 100.0% |
| 0.50 | 0.00% | [0.00%, 1.88%] | 5.5% | 2.0% | 5.5% | 12.0% | 34.5% | 100.0% |
| 1.00 | 0.50% | [0.09%, 2.78%] | 17.5% | 10.5% | 16.5% | 9.0% | 58.5% | 100.0% |
| 1.50 | 4.00% | [2.04%, 7.69%] | 37.0% | 25.5% | 36.5% | 19.5% | 71.5% | 100.0% |
| 2.00 | 5.00% | [2.74%, 8.96%] | 64.5% | 53.5% | 64.0% | 16.0% | 84.5% | 100.0% |
| 2.50 | 8.00% | [4.98%, 12.60%] | 80.5% | 74.5% | 81.5% | 14.5% | 90.0% | 100.0% |
| 3.00 | 11.50% | [7.79%, 16.66%] | 96.0% | 93.0% | 97.0% | 13.5% | 92.0% | 100.0% |

#### B. Sequential Conditional Admission Funnel $P(L_j \mid \bigcap_{i<j} L_i)$
| True $SR$ | $P(\text{DSR})$ | $P(\text{Holm} \mid \text{DSR})$ | $P(\text{Haircut} \mid \text{S2})$ | $P(\text{PBO} \mid \text{S3})$ | $P(\text{OOS} \mid \text{S4})$ | $P(\text{Joint} \mid \text{S5})$ |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.00 | 1.0% | 50.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| 0.50 | 5.5% | 36.4% | 100.0% | 0.0% | 0.0% | 0.0% |
| 1.00 | 17.5% | 60.0% | 100.0% | 14.3% | 33.3% | 100.0% |
| 1.50 | 37.0% | 66.2% | 100.0% | 24.5% | 66.7% | 100.0% |
| 2.00 | 64.5% | 82.2% | 100.0% | 16.0% | 58.8% | 100.0% |
| 2.50 | 80.5% | 91.9% | 100.0% | 12.2% | 88.9% | 100.0% |
| 3.00 | 96.0% | 96.9% | 100.0% | 13.4% | 92.0% | 100.0% |