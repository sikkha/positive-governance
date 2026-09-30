"""Command-line entry point.

    abm-governance run --config experiments/configs/level0_default.yaml \\
        --seed 0 --steps 500 --out outputs/run_0

``--seed`` and ``--steps`` override the corresponding fields of a loaded
config (or of the built-in defaults if ``--config`` is omitted), which
makes single-seed smoke runs and quick reproducibility checks convenient
without hand-editing a YAML file.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys

from abm_governance.core.config import SimulationConfig
from abm_governance.core.export import export_results
from abm_governance.simulation import Simulation
from abm_governance.viz.timeseries import plot_timeseries


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="abm-governance")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a single seeded Level 0 simulation.")
    run.add_argument("--config", type=str, default=None, help="Path to a YAML config file.")
    run.add_argument("--seed", type=int, default=None, help="Override the config's seed.")
    run.add_argument("--steps", type=int, default=None, help="Override the config's n_steps.")
    run.add_argument("--out", type=str, default="outputs/run", help="Output directory.")
    run.add_argument("--no-plot", action="store_true", help="Skip PNG plot generation.")

    return parser


def _load_config(args: argparse.Namespace) -> SimulationConfig:
    config = SimulationConfig.from_yaml(args.config) if args.config else SimulationConfig()
    overrides = {}
    if args.seed is not None:
        overrides["seed"] = args.seed
    if args.steps is not None:
        overrides["n_steps"] = args.steps
    if overrides:
        config = dataclasses.replace(config, **overrides)
    return config


def run_command(args: argparse.Namespace) -> int:
    config = _load_config(args)
    print(f"[abm-governance] running Level 0: seed={config.seed} n_steps={config.n_steps} "
          f"population_size={config.population_size}", file=sys.stderr)

    result = Simulation(config).run()
    paths = export_results(result, args.out)

    if not args.no_plot:
        plot_path = plot_timeseries(result.metrics, f"{args.out}/timeseries.png")
        paths["plot"] = plot_path

    print("[abm-governance] wrote:", file=sys.stderr)
    for key, path in paths.items():
        print(f"  {key}: {path}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_command(args)
    parser.print_help()  # pragma: no cover - unreachable while "run" is the only command
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
