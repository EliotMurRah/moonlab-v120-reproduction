# Preregistration addendum — F2b: MoonLab MT round-1 exploratory signal

- Frozen: 2026-09-09, before any F2b data.
- Author: Claude, for Eliot / EliotMurRah. No independent referee available;
  result carries the CANDIDATE-UNREFEREED cap.
- Script: `f2b_mt_round1_followup.py` (this directory).

## Trigger (exploratory, from the F2 controlled comparison)

The internal review of `artifacts_f2_controlled` (finding M2) noted, on the
full workload, MoonLab MT (nthreads=0), the 16 round-1 detectors: 443,231
fires observed over 2,000,000 shots vs 446,137 expected from the exact
marginals (−0.65 %), negative in 8 of 10 seeds, correlation-corrected
z ≈ −3.17. Family-wise over the 24 engine×round looks the reviewer made,
≈ 3.6 %. Not present in the three single-channel isolations (MT round-1 mean
z −0.20 / −0.41 / +0.19). The frozen rule R1 did not fire. This addendum
exists so that the signal is either replicated or retired on fresh data,
rather than left as an unreported anomaly.

## Design

- Workload: full vendor noise model only (`build_surface_code_noisy(5, 8)`,
  p2 = p1 = pm = 0.001), same vendor builder, translation, detector set, and
  sampling paths as F2.
- Engines: MoonLab MT (nthreads=0) is the subject. MoonLab ST (nthreads=1)
  and Stim (`compile_detector_sampler(seed=seed+1)`) run on the same seeds as
  controls.
- Seeds: 101–140 (40 seeds × 200,000 shots = 8,000,000 shots per engine).
  None of these seeds was used in F2 or its smoke run.
- Reference: the exact per-detector marginals from the DEM, as in F2.

## Primary statistic (one)

T = total fires over the 16 round-1 detectors, summed over all 8,000,000
shots, MoonLab MT. E = 8,000,000 × Σ_{D ∈ round 1} p_exact(D).
SE = sqrt(8,000,000 × v̂), where v̂ is the sample variance across shots of the
per-shot round-1 fire count (model-free; absorbs detector correlations).
z = (T − E) / SE. The per-shot count histogram (K = 0..16) is saved per seed
so v̂ and z are recomputable.

## Decision rule

- |z| ≥ 4.0 → **replicated**: a real MT round-1 effect; magnitude reported.
- |z| ≤ 2.0 → **not replicated**: consistent with no effect at this
  sensitivity.
- 2.0 < |z| < 4.0 → **inconclusive**; no further looks without a new
  preregistration.
Two-sided; the sign is reported.

Power: a real −0.65 % deficit gives E[z] ≈ −6.4 at 8,000,000 shots
(≈ 99 % power at the 4.0 threshold; essentially zero probability of reading
"not replicated"). Under no effect, P(|z| ≥ 4.0) ≈ 6×10⁻⁵ and
P(inconclusive) ≈ 4.6 %.

## Secondary quantities (reported, not decided on)

Same statistic for MoonLab ST and Stim on the same seeds; for MoonLab MT, the
same statistic for round 0 and for rounds 2–7 pooled (specificity); the
per-seed sign pattern.

## Boundary

F2b tests one exploratory signal on one workload on one host. It cannot
promote or demote the F2 verdict, which stands on its own frozen rules. A
"replicated" outcome would be a new, small (sub-percent) MT-path finding to be
reported as such; a "not replicated" outcome retires the signal.
