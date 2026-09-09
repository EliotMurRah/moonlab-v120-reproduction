# F2 controlled comparison — result (MoonLab v1.2.0, issue #21)

- Date: 2026-09-08 (run r1), 2026-09-09 (review, run r2, follow-up F2b)
- Author of harness, runs, and this report: Claude, for Eliot (EliotMurRah)
- Status: **CANDIDATE — UNREFEREED.** No independent referee was available.
  An internal fresh-context adversarial review was run before publication;
  its findings and their dispositions are in section 9. The maintainer's
  independent rerun is the intended referee.
- Preregistration: `CONTROLLED_COMPARISON_PREREG.md`, committed before any
  data (commit `e93cb8d`, 2026-09-08 19:42:00Z; first run began 19:42:40Z).
  Decision rules R1–R3 applied as frozen and evaluated in code
  (`results.json → decision_rules`). Follow-up F2b preregistered separately
  (`CONTROLLED_COMPARISON_PREREG_F2B.md`, commit `f9ec81a`, before its data).
- Harness: `controlled_sampler_comparison.py`. Revision r2 differs from r1
  only in provenance and bookkeeping (saves the Stim null-partner counts,
  records digests, checks MT as well as ST reseed determinism, evaluates the
  frozen rules in code); sampling and statistics are unchanged. r2 reproduced
  every raw count, exact vector, and translated circuit of r1 byte for byte.
- Artifacts: `artifacts_f2_controlled_r2/` (published; `results.json`,
  per-seed raw detector counts for MoonLab ST, MoonLab MT, Stim, and the Stim
  null partner on every workload, exact reference vectors, translated Stim
  circuits, detector labels) and `artifacts_f2b_mt_round1/` (follow-up).
  Every number below is recomputable from those files. Wall time: ~18 s (F2)
  and ~12 s (F2b).

## 1. What was held fixed (the maintainer's four conditions)

