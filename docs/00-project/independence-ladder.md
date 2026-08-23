# Independence ladder

Status: proposed operating protocol  
Replaces: the binary "independent reviewer must not be the author" gate  
Scope: how a claim earns the right to be promoted out of exploratory status

## The problem this solves

Independent review is currently a binary attribute of a person: the reviewer must
not be the author, and must not belong to a model family already used for advisory
work. The project has one maintainer and no volunteer reviewers. The result is that
four review packets are complete and waiting with no reviewer, and roughly a third
of the experiment registry consists of preregistrations that can never execute.

The gate is not merely inconvenient. It is also weaker than it appears, by the
project's own evidence:

- same-cue lexical agreement was explicitly rejected as independent confidence
  evidence because two backends shared common-mode error;
- a DeepSeek advisory pass agreed with author gold on 40/44 rows, yet all four of
  its objections were wrong in the same two ways across both languages;
- strict exact-object agreement on a later 110-row pass was 18/110 and turned out
  to be representation-confounded rather than substantive.

Agreement between two processes that share a failure mode is not evidence. Absence
of a second person is not the only thing that can make review non-independent.

## The reframe

> Independence is decorrelation of errors between the process that produces a
> claim and the process that checks it.

This is a measurable property rather than a credential. It follows that
independence is not binary and not a person-attribute. It should be recorded as a
tier, and each tier should state what it actually rules out, what it cannot rule
out, and how its independence is measured rather than asserted.

## The ladder

### I0 — Mechanical invariant

An executable property decidable from the bytes of the artifact. No reviewer, no
model, no network.

Examples: a span is an exact substring of its source; an obligation graph is
acyclic with backward-only edges; a timestamp normalizes under the declared
grammar; a certificate names predicate, entity, time, and scope; `events.jsonl` is
append-only.

- **Rules out:** construction defects, contract violations, silent corruption,
  representation drift.
- **Cannot rule out:** a well-formed label that is simply wrong.
- **Independence basis:** the checker is written against the contract, not against
  the labels, so its errors are uncorrelated with labelling errors.
- **How it is measured:** mutation testing. Inject a registered set of defects and
  require a detection rate; an undetected class is a declared blind spot.

**Binding rule: every label that can be checked mechanically must be checked
mechanically before any human or model is asked to look at it.** This is the single
largest unblocking move available, because a large share of what is currently
queued for expert review is contract validity, not judgement.

### I1 — Sealed held-out challenge

Generate a case pool with a documented generator. Split it into development and
challenge halves by HMAC of the case identifier under a key whose hash is published
but whose value stays sealed. The author builds against development only. The
challenge half is unsealed only after the candidate implementation hash is
published.

- **Rules out:** tuning to the test set, post-hoc threshold selection, and the
  "post-freeze but same-process" weakness recorded against the PMLAB-MAP challenge.
- **Cannot rule out:** a generator that encodes the author's blind spot into both
  halves.
- **Independence basis:** informational and temporal separation, enforced
  cryptographically rather than by good intentions.
- **How it is measured:** any third party can recompute the split from the revealed
  key and confirm the candidate hash predates the reveal.

This tier gives genuine held-out evaluation with a single author. It is the most
undervalued mechanism currently missing from the project.

### I2 — Adversarial self-review

The author, or a model operated by the author, is permitted only to attempt
refutation against preregistered kill criteria. Confirming evidence produced at
this tier is discarded by construction.

- **Rules out:** some overclaiming and some obvious defects.
- **Cannot rule out:** anything the author cannot imagine being wrong about.
- **Independence basis:** none is claimed.
- **Binding rule: I2 never satisfies a promotion gate on its own.** It is a filter
  applied before spending scarcer review capacity, not evidence.

### I3 — Cross-family model panel with measured decorrelation

Rather than asserting that a model family "is not independent", measure it. Run at
least two families over items where I0 supplies mechanical ground truth, then
compute and publish the pairwise error correlation.

- If the correlation is high, the panel counts as **one** reviewer and must be
  reported that way.
- If it is low on the mechanically checkable subset, that is evidence, though not
  proof, of partial decorrelation on the judgement subset.
- **Rules out:** single-family idiosyncrasy, when the correlation is measured low.
- **Cannot rule out:** bias shared through overlapping pretraining data.
- **How it is measured:** the correlation coefficient is the deliverable. A panel
  without a reported coefficient is recorded as asserted, not measured.

This converts today's unfalsifiable blocker into a number that can be argued with.

### I4 — Human micro-task panel

Decompose monolithic review into self-contained single-judgement tasks of roughly
sixty seconds, with redundancy of at least three annotators per item and
gold-seeded attention checks.

- **Rules out:** author-specific misreadings, when annotators are naive to the
  hypothesis under test.
- **Cannot rule out:** systematic bias introduced by the instructions themselves.
- **Independence basis:** annotator naivety plus redundancy.
- **How it is measured:** inter-annotator agreement and gold-check pass rate, both
  reported per batch.

This tier exists because the current ask does not fit volunteer behaviour. Almost
nobody will blind-review 134 paired rows and sign an attestation. Many people will
answer ten yes-or-no questions about exact substrings. The evidence obtained is
comparable; the request is achievable.

### I5 — Full expert blind review

The existing gold standard, unchanged. It remains the strongest tier and the only
one that can support a confirmatory claim. It stops being the only door.

## Binding rules

1. Every accepted claim records the **highest tier that actually produced it**. No
   claim inherits a tier from a neighbouring result.
2. I2 alone never promotes anything.
3. Where a tier defines a measurement, an unmeasured instance of that tier is
   recorded as `asserted`, not as the tier itself.
4. Author identity is recorded explicitly, including when the author is an AI agent
   operating under a maintainer's account.
5. A tier may be *lowered* by evidence of shared failure modes. Discovering that two
   supposedly independent checks fail together is itself a recordable finding.

## Where the current author sits

The maintainer has assigned the author role to an AI agent. Under this protocol that
is admissible and must be stated rather than hidden. The agent may author, may
operate I0, I1, I3, and I4 harnesses, and may serve as an I2 adversarial reviewer.

The agent **cannot** serve as the project's I5 independent reviewer for its own
work, because its errors correlate with its authoring by construction. The purpose
of this ladder is not to let the author grade itself. It is to make most claims
gradeable without an expert reviewer at all, so that scarce I4 and I5 capacity is
spent only where judgement is genuinely required.

## Immediate consequences

- The four stalled packets are re-routed: the mechanically checkable portion moves
  to I0, and the remainder is decomposed into I4 micro-tasks.
- `PMLAB-MAP-STAGE-001` is re-issued with a sealed split under I1, which addresses
  the recorded "same-process, not independently held out" defect directly.
- The DeepSeek advisory role is relabelled I3 and must report an error-correlation
  coefficient, or be recorded as asserted.
- Claims currently blocked solely on "independent review required" are re-examined
  to determine which were never judgement problems in the first place.
