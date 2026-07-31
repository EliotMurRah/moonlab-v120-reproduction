# MoonLab v1.2.0 Independent Reproduction — Referee Report (Phases 2-3)

- Date: 2026-07-31
- Author of this report and the phase-3 harness: Claude
- Referee review: **ACCEPTED by Codex** (D1 inversion; see
  `REVIEW_PHASE23_CODEX.md`)
- Host: Apple M2 Pro (12 physical cores), macOS 26.5.2, arm64, 16 GiB
- Subjects: moonlab==1.2.0 wheel + source at tag v1.2.0 (peeled 4bf83a6c...),
  stim==1.16.0, PyMatching==2.4.0. Build: cmake Release `build-f3`.
- Governing documents: PREREGISTRATION.md (committed 9d90bb8, before any install),
  PHASE3_AMENDMENT.md (committed before phase-3 data).

## Verdicts against preregistered criteria

- **C1 (batched sampling exceeds Stim): PARTIAL - VENDOR-PATH DIRECTION
  REPRODUCED; FULL CERTIFICATION NOT RUN.** Speed leads on every row of the vendor front on this host
  (1.07-2.06x single-thread, 2.7-11.8x all-cores; detector sampling 1.6-9.3x). But
  `correctness_ok = False` deterministically (finding F2). Per the vendor charter
  ("a front that reports correctness_ok=False fails the campaign regardless of
  throughput"), the front fails on this host until F2 is explained or fixed. The
  base preregistration's independent phase-3 sampler driver was explicitly deferred
  in the pre-data amendment, so C1 is partial rather than fully reproduced.
- **C2a (plain union-find matches PyMatching sub-threshold): REPRODUCED.** Vendor
  path: uf_err == pm_err to ~4th decimal on all four vendor workloads. Independent
  harness: identical to 5 decimals at config A (0.04034 == 0.04034); overlapping
  Wilson 95% CIs at B (0.04908 vs 0.04897, n=200000).
- **C2b (correlated two-pass beats PyMatching): REPRODUCED, WITH A MEASURED
  BOUNDARY.** Vendor workloads (his configs, 1M shots each, standalone front,
  code unmodified): 4/4 `moonlab_corr_better`, reductions 17.07% / 23.25% /
  44.38% / 51.0%, McNemar z 4.9-17.3 — all inside the claimed 17-81% band.
  Independent harness (fresh code, fresh entropy, our configs, 200k shots):
  correlated better in 3/3 with z = 2.25 / 18.41 / 19.52, reductions 1.51% /
  14.72% / 26.77%. Combined 7/7 datapoints show correlated strictly better;
  the SIZE of the advantage compresses toward zero as the operating point
  approaches threshold (1.5% at d=3, p=0.008) and grows in cleaner regimes.
  The 17-81% claim is accurate AS SCOPED to the vendor-tested configurations;
  it is not a universal constant, and the boundary is now independently mapped.
- **C3 (braiding coherence): NOT RUN** (time-boxed out; recorded, not silently
  dropped).

## Findings for upstream

- **F1 — Shipped harness crash.** `run_dominance.py:85` prints `r['mcnemar_z']`;
  the decoder front emits nested `corr_vs_pm.z` instead. KeyError crashes the
  runner on the decoder front. Workaround: run the front standalone via its
  `__main__`. Exact traceback preserved in `phase2_vendor_harness_stdout.log`.
- **F2 — Deterministic sampling-distribution offset (bug candidate).** The
  batch-sampling front's cross-engine correctness gate fails on this host in
  4/4 runs with BIT-IDENTICAL statistics (front is internally seeded):
  detector marginals gate 6.01 sigma single-threaded / 3.59 multi-threaded on
  `surface_code_d5_r8_noisy`; fire rates ml=0.01350 vs stim=0.01347 (~0.2%
  relative). The effect is physically small, strongly significant under the
  shipped gate, and deterministic for the shipped internal seed. It is
  consistent with a systematic difference in noise application/translation
  between the MoonLab sampler path and the Stim reference on this workload,
  but the identical reruns are not independent cross-seed replications. Cause
  is not localized from outside (it could sit in the sampler or in the front's
  Stim-workload translation; both are vendor code).
- **F3 — Clifford front fully reproduces.** correctness True at every size,
  lead 1.62-1.70x over Stim (n=20..500).
- **F4 — Correlated decoding's accuracy is bought with time.** Correlated
  decode throughput on vendor workloads: 0.35x-2.13x vs PyMatching (below 1x
  at d=7), while plain UF is 4.7-8.3x faster. Not a claim violation (accuracy
  was the correlated claim); worth stating as the operating trade-off.

## Methodology notes and limitations

- Phase-2 "vendor path" = vendor code unmodified; decoder front invoked via its
  own `__main__` due to F1 (invocation deviation recorded pre-data).
- Phase-3 harness shares only the public ctypes ABI and standard DEM->edge
  mathematics with vendor code; orchestration, parsing, gating, and statistics
  are freshly authored. Fresh entropy seeds recorded per config.
- Codex's referee replay confirmed detector-major contiguous input, observable-major
  output, binary-only decoder predictions, and exact reproduction of every saved
  rate and discordant-pair count. The original harness does not itself assert that
  output bytes are binary; this was independently checked for all 600,000 decoded
  shots and should become an explicit assertion before the harness is reused.
- The harness does not deduplicate repeated component keys within one mechanism as
  the vendor translator does. No frozen circuit contains such a duplicate; a
  semantic comparison found identical edge and correlation maps on A, B, and C.
- Phase-3 stability reruns discovered the sampling front is internally seeded;
  "fresh entropy" did not apply there. The reruns therefore establish
  determinism of F2 rather than sampling variance (stronger, as it happens).
- Decode timings in phase 3 ran under concurrent load and are non-evidentiary;
  all phase-3 accuracy results are load-independent. Vendor-front timings ran
  unloaded.
- This study tests single-machine claims only. MPI/multi-GPU/hardware
  attestations, GPU backends, and crypto beyond import smoke are out of scope.

## Artifacts

- `phase2_vendor_harness_stdout.log` (runner output incl. F1 traceback, F2 first
  observation, F3 tables) - `artifacts_phase2/dominance_results.jsonl` (an
  exact copy of the pre-existing file shipped in the v1.2.0 clone; preserved
  but not used as run evidence) -
  `artifacts_phase2/decoder_front_standalone.json` (flagship, vendor path) -
  `artifacts_phase3/phase3_decoder_results.json` (independent harness) -
  `artifacts_phase3_sampling_stability.log` (3x reruns) -
  `phase3_decoder_harness.py` (authored code) - `PROVENANCE_PHASE1.md`.

## Bottom line

On an independent Apple M2 Pro host, the Clifford speed claim reproduces cleanly;
the flagship decoder-accuracy claim reproduces on both the
vendor path and a freshly authored independent harness, with its advantage now
honestly mapped from ~1.5% (near threshold) to ~51% (clean regime); the batch
sampler is fast as claimed but carries a small deterministic distribution
offset that the vendor's own correctness gate rightly refuses to certify; and
the shipped benchmark runner has a crash bug on its flagship front. Every
finding is reproducible from the artifacts above.

- Claude (author). Codex referee verdict: **ACCEPT**, with C1 scoped as partial.
