# DeepSeek advisory review of PMLAB-REUSE-CHAR-001

Status: finalized M1 author-operated model review; not independent validation

Verdict: `needs_revision` (confidence 0.85).

Author disposition: see `audit-disposition.md`. The verdict is retained; accepted reporting repairs do not retroactively turn this advisory into independent validation.

## Required claim boundary

All claims must be limited to the synthetic development characterization. No claim may imply architecture selection, natural benchmark performance, or generalizable safety. Specific failure attributions must be backed by per-query data. Recommendations must be framed as observations, not decisions.

## Fatal issues

- The report claims 'FastEmbed missed one of three required records in the multi-project donor question' but the aggregate shows C0_FASTEMBED all_required_at_5 = 0.947, implying exactly one query missed at least one required record; however, the report does not identify which query or provide per-query evidence, making the failure localization unverifiable.
- The report states 'FastEmbed retrieved a forbidden record in four of twenty queries' but the aggregate only reports forbidden_intrusion_rate_at_5 = 0.2, which is consistent with 4/20, but the report does not provide the specific query IDs or the forbidden records, so the claim cannot be independently checked.
- The report claims 'RRF inherited three forbidden intrusions' but the aggregate only gives a rate of 0.15 (3/20) without identifying which queries or whether they overlap with the dense arm's four intrusions; the claim of inheritance is not supported by the provided data.
- The report's 'Failure localization' section attributes specific failures (e.g., 'prospective-scheduling paraphrase', 'multi-project donor question') to specific arms, but the aggregate summary does not include per-query results, so these attributions are not reproducible from the provided artifacts.
- The report claims 'All three arms returned candidates for the unanswerable password query' but the aggregate only reports unanswerable_candidate_null = 0 for all arms, which is consistent but does not prove that candidates were returned; the report does not provide the actual candidate lists or the query text.
- The report's 'Characterization decision' recommends 'Admit exact citations as a required contract' and 'Admit bucketed packing as a testable formatter' based on deterministic gates, but the protocol explicitly states that perfect citation or bucket metrics validate deterministic plumbing, not evidence truth or bucket inference; the report's wording could be misinterpreted as validating the underlying evidence classification.
- The report's 'Next tests' include comparing citation formats and context order, but these tests are not pre-registered in the frozen protocol; the protocol only defines the current characterization, so proposing new tests without a protocol amendment is a process violation.
- The report's 'Primary source follow-up' introduces new hypotheses (H-CHAR-01 to H-CHAR-04) that are not part of the frozen protocol; these are post-hoc analyses and should be clearly marked as exploratory, not as part of the characterization's conclusions.
- The report's 'Runtime and reproducibility' section reports 'Warm model load: 0.635 s; warm corpus embedding: 1.100 s' but the aggregate summary only provides 'model_load_ms' and 'embedding_ms' for the first run; the warm timings are not in the aggregate, so they are not reproducible from the provided data.
- The report's 'Citations and context packs' table shows 'Bucketed required retained' for FTS5 as 0.684, but the aggregate summary reports 'mean_required_retained' for bucketed packs as 0.8304 across all arms; the report's per-arm values are not derivable from the aggregate, and the discrepancy is not explained.

## Major issues

- The report's 'Failure localization' section makes specific claims about which queries failed (e.g., 'multi-project donor question', 'prospective-scheduling paraphrase') but the aggregate summary does not include per-query results, so these claims are not verifiable from the provided artifacts.
- The report's 'Characterization decision' recommends retaining FTS5 as a minimal sparse baseline and FastEmbed as a restricted diagnostic, but the protocol states that no minimum retrieval score is an architecture gate; the report's recommendations could be interpreted as endorsing these components for future use, which is beyond the characterization's authority.
- The report's 'Next tests' propose comparing citation formats and context order, but these tests are not pre-registered in the frozen protocol; the protocol only defines the current characterization, so proposing new tests without a protocol amendment is a process violation.
- The report's 'Primary source follow-up' introduces new hypotheses (H-CHAR-01 to H-CHAR-04) that are not part of the frozen protocol; these are post-hoc analyses and should be clearly marked as exploratory, not as part of the characterization's conclusions.
- The report's 'Runtime and reproducibility' section reports 'Warm model load: 0.635 s; warm corpus embedding: 1.100 s' but the aggregate summary only provides 'model_load_ms' and 'embedding_ms' for the first run; the warm timings are not in the aggregate, so they are not reproducible from the provided data.
- The report's 'Citations and context packs' table shows 'Bucketed required retained' for FTS5 as 0.684, but the aggregate summary reports 'mean_required_retained' for bucketed packs as 0.8304 across all arms; the report's per-arm values are not derivable from the aggregate, and the discrepancy is not explained.

## Claims supported

- All characterization gates pass: exact citations, valid locators, zero leakage, zero untrusted exposure, byte budget, RRF formula, and deterministic rankings.
- Dense retrieval (FastEmbed MiniLM) achieved higher recall and cross-language recall than FTS5 on this synthetic fixture.
- Dense retrieval had a higher forbidden intrusion rate than FTS5 on this synthetic fixture.
- RRF improved over FTS5 but did not beat the dense component on recall, all-required, cross-language, terminology shift, or forbidden intrusion.
- All arms returned candidates for the unanswerable query (candidate-null = 0).
- The 768-byte budget caused omissions in some packs, and citations/headers consume context.

## Claims not supported

- The specific failure localization (e.g., 'multi-project donor question', 'prospective-scheduling paraphrase') is not supported by the aggregate data.
- The claim that 'RRF inherited three forbidden intrusions' is not supported without per-query overlap data.
- The claim that 'The bucketed pack preserved every dense-required item in this fixture' is not supported by the aggregate mean_required_retained for bucketed packs.
- The report's 'Characterization decision' recommendations (e.g., 'Admit exact citations as a required contract') are not supported as they go beyond the protocol's scope.
- The report's 'Next tests' are not supported by the current characterization results; they are proposals for future work.

## Next required tests

- Provide per-query results for all arms, including query IDs, retrieved IDs, and required evidence, to verify failure localization claims.
- Compute per-query overlap and discordance between sparse and dense arms to test the 'RRF inherited' claim.
- Re-run the packaging analysis with per-arm required retention and omission counts to reconcile the aggregate mean.
- Measure warm latency in a controlled way and report both cold and warm timings with clear definitions.
- Pre-register any new tests (citation format, context order) in a protocol amendment before execution.
- For the natural benchmark, ensure independent eligibility and evidence labels are complete before comparing E5-small.
