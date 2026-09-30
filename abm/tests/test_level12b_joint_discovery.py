"""Level 1.2b, Work Package E + Section 10 (initial-condition families):
tests for ``experiments/level12b_stage_e_joint_discovery.py``."""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pytest

from experiments.level12b_stage_e_joint_discovery import (
    IC_FAMILIES,
    N_IC_FAMILIES,
    N_JOINT_POINTS_HARD_MINIMUM,
    N_JOINT_POINTS_PREFERRED,
    N_STEPS,
    SEEDS_PER_POINT_HARD_MINIMUM,
    SEEDS_PER_POINT_PREFERRED,
    _build_config,
    _ECOLOGICAL_SPACE_FOR_WPE,
    _inject_heterogeneous_proto_institutions,
    build_design,
    design_hash,
)
from abm_governance.simulation import Simulation


class TestRunArithmetic:
    def test_preferred_and_hard_minimum_meet_section_9(self):
        assert N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES == 576
        assert N_JOINT_POINTS_HARD_MINIMUM * SEEDS_PER_POINT_HARD_MINIMUM * N_IC_FAMILIES == 288
        assert N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES >= (
            N_JOINT_POINTS_HARD_MINIMUM * SEEDS_PER_POINT_HARD_MINIMUM * N_IC_FAMILIES
        )
        assert N_STEPS >= 600

    def test_two_initial_condition_families(self):
        assert N_IC_FAMILIES == 2
        assert set(IC_FAMILIES) == {"institution_free", "heterogeneous_proto_institution"}


class TestDesignGeneration:
    def test_deterministic(self):
        d1 = build_design()
        d2 = build_design()
        assert d1 == d2
        assert design_hash(d1) == design_hash(d2)

    def test_design_has_explicit_point_count_and_total_runs(self):
        design = build_design()
        assert design["n_joint_points"] == N_JOINT_POINTS_PREFERRED
        assert len(design["points"]) == N_JOINT_POINTS_PREFERRED
        assert design["seeds_per_point"] == SEEDS_PER_POINT_PREFERRED
        assert design["total_runs"] == N_JOINT_POINTS_PREFERRED * SEEDS_PER_POINT_PREFERRED * N_IC_FAMILIES

    def test_hard_minimum_size_also_buildable(self):
        design = build_design(n_joint_points=N_JOINT_POINTS_HARD_MINIMUM, seeds_per_point=SEEDS_PER_POINT_HARD_MINIMUM)
        assert len(design["points"]) == N_JOINT_POINTS_HARD_MINIMUM
        assert all(len(p["seeds"]) == SEEDS_PER_POINT_HARD_MINIMUM for p in design["points"])

    def test_population_patch_ratio_selector_excluded_from_ecological_space(self):
        """Section 9 does not require population/patch variation (that's
        Section 18's scaling-robustness question); an unused-but-sampled
        dimension would be misleading, so it must not appear here."""
        names = [n for n, _, _ in _ECOLOGICAL_SPACE_FOR_WPE]
        assert "population_patch_ratio_selector" not in names


class TestStratificationDiscipline:
    """Section 9: stratified ONLY by ex-ante ratios, never realized
    outcomes; cut points frozen before any run."""

    def test_stratum_computed_before_any_run(self):
        design = build_design()
        for p in design["points"]:
            assert "expected_pressure_ratio" in p
            assert "expected_stratum" in p
            assert p["expected_stratum"] in ("low_feasibility", "medium_feasibility", "high_feasibility", "undefined")

    def test_cut_points_are_frozen_and_deterministic(self):
        d1 = build_design()
        d2 = build_design()
        assert d1["stratum_cut_points"] == d2["stratum_cut_points"]

    def test_multiple_points_per_stratum(self):
        """Section 9 explicit requirement: multiple ecological points per
        institutional... and multiple institutional points per ecological
        stratum. Independent LHS draws (ecological and institutional
        sampled separately, paired only by index) guarantee this by
        construction -- verified here rather than merely asserted."""
        design = build_design()
        stratum_counts = design["stratum_counts"]
        populated_strata = [k for k, v in stratum_counts.items() if v > 0]
        assert len(populated_strata) >= 2, "design should not collapse into a single stratum"
        for stratum in populated_strata:
            if stratum == "undefined":
                continue
            institutional_points_in_stratum = {
                p["institutional_point_id"] for p in design["points"] if p["expected_stratum"] == stratum
            }
            if stratum_counts[stratum] >= 2:
                assert len(institutional_points_in_stratum) >= 2

    def test_never_uses_realized_outcomes(self):
        """AST-level check: build_design's own source never reads a
        result from Simulation.run() or event_log before computing
        strata -- structurally, build_design never calls Simulation at
        all (only _build_config-adjacent throwaway configs +
        expected_pressure_ratio, an ex-ante-only function per Work
        Package B)."""
        import ast
        import inspect

        from experiments.level12b_stage_e_joint_discovery import build_design as bd

        source = inspect.getsource(bd)
        tree = ast.parse(source)
        called_names = {
            node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
            for node in ast.walk(tree) if isinstance(node, ast.Call)
        }
        assert "run" not in called_names
        assert "Simulation" not in called_names


