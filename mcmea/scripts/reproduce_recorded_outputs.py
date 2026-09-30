#!/usr/bin/env python3
"""Recompute every numerical result recorded in the MCMEA evidence notebooks and
compare it with the stored values (expected/recorded_notebook_outputs.json).

Runs from a clean process (no notebook state). Also reports two supplementary
quantities that the notebooks do not print but that the specification audit
needs (docs/mcmea_specification_audit.md): per-generation macrostate
occupancy for the seed-7 examples and the v2 repeated-run terminal macrostates.
Those supplementary values are labelled as such and are not compared with any
stored output.

Usage (from the mcmea/ directory):
    python scripts/reproduce_recorded_outputs.py            # full check, ~1 min
    python scripts/reproduce_recorded_outputs.py --quick    # seed-7 examples only, ~2 s
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

import mcmea_v2  # noqa: E402
import mcmea_v3  # noqa: E402

EXP = json.loads((HERE / "expected" / "recorded_notebook_outputs.json").read_text())
SL = EXP["state_order"]
COMMON = dict(m_eval=5, lambda_robust=1.0, regime_select_mode="robust_max", regime_select_temp=1.0)
failures: list[str] = []


def check(label: str, got, want) -> None:
    ok = got == want
    print(f"[{'ok' if ok else 'FAIL'}] {label}: got={got} expected={want}")
    if not ok:
        failures.append(label)


def close(label: str, got: float, want: float, nd: int) -> None:
    check(label, round(got, nd), round(want, nd))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="seed-7 examples only")
    args = ap.parse_args()

    # v2 seed-7 example
    _, macro, _, _ = mcmea_v2.run_mcmea_v2(pop_size=90, generations=60, seed=7, **COMMON)
    _, C = mcmea_v2.build_markov(macro, SL)
    check("v2 seed7 transition counts", C.astype(int).tolist(), EXP["v2"]["example_seed7"]["transition_counts"])
    print(f"    supplementary: v2 seed7 macrostate occupancy over {len(macro)} generations = {dict(Counter(macro))}; first={macro[0]}")

    # v3 seed-7 examples, all three profiles
    for pf in ("east", "anglo", "europe"):
        _, m3, _, d3 = mcmea_v3.run_mcmea_v3(pop_size=90, generations=60, seed=7, profile=pf, **COMMON)
        _, C3 = mcmea_v3.build_markov(m3, SL)
        if pf == "east":
            check("v3 seed7 east transition counts", C3.astype(int).tolist(), EXP["v3"]["example_seed7_east"]["transition_counts"])
        print(f"    supplementary: v3 seed7 {pf} occupancy = {dict(Counter(m3))}; counts={C3.astype(int).tolist()}")

    if args.quick:
        return 1 if failures else 0

    seeds = list(range(20, 60))
    r2 = mcmea_v2.run_many_v2(seeds, pop_size=90, generations=50, **COMMON)
    e2 = EXP["v2"]["multirun_seeds20_59"]
    close("v2 multirun winner entropy H", r2["H"], e2["winner_entropy_H"], 3)
    close("v2 multirun effective winners", r2["eff"], e2["effective_winners"], 2)
    check("v2 multirun unique winner bins", len(r2["counts"]), e2["unique_winner_bins"])
    term = Counter(mcmea_v2.run_mcmea_v2(seed=s, pop_size=90, generations=50, **COMMON)[1][-1] for s in seeds)
    print(f"    supplementary (not printed by the v2 notebook): v2 terminal elite-centroid macrostates = {dict(term)}")

    for pf, want in EXP["v3"]["multirun_seeds20_59"].items():
        r3 = mcmea_v3.run_many_v3(seeds, profile=pf, pop_size=90, generations=50, **COMMON)
        close(f"v3 multirun {pf} H", r3["H"], want["H"], 3)
        close(f"v3 multirun {pf} eff", r3["eff"], want["eff"], 2)
        check(f"v3 multirun {pf} terminal macrostates", {k: int(v) for k, v in r3["macro_counts"].items()}, want["macro_counts"])

    print("=== ALL RECORDED MCMEA OUTPUTS REPRODUCED ===" if not failures else f"=== {len(failures)} MISMATCH(ES) ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
