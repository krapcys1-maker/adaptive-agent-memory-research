# Sealed held-out split protocol v1

Implements independence tier **I1** from [the independence ladder](../00-project/independence-ladder.md).
Tool: `scripts/sealed_split.py`. Tests: `tests/test_sealed_split.py`.

## What it is for

The project recorded this failure against `PMLAB-MAP`: the challenge set was "post-freeze but same-process, not independently held out", and once the author had seen it, it was spent for tuning. Recruiting a second person to hold data out has not worked — review packets have waited without a reviewer.

This protocol produces a genuinely held-out evaluation with a single author, by making the split cryptographically committed before the candidate exists and verifiable by anyone afterwards.

## Procedure

### 1. Seal

```bash
python scripts/sealed_split.py seal \
  --pool data/lab/<experiment>/pool.jsonl \
  --out  data/lab/<experiment>/sealed \
  --experiment PMLAB-EXAMPLE-001 \
  --generator scripts/build_<experiment>_pool.py
```

A random 32-byte key is generated unless `--key-file` supplies one. **Move the key outside the repository immediately.** Publishing it before a candidate is registered destroys the held-out property.

Published: `development.jsonl` and `sealed-manifest.json`.
The manifest commits to `sha256(key)`, the pool identifier digest, the pool content digest, the development digest, the split rule, counts, and the generator's own hash. It contains no key and no challenge case.

Commit and push both files before doing anything else. **The ordering guarantee comes from publication, not from the `sealed_at` timestamp.**

### 2. Build against development only

The challenge half does not exist on disk yet. It cannot be inspected, counted case by case, or tuned against.

### 3. Register the candidate

```bash
python scripts/sealed_split.py register \
  --sealed data/lab/<experiment>/sealed \
  --candidate scripts/<candidate>.py \
  --thresholds '{"recall@5": 0.75, "forbidden_intrusion@5": 0.05}'
```

This digests every candidate artifact and binds the registration to the sealed manifest. Preregistered thresholds belong here, before any challenge result is visible. Commit and push.

### 4. Reveal

```bash
python scripts/sealed_split.py reveal \
  --sealed data/lab/<experiment>/sealed \
  --pool   data/lab/<experiment>/pool.jsonl \
  --key-file /path/outside/repo/secret.key
```

Refused unless the key matches the commitment, a registration exists and binds this manifest, every registered artifact still hashes to its registered value, and the pool is byte-identical to what was sealed. Only then is `challenge.jsonl` written, alongside a reveal receipt.

### 5. Third-party verification

```bash
python scripts/sealed_split.py verify --sealed ... --pool ... --key-file ...
```

Eleven checks: the key matches the commitment, pool identifiers and content match, the development half recomputes from the key alone, counts agree, the published development half is unmodified, the manifest leaks neither the key nor any challenge case, a candidate is registered, the registration binds this manifest, and every registered artifact is unchanged.

## What it guarantees, and what it does not

**Guaranteed by cryptography.** The split cannot be chosen after seeing results — the key commitment fixes it in advance. The pool cannot be edited after sealing. The candidate cannot be edited after registration. Any third party can recompute everything from the revealed key.

**Not guaranteed.** Ordering rests on publication, not on a trusted clock. An author holding the key could in principle seal, peek at the challenge half privately, then register a candidate tuned to it. Nothing local can prevent that. What makes the ordering real is that the sealed manifest and the registration are committed and pushed to a public repository before the key is released, so the sequence is externally witnessed.

This is stated rather than glossed over. I1 is a strong tier, not an absolute one, and it does not replace I5.

## Design decisions worth knowing

**One tool, four subcommands, not separate scripts.** Seal and reveal must compute an identical split; duplicating that logic would put a divergence bug in the one place where it would silently invalidate a result.

**All artifacts are written as explicit bytes with LF endings.** `Path.write_text` opens in text mode and translates `\n` to `\r\n` on Windows, so a digest computed in memory would disagree with the bytes on disk and the same artifact would hash differently depending on who produced it. That exact failure is already recorded in this repository as a broken cross-platform freeze.

**An experiment may not share an identifier with any of its cases.** Otherwise a challenge identifier appearing in the manifest could be ordinary metadata or a real leak, and no scan can separate the two. The seal step refuses the ambiguity instead of special-casing it. This was found by running the protocol end to end, not by reasoning about it.

**The leak check compares exact JSON leaf values, not substrings.** Substring search over the serialized manifest fires whenever an experiment identifier shares a prefix with case identifiers, which is a false alarm rather than a leak.

## Tamper cases covered by tests

Wrong key · reveal without registration · pool extended after sealing · pool content edited without changing identifiers · candidate changed after registration · registration bound to a different manifest · registered artifact deleted · published development half edited · duplicate case identifiers · case without an identifier · empty pool · experiment identifier colliding with a case identifier.
