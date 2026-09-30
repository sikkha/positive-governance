#!/usr/bin/env python3
"""Level 1.2b, Work Package E + Section 10 (initial-condition families):
the stratified joint discovery design.

Crosses ecological feasibility (Work Package C's own parameter space,
freshly sampled here) x institutional variation (Work Package D's own
parameter space, freshly sampled here) x initial-condition family x
seeds. This is the milestone's actual main data-generating run — the
raw pool Work Packages F/G/H and the discovery pipeline (Section 15+)
consume.

**Stratification discipline (Section 9)**: stratified ONLY by the
ex-ante expected-pressure ratio (Work Package B's `expected_pressure_
ratio`, never any realized simulation outcome). Cut points (tertiles)
are computed from this design's own 48 ecological draws and FROZEN
before any run executes. Ecological and institutional draws are sampled
INDEPENDENTLY (separate Latin Hypercube calls, paired index-by-index),
which by construction gives multiple different institutional points
within each ecological stratum and vice versa (Section 9's own explicit
requirement) — no additional stratified-pairing logic is needed for
that guarantee to hold.

**Run arithmetic** (Section 9, saved as explicit fields): preferred
`n_joint_points=48`, `seeds_per_point=6`, `n_ic_families=2`,
`total_runs=576`, `n_steps=700`. Hard minimum (`n_joint_points=36`,
`seeds_per_point=4`, `n_ic_families=2`, `total_runs=288`) is documented
here but not used unless a stop condition forces a reduction — none
did.

**Initial-condition families (Section 10)**:
- A. institution-free — the model's own default initial state (no
  active rule anywhere; institutions may emerge endogenously through
  ordinary `rule_formation_round` mechanics, completely unmodified).
- B. heterogeneous proto-institution — one independently-parameterized
  `SharedRule` injected per patch immediately after `Simulation.
  __init__` (before `.run()`), each patch's `RuleParameters` drawn on
  its own independent uniform range (never bundled into a package,
  never resembling any preferred macro-type), each patch given its own
  fresh `rule_lineage_id` (Section 10's "multiple lineages" — patches
  never start sharing ancestry). This is experiment-harness-level state
  setup (direct `rule_registry`/`agent.rule_member_of` assignment,
  exactly mirroring how `simulation.py`'s own pre-existing
  `institution_imposed_mode` already injects a rule the same way,
  just heterogeneous instead of uniform) — no change to
  `simulation.py`/`rules/*.py` themselves.

**Preregistration note**: Section 14's full milestone-level
preregistration manifest is created after this design (this session's
own task ordering — Work Packages C/D/E each already generate+hash
their own design before running, exactly like Section 14 will later
assemble). Every run record here carries this design's own
`design_hash` in place of a not-yet-existing `preregistration_hash`,
disclosed explicitly rather than fabricated."""

from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
from scipy.stats import qmc

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.ecological_ledger import compute_ledger_reconciliation, system_total_resources
from abm_governance.observer.feasibility_ratios import expected_pressure_ratio, structural_feasibility_ratio
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation
from experiments.level12b_stage_c_feasibility_map import _build_perturbations
from experiments.level12b_stage_c_feasibility_map import PARAMETER_SPACE as ECOLOGICAL_PARAMETER_SPACE
from experiments.level12b_stage_d_institutional_design import PARAMETER_SPACE as INSTITUTIONAL_PARAMETER_SPACE

OUT_DIR = "outputs/level12b_stage_e_joint_discovery"

N_JOINT_POINTS_PREFERRED = 48
SEEDS_PER_POINT_PREFERRED = 6
N_JOINT_POINTS_HARD_MINIMUM = 36
SEEDS_PER_POINT_HARD_MINIMUM = 4
N_IC_FAMILIES = 2
N_STEPS = 700
POPULATION_SIZE = 32
N_PATCHES = 4

LHS_SEED_ECOLOGICAL = 20260818001  # fixed, disclosed; distinct from Work Package C's own LHS_SEED
LHS_SEED_INSTITUTIONAL = 20260818002

IC_FAMILIES = ("institution_free", "heterogeneous_proto_institution")


