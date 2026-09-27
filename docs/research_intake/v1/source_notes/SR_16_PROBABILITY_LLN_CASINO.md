# SR-16 — Probability / LLN / Casino

SOURCE STATUS: EXTERNAL / UNVERIFIED
THIS FILE PRESERVES CLAIMS; IT DOES NOT ENDORSE THEM.

## 1. Source Context & Raw Claims
- **Source Medium**: Probability theory in trading video / casino mathematics lecture.
- **Preserved Mathematics & Casino Models**:
  - American Roulette Wheel Structure:
    - 18 Red pockets, 18 Black pockets, 2 Green pockets (0 and 00) = 38 total pockets.
    - Probability of Red: 18/38 (P(red) = 18/38 ≈ 47.368%).
    - Probability of Loss: 20/38 (P(loss) = 20/38 ≈ 52.632%).
  - Expected Value (EV) per $1 bet on Red:
    EV = (1 * 18/38) + (-1 * 20/38) = -2/38 ≈ -5.263% (-5.263%).
  - Single-bet standard deviation:
    0.9986 (sigma ≈ 0.9986).
  - Law of Large Numbers (LLN) Concept: As sample size n -> infinity, sample average converges to mathematical expectation.
  - Creator Claims:
    - Claims every roulette spin is "fair as a coin toss".
    - Presents probability of being ahead after n spins: claims n=10 ≈ 47%, n=50 ≈ 43%, n=100 ≈ 40%.
    - Assumes a commercial roulette table generates 500 spins/hour (500 spins/hour warning).

## 2. Human-Reviewed Scientific Critique
- **Weak Law / convergence in probability vs Strong Law distinction**: The Chebyshev inequality derivation presented in the source establishes Weak Law / convergence in probability (a Weak-Law-type result), NOT a mathematical proof of the Strong Law distinction (almost sure convergence).
- **Unfair Game**: Calling roulette "as fair as a coin toss" is `INCORRECT_AS_STATED`. The house edge (-5.263%) ensures asymmetric drift.
- **Exact Binomial Probabilities**: The source's claimed probabilities of being net ahead are mathematically incorrect:
  - Exact P(net ahead) for $1 bets on American roulette:
    - n = 10: Exact binomial probability is 31.41% (31.41%, NOT 47%).
    - n = 50: Exact binomial probability is 30.31% (30.31%, NOT 43%).
    - n = 100: Exact binomial probability is 26.50% (26.50%, NOT 40%).
- **Physical Rate Warning**: Assuming 500 roulette spins per hour per table implies 7.2 seconds per spin, which is physically impossible on a physical casino table (500 spins/hour warning).
- **Crucial ACASH Epistemological Lesson**: A casino has a known, stationary, mathematically proven negative expectation (-5.263%). A trading strategy has an **unknown, non-stationary** expectation that fluctuates across market regimes. The Law of Large Numbers cannot turn an unknown or negative-drift trading strategy into a guaranteed winning edge simply by generating more trades.

## 3. Mapping to ACASH Research Architecture
- **Mapped Research Mechanisms**:
  - Directly maps to [METHODOLOGY_CONTROLS.md](file:///docs/research_intake/v1/METHODOLOGY_CONTROLS.md).
- **Trial Status**: Preserved as a rigorous mathematical benchmark.