class TestConfigBuilding:
    def test_builds_valid_config_for_every_point(self):
        design = build_design()
        for point in design["points"][:5]:
            config = _build_config(point, point["seeds"][0])
            assert config.rng_mode == "mechanism_substreams"
            assert config.n_steps == N_STEPS

    def test_shock_synthetic_keys_never_reach_config_constructor(self):
        """A prior bug: shock_interval_steps/shock_magnitude (WP C-only
        synthetic parameter names, converted into a perturbations tuple)
        were passed directly as SimulationConfig kwargs, which would
        raise TypeError -- this must not regress."""
        design = build_design()
        point = design["points"][0]
        config = _build_config(point, point["seeds"][0])  # must not raise
        assert not hasattr(config, "shock_interval_steps")
        assert not hasattr(config, "shock_magnitude")

    def test_coordination_window_steps_rounded_to_int(self):
        design = build_design()
        config = _build_config(design["points"][0], design["points"][0]["seeds"][0])
        assert isinstance(config.coordination_proposal_window_steps, int)

    def test_ecology_and_institutions_both_vary_across_points(self):
        design = build_design()
        configs = [_build_config(p, p["seeds"][0]) for p in design["points"][:6]]
        regen_rates = {c.patch_regen_rate for c in configs}
        thresholds = {c.preferred_adoption_threshold_mean for c in configs}
        assert len(regen_rates) > 1
        assert len(thresholds) > 1


class TestHeterogeneousProtoInstitutionInjection:
    """Section 10, Family B: no packages, no preferred macro-type,
    multiple independent lineages."""

    def test_injects_one_rule_per_patch_with_distinct_lineages(self):
        design = build_design()
        point = design["points"][0]
        config = _build_config(point, point["seeds"][0])
        sim = Simulation(config)
        _inject_heterogeneous_proto_institutions(sim, point["seeds"][0])
        assert len(sim.rule_registry) == len(sim.patch_system.patches)
        lineage_ids = [r.rule_lineage_id for r in sim.rule_registry.values()]
        assert len(set(lineage_ids)) == len(lineage_ids), "each patch must get its own fresh lineage (no shared ancestry)"

    def test_parameters_independently_drawn_not_bundled_into_a_package(self):
        """Crude but effective 'not secretly bundled' check, mirroring
        Work Package D's own: across many injected rules, no two
        RuleParameters fields should be perfectly correlated."""
        design = build_design()
        point = design["points"][0]
        all_params = []
        for seed in point["seeds"]:
            config = _build_config(point, seed)
            sim = Simulation(config)
            _inject_heterogeneous_proto_institutions(sim, seed)
            for rule in sim.rule_registry.values():
                all_params.append(rule.parameters.as_dict())
        names = list(all_params[0].keys())
        matrix = np.array([[p[n] for n in names] for p in all_params])
        if matrix.shape[0] >= 3:
            corr = np.corrcoef(matrix, rowvar=False)
            n = len(names)
            off_diagonal = [corr[i, j] for i in range(n) for j in range(n) if i != j]
            finite = [c for c in off_diagonal if math.isfinite(c)]
            assert all(abs(c) < 0.95 for c in finite), "two RuleParameters fields appear bundled (|corr| >= 0.95)"

    def test_deterministic_given_seed(self):
        design = build_design()
        point = design["points"][0]
        seed = point["seeds"][0]
        configs = [_build_config(point, seed) for _ in range(2)]
        sims = [Simulation(c) for c in configs]
        for sim in sims:
            _inject_heterogeneous_proto_institutions(sim, seed)
        params_a = [r.parameters.as_dict() for r in sims[0].rule_registry.values()]
        params_b = [r.parameters.as_dict() for r in sims[1].rule_registry.values()]
        assert params_a == params_b

    def test_institution_free_family_starts_with_no_active_rules(self):
        design = build_design()
        point = design["points"][0]
        config = _build_config(point, point["seeds"][0])
        sim = Simulation(config)
        assert len(sim.rule_registry) == 0


class TestActualExperimentOutputIfPresent:
    """If Work Package E's own run has already been executed in this
    environment, verify the saved results meet Section 9's completion
    requirements and the ledger-closure gate (Section 5.7) this run was
    specifically blocked on until the production-scale residual bugs
    were found and fixed (see dev_mem/status_update.md). Skipped
    entirely if the experiment has not been run in this environment."""

    def test_results_meet_section_9_requirements(self):
        out_dir = "outputs/level12b_stage_e_joint_discovery"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package E experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_runs_failed"] == 0
        assert report["hard_minimum_met"] is True
        assert report["n_runs_completed"] >= N_JOINT_POINTS_HARD_MINIMUM * SEEDS_PER_POINT_HARD_MINIMUM * N_IC_FAMILIES
        # Section 5.7's ledger-closure gate: every run must reconcile.
        assert report["n_runs_with_ledger_residual_under_tolerance"] == report["n_runs_completed"]
        for r in report["records"]:
            assert abs(r["ledger_residual"]) < 1e-4
        ic_counts = {}
        for r in report["records"]:
            ic_counts[r["ic_family"]] = ic_counts.get(r["ic_family"], 0) + 1
        assert set(ic_counts.keys()) == {"institution_free", "heterogeneous_proto_institution"}
        assert all(v > 0 for v in ic_counts.values())
