"""Level 1.3, Work Package H (Section 13): outcome-blind phenotype
discovery, repeated for Level 1.3 (``observer/level13_phenotype.py``).

See that module's own docstring for the context-loss disclosure and
the "repeat for Level 1.3" reading (new feature vector, unmodified
existing clustering pipeline) this work package's tests are built on."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from abm_governance.core.config import SimulationConfig
from abm_governance.observer import level13_phenotype as l13p
from abm_governance.observer import phenotype_discovery as pd
from abm_governance.rules.shared_rule import RuleParameters, SharedRule
from abm_governance.simulation import Simulation


def _rule(rule_id=0, patch_id=0, founding_step=0, active=True, performance_legitimacy=0.0, procedural_legitimacy=0.0):
    params = RuleParameters(
        extraction_ceiling=0.3, maintenance_requirement=0.4, monitoring_intensity=0.5,
        sanction_magnitude=0.5, adoption_threshold=0.5, amendment_threshold=0.5,
    )
    r = SharedRule(
        rule_id=rule_id, patch_id=patch_id, parameters=params, founding_step=founding_step,
        founder_id=0, rule_lineage_id=rule_id, members=frozenset({0, 1}), supporters=frozenset({0, 1}),
    )
    r.active = active
    r.performance_legitimacy = performance_legitimacy
    r.procedural_legitimacy = procedural_legitimacy
    return r


class TestDimensionKeys:
    def test_fourteen_dimensions(self):
        assert len(l13p.LEVEL13_DIMENSION_KEYS) == 14

    def test_eight_sequencing_plus_six_others(self):
        seq_keys = [k for k in l13p.LEVEL13_DIMENSION_KEYS if k.startswith("seq_")]
        assert len(seq_keys) == 8
        assert set(l13p.LEVEL13_DIMENSION_KEYS) - set(seq_keys) == {
            "entrenchment", "performance_legitimacy", "procedural_legitimacy",
            "conversion_incidence", "S_obs", "Z_obs",
        }


class TestLevel13PhenotypeVector:
    def test_returns_every_declared_dimension(self):
        from abm_governance.core.events import EventLog
        vec = l13p.level13_phenotype_vector(EventLog(), {}, n_steps=50, current_step=50, entrenchment_maturation_steps=100)
        assert set(vec.keys()) == set(l13p.LEVEL13_DIMENSION_KEYS)
        for key in l13p.LEVEL13_DIMENSION_KEYS:
            assert "value" in vec[key]
            assert "construct_type" in vec[key]

    def test_no_active_rules_yields_nan_snapshot_dimensions(self):
        from abm_governance.core.events import EventLog
        vec = l13p.level13_phenotype_vector(EventLog(), {}, n_steps=50, current_step=50, entrenchment_maturation_steps=100)
        assert np.isnan(vec["entrenchment"]["value"])
        assert np.isnan(vec["performance_legitimacy"]["value"])
        assert np.isnan(vec["procedural_legitimacy"]["value"])

    def test_active_rules_produce_finite_snapshot_dimensions(self):
        from abm_governance.core.events import EventLog
        rule_by_patch = {0: _rule(founding_step=0, performance_legitimacy=0.6, procedural_legitimacy=0.4)}
        vec = l13p.level13_phenotype_vector(EventLog(), rule_by_patch, n_steps=50, current_step=50, entrenchment_maturation_steps=100)
        assert vec["performance_legitimacy"]["value"] == pytest.approx(0.6)
        assert vec["procedural_legitimacy"]["value"] == pytest.approx(0.4)
        assert 0.0 <= vec["entrenchment"]["value"] <= 1.0

    def test_inactive_rule_excluded_from_snapshot_mean(self):
        from abm_governance.core.events import EventLog
        rule_by_patch = {
            0: _rule(rule_id=0, founding_step=0, performance_legitimacy=1.0),
            1: _rule(rule_id=1, founding_step=0, active=False, performance_legitimacy=0.0),
        }
        vec = l13p.level13_phenotype_vector(EventLog(), rule_by_patch, n_steps=50, current_step=50, entrenchment_maturation_steps=100)
        assert vec["performance_legitimacy"]["value"] == pytest.approx(1.0)  # only the active rule counted.

    def test_sequencing_dimensions_are_fractions_or_nan(self):
        from abm_governance.core.events import EventLog
        vec = l13p.level13_phenotype_vector(EventLog(), {}, n_steps=50, current_step=50, entrenchment_maturation_steps=100)
        for name in ("seq_delegation", "seq_monitoring", "seq_accountability"):
            assert np.isnan(vec[name]["value"])  # no events at all -> never crosses threshold.


def _finished_sim(seed, **overrides):
    config = SimulationConfig.level1_rule_formation_default(
        population_size=30, n_steps=150, n_patches=2, seed=seed,
        monitoring_mode="voluntary", sanction_mode="voluntary",
        **overrides,
    )
    sim = Simulation(config)
    sim.run()
    return sim, config


class TestEndToEndOnARealRun:
    def test_vector_from_a_real_run_is_well_formed(self):
        sim, config = _finished_sim(seed=17, performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True)
        vec = l13p.level13_phenotype_vector(
            sim.event_log, sim.rule_registry, n_steps=config.n_steps, current_step=config.n_steps,
            entrenchment_maturation_steps=100,
        )
        for key in l13p.LEVEL13_DIMENSION_KEYS:
            value = vec[key]["value"]
            assert isinstance(value, float)
            if not np.isnan(value):
                assert -1e-9 <= value <= 1.0 + 1e-9

    def test_feeds_directly_into_the_unmodified_clustering_pipeline(self):
        # The whole point of Work Package H's "repeat for Level 1.3"
        # reading: this module's output must work with
        # phenotype_discovery.py's EXISTING, unmodified generic
        # functions, with zero special-casing added there.
        records = []
        for seed in (1, 2, 3, 4, 5, 6):
            sim, config = _finished_sim(seed=seed)
            vec = l13p.level13_phenotype_vector(
                sim.event_log, sim.rule_registry, n_steps=config.n_steps, current_step=config.n_steps,
                entrenchment_maturation_steps=100,
            )
            records.append(vec)

        X, feature_names = pd.build_feature_matrix(records, l13p.LEVEL13_DIMENSION_KEYS)
        assert X.shape == (6, 14)
        assert feature_names == list(l13p.LEVEL13_DIMENSION_KEYS)

        report = pd.missingness_report(X, feature_names)
        assert set(report.keys()) == set(feature_names)

        # A handful of the rarer institutional-response dimensions (e.g.
        # bargaining_participation, cross_founder_reconstruction) can
        # legitimately be all-NaN across just 6 short pilot seeds --
        # preprocess_features's mean_impute strategy already documents
        # and handles this (falls back to a 0.0 column mean), but
        # np.nanmean itself still raises "Mean of empty slice" as a
        # RuntimeWarning for that column. This is a pre-existing,
        # already-handled characteristic of the frozen pipeline, not a
        # defect this new module introduces -- suppressed locally rather
        # than papered over globally.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            processed = pd.preprocess_features(X, X, strategy="mean_impute")
        assert processed["X_train"].shape[0] == 6

        results = pd.compare_k_range(processed["X_train"], method="gmm", k_range=(1, 2, 3))
        assert len(results) == 3
        for r in results:
            assert "k" in r and "labels" in r
