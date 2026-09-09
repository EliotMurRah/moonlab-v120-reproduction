#!/usr/bin/env python3
"""Controlled comparison for MoonLab issue #21 finding F2.

The maintainer asked for: "a controlled comparison of the same workload, seed,
translation, and sampling path against the reference".  This harness holds all
four fixed and adds the one thing the shipped gate lacks -- an exact,
sampling-noise-free reference marginal per detector, computed from Stim's
detector error model of the very circuit the vendor translation produces.

Design (frozen before data; see CONTROLLED_COMPARISON_PREREG.md):

  * Workload:    the vendor builder `build_surface_code_noisy(5, 8, ...)`,
                 imported from the v1.2.0 front module -- not re-implemented.
  * Translation: the vendor `_to_stim_with_detectors` -- not re-implemented.
  * Sampling:    the vendor `moonlab_sample_detectors` (ST nthreads=1 and MT
                 nthreads=0) and the vendor `stim_sample_detectors` on
                 `compile_detector_sampler(seed=seed+1)`, exactly as the gate.
  * Seeds:       the vendor gate seed (1234) first, then further fixed seeds.
  * Reference:   exact per-detector fire probability from the DEM:
                     P(D fires) = (1 - prod_{i : D in err_i} (1 - 2 p_i)) / 2
                 which is exact for independent error mechanisms (XOR of
                 independent Bernoullis).  Cross-checked against a large
                 Stim sample.

Three questions, each answered per detector and per noise channel:

  Q1  Does MoonLab's sampled marginal match the exact reference?   (engine)
  Q2  Does Stim's sampled marginal match the exact reference?      (control)
  Q3  What does the shipped gate statistic read when both sides are Stim
      with different seeds?                                        (gate null)

Everything is written as raw counts (including the Stim null partner) so any
number here is recomputable.

Revision r2 (2026-09-09, after internal review; sampling and statistics are
byte-identical to r1): also saves the Stim null partner counts, records the
preregistration and harness digests, checks MT reseed determinism as well as
ST, and evaluates the frozen decision rules in code.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import stim


# ----------------------------------------------------------------------------
# Vendor front import (by path, unmodified).
# ----------------------------------------------------------------------------
def load_front(moonlab_src: Path, lib_dir: Path):
    os.environ["MOONLAB_LIB_DIR"] = str(lib_dir)
    p = moonlab_src / "benchmarks" / "dominance" / "fronts" / "f3_batch_sampling_vs_stim.py"
    spec = importlib.util.spec_from_file_location("f3_batch_sampling_vs_stim", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, p


# ----------------------------------------------------------------------------
# Detector labels: re-walk the vendor builder's emission order.
# ----------------------------------------------------------------------------
def detector_labels(d: int, rounds: int):
    cells = [(i, j) for i in range(d - 1) for j in range(d - 1)]
    z_cells = [(i, j) for (i, j) in cells if (i + j) % 2 == 0]
    x_cells = [(i, j) for (i, j) in cells if (i + j) % 2 == 1]
    labels = []
    for r in range(rounds):
        for c in z_cells:
            labels.append({"round": r, "type": "Z", "cell": list(c),
                           "kind": "first_round_single" if r == 0 else "pair"})
        for c in x_cells:
            if r > 0:
                labels.append({"round": r, "type": "X", "cell": list(c), "kind": "pair"})
    return labels


# ----------------------------------------------------------------------------
# Exact reference marginals from the DEM.
# ----------------------------------------------------------------------------
def exact_detector_marginals(circuit: stim.Circuit) -> np.ndarray:
    dem = circuit.detector_error_model(decompose_errors=False, flatten_loops=True)
    ndet = circuit.num_detectors
    prod = np.ones(ndet, dtype=np.float64)
    n_err = 0
    for inst in dem:
        if inst.type != "error":
            continue
        p = inst.args_copy()[0]
        n_err += 1
        seen = set()
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                seen.add(t.val)
        for dv in seen:
            prod[dv] *= (1.0 - 2.0 * p)
    return (1.0 - prod) / 2.0, n_err


# ----------------------------------------------------------------------------
# Statistics.
# ----------------------------------------------------------------------------
def z_vs_exact(counts: np.ndarray, shots: int, p_exact: np.ndarray) -> np.ndarray:
    phat = counts / shots
    se = np.sqrt(np.maximum(p_exact * (1 - p_exact), 1e-12) / shots)
    return (phat - p_exact) / se


def vendor_gate_marg_sigma(p_a: np.ndarray, p_b: np.ndarray, shots: int) -> float:
    """The shipped statistic: |p_a - p_b| / sqrt(p_b(1-p_b)/shots), max over detectors.
    (b is the 'stim' side; only ITS variance is used.)"""
    se = np.sqrt(np.maximum(p_b * (1 - p_b), 1e-9) / shots) + 1e-12
    return float(np.abs(p_a - p_b).__truediv__(se).max())


def two_sample_marg_sigma(p_a: np.ndarray, p_b: np.ndarray, shots: int) -> float:
    """Same comparison with the variance of a difference of two independent samples."""
    pbar = (p_a + p_b) / 2
    se = np.sqrt(np.maximum(2 * pbar * (1 - pbar), 1e-9) / shots) + 1e-12
    return float(np.abs(p_a - p_b).__truediv__(se).max())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------------
# Frozen decision rules (CONTROLLED_COMPARISON_PREREG.md), evaluated in code.
# ----------------------------------------------------------------------------
def evaluate_rules(results: dict) -> dict:
    out = {"thresholds": {"exact_check": "max|z| < 4.5 and 0.75 <= chi2/dof <= 1.25",
                          "R1": "max|z| >= 5.0 or chi2/dof >= 1.5 (pooled, per engine)",
                          "R2": ">= 3 of 10 Stim-vs-Stim shipped-statistic readings >= 4.0",
                          "R3": "only if R1 fires on the full workload"},
           "per_workload": {}}
    r1_full = {}
    for w, W in results["workloads"].items():
        ec = W["exact_check"]
        ec_ok = (ec["max_abs_z_stim_big_vs_exact"] < 4.5
                 and 0.75 <= ec["chi2_sum_z2"] / ec["dof"] <= 1.25)
        r1 = {}
        for eng, P in W["pooled_vs_exact"].items():
            r1[eng] = {"max_abs_z": P["max_abs_z"], "chi2_over_dof": P["chi2_sum_z2"] / P["dof"],
                       "fires": bool(P["max_abs_z"] >= 5.0 or P["chi2_sum_z2"] / P["dof"] >= 1.5)}
        nulls = [s["vendor_gate_marg_sigma"]["stim_vs_stim_null"] for s in W["per_seed"]]
        r2 = {"null_readings": nulls, "n_ge_4": int(sum(v >= 4.0 for v in nulls)),
              "max": max(nulls), "fires": bool(sum(v >= 4.0 for v in nulls) >= 3)}
        out["per_workload"][w] = {"exact_check_pass": bool(ec_ok), "R1": r1, "R2": r2}
        if w.startswith("full"):
            r1_full = {e: v["fires"] for e, v in r1.items()}
    fired = [e for e, f in r1_full.items() if f]
    if not fired:
        out["R3"] = "not applicable: R1 did not fire on the full workload for any engine"
    else:
        loc = {}
        for e in fired:
            loc[e] = [w for w, W in out["per_workload"].items()
                      if not w.startswith("full") and W["R1"][e]["fires"]]
        out["R3"] = loc
    return out


# ----------------------------------------------------------------------------
# Main.
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--moonlab-src", required=True, type=Path)
    ap.add_argument("--lib-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--shots", type=int, default=200000)
    ap.add_argument("--seeds", type=str, default="1234,1,2,3,4,5,6,7,8,9")
    ap.add_argument("--exact-check-shots", type=int, default=4000000)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=False)
    seeds = [int(s) for s in args.seeds.split(",")]
    shots = args.shots

    front, front_path = load_front(args.moonlab_src, args.lib_dir)
    lib_path = None
    for nm in ("libmoonlab_bsamp.dylib", "libquantumsim.dylib"):
        if (args.lib_dir / nm).exists():
            lib_path = args.lib_dir / nm
            break

    src_head = subprocess.check_output(["git", "-C", str(args.moonlab_src), "rev-parse", "HEAD"]).decode().strip()
    provenance = {
        "moonlab_source_commit": src_head,
        "front_module": str(front_path.relative_to(args.moonlab_src)),
        "front_module_sha256": sha256(front_path),
        "library": str(lib_path),
        "library_sha256": sha256(lib_path) if lib_path else None,
        "simd_backend": front.SIMD_BACKEND, "simd_lanes": front.SIMD_LANES,
        "phys_cores": front.PHYS_CORES,
        "stim_version": stim.__version__, "numpy_version": np.__version__,
        "python": sys.version.split()[0], "platform": platform.platform(),
        "machine": platform.machine(),
        "shots_per_seed": shots, "seeds": seeds,
        "stim_seed_rule": "seed + 1 (as in the vendor gate)",
        "exact_check_shots": args.exact_check_shots,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "harness_revision": "r2",
        "harness_sha256": sha256(Path(__file__).resolve()),
        "preregistration_sha256": sha256(Path(__file__).resolve().parent / "CONTROLLED_COMPARISON_PREREG.md"),
    }

    # Workloads: the full vendor noise model and three single-channel isolations.
    P = 0.001
    workloads = [
        ("full_p2_p1_pm", dict(p2=P, p1=P, pm=P)),
        ("only_p2_depolarize2", dict(p2=P, p1=0.0, pm=0.0)),
        ("only_p1_depolarize1", dict(p2=0.0, p1=P, pm=0.0)),
        ("only_pm_measure_flip", dict(p2=0.0, p1=0.0, pm=P)),
    ]
    labels = detector_labels(5, 8)

    results = {"provenance": provenance, "workloads": {}}
    for wname, kw in workloads:
        t0 = time.time()
        n, ops, dets = front.build_surface_code_noisy(5, 8, **kw)
        assert len(dets) == len(labels), (len(dets), len(labels))
        circuit = front._to_stim_with_detectors(ops, dets)
        ndet = len(dets)
        p_exact, n_err = exact_detector_marginals(circuit)

        # Exact-formula cross-check with a large independent Stim sample.
        big = circuit.compile_detector_sampler(seed=777).sample(args.exact_check_shots)
        big_counts = big.sum(axis=0).astype(np.int64)
        z_big = z_vs_exact(big_counts, args.exact_check_shots, p_exact)

        per_seed = []
        counts = {"ml_st": [], "ml_mt": [], "stim": [], "stim_null": []}
        determinism = []
        determinism_mt = []
        for seed in seeds:
            ml_st = front.moonlab_sample_detectors(n, ops, dets, shots, seed, 1)
            ml_st2 = front.moonlab_sample_detectors(n, ops, dets, shots, seed, 1)
            determinism.append(bool(np.array_equal(ml_st, ml_st2)))
            ml_mt = front.moonlab_sample_detectors(n, ops, dets, shots, seed, 0)
            ml_mt2 = front.moonlab_sample_detectors(n, ops, dets, shots, seed, 0)
            determinism_mt.append(bool(np.array_equal(ml_mt, ml_mt2)))
            st = front.stim_sample_detectors(
                circuit.compile_detector_sampler(seed=seed + 1), shots)
            c_st, c_mt, c_s = (ml_st.sum(axis=1).astype(np.int64),
                               ml_mt.sum(axis=1).astype(np.int64),
                               st.sum(axis=1).astype(np.int64))
            counts["ml_st"].append(c_st); counts["ml_mt"].append(c_mt); counts["stim"].append(c_s)
            p_st, p_mt, p_s = c_st / shots, c_mt / shots, c_s / shots
            # Gate null: Stim vs Stim with a different seed, same statistic.
            st_b = front.stim_sample_detectors(
                circuit.compile_detector_sampler(seed=seed + 100001), shots)
            c_sb = st_b.sum(axis=1).astype(np.int64)
            counts["stim_null"].append(c_sb)
            p_sb = c_sb / shots
            per_seed.append({
                "seed": seed,
                "vendor_gate_marg_sigma": {
                    "ml_st_vs_stim": vendor_gate_marg_sigma(p_st, p_s, shots),
                    "ml_mt_vs_stim": vendor_gate_marg_sigma(p_mt, p_s, shots),
                    "stim_vs_stim_null": vendor_gate_marg_sigma(p_sb, p_s, shots),
                },
                "two_sample_marg_sigma": {
                    "ml_st_vs_stim": two_sample_marg_sigma(p_st, p_s, shots),
                    "ml_mt_vs_stim": two_sample_marg_sigma(p_mt, p_s, shots),
                    "stim_vs_stim_null": two_sample_marg_sigma(p_sb, p_s, shots),
                },
                "max_abs_z_vs_exact": {
                    "ml_st": float(np.abs(z_vs_exact(c_st, shots, p_exact)).max()),
                    "ml_mt": float(np.abs(z_vs_exact(c_mt, shots, p_exact)).max()),
                    "stim": float(np.abs(z_vs_exact(c_s, shots, p_exact)).max()),
                },
                "fire_rate": {"ml_st": float(p_st.mean()), "ml_mt": float(p_mt.mean()),
                              "stim": float(p_s.mean()), "exact": float(p_exact.mean())},
            })

        # Pooled over seeds against the exact reference.
        pooled = {}
        N = shots * len(seeds)
        for eng in ("ml_st", "ml_mt", "stim"):
            tot = np.sum(np.stack(counts[eng]), axis=0)
            z = z_vs_exact(tot, N, p_exact)
            chi2 = float(np.sum(z ** 2))
            worst = np.argsort(-np.abs(z))[:8]
            pooled[eng] = {
                "N": N,
                "fire_rate": float(tot.sum() / (N * ndet)),
                "fire_rate_exact": float(p_exact.mean()),
                "max_abs_z": float(np.abs(z).max()),
                "n_detectors_abs_z_gt_4": int((np.abs(z) > 4).sum()),
                "n_detectors_abs_z_gt_3": int((np.abs(z) > 3).sum()),
                "chi2_sum_z2": chi2, "dof": ndet,
                "by_kind": {},
                "worst_detectors": [
                    {"detector": int(i), **labels[i], "p_exact": float(p_exact[i]),
                     "p_hat": float(tot[i] / N), "z": float(z[i])} for i in worst],
            }
            for kind in ("first_round_single", "pair"):
                for typ in ("Z", "X"):
                    idx = [i for i, L in enumerate(labels) if L["kind"] == kind and L["type"] == typ]
                    if not idx:
                        continue
                    zz = z[idx]
                    pooled[eng]["by_kind"][f"{typ}:{kind}"] = {
                        "n": len(idx), "mean_z": float(zz.mean()),
                        "max_abs_z": float(np.abs(zz).max()),
                        "mean_p_exact": float(p_exact[idx].mean()),
                        "mean_p_hat": float(tot[idx].sum() / (N * len(idx))),
                    }
            # Also by round, to see whether a boundary round is special.
            by_round = {}
            for r in range(8):
                idx = [i for i, L in enumerate(labels) if L["round"] == r]
                by_round[r] = {"mean_z": float(z[idx].mean()),
                               "max_abs_z": float(np.abs(z[idx]).max())}
            pooled[eng]["by_round"] = by_round

        results["workloads"][wname] = {
            "noise": kw, "n_qubits": n, "n_ops": len(ops), "n_detectors": ndet,
            "dem_error_mechanisms": n_err,
            "exact_check": {"shots": args.exact_check_shots,
                            "max_abs_z_stim_big_vs_exact": float(np.abs(z_big).max()),
                            "chi2_sum_z2": float(np.sum(z_big ** 2)), "dof": ndet},
            "moonlab_st_bit_identical_on_reseed": all(determinism),
            "moonlab_mt_bit_identical_on_reseed": all(determinism_mt),
            "per_seed": per_seed,
            "pooled_vs_exact": pooled,
            "wall_seconds": round(time.time() - t0, 1),
        }
        # Raw counts, one row per seed, so anything above is recomputable.
        np.savetxt(args.out / f"counts_{wname}_ml_st.tsv", np.stack(counts["ml_st"]), fmt="%d", delimiter="\t")
        np.savetxt(args.out / f"counts_{wname}_ml_mt.tsv", np.stack(counts["ml_mt"]), fmt="%d", delimiter="\t")
        np.savetxt(args.out / f"counts_{wname}_stim.tsv", np.stack(counts["stim"]), fmt="%d", delimiter="\t")
        np.savetxt(args.out / f"counts_{wname}_stim_null.tsv", np.stack(counts["stim_null"]), fmt="%d", delimiter="\t")
        np.savetxt(args.out / f"exact_{wname}.tsv", p_exact, fmt="%.12g")
        (args.out / f"circuit_{wname}.stim").write_text(str(circuit))
        print(f"[{wname}] done in {results['workloads'][wname]['wall_seconds']}s; "
              f"pooled max|z| ml_st={pooled['ml_st']['max_abs_z']:.2f} "
              f"ml_mt={pooled['ml_mt']['max_abs_z']:.2f} stim={pooled['stim']['max_abs_z']:.2f}",
              flush=True)

    (args.out / "detector_labels.json").write_text(json.dumps(labels))
    results["decision_rules"] = evaluate_rules(results)
    results["provenance"]["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (args.out / "results.json").write_text(json.dumps(results, indent=2))
    print("wrote", args.out / "results.json")


if __name__ == "__main__":
    main()