| Condition | Value |
|---|---|
| Workload | vendor `build_surface_code_noisy(5, 8, ...)`, imported from the v1.2.0 front module, unmodified |
| Translation | vendor `_to_stim_with_detectors`, unmodified |
| Sampling path | vendor `moonlab_sample_detectors` (nthreads=1 "ST", nthreads=0 "MT") and vendor `stim_sample_detectors` on `compile_detector_sampler(seed=seed+1)`, exactly as the shipped gate |
| Seeds / shots | shipped gate seed 1234, then 1–9; 200,000 shots per seed per engine (the gate's count); Stim null partner at seed+100001 |
| Source | tag v1.2.0, commit `4bf83a6c47e7f1c53db14fcb2a61053499fd82df` |
| Library | `libquantumsim.dylib` built on this host with `cmake -DCMAKE_BUILD_TYPE=Release`, sha256 `c762299bc5245dea12e5b67facaf8827d4f311d7d33059e982cea813f463e72e` |
| Environment | stim 1.16.0, numpy 2.5.1, Python 3.12.11, macOS arm64, Apple M2 Pro (12 physical cores), SIMD backend neon / 2 lanes |

The July observation used the pip-wheel binary (sha256 `677c8460…`); this
study used a fresh source build. Both give the same reading (section 3).

## 2. The reference

Exact per-detector fire probability from Stim's detector error model of the
circuit the vendor translation produces:
`P(D) = (1 − ∏_{i : D ∈ err_i} (1 − 2 p_i)) / 2`, exact for independent
error mechanisms. Validity check (prereg: 4,000,000-shot Stim sample, seed
777; pass if max|z| < 4.5 and Σz²/120 ∈ [0.75, 1.25]):

| Workload | DEM mechanisms | max\|z\| (4M Stim vs exact) | Σz²/120 | Check |
|---|---|---|---|---|
| full_p2_p1_pm | 1943 | 3.27 | 0.981 | pass |
| only_p2_depolarize2 | 1943 | 2.40 | 0.945 | pass |
| only_p1_depolarize1 | 372 | 2.66 | 0.862 | pass |
| only_pm_measure_flip | 128 | 2.89 | 1.153 | pass |

The DEM contains only `error` instructions (no `repeat`, `shift_detectors`,
separators, or observables; the circuit has no REPEAT blocks), 120 detectors.
The reviewer recomputed the marginals independently and matched the stored
vectors to ≤ 4×10⁻¹⁴, and verified the detector-label order against the
vendor `dets` list with 0/120 mismatches.

What the reference is: Stim's semantics of the vendor op list. "Stim vs
exact" is therefore a self-consistency control, and the study reads "MoonLab
agrees with Stim's semantics of the vendor-translated circuit", which is the
comparison the maintainer asked for.

## 3. The July reading reproduces exactly

Seed 1234, shipped statistic, full workload: **ST 6.01, MT 3.59**; fire
rates ml 0.01350 vs stim 0.01347. Identical to
`artifacts_phase3_sampling_stability.log` (July, wheel binary). MoonLab's
detector output is bit-identical on re-sampling with the same seed on every
workload, for both the ST and the MT path.

## 4. Decision rules as frozen → values → outcomes

| Rule | Threshold | Value | Outcome |
|---|---|---|---|
| Exact check | max\|z\| < 4.5 and Σz²/120 ∈ [0.75, 1.25], each workload | 3.27/0.981; 2.40/0.945; 2.66/0.862; 2.89/1.153 | pass ×4 |
| R1 (engine deviates) | pooled max\|z\| ≥ 5.0 or Σz²/120 ≥ 1.5 | largest across 12 engine×workload cells: max\|z\| 3.90, Σz²/120 1.220 | **does not fire, any engine, any workload** |
| R2 (gate miscalibrated) | ≥ 3 of 10 Stim-vs-Stim shipped readings ≥ 4.0 | 4, 5, 6, 5 of 10 (max 5.44) | **fires on all four workloads** |
| R3 (localisation) | only if R1 fires on the full workload | — | not applicable |

## 5. Q1/Q2 — engines versus the exact reference

Pooled over 10 seeds = 2,000,000 shots per engine; z per detector against the
exact marginal; 120 detectors.

| Workload | Engine | fire rate (pooled) | exact | max\|z\| | #\|z\|>4 | Σz²/120 |
|---|---|---|---|---|---|---|
| full | MoonLab ST | 0.013435 | 0.013437 | 3.24 | 0 | 0.800 |
| full | MoonLab MT | 0.013422 | 0.013437 | 3.90 | 0 | 1.091 |
| full | Stim | 0.013416 | 0.013437 | 2.87 | 0 | 1.209 |
| only_p2 | MoonLab ST | 0.008945 | 0.008937 | 2.28 | 0 | 0.863 |
| only_p2 | MoonLab MT | 0.008922 | 0.008937 | 3.55 | 0 | 1.097 |
| only_p2 | Stim | 0.008920 | 0.008937 | 2.58 | 0 | 1.029 |
| only_p1 | MoonLab ST | 0.002664 | 0.002661 | 2.63 | 0 | 1.168 |
| only_p1 | MoonLab MT | 0.002667 | 0.002661 | 2.45 | 0 | 0.866 |
| only_p1 | Stim | 0.002661 | 0.002661 | 2.32 | 0 | 0.866 |
| only_pm | MoonLab ST | 0.001937 | 0.001931 | 3.10 | 0 | 1.123 |
| only_pm | MoonLab MT | 0.001933 | 0.001931 | 2.63 | 0 | 1.220 |
| only_pm | Stim | 0.001928 | 0.001931 | 2.17 | 0 | 1.013 |

Per-seed (unpooled) Σz²/dof over all 4800 seed×detector cells: MoonLab ST
0.987, MoonLab MT 1.035, Stim 1.010 — no variance inflation in either MoonLab
path. Aggregate fire-rate differences carry a correlation-corrected SE
(per-shot total variance/mean ≈ 2.49) and read −0.14σ (ST), −1.25σ (MT),
−1.77σ (Stim); as the preregistration says, fire rate decides nothing. The
`by_kind` / `by_round` mean-z fields in `results.json` carry no standard error
and the detectors are positively correlated (max r 0.245); they are
descriptive only.

## 6. Q3 — the shipped gate against itself, and its exceedance profile

The shipped statistic is `max_D |p_ml(D) − p_stim(D)| / sqrt(p_stim(1−p_stim)/shots)`.
Two calibration defects: (a) the comparison is between two independent
samples but the denominator carries the variance of one, inflating the
statistic by √2 relative to a two-sample z; (b) the maximum over 120
detectors is compared to a single-test threshold. For a correct sampler, the
expected maximum of 120 |z| values is 2.81, and on the shipped scale
P(≥ 4.0) ≈ 43 %, P(≥ 5.0) ≈ 4.8 %, P(≥ 6.0) ≈ 0.26–0.28 % per comparison
(independent-Gaussian and measured-correlation nulls, respectively; the
reviewer's measured mean off-diagonal detector correlation is 0.012).

Exceedance profile of the shipped statistic over this study — 80
MoonLab-vs-Stim evaluations (10 seeds × ST/MT × 4 workloads) against 40
Stim-vs-Stim null evaluations (same seeds, same circuits, same shots):

| threshold | MoonLab-vs-Stim (n=80) | Stim-vs-Stim (n=40) | Gaussian null |
|---|---|---|---|
| ≥ 3.5 | 62 (77.5 %) | 34 (85.0 %) | 80.0 % |
| ≥ 4.0 | 42 (52.5 %) | 20 (50.0 %) | 43.0 % |
| ≥ 4.5 | 16 (20.0 %) | 8 (20.0 %) | 16.1 % |
| ≥ 5.0 | 7 (8.8 %) | 4 (10.0 %) | 4.8 % |
| ≥ 5.5 | 3 (3.8 %) | 0 | 1.2 % |
| ≥ 6.0 | 1 (1.2 %) | 0 | 0.26 % |

Means: 4.07 (MoonLab-vs-Stim) vs 4.09 (null). Through 5.0 the two profiles
are indistinguishable. In the extreme tail, three MoonLab-vs-Stim readings
(6.01, 5.98, 5.84; full/1234/ST, only_pm/2/ST, full/2/MT) sit where roughly
one was expected (ST and MT share each seed's Stim sample, so these are not
independent trials). Each decomposes into a MoonLab fluctuation of
+2.8…+3.6σ against exact — ordinary max-of-120 territory for a single seed —
coincident with a Stim fluctuation of −2.1…−2.7σ at the same detector, and
MoonLab pooled over the other nine seeds at those three detectors reads
−0.10, +0.33, +0.83σ. Under a two-sample denominator the seed-1234 comparison
reads 4.14 (ST) and 2.50 (MT), and the ten null pairs read 2.34–3.75 (mean
2.82; theoretical 2.81 for 120 i.i.d. detectors). R2 has ≈ 87 % power against
the √2 miscalibration and a ≈ 5×10⁻⁵ false-fire rate if the gate were
calibrated.

The measurement-level gate (`check_correctness`) and the parity test share the
same one-sample denominator; they were not the failing rows and were not
re-examined here.

## 7. Anatomy of the 6.01

The seed-1234 ST maximum sits on detector 93 (round 6, Z plaquette (2,2)),
exact p = 0.016144.

| Sample | p̂ | z vs exact |
|---|---|---|
| MoonLab ST, seed 1234 | 0.017040 | +3.18 |
| Stim, seed 1235 | 0.015385 | −2.69 |
| MoonLab ST, pooled 10 seeds | 0.016225 | +0.91 |
| MoonLab ST, the other nine seeds (1.8M shots) | — | −0.10 |
| Stim, pooled 10 seeds | 0.015971 | −1.94 |

MoonLab per-seed z on that detector: +3.18, +0.80, +0.18, −0.58, +0.34,
−1.22, −0.35, −1.40, +0.57, +1.35. On seed 1234 MoonLab's own whole-sample
picture against exact is unremarkable (max|z| 3.18 — P(max of 120 ≥ 3.18) ≈
16 % — and Σz²/120 = 1.10). Two opposite-sign fluctuations met on one detector
of 120; the one-sample denominator turned their gap into 6.01. The MT 3.59 is
the same shape on detector 58 (round 4, Z (1,1)): MT +3.25 vs exact on that
seed, Stim −0.33, MT pooled +1.00.

Bound on a persistent offset at detector 93 from the nine seeds that did not
produce the reading: |offset| ≤ 0.69 σ_200k at 95 %, i.e. at most ≈ 11 % of the
6.01 reading. The reading was, under the null, roughly a 1-in-360 draw per
evaluation; it became "deterministic" because the front replays a fixed
internal seed.

## 8. Exploratory signal and its preregistered follow-up (F2b)

The internal review flagged one thing R1 does not test: on the full workload,
MoonLab MT, the 16 round-1 detectors summed to 443,231 fires over 2M shots vs
446,137 expected (−0.65 %), negative in 8 of 10 seeds, correlation-corrected
z ≈ −3.17 (≈ 3.6 % family-wise over the reviewer's 24 engine×round looks);
absent in the three isolations. Rather than leave it, F2b was preregistered
(`CONTROLLED_COMPARISON_PREREG_F2B.md`: one statistic, fresh seeds 101–140,
8,000,000 shots, model-free SE from the per-shot count variance; |z| ≥ 4.0
replicated, |z| ≤ 2.0 not replicated, between inconclusive; power ≈ 99 %
against a real −0.65 %).

| | observed | expected | relative | z | verdict |
|---|---|---|---|---|---|
| MoonLab MT, round-1 total, 8M fresh shots | 1,782,012 | 1,784,547 | −0.142 % | **−1.39** | **not replicated** |

A real −0.65 % deficit would have read z ≈ −6.35. Negative in 25 of 40 seeds.
Controls on the same seeds (secondary, not decided on): MoonLab ST round-1
+1.25, Stim round-1 +0.67; MoonLab MT round-0 +2.44, rounds 2–7 +0.37, all
+0.21 (one of twelve secondary looks at |z| 2.4 is unremarkable). The signal
is retired.

## 9. Internal review (fresh-context adversarial; not an independent referee)

Run on the harness, both preregistrations, the vendor front, and the r1
results before publication. **No MAJOR findings.** Verified: no leakage of
the reference into sampling; exact formula and DEM parsing; detector order;
`vendor_gate_marg_sigma` identical to the vendor `check_detector_correctness`
(same floors); seed rule; 6.0136/3.5943 reproduced; no RNG-stream overlap
across seeds or between ST and MT (so pooling is valid); MT reseed
determinism; two-sample formula calibrated; every number in `results.json`
recomputed from the TSVs. MINOR findings and dispositions:

- **M1** — "would appear as ≈ 19σ" overstated the bound and the write-up
  understated how rare the reading was under the null. **Accepted:** replaced
  by the other-nine-seed bound (≤ 0.69 σ_200k, ≈ 11 % of 6.01), the ≈ 1-in-360
  statement, the full exceedance profile, and the per-seed Σz²/dof (section
  6–7).
- **M2** — unreported exploratory MT round-1 deficit. **Accepted:**
  preregistered follow-up F2b run on fresh data; not replicated (section 8).
- **M3** — sensitivity quoted at 50 % power. **Accepted:** restated with 97.5
  % power and the χ² branch (section 10).
- **M4** — Stim null-partner counts not saved; no prereg digest recorded.
  **Accepted:** harness r2 saves them and records digests; r2 rerun
  reproduced r1 byte for byte.
- **M5** — decision rules applied by hand. **Accepted:** evaluated in code
  (`decision_rules` in `results.json`) and tabulated (section 4).
- **NOTE** — the reference is Stim's semantics of the vendor op list.
  **Accepted:** stated in section 2.

## 10. Verdict, with its boundary

**F2 is a calibration defect of the shipped correctness gate, not a
discrepancy between MoonLab's detector sampler and the Stim reference.** On
this host, this workload family, and this build, MoonLab's ST and MT
detector-sampling paths are statistically indistinguishable from the exact
marginals implied by the circuit the vendor translation hands to Stim, to the
sensitivity of 2,000,000 shots per engine; the shipped statistic's exceedance
profile with MoonLab on one side matches its profile with a second Stim run on
one side; and the one exploratory signal the data offered was retired on
8,000,000 fresh shots. The "deterministic" failure was a fixed internal seed
replaying one ≈ 1-in-360 draw. With fresh seeds the same gate would fail a
correct sampler in roughly 0.5 % of runs on the detector stage alone.

What this does not show. Sensitivity for a persistent offset on a single
detector at 2M shots: ≈ 4.1×10⁻⁴ absolute (3.0 % relative at p ≈ 0.0135) is
detected with 50 % power at 5σ, ≈ 5.7×10⁻⁴ (4.2 %) with 97.5 % power; a bias
confined to a fraction f of shots (e.g. one thread block) is diluted by f. A
uniform relative bias of ≈ 0.43 % across all 120 detectors would fire the χ²
branch in expectation; smaller uniform biases are not excluded. Nothing here
concerns throughput, other workloads, other hosts, the measurement-level
gate's own calibration beyond the shared denominator, or the v1.2.1 candidate.
The speed result's certification remains the maintainer's decision and
requires his own rerun; this study supplies the correctness evidence he asked
for and a harness that reruns in under a minute.

Suggested gate repair (not implemented here; maintainer's call): compare each
engine to the exact DEM marginals instead of to a second sample; use a
two-sample denominator wherever two samples are compared; gate on a
family-wise quantity (Σz² over detectors against its χ² reference, or a
Bonferroni-adjusted maximum) with seeds pooled or drawn fresh.
