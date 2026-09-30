"""Level 1.2: sanity tests for experiments/level12_common.py's shared summarizer."""

from __future__ import annotations

from abm_governance.core.config import SimulationConfig
from abm_governance.observer.institutional_viability import ALL_OUTCOME_LABELS
from experiments.level12_common import (
    LEVEL12_EVENT_LOG_ATTRS,
    build_rule_by_patch,
    compute_eligibility,
    compute_phenotype_vector,
    run_and_summarize,
)


class TestRunAndSummarize:
    def test_bare_default_config_produces_all_gated_counters_zero(self):
        config = SimulationConfig(population_size=20, n_steps=20, seed=1)
        out = run_and_summarize(config)
        for attr in LEVEL12_EVENT_LOG_ATTRS:
            assert out[f"n_{attr}"] == 0

    def test_returns_a_valid_all_outcome_label(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=30, n_patches=2, seed=2,
        )
        out = run_and_summarize(config)
        assert out["all_outcome_label"] in ALL_OUTCOME_LABELS

    def test_institution_counts_are_non_negative_and_consistent(self):
        config = SimulationConfig.level1_rule_formation_default(
            population_size=20, n_steps=30, n_patches=2, seed=3,
        )
        out = run_and_summarize(config)
        assert out["n_institutions_ever_formed"] >= out["n_institutions_active_at_end"] >= 0

    def test_return_sim_true_yields_tuple(self):
        config = SimulationConfig.level1_rule_formation_default(population_size=20, n_steps=20, n_patches=2, seed=4)
        result = run_and_summarize(config, return_sim=True)
        assert isinstance(result, tuple) and len(result) == 2
        summary, sim = result
        assert isinstance(summary, dict)
        assert sim.config is config


class TestPhenotypeAndEligibilityHelpers:
    def _run(self, seed=5):
        config = SimulationConfig.level11_complete(population_size=20, n_steps=40, n_patches=2, seed=seed)
        return config, *run_and_summarize(config, return_sim=True)

    def test_build_rule_by_patch_covers_every_patch_with_history(self):
        config, summary, sim = self._run()
        rule_by_patch = build_rule_by_patch(sim)
        assert set(rule_by_patch.keys()) <= set(sim.patch_system.patches.keys())

    def test_compute_phenotype_vector_returns_all_ten_dimensions(self):
        config, summary, sim = self._run()
        vector = compute_phenotype_vector(sim, config)
        assert set(vector.keys()) == {"C", "E", "L", "D", "M", "R", "S", "F", "V", "H"}

    def test_compute_eligibility_returns_eligible_and_reasons(self):
        config, summary, sim = self._run()
        vector = compute_phenotype_vector(sim, config)
        result = compute_eligibility(sim, config, vector, summary)
        assert "eligible" in result and "reasons" in result
