"""How much of the extractor is knowledge about our own corpora?

Why this runs before an external benchmark, not after
------------------------------------------------------
``E2-A3`` scores 1.000 on dev-a and valid-b. Those splits share no question and
draw subjects from disjoint blocks, which controls for *wording*. Neither
controls for the rules having been written by someone who knows the seven
families and their vocabulary.

If the patterns are largely made of `staging`, `pytest`, `retry loop` and
`deployment key`, then 1.000 means *we solved our own taxonomy* — which is worth
knowing before spending an external benchmark to discover it. An external run is
a scarce resource: once seen, a benchmark becomes a development set.

What is counted
---------------
Each pattern is classified against two vocabularies, both taken from the corpus
generators rather than written here, so the audit cannot be tuned:

``corpus-specific``   contains a token that appears in H1's or H2's generated
                      text and nowhere in ordinary grammar — a service name, a
                      property noun, a tool name from the synthetic domain
``general``           matches a grammatical construction with no domain token —
                      possessives, prepositional objects, interrogative frames

The ratio is the finding. A high corpus-specific share does not mean the
approach is wrong; it means the *measurement* of it has not yet been made, and
that the number to report externally is unknown rather than 1.000.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

TARGETS = {
    "address_extract._ENTITY_PATTERNS": ("scripts/corpus/address_extract.py", "_ENTITY_PATTERNS"),
    "address_extract._PROPERTY_RULES": ("scripts/corpus/address_extract.py", "_PROPERTY_RULES"),
    "property_canon._PROPERTY_FORMS": ("scripts/corpus/property_canon.py", "_PROPERTY_FORMS"),
    "entity_canon._QUESTION_POSITIONS": ("scripts/corpus/entity_canon.py", "_QUESTION_POSITIONS"),
}

# Ordinary English and Polish function words plus regex syntax. Anything left
# after removing these is a content word, and a content word drawn from the
# synthetic domain is what this audit is looking for.
FUNCTION_WORDS = frozenset("""
a an the this that these those our your its their all any some one two
and or not for with from into onto to of in on at by as is are was were be been
should would could must can may might do does did has have had
what which where when why how before after now again today
per since between only every each no nor
i s w z na do od po pod nad za przed dla oraz jest sa byl byla nie tak
""".split())


def corpus_vocabulary() -> set[str]:
    """Content words the generators actually emit. Read, never hand-written."""
    words: set[str] = set()
    for name in ("history_family_spec.py",):
        text = (ROOT / "scripts" / "corpus" / name).read_text(encoding="utf-8")
        for match in re.findall(r'"([^"]{3,})"', text):
            for token in re.findall(r"[a-zA-Z]{3,}", match):
                token = token.lower()
                if token not in FUNCTION_WORDS:
                    words.add(token)
    generator = (ROOT / "scripts" / "build_temporal_corpus_h2.py")
    if generator.is_file():
        for match in re.findall(r'"([^"]{3,})"', generator.read_text(encoding="utf-8")):
            for token in re.findall(r"[a-zA-Z]{3,}", match):
                token = token.lower()
                if token not in FUNCTION_WORDS:
                    words.add(token)
    return words


def patterns_in(path: Path, symbol: str) -> list[str]:
    """The literal pattern strings in one declaration block."""
    text = path.read_text(encoding="utf-8")
    start = text.index(symbol)
    depth, end = 0, start
    for index in range(start, len(text)):
        if text[index] == "(":
            depth += 1
        elif text[index] == "{":
            depth += 1
        elif text[index] in ")}":
            depth -= 1
            if depth == 0:
                end = index
                break
    block = text[start:end]
    # Comments in these files deliberately quote example sentences from the
    # corpus, so counting them as patterns inflates the corpus-specific share —
    # in the audit's own favour, which is the direction most worth removing.
    code = "\n".join(line.split("#", 1)[0] for line in block.splitlines())
    return [p for p in re.findall(r'r?"((?:[^"\\]|\\.)+)"', code) if len(p) > 2]


def classify(pattern: str, vocabulary: set[str]) -> tuple[str, list[str]]:
    """Corpus-specific if it names a content word the generators emit."""
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z]{3,}", pattern)}
    tokens -= FUNCTION_WORDS
    # Regex keywords are not domain vocabulary.
    tokens -= {"az", "za", "zaz"}
    hits = sorted(tokens & vocabulary)
    return ("corpus-specific" if hits else "general"), hits


def run() -> dict[str, Any]:
    vocabulary = corpus_vocabulary()
    blocks: dict[str, Any] = {}
    total_specific = total = 0

    for label, (relative, symbol) in TARGETS.items():
        path = ROOT / relative
        if not path.is_file():
            continue
        rows = []
        for pattern in patterns_in(path, symbol):
            kind, hits = classify(pattern, vocabulary)
            rows.append({"pattern": pattern[:72], "kind": kind, "domain_tokens": hits[:6]})
        specific = sum(1 for r in rows if r["kind"] == "corpus-specific")
        total_specific += specific
        total += len(rows)
        blocks[label] = {
            "patterns": len(rows),
            "corpus_specific": specific,
            "general": len(rows) - specific,
            "corpus_specific_share": round(specific / len(rows), 3) if rows else None,
            "detail": rows,
        }

    return {
        "audit": "extractor coupling to the corpora it was written against",
        "corpus_vocabulary_size": len(vocabulary),
        "patterns_total": total,
        "corpus_specific_total": total_specific,
        "corpus_specific_share": round(total_specific / total, 3) if total else None,
        "by_block": blocks,
        "how_to_read_this": (
            "a high share does not mean the approach is wrong. It means E2-A3's 1.000 has not yet "
            "been shown to be about addressing rather than about this corpus's vocabulary, and that "
            "the number to expect externally is unknown rather than 1.000"
        ),
        "why_before_the_external_run": (
            "an external benchmark is spent once. Discovering there that the rules encode our own "
            "taxonomy would consume it to learn something free to learn here"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args(argv)

    report = run()
    if arguments.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("Extractor coupling to its own corpora\n")
        print(f"  {'block':<38}{'patterns':>9}{'specific':>10}{'general':>9}{'share':>8}")
        for label, block in report["by_block"].items():
            print(f"  {label:<38}{block['patterns']:>9}{block['corpus_specific']:>10}"
                  f"{block['general']:>9}{block['corpus_specific_share']:>8.3f}")
        print(f"\n  {'TOTAL':<38}{report['patterns_total']:>9}"
              f"{report['corpus_specific_total']:>10}"
              f"{report['patterns_total'] - report['corpus_specific_total']:>9}"
              f"{report['corpus_specific_share']:>8.3f}")
        print("\n  examples of corpus-specific patterns")
        shown = 0
        for block in report["by_block"].values():
            for row in block["detail"]:
                if row["kind"] == "corpus-specific" and shown < 8:
                    print(f"    {row['pattern'][:58]:<60} {row['domain_tokens'][:3]}")
                    shown += 1
        print(f"\n  {report['how_to_read_this']}")

    if arguments.out:
        destination = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(f"\nwritten: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
