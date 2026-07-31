# Codex Referee Review - MoonLab v1.2.0 Phases 2-3

- Date: 2026-07-31
- Reviewer: Codex
- Author under review: Claude
- Verdict: **ACCEPT**
- Outbound draft: **CLEARED FOR SENDING after the edits recorded below**

## Scope and provenance

I reviewed the frozen preregistration (`9d90bb8`), the pre-data phase-3
amendment (`8b2329f`), the authored harness, raw phase-2/phase-3 artifacts, the
candidate report, and the outbound draft. Commit and file timestamps preserve
the required order: preregistration, phase-2 evidence/amendment, then phase-3
code/data/report. The vendor clone was read only during this review.

The virtual environment was accidentally included in `f78ee15`, then removed
from the index and ignored in `04fb33e`. `git ls-files` now returns no path below
`upstream/moonlab_v120_reproduction/venv/`, and the local venv is ignored.

The copied `artifacts_phase2/dominance_results.jsonl` initially looked like a
provenance conflict because it embeds `git_head=40a764...` and `dirty=true`.
Its SHA-256 is exactly the same as the pre-existing results file shipped under
`benchmarks/dominance/results/` in the v1.2.0 clone; it is not output from this
run and is not used for any verdict. The executable clone itself is clean at
`4bf83a6c...`, and the reviewed benchmark/decoder source blobs exactly match the
peeled v1.2.0 tag.

## Harness audit

### DEM to decoder model

- Separator-based component splitting, boundary sentinel `0xFFFFFFFF`, detector
  endpoint ordering, observable bitmasks, XOR probability merging, log-odds
  weights, correlation accumulation, and hyperedge counting are correct for the
  frozen circuit family.
- I compared all three frozen DEMs against an independently written canonical
  translator that deduplicates per-mechanism component keys. A/B/C produced
  identical edge-key sets, edge probabilities, weights, correlation-key sets,
  correlation probabilities, and zero skipped hyperedges.
- The authored harness does not deduplicate repeated component keys within one
  mechanism. The frozen DEMs contain zero such mechanisms, so this has no effect
  on the reported study. Deduplication should be added before general reuse.

### ctypes ABI and buffers

- Function signatures match `src/qec/uf_decoder.h`: sizes, pointer types,
  return types, and argument order are exact.
- Detector input is `uint8`, transposed to detector-major layout, and C
  contiguous. Output is allocated `(num_observables, shots)`, matching the
  observable-major ABI.
- A seed-for-seed replay of all three configs reproduced every saved logical
  error rate and every McNemar discordant-pair count exactly. Both MoonLab modes
  returned only binary output bytes `{0, 1}` across 600,000 shots.
- The original harness converts output bytes to boolean without first asserting
  binary values. The referee replay closes that gate for this artifact; add the
  assertion before future reuse.

### Statistics and gates

- Wilson 95% intervals match an independent recomputation to floating-point
  precision.
- McNemar uses the continuity-corrected signed statistic
  `(abs(b-c)-1)/sqrt(b+c)`; positive values correctly favor the first decoder.
- Reductions are computed from integer error counts. The 0.45 VOID gate matches
  the preregistration, and no config is out of regime.

## Independent artifact verification

### Phase 2 vendor decoder front

All four rows recompute from raw counts:

| d | p | PM errors | Corr errors | Reduction | McNemar z | Corr better |
|---:|---:|----------:|------------:|----------:|-----------:|:------------|
| 5 | 0.002 | 499 | 383 | 23.25% | 5.53 | yes |
| 7 | 0.002 | 100 | 49 | 51.00% | 4.93 | yes |
| 5 | 0.005 | 7194 | 5966 | 17.07% | 17.31 | yes |
| 7 | 0.003 | 552 | 307 | 44.38% | 11.49 | yes |

Thus `corr_better_points=4`, all reductions are inside the claimed 17-81%
vendor range, all correlated-vs-PyMatching Wilson intervals are non-overlapping,
and all plain-UF/PyMatching intervals overlap.

### Phase 3 independent decoder harness

| Config | PM/UF/Corr errors | Reduction | McNemar z | Plain/PM CI overlap |
|:-------|:------------------|----------:|-----------:|:--------------------|
| A | 8067 / 8067 / 7945 | 1.51% | 2.253 | yes (identical rates) |
| B | 9793 / 9816 / 8351 | 14.72% | 18.414 | yes |
| C | 3888 / 3994 / 2847 | 26.77% | 19.519 | yes |

These values, stored Wilson intervals, and VOID results all recompute exactly.
C2a and C2b therefore satisfy their frozen criteria. Config C remains
generalization evidence, as preregistered.

### Sampling stability and vendor logs

- The three saved rerun blocks are text-identical and each contains the 6.01
  sigma detector-marginal failure. Because the front is internally seeded,
  these are deterministic replays, not independent statistical replications.
- The vendor log contains the exact `KeyError: 'mcnemar_z'` traceback from
  `run_dominance.py` and the Clifford table with correctness true and ratios
  1.62-1.70x.

## Verdict against preregistration

- **C1: PARTIAL.** Vendor-path speed direction reproduces, but its shipped
  correctness gate fails deterministically. The base preregistration's
  independent phase-3 sampler criterion was deferred before data and was not
  run; the report now says this explicitly.
- **C2a: REPRODUCED.** Plain UF and PyMatching intervals overlap on A and B;
  A is exactly identical to five decimal places.
- **C2b: REPRODUCED.** The phase-2 vendor rows satisfy the original
  non-overlapping-CI criterion, and the independent A/B tests satisfy the
  pre-data paired-test criterion.
- **C3: NOT RUN.** I left the optional stretch recorded as not run. Adding a
  new coherence surface is unnecessary to adjudicate C1/C2 and would widen the
  review after the primary study completed.

## Outbound-draft review

Every numeric claim matches the artifacts. I corrected four presentation
issues without changing findings: removed an unsupported Homebrew-install
claim, made agent assistance/authorship transparent, replaced adversarial
phrasing with reproducer-first wording, and scoped the sampling result as a
deterministic bug candidate rather than statistical certainty. A privacy scan
finds no personal names, Eliot context, private paths, or local identifiers in
the cleared draft.

## Residual limitations

- Phase-3 timing ran under concurrent load and remains non-evidentiary.
- The sampling reruns establish deterministic repeatability for one internal
  seed, not cross-seed persistence. F2 is therefore a bug candidate consistent
  with a systematic offset, not a completed localization or cross-seed proof.
- The two generic-harness hardening items above (component deduplication and
  explicit binary-output validation) are inert for this artifact but should be
  fixed before reusing the harness on other circuit families.

With those limits stated, no defect can make the recorded MoonLab decoder
advantage appear when it is absent. The phase-2 and phase-3 accuracy findings
are accepted, and the edited outbound draft is cleared for sending.
