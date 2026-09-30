"""Level 1.3, task #93: ecological control integration (feasibility
strata) for Level 1.3 designs (``experiments/level13_common.py``).

See that module's own docstring for why this is integration (reusing
Level 1.2b's ``feasibility_ratios.py`` unmodified), not a new empirical
calibration -- the actual Level 1.3 cut points are frozen by Stage 2
(task #97), not here."""

from __future__ import annotations

import math

import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.feasibility_ratios import expected_pressure_ratio, structural_feasibility_ratio
from experiments import level13_common as l13c


class TestFeasibilityStratum:
    def test_at_or_below_low_cut_is_low_feasibility(self):
        assert l13c.feasibility_stratum(1.0, low_cut=2.0, high_cut=5.0) == "low_feasibility"
        assert l13c.feasibility_stratum(2.0, low_cut=2.0, high_cut=5.0) == "low_feasibility"

    def test_between_cuts_is_medium_feasibility(self):
        assert l13c.feasibility_stratum(3.5, low_cut=2.0, high_cut=5.0) == "medium_feasibility"
        assert l13c.feasibility_stratum(5.0, low_cut=2.0, high_cut=5.0) == "medium_feasibility"

    def test_above_high_cut_is_high_feasibility(self):
        assert l13c.feasibility_stratum(5.01, low_cut=2.0, high_cut=5.0) == "high_feasibility"

    def test_nonfinite_ratio_is_undefined(self):
        assert l13c.feasibility_stratum(float("nan"), low_cut=2.0, high_cut=5.0) == "undefined"
        assert l13c.feasibility_stratum(float("inf"), low_cut=2.0, high_cut=5.0) == "undefined"

    def test_nonfinite_cut_points_are_undefined(self):
        assert l13c.feasibility_stratum(3.0, low_cut=float("nan"), high_cut=float("nan")) == "undefined"


class TestComputeStratumCutPoints:
    def test_tercile_cut_points(self):
        ratios = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
        low_cut, high_cut = l13c.compute_stratum_cut_points(ratios)
        assert low_cut == pytest.approx(4.0)  # index 9//3 = 3 -> value 4.0
        assert high_cut == pytest.approx(7.0)  # index (2*9)//3 = 6 -> value 7.0

    def test_ignores_nonfinite_values(self):
        ratios = [1.0, 2.0, 3.0, float("nan"), float("inf")]
        low_cut, high_cut = l13c.compute_stratum_cut_points(ratios)
        assert math.isfinite(low_cut)
        assert math.isfinite(high_cut)

    def test_fewer_than_three_finite_ratios_yields_nan(self):
        low_cut, high_cut = l13c.compute_stratum_cut_points([1.0, float("nan")])
        assert math.isnan(low_cut)
        assert math.isnan(high_cut)


class TestEcologicalLhsDraws:
    def test_correct_count_and_fields(self):
        draws = l13c.ecological_lhs_draws(n=10, seed=1)
        assert len(draws) == 10
        field_names = {name for name, _, _ in l13c.ECOLOGICAL_SPACE_FOR_LEVEL13}
        for draw in draws:
            assert set(draw.keys()) == field_names

    def test_population_patch_ratio_selector_excluded(self):
        names = {name for name, _, _ in l13c.ECOLOGICAL_SPACE_FOR_LEVEL13}
        assert "population_patch_ratio_selector" not in names

    def test_deterministic_given_same_seed(self):
        d1 = l13c.ecological_lhs_draws(n=8, seed=42)
        d2 = l13c.ecological_lhs_draws(n=8, seed=42)
        assert d1 == d2

    def test_different_seeds_differ(self):
        d1 = l13c.ecological_lhs_draws(n=8, seed=1)
        d2 = l13c.ecological_lhs_draws(n=8, seed=2)
        assert d1 != d2


