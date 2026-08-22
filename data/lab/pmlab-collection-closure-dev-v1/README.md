# PMLAB collection-closure construction corpus v1

Status: authored construction freeze candidate; not held out; no architecture claim permitted

V1 preserves v0 and repairs one pre-run design flaw. In v0, the two insertion-counterexample certificates already declared `partial`, so a certificate arm could reject them without checking insertion independence. In v1 those two synthetic certificates declare `complete`, while their allowed update artifact contains an admissible insertion that changes the answer. This makes a certificate-only arm and a certificate-plus-insertion-test arm observably different.

No runner existed and no policy result was observed when this repair was authored. The manifest records the v0 parent hash and the exact changes. V0 remains immutable in Git as a preserved failed instrument version.

All other limitations and artifact meanings from v0 remain. Gold fields must never enter model-visible payloads, and bilingual rows must be split by `pair_group`.
