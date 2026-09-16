# Martina's FINAL RQ2-v2 end-to-end reproduction

**Private student research package. Keep it local. Do not commit, push, publish,
or upload this directory or its inputs.** This package reproduces the final v2
experiment frozen in `ghasempouri1984/ShopJournal-final-eval-redesign`, branch
`final-eval-redesign-v1`, HEAD `d3107c78013bfe33d9f0e267daeb7cd4702f20ac`.

## What you will reproduce

Starting with the exact Amazon metadata file and your exact returned judgment
CSV, you independently reconstruct the retrieval catalog, all 40 candidate
sets and Base/Full rankings, the deterministic 20-query v2 selection, its
313-judgment universe, and the final NDCG@10 and Precision@10 paired results.
The script runs locally, reads inputs, prints aggregate results, and writes no
files. It has no network calls. Product IDs and scores used during reconstruction
remain in memory and are not printed or exported.

The scientific path is:

```text
authenticated Amazon metadata + frozen retrieval membership
  -> retrieval catalog and frozen arithmetic rating mean
  -> exact frozen 40 queries + 40 paired note term lists
  -> shared candidates (cap 200)
  -> Base and Full rankings for all 40 pairs
  -> deterministic v2 selection (4 queries in each of 5 strata)
  -> each selected query's Base top10 union Full top10
  -> reconstructed opaque judgment IDs + your returned CSV
  -> NDCG@10 and Precision@10, Full minus Base
  -> frozen stratified bootstrap and exact final aggregate verification
```

**Quick final-analysis reproduction** starts from already prepared analysis
inputs and checks only the metric/aggregation stage. The separate earlier
`martina_rq2_repro_bundle` serves that purpose. **This full reproduction** starts
from external metadata and reconstructs rankings before joining your labels.
It does not use that quick bundle or its prepared analysis input. Passing the
quick analysis alone does not verify catalog construction or ranking reproduction.

## Required external files

### 1. Amazon metadata only

Obtain the file from the exact dataset revision below. You can download it in a
browser, then place it in a local data folder outside this package, for example
`C:\RQ2-data\meta_Grocery_and_Gourmet_Food.jsonl`. Any path is supported; pass it
explicitly with `--metadata`. The script does not download or discover data.

- Dataset: `McAuley-Lab/Amazon-Reviews-2023`
- Revision: `2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e`
- Path: `raw/meta_categories/meta_Grocery_and_Gourmet_Food.jsonl`
- [Exact metadata download](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/2b6d039ed471f2ba5fd2acb718bf33b0a7e5598e/raw/meta_categories/meta_Grocery_and_Gourmet_Food.jsonl)
- Size: **1,382,105,675 bytes** (about 1.38 GB / 1.29 GiB)
- SHA-256: `ed9b24ea707f7010b5cb321462a8e896ad1fcd59620fbc55f05084c3da59842e`

**Only metadata is required. Amazon review data is not required.** Keep the
original JSONL bytes: do not reformat, decompress a different source into this
name, edit line endings, or substitute a newer dataset revision. Wrong size or
SHA-256 causes refusal before scientific computation. The streaming catalog
pass hashes the file again to detect changes during reading.

### 2. Your frozen returned judgments

Supply the exact CSV you produced earlier, for example
`C:\RQ2-data\rq2_primary_judgments_returned.csv`. The filename is flexible; the
bytes are fixed. This package intentionally does not contain your CSV or labels.

- SHA-256: `3e2240796c793917cbc1e87fd268da174a8d9864f966d5f20a86dc23f12c3b57`
- Exact ordered header: `judgment_id,grade,uncertain,reason`
- Exactly **313 data rows and 313 unique judgment IDs**
- Grades: `0`, `1`, `2`; uncertainty: `true`, `false`; nonempty reasons

Do not resave the file through spreadsheet software: changing CSV quoting,
encoding, line endings, or any cell changes its hash. The exact hash is checked
before parsing. Every reconstructed v2 judgment must have one label; missing or
extra IDs fail. Uncertain judgments retain their supplied grades, as in the
frozen analysis. Reasons and uncertainty are validated but do not weight metrics.

## Setup and exact commands

Python **3.11.x** is recommended. The verified environment is CPython 3.11.15
with **NumPy 1.26.4**. NumPy is the only nonstandard dependency. Install it once;
the reproduction itself is offline. `--verify` requires NumPy 1.26.4 and checks
exact numeric equality without rounding or tolerances.

