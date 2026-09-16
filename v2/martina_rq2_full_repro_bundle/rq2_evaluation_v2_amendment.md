# RQ2 Evaluation v2 Amendment

## Authority, timing, and scope

Adopted on 2026-09-15 for `ghasempouri1984/ShopJournal-final-eval-redesign`,
branch `final-eval-redesign-v1`, from commit
`571c1a04e931b843f377d794acf1f37daae0ce28`.

This amendment supersedes only the RQ2 human-labeling and evaluation design
of v1, solely to reduce annotation burden. Rankings for all 40 queries were
already generated; no row-level ranking outcomes were inspected to design v2.
Zero final-RQ2 qrels, relevance labels, or RQ2 metrics exist at redesign and
method-freeze time. Historical pilot material is outside this final evaluation.

Queries, notes, retrieval split, candidate generation, Base/Full rankings,
scorer, weights, cue rules, and the relevance contract remain frozen. No query
or ranking rerun or tuning is authorized. RQ1 remains unchanged.

## Primary population and outcome-blind selection

The primary population is 20 cue-bearing queries: exactly four each from DIET,
GIFT, URGENCY, BUDGET, and dual-cue. Within each frozen intended stratum, compute
the hexadecimal SHA-256 digest of the UTF-8 encoding of:

```text
"20260915\nrq2-v2-primary-subsample\n" + opaque_slot_id
```

Here `\n` denotes a single LF newline. Sort by ascending digest, then ascending
opaque_slot_id, and take the first four per stratum. Use the existing opaque
query ID as opaque_slot_id. Selection uses only IDs and intended strata; freeze
it before mechanically extracting selected top-10 membership.

The remaining ten cue-bearing queries receive no v2 judgments and are excluded
from the v2 primary analysis. The ten cue-free queries remain mechanical
controls only and receive no human judgments: frozen Base=Full equality has
already been verified.

## Judgment set and unchanged relevance contract

For each selected query, judge exactly the deduplicated union of its already
frozen Base top 10 and Full top 10, by canonical item identity. The maximum is
20 judgments per query and 400 total. BM25 pooling and random supplements are
removed. An item also present in those historical sources remains eligible only
if it belongs to Base top 10 or Full top 10.

Reuse the frozen v1 blinded evidence and existing opaque judgment IDs; filter
the existing frozen label order. Preserve query, note, and evidence content
exactly and keep source, condition, product identifiers, ranks, and scores out
of the annotator presentation. Freeze v2 membership before labeling.

The relevance contract in Section 3 of `final_evaluation_system_spec_v1.0.md`
and its 0/1/2 scale remain unchanged. Copy the frozen instructions byte-for-byte.
Use one blind primary judge, a separate explicit uncertainty flag, and a required
non-empty reason. No labels are prefilled. The final export schema is exactly
`judgment_id,grade,uncertain,reason`. Freeze complete judgments before analysis;
this adoption/packet-construction task does not authorize labeling or metrics.

## Metrics and paired analysis

Primary: judged-union NDCG@10. For each condition, score its frozen top 10 using
grades from that query's Base-union-Full judged set. DCG uses gain
`2**grade - 1` and discount `log2(rank + 1)` for ranks 1 through 10. IDCG uses
the ten highest available grades in that same judged union. If IDCG is zero,
NDCG@10 is zero; flag and count these cases without dropping queries. This is
judged-union normalization, not catalog-wide normalization.

Secondary: Precision@10, the number of returned top-10 items graded 1 or 2
divided by 10; grade 0 is non-relevant. Unfilled positions contribute zero.
Every returned top-10 item must be judged; missing judgments are errors, not
implicit grade 0. Recall@10 is removed from v2.

Across the 20 queries, compute paired
`delta_q = NDCG@10_Full - NDCG@10_Base`. Report mean and median paired differences
and positive/zero/negative counts. Precision@10 differences are secondary.

## Stratified bootstrap

Use 10,000 replicates with `numpy.random.Generator(numpy.random.PCG64(20260915))`.
For each replicate, independently sample four paired queries with replacement
within each of DIET, GIFT, URGENCY, BUDGET, and dual, in that order, yielding
20 queries. Within-stratum input order is the frozen hash-selection order.
Compute the mean paired NDCG difference for each replicate and report the
two-sided 95% percentile interval at 2.5/97.5 with the linear percentile method.
Record the NumPy version when analysis is later authorized.

The interval describes uncertainty for this constructed balanced 20-query
experimental design and is not a population-effectiveness confidence interval.

## V1 preservation and freeze sequence

The existing v1 rank/pool execution is **HISTORICAL / SUPERSEDED BEFORE LABELING**.
Preserve all its artifacts byte-for-byte. The v1 pool is not the v2 judgment set;
no v1 relevance judgments may be collected or reused for v2. Only the unchanged
blinded evidence for v2-eligible items is reused.

Commit and push this amendment to `origin/final-eval-redesign-v1` before creating
the v2 packet. Bind the local selection, judgment set, and aggregate record to
that method-freeze commit and the source v1 pool-freeze SHA-256. Keep all row-level
selection/mappings, packets, and the portable annotation bundle local-only.
Publish only the permitted aggregate freeze and a narrowly necessary mechanical
helper. All nonconflicting v1 scientific provisions remain in force.
