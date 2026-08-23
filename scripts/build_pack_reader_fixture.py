#!/usr/bin/env python3
"""Build the fresh grouped fixture and opaque schedule for PMLAB-PACK-READER-001."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "lab" / "pmlab-pack-reader-v0"
SALT = "pmlab-pack-reader-v0-condition-schedule"
SOURCE_PATHS = {
    "en": "data/lab/pmlab-pack-reader-v0/sources/english/evidence.md",
    "pl": "data/lab/pmlab-pack-reader-v0/sources/polish/evidence.md",
}
FORMATS = ["F0_FULL", "F1_COMPACT"]
ORDERS = ["O0_RETRIEVAL", "O1_GOVERNED"]


ENTITIES = [
    ("Amber", "Amber"), ("Birch", "Birch"), ("Cedar", "Cedar"), ("Delta", "Delta"),
    ("Ember", "Ember"), ("Flint", "Flint"), ("Garnet", "Garnet"), ("Harbor", "Harbor"),
    ("Indigo", "Indigo"), ("Juniper", "Juniper"), ("Kestrel", "Kestrel"), ("Lumen", "Lumen"),
    ("Mosaic", "Mosaic"), ("Nimbus", "Nimbus"), ("Onyx", "Onyx"), ("Prairie", "Prairie"),
]

FIELDS = [
    (("owner code", "kod właściciela"), ("release code", "kod wydania"), ("approval code", "kod zatwierdzenia")),
    (("deployment region", "region wdrożenia"), ("cluster code", "kod klastra"), ("revision code", "kod rewizji")),
    (("status code", "kod statusu"), ("start-date code", "kod daty rozpoczęcia"), ("review code", "kod przeglądu")),
    (("backup location", "lokalizacja kopii"), ("key code", "kod klucza"), ("rotation code", "kod rotacji")),
    (("severity code", "kod ważności"), ("incident owner", "właściciel incydentu"), ("recovery code", "kod odzyskiwania")),
    (("retention date", "data retencji"), ("legal-basis code", "kod podstawy prawnej"), ("reviewer code", "kod recenzenta")),
    (("encryption suite", "zestaw szyfrowania"), ("rotation interval", "interwał rotacji"), ("keyring code", "kod keyringu")),
    (("endpoint state", "stan endpointu"), ("route code", "kod trasy"), ("authorization code", "kod autoryzacji")),
    (("reviewer identity", "tożsamość recenzenta"), ("approval token", "token zatwierdzenia"), ("audit code", "kod audytu")),
    (("timezone code", "kod strefy czasowej"), ("schedule code", "kod harmonogramu"), ("deadline code", "kod terminu")),
    (("canonical store", "magazyn kanoniczny"), ("index policy", "polityka indeksu"), ("manifest code", "kod manifestu")),
    (("export policy", "polityka eksportu"), ("deletion code", "kod usuwania"), ("receipt code", "kod potwierdzenia")),
    (("router tier", "poziom routera"), ("fallback code", "kod fallbacku"), ("deferral code", "kod odroczenia")),
    (("privacy class", "klasa prywatności"), ("access code", "kod dostępu"), ("retention code", "kod retencji")),
    (("audit revision", "rewizja audytu"), ("signer code", "kod podpisującego"), ("evidence code", "kod dowodu")),
    (("recovery step", "krok odzyskiwania"), ("probe code", "kod sondy"), ("rollback code", "kod rollbacku")),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def condition_id(case_id: str, format_arm: str, order_arm: str) -> str:
    digest = hashlib.sha256(f"{SALT}|{case_id}|{format_arm}|{order_arm}".encode()).hexdigest()[:16]
    return f"C{digest}"


def atoms(group_index: int, count: int, old: bool = False) -> list[str]:
    prefix = "OLD" if old else "ACTIVE"
    return [f"G{group_index:02d}-{prefix}-{letter}" for letter in "ABC"[:count]]


def evidence_rows(group_index: int, language: str, entity: str, answer_count: int) -> list[dict[str, Any]]:
    field_set = FIELDS[group_index - 1]
    active = atoms(group_index, answer_count)
    stale = atoms(group_index, answer_count, old=True)
    if language == "en":
        texts = [
            f"Current record: {entity}'s {field_set[0][0]} is {active[0]}.",
            f"Supporting record: {entity}'s {field_set[1][0]} is {active[1] if answer_count >= 2 else f'G{group_index:02d}-SUPPORT-X'}.",
            f"Current record: {entity}'s {field_set[2][0]} is {active[2] if answer_count == 3 else f'G{group_index:02d}-MONITOR-X'}.",
            f"Supporting reviewed distractor: {entity}'s documentation marker is G{group_index:02d}-DOC-X.",
            f"Stale conflicting record: {entity}'s former {field_set[0][0]} was {stale[0]}"
            + (f" and former {field_set[1][0]} was {stale[1]}" if answer_count >= 2 else "")
            + (f" with former {field_set[2][0]} {stale[2]}" if answer_count == 3 else "") + ".",
            f"Stale unrelated record: {entity}'s retired transport marker was G{group_index:02d}-OLD-TRANSPORT.",
            f"Reviewed distractor: a different project uses G{group_index:02d}-OTHER-CURRENT.",
            f"Reviewed distractor: an archived test fixture references G{group_index:02d}-FIXTURE-X.",
        ]
    else:
        texts = [
            f"Aktualny rekord: {field_set[0][1]} projektu {entity} to {active[0]}.",
            f"Rekord wspierający: {field_set[1][1]} projektu {entity} to {active[1] if answer_count >= 2 else f'G{group_index:02d}-SUPPORT-X'}.",
            f"Aktualny rekord: {field_set[2][1]} projektu {entity} to {active[2] if answer_count == 3 else f'G{group_index:02d}-MONITOR-X'}.",
            f"Wspierający dystraktor: znacznik dokumentacji projektu {entity} to G{group_index:02d}-DOC-X.",
            f"Nieaktualny konflikt: poprzedni {field_set[0][1]} projektu {entity} to {stale[0]}"
            + (f", a poprzedni {field_set[1][1]} to {stale[1]}" if answer_count >= 2 else "")
            + (f", zaś poprzedni {field_set[2][1]} to {stale[2]}" if answer_count == 3 else "") + ".",
            f"Nieaktualny rekord niezwiązany: wycofany znacznik transportu projektu {entity} to G{group_index:02d}-OLD-TRANSPORT.",
            f"Zweryfikowany dystraktor: inny projekt używa G{group_index:02d}-OTHER-CURRENT.",
            f"Zweryfikowany dystraktor: archiwalny test odwołuje się do G{group_index:02d}-FIXTURE-X.",
        ]
    buckets = ["current", "supporting", "current", "supporting", "stale_conflicting", "stale_conflicting", "distractor", "distractor"]
    return [
        {
            "record_id": f"G{group_index:02d}-{language.upper()}-R{index + 1:02d}",
            "local_id": f"R{index + 1:02d}",
            "group_id": f"PRG-{group_index:02d}",
            "language": language,
            "text": text,
            "bucket": buckets[index],
            "trust": "reviewed",
            "source_path": SOURCE_PATHS[language],
        }
        for index, text in enumerate(texts)
    ]


def question(group_index: int, language: str, entity: str, answer_count: int) -> str:
    fields = FIELDS[group_index - 1]
    if language == "en":
        requested = ", ".join(field[0] for field in fields[:answer_count])
        return f"Return the current values for {entity}: {requested}. Use only exact value atoms from evidence."
    requested = ", ".join(field[1] for field in fields[:answer_count])
    return f"Zwróć aktualne wartości dla projektu {entity}: {requested}. Użyj wyłącznie dokładnych atomów z dowodów."


def main() -> None:
    corpus: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    answer_counts = [1, 2, 3, 2] * 4
    retrieval_patterns = [
        ["R05", "R03", "R01", "R07", "R02", "R06", "R04", "R08"],
        ["R07", "R02", "R05", "R04", "R01", "R03", "R06", "R08"],
        ["R06", "R04", "R08", "R05", "R01", "R03", "R02", "R07"],
        ["R03", "R05", "R07", "R01", "R06", "R08", "R02", "R04"],
    ]
    for group_index, entity_pair in enumerate(ENTITIES, start=1):
        count = answer_counts[group_index - 1]
        active = atoms(group_index, count)
        stale = atoms(group_index, count, old=True)
        groups.append(
            {
                "group_id": f"PRG-{group_index:02d}",
                "answer_atoms": active,
                "stale_atoms": stale,
                "answer_count": count,
                "strata": ["single" if count == 1 else "multi", "current-stale-conflict", "bilingual-pair"],
            }
        )
        for language, entity in zip(("en", "pl"), entity_pair):
            rows = evidence_rows(group_index, language, entity, count)
            corpus.extend(rows)
            cases.append(
                {
                    "case_id": f"PRG-{group_index:02d}-{language.upper()}",
                    "group_id": f"PRG-{group_index:02d}",
                    "language": language,
                    "question": question(group_index, language, entity, count),
                    "retrieval_order": retrieval_patterns[(group_index - 1) % len(retrieval_patterns)],
                    "all_local_ids": [f"R{i:02d}" for i in range(1, 9)],
                }
            )

    for language, source_path in SOURCE_PATHS.items():
        selected = [row for row in corpus if row["language"] == language]
        path = ROOT / source_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(row["text"] for row in selected) + "\n", encoding="utf-8", newline="\n")
        for line_number, row in enumerate(selected, start=1):
            row["line_start"] = line_number
            row["line_end"] = line_number

    conditions: list[dict[str, Any]] = []
    for case in cases:
        for format_arm in FORMATS:
            for order_arm in ORDERS:
                conditions.append(
                    {
                        "condition_id": condition_id(case["case_id"], format_arm, order_arm),
                        "case_id": case["case_id"],
                        "format_arm": format_arm,
                        "order_arm": order_arm,
                    }
                )
    conditions.sort(key=lambda row: row["condition_id"])
    blind_schedule = [
        {"sequence": index + 1, "condition_id": row["condition_id"], "case_id": row["case_id"]}
        for index, row in enumerate(conditions)
    ]
    groups_by_id = {group["group_id"]: group for group in groups}
    gold = []
    for case in cases:
        group = groups_by_id[case["group_id"]]
        count = group["answer_count"]
        gold.append(
            {
                "case_id": case["case_id"],
                "group_id": case["group_id"],
                "language": case["language"],
                "answer_atoms": group["answer_atoms"],
                "stale_atoms": group["stale_atoms"],
                "required_local_ids": ["R01"] + (["R02"] if count >= 2 else []) + (["R03"] if count == 3 else []),
            }
        )

    write_jsonl(BASE / "corpus.jsonl", corpus)
    write_jsonl(BASE / "internal" / "groups.jsonl", groups)
    write_jsonl(BASE / "cases.jsonl", cases)
    write_jsonl(BASE / "internal" / "condition-map.jsonl", conditions)
    write_jsonl(BASE / "internal" / "gold.jsonl", gold)
    write_jsonl(BASE / "blind" / "schedule.jsonl", blind_schedule)
    tracked = [
        BASE / "corpus.jsonl", BASE / "internal" / "groups.jsonl", BASE / "cases.jsonl",
        BASE / "internal" / "condition-map.jsonl", BASE / "internal" / "gold.jsonl",
        BASE / "blind" / "schedule.jsonl", *(ROOT / path for path in SOURCE_PATHS.values()),
    ]
    manifest = {
        "experiment_id": "PMLAB-PACK-READER-001",
        "status": "fixture-and-opaque-schedule-built-awaiting-freeze",
        "groups": len(groups),
        "cases": len(cases),
        "records": len(corpus),
        "conditions": len(conditions),
        "bilingual_grouping": True,
        "authored_synthetic": True,
        "independently_reviewed": False,
        "runner": "not-built",
        "prompt_packet": "not-built",
        "api_authorized": False,
        "hashes": {str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path) for path in tracked},
        "authority": "visible construction fixture; reader compatibility only",
    }
    (BASE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"groups": len(groups), "cases": len(cases), "records": len(corpus), "conditions": len(conditions)}))


if __name__ == "__main__":
    main()