def _lhs_draws(space: tuple, n: int, seed: int) -> list[dict]:
    sampler = qmc.LatinHypercube(d=len(space), seed=seed)
    unit_sample = sampler.random(n=n)
    lows = np.array([lo for _, lo, _ in space])
    highs = np.array([hi for _, _, hi in space])
    scaled = qmc.scale(unit_sample, lows, highs)
    names = [name for name, _, _ in space]
    return [dict(zip(names, row)) for row in scaled.tolist()]


#: Work Package E reuses Work Package C's own ecological parameter
#: bounds for consistency, EXCLUDING ``population_patch_ratio_selector``
#: -- population/patch structure is held fixed here (``POPULATION_SIZE``/
#: ``N_PATCHES`` below); varying it is Section 18's own scaling-
#: robustness question, not this design's.
_ECOLOGICAL_SPACE_FOR_WPE: tuple = tuple(
    t for t in ECOLOGICAL_PARAMETER_SPACE if t[0] != "population_patch_ratio_selector"
)


def build_design(n_joint_points: int = N_JOINT_POINTS_PREFERRED, seeds_per_point: int = SEEDS_PER_POINT_PREFERRED) -> dict:
    eco_draws = _lhs_draws(_ECOLOGICAL_SPACE_FOR_WPE, n_joint_points, LHS_SEED_ECOLOGICAL)
    inst_draws = _lhs_draws(INSTITUTIONAL_PARAMETER_SPACE, n_joint_points, LHS_SEED_INSTITUTIONAL)

    # Ex-ante expected-pressure ratio for each ecological draw, computed
    # BEFORE any run and BEFORE stratum cut points are frozen -- uses a
    # throwaway config (institutional fields at level12_complete's own
    # defaults; only the ecological fields this ratio depends on matter).
    ratios = []
    for draw in eco_draws:
        eco = dict(draw)
        eco.pop("shock_interval_steps", None)
        eco.pop("shock_magnitude", None)
        cfg = SimulationConfig.level12_complete(
            population_size=POPULATION_SIZE, n_patches=N_PATCHES, n_steps=N_STEPS, seed=1, **eco,
        )
        ratios.append(expected_pressure_ratio(cfg).ratio)

    finite_ratios = sorted(r for r in ratios if math.isfinite(r))
    if len(finite_ratios) >= 3:
        low_cut = finite_ratios[len(finite_ratios) // 3]
        high_cut = finite_ratios[(2 * len(finite_ratios)) // 3]
    else:
        low_cut = high_cut = math.nan

    def _stratum(r: float) -> str:
        if not math.isfinite(r) or not math.isfinite(low_cut):
            return "undefined"
        if r <= low_cut:
            return "low_feasibility"
        if r <= high_cut:
            return "medium_feasibility"
        return "high_feasibility"

    points = []
    for point_id in range(n_joint_points):
        eco = eco_draws[point_id]
        points.append({
            "joint_point_id": point_id,
            "ecological_point_id": point_id,
            "institutional_point_id": point_id,
            "ecological_parameters": eco,
            "institutional_parameters": inst_draws[point_id],
            "expected_pressure_ratio": ratios[point_id],
            "expected_stratum": _stratum(ratios[point_id]),
            "population_size": POPULATION_SIZE,
            "n_patches": N_PATCHES,
            "seeds": [9_000_000 + point_id * 1000 + s for s in range(seeds_per_point)],
        })

    stratum_counts = {}
    for p in points:
        stratum_counts[p["expected_stratum"]] = stratum_counts.get(p["expected_stratum"], 0) + 1

    return {
        "milestone": "level1.2b_stratified_joint_discovery_design_work_package_e",
        "n_joint_points": n_joint_points,
        "seeds_per_point": seeds_per_point,
        "n_ic_families": N_IC_FAMILIES,
        "ic_families": list(IC_FAMILIES),
        "total_runs": n_joint_points * seeds_per_point * N_IC_FAMILIES,
        "n_steps": N_STEPS,
        "lhs_seed_ecological": LHS_SEED_ECOLOGICAL,
        "lhs_seed_institutional": LHS_SEED_INSTITUTIONAL,
        "stratum_cut_points": {"low_cut": low_cut, "high_cut": high_cut},
        "stratum_counts": stratum_counts,
        "points": points,
        "stratification_basis": "ex_ante_expected_pressure_ratio_only_never_realized_outcomes",
    }


def design_hash(design: dict) -> str:
    payload = json.dumps(design, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_design(out_dir: str = OUT_DIR, **kwargs) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    design = build_design(**kwargs)
    digest = design_hash(design)
    with open(f"{out_dir}/design.json", "w") as f:
        json.dump(design, f, indent=2, sort_keys=True, default=str)
    with open(f"{out_dir}/design_hash.txt", "w") as f:
        f.write(digest + "\n")
    return {"design": design, "hash": digest}


def load_and_verify_design(out_dir: str = OUT_DIR) -> dict:
    with open(f"{out_dir}/design.json") as f:
        design = json.load(f)
    with open(f"{out_dir}/design_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = design_hash(design)
    if recomputed != stored_hash:
        raise ValueError(
            f"Work Package E joint discovery design at {out_dir}/design.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"design": design, "hash": recomputed}


def _build_config(point: dict, seed: int) -> SimulationConfig:
    eco = dict(point["ecological_parameters"])
    inst = dict(point["institutional_parameters"])
    inst["coordination_proposal_window_steps"] = int(round(inst["coordination_proposal_window_steps"]))
    perturbations = _build_perturbations(point, N_STEPS)
    eco.pop("shock_interval_steps", None)
    eco.pop("shock_magnitude", None)
    return SimulationConfig.level12_complete(
        population_size=point["population_size"], n_patches=point["n_patches"], n_steps=N_STEPS, seed=seed,
        delegation_enabled=True, discretion_enabled=True, accountability_enabled=True,
        interpatch_coordination_enabled=True, institutional_fund_contribution_rate=0.05,
        perturbations=perturbations,
        **eco, **inst,
    )


def _inject_heterogeneous_proto_institutions(sim: Simulation, seed: int) -> None:
    """Section 10, Family B. Deterministic given ``seed`` -- a dedicated
    RNG derived from this run's own seed (not the simulation's own
    mechanism-substream registry, since this happens before ``sim.run()``
    even begins stepping), disclosed and reproducible."""
    rng = np.random.default_rng(seed * 1_000 + 777)
    for pid, patch in sim.patch_system.patches.items():
        eligible = [aid for aid in patch.members if sim.agents_by_id[aid].alive]
        if not eligible:
            continue
        params = RuleParameters(
            extraction_ceiling=float(rng.uniform(0.1, 0.9)),
            maintenance_requirement=float(rng.uniform(0.0, 0.5)),
            monitoring_intensity=float(rng.uniform(0.0, 1.0)),
            sanction_magnitude=float(rng.uniform(0.0, 1.0)),
            adoption_threshold=float(rng.uniform(0.1, 0.9)),
            amendment_threshold=float(rng.uniform(0.1, 0.9)),
        )
        rule_id = sim._rule_id_state["next_rule_id"]
        sim._rule_id_state["next_rule_id"] += 1
        lineage_id = sim._rule_id_state["next_lineage_id"]  # a fresh, patch-own lineage: no shared ancestry
        sim._rule_id_state["next_lineage_id"] += 1
        member_fraction = float(rng.uniform(0.3, 1.0))
        n_members = max(1, int(round(member_fraction * len(eligible))))
        chosen = rng.choice(np.array(eligible), size=n_members, replace=False)
        members = frozenset(int(a) for a in chosen)
        rule = SharedRule(
            rule_id=rule_id, patch_id=pid, parameters=params, founding_step=0,
            founder_id=-1, rule_lineage_id=lineage_id, members=members, supporters=members,
        )
        sim.rule_registry[pid] = rule
        for aid in members:
            sim.agents_by_id[aid].rule_member_of = rule_id


def _config_hash(config: SimulationConfig) -> str:
    payload = json.dumps({k: v for k, v in vars(config).items()}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run(n_joint_points: int = N_JOINT_POINTS_PREFERRED, seeds_per_point: int = SEEDS_PER_POINT_PREFERRED) -> dict:
    verified = load_and_verify_design()
    design = verified["design"]

    records = []
    failures = []
    for point in design["points"]:
        for ic_family in IC_FAMILIES:
            for seed in point["seeds"]:
                config = _build_config(point, seed)
                try:
                    sim = Simulation(config)
                    if ic_family == "heterogeneous_proto_institution":
                        _inject_heterogeneous_proto_institutions(sim, seed)
                    opening = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
                    result = sim.run()
                    closing = system_total_resources(sim.patch_system, sim.agents, sim.rule_registry)
                    rec = compute_ledger_reconciliation(
                        opening_stock=opening, closing_stock=closing, patch_system=sim.patch_system,
                        event_log=sim.event_log, search_cost=config.search_cost,
                        membership_exit_cost=config.membership_exit_cost,
                    )
                except Exception as exc:  # noqa: BLE001 -- preserve failed runs, never silently drop
                    failures.append({
                        "joint_point_id": point["joint_point_id"], "ic_family": ic_family, "seed": seed, "error": str(exc),
                    })
                    continue

                n_rules_active_at_end = sum(1 for r in sim.rule_registry.values() if r.active)
                # Total rule IDs ever allocated (sequential from 0) --
                # a crude "ever formed" count; Work Package F's own
                # audited phenotype features supersede this for the
                # main discovery pipeline.
                n_rules_ever_formed = sim._rule_id_state["next_rule_id"]
                surviving_population = sum(1 for a in sim.agents if a.alive)

                records.append({
                    "design_hash": verified["hash"],
                    "joint_point_id": point["joint_point_id"],
                    "ecological_point_id": point["ecological_point_id"],
                    "institutional_point_id": point["institutional_point_id"],
                    "ic_family": ic_family,
                    "seed": seed,
                    "expected_stratum": point["expected_stratum"],
                    "expected_pressure_ratio": point["expected_pressure_ratio"],
                    "config_hash": _config_hash(config),
                    "preregistration_hash": None,  # Section 14 manifest not yet created -- disclosed, not fabricated
                    "ledger_residual": rec.residual,
                    "n_rules_active_at_end": n_rules_active_at_end,
                    "n_rules_ever_formed": n_rules_ever_formed,
                    "surviving_population": surviving_population,
                    "surviving_population_fraction": surviving_population / point["population_size"],
                })
        print(f"joint point {point['joint_point_id']} ({point['expected_stratum']}) done", flush=True)

    # Level 1.2b, Work Package E production-scale ledger-residual fix:
    # tightened from an earlier 1e-2 (a loose gate chosen before the
    # underlying accounting bugs -- see dev_mem/status_update.md -- were
    # found and fixed) to 1e-4, matching this project's own established
    # full-run integration tolerance (tests/test_level12b_ecological_
    # ledger.py::TestFullSimulationResidualIsZero). Real production runs
    # now reconcile to ~1e-10, so 1e-4 is comfortably tight while still
    # allowing for genuine floating-point accumulation across 700 steps.
    n_ledger_ok = sum(1 for r in records if abs(r["ledger_residual"]) < 1e-4)

    report = {
        "design_hash": verified["hash"],
        "n_runs_completed": len(records),
        "n_runs_failed": len(failures),
        "failures": failures,
        "n_runs_with_ledger_residual_under_tolerance": n_ledger_ok,
        "stratum_counts": design["stratum_counts"],
        "hard_minimum_met": len(records) >= N_JOINT_POINTS_HARD_MINIMUM * SEEDS_PER_POINT_HARD_MINIMUM * N_IC_FAMILIES,
        "preferred_target_met": len(records) >= N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES,
        "records": records,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/results.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    design_result = write_design()
    print(f"Work Package E joint design frozen at {OUT_DIR}/design.json")
    print(f"design hash: {design_result['hash']}")
    print(f"stratum_counts: {design_result['design']['stratum_counts']}")
    report_result = run()
    print(f"n_runs_completed={report_result['n_runs_completed']} n_runs_failed={report_result['n_runs_failed']}")
    print(f"hard_minimum_met={report_result['hard_minimum_met']} preferred_target_met={report_result['preferred_target_met']}")
    print(f"n_runs_with_ledger_residual_under_tolerance={report_result['n_runs_with_ledger_residual_under_tolerance']}")
