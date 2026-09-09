#!/usr/bin/env python3
"""F2b follow-up: MoonLab MT round-1 detector total on fresh seeds.

Preregistered in CONTROLLED_COMPARISON_PREREG_F2B.md (read it first).  One
primary statistic: the total number of round-1 detector fires for MoonLab MT
over 8,000,000 fresh shots, against the exact expectation, with a model-free
standard error from the per-shot count variance.  ST and Stim run on the same
seeds as controls; other rounds are reported for specificity.
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import stim

sys.path.insert(0, str(Path(__file__).resolve().parent))
from controlled_sampler_comparison import (detector_labels, exact_detector_marginals,
                                           load_front, sha256)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--moonlab-src", required=True, type=Path)
    ap.add_argument("--lib-dir", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--shots", type=int, default=200000)
    ap.add_argument("--seeds", type=str, default=",".join(str(s) for s in range(101, 141)))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    seeds = [int(s) for s in args.seeds.split(",")]
    shots = args.shots

    front, front_path = load_front(args.moonlab_src, args.lib_dir)
    lib_path = next(args.lib_dir / nm for nm in ("libmoonlab_bsamp.dylib", "libquantumsim.dylib")
                    if (args.lib_dir / nm).exists())
    here = Path(__file__).resolve().parent
    provenance = {
        "moonlab_source_commit": subprocess.check_output(
            ["git", "-C", str(args.moonlab_src), "rev-parse", "HEAD"]).decode().strip(),
        "front_module_sha256": sha256(front_path),
        "library": str(lib_path), "library_sha256": sha256(lib_path),
        "script_sha256": sha256(Path(__file__).resolve()),
        "preregistration_sha256": sha256(here / "CONTROLLED_COMPARISON_PREREG_F2B.md"),
        "stim_version": stim.__version__, "numpy_version": np.__version__,
        "python": sys.version.split()[0], "platform": platform.platform(),
        "simd_backend": front.SIMD_BACKEND, "phys_cores": front.PHYS_CORES,
        "shots_per_seed": shots, "seeds": seeds, "n_shots_total": shots * len(seeds),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    n, ops, dets = front.build_surface_code_noisy(5, 8)
    labels = detector_labels(5, 8)
    assert len(dets) == len(labels) == 120
    circuit = front._to_stim_with_detectors(ops, dets)
    p_exact, n_err = exact_detector_marginals(circuit)
    rounds = np.array([L["round"] for L in labels])
    groups = {"round1": np.where(rounds == 1)[0], "round0": np.where(rounds == 0)[0],
              "rounds2to7": np.where(rounds >= 2)[0], "all": np.arange(120)}
    kmax = 120

    engines = ("ml_mt", "ml_st", "stim")
    # Accumulators: per engine, per group: total fires, sum of per-shot count^2, histogram.
    acc = {e: {g: {"T": 0, "S2": 0, "hist": np.zeros(len(idx) + 1, dtype=np.int64)}
               for g, idx in groups.items()} for e in engines}
    per_seed_counts = {e: [] for e in engines}
    per_seed_sign = {e: [] for e in engines}
    E_r1_per_shot = float(p_exact[groups["round1"]].sum())

    t0 = time.time()
    for seed in seeds:
        samples = {
            "ml_mt": front.moonlab_sample_detectors(n, ops, dets, shots, seed, 0),
            "ml_st": front.moonlab_sample_detectors(n, ops, dets, shots, seed, 1),
            "stim": front.stim_sample_detectors(circuit.compile_detector_sampler(seed=seed + 1), shots),
        }
        for e, smp in samples.items():
            per_seed_counts[e].append(smp.sum(axis=1).astype(np.int64))
            for g, idx in groups.items():
                k = smp[idx].sum(axis=0).astype(np.int64)          # per-shot count
                a = acc[e][g]
                a["T"] += int(k.sum()); a["S2"] += int((k.astype(np.int64) ** 2).sum())
                a["hist"] += np.bincount(k, minlength=len(idx) + 1)[: len(idx) + 1]
            k1 = samples[e][groups["round1"]].sum()
            per_seed_sign[e].append(int(np.sign(k1 - shots * E_r1_per_shot)))
    N = shots * len(seeds)

    def stat(e, g):
        a = acc[e][g]; idx = groups[g]
        E = N * float(p_exact[idx].sum())
        mean = a["T"] / N
        var = a["S2"] / N - mean ** 2                      # per-shot variance (model-free)
        se = float(np.sqrt(N * var))
        z = (a["T"] - E) / se
        return {"observed": int(a["T"]), "expected": E, "relative_diff": (a["T"] - E) / E,
                "per_shot_var": var, "se": se, "z": float(z), "n_detectors": int(len(idx))}

    primary = stat("ml_mt", "round1")
    z = primary["z"]
    verdict = ("replicated" if abs(z) >= 4.0 else
               "not replicated" if abs(z) <= 2.0 else "inconclusive")
    results = {
        "provenance": provenance | {"finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    "wall_seconds": round(time.time() - t0, 1),
                                    "dem_error_mechanisms": n_err},
        "primary": {"engine": "ml_mt", "group": "round1", **primary,
                    "rule": "|z|>=4.0 replicated; |z|<=2.0 not replicated; else inconclusive",
                    "verdict": verdict,
                    "per_seed_sign_ml_mt_round1": per_seed_sign["ml_mt"],
                    "n_seeds_negative": int(sum(s < 0 for s in per_seed_sign["ml_mt"]))},
        "secondary": {e: {g: stat(e, g) for g in groups} for e in engines},
        "per_seed_sign": per_seed_sign,
    }
    for e in engines:
        np.savetxt(args.out / f"counts_full_{e}.tsv", np.stack(per_seed_counts[e]), fmt="%d", delimiter="\t")
        for g in groups:
            np.savetxt(args.out / f"hist_{e}_{g}.tsv", acc[e][g]["hist"], fmt="%d")
    np.savetxt(args.out / "exact_full.tsv", p_exact, fmt="%.12g")
    (args.out / "circuit_full.stim").write_text(str(circuit))
    (args.out / "detector_labels.json").write_text(json.dumps(labels))
    (args.out / "results.json").write_text(json.dumps(results, indent=2))
    print(f"F2b primary: ml_mt round1 T={primary['observed']} E={primary['expected']:.1f} "
          f"rel={primary['relative_diff']*100:+.3f}% z={z:+.2f} -> {verdict}")
    for e in engines:
        print("  ", e, {g: round(results['secondary'][e][g]['z'], 2) for g in groups})


if __name__ == "__main__":
    main()
