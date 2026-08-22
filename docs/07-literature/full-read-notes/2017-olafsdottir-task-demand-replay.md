# Ólafsdóttir et al. — Task Demands Predict a Dynamic Switch in the Content of Awake Hippocampal Replay

- Status: full text read; extracted; first challenge pass complete; primary rat electrophysiology study
- Version read: Neuron 96, article plus STAR Methods, 2017, 18 PDF pages
- Source: https://doi.org/10.1016/j.neuron.2017.09.035
- Cached file: `sources/papers/task-demand-replay-2017.pdf` (2,319,730 bytes)
- SHA-256: `1B13B8C0B4BFACC9D42BAF42B497A8790607F300ED50C94AD2D64DFA569D62FB`

## Research question, system, and method

Eight male Lister Hooded rats performed a self-paced rewarded Z-track task while CA1 place cells and medial-entorhinal cortex (MEC) grid cells were recorded. Twenty-four sessions passed decoding/data-quality exclusions. Corner immobility was divided into task-engaged periods immediately after arrival and before departure and intervening disengaged periods. Bayesian decoding, trajectory fitting, shuffle tests, LFP analyses, grid/place coherence, and cross-validated decision trees compared replay content across states.

## Extracted results

- Of 4,425 candidate reactivation events, 513 qualified as replay trajectories under an event-specific spatial-shuffle threshold (`p<0.025`; STAR Methods, pp. e2–e3). The trajectory analysis contained 149 engaged and 364 disengaged events (Results, p. 4).
- Engaged replay was more often congruent with current travel (60.82%, `p=0.024`), local (70.21%, `p<0.001`), and forward (75.8%, `p<0.0001`). Disengaged replay lacked congruence and direction bias and was more remote; the engaged/disengaged contrasts were significant for these reported measures (pp. 3–5, Figures 2–3).
- The content transition was brief and task-aligned: congruent/local biases persisted for roughly 10–15 seconds after corner arrival and before departure (p. 3, Figures 2D–E).
- Deep-MEC grid/place coordination was above chance during disengagement (`0.097`, SD `0.08`, `p=0.011`) but not engagement (`0.074`, SD `0.037`, `p=0.75`); the state difference was `p=0.0035` (p. 6, Figure 4).
- Before correct turns, engaged reactivations were congruent (62.79%, `p<0.0001`) and local (81.5%, `p<0.0001`); these biases were absent before errors. However, the engagement-by-accuracy interactions were not significant (`p=0.19` congruence; `p=0.14` locality) with 90 engaged and 121 disengaged error events (p. 7, Figure 5).
- A 10-fold cross-validated decision tree using engaged-event locality, congruence, and ripple power predicted correct/error outcome at 62.8% versus 49.6% mean shuffled accuracy (`p=0.001`). Disengaged events achieved 55.2% versus 49.8% shuffled (`p=0.09`; pp. 7–8).

## Limitations and challenge pass

- The study is observational; the authors explicitly say the causal link remains to be proven.
- Small animal and error-event counts make the positive within-state comparisons stronger than the nonsignificant state-by-accuracy interactions.
- The planning/consolidation functional labels are plausible interpretations. Immediate task prediction supports the planning interpretation more directly; the study did not measure delayed consolidation benefit from disengaged replay.
- Sessions and events are nested within eight animals, and several event-level bootstrap/classifier analyses can overstate independence if read as animal-level replication.
- Four rats were pretrained while four were recorded from first exposure, adding heterogeneous experience history.
- Data were available from authors on request, not as a pinned public artifact; the paper lists MATLAB and manual spike-sorting tools without a reproducible environment.

## Project relevance and falsifiable hypothesis

Test phase-conditioned replay rather than a single global priority queue: a small online budget for task-local, contradiction-aware rehearsal near decisions, and a separate offline budget for diverse, remote, cross-context evidence. Reject the split if it does not outperform matched uniform, recency, and diversity baselines on both immediate decisions and delayed transfer, or if it amplifies poison, common-event dominance, or procedural perseveration.

