# MoonLab v1.2.0 Independent Reproduction Study — Preregistration

- Frozen at: `2026-07-31T14:43:18Z`
- Status at freeze: no MoonLab/Stim/PyMatching installation, benchmark run, or
  result exists in this study. This document is committed before any data.
- Host: macOS `26.5.2` (`25F84`), Apple M2 Pro, arm64, 16 GiB.
- Relationship to Eliot: **none at runtime.** This is an upstream reproduction
  study only. No process in this study receives Eliot's diary, state, config,
  or artifacts. Locked V0.x baselines remain untouched and are not re-hashed by
  this study (it never writes outside `upstream/moonlab_v120_reproduction/` and
  its declared artifact/dependency dirs).

## Question

Do MoonLab v1.2.0's two headline single-machine QEC claims reproduce on
independent hardware, measured by an independent party?

- **C1 (sampling speed):** "on batched shot sampling it exceeds Stim."
- **C2 (decoding accuracy):** "sub-threshold it matches PyMatching exactly.
  with correlated two-pass decoding ... 17-81% lower logical error rates across
  the tested surface-code configurations."

Optional stretch (cheap, self-contained; run only if C1/C2 complete):

- **C3 (braiding coherence):** F/R coherence residuals and braid-group checks
  reported at <= ~1e-15 are reproducible through the public API/test surface.

## Explicitly out of scope

Distributed/MPI and multi-GPU claims (no fleet available), Metal/CUDA GPU
paths, "hardware-verified" attestations, ML-KEM/crypto beyond an import smoke,
performance numbers other than C1, and any comparison we cannot make
apples-to-apples. Failure to test something is reported as "not tested," never
silently dropped.

## Fixed test subjects

- MoonLab: exactly `v1.2.0` — pip wheel `moonlab==1.2.0` for Python-surface
  runs, plus source at the `v1.2.0` git tag for the vendor benchmark harness.
  Peeled tag commit recorded at acquisition; wheel SHA-256 recorded.
- Stim and PyMatching: latest stable pip releases at install time, versions
  pinned and recorded at acquisition, then frozen for the study.
- All three installed in a dedicated venv under this directory. No system
  Python packages modified. Every installed artifact hashed.

## Phases

1. **Environment + provenance.** Create venv, install pinned packages, record
   versions/hashes/platform, smoke-test imports and one trivial functional call
   per package. No benchmark data.
2. **Vendor harness, unmodified.** Locate MoonLab's shipped Stim/PyMatching
   comparison benchmarks in the v1.2.0 source; build with the recorded profile
   if required; run them AS SHIPPED on this host; record complete stdout,
   configs, and timings. This tests "do his numbers reproduce on hardware he
   does not control," not our own experimental design.
3. **Independent harness.** A comparison written by us: same circuits, same
   noise, same shot budgets in both frameworks; correctness-gated; configs
   preregistered in an amendment BEFORE phase-3 data (they must be drawn from
   the vendor-tested configurations plus at least one config of our choosing).
   Author/referee separation: implementation authored by one agent (Codex
   proposed), independently reviewed by the other (Claude) before results are
   accepted.

## Reproduction criteria (frozen before any data)

- **C1 reproduced** if MoonLab's batched shot sampling throughput >= Stim's on
  a majority of matched configurations in phase 3 (and directionally in phase
  2). Magnitudes are reported; the claim under test is directional.
- **C2a reproduced** if sub-threshold logical error rates of MoonLab's
  union-find decoder match PyMatching within overlapping 95% binomial CIs on
  matched configs.
- **C2b reproduced** if correlated two-pass decoding shows LOWER logical error
  rates than PyMatching with non-overlapping 95% CIs on at least one
  vendor-tested config; the observed reduction is reported against the claimed
  17-81% range. Partial reproduction is reported as partial.
- Every benchmark is correctness-gated: decoder outputs validated, sampler
  outputs sanity-checked against expected distributions. A speed result on
  wrong answers is a FAIL, not a datapoint.

## Integrity rules

- Failures, crashes, and non-reproductions are results; they are preserved and
  reported, never rerun away or deleted.
- No threshold, config, or criterion changes after data exists without a
  committed amendment marked as such.
- Vendor code is never modified in phase 2; any patch required to build is a
  recorded deviation.
- Raw logs are the evidence; summaries are derived views.
- Outcome (confirm, partial, or discrepancy) is written up for tsotchke either
  way. Discrepancies get the same courtesy as the Eshkol report: reproducer
  first, adjectives never.

— Frozen by Claude (referee), on Marko's authorization, before any installation.
