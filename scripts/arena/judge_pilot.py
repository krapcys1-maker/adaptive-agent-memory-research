#!/usr/bin/env python3
"""Score the sixteen frozen pilot answers with LongMemEval's own evaluator.

Not a new criterion. The benchmark ships one, and inventing a second would make
this project's numbers incomparable with everyone else's — the whole reason for
running an external benchmark in the first place.

    src/evaluation/evaluate_qa.py, LongMemEval @ 9e0b455f

Reproduced exactly: the five per-question-type prompt templates and the
abstention template, `temperature=0`, `max_tokens=10`, `n=1`, and the label rule,
which is literally `'yes' in response.lower()`. The evaluator is **binary**. It
has no partial credit and no third class, and a response that carries only a
subset of the required information is scored wrong by its own instruction.

The one deviation, stated plainly
----------------------------------
Their `model_zoo` offers `gpt-4o-mini-2024-07-18`, `gpt-4o-2024-08-06`, or a
local Llama-3.1-70B. This machine has a DeepSeek credential and no OpenAI one,
so the judge model is `deepseek-chat`. Prompt, parameters and label rule are
theirs; the model is not. Scores from this run are therefore comparable *within*
this run and are not directly comparable with published LongMemEval numbers.

Blind by construction
---------------------
The official prompt contains only question, gold and response — no system name —
so blindness is a property of the evaluator rather than something added here.
The anonymous labels are assigned anyway and the mapping is written to a separate
file, so that the ordering of requests carries no information either.

Two passes, because temperature zero is not determinism
--------------------------------------------------------
Measured on this provider: 3 distinct outputs in 20 identical structured
requests. So every answer is judged twice; only where the two disagree is a third
judgement taken, and the majority of three decides. Every raw judgement is kept,
including the ones that were overruled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from arena.decoding import PRICE_PER_MTOK, FixedDecoding, SpendCapReached  # noqa: E402
from arena.spend_ledger import SpendLedger  # noqa: E402

RAW = ROOT / "data/lab/arena/pilot-raw"
SELECTION = ROOT / "data/lab/arena/pilot-selection.json"
SYSTEMS = ("aamr", "mem0", "cupmem", "hindsight")

#: Verbatim from LongMemEval `src/evaluation/evaluate_qa.py` @ 9e0b455f. Not
#: reworded, not shortened, not adapted. A judge prompt is part of a benchmark's
#: definition, and editing one silently redefines the benchmark.
GENERIC = ("I will give you a question, a correct answer, and a response from a model. "
           "Please answer yes if the response contains the correct answer. Otherwise, "
           "answer no. If the response is equivalent to the correct answer or contains "
           "all the intermediate steps to get the correct answer, you should also answer "
           "yes. If the response only contains a subset of the information required by "
           "the answer, answer no. \n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel "
           "Response: {}\n\nIs the model response correct? Answer yes or no only.")

TEMPORAL = ("I will give you a question, a correct answer, and a response from a model. "
            "Please answer yes if the response contains the correct answer. Otherwise, "
            "answer no. If the response is equivalent to the correct answer or contains "
            "all the intermediate steps to get the correct answer, you should also answer "
            "yes. If the response only contains a subset of the information required by "
            "the answer, answer no. In addition, do not penalize off-by-one errors for "
            "the number of days. If the question asks for the number of days/weeks/months, "
            "etc., and the model makes off-by-one errors (e.g., predicting 19 days when "
            "the answer is 18), the model's response is still correct. \n\nQuestion: {}"
            "\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model response "
            "correct? Answer yes or no only.")

KNOWLEDGE_UPDATE = ("I will give you a question, a correct answer, and a response from a "
                    "model. Please answer yes if the response contains the correct answer. "
                    "Otherwise, answer no. If the response contains some previous "
                    "information along with an updated answer, the response should be "
                    "considered as correct as long as the updated answer is the required "
                    "answer.\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}"
                    "\n\nIs the model response correct? Answer yes or no only.")

PREFERENCE = ("I will give you a question, a rubric for desired personalized response, and "
              "a response from a model. Please answer yes if the response satisfies the "
              "desired response. Otherwise, answer no. The model does not need to reflect "
              "all the points in the rubric. The response is correct as long as it recalls "
              "and utilizes the user's personal information correctly.\n\nQuestion: {}"
              "\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response correct? "
              "Answer yes or no only.")

ABSTENTION = ("I will give you an unanswerable question, an explanation, and a response "
              "from a model. Please answer yes if the model correctly identifies the "
              "question as unanswerable. The model could say that the information is "
              "incomplete, or some other information is given but the asked information "
              "is not.\n\nQuestion: {}\n\nExplanation: {}\n\nModel Response: {}\n\nDoes "
              "the model correctly identify the question as unanswerable? Answer yes or "
              "no only.")

BY_TYPE = {
    "single-session-user": GENERIC,
    "single-session-assistant": GENERIC,
    "multi-session": GENERIC,
    "temporal-reasoning": TEMPORAL,
    "knowledge-update": KNOWLEDGE_UPDATE,
    "single-session-preference": PREFERENCE,
}

#: Their kwargs, unchanged.
JUDGE_PARAMS = {"n": 1, "temperature": 0, "max_tokens": 10}


def prompt_for(qtype: str, question: str, gold: str, response: str,
               abstention: bool) -> str:
    if abstention:
        return ABSTENTION.format(question, gold, response)
    template = BY_TYPE.get(qtype)
    if template is None:
        raise NotImplementedError(f"no official template for question type {qtype!r}")
    return template.format(question, gold, response)


def label_of(text: str) -> bool:
    """Their rule, character for character: `'yes' in eval_response.lower()`."""
    return "yes" in (text or "").strip().lower()


def degenerate(response: str, abstention: bool) -> str | None:
    """Why this answer must not be sent to the judge at all, or None.

    An empty response is outside the evaluator's domain. LongMemEval's own runner
    always produces a hypothesis string, and its abstention branch keys on the
    question id ending in `_abs`, not on the response being blank. Handed
    "Model Response: " with nothing after it, the judge answered **yes** on four
    out of four — deterministically, both passes, for a system that had stored
    nothing and abstained on everything.

    Scored by the evaluator's own stated criterion — "answer yes if the response
    contains the correct answer" — an empty response contains nothing and is
    wrong. That is applying their rule to an input their code never sees, not
    inventing a second criterion.

    Left to itself this would have handed the arena's deliberate floor arm a
    perfect score, and any system could obtain one by declining to answer.
    """
    if abstention:
        # On a genuinely unanswerable question the abstention template asks
        # whether the model identified it as unanswerable, and a blank response
        # is a real, if terse, judgement call. Left to the judge.
        return None
    if not (response or "").strip():
        return ("empty response to an answerable question: nothing to contain the "
                "correct answer")
    return None


def anonymous_label(system: str, salt: str) -> str:
    """A stable pseudonym per system, from a recorded salt.

    Deterministic rather than random, so the assignment can be reproduced and
    checked afterwards. It is not a secret; it is a guarantee that request order
    carries no system identity either.
    """
    digest = hashlib.sha256(f"{salt}{system}".encode()).hexdigest()
    return f"candidate_{chr(65 + int(digest[:8], 16) % 26)}_{digest[:4]}"


def load_cases(selection_path: Path, systems: tuple[str, ...],
               raw_files: dict[str, list[Path]]) -> list[dict[str, Any]]:
    """Every frozen answer to be judged, from one or more raw files per system.

    A system's answers can come from more than one run — the expansion reuses the
    pilot's four units and pays only for six new ones — so each raw file is read
    and the run it came from is carried through to the judgement. Answers are
    taken exactly as the systems produced them: not trimmed, not normalised, not
    repaired, not reordered.
    """
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    by_qid = {u["question_id"]: u for u in selection["units"]}
    cases: list[dict[str, Any]] = []
    for system in systems:
        for path in raw_files[system]:
            for entry in json.loads(path.read_text(encoding="utf-8")):
                unit = by_qid.get(entry["question_id"])
                if unit is None:
                    continue  # an answer to a unit this selection does not contain
                cases.append({
                    "system": system,
                    "run": path.stem,
                    "question_id": entry["question_id"],
                    "question_type": unit["question_type"],
                    "slot": unit["slot"],
                    "question": entry["question"],
                    "gold": entry["gold"],
                    # Frozen. Not trimmed, not normalised, not repaired.
                    "response": entry["answer"],
                    "abstention": entry["question_id"].endswith("_abs"),
                })
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--cap-usd", type=float, default=0.25)
    parser.add_argument("--salt", default="arena-pilot-judge-v1")
    parser.add_argument("--out", default=str(ROOT / "data/lab/arena/pilot-judged.json"))
    parser.add_argument("--mapping-out",
                        default=str(ROOT / "data/lab/arena/pilot-judge-blinding.json"))
    parser.add_argument("--project-only", action="store_true")
    parser.add_argument("--selection", default=str(SELECTION))
    parser.add_argument("--systems", default=",".join(SYSTEMS))
    parser.add_argument("--raw", action="append", default=None,
                        help="system=path, repeatable; defaults to pilot-raw/<system>.json")
    args = parser.parse_args()

    systems = tuple(s.strip() for s in args.systems.split(",") if s.strip())
    raw_files: dict[str, list[Path]] = {s: [] for s in systems}
    for spec in (args.raw or []):
        system, _, path = spec.partition("=")
        raw_files[system.strip()].append(Path(path.strip()))
    for system in systems:
        if not raw_files[system]:
            raw_files[system] = [RAW / f"{system}.json"]

    cases = load_cases(Path(args.selection), systems, raw_files)
    blinding = {system: anonymous_label(system, args.salt) for system in systems}

    # -- projection, before a single call ------------------------------------
    prompts = [prompt_for(c["question_type"], c["question"], c["gold"],
                          c["response"], c["abstention"]) for c in cases]
    #: Four characters per token is the usual rough conversion; deliberately
    #: generous, because a projection that under-states is how a cap gets passed.
    projected_prompt_tokens = sum(len(p) for p in prompts) // 4 * 2  # two passes
    projected_usd = round(
        projected_prompt_tokens / 1e6 * PRICE_PER_MTOK["input"]
        + len(cases) * 2 * JUDGE_PARAMS["max_tokens"] / 1e6 * PRICE_PER_MTOK["output"], 6)

    print(f"{len(cases)} answers x 2 passes = {len(cases) * 2} calls")
    print(f"projected ~{projected_prompt_tokens} prompt tokens, ${projected_usd:.4f} "
          f"against a ${args.cap_usd:.2f} cap")
    if projected_usd > args.cap_usd:
        raise SystemExit(f"projection ${projected_usd} exceeds the cap; stopping")
    if args.project_only:
        return 0

    from openai import OpenAI

    from arena.run_pilot import load_key

    ledger = SpendLedger(run_id="pilot-judge")
    client = FixedDecoding(OpenAI(api_key=load_key(), base_url=args.base_url),
                           fixed={"temperature": JUDGE_PARAMS["temperature"]},
                           spend_cap_usd=args.cap_usd, shared_ledger=ledger)

    def judge(case: dict[str, Any], prompt: str, pass_name: str) -> dict[str, Any]:
        response = client.chat.completions.create(
            model=args.model, messages=[{"role": "user", "content": prompt}],
            n=JUDGE_PARAMS["n"], max_tokens=JUDGE_PARAMS["max_tokens"])
        text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        return {
            "pass": pass_name,
            "raw": text,
            "label": label_of(text),
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        }

    judged: list[dict[str, Any]] = []
    stopped = None
    try:
        for case, prompt in zip(cases, prompts):
            reason = degenerate(case["response"], case["abstention"])
            if reason is not None:
                judged.append({
                    "candidate": blinding[case["system"]],
                    "question_id": case["question_id"],
                    "question_type": case["question_type"],
                    "slot": case["slot"],
                    "response_chars": len(case["response"]),
                    "abstention_prompt": case["abstention"],
                    "run": case["run"],
                    "passes": [],
                    "stable": True,
                    "disputed": False,
                    "label": False,
                    "not_sent_to_judge": reason,
                    "_system": case["system"],
                })
                continue
            # Everything the judge sees, and nothing else. The system name is not
            # in the prompt because the official prompt has no place for it.
            passes = [judge(case, prompt, "A"), judge(case, prompt, "B")]
            if passes[0]["label"] != passes[1]["label"]:
                passes.append(judge(case, prompt, "C"))
            votes = [p["label"] for p in passes]
            final = sum(votes) > len(votes) / 2
            judged.append({
                "candidate": blinding[case["system"]],
                "question_id": case["question_id"],
                "question_type": case["question_type"],
                "slot": case["slot"],
                "response_chars": len(case["response"]),
                "abstention_prompt": case["abstention"],
                "run": case["run"],
                "passes": passes,
                "stable": passes[0]["label"] == passes[1]["label"],
                "disputed": len(passes) == 3,
                "label": final,
                # Written last and read only when the table is built.
                "_system": case["system"],
            })
    except SpendCapReached as stop:
        stopped = str(stop)

    prompt_tokens = sum(p["prompt_tokens"] for j in judged for p in j["passes"])
    completion_tokens = sum(p["completion_tokens"] for j in judged for p in j["passes"])
    record = {
        "artifact": "arena-pilot-judged",
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selection": json.loads(Path(args.selection).read_text(encoding="utf-8"))["selection_sha256"],
        "selection_id": json.loads(Path(args.selection).read_text(encoding="utf-8")).get("selection_id"),
        "raw_files": {s: [str(p) for p in raw_files[s]] for s in systems},
        "protocol": {
            "source": "LongMemEval src/evaluation/evaluate_qa.py",
            "repository": "xiaowu0162/LongMemEval",
            "commit": "9e0b455f4ef0e2ab8f2e582289761153549043fc",
            "templates_verbatim": True,
            "template_sha256": {
                name: hashlib.sha256(template.encode()).hexdigest()
                for name, template in (("generic", GENERIC), ("temporal", TEMPORAL),
                                       ("knowledge_update", KNOWLEDGE_UPDATE),
                                       ("preference", PREFERENCE),
                                       ("abstention", ABSTENTION))
            },
            "label_rule": "'yes' in response.lower(); binary, no partial credit",
            "parameters": JUDGE_PARAMS,
        },
        "judge_model": {
            "model": args.model,
            "provider": "DeepSeek",
            "official_model_zoo": ["gpt-4o-mini-2024-07-18", "gpt-4o-2024-08-06",
                                   "meta-llama/Meta-Llama-3.1-70B-Instruct"],
            "deviation": ("this machine has a DeepSeek credential and no OpenAI one. "
                          "Prompt, parameters and label rule are LongMemEval's; the "
                          "model is not. Scores here are comparable within this run "
                          "and NOT directly comparable with published LongMemEval "
                          "numbers"),
            "seed": "not supported by this provider",
            "determinism": ("not assumed. Measured at 3 distinct outputs in 20 "
                            "identical structured requests, which is why every answer "
                            "is judged twice"),
        },
        "blinding": {
            "method": "stable pseudonym per system from sha256(salt + system)",
            "salt": args.salt,
            "note": ("the official prompt carries only question, gold and response, so "
                     "no system identity could reach the judge in any case"),
            "mapping_file": Path(args.mapping_out).name,
        },
        "cost": {
            "calls": len(client.request_log),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "usd": round(client.spent_usd, 6),
            "cap_usd": args.cap_usd,
            "projected_usd": projected_usd,
        },
        "stopped_by_cap": stopped,
        "judgements": judged,
    }
    Path(args.out).write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    Path(args.mapping_out).write_text(
        json.dumps({"salt": args.salt, "mapping": blinding}, indent=2) + "\n",
        encoding="utf-8")

    print(f"judged {len(judged)}/{len(cases)}  "
          f"{len(client.request_log)} calls  ${client.spent_usd:.4f}")
    print(f"stable {sum(1 for j in judged if j['stable'])}  "
          f"disputed {sum(1 for j in judged if j['disputed'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
