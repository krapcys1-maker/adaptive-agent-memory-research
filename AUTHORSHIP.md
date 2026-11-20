# Credit and authorship

This project runs on volunteer work: people lend GPUs, write code, read papers, review designs and try to break our
results. This page says exactly how that work is credited, so nobody has to guess or ask.

## 1. Co-authorship of the next report

The experience-memory ladder will be written up as a technical report: an arXiv preprint and a release with a DOI.
You are invited as a **co-author** of the next report if, before its announced cut-off date, you contributed at least
one of the following. The three paths are independent: any one of them is enough, and none depends on another.

1. **A validated experiment cell** that is included in the reported results.
   - Validated means that the cell passed the lab's code checks and the CPU replay of all its action sequences, and
     that its spot-check, a re-run of a small random sample of its games on our hardware, flagged no gross deviation.
   - Whether a cell is also drawn for the fuller replication of at least 10% of cells never decides credit.
   - See [the rule](docs/research-map/VOLUNTEER_COMPUTE.md#how-results-are-checked).
2. **A merged, substantive pull request** that the report relies on: code, analysis, data or documentation.
   - A merged data pull request, such as a submitted cell, counts through this path if the report relies on its data,
     whatever the validation status of the cell.
3. **A written review or an independent replication** of a result in the report, including one that finds a problem.

Credit follows the criteria published here. They are never changed for a report after its results have been seen, except to correct an error. The report then
states the correction.

The cut-off date of each report is announced in [#84](../../issues/84) at least two weeks in advance. Contributions
after the cut-off count toward the next report. This rule follows the one BIG-bench used for its 450 authors.

## 2. Your role is recorded

Each author's contribution is recorded with the [CRediT](https://credit.niso.org/) roles, together with its degree
(lead, equal or supporting):

- Investigation, for running cells;
- Software;
- Formal analysis;
- Data curation;
- Validation, for replications and reviews;
- Writing – review & editing.

Running compute alone qualifies through *Investigation*. Every author is invited to review the manuscript before it is
posted.

## 3. Order of authors

1. The maintainer.
2. Major contributors: people who designed an experiment, wrote a substantial part of the analysis, or drafted a
   section.
3. Everyone else, in alphabetical order.

A contributions section lists each person's roles.

## 4. Consent

- Every author approves the final text before it is posted.
- You can decline authorship and be acknowledged instead.
- You choose the name you are credited under, including a pseudonym.
- Credit is never removed afterwards.

## 5. Below the authorship bar

Smaller contributions are thanked by name in [CONTRIBUTORS.md](CONTRIBUTORS.md) and in the report's acknowledgements:

- a typo fix;
- a comment that changed a design;
- a cell that could not be validated and whose data the report does not use.

Each result's README also names the people whose cells it uses.

## 6. Citable releases

Every results release gets a DOI, and [CITATION.cff](CITATION.cff) lists its authors.

## What this page does not promise

- A pull request is merged when it passes review and CI, not because it was submitted.
- Authorship follows the rules above, not the amount of compute or the number of comments.
- Questions about a specific case go in an issue. The maintainer answers them there, in public.
