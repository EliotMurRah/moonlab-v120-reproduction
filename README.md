# MoonLab v1.2.0 — Independent Reproduction Artifact Set

First independent reproduction of the MoonLab v1.2.0 dominance-front claims,
run on an Apple M2 Pro (macOS arm64, 12 physical cores). Filed publicly at the
maintainer's request (see the merge discussion of
[tsotchke/moonlab#20](https://github.com/tsotchke/moonlab/pull/20)).

Methodology was frozen before any data: preregistered criteria, no post-hoc
threshold changes. The study was agent-assisted and dual-controlled — the
phase-3 harness and referee report were authored by one agent (Claude) and
independently audited by a second (Codex), including a byte-level replay of
all 600,000 phase-3 decoded shots. Every number in the reports is recomputable
from the raw artifacts in this repository.

## Results at a glance

| Claim | Verdict |
|---|---|
| C1 — batched sampling beats Stim | **Partial**: speed direction reproduces on every row (up to 11.8× MT), but the shipped cross-engine correctness gate fails deterministically on this host (finding F2 below, since explained as a gate calibration defect; certification of the speed result remains the maintainer's call) |
| C2a — plain union-find matches PyMatching sub-threshold | **Reproduced** (vendor path ~4 decimals; independent harness to 5 decimals at config A) |
| C2b — correlated two-pass beats PyMatching | **Reproduced on both paths, with a measured boundary**: vendor workloads 4/4, reductions 17.07–51.0%; independent harness 3/3, reductions 1.51–26.77%; advantage compresses toward zero near threshold |
| F1 — dominance runner crash on decoder front | **Fixed** — merged as [#20](https://github.com/tsotchke/moonlab/pull/20) |
| F2 — batch-sampling correctness gate fails deterministically | **Explained (2026-09-09): a calibration defect of the gate statistic, not a sampler discrepancy; independently reached by the maintainer the same night (moonlab#21, PR #36); his candidate `b74c469` passes his repaired checks on this host and preserves the v1.2.0 sampled bytes** — see `RESULT_F2_CONTROLLED.md` (controlled comparison under the maintainer's four conditions, exact DEM reference, 2M shots per engine; candidate-unreferreed). Original observation: 6.01σ ST / 3.59σ MT detector-marginals gate on `surface_code_d5_r8_noisy`; fire rates ml=0.01350 vs stim=0.01347; bit-identical across reruns (front internally seeded) |
| F3 — Clifford front | **Reproduced cleanly**, 1.62–1.70× (n=20..500), correctness True at every size |
| F4 — correlated decode throughput | Trade-off measured: 0.35–2.13× vs PyMatching on vendor workloads (accuracy is bought with time at larger d) |

## File map

- `PREREGISTRATION.md` — criteria frozen before install
- `PHASE3_AMENDMENT.md` — phase-3 design frozen before phase-3 data (authorship swap, configs A/B/C)
- `PROVENANCE_PHASE1.md` — pinned environment: moonlab==1.2.0, stim==1.16.0, PyMatching==2.4.0; source at tag v1.2.0 (peeled `4bf83a6c47e7f1c53db14fcb2a61053499fd82df`)
- `phase3_decoder_harness.py` — independently authored harness (own DEM→edge translation, ctypes ABI per public headers, Wilson CIs, continuity-corrected signed McNemar)
- `phase2_vendor_harness_stdout.log` — vendor-path runner output incl. the F1 traceback and first F2 observation
- `artifacts_phase2/decoder_front_standalone.json` — flagship decoder front, vendor path, 1M shots/workload
- `artifacts_phase2/dominance_results.jsonl` — **non-evidentiary**: byte-identical copy of a results file shipped in the v1.2.0 clone, preserved for provenance only
- `artifacts_phase3/phase3_decoder_results.json` — independent-harness results (200k shots/config, fresh entropy)
- `artifacts_phase3_sampling_stability.log` — 3× sampling-front reruns establishing F2 determinism
- `REPORT_PHASE23.md` — referee report (verdicts against preregistered criteria)
- `REVIEW_PHASE23_CODEX.md` — independent adversarial audit of the harness and report (ACCEPT)
- `CONTROLLED_COMPARISON_PREREG.md` — F2 controlled comparison, decision rules frozen before data (2026-09-08)
- `controlled_sampler_comparison.py` — F2 harness: vendor builders/translation/sampling paths imported unmodified; exact per-detector reference from the DEM; shipped statistic, two-sample version, Stim-vs-Stim null; pooled tests; rules evaluated in code. Reruns in ~18 s (`--moonlab-src`, `--lib-dir`)
- `artifacts_f2_controlled_r2/` — F2 raw artifacts: `results.json`, per-seed detector counts for MoonLab ST/MT, Stim, and the Stim null partner on four workloads, exact vectors, translated circuits, labels (run r2 reproduced run r1 byte for byte)
- `CONTROLLED_COMPARISON_PREREG_F2B.md`, `f2b_mt_round1_followup.py`, `artifacts_f2b_mt_round1/` — preregistered follow-up of one exploratory signal (MoonLab MT, round-1 detectors) on 8M fresh shots: not replicated
- `RESULT_F2_CONTROLLED.md` — F2 result report, with the internal review's findings and dispositions
- `artifacts_f2_candidate_b74c469_vendorchecks/` — independent rerun of the maintainer's candidate `b74c469` (`astra/stim-parity-v121`) with his three documented commands, verbatim, outputs and exit codes (unit tests OK; sampling-reference probe PASS 15/15; joint audit passed 10/10)
- `artifacts_f2_candidate_b74c469_ourharness/` — this study's harness against the candidate build: every sampled count byte-identical to the v1.2.0 build (24/24 files)
- `artifacts_f2_v121_a15dabc_vendorchecks/`, `artifacts_f2_v121_a15dabc_ourharness/` — the same two reruns on the `v1.2.1` tag (`a15dabc`, contains the #36 gate fix): vendor checks pass (unit tests OK; sampling-reference PASS 15/15; joint audit passed 10/10); 24/24 raw files byte-identical to v1.2.0
- `SHA256SUMS` — hashes of every file above

## Redaction note

Exactly two lines of `phase2_vendor_harness_stdout.log` (the F1 traceback)
contained local absolute paths; the local clone prefix was replaced with
`<MOONLAB_CLONE>`. No other bytes in any raw artifact were altered.

Commit ids cited inside the reports (e.g. the preregistration freeze commits)
refer to a private study workspace repository; the freeze ordering they attest
is available to the maintainer on request.

## Re-run sketch

```
python3 -m venv venv && venv/bin/pip install moonlab==1.2.0 stim==1.16.0 PyMatching==2.4.0
git clone https://github.com/tsotchke/moonlab && cd moonlab && git checkout v1.2.0
cmake -B build-f3 -DCMAKE_BUILD_TYPE=Release && cmake --build build-f3
# vendor decoder front, standalone (runner crash F1 is fixed on master by #20):
MOONLAB_LIB_DIR=$PWD/build-f3 PYTHONPATH=$PWD/bindings/python \
  python3 benchmarks/dominance/fronts/f3_decoder_vs_pymatching.py
# independent harness (from this repo):
MOONLAB_LIB_DIR=<moonlab>/build-f3 python3 phase3_decoder_harness.py
```

F2 controlled comparison (from this repo, same venv and build directory):

```
python3 controlled_sampler_comparison.py --moonlab-src <moonlab> --lib-dir <moonlab>/build-f3 --out artifacts_f2_rerun
python3 f2b_mt_round1_followup.py       --moonlab-src <moonlab> --lib-dir <moonlab>/build-f3 --out artifacts_f2b_rerun
```

Scope: single-machine claims only. MPI/multi-GPU, GPU backends, and crypto
beyond import smoke were out of scope for this study.
