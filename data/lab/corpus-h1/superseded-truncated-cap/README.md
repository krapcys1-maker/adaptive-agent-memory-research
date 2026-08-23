# Two arm runs superseded by an output-token cap

Kept as evidence, not as results. Both runs are superseded by re-runs at
`MAX_OUTPUT_TOKENS = 900`.

## What went wrong

`MAX_OUTPUT_TOKENS` was 200. The reader is a **reasoning model**, and on the
harder probes it spent the entire allowance thinking:

```
finish_reason              length
completion_tokens          200
completion_tokens_details  reasoning_tokens: 200
content                    ''
```

Five probes returned an empty string, all in `RARE-EXC`. The model had reached
the correct answer — its `reasoning_content` quotes the right flag and the right
suite — and had no budget left to write it down.

So the cap bit hardest on exactly the probes that needed the most thought, which
is the worst place for a measurement artifact to sit: it looks like difficulty.

## Why the empty answers were not obvious

They scored as ordinary failures. `answered` was 0, nothing else fired, and the
family simply looked hard. Nothing in the summary said *five of these probes
produced no answer at all*.

`empty` is now a reported outcome of its own, with a test, precisely so a future
truncation announces itself instead of hiding inside a failure count. A harness
fact and a model fact should never share a number.

## The numbers, for comparison against the re-runs

```
          gold    answered   leaked   abstained
fts5      0.881     0.798     0.131     0.000
recency   0.000     0.000     0.000     0.976
```

One result here survives the defect and is worth carrying forward: **`recency`
abstained on 97.6% of probes rather than confabulating.** Given a context window
containing nothing relevant, the reader said it did not know. Truncation cannot
manufacture an abstention — the model must produce the words "I do not know" —
so that figure is not an artifact of the cap.

That matters for how naive compaction should be described. It does not answer
these probes, and it also does not invent answers to them. Failing safely is a
different thing from failing, and a comparison that reported only `answered`
would have flattened the two together.

## Also recorded here

An earlier `fts5` invocation was launched with `nohup … &` *inside* a tool that
already backgrounds the command. The double-backgrounding killed the process
after 29 calls and the results were lost. The budget ledger caught the spend
($0.0136) even though no result file survived, which is the argument for
recording spend per call rather than per run.
