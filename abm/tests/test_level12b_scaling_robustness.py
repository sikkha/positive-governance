"""Level 1.2b, Work Package M (Section 18): tests for
``experiments/level12b_stage_m_scaling_robustness.py``."""
from __future__ import annotations

import json
import math
import os

import networkx as nx
import pytest

from experiments.level12b_stage_m_scaling_robustness import (
    GRID_CELLS,
    N_PATCHES_VALUES,
    POPULATION_SIZES,
    REWIRING_PROB_LEVELS,
    SEEDS_PER_CELL,
    _fragmentation_index,
    _measured_modularity,
)


class TestGridArithmetic:
    def test_grid_has_32_runs(self):
        assert len(GRID_CELLS) * SEEDS_PER_CELL == 32

    def test_grid_is_full_cross_product(self):
        assert len(GRID_CELLS) == len(POPULATION_SIZES) * len(N_PATCHES_VALUES) * len(REWIRING_PROB_LEVELS)

    def test_grid_cells_are_unique(self):
        assert len(set(GRID_CELLS)) == len(GRID_CELLS)


class TestFragmentationIndex:
    def test_zero_when_one_jurisdiction_spans_every_patch(self):
        assert _fragmentation_index(max_jurisdiction_size=4, n_patches=4) == pytest.approx(0.0)

    def test_high_when_largest_jurisdiction_is_a_small_share(self):
        assert _fragmentation_index(max_jurisdiction_size=1, n_patches=8) == pytest.approx(0.875)

    def test_nan_when_no_patches(self):
        assert math.isnan(_fragmentation_index(max_jurisdiction_size=0, n_patches=0))


class TestMeasuredModularity:
    def test_nan_on_empty_graph(self):
        g = nx.Graph()
        g.add_nodes_from(range(5))
        assert math.isnan(_measured_modularity(g))

    def test_nan_on_tiny_graph(self):
        g = nx.Graph()
        g.add_edge(0, 1)
        assert math.isnan(_measured_modularity(g))

    def test_defined_on_two_clear_clusters(self):
        g = nx.Graph()
        g.add_edges_from([(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
        result = _measured_modularity(g)
        assert result == result  # not NaN
        assert result > 0.0  # two disconnected triangles should show positive modularity


class TestActualExperimentOutputIfPresent:
    def test_results_meet_section_18_structural_requirements(self):
        out_dir = "outputs/level12b_stage_m_scaling_robustness"
        if not os.path.exists(f"{out_dir}/results.json"):
            pytest.skip("Work Package M experiment output not present in this environment")
        with open(f"{out_dir}/results.json") as f:
            report = json.load(f)
        assert report["n_runs_completed"] > 0
        assert report["scale_invariance_required"] is False
        assert report["source_design_hash"]
        assert report["preregistration_manifest_hash"]
        assert report["candidate_or_null_baseline"]
        measured_keys = {
            "ecological_state", "phenotype_assignment", "administrative_workload", "scale",
            "migration", "fragmentation", "functional_recovery", "transition_to_failure",
        }
        for rec in report["records"]:
            assert measured_keys.issubset(rec.keys())
            assert rec["population_size"] in POPULATION_SIZES
            assert rec["n_patches"] in N_PATCHES_VALUES
            assert rec["modularity_level"] in REWIRING_PROB_LEVELS
