# Source-grounded structured memory — engineering development

This candidate adds the missing text-to-fact-to-answer flow without changing
Claude's frozen kernels or NIE's personality, prompts or deployment. It is a
working development implementation, not a validated universal adaptive memory.

## Complete hard development results

Same spent 100-question FC-MH 262k corpus as PR #104; exact matching remains the
primary measure. One **local-derived** graph is shared by both planners.

| Question routing | Local Qwen 14B | DeepSeek V4.1 Flash |
|---|---:|---:|
| Free relation sequence (v3) | 25/100 | 19/100 |
| Executable schema options (v5) | **55/100** | **59/100** |

The earlier local iterative raw-text run was 4/100. This is an engineering
comparison on already inspected questions, with a different representation and
system execution; it is not a leaderboard replication or evidence of superiority
over another company. The 80/100 development aspiration is **not met**.

The complete capture saved 18,333 raw sources, accepted 18,328 claims, retained
four quarantined extractions and one empty header. Local Qwen 14B made 110
extraction calls; 18,223 sources used learned literal shells. There are 53
informative templates and 48 predicate labels. Span checks and repeatable paths
do not establish semantic extraction accuracy. `is` and other weak labels remain
known representation risks. Failed and cutoff captures remain in the evidence.

Models choose relation paths/options, not final values. Code executes the chosen
path over current facts and returns a literal value plus source IDs. The v5
model input contains question, literal anchors, relation sentence shells and
option IDs, **not terminal answer values or gold**. A separate artifact audit
reconstructs the exact choices, requests and paths. No model acts as a judge.

## Entry points and contracts

- `tools/structured_memory_v1.py`: canonical append-only source/extraction log,
  literal-span validation, separate effective/recording clocks, conflicts,
  explicit supersession and read-only multi-hop execution.
- `tools/structured_memory_v2.py`: versioned informative-shell/specificity fix.
- `tools/structured_memory_cli_v1.py`: offline source/extract/resolve/query/status
  CLI. It requires no model credentials. Source JSON is a `Source` dataclass;
  extraction JSON contains `claims`. Do not supply benchmark gold as claims.
- `scripts/structured_memory_pipeline_v1.py`: frozen capture/query/score runner.
  v2 adds explicit extraction examples/native local schema; v3 selects the
  corrected runtime. v4 exclusively copies a frozen prefix and completes
  unattempted sources, preserving quarantines and earlier attempts.
- `scripts/structured_memory_paths_v5.py`: bounded, scoped executable-path
  selection. At most six hops, 96 schemas, 512 expansions, and 5900 input bytes;
  truncation and abstention remain visible in the outputs.
- `scripts/audit_structured_memory_v1.py`: artifact reconstruction including
  causal template provenance and offered/selected schema options (`--cache-version 2`).
- `scripts/diagnose_structured_memory_v1.py`: separately labelled post-hoc
  coverage and fixed-plan oldest-state intervention; never used at inference.

```bash
python tools/structured_memory_cli_v1.py --store /absolute/path/memory.jsonl status
python tools/structured_memory_cli_v1.py --store /absolute/path/memory.jsonl source --input /absolute/path/source.json
python tools/structured_memory_cli_v1.py --store /absolute/path/memory.jsonl extract --source-id note-1 --input /absolute/path/proposal.json
python tools/structured_memory_cli_v1.py --store /absolute/path/memory.jsonl resolve --scope fiction-profile --subject Mira --predicate lives_in --valid-at 30 --known-at 30
```

One writer owns an exclusive lock. A torn or corrupted canonical log stops
loading; no automatic deletion or silent recovery. Original text survives a
failed extraction. Identity collisions cannot rewrite a source. A lookup never
creates, corrects or overwrites a fact. Generic sources default to **conflict**
when incompatible assertions remain; MAB's ordered single-value rule is an
explicit source policy, not the default for ordinary conversations.

## Evidence and limits

Read [PLAN](PLAN.md) and the versioned amendments in order. Source/capture and
every complete query output were Git-frozen before separate scoring. Earlier
cutoff runs are not reported as complete. `failed-captures.json` preserves their
raw hashes; v4 reports inherited versus newly generated calls and unchanged
prefix bytes. Full raw data stays outside Git in the dated external run folder.

Total for this development boundary: 783 actual generations, **494 local and
289 Flash**. API permanent reservations $1.156; peak/uncached usage upper estimate
$0.043056, cumulative cap $2/400 attempts, zero unknown usage. The ledger retains
all earlier failed paid capture calls. No Pro, alternate model, hidden retry,
model judge or model project-planning call. Shared/inherited capture logs must
not be double-counted as new generations.

Aliases, minimal value spans, pronouns, predicate collisions, ordinary prose,
multi-valued relations and extraction semantics remain open. In particular,
99.97% accepted source coverage is **not** 99.97% correct facts. H1's derived-chain
OBSOLETE leakage, free-prose NIE transfer and fresh hard external validation are
still required before integration claims. No sealed confirmation data was used.

The upstream benchmark uses normalized substring match, which differs from our
primary exact score; any supplementary SubEM reading must be separately labelled.
Some raw latest-fact chains also disagree with supplied gold in inspected cases;
retain those misses and audit the discrepancy rather than changing state rules
to fit answers. See the continuing post-hoc diagnosis, not an assumption that
every remaining error is a benchmark defect.
