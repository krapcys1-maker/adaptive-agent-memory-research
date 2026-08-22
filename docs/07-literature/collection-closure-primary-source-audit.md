# Collection-closure primary-source audit

Status: targeted full-text extraction complete; whole-paper formal verification and independent review incomplete

This audit records exactly which locally cached pages were used for the first collection-closure synthesis. Page numbers below are PDF pages; printed proceedings pages are added where visible. Local PDFs are ignored research cache artifacts and are identified by SHA-256 so another contributor can verify the same files.

| Source | Inspected locator | Extracted result | Boundary | Local SHA-256 |
| --- | --- | --- | --- | --- |
| Reiter, *On Closed World Data Bases* | PDF pp. 1-3; Section 3, PDF pp. 7-10; Theorem 5.1 and Corollary 5.4, PDF pp. 16-17 | OWA accepts proof-supported answers; CWA adds negative ground literals after failure to prove positives; unrestricted CWA may be inconsistent while the paper gives a Horn-database consistency result | old deductive-database setting; the restricted consistency result is not permission for global personal-memory closure | `bb4d5839133a547d878ad83c1247937367136258cf3866d7c65452d44fe7f585` |
| Imieliński and Lipski, *Incomplete Information in Relational Databases* | introduction, printed pp. 761-766; Section 3, printed pp. 766-770; main representation results in Sections 4, 6-9 | an incomplete table represents a set of relations; representation systems must preserve supported query operations safely and completely; expressiveness changes with table and operator class | not one unrestricted possible-world evaluator; operations and representations have specific impossibility/tractability boundaries | `e7e70a2354f15f7baa05922ba58e44fa256949dc4ce0d2c0a607f01b3a40b61d` |
| Motro, *Integrity = Validity + Completeness* | abstract/introduction, PDF p. 1 (printed p. 480); definitions, PDF pp. 5-6 (printed pp. 484-485); answer certificates, Section 6; freshness/contributor caveat, PDF p. 22 (printed p. 501) | validity excludes false tuples while completeness includes true tuples; view-specific integrity can accompany answers; certifications depend on currently satisfied constraints and may need contributor/time annotations | method is restricted and explicitly not logically complete; certificate metadata may itself be stale or untrusted | `1c38f40aa0833784b02339bd4b08ac5a399076b95e2d57e360ce4b46636490e2` |
| Levy, *Obtaining Complete Answers from Incomplete Databases* | abstract, PDF p. 1 (printed p. 402); Definitions 2.1-2.5, PDF pp. 4-5 (printed pp. 405-406); Theorem 3.1; current-instance method, Section 5 | local completeness constrains relation fragments; answer completeness is connected to query independence from insertion updates; auxiliary queries can establish completeness in a current state | conjunctive-query/constraint assumptions and complexity results do not transfer automatically to arbitrary natural-language memory queries | `0017a610b5e1fa1edd8ebb0347500eaa77c03b9176519da32bd3aa2089b3d51a` |
| Razniewski and Nutt, *Completeness of Queries over Incomplete Databases* | abstract/introduction, PDF p. 1 (printed p. 749); formal TC/QC definitions, PDF pp. 2-3 (printed pp. 750-751); weakest-precondition results, Sections 4-5; practical acquisition discussion, PDF p. 8 (printed p. 756) | table-completeness and query-completeness statements differ; entailment can identify exact database fragments critical to supported query classes; completeness evidence may come from collection processes | null-free relational assumptions and stated language/complexity limits; accurate completeness assertions remain an operational dependency | `bf766c22c90915ac6dd151d711eb728306b7d7767adf48bd231aa3841d9bee42` |
| Libkin, *Incomplete Information and Certain Answers in General Data Models* | abstract/introduction, PDF pp. 1-2; general semantic ordering and OWA/CWA discussion, PDF pp. 5-8 | certain-answer behavior depends on a model of incomplete objects, their completions, and an information ordering | abstract theory; it does not supply the inventory probes or authorization model needed here | `bda9a03a839a540c60ef07c49453c4b45caefd33483a12b6e83ce9146309cdac` |
| Libkin, *Certain Answers as Objects and Knowledge* | abstract/introduction, PDF pp. 1-4; problematic standard answers, Section 3, PDF p. 7; objects/knowledge/information ordering, Section 4, PDF pp. 8-10; computation, Section 7 | standard intersection-based certain answers can be counterintuitive under some semantics; certain objects and certain knowledge must be distinguished; semantics and information ordering matter | supports caution, not abandonment of all certain-answer methods; concrete query languages still need separate validation | `ed3a343607504a2a83c709760d994052e963e56c474e500cab1d81fe9fa6db01` |
| Darari, Razniewski, and Nutt, *Bridging the Semantic Gap between RDF and SPARQL using Completeness Statements* | abstract/introduction, PDF pp. 1-2; Definitions 1-3, PDF pp. 2-4; discussion, PDF p. 5 | explicit graph-pattern completeness statements restrict admissible RDF interpretations and can make selected negative query results certain; timestamps are suggested for changing information | assumes graph correctness, targets restricted SPARQL patterns, and leaves maintenance/freshness as future work | `1980b4251a6def421c967b85efa22787d803d685b730dcae9d55c587d79d100a` |

## Cross-source inference audit

The four project tiers N0-N3 are not copied from one paper. They are a conservative engineering synthesis:

- Reiter supplies the danger boundary between proof-supported answers and negation by failure;
- incomplete-information work supplies admissible completions and certainty boundaries;
- Motro separates valid from complete answers and exposes freshness/authority requirements;
- Levy and Razniewski/Nutt make completeness query-relative and update-sensitive;
- Darari et al. show that explicit scoped completeness metadata can license selected negative graph queries.

Therefore `NO_AUTHORIZED_CURRENT_RECORD_IN_COMPLETE_SCOPE` is intentionally weaker than `PROPOSITION_FALSE`. The former is a database/inventory statement. The latter additionally requires explicit negative evidence or a domain-specific closed-world rule.

## Unresolved verification tasks

- reproduce formal definitions and theorem preconditions in executable toy relational examples;
- inspect the complete proof of Levy's Theorem 3.1 and the exact direction of every reduction before implementing insertion tests;
- read later local-closed-world and negative-knowledge work cited by Razniewski/Nutt and Libkin;
- locate an accessible copy of the 2020 Semantic Web journal version and compare it with the cached 2018 extended preprint;
- obtain a reviewer who did not author the corpus or synthesis.
