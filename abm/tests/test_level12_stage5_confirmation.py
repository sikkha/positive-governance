"""Level 1.2, Stage 5: prospective confirmation (fresh seeds)."""

from __future__ import annotations

import importlib
import inspect

from experiments import level12_stage3_search as stage3
from experiments import level12_stage5_confirmation as stage5
from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments


class TestFreshSeedsNeverCollideWithStage3:
    def test_seed_base_disjoint_from_stage3_range(self):
        draws = stage3.build_parameter_draws()
        stage3_seeds = {4000 + d * 100 + s for d in range(len(draws)) for s in range(stage3.N_SEEDS_PER_DRAW)}
        fresh_seeds = {stage5.SEED_BASE + d for d in range(len(draws))}
        assert stage3_seeds.isdisjoint(fresh_seeds)

    def test_fresh_pool_reuses_stage3_parameter_draws(self):
        # Same fixed LHS seed -- draw-for-draw parameter correspondence
        # is the whole point of this stage's design (see module docstring).
        assert stage3.build_parameter_draws() == stage3.build_parameter_draws()


class TestForbiddenTerminologyGuardExtendsToStage5Script:
    def test_stage5_module_free_of_forbidden_terms(self):
        module = importlib.import_module("experiments.level12_stage5_confirmation")
        source = inspect.getsource(module)
        cleaned = _strip_docstrings_and_comments(source).lower()
        offenders = [
            term for term in FORBIDDEN_LEVEL12_TERMS
            if term in cleaned or term.replace("_", " ") in cleaned
        ]
        assert offenders == []