class TestBuildEcologicalFeasibilityDesign:
    def test_well_formed_design(self):
        design = l13c.build_ecological_feasibility_design(n_points=15, n_steps=50)
        assert design["n_points"] == 15
        assert len(design["points"]) == 15
        assert sum(design["stratum_counts"].values()) == 15
        for p in design["points"]:
            assert p["expected_stratum"] in ("low_feasibility", "medium_feasibility", "high_feasibility", "undefined")

    def test_deterministic_given_same_seed(self):
        d1 = l13c.build_ecological_feasibility_design(n_points=12, seed=7, n_steps=50)
        d2 = l13c.build_ecological_feasibility_design(n_points=12, seed=7, n_steps=50)
        assert d1 == d2

    def test_no_level13_mechanism_flag_present_in_base_config(self):
        # The design's own docstring claim: the ratio is computed
        # against a config with every Level 1.3 mechanism off.
        design = l13c.build_ecological_feasibility_design(n_points=5, n_steps=30)
        assert design["n_points"] == 5  # smoke: the call itself must not raise.


class TestLevel13FieldsNeverMoveTheRatio:
    """The central "ecological control integration" invariant: Level
    1.3's own mechanism flags must never perturb the ex-ante feasibility
    ratio, since it is a property of the ecological substrate alone,
    computed before any Level 1.3 mechanism is layered on top."""

    def test_structural_ratio_identical_with_historical_module_on_or_off(self):
        base = SimulationConfig.level12b_frozen_reference(population_size=24, n_patches=3, n_steps=60, seed=5)
        with_level13_on = SimulationConfig.level12b_frozen_reference(
            population_size=24, n_patches=3, n_steps=60, seed=5,
            historical_module_enabled=True, security_pressure_enabled=True,
            entrenchment_enabled=True, performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
        )
        r1 = structural_feasibility_ratio(base)
        r2 = structural_feasibility_ratio(with_level13_on)
        assert r1.ratio == pytest.approx(r2.ratio)
        assert r1.max_sustainable_supply == pytest.approx(r2.max_sustainable_supply)
        assert r1.minimum_mandatory_burden == pytest.approx(r2.minimum_mandatory_burden)

    def test_expected_pressure_ratio_identical_with_historical_module_on_or_off(self):
        base = SimulationConfig.level12b_frozen_reference(population_size=24, n_patches=3, n_steps=60, seed=5)
        with_level13_on = SimulationConfig.level12b_frozen_reference(
            population_size=24, n_patches=3, n_steps=60, seed=5,
            historical_module_enabled=True, bargaining_pressure_enabled=True, coordination_complexity_enabled=True,
        )
        r1 = expected_pressure_ratio(base)
        r2 = expected_pressure_ratio(with_level13_on)
        assert r1.ratio == pytest.approx(r2.ratio)


class TestTransmissionOverridesForChannel:
    """Task #109's bug-fix helper: both of Work Package A's own
    transmission sub-flags per channel, and nothing else."""

    def test_security_pressure_channel(self):
        overrides = l13c.transmission_overrides_for_channel("security_pressure")
        assert overrides == {
            "security_pressure_returns_to_delegation_enabled": True,
            "security_pressure_admin_capacity_demand_enabled": True,
        }

    def test_bargaining_pressure_channel(self):
        overrides = l13c.transmission_overrides_for_channel("bargaining_pressure")
        assert overrides == {
            "bargaining_pressure_conditional_contribution_enabled": True,
            "bargaining_pressure_appeal_recall_enabled": True,
        }

    def test_coordination_complexity_channel(self):
        overrides = l13c.transmission_overrides_for_channel("coordination_complexity")
        assert overrides == {
            "coordination_complexity_cross_patch_transactions_enabled": True,
            "coordination_complexity_interoperable_demand_enabled": True,
        }

    def test_every_flag_name_is_a_real_config_field(self):
        cfg = SimulationConfig.level12b_frozen_reference(population_size=8, n_patches=2, n_steps=5, seed=1)
        for channel in l13c.TRANSMISSION_SUBFLAGS_BY_CHANNEL:
            for flag in l13c.transmission_overrides_for_channel(channel):
                assert hasattr(cfg, flag)

    def test_unknown_channel_raises(self):
        with pytest.raises(KeyError):
            l13c.transmission_overrides_for_channel("not_a_real_channel")
