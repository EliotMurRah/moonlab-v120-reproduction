# Preregistration — Controlled sampler-vs-reference comparison (issue #21, F2)

- Frozen: 2026-09-08 (before any confirmation data; a smoke run with
  shots=2000 is permitted only to validate that the harness executes, and its
  numbers are non-evidentiary)
- Author: Claude (harness + this document), for Eliot / EliotMurRah
- Referee: none available at freeze (Codex idle); result therefore carries the
  CANDIDATE-UNREFEREED cap unless independently rerun
- Harness: `controlled_sampler_comparison.py` (this directory)

## Fixed conditions (the maintainer's four)

1. Workload: `build_surface_code_noisy(5, 8, ...)` imported from the v1.2.0
   front `benchmarks/dominance/fronts/f3_batch_sampling_vs_stim.py` at commit
   `4bf83a6c47e7f1c53db14fcb2a61053499fd82df`. Not re-implemented.
2. Translation: the vendor `_to_stim_with_detectors`. Not re-implemented.
3. Sampling path: vendor `moonlab_sample_detectors` (nthreads=1 "ST" and
   nthreads=0 "MT") vs vendor `stim_sample_detectors` on
   `compile_detector_sampler(seed=seed+1)`, exactly as the shipped gate.
4. Seeds: the shipped gate seed 1234 first, then 1..9. 200,000 shots per seed
   per engine (the gate's shot count). Stim's gate-null partner uses
   seed+100001.

Library: `libquantumsim.dylib` built with `cmake -DCMAKE_BUILD_TYPE=Release`
from the same commit on this host (sha256 recorded in results.json).

## Reference

Exact per-detector fire probability from Stim's DEM of the translated circuit:
P(D) = (1 - prod_{i: D in err_i}(1 - 2 p_i)) / 2. Validity of the formula is
checked against one 4,000,000-shot Stim sample (seed 777): the check passes if
max|z| over 120 detectors is < 4.5 and sum(z^2)/120 is in [0.75, 1.25]. If the
check fails, the exact reference is not used and the study stops.

## Workloads

`full_p2_p1_pm` (p=0.001 on all three channels, the gate's workload) plus
three single-channel isolations: `only_p2_depolarize2`, `only_p1_depolarize1`,
`only_pm_measure_flip`, each at p=0.001 on that channel alone.

## Decision rules (per engine, pooled over 10 seeds = 2,000,000 shots)

- R1 "engine deviates from reference": max|z| vs exact >= 5.0 OR
  sum(z^2)/120 >= 1.5. Otherwise "consistent with reference".
- R2 "gate miscalibrated": the shipped statistic on Stim-vs-Stim (null pairs)
  reads >= 4.0 in at least 3 of 10 seeds. (Under a correct calibration the
  max over 120 detectors of a two-sample z is expected around 2.5-3.5.)
- R3 "localised": if R1 fires on the full workload, the channel isolation in
  which R1 also fires names the responsible translation/sampling channel; if
  none fires alone, the deviation is attributed to a channel interaction.
- Fire-rate difference alone (ml vs stim aggregate) decides nothing.

## What a result can and cannot say

It can say whether MoonLab's detector sampler, on this workload and this host,
matches the exact marginals implied by the circuit the vendor translation
hands to Stim, and whether the shipped gate's sigma is calibrated. It cannot
say which of MoonLab's C source lines is responsible, nor anything about
throughput, nor anything about other workloads.
