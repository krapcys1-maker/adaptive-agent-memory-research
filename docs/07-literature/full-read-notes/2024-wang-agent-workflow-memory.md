# Wang, Mao, Fried & Neubig — Agent Workflow Memory

- Status: full text read; extracted; independent reproduction not run
- Version read: arXiv:2409.07429v1, 2024
- Source: https://arxiv.org/abs/2409.07429
- Code: https://github.com/zorazrw/agent-workflow-memory at `8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1`; Apache-2.0 read from `LICENSE`, no code execution
- Read artifact: 16 pages, 941281 bytes, SHA-256 `ddc6f6fedec48c88ae743b43a464f7eb4aecaab05acd18c29cfb657ab445ebe4`

## Authors' claim and method

AWM induces reusable procedural workflows from successful trajectories. Each workflow has a natural-language goal and a sequence of environment descriptions, reasoning and executable actions, with task-specific values abstracted into variables. Offline AWM induces workflows from training examples before testing. Online AWM instead processes the test stream, uses a learned evaluator to select apparently successful trajectories, and adds their workflows to memory for later test queries (Sections 2.2–2.3, pp. 3–4).

## Reported results

- WebArena, Table 1 (p. 5): `BrowserGymax-tree` scored 15.0 total SR with 7.9 steps, while AWM scored 35.5 total SR with 5.9 steps.
- WebArena, Table 5 (p. 8): rule-based and LM-based induction scored 35.6 and 35.5 SR, respectively, with 6.3 and 5.9 steps. The table does not support claiming that LM induction is inherently better here.
- Mind2Web, Table 4 (p. 8): online AWM's step SR was 43.6 cross-task, 33.9 cross-website and 35.5 cross-domain; MindAct scored 36.2, 30.1 and 18.6 in the same columns.
- Mind2Web, Table 11 (p. 16): offline+online was not additive. Its cross-domain step SR was 34.1, between offline AWM's 32.6 and online AWM's 35.5; its cross-task task SR was 1.6, below offline AWM's 4.8 and online AWM's 4.0.

## Limitations and competing interpretations

- Online AWM learns from the test stream. Its results are test-time adaptation, not evidence that a bank frozen before evaluation generalizes to untouched tasks. The paper also notes that incorrectly predicted trajectories can create harmful workflows (p. 8).
- The main tables report point estimates without variance. Experiments use GPT-3.5-turbo or GPT-4 at temperature 0, on WebArena and Mind2Web; they do not establish effects for small local models or ALFWorld, and there is no random-bank control.
- On Mind2Web cross-task, AWM's action F1 was below MindAct's despite higher element accuracy (Table 3, p. 7). The authors suggest that workflows can guide actions inappropriate for the current state. Fixed workflow actions also cannot react to intermediate pop-up options (Figure 7, p. 10).
- The comparison with Synapse supports an abstraction advantage in that setup, but does not isolate abstraction from workflow induction, prompt format and environment representation.

## Project consequence and falsifiable test

Treat procedural abstraction as a candidate representation, not a presumed improvement. Compare raw trajectories, rule-induced workflows and LM-induced workflows under the same model, task set, token budget and random/fixed-bank controls. Keep a frozen offline bank separate from an online growing bank, and record negative interactions and per-task gains and losses.

**Hypothesis:** abstract workflows will outperform raw and same-type random memories only for some task families. If matched-budget comparisons show no advantage over those controls, reject that advantage rather than attributing it to memory in general.
