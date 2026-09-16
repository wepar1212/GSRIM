"""CLI entry points: python -m gsrim.cli <command>."""
import argparse
import json
import sys
from pathlib import Path
from .project import DEFAULT, validate
from .simulation import Simulation
from .validation import VALIDATION_TARGETS, run_range_comparison, convergence_impact_scale


def cmd_run(args):
    project = json.loads(Path(args.project).read_text(encoding="utf-8")) if args.project else DEFAULT
    if args.ions is not None:
        project = dict(project)
        project["run"] = dict(project["run"], ions=args.ions)
    if args.batch is not None:
        project["run"]["batch_size"] = args.batch
    validate(project)
    sim = Simulation(project)
    sim.start()
    sim.thread.join()
    snap = sim.snapshot()
    if args.output:
        Path(args.output).write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": snap["status"],
        "error": snap["error"],
        "stats": snap["stats"],
        "timings": sim.timings(),
    }, ensure_ascii=False, indent=2))
    return 0 if snap["status"] == "completed" else 1


def cmd_validate(args):
    selected = []
    for t in VALIDATION_TARGETS:
        if args.ion and t.ion_symbol.lower() != args.ion.lower():
            continue
        if args.energy and abs(t.energy_kev - args.energy) > 1e-6:
            continue
        selected.append(t)
    if not selected:
        print("No matching validation targets", file=sys.stderr)
        return 2
    reports = []
    for t in selected:
        print(f"Running {t.ion_symbol} in {t.target_symbol} @ {t.energy_kev:g} keV ...", flush=True)
        reports.append(run_range_comparison(t, ions=args.ions, timeout_s=args.timeout))
    text = json.dumps(reports, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    return 0


def cmd_convergence(args):
    project = json.loads(Path(args.project).read_text(encoding="utf-8")) if args.project else DEFAULT
    report = convergence_impact_scale(project, ions=args.ions)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="gsrim", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run a simulation project")
    p_run.add_argument("--project", type=Path)
    p_run.add_argument("--ions", type=int)
    p_run.add_argument("--batch", type=int)
    p_run.add_argument("--output", type=Path)
    p_run.set_defaults(func=cmd_run)

    p_val = sub.add_parser("validate", help="Compare against published range targets")
    p_val.add_argument("--ion")
    p_val.add_argument("--energy", type=float, help="keV")
    p_val.add_argument("--ions", type=int, default=8192)
    p_val.add_argument("--timeout", type=float, default=180.0)
    p_val.add_argument("--output", type=Path)
    p_val.set_defaults(func=cmd_validate)

    p_c = sub.add_parser("convergence", help="Impact-scale convergence check")
    p_c.add_argument("--project", type=Path)
    p_c.add_argument("--ions", type=int, default=2048)
    p_c.add_argument("--output", type=Path)
    p_c.set_defaults(func=cmd_convergence)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
