"""Benchmarks for the elementary solver and for complete transport workloads.

Every report states its own scope. No number here is a speedup versus SRIM or
versus an optimized CPU binary-collision code: no such comparison is measured.
"""
import argparse
import copy
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from .scattering import scatter, backend
from .project import DEFAULT, validate
from .simulation import Simulation

SCOPE_SCATTER = "elementary binary collisions only; no transport or cascades"
SCOPE_TRANSPORT = "complete binary-collision transport histories including recoil cascades"
NOTES = [
    "Measured on one GPU model; results do not transfer to other devices.",
    "Absolute GPU cost only. Not a speedup versus SRIM, TRIM, or any CPU BCA code.",
    "Wall time includes the device-to-host copy of each batch; kernel time does not.",
    "Timings are taken on the production code path, not a synthetic loop.",
]


def device_name(cp):
    return cp.cuda.runtime.getDeviceProperties(0)["name"].decode()


def elementary(count):
    cp = backend("gpu")
    e = np.geomspace(100, 1e6, count)
    b = np.geomspace(.001, 1, count)
    config = dict(z1=2, z2=14, m1=4, m2=28)
    start = perf_counter()
    scatter(e, b, engine="gpu", **config)
    cp.cuda.Stream.null.synchronize()
    cold = perf_counter()-start
    times = {}
    results = {}
    for engine in ("cpu", "gpu"):
        samples = []
        for _ in range(3):
            start = perf_counter()
            result = scatter(e, b, engine=engine, **config)
            if engine == "gpu":
                result = tuple(x.get() for x in result)
            samples.append(perf_counter()-start)
        results[engine] = result
        times[engine] = float(np.median(samples))
    for x, y in zip(results["cpu"], results["gpu"]):
        np.testing.assert_allclose(x, y, rtol=1e-6, atol=2e-6)
    return {"scope": SCOPE_SCATTER, "device": device_name(cp), "count": count,
            "precision": "float64", "quadrature_order": 128,
            "cpu_reference": "NumPy vectorized; not an optimized CPU BCA engine",
            "gpu_first_call_seconds": cold, "median_seconds_including_transfers": times,
            "speed_ratio_vs_numpy": times["cpu"]/times["gpu"],
            "max_angle_error_rad": float(np.max(np.abs(results['cpu'][0]-results['gpu'][0]))),
            "notes": NOTES}


def transport(project, ions, batch_size, timeout_s=900.0):
    """Run a matched physical workload end to end and report its measured cost.

    The run is a real simulation: it must complete, conserve energy and produce
    finite statistics, otherwise no benchmark number is reported at all.
    """
    p = copy.deepcopy(project)
    p["run"]["ions"] = ions
    p["run"]["batch_size"] = batch_size
    validate(p)
    sim = Simulation(p)
    sim.start()
    sim.thread.join(timeout_s)
    if sim.thread.is_alive():
        sim.cancel()
        sim.thread.join(60)
        raise RuntimeError("Transport benchmark exceeded its time budget; no result reported")
    if sim.status != "completed":
        raise RuntimeError(f"Transport benchmark did not complete: {sim.status} {sim.error}")
    timing = sim.timings()
    if timing is None:
        raise RuntimeError("No dispatch timing was recorded")
    snap = sim.snapshot()
    stats = snap["stats"]
    if not np.isfinite([stats["max_energy_error_ev"], timing["median_batch_kernel_s"]]).all():
        raise RuntimeError("Nonfinite benchmark output; results rejected")
    measured = timing["ions_measured"]
    if timing["steady_batches"] < 1 or measured <= 0:
        raise RuntimeError("Too few dispatches to report a steady-state rate; increase ions or reduce batch size")
    cp = backend("gpu")
    return {"scope": SCOPE_TRANSPORT, "device": device_name(cp), "precision": "float64",
            "project": {"name": p["name"], "ion": p["ion"],
                        "layers": [{"name": l["name"], "thickness_a": l["thickness_a"],
                                    "species": [s["symbol"] for s in l["species"]]} for l in p["layers"]],
                        "mode": p["run"]["mode"], "cutoff_ev": p["run"]["cutoff_ev"]},
            "workload": {"ions": ions, "batch_size": batch_size, "completed_histories": snap["completed"]},
            "prepare_s": timing["prepare_s"], "steady_batches": timing["steady_batches"],
            "median_batch_wall_s": timing["median_batch_wall_s"],
            "median_batch_kernel_s": timing["median_batch_kernel_s"],
            "total_kernel_s": timing["total_kernel_s"],
            "throughput": {"ions_per_s_wall": timing["ions_per_s_wall"],
                           "ions_per_s_kernel": timing["ions_per_s_kernel"],
                           "events_per_s_kernel": timing["events_per_s_kernel"]},
            "physics": {"total_events": timing["events"],
                        "mean_events_per_ion": timing["events"]/max(1, measured),
                        "mean_range_nm": stats["mean_range_nm"],
                        "range_std_nm": stats["range_std_nm"],
                        "implanted": stats["implanted"], "backscattered": stats["backscattered"],
                        "transmitted": stats["transmitted"],
                        "displacements_per_ion": stats["displacements_per_ion"],
                        "sputter_yield_front": stats["sputter_yield_front"],
                        "max_energy_error_ev": stats["max_energy_error_ev"]},
            "notes": NOTES + ["Workload must complete and conserve energy before any number is reported."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("scattering", "transport"), default="scattering")
    parser.add_argument("--count", type=int, default=65536, help="collisions for scattering mode")
    parser.add_argument("--ions", type=int, default=4096, help="histories for transport mode")
    parser.add_argument("--batch", type=int, default=4096, help="histories per dispatch for transport mode")
    parser.add_argument("--project", type=Path, help="project JSON for transport mode")
    parser.add_argument("--timeout", type=float, default=900.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "scattering":
        if not 1 <= args.count <= 1000000:
            parser.error("count must be 1..1000000")
        report = elementary(args.count)
    else:
        project = DEFAULT
        if args.project is not None:
            project = json.loads(args.project.read_text(encoding="utf-8"))
        if not 1 <= args.ions <= 1000000:
            parser.error("ions must be 1..1000000")
        if not 1 <= args.batch <= 65536:
            parser.error("batch must be 1..65536")
        report = transport(project, args.ions, args.batch, args.timeout)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
