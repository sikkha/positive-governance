"""Level 1.2b, Work Package D (Section 8): tests for
``experiments/level12b_stage_d_institutional_design.py``."""
from __future__ import annotations

import pytest

from experiments.level12b_stage_d_institutional_design import (
    N_INSTITUTIONAL_POINTS,
    PARAMETER_SPACE,
    build_config_for_point,
    build_design,
    design_hash,
    run_secondary_validation,
)


class TestDesignGeneration:
    def test_at_least_twenty_one_dimensions_swept(self):
        assert len(PARAMETER_SPACE) >= 21

    def test_no_duplicate_field_names(self):
        names = [n for n, _, _ in PARAMETER_SPACE]
        assert len(names) == len(set(names))

    def test_design_has_explicit_point_count(self):
        design = build_design()
        assert design["n_institutional_points"] == N_INSTITUTIONAL_POINTS
        assert len(design["points"]) == N_INSTITUTIONAL_POINTS

    def test_no_packages_no_resemblance_selection(self):
        design = build_design()
        assert design["n_packages"] == 0
        assert design["selection_method"] == "space_filling_latin_hypercube_no_resemblance_based_selection"

    def test_deterministic(self):
        d1 = build_design()
        d2 = build_design()
        assert d1 == d2
        assert design_hash(d1) == design_hash(d2)

    def test_every_dimension_varies_independently_across_points(self):
        # No two dimensions must be perfectly correlated across points --
        # a crude but effective "these are not secretly bundled into a
        # package" check (a real package would show 1.0 correlation
        # between every pair of its own bundled dimensions).
        design = build_design()
        import numpy as np

        names = [n for n, _, _ in PARAMETER_SPACE]
        matrix = np.array([[p["institutional_parameters"][n] for n in names] for p in design["points"]])
        corr = np.corrcoef(matrix, rowvar=False)
        n = len(names)
        off_diagonal = [corr[i, j] for i in range(n) for j in range(n) if i != j]
        assert all(abs(c) < 0.9 for c in off_diagonal), "two dimensions appear bundled (|corr| >= 0.9)"


class TestConfigBuilding:
    def test_builds_valid_config_for_every_point(self):
        design = build_design()
        for point in design["points"][:5]:
            config = build_config_for_point(point, seed=1)
            assert config.rng_mode == "mechanism_substreams"

    def test_ecological_parameters_fixed_across_points(self):
        design = build_design()
        configs = [build_config_for_point(p, seed=1) for p in design["points"][:5]]
        regen_rates = {c.patch_regen_rate for c in configs}
        assert len(regen_rates) == 1  # Section 8's own ecology-held-fixed design

    def test_institutional_parameters_vary_across_points(self):
        design = build_design()
        configs = [build_config_for_point(p, seed=1) for p in design["points"][:5]]
        thresholds = {c.preferred_adoption_threshold_mean for c in configs}
        assert len(thresholds) > 1

    def test_coordination_window_steps_rounded_to_int(self):
        design = build_design()
        config = build_config_for_point(design["points"][0], seed=1)
        assert isinstance(config.coordination_proposal_window_steps, int)


class TestSecondaryValidation:
    """Section 8: 'use the audited Level 1.1b classifier only for
    secondary validation' -- diagnostic only, never filtering."""

    def test_runs_and_returns_label_distributions(self):
        design = build_design()
        result = run_secondary_validation(design, n_seeds=1)
        assert result["n_rules_classified"] > 0
        assert isinstance(result["historical_label_distribution"], dict)
        assert isinstance(result["audited_label_distribution"], dict)

    def test_never_filters_design_points(self):
        # run_secondary_validation must not mutate or return a filtered
        # design -- it takes the design as read-only input.
        design = build_design()
        original_n_points = len(design["points"])
        run_secondary_validation(design, n_seeds=1)
        assert len(design["points"]) == original_n_points

    def test_downgraded_count_never_negative(self):
        design = build_design()
        result = run_secondary_validation(design, n_seeds=1)
        assert result["n_downgraded_historical_to_audited"] >= 0
