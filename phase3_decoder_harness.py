#!/usr/bin/env python3
"""Phase 3 independent decoder comparison — authored by Claude (referee: Codex).

Tests MoonLab v1.2.0's flagship claim on freshly authored code: plain union-find
and correlated two-pass decoding vs PyMatching 2, same shots, same merged edge
model, statistics computed here. Shared surfaces (declared in PHASE3_AMENDMENT):
the public ctypes decoder ABI and the standard DEM->edge mathematics.

Frozen configs (PHASE3_AMENDMENT.md): A(d=3,p=0.008) B(d=5,p=0.008) C(d=7,p=0.006),
200000 shots each, rotated_memory_z, rounds=d, all four stim noise channels = p.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import secrets
import sys
import time
from pathlib import Path

import numpy as np
import pymatching
import stim

BOUNDARY = 0xFFFFFFFF
CONFIGS = [
    {"id": "A", "d": 3, "p": 0.008, "provenance": "vendor family"},
    {"id": "B", "d": 5, "p": 0.008, "provenance": "vendor family"},
    {"id": "C", "d": 7, "p": 0.006, "provenance": "our choice"},
]
SHOTS = 200_000
VOID_RATE = 0.45


def load_lib() -> ctypes.CDLL:
    lib_dir = os.environ.get("MOONLAB_LIB_DIR")
    if not lib_dir:
        raise SystemExit("set MOONLAB_LIB_DIR to the built moonlab library dir")
    lib = ctypes.CDLL(str(Path(lib_dir) / "libquantumsim.dylib"))
    lib.moonlab_uf_decoder_new.restype = ctypes.c_void_p
    lib.moonlab_uf_decoder_new.argtypes = [
        ctypes.c_size_t, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_size_t]
    lib.moonlab_uf_decoder_new_correlated.restype = ctypes.c_void_p
    lib.moonlab_uf_decoder_new_correlated.argtypes = [
        ctypes.c_size_t, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_double), ctypes.POINTER(ctypes.c_uint64),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
        ctypes.POINTER(ctypes.c_double), ctypes.c_size_t]
    lib.moonlab_uf_decode_batch.restype = ctypes.c_long
    lib.moonlab_uf_decode_batch.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.c_int, ctypes.POINTER(ctypes.c_uint8)]
    lib.moonlab_uf_decoder_free.restype = None
    lib.moonlab_uf_decoder_free.argtypes = [ctypes.c_void_p]
    return lib


def dem_to_model(dem: stim.DetectorErrorModel):
    """Own implementation of the standard DEM -> merged graphlike edge model.

    Components of a decomposed mechanism become edges (1-2 detectors, obs mask).
    Parallel edges merge with p = p1(1-p2) + p2(1-p1). Correlated pair strengths
    accumulate the same way across mechanisms. Hyper-components are counted and
    skipped (must be ~0 for decompose_errors=True on this family).
    """
    acc: dict[tuple[int, int, int], float] = {}
    corr: dict[tuple[tuple[int, int, int], tuple[int, int, int]], float] = {}
    hyper = 0

    def edge_key(dets: list[int], obs_mask: int):
        if len(dets) == 1:
            return (dets[0], BOUNDARY, obs_mask)
        a, b = sorted(dets)
        return (a, b, obs_mask)

    for inst in dem.flattened():
        if inst.type != "error":
            continue
        p = inst.args_copy()[0]
        comps: list[list] = [[]]
        for t in inst.targets_copy():
            if t.is_separator():
                comps.append([])
            else:
                comps[-1].append(t)
        keys = []
        for comp in comps:
            dets = [t.val for t in comp if t.is_relative_detector_id()]
            obs = 0
            for t in comp:
                if t.is_logical_observable_id():
                    obs |= 1 << t.val
            if not dets and obs == 0:
                continue
            if len(dets) > 2:
                hyper += 1
                continue
            if not dets:
                # observable-only component: undetectable, skip (counts as hyper-ish)
                hyper += 1
                continue
            k = edge_key(dets, obs)
            keys.append(k)
            q = acc.get(k, 0.0)
            acc[k] = p * (1 - q) + q * (1 - p)
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                pair = tuple(sorted((keys[i], keys[j])))
                q = corr.get(pair, 0.0)
                corr[pair] = p * (1 - q) + q * (1 - p)

    keys = sorted(acc)
    index = {k: i for i, k in enumerate(keys)}
    ea = np.array([k[0] for k in keys], dtype=np.uint32)
    eb = np.array([k[1] for k in keys], dtype=np.uint32)
    ew = np.array([math.log((1 - acc[k]) / acc[k]) for k in keys], dtype=np.float64)
    eo = np.array([k[2] for k in keys], dtype=np.uint64)
    ep = np.array([acc[k] for k in keys], dtype=np.float64)
    pairs = sorted(corr)
    ca = np.array([index[a] for a, _ in pairs], dtype=np.uint32)
    cb = np.array([index[b] for _, b in pairs], dtype=np.uint32)
    cq = np.array([corr[pr] for pr in pairs], dtype=np.float64)
    return ea, eb, ew, eo, ep, ca, cb, cq, hyper


def wilson_ci(k: int, n: int, z: float = 1.959964):
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    den = 1 + z * z / n
    center = (ph + z * z / (2 * n)) / den
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, center - half), min(1.0, center + half))


def mcnemar(bad_a: np.ndarray, bad_b: np.ndarray):
    """Continuity-corrected paired McNemar; positive z favours A (fewer errors)."""
    only_a = int((bad_a & ~bad_b).sum())
    only_b = int((bad_b & ~bad_a).sum())
    n = only_a + only_b
    if n == 0:
        return only_a, only_b, 0.0
    z = (abs(only_a - only_b) - 1) / math.sqrt(n)
    if only_a < only_b:
        return only_a, only_b, z
    if only_a > only_b:
        return only_a, only_b, -z
    return only_a, only_b, 0.0


def run_config(lib, cfg):
    seed = secrets.randbits(31)
    c = stim.Circuit.generated(
        "surface_code:rotated_memory_z",
        distance=cfg["d"], rounds=cfg["d"],
        after_clifford_depolarization=cfg["p"],
        before_round_data_depolarization=cfg["p"],
        before_measure_flip_probability=cfg["p"],
        after_reset_flip_probability=cfg["p"])
    dem = c.detector_error_model(decompose_errors=True)
    ea, eb, ew, eo, ep, ca, cb, cq, hyper = dem_to_model(dem)
    ndet, nobs = c.num_detectors, c.num_observables

    det, obs = c.compile_detector_sampler(seed=seed).sample(
        SHOTS, separate_observables=True)
    truth = obs[:, 0]

    pm = pymatching.Matching.from_detector_error_model(dem)
    t0 = time.perf_counter()
    pm_pred = pm.decode_batch(det)[:, 0].astype(bool)
    pm_t = time.perf_counter() - t0

    det_u8 = np.ascontiguousarray(det.astype(np.uint8).T)
    out = np.empty((nobs, SHOTS), dtype=np.uint8)

    def moon_decode(handle):
        t0 = time.perf_counter()
        rc = lib.moonlab_uf_decode_batch(
            handle,
            det_u8.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)),
            SHOTS, 0,
            out.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)))
        dt = time.perf_counter() - t0
        if rc != SHOTS:
            raise RuntimeError(f"moonlab_uf_decode_batch rc={rc}")
        return out[0].astype(bool).copy(), dt

    h = lib.moonlab_uf_decoder_new(
        ndet, nobs,
        ea.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        eb.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        ew.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        eo.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)),
        len(ea))
    if not h:
        raise RuntimeError("moonlab_uf_decoder_new failed")
    ml_pred, ml_t = moon_decode(h)
    lib.moonlab_uf_decoder_free(h)

    h = lib.moonlab_uf_decoder_new_correlated(
        ndet, nobs,
        ea.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        eb.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        ew.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        eo.ctypes.data_as(ctypes.POINTER(ctypes.c_uint64)),
        len(ea),
        ep.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ca.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        cb.ctypes.data_as(ctypes.POINTER(ctypes.c_uint32)),
        cq.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        len(ca))
    if not h:
        raise RuntimeError("moonlab_uf_decoder_new_correlated failed")
    mlc_pred, mlc_t = moon_decode(h)
    lib.moonlab_uf_decoder_free(h)

    pm_bad = pm_pred != truth
    ml_bad = ml_pred != truth
    mlc_bad = mlc_pred != truth
    rates = {k: int(b.sum()) / SHOTS for k, b in
             (("pymatching", pm_bad), ("moonlab_uf", ml_bad),
              ("moonlab_corr", mlc_bad))}
    void = any(r > VOID_RATE for r in rates.values())

    def ci(k):
        n_bad = int(round(rates[k] * SHOTS))
        return wilson_ci(n_bad, SHOTS)

    res = {
        "config": cfg, "seed": seed, "shots": SHOTS,
        "ndet": ndet, "nobs": nobs, "edges": int(len(ea)),
        "corr_links": int(len(ca)), "hyper_skipped": int(hyper),
        "void_out_of_regime": bool(void),
        "logical_error_rate": rates,
        "wilson95": {k: ci(k) for k in rates},
        "mcnemar": {},
        "decode_seconds_singlethread": {
            "pymatching": pm_t, "moonlab_uf": ml_t, "moonlab_corr": mlc_t},
    }
    for name, (a, b) in (("uf_vs_pm", (ml_bad, pm_bad)),
                          ("corr_vs_pm", (mlc_bad, pm_bad)),
                          ("corr_vs_uf", (mlc_bad, ml_bad))):
        oa, ob, z = mcnemar(a, b)
        res["mcnemar"][name] = {"only_first_bad": oa, "only_second_bad": ob,
                                 "z_positive_favours_first": round(z, 3)}
    pm_err = int(pm_bad.sum())
    res["corr_reduction_vs_pm_pct"] = (
        round(100.0 * (1.0 - int(mlc_bad.sum()) / pm_err), 2) if pm_err else None)
    return res


def main():
    out_dir = Path(__file__).parent / "artifacts_phase3"
    out_dir.mkdir(exist_ok=True)
    lib = load_lib()
    results = []
    for cfg in CONFIGS:
        print(f"[phase3] config {cfg['id']} d={cfg['d']} p={cfg['p']} "
              f"shots={SHOTS} ...", flush=True)
        r = run_config(lib, cfg)
        results.append(r)
        lr = r["logical_error_rate"]
        mz = r["mcnemar"]["corr_vs_pm"]["z_positive_favours_first"]
        red = r["corr_reduction_vs_pm_pct"]
        print(f"  pm={lr['pymatching']:.5f} uf={lr['moonlab_uf']:.5f} "
              f"corr={lr['moonlab_corr']:.5f}  corr-vs-pm z={mz} "
              f"reduction={red}%  void={r['void_out_of_regime']}", flush=True)
    payload = {
        "study": "moonlab_v120_reproduction/phase3_decoder",
        "authored_by": "Claude", "referee_pending": "Codex",
        "host": "Apple M2 Pro, macOS 26.5.2, arm64",
        "versions": {"moonlab_src_commit": "4bf83a6c47e7f1c53db14fcb2a61053499fd82df",
                      "stim": stim.__version__,
                      "pymatching": pymatching.__version__},
        "results": results,
    }
    path = out_dir / "phase3_decoder_results.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"[phase3] wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
