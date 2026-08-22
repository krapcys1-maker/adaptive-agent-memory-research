# Replay synthesis: selection and phase matter more than repetition alone

Status: extracted synthesis; not an architecture decision

## Evidence boundary

Two observational rat experiments establish that neural replay can be temporally compressed and that awake replay content varies with task state. Two perturbation studies further show that disrupting ripple-associated activity can impair selected spatial-memory performance. They still do not establish that copying either pattern into an LLM memory system will improve performance, that decoded replay content rather than the wider SWR processing window is causal, or that broad disengaged replay performs systems consolidation.

| Reported observation | Strongest justified inference | Not yet justified |
| --- | --- | --- |
| waking-related sequences recur during later sleep and short sequences align with ripple states | replay can reactivate ordered experience under a different timescale/state | replay caused better retention or specifies an optimal compression ratio |
| engaged replay is local, congruent, and often forward | task state predicts which experience is reactivated | a dedicated planning module is necessary |
| engaged replay predicts near-term choice better than disengaged replay | replay content contains behavior-relevant information | replay itself caused the correct choice |
| disengaged replay is broader and more coherent with deep MEC | different network targets/modes accompany broad replay | this mode consolidated long-term memory in the measured experiment |
| post-training ripple disruption slows one spatial task | ripple-associated rest processing contributes causally under those conditions | decoded replay content is the unique cause or impairment is permanent |
| awake SWR disruption selectively impairs memory-demanding outbound alternation | awake SWR-associated processing contributes to a specific history-dependent decision | every task or the replay sequence itself requires the same mechanism |

## Engineering hypotheses to keep separate

1. **Selection:** which episodes enter a replay batch may matter more than replay volume.
2. **Phase:** online rehearsal near a decision and offline maintenance may require different sampling objectives.
3. **Compression:** shorter representations can increase maintenance throughput, but only if sequence, provenance, and exception fidelity survive.
4. **Interleaving:** diverse offline replay may reduce interference better than recency-only or reward-only replay.
5. **Destination:** replay for evidence retrieval, semantic consolidation, and procedural revision should be evaluated as different write targets.
6. **Content specificity:** matched sham/random maintenance is required to show that selected replay content, not extra computation, causes benefit.

## Candidate phase schedule — hypothesis only

```text
task-active / decision boundary
  -> retrieve contradictions and local task state
  -> rehearse a small evidence-linked working set
  -> do not update durable semantics merely because an item was retrieved

idle / explicit maintenance window
  -> sample diverse episodes under a fixed cost budget
  -> include rare, corrected, low-frequency, and negative examples
  -> propose derived updates with source links
  -> verify on held-out consequences before promotion
```

This schedule is not a biological replica. “Online” and “offline” describe engineering phases, not wake and sleep.

## Failure mechanisms that must be measured

- replay poisoning: adversarial or false events gain repeated exposure;
- rich-get-richer sampling: common/rewarded events eliminate rare exceptions;
- catastrophic semanticization: repeated summaries replace contradictory raw evidence;
- procedural perseveration: replay protects a once-useful rule after it changes;
- source laundering: a generated replay item loses the provenance of its episode;
- maintenance addiction: gains disappear when extra calls/tokens are counted;
- evaluation leakage: a sampler uses future test questions or answer labels.

## Current research decision

Replay remains in the benchmark portfolio, not the minimal architecture. Causal perturbation evidence upgrades ripple-associated processing from a correlation-only lead to a serious candidate, but not decoded replay content to an established mechanism. The raw archive remains sufficient for capture. A replay subsystem is only promoted if it beats retrieval-only, sham, and random maintenance at a frozen budget across a second corpus and reader/provider family, while preserving provenance and passing poison, rare-event, and rule-change guardrails.
