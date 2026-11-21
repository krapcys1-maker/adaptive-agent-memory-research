"""Checks the provenance of laboratory objects: recomputes the sha256 of every object in knowledge.jsonl and checks
that every parent appears before its child. Usage: python verify_provenance.py knowledge.jsonl (standard library only).
The output is ASCII only, so it reads the same under any console encoding."""
import hashlib, json, sys

def canonical(o):
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

objs = [json.loads(x) for x in open(sys.argv[1], encoding="utf-8") if x.strip()]
ids, bad, red = set(), [], 0
for o in objs:
    sha = hashlib.sha256(canonical({"kind": o["kind"], "program": o["program"], "payload": o["payload"],
                                    "parents": sorted(set(o["parents"]))}).encode("utf-8")).hexdigest()
    if o.get("redacted"):
        # machine-local paths were replaced in this copy: sha256_redacted covers the copy, while id and sha256 are
        # the hashes of the original object in the lab's private registry
        red += 1
        if sha != o.get("sha256_redacted"):
            bad.append(o["id"] + ": hash mismatch (redacted copy)")
    elif sha != o["sha256"] or not o["id"].endswith(sha[:16]):
        bad.append(o["id"] + ": hash mismatch")
    bad += [o["id"] + ": missing parent " + p for p in o["parents"] if p not in ids]
    ids.add(o["id"])
print("OK" if not bad else "\n".join(bad), f"({len(objs)} objects, {red} with machine-local paths redacted)")
sys.exit(1 if bad else 0)
