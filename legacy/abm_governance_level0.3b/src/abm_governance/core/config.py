"""Configuration for a Level 0 (atomic relational ecology) run.

All parameters that affect stochastic behaviour must be explicit fields
here — nothing is read from module-level globals or environment variables
at simulation time. Validation is strict: invalid configurations raise
``ValueError`` immediately rather than being silently clamped, so a typo in
a sweep specification fails loudly instead of quietly producing meaningless
results.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Mapping

import yaml

#: Allowed Level-0 policy names. Kept as an explicit whitelist so that a
#: config file cannot silently request a policy that does not exist.
VALID_POLICIES = (
    "always_cooperate",
    "always_defect",
    "tit_for_tat",
    "generous_tit_for_tat",
    "grim",
    "random",
)

VALID_TOPOLOGIES = ("erdos_renyi", "watts_strogatz", "regular")

#: Perturbation kinds. The first two are Level 0.1's original minimal pair;
#: "subsistence_increase" and "regeneration_reduction" are added at Level
#: 0.2, Work Package J, to give the boundary-region perturbation experiment
#: more than one demand-side/supply-side shock to choose from (the
#: milestone brief names both as example shocks). Deliberately small and
#: generic — no political interpretation is attached to any of them; see
#: core/perturbation.py.
VALID_PERTURBATION_KINDS = (
    "resource_depletion",
    "observation_noise_increase",
    "subsistence_increase",
    "regeneration_reduction",
)

#: Level 0.2, Work Package B: agent viability modes. "none" reproduces
#: Level 0.1 exactly (no demographic consequence of resource failure ever).
VALID_VIABILITY_MODES = ("none", "dormancy_recovery", "removal_replacement")

#: Level 0.2, Work Package B: what a replacement agent (removal_replacement
#: mode only) starts with. Defaults to "random_init" — a fresh draw from
#: policy_mix and the ordinary trait distributions, exactly like an
#: initial-population agent — deliberately NOT the population's current
#: dominant policy, per the milestone's explicit instruction.
VALID_REPLACEMENT_POLICIES = ("random_init", "dominant_policy", "parent_lineage_imitation", "mutation_fresh")

#: Level 0.2, Work Package C: the imitation fitness signal. None of these
#: is asserted "correct" in advance — see docs/level0.2_scientific_note.md.
VALID_FITNESS_MODES = ("cumulative_resources", "recent_payoff", "resource_delta", "viability_adjusted")

#: Level 0.3, Work Package A: spatial resource topology. "global_pool" is
#: the exact Level-0.2-compatible default (see environment/resource_pool.py,
#: untouched). "patches" activates environment/patches.py and, with it,
#: the entire ecological-action apparatus (Work Packages B-D).
VALID_ECOLOGY_TOPOLOGIES = ("global_pool", "patches")

#: Level 0.3, Work Package A: neutral patch-membership assignment rules —
#: see environment/patches.py's module docstring. Never a function of any
#: agent's policy or resources.
VALID_PATCH_ASSIGNMENT_MODES = ("network_neighborhood", "random_assignment")

#: Level 0.3, Work Package B: how excess ecological-extraction demand
#: (patch-level, simultaneous requests from every member) is rationed
#: when it exceeds the patch's current stock.
VALID_ECOLOGICAL_ALLOCATION_RULES = ("proportional", "sequential_random")

#: Level 0.3, Work Package D: how the two behavioral dimensions'
#: inheritance is coupled (or not) during the adaptation round. Neither
#: is asserted the "correct" choice — both are experimentally comparable.
VALID_ECOLOGICAL_INHERITANCE_MODES = ("independent", "coupled_same_model")


@dataclass(frozen=True)
class SimulationConfig:
    # --- population -----------------------------------------------------
    population_size: int = 60
    n_steps: int = 500

    # --- initial policy mix ---------------------------------------------
    # Fractions of the initial population assigned each policy; must be
    # non-negative and sum to (approximately) 1.0.
    policy_mix: Mapping[str, float] = field(
        default_factory=lambda: {
            "always_cooperate": 0.2,
            "always_defect": 0.2,
            "tit_for_tat": 0.3,
            "generous_tit_for_tat": 0.15,
            "grim": 0.1,
            "random": 0.05,
        }
    )

    # --- heterogeneous trait distributions (mean, std), clipped to valid ranges --
    observation_accuracy_mean: float = 0.9
    observation_accuracy_std: float = 0.05
    learning_rate_mean: float = 0.1
    learning_rate_std: float = 0.03
    forgiveness_mean: float = 0.1  # memory-decay / forgiveness rate, in [0, 1]
    forgiveness_std: float = 0.05
    risk_sensitivity_mean: float = 0.5
    risk_sensitivity_std: float = 0.15

    initial_resources_mean: float = 10.0
    initial_resources_std: float = 2.0
    initial_coercive_capability_mean: float = 1.0
    initial_coercive_capability_std: float = 0.3

    memory_length: int = 10  # max remembered interactions per partner

    # --- network ----------------------------------------------------------
    topology: str = "watts_strogatz"
    mean_degree: int = 4          # target average degree
    rewiring_prob: float = 0.1    # only used for watts_strogatz

    # --- interaction payoff grammar (iterated prisoner's dilemma) --------
    payoff_temptation: float = 5.0   # T: defect against cooperator
    payoff_reward: float = 3.0       # R: mutual cooperation
    payoff_punishment: float = 1.0   # P: mutual defection
    payoff_sucker: float = 0.0       # S: cooperate against defector

    # --- costly punishment (optional) -------------------------------------
    punishment_enabled: bool = True
    punishment_probability: float = 0.3  # chance a wronged cooperator punishes
    punishment_cost: float = 1.0         # cost paid by the punisher
    punishment_penalty: float = 3.0      # resources deducted from the punished

    # --- exit / rewiring ----------------------------------------------------
    exit_cost: float = 1.0
    exit_resource_threshold: float = -2.0  # net recent payoff below which exit is considered

    # --- adaptation timescales --------------------------------------------
    imitation_period: int = 10   # steps between imitation rounds
    mutation_rate: float = 0.01  # per-agent probability of random policy mutation per imitation round
    rewiring_period: int = 5     # steps between exit/rewiring rounds
    interactions_per_step: int = 1  # bilateral encounters sampled per edge per step

    # --- ecological closure (Level 0.1, Work Package A) ---------------------
    # Master switch. When False, interaction payoffs are credited directly to
    # agents exactly as in Level 0 — no environment pool, no subsistence, no
    # distress-driven withholding. This is the "Level-0 compatibility mode"
    # (see `SimulationConfig.level0_compat`) used for regression testing
    # against pre-Level-0.1 runs; with it False, ecology consumes zero extra
    # RNG draws and the original unbounded resource dynamics are exact.
    ecology_enabled: bool = True
    #: K — carrying capacity of the shared environmental resource pool.
    environment_capacity: float = 2000.0
    #: r — logistic regeneration rate applied once per step, after that
    #: step's extraction: R_{t+1} = clip(R_t' + r * R_t' * (1 - R_t'/K), 0, K)
    #: where R_t' = R_t minus that step's extraction. See
    #: environment/resource_pool.py for the full derivation and rationale.
    environment_regen_rate: float = 0.5
    #: Pool starts at this fraction of K (0 = empty, 1 = pristine/full).
    environment_initial_fraction: float = 0.5
    #: Per-agent, per-step upkeep charge, paid unconditionally out of the
    #: agent's own resources (not pool-linked — see project_vision.md's
    #: documented simplification that subsistence is a sink out of the
    #: agent economy, not recycled into the environment pool at this level).
    subsistence_cost: float = 0.3
    #: An agent whose resources are below this value at the *start* of a
    #: step is "distressed" for that whole step (status is a per-step
    #: snapshot, not re-evaluated mid-step, for determinism).
    distress_threshold: float = 0.0
    #: Probability a distressed agent still engages in a given scheduled
    #: interaction this step (independently drawn per edge); the complement
    #: is a "withhold" event: reduced interaction capacity, not death.
    distress_engagement_prob: float = 0.5

    # --- endogenous relationship dynamics (Level 0.1, Work Package B) ------
    # Master switch. When False, exit/rewiring uses the original Level-0
    # logic exactly (unconditional exit below exit_resource_threshold, blind
    # single-shot edge addition up to mean_degree, no accept/reject, no
    # failed-exit accounting, no search cost) — the other half of the
    # Level-0 compatibility mode.
    relationship_dynamics_enabled: bool = True
    #: Cost paid by the proposer for each connection attempt, win or lose.
    search_cost: float = 0.2
    #: Baseline probability a target accepts a connection proposal before
    #: the local degree-saturation adjustment described in
    #: network/graph.py::decide_connection_acceptance.
    connection_accept_base_prob: float = 0.7
    #: When ``relationship_dynamics_enabled`` is True, this sub-switch lets
    #: voluntary exit specifically be turned off while connection formation
    #: stays active — used by Work Package E's "no relationship exit"
    #: ablation. Has no effect in compat mode (which uses its own legacy
    #: exit logic unconditionally). Consumes no RNG draws either way, so
    #: toggling it does not perturb the draw sequence of anything else.
    relationship_exit_enabled: bool = True

    # --- adaptation sub-switch (Level 0.1, Work Package E ablations) -------
    #: Lets imitation specifically be disabled while mutation stays active
    #: — used by the "no imitation" ablation. True reproduces the original
    #: Level-0 behaviour exactly (imitation always ran unconditionally).
    imitation_enabled: bool = True

    # --- perturbations (Level 0.1, Work Package G) --------------------------
    # A tuple of perturbation specs (see core/perturbation.py), each a
    # mapping with keys {start_step, duration, kind, magnitude}. Empty by
    # default — perturbations are opt-in per experiment, never implicit.
    perturbations: tuple = field(default_factory=tuple)

    # --- viability state machine (Level 0.2, Work Package B) ----------------
    # "none" is the Level-0.1-compatible default: resources may go arbitrarily
    # negative with zero demographic consequence (see
    # dev_mem/status_update.md's session-3-start entry for why this was
    # identified as an untested candidate explanation for Level 0.1's
    # near-universal cooperation result). Has NO effect at all — consumes
    # zero extra RNG draws, no state transitions computed — unless
    # ecology_enabled is also True (viability is defined in terms of
    # resource deficit against subsistence, which only exists under ecology).
    viability_mode: str = "none"
    #: Consecutive steps an agent's resources must stay below
    #: `distress_threshold` before it transitions distressed -> dormant.
    #: Cumulative/duration-based, not a one-step trigger, per the milestone's
    #: explicit instruction.
    viability_deficit_steps_threshold: int = 20
    #: Resources threshold (>= this) required to transition dormant ->
    #: recovered (active). Deliberately a separate field from
    #: distress_threshold (not reused) so the recovery bar can be set with
    #: hysteresis above the distress bar, avoiding immediate re-flicker.
    viability_recovery_resources: float = 0.0
    #: Steps an agent may remain dormant before it is (in
    #: removal_replacement mode) marked nonviable and removed. In
    #: dormancy_recovery mode this is advisory bookkeeping only (dormant
    #: agents may remain dormant indefinitely; nothing removes them) —
    #: still recorded so the two modes are comparable on this axis.
    viability_max_dormant_steps: int = 50
    #: removal_replacement only: what a fresh replacement agent starts with.
    viability_replacement_policy: str = "random_init"

    # --- imitation fitness signal (Level 0.2, Work Package C) ---------------
    #: "cumulative_resources" reproduces Level 0.1's Fermi-rule-over-total-
    #: resources exactly (the default, for compatibility).
    fitness_mode: str = "cumulative_resources"
    #: Rolling-window length (in steps) for the recent_payoff and
    #: resource_delta fitness signals.
    fitness_window: int = 20
    #: viability_adjusted mode only: fixed penalty subtracted from a dormant
    #: agent's recent_payoff-based fitness signal (kept finite, not -inf, so
    #: the Fermi rule stays well-defined) — makes a dormant agent's strategy
    #: very unlikely, but not impossible, to be imitated.
    viability_adjusted_dormant_penalty: float = 10.0

    # --- local ecological patches (Level 0.3, Work Package A) ---------------
    #: Master spatial-topology switch. "global_pool" (default) is an exact
    #: Level-0.2-compatible no-op: environment/patches.py is never touched,
    #: consumes zero extra RNG draws. "patches" activates a fixed
    #: collection of independent ResourcePatch objects and, with it, the
    #: entire ecological-action apparatus (Work Packages B-D) — only
    #: meaningful when ecology_enabled is also True.
    ecology_topology: str = "global_pool"
    #: Number of independent patches when ecology_topology="patches".
    n_patches: int = 4
    #: K_j — per-patch carrying capacity (all patches share this nominal
    #: capacity; per-patch productivity heterogeneity is expressed via
    #: patch_quality_std instead of varying capacity directly).
    patch_capacity: float = 500.0
    #: r_j (nominal) — per-patch logistic regeneration rate, before the
    #: patch's own quality multiplier.
    patch_regen_rate: float = 0.5
    #: Each patch starts at this fraction of patch_capacity.
    patch_initial_fraction: float = 0.5
    #: Standard deviation of each patch's productivity multiplier, drawn
    #: once at initialization from Normal(1.0, patch_quality_std), clipped
    #: to a small positive floor. 0.0 (default) => every patch has
    #: identical quality 1.0 (a neutral no-op).
    patch_quality_std: float = 0.0
    #: Neutral rule assigning each agent to exactly one patch, once, at
    #: initialization (never migrates — see environment/patches.py).
    patch_assignment_mode: str = "network_neighborhood"

    # --- ecological policy / niche construction (Level 0.3, WP-B/C) --------
    # Only read when ecology_topology == "patches". Trait-distribution
    # parameters for the independent ecological policy (see
    # agents/ecological_policy.py) — same Normal(mean, std)-then-clip
    # convention as every other heterogeneous trait in this project.
    extraction_propensity_mean: float = 0.5
    extraction_propensity_std: float = 0.2
    maintenance_propensity_mean: float = 0.3
    maintenance_propensity_std: float = 0.2
    scarcity_sensitivity_mean: float = 0.3
    scarcity_sensitivity_std: float = 0.2
    #: Scale constants converting a [0,1] propensity into a resource-unit
    #: request/investment — see agents/ecological_policy.py::
    #: decide_ecological_action. Preliminary-calibration constants (see
    #: dev_mem/status_update.md's Level-0.3 entry), not tuned toward any
    #: particular outcome.
    ecological_harvest_unit: float = 5.0
    ecological_maintenance_unit: float = 5.0
    #: eta_m — fraction of invested maintenance that actually reaches the
    #: patch (the milestone's explicit "do not assume maintenance is
    #: fully efficient" requirement; must be < 1 to be meaningfully
    #: inefficient, but values up to 1.0 are accepted).
    maintenance_efficiency: float = 0.7
    #: Per-step cost paid by every agent regardless of extraction success,
    #: in addition to whatever it actually receives. 0.0 (default) means
    #: no effort cost beyond the maintenance investment itself already
    #: being a paid cost.
    ecological_search_cost: float = 0.0
    #: How excess simultaneous extraction demand within one patch is
    #: rationed (see environment/patches.py::allocate_extraction).
    ecological_allocation_rule: str = "proportional"
    #: Work Package F counterfactual ("no environmental effect"): when
    #: False, agents still decide, still pay maintenance cost, still
    #: receive extraction gain exactly as computed by the same allocation
    #: arithmetic — but the patch's own stock is left untouched by either
    #: (only natural regeneration still runs). See simulation.py's
    #: _ecological_round for the exact dry-run construction.
    ecological_actions_affect_patch: bool = True
    #: Work Package F counterfactual ("randomized ecological policy"):
    #: when True, every agent's per-step (h, m) decision uses a *fresh*
    #: i.i.d. draw from the configured trait distributions instead of its
    #: own inherited ecological_policy (which is left completely untouched
    #: — imitation/mutation still operate on it, but it is never read for
    #: an actual decision, so it has no behavioral consequence in this
    #: mode).
    ecological_policy_randomized_each_step: bool = False
    #: Work Package F counterfactual ("replay / policy-shuffle"): when
    #: True, immediately after the initial population's ecological
    #: policies are drawn (preserving the exact marginal distribution),
    #: they are permuted across agents once, before step 0 — breaking
    #: whatever correlation initialization would otherwise have created
    #: between an agent's other traits/patch membership and its
    #: ecological policy.
    ecological_policy_shuffle: bool = False

    # --- ecological-policy learning (Level 0.3, Work Package D) -------------
    #: Work Package F counterfactual ("frozen ecological policy") is
    #: expressed by setting this False (no new flag needed): ecological
    #: policies are drawn once at initialization and never imitated.
    ecological_imitation_enabled: bool = True
    #: Independent of (may differ from) the social mutation_rate.
    ecological_mutation_rate: float = 0.01
    #: The fitness signal used for *ecological*-policy imitation — may
    #: differ from fitness_mode (used for social-policy imitation and, in
    #: ecological_inheritance_mode="coupled_same_model", for the shared
    #: peer-selection decision too). Neither is asserted more correct.
    fitness_mode_ecological: str = "cumulative_resources"
    #: How the two behavioral dimensions' inheritance is coupled during
    #: the adaptation round — see VALID_ECOLOGICAL_INHERITANCE_MODES.
    ecological_inheritance_mode: str = "independent"

    seed: int = 0

    def __post_init__(self) -> None:
        errors: list[str] = []

        if self.population_size < 2:
            errors.append("population_size must be >= 2")
        if self.n_steps < 1:
            errors.append("n_steps must be >= 1")
        if self.memory_length < 1:
            errors.append("memory_length must be >= 1")

        for name in (
            "observation_accuracy_mean",
            "learning_rate_mean",
            "forgiveness_mean",
            "risk_sensitivity_mean",
            "rewiring_prob",
            "punishment_probability",
            "mutation_rate",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")

        for name in (
            "observation_accuracy_std",
            "learning_rate_std",
            "forgiveness_std",
            "risk_sensitivity_std",
            "initial_resources_std",
            "initial_coercive_capability_std",
            "punishment_cost",
            "punishment_penalty",
            "exit_cost",
        ):
            value = getattr(self, name)
            if value < 0.0:
                errors.append(f"{name} must be >= 0, got {value}")

        if self.initial_resources_mean <= 0:
            errors.append("initial_resources_mean must be > 0")
        if self.initial_coercive_capability_mean < 0:
            errors.append("initial_coercive_capability_mean must be >= 0")

        if self.topology not in VALID_TOPOLOGIES:
            errors.append(f"topology must be one of {VALID_TOPOLOGIES}, got {self.topology!r}")
        if self.mean_degree < 1 or self.mean_degree >= self.population_size:
            errors.append("mean_degree must be >= 1 and < population_size")

        if self.imitation_period < 1:
            errors.append("imitation_period must be >= 1")
        if self.rewiring_period < 1:
            errors.append("rewiring_period must be >= 1")
        if self.interactions_per_step < 1:
            errors.append("interactions_per_step must be >= 1")

        if self.seed < 0:
            errors.append("seed must be >= 0")

        # -- ecological closure ------------------------------------------
        if self.environment_capacity <= 0:
            errors.append("environment_capacity must be > 0")
        if not (0.0 <= self.environment_regen_rate <= 2.0):
            errors.append(
                f"environment_regen_rate must be in [0, 2] (discrete logistic update "
                f"becomes unstable/oscillatory outside this range), got {self.environment_regen_rate}"
            )
        if not (0.0 <= self.environment_initial_fraction <= 1.0):
            errors.append("environment_initial_fraction must be in [0, 1]")
        if self.subsistence_cost < 0:
            errors.append("subsistence_cost must be >= 0")
        if not (0.0 <= self.distress_engagement_prob <= 1.0):
            errors.append("distress_engagement_prob must be in [0, 1]")

        # -- relationship dynamics -----------------------------------------
        if self.search_cost < 0:
            errors.append("search_cost must be >= 0")
        if not (0.0 <= self.connection_accept_base_prob <= 1.0):
            errors.append("connection_accept_base_prob must be in [0, 1]")

        # -- perturbations ---------------------------------------------------
        for i, spec in enumerate(self.perturbations):
            if not isinstance(spec, Mapping):
                errors.append(f"perturbations[{i}] must be a mapping, got {type(spec)!r}")
                continue
            missing = {"start_step", "duration", "kind", "magnitude"} - set(spec)
            if missing:
                errors.append(f"perturbations[{i}] missing keys: {sorted(missing)}")
                continue
            if not (isinstance(spec["start_step"], int) and spec["start_step"] >= 0):
                errors.append(f"perturbations[{i}].start_step must be a non-negative int")
            if not (isinstance(spec["duration"], int) and spec["duration"] >= 1):
                errors.append(f"perturbations[{i}].duration must be an int >= 1")
            if spec["kind"] not in VALID_PERTURBATION_KINDS:
                errors.append(
                    f"perturbations[{i}].kind must be one of {VALID_PERTURBATION_KINDS}, "
                    f"got {spec['kind']!r}"
                )
            if not (0.0 <= spec["magnitude"] <= 1.0):
                errors.append(f"perturbations[{i}].magnitude must be in [0, 1]")

        # -- viability state machine ----------------------------------------
        if self.viability_mode not in VALID_VIABILITY_MODES:
            errors.append(f"viability_mode must be one of {VALID_VIABILITY_MODES}, got {self.viability_mode!r}")
        if self.viability_deficit_steps_threshold < 1:
            errors.append("viability_deficit_steps_threshold must be >= 1")
        if self.viability_max_dormant_steps < 1:
            errors.append("viability_max_dormant_steps must be >= 1")
        if self.viability_replacement_policy not in VALID_REPLACEMENT_POLICIES:
            errors.append(
                f"viability_replacement_policy must be one of {VALID_REPLACEMENT_POLICIES}, "
                f"got {self.viability_replacement_policy!r}"
            )

        # -- fitness / imitation signal --------------------------------------
        if self.fitness_mode not in VALID_FITNESS_MODES:
            errors.append(f"fitness_mode must be one of {VALID_FITNESS_MODES}, got {self.fitness_mode!r}")
        if self.fitness_window < 1:
            errors.append("fitness_window must be >= 1")
        if self.viability_adjusted_dormant_penalty < 0:
            errors.append("viability_adjusted_dormant_penalty must be >= 0")

        # -- local ecological patches (Level 0.3, WP-A) ----------------------
        if self.ecology_topology not in VALID_ECOLOGY_TOPOLOGIES:
            errors.append(f"ecology_topology must be one of {VALID_ECOLOGY_TOPOLOGIES}, got {self.ecology_topology!r}")
        if self.n_patches < 1:
            errors.append("n_patches must be >= 1")
        if self.patch_capacity <= 0:
            errors.append("patch_capacity must be > 0")
        if not (0.0 <= self.patch_regen_rate <= 2.0):
            errors.append(f"patch_regen_rate must be in [0, 2], got {self.patch_regen_rate}")
        if not (0.0 <= self.patch_initial_fraction <= 1.0):
            errors.append("patch_initial_fraction must be in [0, 1]")
        if self.patch_quality_std < 0:
            errors.append("patch_quality_std must be >= 0")
        if self.patch_assignment_mode not in VALID_PATCH_ASSIGNMENT_MODES:
            errors.append(
                f"patch_assignment_mode must be one of {VALID_PATCH_ASSIGNMENT_MODES}, "
                f"got {self.patch_assignment_mode!r}"
            )

        # -- ecological policy / niche construction (Level 0.3, WP-B/C) ------
        for name in (
            "extraction_propensity_std", "maintenance_propensity_std", "scarcity_sensitivity_std",
            "ecological_harvest_unit", "ecological_maintenance_unit", "ecological_search_cost",
        ):
            value = getattr(self, name)
            if value < 0:
                errors.append(f"{name} must be >= 0, got {value}")
        for name in ("extraction_propensity_mean", "maintenance_propensity_mean", "scarcity_sensitivity_mean"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        if not (0.0 <= self.maintenance_efficiency <= 1.0):
            errors.append(f"maintenance_efficiency must be in [0, 1], got {self.maintenance_efficiency}")
        if self.ecological_allocation_rule not in VALID_ECOLOGICAL_ALLOCATION_RULES:
            errors.append(
                f"ecological_allocation_rule must be one of {VALID_ECOLOGICAL_ALLOCATION_RULES}, "
                f"got {self.ecological_allocation_rule!r}"
            )

        # -- ecological-policy learning (Level 0.3, WP-D) ---------------------
        if not (0.0 <= self.ecological_mutation_rate <= 1.0):
            errors.append(f"ecological_mutation_rate must be in [0, 1], got {self.ecological_mutation_rate}")
        if self.fitness_mode_ecological not in VALID_FITNESS_MODES:
            errors.append(
                f"fitness_mode_ecological must be one of {VALID_FITNESS_MODES}, got {self.fitness_mode_ecological!r}"
            )
        if self.ecological_inheritance_mode not in VALID_ECOLOGICAL_INHERITANCE_MODES:
            errors.append(
                f"ecological_inheritance_mode must be one of {VALID_ECOLOGICAL_INHERITANCE_MODES}, "
                f"got {self.ecological_inheritance_mode!r}"
            )

        unknown_policies = set(self.policy_mix) - set(VALID_POLICIES)
        if unknown_policies:
            errors.append(f"unknown policies in policy_mix: {sorted(unknown_policies)}")
        if any(v < 0 for v in self.policy_mix.values()):
            errors.append("policy_mix fractions must be >= 0")
        total = sum(self.policy_mix.values())
        if self.policy_mix and not (0.99 <= total <= 1.01):
            errors.append(f"policy_mix fractions must sum to ~1.0, got {total}")

        # Payoff grammar sanity: standard PD ordering T > R > P > S with
        # 2R > T + S is required for the game to *be* a prisoner's dilemma
        # (a design choice, not an outcome bias). We validate the ordering
        # but do not choose the values for the user.
        if not (
            self.payoff_temptation
            > self.payoff_reward
            > self.payoff_punishment
            >= self.payoff_sucker
        ):
            errors.append(
                "payoffs must satisfy temptation > reward > punishment >= sucker "
                f"(got T={self.payoff_temptation}, R={self.payoff_reward}, "
                f"P={self.payoff_punishment}, S={self.payoff_sucker})"
            )

        if errors:
            raise ValueError("Invalid SimulationConfig:\n  - " + "\n  - ".join(errors))

    # -- (de)serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        # tuples of dicts (perturbations) aren't representable by
        # yaml.safe_dump; normalize to plain lists for serialization. The
        # live object itself keeps perturbations as a tuple.
        d["perturbations"] = [dict(p) for p in self.perturbations]
        return d

    @classmethod
    def from_dict(cls, data: Mapping) -> "SimulationConfig":
        data = dict(data)
        if "perturbations" in data and data["perturbations"] is not None:
            data["perturbations"] = tuple(dict(p) for p in data["perturbations"])
        return cls(**data)

    @classmethod
    def level0_compat(cls, **overrides) -> "SimulationConfig":
        """Original Level-0 compatibility mode: ecology and the new
        relationship-dynamics machinery are both switched off, so the
        simulation follows exactly the pre-Level-0.1 code path — same RNG
        draw sequence, same resource dynamics, same exit/rewire semantics.
        Used for regression testing and as the "Original Level-0
        compatibility mode" arm of the Level 0.1 baseline ensemble.
        """
        compat_fields = {
            "ecology_enabled": False,
            "relationship_dynamics_enabled": False,
            "perturbations": (),
            "viability_mode": "none",
            "fitness_mode": "cumulative_resources",
            "ecology_topology": "global_pool",
        }
        compat_fields.update(overrides)
        return cls(**compat_fields)

    @classmethod
    def level02_compat(cls, **overrides) -> "SimulationConfig":
        """Explicit Level-0.2 compatibility preset (Level 0.3, Work Package
        18): every Level 0.3 mechanism disabled/at its no-op default
        (``ecology_topology="global_pool"``), every Level 0.1/0.2 field at
        its normal (non-compat, i.e. ecology and relationship-dynamics
        both *on*) default. This is exactly what a bare ``SimulationConfig()``
        already does — this classmethod exists so a caller can name the
        intent explicitly rather than relying on "the defaults happen to
        still be Level-0.2-compatible," which is otherwise an unstated
        invariant. See ``tests/test_compat_regression.py`` for the
        byte-for-byte check this preset supports.
        """
        compat_fields = {"ecology_topology": "global_pool"}
        compat_fields.update(overrides)
        return cls(**compat_fields)

    @classmethod
    def level03_patches_default(cls, **overrides) -> "SimulationConfig":
        """Level-0.3 local-patch default preset (Work Package 18):
        ``ecology_topology="patches"`` with every other Level 0.3 field at
        its normal (endogenous-feedback) default — the "everything is
        switched on and adaptive" condition every Work-Package-F
        counterfactual is a controlled deviation from."""
        compat_fields = {"ecology_topology": "patches"}
        compat_fields.update(overrides)
        return cls(**compat_fields)

    # -- Level 0.3, Work Package F: causal-intervention presets. Each is a
    # small, individually-testable deviation from level03_patches_default
    # (the "endogenous feedback" condition) -- see
    # environment/patches.py, agents/adaptation.py, and simulation.py's
    # module docstrings for exactly what each flag changes, and
    # dev_mem/status_update.md's Level 0.3 entry (design decision 4) for
    # why these are orthogonal flags rather than five bespoke simulation
    # variants.
    @classmethod
    def level03_no_environmental_effect(cls, **overrides) -> "SimulationConfig":
        """WP-F condition 2: agents still decide, still pay/earn (their own
        ledgers change), but no patch's own resources are affected by any
        agent action -- only natural regeneration runs on the patch
        side."""
        fields = {"ecology_topology": "patches", "ecological_actions_affect_patch": False}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level03_frozen_ecological_policy(cls, **overrides) -> "SimulationConfig":
        """WP-F condition 3: every agent's ecological policy is fixed at
        its initial (randomly drawn) value for the whole run -- it can
        still affect the patch, but it can never imitate or mutate."""
        fields = {
            "ecology_topology": "patches",
            "ecological_imitation_enabled": False,
            "ecological_mutation_rate": 0.0,
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level03_randomized_ecological_policy(cls, **overrides) -> "SimulationConfig":
        """WP-F condition 4: every agent's ecological *decision* each step
        is drawn fresh, i.i.d., from the configured trait distributions --
        its own stored (and never-mutated, never-imitated-into) policy is
        never read for a decision."""
        fields = {"ecology_topology": "patches", "ecological_policy_randomized_each_step": True}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level03_policy_shuffle(cls, **overrides) -> "SimulationConfig":
        """WP-F condition 5 ("replay/policy-shuffle"): the initially-drawn
        ecological policies are permuted across agents once at
        initialization -- the exact marginal distribution of policies in
        the population is preserved, but any correlation between an
        agent's identity/patch and its ecological policy that
        initialization might otherwise have created is broken."""
        fields = {"ecology_topology": "patches", "ecological_policy_shuffle": True}
        fields.update(overrides)
        return cls(**fields)

    # -- Level 0.3, Work Package G: viability-threshold sweep preset. -----
    @classmethod
    def level03_viability_sweep_base(cls, **overrides) -> "SimulationConfig":
        """Base config for the WP-G viability-threshold staged sweep:
        patches active (so ecological-policy composition before/after
        filtering is meaningful) and ``viability_mode="dormancy_recovery"``
        by default -- callers sweep ``distress_threshold``,
        ``viability_deficit_steps_threshold``, ``viability_recovery_resources``,
        and ``viability_mode`` itself on top of this via ``overrides``/
        ``dataclasses.replace``."""
        fields = {"ecology_topology": "patches", "viability_mode": "dormancy_recovery"}
        fields.update(overrides)
        return cls(**fields)

    # -- Level 0.3, Work Package H: phase-search preset. -------------------
    @classmethod
    def level03_phase_search_base(cls, **overrides) -> "SimulationConfig":
        """Base config for the WP-H reproducible phase-space search:
        patches active, every mechanism at its normal endogenous-feedback
        default; callers vary the milestone's named parameter axes
        (``patch_regen_rate``, ``patch_capacity``, ``n_patches``,
        population-to-patch density via ``population_size``,
        ``payoff_temptation``/other payoff terms for extraction benefit,
        ``ecological_harvest_unit``, ``ecological_maintenance_unit``,
        ``maintenance_efficiency``, ``ecological_mutation_rate``,
        ``scarcity_sensitivity_mean``, ``fitness_mode``) via a design
        matrix, never this preset's own defaults, which are deliberately
        unremarkable (not pre-tuned toward any particular outcome)."""
        fields = {"ecology_topology": "patches"}
        fields.update(overrides)
        return cls(**fields)

    # -- Level 0.3, Work Package J: perturbation-experiment preset. -------
    @classmethod
    def level03_perturbation_base(cls, **overrides) -> "SimulationConfig":
        """Base config for the WP-J perturbation/recovery experiment:
        patches active; callers attach a ``perturbations`` tuple (see
        ``core/perturbation.py``) on top via ``overrides`` to apply a
        specific shock, and construct a matched unperturbed control by
        calling this same preset with ``perturbations=()`` and every
        other field identical."""
        fields = {"ecology_topology": "patches"}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def from_yaml(cls, path: str) -> "SimulationConfig":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)

    def to_yaml(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_dict(), fh, sort_keys=False)
