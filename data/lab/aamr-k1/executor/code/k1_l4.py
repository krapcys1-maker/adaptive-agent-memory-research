"""K1 v0.4 (W3): leak check L4a for the neutral P corpus, as frozen code. L4b (Jaccard) is unchanged from v0.3.

L4a stops a sentence that contains any of:
  1. a digit;
  2. a number word (NUMBER_WORDS), also inside hyphenated compounds (twenty-five);
  3. a second-person word (you, your, yours, yourself, yourselves);
  4. a code / trace character: ( ) [ ] { } " ` _ = / \\ < > | , a straight apostrophe that is not between two letters,
     or any non-ASCII character (typographic quotes, accented letters);
  5. a domain word, compared on stems (stem()): the stem of a sentence word equals the stem of a word on the domain list.
     Domain list = components of function and parameter identifiers and enum literals in the tool documentation of the
     involved classes + components of argument literals and of result keys in the FULL success pools of the three domains
     + the frozen list of domain variants (DOMAIN_VARIANTS: synonyms and spellings not derivable from identifiers),
     minus the frozen function-word list (FUNCTION_WORDS).
Known residual: synonyms outside DOMAIN_VARIANTS are not detected; the report prints L4b for every P block.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

FUNCTION_WORDS = frozenset("""a an and are as at be been but by can could did do does for from had has have he her his i if in into is it its
may might more most no not of on or our she should so some such than that the their them then there these they this those to
was we were what when where which who will with would also any each how many much only other over own same too very
all both few just now out up about after again before between during through under until while here why off per via
get set new old along across around among against behind below beneath beside beyond near toward towards within without upon
onto since though although because whether either neither every still yet even ever never always often""".split())
NUMBER_WORDS = frozenset("""zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen
seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred hundreds thousand thousands million
millions billion billions dozen dozens half halves twice thrice""".split())
SECOND_PERSON = frozenset({"you", "your", "yours", "yourself", "yourselves"})
DOMAIN_VARIANTS = frozenset("""petrol gasoline diesel gallon litre liter tyre tire automobile car motorist mileage odometer kilometre
kilometer mile brake ignition headlight dashboard airplane aeroplane aircraft plane airline airport airfare passport luggage
baggage visa directory folder document byte kilobyte megabyte celsius fahrenheit""".split())
CODE_CHARS = re.compile(r"""[()\[\]{}"`_=/\\<>|]""")
LONE_APOSTROPHE = re.compile(r"(?<![A-Za-z])'|'(?![A-Za-z])")
NON_ASCII = re.compile(r"[^\x00-\x7f]")
WORD = re.compile(r"[A-Za-z]+")


def stem(w: str) -> str:
    """Light suffix stripping, applied identically to sentence words and list words: -ies->y, -ing, -ed, -es, -s
    (longest first, only if at least 3 letters remain), then a doubled final consonant is undoubled, then a final -e dropped."""
    w = w.lower()
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    else:
        for suf in ("ing", "ed", "es", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
    if len(w) >= 4 and w[-1] == w[-2] and w[-1] not in "aeiou":
        w = w[:-1]
    if len(w) >= 4 and w.endswith("e"):
        w = w[:-1]
    return w


def split_identifier(name: str):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)
    return [p.lower() for p in re.split(r"[^A-Za-z]+", s) if p]


def _walk_docs(o, idents, lits):
    if isinstance(o, dict):
        for k, x in o.items():
            if k == "name" and isinstance(x, str):
                idents.add(x)
            if k == "properties" and isinstance(x, dict):
                idents.update(x)
            if k == "enum" and isinstance(x, list):
                lits.update(map(str, x))
            _walk_docs(x, idents, lits)
    elif isinstance(o, list):
        for x in o:
            _walk_docs(x, idents, lits)


def _call_parts(call: str, idents, lits):
    try:
        node = ast.parse(call.strip(), mode="eval").body
    except SyntaxError:
        return
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            idents.add(node.func.id)
        for kw in node.keywords:
            if kw.arg:
                idents.add(kw.arg)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                lits.add(sub.value)


def _result_keys(result, idents):
    try:
        o = json.loads(result) if isinstance(result, str) else result
    except (ValueError, TypeError):
        return
    stack = [o]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            idents.update(k for k in x if isinstance(k, str))
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)


def build_domain_list(doc_files, pools):
    """doc_files: paths of multi_turn_func_doc/*.json; pools: iterable of pool rows (full success pools)."""
    idents, lits = set(), set()
    for f in doc_files:
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if line.strip():
                _walk_docs(json.loads(line), idents, lits)
    for row in pools:
        for st in row.get("steps") or []:
            if st.get("call"):
                _call_parts(st["call"], idents, lits)
            if st.get("result") is not None:
                _result_keys(st["result"], idents)
    words = set()
    for n in idents:
        words.update(split_identifier(n))
    for l in lits:
        words.update(w.lower() for w in WORD.findall(l))
    words |= DOMAIN_VARIANTS
    words = {w for w in words if len(w) >= 3 and w not in FUNCTION_WORDS and w not in NUMBER_WORDS}
    return frozenset(words), frozenset(stem(w) for w in words)


def l4a(sentence: str, domain_stems) -> list:
    """Reasons to stop the sentence (empty list = passes)."""
    why = []
    if re.search(r"\d", sentence):
        why.append("digit")
    if NON_ASCII.search(sentence):
        why.append("non-ascii")
    if CODE_CHARS.search(sentence):
        why.append("code-char")
    if LONE_APOSTROPHE.search(sentence):
        why.append("apostrophe")
    ws = [w.lower() for w in WORD.findall(sentence)]
    if set(ws) & NUMBER_WORDS:
        why.append("number-word:" + ",".join(sorted(set(ws) & NUMBER_WORDS)))
    if set(ws) & SECOND_PERSON:
        why.append("second-person")
    hit = sorted({w for w in ws if w not in FUNCTION_WORDS and stem(w) in domain_stems})
    if hit:
        why.append("domain:" + ",".join(hit))
    return why
