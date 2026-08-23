# Citation compression and pack-order audit v0

Status: targeted primary-source and reusable-component audit before `PMLAB-PACK-001`

## Decision context from project memory

The project has already shown that retrieval quality, evidence validity, answerability, and reader use are different stages. `PMLAB-REUSE-CHAR-001` validated exact locator plumbing but found that repeated paths and bucket headers consume a fixed context budget. Its visible fixture is spent and may not be tuned.

The next unblocked question is therefore narrower: with a fixed candidate set and fixed byte budget, can a compact but reversible citation representation preserve more required evidence than repeated full locators? Ordering is characterized in the same fixture only as a capacity intervention. Reader behavior remains a later, separately registered experiment.

## Primary-source boundaries

### Short identifiers are established interfaces, not proof of support

ALCE presents retrieved passages as numbered documents and asks the reader to emit short references such as `[1][2]`. It separates citation recall (whether cited passages jointly support a statement) from citation precision (whether individual citations are relevant). This supports short, locally resolvable handles as a reader interface and supports separating locator validity from claim support. It does not test whether a footer dictionary is byte-optimal, and its NLI-based evaluator has known partial-support limitations.

Primary source: [Gao et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/).

### Compression is a lossy selection decision unless exact spans are preserved

RECOMP inserts a compressor between retrieval and the reader and permits an empty augmentation when retrieved material is irrelevant. LLMLingua and LongLLMLingua demonstrate that question-aware compression and reordering can reduce context cost and sometimes improve downstream performance. These methods justify compression and selective augmentation as comparator families. They do not preserve byte-identical evidence by construction, and their gains are reader-, task-, model-, and compression-ratio-dependent.

For this project, learned token deletion or abstractive summaries cannot replace the canonical evidence layer. They may later become derived reader views only if every retained claim remains traceable to exact source spans and omission is explicit.

Primary sources: [Xu et al., ICLR 2024](https://openreview.net/forum?id=mlJLVigNHp), [Jiang et al., ACL 2024](https://aclanthology.org/2024.acl-long.91/), [Pan et al., ACL Findings 2024](https://aclanthology.org/2024.findings-acl.57/).

### Order is model behavior, not a formatter-only property

Lost in the Middle shows that moving the same relevant document between the beginning, middle, and end can substantially change reader performance. LongLLMLingua includes document reordering as part of its long-context method. Consequently, a deterministic packer may measure which facts survive a budget, but it cannot declare `current-first`, relevance-first, or edge placement useful without a reader experiment that holds evidence and bytes constant.

Primary source: [Liu et al., TACL 2024](https://aclanthology.org/2024.tacl-1.9/).

## Reuse audit

| Candidate | Reusable concept | Why not adopt wholesale |
|---|---|---|
| ALCE | compact numeric evidence handles; citation recall/precision separation | End-to-end benchmark and NLI judge do not provide our exact local locator or validity contract |
| RECOMP | compression as an explicit stage; empty augmentation as a comparator | learned extractive/abstractive compression is model- and task-dependent and may alter evidence |
| LLMLingua family | budget control, question-aware selection, ordering comparator | heavy model dependency; token deletion is not byte-identical evidence preservation |
| `mnemos` | path-safe exact cited retrieval and deterministic rank traces | useful donor contract already characterized; does not answer compact-dictionary tradeoffs |
| `memo` | current/supporting/stale pack categories and omission ledger | authored categories and platform-specific implementation do not validate inference or reader use |

## Falsifiable hypotheses

- `H-PACK-01`: compact in-pack source handles plus a complete footer dictionary retain at least 0.05 more required evidence than repeated full locators at 768 UTF-8 bytes, with zero ambiguous or orphaned handles.
- `H-PACK-02`: compact-handle benefit is larger for long locators and repeated source reuse than for short unique locators.
- `H-PACK-03`: governance ordering changes which obligations survive a budget even when the candidate set is fixed; no ordering policy is promotable until a controlled reader experiment measures answer and stale-use effects.
- `H-PACK-04`: learned compression is unnecessary to test the citation-format mechanism and must not be introduced into the deterministic characterization.

## Investment decision

Invest first in a dependency-free factorial pack benchmark. Do not download LLMLingua or RECOMP weights yet. Their code remains a later comparator candidate only after the exact, reversible baseline and its reader protocol exist.