Open a terminal in this directory. Windows PowerShell or Command Prompt:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B reproduce_rq2_end_to_end.py --metadata "C:\RQ2-data\meta_Grocery_and_Gourmet_Food.jsonl" --labels "C:\RQ2-data\rq2_primary_judgments_returned.csv" --verify
```

With an existing Python environment, this normal single-line Windows command
also works:

```powershell
python -B reproduce_rq2_end_to_end.py --metadata "C:\RQ2-data\meta_Grocery_and_Gourmet_Food.jsonl" --labels "C:\RQ2-data\rq2_primary_judgments_returned.csv" --verify
```

macOS/Linux, with Python 3.11 and the pinned requirement installed:

```sh
python3.11 -m pip install -r requirements.txt
python3.11 -B reproduce_rq2_end_to_end.py \
  --metadata "/path/to/meta_Grocery_and_Gourmet_Food.jsonl" \
  --labels "/path/to/rq2_primary_judgments_returned.csv" \
  --verify
```

No paths belonging to the package author are required. Inputs beside the script
are resolved relative to the script, so the command also works from another
working directory when you provide the script path. Progress goes to stderr;
the final aggregate JSON goes to stdout. Exit code 0 plus `"verification":
"PASS"` means all requested checks passed; failures exit 1. Without `--verify`,
input authentication, selection and coverage checks still run, but exact ranking
and aggregate agreement is not enforced and the overall status is
`NOT_REQUESTED`. Use `--verify` for reproduction.

## Private bundled inputs and provenance

`retrieval_parent_asins.txt` is a **private research asset**, mechanically derived
from the already frozen canonical partition manifest, not a new partition. It
contains exactly 301,889 unique canonical retrieval IDs in ascending Unicode
order, one per line. Assembly verified 301,385 generation IDs and zero overlap.
Generation membership is not distributed. The fixed retrieval-file hash binds
that checked derivation for subsequent standalone runs.

- Manifest repository: `ghasempouri1984/ShopJournal-Master`
- Ref: `27cc8a0755c0ff56301fc448e2357060100085f8`
- Path: `data/partition/ggf_partition_manifest_20260530.json`
- Manifest SHA-256: `3f0feb06d9d1c4e9ffe3bc98ed3333ff1fc7c2f05dbbe00681d06c006fcaec57`
- Canonical retrieval-list identity **and derived file SHA-256**:
  `da7cfa28541f6f646095c94b2e8f85828fbcb33f0694f8ea30cc7efbc91fbe26`

`rq2_final_queries.csv` retains only the four requested fields from the final
40-query source. The source uses semicolon CSV; this projection uses comma CSV
with UTF-8 and LF. Field strings, including query text, are unchanged: no trimming,
case conversion, spelling repair, or other silent normalization is applied to
stored queries. The frozen scorer applies its own lexical rules at ranking time.

- Underlying canonical final query-set SHA-256:
  `103772fdaded03c99a35d5227222aeb1d087eeb1ed46f978b939a71bd53b9986`
- The projection has its own byte hash in `bundle_manifest.json` and the table below.
- Assembly checked every query's UTF-8 hash against the frozen per-row provenance.

`rq2_note_inputs.json` contains exactly `opaque_slot_id`, `canonical_note_id`,
and `distinctive_terms` for each of the 40 pairings. Terms are projected unchanged
from the authenticated canonical notes and matched to the frozen selected-note
pairings. **Note histories are intentionally not distributed:** source product
histories, generation product IDs, raw reviews, and provenance narratives are
unnecessary for final ranking reproduction. Note generation is upstream of the
frozen inputs and is not rerun.

- Selected-note/pairing SHA-256:
  `633f2513e891c734bf81d20fb7aff833e732678a713e1b4f7234158fba11bf04`
- Canonical notes SHA-256:
  `020fc966474b530d91d0d3a297946169eb464c400a549738e8e670a23d8c4051`
- Canonical notes: same Master ref, `data/notes/ggf_notes_v0.1.jsonl`

## How the frozen ranking works

Read the local `final_evaluation/lexical.py`, `cues.py`, and `scoring.py`. These
are byte-identical copies of the frozen scientific modules, with the original
package initializer. The wrapper calls `prepare_catalog` and `rank_pair` directly;
it does not substitute a simplified scorer or use precomputed rankings.

The metadata stream retains only retrieval members, using `parent_asin` as the
canonical identity and `title`, `price`, and `average_rating` as catalog inputs.
Duplicate retrieval IDs, conflicting records, missing membership, or changed
counts fail. `valid_rating` rejects booleans, missing/unconvertible/nonfinite
values, and values outside [1,5]. The mean is `math.fsum` over valid ratings in
ascending canonical ID order divided by the valid count. For this frozen input,
all **301,889** ratings are valid and the exact mean is **4.172684993490985**
(`0x1.0b0d455be370bp+2`). The scorer's frozen missing/invalid item policy is to
substitute that catalog mean for the rating prior; none requires it in this run.

Shared candidates match distinct units in the union of query units and note-only
tokens. Sort by descending matched-unit count, then ascending canonical ID; keep
200. Both conditions score this identical candidate sequence:

```text
Base = (matchQuery + matchNotes) + ratingPrior
Full = Base + cueScore
ratingPrior = valid item mean rating / 5
```

All four coefficients equal 1. Coverage is unweighted; no term-count weighting is
introduced. Cues are extracted from the query only. Title/price evidence supplies
compatibility; missing support is zero. Numeric budgets use the frozen USD parser,
strict/inclusive bounds, exclusions, and rejection rules in `cues.py`. Final
orders use descending unrounded scores and ascending canonical ID ties. The
script checks 200 candidates for each query, all nine executable numeric budgets,
and exact Base=Full equality for all ten cue-free controls.

### Ranking signature serialization

`expected_ranking_signatures.json` contains only opaque query IDs and SHA-256
signatures of each ordered candidate sequence, Base top 10, and Full top 10.
It contains no product IDs, rankings, or scores. Each signature hashes:

```python
hashlib.sha256(("\n".join(ordered_ids) + "\n").encode("utf-8")).hexdigest()
```

There is one LF byte after **every** ID, including the last; no BOM, CR, JSON,
spaces, or sorting added during serialization. Candidate order and each ranking
order are preserved separately. Assembly authenticated the private ranking file
and its seal, then extracted these signatures. The runtime independently computes
all 120 signatures (3 for each of 40 queries) and requires exact match in
`--verify` mode. Retrieval membership is the only distributed product-ID list.

## Selection, judgment join, and analysis

Selection depends only on the opaque query ID and intended stratum. Hash
`UTF8("20260915\nrq2-v2-primary-subsample\n" + opaque_slot_id)`, sort by ascending
hexadecimal digest then ascending opaque ID, and take four from each of DIET,
GIFT, URGENCY, BUDGET, and dual, in that order. `expected_v2_selection.json`
binds the exact frozen selected sequence. The other ten cue-bearing queries and
ten cue-free controls receive no v2 metrics.

For each selected query take the deduplicated Base-top10 union Full-top10.
Reconstruct each judgment ID as the full SHA-256 hexadecimal digest of:

```python
f"20260914\njudgment-id/{opaque_slot_id}\n{parent_asin}".encode("utf-8")
```

There is no trailing LF in this judgment-ID preimage. This is the original
judgment-ID rule retained by v2. Assembly checked it against all 313 frozen v2
mappings. The standalone run computes IDs anew and demands exact equality between
the reconstructed 313-ID universe and the supplied label CSV's IDs.

NDCG@10 uses gain `2**grade - 1` discounted by `log2(rank+1)`. IDCG uses the ten
highest grades in that query's judged union. Zero IDCG gives NDCG zero and the
query remains in the analysis. Precision@10 counts grades 1 and 2 as relevant,
divided by 10. Both paired summaries use **Full minus Base**: mean, median, and
positive/zero/negative counts. Floating-point operation order follows the frozen
v2 controller, including `math.fsum` for DCG and paired means.

The NDCG mean-difference bootstrap uses 10,000 replicates, NumPy PCG64 seed
20260915, and four draws with replacement from each of the five strata in the
order above. Within-stratum input order is the frozen selection order. Each
20-query replicate uses the exact `np.concatenate(draws).mean()` operation.
The 2.5/97.5 percentiles use `method="linear"`. No Precision bootstrap is added.
The bundled committed aggregate is opened for comparison after calculation;
it never supplies calculated metric values.

## Expected final results

All entries below are paired Full-minus-Base differences across 20 queries.

| Metric | Mean | Median | Positive / zero / negative |
| --- | --- | --- | --- |
| NDCG@10 | 0.30081140426797137 | 0.05525379734128455 | 11 / 7 / 2 |
| Precision@10 | 0.22000000000000003 | 0.15 | 12 / 8 / 0 |

NDCG bootstrap interval: **[0.14704192509677733, 0.4590615897564671]**.
Zero-IDCG queries: **2**. Exact results must also match the byte-copy of
`final_evaluation/rq2_v2_result_v1.json` distributed as `rq2_v2_result_v1.json`.

## Resources and local verification

The frozen scorer scans the 301,889-title catalog for each of 40 queries and uses
one CPU process. Allow tens of minutes, potentially longer on a slow laptop;
runtime depends on CPU, storage, and competing work. No GPU is needed. A practical
conservative allowance is 2 GiB of available RAM and 3 GB of free disk for metadata,
Python/NumPy, and the small bundle. Metadata is streamed and is not copied into
memory in full. The script creates no catalog cache or ranking output files.
The metadata file remains outside the roughly 3.5 MB bundle. A Python virtual
environment adds its own disk usage.

Full local verification **PASS** from a copied bundle, using isolated Python
(`-I -B`), CPython 3.11.15 and NumPy 1.26.4.
Measured script runtime: **946.782067 seconds (15 minutes 46.78 seconds)**, including
metadata authentication, catalog construction, all rankings, and analysis.
External-process wall time: 947.454950 seconds.

The copied run verified 301,889 retrieval items and valid ratings; exact mean
4.172684993490985; 200 candidates per query; all 120 signatures across
40 queries; ten cue-free Base=Full controls; the exact selected 20; exact
313-label coverage; both paired aggregates; and the exact bootstrap interval.
Thirty focused integrity, rejection, coverage, and analysis checks also passed.
The run wrote no bundle files. Only this documentation and the checksum
inventory were finalized afterward; every executed script and scientific
input remains byte-identical to the verified copy. All 145 pre-existing
repository files, including official private outputs, passed a before/after
SHA-256 comparison. Nothing was committed or pushed.

## Scientific limits and historical v1

This is a **constructed, balanced query set**, evaluated by **one primary judge**.
It is a **reranking evaluation** with a shared capped candidate set and judged-union
normalization. It does not measure catalog-wide relevance, general user traffic,
or population effectiveness. The bootstrap describes uncertainty for this
constructed balanced 20-query design; it is not a population-effectiveness
confidence interval.

**V1 BM25 pooling, random supplementation, Recall@10, and the 1,077-item labeling
design are historical and were superseded before labeling.** They are not
implemented, executed, or reproduced here. The final v2 reuses unchanged frozen
Base/Full rankings and the judgment-ID rule from the earlier ranking stage, then
uses only its selected 20 queries and 313 Base/Full-union judgments. The retained
filename `rq2_v2_result_v1.json` is the version-1 result artifact for the **v2**
evaluation; it is not a v1 scientific result. **This package follows the FINAL v2
scientific path.**

The included amendment is preserved byte-for-byte as historical scientific
authority. Its historical operational freeze/publish instructions are not steps
for Martina to execute. This educational reproduction does not rerun the official
experiment controller, change its artifacts, or publish any results.

## File inventory and integrity

The table below records every asset and its SHA-256. `bundle_manifest.json`
binds frozen source identities, derivation checks, and all scientific assets.
The script pins that manifest's SHA-256 and authenticates assets before imports
or computation. `SHA256SUMS.txt` covers every distributed file except itself;
its own digest is supplied in the handoff. It also covers this README and the
reproduction script, avoiding a self-referential hash. No metadata, reviews,
returned labels, note histories, raw ranking files, product scores, or qrels
are packaged.

### Asset SHA-256 values

| Bundle file | SHA-256 |
| --- | --- |
| `bundle_manifest.json` | `8a76f6062774923bcc1bc7df8044c08db9c34ba86148e42d2c7eaf11c2c92bc4` |
| `expected_ranking_signatures.json` | `f460a43a99da8388351613aabc4e38e1e873885446f9d8175a056a1cf0423fb5` |
| `expected_v2_selection.json` | `67b49491a0589b25c6cdd8c763de28d0439166ab1714290a5285dd3b1da2fe93` |
| `final_evaluation/__init__.py` | `6b6d98c78fe1648e24250e364da66818d855593060882bf9088cc2c21a59fa90` |
| `final_evaluation/cues.py` | `b3db6382d1ec232a99583fac821ba1d79384cb04107f13077490bf6ba81f9251` |
| `final_evaluation/lexical.py` | `8c8843747a436d897209e3e5dd3b1eca0a3f4cfd1c9b51c9d8fe4221ea1b711e` |
| `final_evaluation/scoring.py` | `48d2f97150527b8d6b381e80cec7bf3c990c20f8716ec3ecc6649e3a33193818` |
| `reproduce_rq2_end_to_end.py` | `400a53ac415d8ee32e151f4e7abed481f28b193c42a78c60d04dedca230b6264` |
| `requirements.txt` | `e77e7045d01a9431264f9262c6b199d8e7988c139276a5266a3cf689588ad66e` |
| `retrieval_parent_asins.txt` | `da7cfa28541f6f646095c94b2e8f85828fbcb33f0694f8ea30cc7efbc91fbe26` |
| `rq2_evaluation_v2_amendment.md` | `78befd1e8da9b2b2b7cc1023b3b56664a6c141bc4c0fe56330db865c156720da` |
| `rq2_final_queries.csv` | `ab0b853ff6bf420250b2f16fda56bf1925b53d8eac466e793863e17f611151f4` |
| `rq2_note_inputs.json` | `aa15498967fa1793697db98fdc24aced00e0eef4fccd91516d15c73c5118df59` |
| `rq2_v2_result_v1.json` | `1d89ee28988dde5cc39c7163b2d4a412ee648793a63ceab3748d3a53d5a50f8f` |

The README and `SHA256SUMS.txt` complete the inventory. The README hash is in
`SHA256SUMS.txt`; the checksum file cannot contain its own hash, which is provided
in the handoff. These integrity references detect changed bytes; keep the trusted
original handoff when transferring this private package.
