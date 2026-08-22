# Jakob and Gershman — Rate-distortion theory of neural coding and its implications for working memory

- Status: full text read; extracted; first challenge pass complete; independent reanalysis pending
- Version read: eLife article PDF, 19 article pages plus methods/reviews, 2023
- Source: https://elifesciences.org/articles/79450
- Code reported by publisher: https://github.com/amvjakob/wm-rate-distortion
- Cached file: `sources/papers/rate-distortion-working-memory-79450.pdf` (1,098,887 bytes)
- SHA-256: `94DD5AD9D117FF693BC9857899FACFFABEC2F32B0350D8D36C228E0A3B3747EE`

## Research question

Can a biologically plausible spiking population code operate near a rate-distortion frontier and jointly explain structured visual working-memory errors?

## Data, method, and comparison

The authors derive a population-coding model with intrinsic gain adaptation and compare a full rate-distortion model, a population-coding baseline, fixed-gain RD, and no-plasticity RD. They reanalyze five human datasets and one monkey dataset; individual experiments yield eight rows in the model-comparison table. Neural evidence is a reanalysis of two monkeys' dorsolateral prefrontal recordings.

## Extracted results

- The model targets effects of set size, stimulus prioritization, timing, serial dependence, systematic bias, and gain adaptation (Figures 2–7, pp. 7–15).
- Random-effects Bayesian comparison favored the full RD model in seven of eight table rows. Protected exceedance probability for the full model averaged 0.76; Bays (2014) Experiment 1 did not discriminate strongly and favored fixed gain numerically (`0.4128` versus full RD `0.2286`; Table 1, p. 16).
- In the two-monkey reanalysis, current-trial squared error was lower after above-average previous error (`p<0.001`); session mean squared error correlated negatively with fitted neural gain (`r=-0.32`, `p<0.02`; Figure 8, pp. 16–17).
- The authors propose catecholamines, including dopamine and norepinephrine, as possible biological gain-control mechanisms, while calling for direct continuous-report pharmacological tests (Open questions, pp. 18–19).

## Limitations and challenge pass

- The model covers a restricted family of visual delayed-response tasks; serial order, AX-CPT, N-back, natural images, and sequences are outside scope (p. 19).
- The biological capacity constraint and gain controller are hypotheses, not established mechanisms.
- The neural reanalysis has `N=2` monkeys and is correlational with respect to the proposed gain mechanism.
- Strong model comparison across reused datasets is not an out-of-sample test of an LLM memory architecture.
- Optimizing distortion predicts structured error under scarcity; it does not justify deleting source evidence when disk capacity is cheap.

## Project relevance

Memory quality should be evaluated with a consequence/task-weighted distortion function as well as exact reconstruction. This supports a fixed active-context budget with unequal allocation, but the raw archive should remain available for correction.

## Falsifiable hypothesis

At a fixed retrieval-token budget, allocating evidence by preregistered consequence weights should lower risk-weighted error than uniform allocation without hiding a rise in unweighted critical misses. Reject if gains disappear across query distributions or require using held-out answers to set the weights.
