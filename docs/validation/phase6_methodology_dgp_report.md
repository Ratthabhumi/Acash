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

## 4. Experiment D: Statistical Power Analysis (Detection Rate across True $SR$)

### Topology 1: Diverse Search Universe (1 True Alpha + 9 Exploratory Noise Models)
| True Annualized Sharpe | Simulations | Pass Count | Statistical Power $P(\text{PASS})$ | Wilson 95% CI |
| :---: | :---: | :---: | :---: | :---: |
| 0.00 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 0.50 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 1.00 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 1.50 | 50 | 2 | 4.00% | [1.10%, 13.46%] |
| 2.00 | 50 | 6 | 12.00% | [5.62%, 23.80%] |
| 2.50 | 50 | 10 | 20.00% | [11.24%, 33.04%] |
| 3.00 | 50 | 22 | 44.00% | [31.16%, 57.69%] |

### Topology 2: Collinear Sweep Universe (1 Primary + 9 Correlated Perturbations $\rho=0.85$)
| True Annualized Sharpe | Simulations | Pass Count | Statistical Power $P(\text{PASS})$ | Wilson 95% CI |
| :---: | :---: | :---: | :---: | :---: |
| 0.00 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 0.50 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 1.00 | 50 | 0 | 0.00% | [0.00%, 7.13%] |
| 1.50 | 50 | 3 | 6.00% | [2.06%, 16.22%] |
| 2.00 | 50 | 2 | 4.00% | [1.10%, 13.46%] |
| 2.50 | 50 | 4 | 8.00% | [3.15%, 18.84%] |
| 3.00 | 50 | 9 | 18.00% | [9.77%, 30.80%] |