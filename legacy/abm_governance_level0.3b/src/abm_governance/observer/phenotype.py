"""Provisional behavioural-phenotype representation (Level 0.1, Work
Package D).

Policy *names* (``tit_for_tat``, ``grim``, ...) are convenient labels, but
the milestone brief asks whether parametrically or genetically different
policies might produce similar observable behaviour — a question names
alone can't answer. This module runs each policy *type* against a small
set of standardized test histories (not live interaction) and records the
action it takes in each, producing a fixed-length "phenotype" vector that
can be compared across policies independently of their names.

This is explicitly observer-side and provisional:

* It is descriptive bookkeeping over policy *types*, computed off-line
  against synthetic histories — it never runs during, or influences, the
  generative simulation loop.
* At Level 0.1, every agent using a given policy *name* is behaviourally
  identical (policies have no per-agent-tunable parameters yet — see
  ``agents/policy.py``), so phenotype distance here is really a
  distance between the 6 policy *types*, not yet a per-agent
  measurement. This is a known limitation, not an oversight: per-agent
  parametric policy variation is a natural extension for a later
  milestone, at which point this module's ``behavioral_phenotype``
  function should be called per-agent instead of per-type.
* No political or governance-style names are attached to phenotypes.
"""

from __future__ import annotations

import numpy as np

from abm_governance.agents.policy import VALID_POLICY_NAMES, make_policy
from abm_governance.interactions.game import COOPERATE, DEFECT

#: A small, fixed battery of "what has the partner done so far" test
#: histories, oldest-first. Deliberately short and simple — this is a
#: coarse behavioural fingerprint, not a full strategy characterization.
STANDARD_TEST_HISTORIES: tuple[tuple[int, ...], ...] = (
    (),  # first move (no history)
    (COOPERATE,),
    (DEFECT,),
    (COOPERATE, COOPERATE),
    (COOPERATE, DEFECT),
    (DEFECT, COOPERATE),
    (DEFECT, DEFECT),
)

#: Fixed seed for any stochastic policy (e.g. RandomPolicy,
#: GenerousTitForTat's forgiveness draw) so phenotypes are themselves
#: reproducible test artifacts, not a new source of run-to-run noise.
_PHENOTYPE_RNG_SEED = 12345


def behavioral_phenotype(policy_name: str, rng_seed: int = _PHENOTYPE_RNG_SEED) -> tuple[int, ...]:
    """The action (COOPERATE/DEFECT) a fresh instance of ``policy_name``
    takes against each of :data:`STANDARD_TEST_HISTORIES`, in order."""
    policy = make_policy(policy_name)
    rng = np.random.default_rng(rng_seed)
    return tuple(int(policy.decide(list(h), rng)) for h in STANDARD_TEST_HISTORIES)


def phenotype_distance(name_a: str, name_b: str, rng_seed: int = _PHENOTYPE_RNG_SEED) -> float:
    """Normalized Hamming distance (fraction of test situations in which
    the two policies disagree) between two policy types' phenotypes.
    0.0 = behaviourally identical on this test battery; 1.0 = disagree on
    every test situation."""
    a = behavioral_phenotype(name_a, rng_seed)
    b = behavioral_phenotype(name_b, rng_seed)
    return sum(1 for x, y in zip(a, b) if x != y) / len(a)


def pairwise_distance_matrix(
    policy_names: tuple[str, ...] = VALID_POLICY_NAMES, rng_seed: int = _PHENOTYPE_RNG_SEED
) -> dict[tuple[str, str], float]:
    """All pairwise phenotype distances among ``policy_names``."""
    return {
        (a, b): phenotype_distance(a, b, rng_seed) for a in policy_names for b in policy_names
    }
