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

#: Level 1.0, Work Package E: monitoring implementations. "none" = no
#: monitoring occurs (no sanction can ever trigger, since sanctioning is
#: gated on detection). "voluntary" = each member independently decides,
#: at its own cost, whether to monitor one other member this step.
#: "designated" = one member is chosen at adoption and monitors every
#: member each step, at its own cost. "perfect" = every member's true
#: compliance is observed with zero error — a diagnostic control only,
#: never the default.
VALID_MONITORING_MODES = ("none", "voluntary", "designated", "perfect")

#: Level 1.0, Work Package F: collective-sanctioning implementations.
#: "none" = detected violations are never sanctioned. "voluntary" = a
#: bystander member independently decides, at its own cost, whether to
#: sanction a detected violator. "collective_fund" = sanction cost is
#: drawn from the rule's own accumulated fund (see
#: institutional_fund_contribution_rate) rather than any one member;
#: sanctioning stops once the fund is exhausted. "imposed_perfect" = every
#: detected violation is automatically sanctioned at full magnitude with
#: no voluntary decision and no borne cost — a mechanical benchmark
#: control, never the default (see the imposed-rule preset).
VALID_SANCTION_MODES = ("none", "voluntary", "collective_fund", "imposed_perfect")

#: Level 1.0, Work Package C: how a proposal's support is aggregated into
#: an adopt/reject decision. Deliberately not chosen for ecological
#: performance — see dev_mem/status_update.md's Level 1.0 entry.
VALID_ADOPTION_PROCESSES = ("unweighted_voting", "resource_weighted_voting")

#: Level 1.1, Work Package D: elementary local selection procedures for a
#: rule's single delegate slot -- none of these is a governance-type
#: label; each is a bare aggregation mechanism (mirrors
#: VALID_ADOPTION_PROCESSES's own register). "voluntary_approval" = every
#: evaluator independently approves/disapproves each candidate; the
#: candidate with the highest approval fraction is appointed if it clears
#: delegate_selection_support_threshold. "plurality_support" = every
#: evaluator supports exactly one candidate (its highest-scoring); the
#: candidate with the most support is appointed regardless of an absolute
#: threshold, provided support is nonzero. "threshold_acceptance" =
#: identical evaluation to voluntary_approval, but *no* candidate is
#: appointed unless it clears the threshold (voluntary_approval always
#: appoints the best-supported candidate that clears the same threshold —
#: the two differ only when multiple candidates tie above threshold vs.
#: none does). "lottery" = one candidate is drawn uniformly at random from
#: the candidate set, bypassing evaluation entirely.
VALID_DELEGATE_SELECTION_PROCEDURES = ("voluntary_approval", "plurality_support", "threshold_acceptance", "lottery")

#: Level 1.1, Work Package D: the fixed, small vocabulary of elementary
#: administrative tasks a delegate may hold (never roles/titles).
VALID_DELEGATION_TASKS = (
    "monitoring", "resource_accounting", "sanction_execution",
    "maintenance_coordination", "interpatch_communication",
)

#: Level 1.2, Work Package B: how a local institutional observation was
#: formed.
VALID_OBSERVATION_SOURCES = ("passive_observation", "administrative_report")
#: Level 1.2, Work Package C: component-wise by default; whole-package is
#: one explicit, rare, separately-configured route (Work Package C
#: requirement: "component-wise by default, whole-package copy only as
#: one explicit rare configurable route").
VALID_TRANSMISSION_MODES = ("component_wise", "whole_package")
#: Level 1.2, Work Package D: population accounting must always be exact
#: -- these are the only two ways an agent's rule-level standing can
#: change without a physical relocation.
VALID_MIGRATION_ROUTES = ("physical_migration", "membership_exit_only")

#: Level 1.1, Work Package H: elementary collective-contribution
#: collection structures. "none" = no contribution mechanism runs at all
#: (the master no-op). "equal" = every member is asked for the same fixed
#: amount each period. "voluntary" = each member independently decides
#: whether to pay the fixed amount. "proportional" = each member is asked
#: for a fraction of its own current resources. "negotiated" = the asked
#: amount is the mean of participating members' own stated preferences
#: (a minimal, elementary negotiation heuristic, not a bargaining-game
#: solution concept).
VALID_CONTRIBUTION_MODES = ("none", "equal", "voluntary", "proportional", "negotiated")

#: Level 1.1, Work Package H requirement 6: what happens to a rule's
#: remaining collective fund at dissolution. "distributed_to_members" =
#: split evenly among the rule's members at the moment of dissolution.
#: "lost" = the balance is removed from circulation entirely (an explicit,
#: resource-accounted sink, not an accounting gap). "retained_for_
#: reconstruction" = the balance is preserved and, if a reconstruction
#: (Work Package G/C) later re-establishes a rule at the same patch
#: sharing this lineage, seeds that new rule's starting fund.
VALID_FUND_DISSOLUTION_DISPOSITIONS = ("distributed_to_members", "lost", "retained_for_reconstruction")

#: Level 1.1, Work Package I: the fixed, small vocabulary of elementary
#: interpatch coordination purposes (never a federation/state/merger
#: concept -- see the milestone's own "do not yet build a state,
#: constitution, or national government" instruction).
VALID_COORDINATION_KINDS = (
    "information_exchange", "ecological_restraint", "shared_monitoring",
    "mutual_assistance", "shared_records",
)

#: Level 1.1b, Work Package A. See ``core/rng.py`` for the full
#: mode/registry rationale.
VALID_RNG_MODES = ("legacy_single_stream", "mechanism_substreams")


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
    #: Level 1.2, Work Package G: correlates neighboring patches' quality
    #: (see ``environment/patches.py::build_patch_system``'s own
    #: docstring for the exact AR(1)-over-index construction and its
    #: disclosed "patch index order is the adjacency" simplification).
    #: ``0.0`` (default) is an exact no-op — independent draws, identical
    #: to every pre-Level-1.2 run.
    patch_quality_spatial_correlation: float = 0.0
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

    # --- Level 1.0: locally shared, patch-attached rules --------------------
    # Only read when rule_formation_enabled is True (and, for any of it to
    # matter behaviorally, ecology_topology == "patches" too, since a rule
    # is attached to a patch — see rules/shared_rule.py). Default False is
    # an exact Level-0.3b no-op: zero extra RNG draws, zero new event
    # types populated, zero change to any existing metric. A rule is a
    # SharedRule (rules/shared_rule.py) — deliberately not named after any
    # governance concept; "proto-institution" is applied only as an
    # observer-side label (observer/institution_diagnostics.py), never a
    # generative-layer object name (see dev_mem/project_vision.md §5, §9).
    rule_formation_enabled: bool = False

    # -- proposal traits (Work Package C) ------------------------------------
    #: Per-step Bernoulli probability that a given non-proposer-blocked
    #: agent at a patch with no active rule proposes a rule this step.
    #: Deliberately small by default (an "unconditional low probability,"
    #: per the milestone's explicit fallback) rather than scarcity-gated —
    #: scarcity-conditioned proposal behavior (H1) is tested via
    #: ``proposal_probability_scarcity_sensitivity`` below, not by
    #: hard-coding an experimenter threshold.
    proposal_probability_mean: float = 0.01
    proposal_probability_std: float = 0.005
    #: H1 (rule formation / scarcity responsiveness): each agent's
    #: proposal probability this step is additionally scaled up by
    #: ``1 + proposal_probability_scarcity_sensitivity * (1 -
    #: local_patch_occupancy)`` — 0.0 (default) means proposal behavior is
    #: unconditional; a positive value makes deteriorating *local* patch
    #: conditions (never global state) more likely to trigger a proposal.
    #: An agent trait, not an experimenter-chosen global threshold.
    proposal_probability_scarcity_sensitivity: float = 0.0
    #: A proposing agent's own preferred rule parameters (Work Package B) —
    #: proposals are drawn from the proposer's own traits, never optimized
    #: for future patch survival.
    preferred_extraction_ceiling_mean: float = 0.5
    preferred_extraction_ceiling_std: float = 0.2
    preferred_maintenance_requirement_mean: float = 0.3
    preferred_maintenance_requirement_std: float = 0.2
    preferred_monitoring_intensity_mean: float = 0.3
    preferred_monitoring_intensity_std: float = 0.2
    preferred_sanction_magnitude_mean: float = 0.3
    preferred_sanction_magnitude_std: float = 0.2
    preferred_adoption_threshold_mean: float = 0.5
    preferred_adoption_threshold_std: float = 0.15
    preferred_amendment_threshold_mean: float = 0.5
    preferred_amendment_threshold_std: float = 0.15
    #: Rule-parameter mutation (Work Package G): a bounded Gaussian
    #: perturbation of an existing proposal's parameters (distinct from
    #: ecological-policy mutation's fresh redraw — this is deliberately a
    #: *local* variation around an existing rule lineage, matching the
    #: milestone's "mutation from an existing proposal" requirement).
    rule_mutation_rate: float = 0.02
    rule_mutation_std: float = 0.1

    # -- adoption process (Work Package C) -----------------------------------
    #: How a proposal's support is aggregated into adopt/reject — see
    #: VALID_ADOPTION_PROCESSES. Not chosen for ecological performance.
    adoption_process: str = "unweighted_voting"
    #: How many steps a proposal remains open for support before it lapses
    #: unadopted (a "time-limited proposal window," per the milestone).
    proposal_window_steps: int = 5

    # -- membership / compliance traits (Work Package C/D) -------------------
    willingness_to_join_mean: float = 0.5
    willingness_to_join_std: float = 0.2
    willingness_to_monitor_mean: float = 0.3
    willingness_to_monitor_std: float = 0.2
    sanction_preference_mean: float = 0.5
    sanction_preference_std: float = 0.2
    #: How strongly private payoff considerations push toward violation —
    #: higher tolerance means an agent needs a larger expected private
    #: gain from violating before it actually violates.
    violation_tolerance_mean: float = 0.5
    violation_tolerance_std: float = 0.2
    amendment_propensity_mean: float = 0.03
    amendment_propensity_std: float = 0.02
    #: Bernoulli decision noise applied to every join/leave/comply/monitor/
    #: sanction/amend decision below — 0.0 would make every decision a
    #: deterministic threshold comparison; a small positive default keeps
    #: every decision genuinely stochastic, never mechanically certain.
    institutional_decision_noise_std: float = 0.1
    #: Resource cost paid by a member who chooses to leave an active rule
    #: (0.0 = free exit).
    membership_exit_cost: float = 0.0

    # -- monitoring (Work Package E) ------------------------------------------
    monitoring_mode: str = "none"
    monitoring_cost: float = 0.1
    #: True-positive rate: P(detected as violating | actually violating).
    monitoring_detection_accuracy: float = 0.8
    #: False-positive rate: P(detected as violating | actually complying).
    monitoring_false_positive_rate: float = 0.05
    #: "designated"/rotating-monitor mode only: how often the monitor role
    #: rotates to a new member (0 = never rotates after initial
    #: assignment).
    monitor_rotation_period_steps: int = 0

    # -- collective sanctioning (Work Package F) -----------------------------
    sanction_mode: str = "none"
    #: Resource cost paid by the sanctioning party (a bystander member
    #: under "voluntary", or drawn from the rule's fund under
    #: "collective_fund") per unit of sanction_magnitude imposed.
    sanction_cost_per_unit: float = 0.5
    #: Converts a rule's ``[0, 1]``-scale ``sanction_magnitude`` into actual
    #: resource units removed from a detected violator's ``resources``
    #: (mirrors ``ecological_harvest_unit``/``ecological_maintenance_unit``'s
    #: propensity-to-resource-unit conversion role) — penalty_resources =
    #: sanction_magnitude * sanction_penalty_unit, applied only on a
    #: detected (possibly false-positive) violation and only up to the
    #: violator's current resources (never driving resources negative).
    #: Distinct from ``sanction_cost_per_unit``, which prices what the
    #: *sanctioning party* pays, not what the *target* loses.
    sanction_penalty_unit: float = 3.0
    #: "collective_fund" mode only: the fraction of every member's
    #: *effective* maintenance investment this step that is diverted into
    #: the rule's fund instead of the patch (0.0 = no fund accumulation,
    #: sanctioning under collective_fund mode can then never occur once
    #: any starting fund is exhausted).
    institutional_fund_contribution_rate: float = 0.0

    # -- dissolution (Work Package H) -----------------------------------------
    #: A rule dissolves once its living-member fraction of eligible patch
    #: agents falls below this floor.
    rule_dissolution_membership_floor: float = 0.15
    #: A rule dissolves once its most recent amendment/reaffirmation
    #: support fraction falls below this floor (checked only when an
    #: amendment vote occurs — a rule with no amendment attempts is not
    #: dissolved on this criterion alone).
    rule_dissolution_support_floor: float = 0.2
    #: A rule with zero members for this many consecutive steps dissolves
    #: ("the rule remains inactive for a sustained duration").
    rule_inactive_dissolution_steps: int = 40
    #: "collective_fund" sanction mode only: a rule dissolves if its fund
    #: has been exactly 0.0 for this many consecutive steps while
    #: violations continue to be detected (insufficient institutional
    #: resources) -- 0 disables this specific dissolution trigger.
    rule_fund_depletion_dissolution_steps: int = 0

    # -- mechanical benchmark / control presets (Work Package, Stage 4) ------
    #: Stage-4 condition 7 ("imposed rule"): when True, at initialization
    #: every eligible patch is directly given an active rule with the
    #: ``imposed_rule_*`` parameters below, skipping proposal/adoption
    #: entirely -- a mechanical benchmark, never an emergent institution.
    #: Compliance/monitoring/sanctioning still operate normally on top of
    #: it (membership is still voluntary and compliance still noisy,
    #: unless the caller also sets monitoring_mode="perfect" and
    #: sanction_mode="imposed_perfect" for a fully mechanical control).
    institution_imposed_mode: bool = False
    imposed_rule_extraction_ceiling: float = 0.4
    imposed_rule_maintenance_requirement: float = 0.4
    imposed_rule_monitoring_intensity: float = 0.5
    imposed_rule_sanction_magnitude: float = 0.5
    #: Stage-4 condition 8 ("randomized pseudo-institution"): when True,
    #: every member's compliance decision ignores the rule's actual
    #: parameters and instead complies/violates via an unconditional coin
    #: flip at ``randomized_pseudo_institution_compliance_probability`` --
    #: monitoring/sanctioning still consume their configured cost, so
    #: institutional *activity and cost* are matched to a real rule while
    #: the rule-content-to-behavior linkage is deliberately broken.
    randomized_pseudo_institution_mode: bool = False
    randomized_pseudo_institution_compliance_probability: float = 0.5

    # --- Level 1.1: delegation, administrative capacity, discretion, --------
    # accountability, collective contributions, interpatch coordination -----
    # Master no-op flags: delegation_enabled=False and
    # interpatch_coordination_enabled=False (both defaults) leave every
    # field below unread and every new Level 1.1 event type permanently
    # empty -- an exact, verified Level-1.0-compatible no-op (see
    # tests/test_level11_compatibility.py). Nothing here is read unless
    # rule_formation_enabled is also True, since delegation/coordination
    # both attach to an active SharedRule.
    delegation_enabled: bool = False

    # -- nomination and selection (Work Package D) ---------------------------
    #: Which tasks a rule's single active delegate holds at once (Work
    #: Package D's own permitted simplification, mirroring Level 1.0's
    #: "at most one active rule per patch": at most one active delegate
    #: per rule at a time, holding this fixed task set, rather than
    #: independent per-task delegate slots -- a documented scope choice,
    #: not a claim that multi-delegate task division is uninteresting).
    delegated_tasks: tuple[str, ...] = ("monitoring",)
    #: How a candidate clears the delegate slot — see
    #: VALID_DELEGATE_SELECTION_PROCEDURES.
    delegate_selection_procedure: str = "voluntary_approval"
    #: Minimum support fraction required under "voluntary_approval" /
    #: "threshold_acceptance".
    delegate_selection_support_threshold: float = 0.5
    #: How many steps a nomination window stays open before resolving
    #: with whatever candidates/support have accumulated so far.
    delegate_nomination_window_steps: int = 5
    #: Weights (each >= 0) combining a candidate's observed reliability
    #: (this candidate's own prior-delegate track record; 0.5 neutral
    #: prior if never delegated), perceived_competence, social_trust,
    #: relative resource position, and expected administrative cost
    #: (jurisdiction-size aversion) into one evaluator's support draw —
    #: an explicit, inspectable heuristic (same register as Level 1.0's
    #: decide_rule_compliance), not a solved mechanism-design optimum.
    delegate_evaluation_reliability_weight: float = 0.35
    delegate_evaluation_competence_weight: float = 0.25
    delegate_evaluation_trust_weight: float = 0.2
    delegate_evaluation_resource_weight: float = 0.1
    delegate_evaluation_cost_aversion_weight: float = 0.1

    # -- administrative capacity (Work Package E) ----------------------------
    #: Per-task resource cost paid by the delegate whenever it performs
    #: that task this step (Work Package E requirement 3: capacity must
    #: have costs).
    delegation_task_cost: float = 0.05
    #: How much concurrent task load degrades this step's success
    #: probability (Work Package E "coordination burden"/diseconomies) —
    #: 0.0 disables the workload penalty regardless of how many tasks are
    #: held at once.
    delegation_workload_penalty_per_task: float = 0.05
    #: How much a rule's own jurisdiction size (member count, rescaled by
    #: 1/10) degrades (positive) or improves (negative) this step's
    #: success probability — lets a caller explore either administrative
    #: economies or diseconomies of scale (Work Package E requirement 5)
    #: without hard-coding which direction is "true." 0.0 by default:
    #: scale effects are neither assumed beneficial nor harmful.
    delegation_scale_coefficient: float = 0.0
    #: Multiplier translating this delegate's realized capacity index
    #: (accumulated only from past task_successes/task_attempts, never a
    #: raw assigned trait — Work Package E requirement 8) into this
    #: step's success-probability bonus.
    delegation_capacity_learning_weight: float = 0.3
    #: Per-step multiplicative decay applied to record_quality whenever
    #: the delegate performs no task this step (inactivity decay, Work
    #: Package E requirement 2).
    delegation_inactivity_decay_rate: float = 0.02
    #: Fraction of an outgoing delegate's final record_quality retained
    #: as this rule's own institutional_memory on replacement/removal
    #: (Work Package E requirements 6-7) — 0.0 means no institutional
    #: memory survives a delegate change (every replacement starts from
    #: zero); 1.0 means the rule retains everything the outgoing delegate
    #: ever learned.
    institutional_memory_retention: float = 0.3
    #: Fraction of the rule's current institutional_memory granted to a
    #: newly appointed delegate as a starting record_quality bonus.
    institutional_memory_transfer_to_new_delegate: float = 0.5

    # -- discretion and appropriation (Work Package F) -----------------------
    #: Master switch for discretion/appropriation behavior — False means
    #: every delegate always attempts every task faithfully (still
    #: subject to ordinary capacity-driven success/failure noise, but
    #: never deliberately withholds effort or appropriates funds). Kept
    #: as its own flag (distinct from delegation_enabled) so a caller can
    #: study capacity accumulation in complete isolation from discretion
    #: (the milestone's "delegation plus capacity accumulation"
    #: ablation).
    discretion_enabled: bool = False
    #: Multiplier on appropriation_propensity converting it into a
    #: per-step Bernoulli probability of attempting appropriation (only
    #: possible when the rule's fund is positive) — 0.0 makes
    #: appropriation structurally impossible even with
    #: discretion_enabled=True.
    appropriation_opportunity_scale: float = 1.0
    #: Fraction of the rule's current fund an attempted appropriation
    #: removes (bounded, never more than the fund holds).
    appropriation_fraction_of_fund: float = 0.2
    #: Multiplier on effort_reduction_propensity converting it into a
    #: per-step Bernoulli probability of withholding effort on a task
    #: this step (Work Package F "effort reduction" — lowers that task's
    #: success probability toward its unlearned floor).
    effort_reduction_opportunity_scale: float = 1.0

    # -- accountability and constraint (Work Package G) -----------------------
    accountability_enabled: bool = False
    # -- Level 1.1b, Work Package E: accountability *component* ablations.
    # Only meaningful when accountability_enabled=True; each defaults to
    # True (i.e. "full accountability" is the same behavior as before
    # these fields existed — legacy/exact-compat when left at defaults).
    # Real architectural coupling, not a bug: recall can never fire
    # without a "found" audit finding to trigger it (see
    # rules/delegation.py::accountability_round), so
    # audit_enabled=False, recall_enabled=True still produces zero
    # recalls — there is no code path for a "pure recall without audit"
    # condition in this implementation, and this milestone does not add
    # one (that would be a new governance mechanism, out of scope). Appeal
    # is architecturally independent of both (it responds to
    # SanctionEvents, not audit/recall state), so "appeal only"
    # (audit_enabled=False, recall_enabled=False, appeal_enabled=True) is
    # a genuinely isolated condition.
    #: Whether member audits happen at all this rule.
    audit_enabled: bool = True
    #: Whether a found-misconduct audit can trigger a recall vote. See
    #: the coupling note above — has no effect unless audit_enabled is
    #: also True.
    recall_enabled: bool = True
    #: Whether a fresh SanctionEvent can be appealed.
    appeal_enabled: bool = True
    #: Multiplier on each eligible member's audit_diligence trait,
    #: converting it into a per-step audit-attempt probability (Work
    #: Package G: "accountability is costly" — gated by an individual
    #: trait, never a population-level guarantee).
    audit_probability_scale: float = 1.0
    #: True-positive/true-negative rate of an audit correctly identifying
    #: whether misconduct (appropriation or withheld effort) actually
    #: occurred this step (imperfect information, Work Package G
    #: requirement 2).
    audit_accuracy: float = 0.75
    #: Resource cost paid by the auditing member, win or lose.
    audit_cost: float = 0.1
    #: Minimum support fraction (among eligible rule members) required
    #: for a recall triggered by a found-misconduct audit to succeed.
    recall_support_threshold: float = 0.5
    #: Fraction of a removed delegate's cumulative appropriated_total
    #: recovered back into the rule's fund on a successful recall.
    recall_fund_recovery_fraction: float = 0.5
    #: Per-new-SanctionEvent probability that the sanctioned member
    #: appeals.
    appeal_probability: float = 0.3
    #: P(appeal upheld | the underlying sanction was actually a false
    #: positive) — imperfect review, not guaranteed correction.
    appeal_accuracy_true_positive: float = 0.7
    #: P(appeal upheld | the underlying sanction was actually justified)
    #: — a false-appeal-success rate, kept explicit and nonzero-capable
    #: (review is imperfect in both directions, never one-sided).
    appeal_accuracy_false_positive: float = 0.1
    #: Fraction of the original sanction penalty refunded to the target
    #: when an appeal is upheld.
    appeal_refund_fraction: float = 1.0
    #: Resource cost paid by the appellant regardless of outcome.
    appeal_cost: float = 0.05

    # -- collective contributions (Work Package H) -----------------------------
    contribution_mode: str = "none"  # see VALID_CONTRIBUTION_MODES
    #: How often (in steps) a contribution period is assessed.
    contribution_period_steps: int = 10
    #: Flat per-period amount asked under "equal"/"voluntary" modes.
    contribution_amount: float = 0.2
    #: Fraction of current resources asked under "proportional" mode.
    contribution_proportional_rate: float = 0.02
    #: What happens to a rule's remaining fund balance at dissolution —
    #: see VALID_FUND_DISSOLUTION_DISPOSITIONS (Work Package H
    #: requirement 6: dissolution must specify a disposition, never leave
    #: the balance unaccounted).
    fund_dissolution_disposition: str = "distributed_to_members"

    # -- interpatch coordination (Work Package I) ------------------------------
    # Deliberately decoupled from delegation_enabled — Work Package I is
    # about rule-to-rule coordination generally, not specifically a
    # delegate's "interpatch_communication" task, so
    # interpatch_coordination_enabled can be studied with or without
    # delegation active (the milestone's "coordination_only" preset).
    interpatch_coordination_enabled: bool = False
    #: Per-step, per-rule probability of initiating a coordination
    #: proposal toward another randomly chosen rule-bearing patch (no
    #: explicit interpatch adjacency topology exists in this project —
    #: a documented scope simplification; see docs/odd_level1.1.md), when
    #: this rule currently has no active outgoing link and no pending
    #: proposal.
    coordination_proposal_probability: float = 0.02
    #: How many steps a pending coordination proposal stays open.
    coordination_proposal_window_steps: int = 5
    #: Per-step probability that an active link actually exchanges
    #: information/assistance this step (imperfect and costly, Work
    #: Package I requirement 6).
    coordination_activity_probability: float = 0.3
    #: Standard deviation of the Gaussian noise applied to a link's
    #: transmitted occupancy estimate (0.0 = perfect transmission).
    coordination_info_error_std: float = 0.1
    #: Resource cost deducted from each side's rule fund (a documented
    #: no-op — never charged — when that side has no fund) per step a
    #: link is active.
    coordination_cost_per_step: float = 0.05
    #: Fraction of the sending rule's fund transferred, capped by
    #: available fund, on a "mutual_assistance" link's activity step when
    #: the receiving patch's occupancy is below
    #: coordination_assistance_occupancy_threshold.
    coordination_assistance_transfer_fraction: float = 0.2
    coordination_assistance_occupancy_threshold: float = 0.2
    #: Per-step probability an active link voluntarily dissolves.
    coordination_dissolution_probability: float = 0.02

    # --- Level 1.1b, Work Package A: RNG architecture --------------------
    #: "legacy_single_stream" (default): byte-for-byte the pre-Level-1.1b
    #: single shared ``Generator`` — required for exact Level 1.1
    #: reproduction. "mechanism_substreams": each named mechanism in
    #: ``core/rng.py::STREAM_REGISTRY`` draws from its own independent
    #: ``Generator`` — required for every Level 1.1b causal-isolation
    #: experiment (disabling one mechanism cannot perturb another's
    #: stream). See ``docs/level1.1b_rng_design.md``.
    rng_mode: str = "legacy_single_stream"
    #: Exported in every run manifest alongside ``rng_mode`` so a result
    #: can always be traced to the exact stream registry that produced it
    #: — bump this string (never silently reorder/remove a registry
    #: entry) whenever ``core/rng.py::STREAM_REGISTRY`` changes. Must
    #: always equal ``core/rng.py::RNG_REGISTRY_VERSION`` (enforced by
    #: ``tests/test_level11b_rng_substreams.py``) — bumped to
    #: ``"level13_v1"`` when Level 1.3 appended its own substream names
    #: (a pure append, per ``core/rng.py``'s own "never reorder or
    #: remove" rule, so every Level 1.1b-1.2b stream keeps its exact
    #: byte-for-byte seed regardless of this bump).
    rng_registry_version: str = "level13_v1"

    # --- Level 1.2, Work Package B: local institutional observation --------
    #: Strict no-op (no observations ever formed) by default, exactly like
    #: every other new-mechanism master flag in this codebase.
    institutional_observation_enabled: bool = False
    #: How often (in steps) each active interpatch coordination link
    #: produces a fresh pair of local observations.
    observation_period_steps: int = 5
    #: Gaussian noise std applied to every perceived-signal component
    #: (Work Package B "imperfect/noisy" requirement), scaled by the
    #: observing agent's own ``1 - observation_accuracy`` (an agent with
    #: perfect observation accuracy still receives the structural delay/
    #: distortion terms below, but zero added noise).
    observation_noise_std: float = 0.15
    #: Maximum possible delay (in steps) between when a true signal was
    #: generated and when it is perceived -- drawn uniformly on
    #: ``[0, observation_delay_max_steps]`` per observation (Work Package
    #: B "delayed" requirement). ``0`` (the default) means same-step
    #: observation, i.e. no delay.
    observation_delay_max_steps: int = 0
    #: When a target patch has an active delegate AND
    #: ``config.discretion_enabled``, an "administrative_report" is used
    #: instead of passive observation, and the delegate's own
    #: ``effort_reduction_propensity`` trait (already used by Work Package
    #: F's discretion mechanism -- reused here rather than adding a
    #: second, redundant misconduct-propensity trait) scales how far the
    #: reported values are pushed away from the true ones (Work Package B
    #: "administrative reporting may be accurate/mistaken/selectively
    #: disclosed/distorted if discretion mechanisms support it").
    #: ``0.0`` (the default) makes every administrative report exactly as
    #: noisy as passive observation -- never systematically distorted.
    administrative_report_distortion_scale: float = 0.0

    # --- Level 1.2, Work Package C: component-wise institutional transmission
    institutional_transmission_enabled: bool = False
    transmission_mode: str = "component_wise"  # see VALID_TRANSMISSION_MODES
    #: How often (in steps) a transmission opportunity is evaluated per
    #: observing agent-pair.
    transmission_period_steps: int = 5
    #: Base per-opportunity transmission-attempt probability before the
    #: perceived-performance/trust/similarity/communication-quality/
    #: switching-cost adjustment (Work Package C requirement 4) is
    #: applied.
    transmission_base_probability: float = 0.05
    #: Std of the Gaussian perturbation applied to a numeric component on
    #: a "noisy"/"mutated" transfer outcome.
    transmission_mutation_std: float = 0.05
    #: Probability that a successful transfer recombines the copied
    #: component(s) with the receiver's own existing value (a weighted
    #: blend) rather than replacing it outright.
    transmission_recombination_probability: float = 0.1
    #: Probability that a well-formed, in-flight transfer nonetheless
    #: fails outright (Work Package C: "must not guarantee survival").
    transmission_failure_probability: float = 0.1

    # --- Level 1.2, Work Package D: migration and membership selection -----
    migration_enabled: bool = False
    #: How often (in steps) each agent evaluates a migration/exit decision.
    migration_evaluation_period_steps: int = 10
    #: Flat resource cost paid on a successful physical migration (Work
    #: Package D "movement cost").
    migration_cost: float = 1.0
    #: Optional hard cap on a destination patch's member count -- ``None``
    #: (the default) means unconstrained (Work Package D still requires
    #: exact accounting either way; this only affects whether an attempt
    #: can be refused for "no_capacity").
    migration_capacity_per_patch: int | None = None
    #: Std of the logistic-decision noise applied to the migration/exit
    #: utility comparison (mirrors ``institutional_decision_noise_std``'s
    #: role elsewhere in this codebase, kept separate so migration's own
    #: noise scale can be tuned independently).
    migration_decision_noise_std: float = 0.2
    #: Population-level distribution ``Agent.migration_propensity`` is
    #: drawn from (only when ``migration_enabled`` is True — see that
    #: field's own docstring).
    migration_propensity_mean: float = 0.15
    migration_propensity_std: float = 0.1
    #: A rule member may leave membership without physically relocating
    #: (Work Package D: "membership exit vs. physical migration" must be
    #: distinguishable) -- a strict no-op (no exits ever occur) by
    #: default, independent of ``migration_enabled`` (an operator may want
    #: one mechanism without the other).
    membership_exit_enabled: bool = False

    # --- Level 1.2, Work Package F: institutional scaling -------------------
    #: Strict no-op (no scale-change events, no administrative-overhead
    #: multiplier ever applied) by default. Reuses the same active-
    #: coordination-link topology Work Packages B/C already reuse --
    #: "jurisdictional patch count" here is a connected component's size
    #: over ``coordination_link_registry`` (never a new topology).
    institutional_scaling_enabled: bool = False
    #: Fractional administrative-cost change per additional patch beyond
    #: the first in a rule's coordination-network jurisdiction. Positive
    #: (Work Package F: "admin workload increases with scale") or
    #: negative (Work Package G: administrative *economies* of scale are
    #: an equally permitted, equally neutral possibility — nothing in
    #: this milestone favors either direction a priori). The resulting
    #: multiplier is floored at 0.1 (never zero or negative cost) at its
    #: one call site (``rules/delegation.py::task_performance_round``).
    #: ``0.0`` makes scale-tracking purely observer-side (events still
    #: emitted; no behavioral effect).
    scaling_admin_overhead_per_patch: float = 0.05

    # ============================================================
    # Level 1.3: historical sequencing, entrenchment, and
    # path-dependent institutional differentiation (Section 3 scaffold
    # only -- the pressure-history/activation/entrenchment/legitimacy
    # FIELDS these flags gate are added incrementally, Work Package by
    # Work Package, exactly like every earlier level's own field set).
    # ------------------------------------------------------------
    # Every field below is a strict no-op by default (Section 3 item 6:
    # "All Level 1.3 mechanisms must be disabled by default"; item 7:
    # with Level 1.3 disabled, the frozen Level 1.2b model must
    # reproduce the reference byte-for-byte/field-for-field). Individual
    # mechanisms each get their OWN master flag too, mirroring this
    # codebase's existing per-mechanism-flag convention (e.g.
    # ``institutional_observation_enabled``), so a caller can isolate
    # exactly one Level 1.3 mechanism the same way Stage 1 activation
    # tests isolate one Level 1.1/1.2 mechanism (Section 15 Stage 1).
    # See ``Simulation.__init__``'s historical-state block and
    # ``tests/test_level13_compatibility.py`` for the mechanical proof
    # that ``historical_module_enabled=False`` means no Level 1.3 field
    # is ever read by any Level 1.2b generative code path.
    # ------------------------------------------------------------
    #: The single overall Level 1.3 gate. False (the default) is
    #: equivalent to "Level 1.3 does not exist" -- every mechanism-
    #: specific flag below only has any effect when this is ALSO True.
    historical_module_enabled: bool = False
    #: Work Package A: security/territorial pressure (``security_
    #: pressure``, ``W_t`` in Section 5's notation).
    security_pressure_enabled: bool = False
    #: Work Package A: state-society bargaining pressure (``bargaining_
    #: pressure``, ``B_t``).
    bargaining_pressure_enabled: bool = False
    #: Work Package A: impersonal coordination pressure (``coordination_
    #: complexity``, ``X_t``).
    coordination_complexity_enabled: bool = False
    #: Work Package C: continuous institutional entrenchment.
    entrenchment_enabled: bool = False
    #: Work Package D: performance legitimacy ledger (``L_P``).
    performance_legitimacy_enabled: bool = False
    #: Work Package D: procedural/reciprocal legitimacy ledger (``L_R``).
    procedural_legitimacy_enabled: bool = False

    # --- Level 1.3, Section 5: pressure-history specifications --------
    # Flat/primitive fields (mirrors every other mechanism's own field
    # convention in this class -- e.g. contribution_mode/period/amount
    # above -- rather than a nested dataclass), so these round-trip
    # through to_dict/to_yaml with no special-casing. Read only inside
    # Simulation.__init__'s historical_module_enabled-gated block,
    # which assembles each channel's own core.historical_pressure.
    # PressureHistorySpec from the ten fields below and calls
    # generate_pressure_series() once per enabled channel. Defaults are
    # inert (kind="constant_low", low_level==the same 0.1 for every
    # channel) but NOT read at all unless both historical_module_
    # enabled and that channel's own *_enabled flag are True.
    security_pressure_history_kind: str = "constant_low"
    security_pressure_low_level: float = 0.1
    security_pressure_high_level: float = 0.5
    security_pressure_onset_step: int = 0
    security_pressure_duration_steps: int | None = None
    security_pressure_decay_rate: float = 0.0
    security_pressure_volatility_std: float = 0.0
    security_pressure_n_shocks: int = 3
    security_pressure_shock_width_steps: int = 5
    security_pressure_shock_interval_steps: int = 20

    bargaining_pressure_history_kind: str = "constant_low"
    bargaining_pressure_low_level: float = 0.1
    bargaining_pressure_high_level: float = 0.5
    bargaining_pressure_onset_step: int = 0
    bargaining_pressure_duration_steps: int | None = None
    bargaining_pressure_decay_rate: float = 0.0
    bargaining_pressure_volatility_std: float = 0.0
    bargaining_pressure_n_shocks: int = 3
    bargaining_pressure_shock_width_steps: int = 5
    bargaining_pressure_shock_interval_steps: int = 20

    coordination_complexity_history_kind: str = "constant_low"
    coordination_complexity_low_level: float = 0.1
    coordination_complexity_high_level: float = 0.5
    coordination_complexity_onset_step: int = 0
    coordination_complexity_duration_steps: int | None = None
    coordination_complexity_decay_rate: float = 0.0
    coordination_complexity_volatility_std: float = 0.0
    coordination_complexity_n_shocks: int = 3
    coordination_complexity_shock_width_steps: int = 5
    coordination_complexity_shock_interval_steps: int = 20

    #: Section 7's own "preregistered sustained-duration criterion" --
    #: shared by every institutional-response series Work Package B
    #: measures (see core/historical_pressure.py::first_sustained_
    #: crossing), rather than one threshold per response type, for
    #: auditability. Purely observer-side: never read by any generative
    #: mechanism.
    activation_sustained_duration_steps: int = 10

    # --- Level 1.3, Work Package A (Section 6): pressure transmission
    # channels. Six channels (two per pressure), each independently
    # enabled/disabled per Section 6's own requirement, each ALSO
    # requiring its parent pressure's own master flag (e.g.
    # security_pressure_enabled) to have any effect at all -- see
    # core/historical_transmission.py's module docstring for the full
    # disclosed-scope-reduction rationale (six of Section 6's eighteen
    # listed candidate channels implemented this milestone). Every
    # sensitivity defaults to a small positive value so an activation
    # test can observe SOME effect the moment its own flag is flipped,
    # without needing an override -- exactly like ``coordination_info_
    # error_std`` and other existing "on means something, not a no-op
    # you also have to tune" defaults in this class.
    security_pressure_returns_to_delegation_enabled: bool = False
    security_pressure_returns_to_delegation_sensitivity: float = 0.15
    security_pressure_admin_capacity_demand_enabled: bool = False
    security_pressure_admin_capacity_demand_sensitivity: float = 0.3
    bargaining_pressure_conditional_contribution_enabled: bool = False
    bargaining_pressure_conditional_contribution_sensitivity: float = 0.2
    bargaining_pressure_appeal_recall_enabled: bool = False
    bargaining_pressure_appeal_recall_sensitivity: float = 0.2
    coordination_complexity_cross_patch_transactions_enabled: bool = False
    coordination_complexity_cross_patch_transactions_sensitivity: float = 0.3
    coordination_complexity_interoperable_demand_enabled: bool = False
    coordination_complexity_interoperable_demand_sensitivity: float = 0.3

    # --- Level 1.3, Work Package C (Section 8): continuous institutional
    # entrenchment. A single mechanism (not sub-flagged into several
    # channels like Work Package A) gated by ``entrenchment_enabled``
    # alone -- "entrenched institutions resist change/dissolution" is one
    # coherent hypothesis, not several independent ones. Deliberately
    # adds NO new mutable state to ``SharedRule``: entrenchment is a pure
    # function of age (``step - rule.founding_step``, already recorded
    # since Level 1.0) via ``core/entrenchment.py::entrenchment_level``,
    # exactly the same "compute from existing state, don't add a new
    # stock" discipline Work Package A used for its capacity-demand
    # channel. See ``rules/dynamics.py``'s ``amendment_round``/
    # ``dissolution_round`` for the two places this is applied.
    entrenchment_maturation_steps: int = 200
    entrenchment_amendment_threshold_sensitivity: float = 0.3
    entrenchment_dissolution_survival_sensitivity: float = 0.5

    # --- Level 1.3, Work Package D (Section 9): dual legitimacy ledgers
    # (L_P performance, L_R procedural/reciprocal). "legitimacy" is
    # permitted here and in ``core/legitimacy.py``/``rules/shared_rule.
    # py``'s two new ledger fields per project_vision.md §5's Level 1.3
    # amendment (a narrow, disclosed carve-out) — the Agent-level ban
    # remains fully enforced and untouched; see
    # ``tests/test_level03_niche_construction.py::
    # test_agent_level_legitimacy_ban_is_unaffected_by_the_config_level_
    # exception``. Each ledger tracks toward this rule's own CUMULATIVE
    # track record (compliance rate for L_P; inverse sanction intensity
    # for L_R — see ``core/legitimacy.py`` module docstring for the full
    # disclosed rationale for this simplified, delegation-independent
    # signal choice) via a bounded EMA plus a small fallibility draw from
    # the dedicated ``legitimacy_accumulation`` RNG substream.
    performance_legitimacy_learning_rate: float = 0.1
    performance_legitimacy_fallibility_std: float = 0.05
    procedural_legitimacy_learning_rate: float = 0.1
    procedural_legitimacy_fallibility_std: float = 0.05

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
        if not (0.0 <= self.patch_quality_spatial_correlation <= 1.0):
            errors.append("patch_quality_spatial_correlation must be in [0, 1]")
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

        # -- Level 1.0: locally shared rules --------------------------------
        for name in (
            "proposal_probability_mean", "proposal_probability_std", "preferred_extraction_ceiling_std",
            "preferred_maintenance_requirement_std", "preferred_monitoring_intensity_std",
            "preferred_sanction_magnitude_std", "preferred_adoption_threshold_std",
            "preferred_amendment_threshold_std", "rule_mutation_rate", "rule_mutation_std",
            "willingness_to_join_std", "willingness_to_monitor_std", "sanction_preference_std",
            "violation_tolerance_std", "amendment_propensity_mean", "amendment_propensity_std",
            "institutional_decision_noise_std", "membership_exit_cost", "monitoring_cost",
            "sanction_cost_per_unit", "institutional_fund_contribution_rate",
            "proposal_probability_scarcity_sensitivity", "sanction_penalty_unit",
        ):
            value = getattr(self, name)
            if value < 0:
                errors.append(f"{name} must be >= 0, got {value}")
        for name in (
            "preferred_extraction_ceiling_mean", "preferred_maintenance_requirement_mean",
            "preferred_monitoring_intensity_mean", "preferred_sanction_magnitude_mean",
            "preferred_adoption_threshold_mean", "preferred_amendment_threshold_mean",
            "willingness_to_join_mean", "willingness_to_monitor_mean", "sanction_preference_mean",
            "violation_tolerance_mean", "monitoring_detection_accuracy", "monitoring_false_positive_rate",
            "randomized_pseudo_institution_compliance_probability", "rule_dissolution_membership_floor",
            "rule_dissolution_support_floor",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        if self.proposal_window_steps < 1:
            errors.append("proposal_window_steps must be >= 1")
        if self.monitor_rotation_period_steps < 0:
            errors.append("monitor_rotation_period_steps must be >= 0")
        if self.rule_inactive_dissolution_steps < 1:
            errors.append("rule_inactive_dissolution_steps must be >= 1")
        if self.rule_fund_depletion_dissolution_steps < 0:
            errors.append("rule_fund_depletion_dissolution_steps must be >= 0")
        if self.adoption_process not in VALID_ADOPTION_PROCESSES:
            errors.append(f"adoption_process must be one of {VALID_ADOPTION_PROCESSES}, got {self.adoption_process!r}")
        if self.monitoring_mode not in VALID_MONITORING_MODES:
            errors.append(f"monitoring_mode must be one of {VALID_MONITORING_MODES}, got {self.monitoring_mode!r}")
        if self.sanction_mode not in VALID_SANCTION_MODES:
            errors.append(f"sanction_mode must be one of {VALID_SANCTION_MODES}, got {self.sanction_mode!r}")
        for name in ("imposed_rule_extraction_ceiling", "imposed_rule_maintenance_requirement",
                     "imposed_rule_monitoring_intensity", "imposed_rule_sanction_magnitude"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        if self.rule_formation_enabled and self.ecology_topology != "patches":
            errors.append("rule_formation_enabled requires ecology_topology='patches' (a rule attaches to a patch)")

        # -- Level 1.1: delegation, capacity, discretion, accountability -----
        if self.delegation_enabled and not self.rule_formation_enabled:
            errors.append("delegation_enabled requires rule_formation_enabled (a delegate attaches to a rule)")
        if self.interpatch_coordination_enabled and not self.rule_formation_enabled:
            errors.append("interpatch_coordination_enabled requires rule_formation_enabled (a link attaches to a rule)")
        unknown_tasks = set(self.delegated_tasks) - set(VALID_DELEGATION_TASKS)
        if unknown_tasks:
            errors.append(f"delegated_tasks contains unknown task(s): {sorted(unknown_tasks)}")
        if not self.delegated_tasks:
            errors.append("delegated_tasks must be non-empty when delegation_enabled is True")
        if self.delegate_selection_procedure not in VALID_DELEGATE_SELECTION_PROCEDURES:
            errors.append(
                f"delegate_selection_procedure must be one of {VALID_DELEGATE_SELECTION_PROCEDURES}, "
                f"got {self.delegate_selection_procedure!r}"
            )
        if not (0.0 <= self.delegate_selection_support_threshold <= 1.0):
            errors.append("delegate_selection_support_threshold must be in [0, 1]")
        if self.delegate_nomination_window_steps < 1:
            errors.append("delegate_nomination_window_steps must be >= 1")
        for name in (
            "delegate_evaluation_reliability_weight", "delegate_evaluation_competence_weight",
            "delegate_evaluation_trust_weight", "delegate_evaluation_resource_weight",
            "delegate_evaluation_cost_aversion_weight", "delegation_task_cost",
            "delegation_workload_penalty_per_task", "delegation_capacity_learning_weight",
            "delegation_inactivity_decay_rate", "appropriation_opportunity_scale",
            "appropriation_fraction_of_fund", "effort_reduction_opportunity_scale",
            "audit_probability_scale", "audit_cost", "recall_fund_recovery_fraction",
            "appeal_probability", "appeal_cost", "contribution_period_steps",
            "contribution_amount", "contribution_proportional_rate",
            "coordination_proposal_probability", "coordination_proposal_window_steps",
            "coordination_activity_probability", "coordination_info_error_std",
            "coordination_cost_per_step", "coordination_assistance_transfer_fraction",
            "coordination_dissolution_probability",
        ):
            value = getattr(self, name)
            if value < 0:
                errors.append(f"{name} must be >= 0, got {value}")
        for name in (
            "institutional_memory_retention", "institutional_memory_transfer_to_new_delegate",
            "recall_support_threshold", "appeal_accuracy_true_positive",
            "appeal_accuracy_false_positive", "appeal_refund_fraction",
            "coordination_assistance_occupancy_threshold",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        if not (0.0 <= self.audit_accuracy <= 1.0):
            errors.append("audit_accuracy must be in [0, 1]")
        if self.contribution_mode not in VALID_CONTRIBUTION_MODES:
            errors.append(f"contribution_mode must be one of {VALID_CONTRIBUTION_MODES}, got {self.contribution_mode!r}")
        if self.fund_dissolution_disposition not in VALID_FUND_DISSOLUTION_DISPOSITIONS:
            errors.append(
                f"fund_dissolution_disposition must be one of {VALID_FUND_DISSOLUTION_DISPOSITIONS}, "
                f"got {self.fund_dissolution_disposition!r}"
            )
        if self.coordination_proposal_window_steps < 1:
            errors.append("coordination_proposal_window_steps must be >= 1")
        if self.rng_mode not in VALID_RNG_MODES:
            errors.append(f"rng_mode must be one of {VALID_RNG_MODES}, got {self.rng_mode!r}")

        # -- Level 1.2 ------------------------------------------------------
        if self.observation_period_steps < 1:
            errors.append("observation_period_steps must be >= 1")
        if self.observation_noise_std < 0:
            errors.append("observation_noise_std must be >= 0")
        if self.observation_delay_max_steps < 0:
            errors.append("observation_delay_max_steps must be >= 0")
        if not (0.0 <= self.administrative_report_distortion_scale <= 1.0):
            errors.append("administrative_report_distortion_scale must be in [0, 1]")
        if self.transmission_mode not in VALID_TRANSMISSION_MODES:
            errors.append(f"transmission_mode must be one of {VALID_TRANSMISSION_MODES}, got {self.transmission_mode!r}")
        if self.transmission_period_steps < 1:
            errors.append("transmission_period_steps must be >= 1")
        for name in (
            "transmission_base_probability", "transmission_mutation_std",
            "transmission_recombination_probability", "transmission_failure_probability",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        if self.migration_evaluation_period_steps < 1:
            errors.append("migration_evaluation_period_steps must be >= 1")
        if self.migration_cost < 0:
            errors.append("migration_cost must be >= 0")
        if self.migration_capacity_per_patch is not None and self.migration_capacity_per_patch < 1:
            errors.append("migration_capacity_per_patch must be >= 1 when set")
        if self.migration_decision_noise_std <= 0:
            errors.append("migration_decision_noise_std must be > 0")
        if self.migration_propensity_std < 0:
            errors.append("migration_propensity_std must be >= 0")
        if self.institutional_scaling_enabled and not self.interpatch_coordination_enabled:
            errors.append("institutional_scaling_enabled requires interpatch_coordination_enabled (Level 1.2 scaling reuses coordination links as its jurisdiction topology)")
        if self.institutional_observation_enabled and not self.interpatch_coordination_enabled:
            errors.append("institutional_observation_enabled requires interpatch_coordination_enabled (Level 1.2 observation reuses coordination links as the observation topology)")
        if self.institutional_transmission_enabled and not self.interpatch_coordination_enabled:
            errors.append("institutional_transmission_enabled requires interpatch_coordination_enabled (Level 1.2 transmission reuses coordination links as its interpatch_communication route)")
        if self.migration_enabled and self.ecology_topology != "patches":
            errors.append("migration_enabled requires ecology_topology='patches'")

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

        # -- Level 1.3, Section 5: pressure-history field validation --
        # Runs unconditionally (mirrors VALID_CONTRIBUTION_MODES etc.
        # above -- catches a typo'd kind even if the channel is
        # currently disabled) via each channel's own PressureHistorySpec
        # .validate(), which is the exact same validation
        # Simulation.__init__ implicitly relies on when it later builds
        # that spec -- one audited implementation, not one hand-rolled
        # duplicate per channel here.
        from abm_governance.core.historical_pressure import PressureHistorySpec

        for prefix in ("security_pressure", "bargaining_pressure", "coordination_complexity"):
            spec = PressureHistorySpec(
                kind=getattr(self, f"{prefix}_history_kind"),
                low_level=getattr(self, f"{prefix}_low_level"),
                high_level=getattr(self, f"{prefix}_high_level"),
                onset_step=getattr(self, f"{prefix}_onset_step"),
                duration_steps=getattr(self, f"{prefix}_duration_steps"),
                decay_rate=getattr(self, f"{prefix}_decay_rate"),
                volatility_std=getattr(self, f"{prefix}_volatility_std"),
                n_shocks=getattr(self, f"{prefix}_n_shocks"),
                shock_width_steps=getattr(self, f"{prefix}_shock_width_steps"),
                shock_interval_steps=getattr(self, f"{prefix}_shock_interval_steps"),
            )
            errors.extend(f"{prefix}: {e}" for e in spec.validate())
        if self.activation_sustained_duration_steps < 1:
            errors.append("activation_sustained_duration_steps must be >= 1")
        if self.entrenchment_maturation_steps < 1:
            errors.append("entrenchment_maturation_steps must be >= 1")
        for name in (
            "performance_legitimacy_learning_rate",
            "procedural_legitimacy_learning_rate",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name} must be in [0, 1], got {value}")
        for name in (
            "performance_legitimacy_fallibility_std",
            "procedural_legitimacy_fallibility_std",
        ):
            value = getattr(self, name)
            if value < 0.0:
                errors.append(f"{name} must be >= 0, got {value}")

        if errors:
            raise ValueError("Invalid SimulationConfig:\n  - " + "\n  - ".join(errors))

    # -- (de)serialization ---------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        # tuples of dicts (perturbations) aren't representable by
        # yaml.safe_dump; normalize to plain lists for serialization. The
        # live object itself keeps perturbations as a tuple.
        d["perturbations"] = [dict(p) for p in self.perturbations]
        # Level 1.1: delegated_tasks is a tuple[str, ...] for the same
        # reason -- normalize to a plain list for serialization only.
        d["delegated_tasks"] = list(self.delegated_tasks)
        return d

    @classmethod
    def from_dict(cls, data: Mapping) -> "SimulationConfig":
        data = dict(data)
        if "perturbations" in data and data["perturbations"] is not None:
            data["perturbations"] = tuple(dict(p) for p in data["perturbations"])
        if "delegated_tasks" in data and data["delegated_tasks"] is not None:
            data["delegated_tasks"] = tuple(data["delegated_tasks"])
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

    # -- Level 1.0: locally shared rules -------------------------------------
    @classmethod
    def level1_rule_formation_default(cls, **overrides) -> "SimulationConfig":
        """Level-1.0 default preset: patches active, rule formation
        active, every rule-formation mechanism at its normal (voluntary
        monitoring, voluntary sanctioning, unweighted-voting adoption)
        default — the "emergent, unforced" condition every Stage-4
        institutional counterfactual is a controlled deviation from.
        ``rule_formation_enabled=False`` (the ``SimulationConfig()``
        default) remains the exact Level-0.3b no-op."""
        fields = {"ecology_topology": "patches", "rule_formation_enabled": True}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_no_institution(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 1 (atomic baseline): patches active, rule
        formation mechanism entirely off -- byte-for-byte identical to
        ``level03_patches_default`` under the hood (rule_formation_enabled
        is the master no-op flag), named explicitly for the institutional
        counterfactual design's own readability."""
        fields = {"ecology_topology": "patches", "rule_formation_enabled": False}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_proposals_only(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 2: proposals/adoption/membership/compliance
        active, monitoring and sanctioning both off -- isolates whether
        a merely-adopted, unenforced rule changes anything on its own."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "none", "sanction_mode": "none",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_monitoring_only(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 3: voluntary monitoring active, sanctioning
        off -- violations are detected (and reported) but never
        sanctioned."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "voluntary", "sanction_mode": "none",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_sanction_without_reliable_monitoring(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 4: sanctioning active but monitoring detection
        accuracy is deliberately poor (near-chance) -- isolates whether
        enforcement without reliable detection still has any effect."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "voluntary", "monitoring_detection_accuracy": 0.5,
            "monitoring_false_positive_rate": 0.45, "sanction_mode": "voluntary",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_monitoring_plus_voluntary_sanction(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 5: the full voluntary monitoring + voluntary
        sanction combination -- the milestone's H5 "complementarity" test
        pairs this against conditions 3 and 4 above."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_monitoring_plus_collective_sanction(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 6: voluntary monitoring + collectively-funded
        sanctioning (fund replenished from a share of members' effective
        maintenance investment)."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "voluntary", "sanction_mode": "collective_fund",
            "institutional_fund_contribution_rate": 0.05,
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_imposed_rule(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 7: a mechanical benchmark, not an emergent
        institution -- every eligible patch starts with an already-active
        rule at fixed parameters (``imposed_rule_*``), skipping
        proposal/adoption entirely. Monitoring/sanctioning still operate
        at their normal (voluntary/imperfect) defaults unless overridden."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "institution_imposed_mode": True,
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level1_randomized_pseudo_institution(cls, **overrides) -> "SimulationConfig":
        """Stage-4 condition 8: matches institutional activity/cost (a
        real rule forms, monitoring/sanctioning still run and still cost
        resources) while deliberately breaking the rule-content-to-
        behavior linkage -- every member's compliance decision ignores the
        rule's actual parameters."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
            "randomized_pseudo_institution_mode": True,
        }
        fields.update(overrides)
        return cls(**fields)

    # -- Level 1.1: delegation, capacity, discretion, accountability --------
    # Preset names are experiment conveniences (Section 10's own explicit
    # instruction), never governance types -- see
    # docs/level1.1_scientific_note.md's structural-terminology guard.
    @classmethod
    def level10_compat(cls, **overrides) -> "SimulationConfig":
        """Exact Level-1.0 compatibility mode, named explicitly for this
        milestone's own presets: rule formation active at its normal
        (level1_rule_formation_default) settings, every Level 1.1
        mechanism at its no-op default (delegation_enabled=False,
        interpatch_coordination_enabled=False, contribution_mode="none").
        Byte-for-byte identical to ``level1_rule_formation_default()``
        under the hood."""
        fields = {"ecology_topology": "patches", "rule_formation_enabled": True}
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level11_delegation_only(cls, **overrides) -> "SimulationConfig":
        """Delegation (Work Package D) active; discretion, accountability,
        contributions, and interpatch coordination all off. Administrative
        capacity (Work Package E) still accumulates from realized
        performance whenever a delegate exists -- it is not a separately
        switchable mechanism (see core/config.py's field docstrings) --
        so this preset also exercises Work Package E, deliberately."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "delegation_enabled": True, "discretion_enabled": False,
            "accountability_enabled": False, "contribution_mode": "none",
            "interpatch_coordination_enabled": False,
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level11_capacity_only(cls, **overrides) -> "SimulationConfig":
        """Alias of ``level11_delegation_only`` with a name matching the
        milestone's own requested preset list — capacity accumulation is
        intrinsic to any active delegate in this implementation (Work
        Package E requirement 1), so "delegation only" and "capacity
        only" are the same configuration; kept as two names for
        experiment-script readability."""
        return cls.level11_delegation_only(**overrides)

    @classmethod
    def level11_accountability_only(cls, **overrides) -> "SimulationConfig":
        """Delegation, discretion, and accountability all active
        (accountability needs discretion active or there is nothing for
        it to ever catch — see docs/level1.1_scientific_note.md); no
        collective contributions, no interpatch coordination."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "delegation_enabled": True, "discretion_enabled": True,
            "accountability_enabled": True, "contribution_mode": "none",
            "interpatch_coordination_enabled": False,
            # Level 1.0's own sanctioning must be active for Work Package
            # G's appeal mechanism (which reacts to SanctionEvents) to
            # ever have anything to act on.
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level11_coordination_only(cls, **overrides) -> "SimulationConfig":
        """Interpatch coordination (Work Package I) active; delegation
        entirely off — demonstrates I's deliberate independence from
        D-H (a rule can coordinate with a neighboring rule without either
        one ever having a delegate)."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "delegation_enabled": False, "interpatch_coordination_enabled": True,
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level11_complete(cls, **overrides) -> "SimulationConfig":
        """Every Level 1.1 mechanism active at its normal default —
        delegation, discretion, accountability, a voluntary collective
        contribution, and interpatch coordination — the condition every
        ablation preset below is a controlled deviation from."""
        fields = {
            "ecology_topology": "patches", "rule_formation_enabled": True,
            "delegation_enabled": True, "discretion_enabled": True,
            "accountability_enabled": True, "contribution_mode": "voluntary",
            "interpatch_coordination_enabled": True,
            "monitoring_mode": "voluntary", "sanction_mode": "voluntary",
        }
        fields.update(overrides)
        return cls(**fields)

    @classmethod
    def level11_no_memory(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with institutional memory switched off
        (``institutional_memory_retention=0.0``) — every delegate
        replacement starts administrative capacity from zero, with
        nothing bridged from the outgoing delegate."""
        fields = {"institutional_memory_retention": 0.0}
        base = cls.level11_complete(**{**fields, **overrides})
        return base

    @classmethod
    def level11_no_accountability(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with accountability switched off —
        discretion (including appropriation) remains active, but members
        can never audit, appeal, or recall."""
        fields = {"accountability_enabled": False}
        return cls.level11_complete(**{**fields, **overrides})

    @classmethod
    def level11_no_admin_cost(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with every administrative *cost* field
        zeroed (task cost, coordination cost) while every mechanism stays
        structurally active — isolates whether administrative activity
        itself, independent of its resource cost, has any effect."""
        fields = {
            "delegation_task_cost": 0.0,
            "coordination_cost_per_step": 0.0,
            "audit_cost": 0.0,
            "appeal_cost": 0.0,
        }
        return cls.level11_complete(**{**fields, **overrides})

    @classmethod
    def level11_no_interpatch_coordination(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with interpatch coordination switched
        off — delegation/discretion/accountability/contributions remain
        active within each patch, but no patch ever coordinates with
        another."""
        fields = {"interpatch_coordination_enabled": False}
        return cls.level11_complete(**{**fields, **overrides})

    # -- Level 1.1b, Work Package A: RNG-mode presets. Experimental
    # conveniences (a documented starting point for scripts/notebooks), not
    # governance types — see docs/level1.1b_rng_design.md. -------------------
    @classmethod
    def level11_legacy_compat(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with ``rng_mode="legacy_single_stream"``
        (the default already, so this preset exists purely to make the
        choice explicit at call sites that want to assert/document it) —
        every mechanism draws from the one shared RNG stream, in the exact
        call order Level 1.1 always used. Byte-for-byte identical to
        Level 1.1's own output for the same seed/config (see
        ``tests/test_level11b_rng_substreams.py``'s legacy-replication
        tests)."""
        fields = {"rng_mode": "legacy_single_stream"}
        return cls.level11_complete(**{**fields, **overrides})

    @classmethod
    def level11b_substreams(cls, **overrides) -> "SimulationConfig":
        """``level11_complete`` with ``rng_mode="mechanism_substreams"`` —
        required for every Level 1.1b causal-isolation experiment
        (Work Packages C-H): each mechanism in
        ``abm_governance.core.rng.STREAM_REGISTRY`` draws from its own
        independent ``Generator``, so disabling/ablating one mechanism
        cannot change any other mechanism's draw sequence. Produces a
        *different* (but equally valid, equally reproducible) trajectory
        than ``level11_legacy_compat`` for the same seed — the two modes
        are not expected to match draw-for-draw, only each to be
        internally deterministic and reproducible."""
        fields = {"rng_mode": "mechanism_substreams"}
        return cls.level11_complete(**{**fields, **overrides})

    @classmethod
    def level11b_coordination_nondegenerate(cls, **overrides) -> "SimulationConfig":
        """Level 1.1b, Work Package C: an interpatch-coordination
        calibration whose proposal/acceptance/rejection/dissolution mix is
        NOT structurally near-certain in either direction — chosen purely
        from mechanism-activation criteria (every one of propose, accept,
        reject, dissolve actually fires at typical seeds), never because
        it produces a preferred macro pattern.

        Level 1.1's own default (``coordination_proposal_window_steps=5``,
        preserved here unchanged and NOT overwritten by this preset) lets
        a pending proposal retry its acceptance draw once per step for up
        to 5 steps before its window expires. At this project's default
        ``interpatch_acceptance_propensity ~ N(0.5, 0.2)`` (clipped,
        averaged over a rule's members), a single attempt succeeds only
        about half the time -- but the *eventual* probability of at least
        one success within 5 independent attempts is close to
        1 - 0.5**5 ~= 0.97, which is what actually produced the
        historical "72/72" result documented in
        ``docs/level1.1_scientific_note.md`` §4: near-certain eventual
        acceptance is the expected behavior of this exact mechanism at
        this exact (legitimate, not degenerate, not buggy) calibration --
        confirmed by direct reproduction in
        ``tests/test_level11b_coordination.py``, which recovers genuine
        (if infrequent) window-expiry rejections at the very same
        parameters across other seeds.

        Setting ``coordination_proposal_window_steps=1`` removes the
        retry structure entirely: a pending proposal gets exactly one
        acceptance draw before its window expires, so the empirical
        acceptance rate directly reflects the underlying ~0.5 propensity
        rather than an escalated multi-attempt success probability --
        typically 35-65% accepted / 35-65% rejected across seeds at this
        project's default population/patch scale, alongside routine
        voluntary and rule-triggered dissolutions. See
        ``experiments/level11b_coordination_calibration.py`` for the full
        sweep this preset was chosen from."""
        fields = {"coordination_proposal_window_steps": 1}
        return cls.level11b_substreams(**{**fields, **overrides})

    # -- Level 1.1b, Work Package E: accountability contrast presets, all
    # built on ``level11b_substreams`` (matched-seed causal work requires
    # substream mode). "audit only"/"appeal only" are genuinely isolated
    # conditions; "recall only" is really "audit+recall, no appeal" — see
    # ``audit_enabled``/``recall_enabled``'s field docs for the
    # architectural coupling (recall cannot fire without an audit finding
    # to trigger it in this implementation). -----------------------------
    @classmethod
    def level11b_accountability_audit_only(cls, **overrides) -> "SimulationConfig":
        """Audits run (cost paid, confusion-matrix outcomes recorded) but
        can never trigger a recall or be followed by an appeal."""
        fields = {"accountability_enabled": True, "audit_enabled": True, "recall_enabled": False, "appeal_enabled": False}
        return cls.level11b_substreams(**{**fields, **overrides})

    @classmethod
    def level11b_accountability_appeal_only(cls, **overrides) -> "SimulationConfig":
        """Appeals against fresh sanctions run normally; audits (and
        therefore recalls, which require an audit finding) never happen
        — the one genuinely architecture-independent isolation among the
        three components."""
        fields = {"accountability_enabled": True, "audit_enabled": False, "recall_enabled": False, "appeal_enabled": True}
        return cls.level11b_substreams(**{**fields, **overrides})

    @classmethod
    def level11b_accountability_recall_only(cls, **overrides) -> "SimulationConfig":
        """Audits and recall run normally; appeals never happen. Named
        'recall only' per the milestone's requested condition list, but
        see the module-level coupling note: recall cannot be isolated
        from audit in this implementation (recall requires an audit
        finding as its trigger), so this is really 'audit+recall, no
        appeal' — reported honestly as such rather than silently
        relabeled."""
        fields = {"accountability_enabled": True, "audit_enabled": True, "recall_enabled": True, "appeal_enabled": False}
        return cls.level11b_substreams(**{**fields, **overrides})

    @classmethod
    def level11b_accountability_costless(cls, **overrides) -> "SimulationConfig":
        """Full accountability (audit + recall + appeal) with every
        accountability-specific resource cost zeroed
        (``audit_cost``/``appeal_cost``) — isolates whether accountability
        activity itself, independent of its cost, has any effect (the
        same "opportunity vs. cost" logic as
        ``level11_no_admin_cost``, applied to accountability instead of
        ordinary administrative tasks)."""
        fields = {"accountability_enabled": True, "audit_cost": 0.0, "appeal_cost": 0.0}
        return cls.level11b_substreams(**{**fields, **overrides})

    @classmethod
    def level11b_accountability_perfect_info(cls, **overrides) -> "SimulationConfig":
        """Full accountability with ``audit_accuracy=1.0`` — every audit
        correctly identifies whether misconduct actually occurred (no
        false positives, no false negatives). The upper bound on
        detection-driven effective constraint at this project's other
        default parameters."""
        fields = {"accountability_enabled": True, "audit_accuracy": 1.0}
        return cls.level11b_substreams(**{**fields, **overrides})

    @classmethod
    def level11b_accountability_randomized_placebo(cls, **overrides) -> "SimulationConfig":
        """Full accountability machinery runs at its normal rate (same
        audit/recall/appeal *attempt* frequencies as ``level11_complete``
        — high ``accountability_activity``) but ``audit_accuracy=0.5``
        makes every audit's finding a coin flip, carrying no real
        information about whether misconduct actually occurred. The
        intended contrast case for
        ``observer/accountability_diagnostics.py``: activity stays high,
        but ``effective_constraint`` should collapse toward the level a
        pure coin flip would produce, since detections and false alarms
        become statistically indistinguishable from noise."""
        fields = {"accountability_enabled": True, "audit_accuracy": 0.5}
        return cls.level11b_substreams(**{**fields, **overrides})

    # -- Level 1.2, Section 17: config presets (added after Stages 0-13's
    # own experiment scripts had already hand-built these exact flag
    # combinations repeatedly -- these presets exist for Level 1.3 and
    # any future caller, not to retroactively change how Stages 1-13
    # were run; no existing experiment script was refactored to use
    # them, so no already-generated/hashed output is affected). Every
    # preset defaults its own five new mechanism flags to whatever it
    # names explicitly and leaves everything else at
    # ``level11_complete``'s own defaults -- a bare ``SimulationConfig()``
    # remains untouched by any preset existing here. -----------------

    @classmethod
    def level12_complete(cls, **overrides) -> "SimulationConfig":
        """Every Level 1.1 mechanism (via ``level11_complete``) plus all
        five Level 1.2 generative mechanisms (Work Packages B/C/D/F:
        institutional observation, transmission, migration, membership
        exit, and institutional scaling) active at their normal
        defaults, with ``rng_mode="mechanism_substreams"`` (mandatory
        for Level 1.2 per Section 15) — the condition every Level 1.2
        ablation preset below is a controlled deviation from, mirroring
        ``level11_complete``'s own role for Level 1.1."""
        fields = {
            "rng_mode": "mechanism_substreams",
            "institutional_observation_enabled": True, "institutional_transmission_enabled": True,
            "migration_enabled": True, "membership_exit_enabled": True, "institutional_scaling_enabled": True,
        }
        return cls.level11_complete(**{**fields, **overrides})

    @classmethod
    def level12_observation_only(cls, **overrides) -> "SimulationConfig":
        """``level1_rule_formation_default`` plus interpatch coordination
        (a Work Package B prerequisite) and institutional observation
        only — every other Level 1.1/1.2 mechanism stays at its default
        (off), isolating Work Package B exactly as
        ``experiments/level12_stage1_activation.py``'s own
        ``level12_observation_only`` condition does by hand."""
        fields = {"interpatch_coordination_enabled": True, "institutional_observation_enabled": True}
        return cls.level1_rule_formation_default(**{**fields, **overrides})

    @classmethod
    def level12_transmission_only(cls, **overrides) -> "SimulationConfig":
        """Isolates Work Package C (component transmission) only, same
        pattern as ``level12_observation_only``."""
        fields = {"interpatch_coordination_enabled": True, "institutional_transmission_enabled": True}
        return cls.level1_rule_formation_default(**{**fields, **overrides})

    @classmethod
    def level12_migration_only(cls, **overrides) -> "SimulationConfig":
        """Isolates Work Package D's migration mechanism only. Note:
        this alone also structurally produces ``MembershipExitEvent
        (reason="migration")`` — a mechanical consequence of relocating,
        not a separate mechanism activating (see
        ``experiments/level12_stage1_activation.py``'s own module
        docstring for the full explanation)."""
        fields = {"migration_enabled": True}
        return cls.level1_rule_formation_default(**{**fields, **overrides})

    @classmethod
    def level12_membership_exit_only(cls, **overrides) -> "SimulationConfig":
        """Isolates Work Package D's voluntary membership-exit mechanism
        (``reason="dissatisfaction"``) only, migration left off."""
        fields = {"membership_exit_enabled": True}
        return cls.level1_rule_formation_default(**{**fields, **overrides})

    @classmethod
    def level12_scaling_only(cls, **overrides) -> "SimulationConfig":
        """Isolates Work Package F's institutional-scaling mechanism
        only."""
        fields = {"interpatch_coordination_enabled": True, "institutional_scaling_enabled": True}
        return cls.level1_rule_formation_default(**{**fields, **overrides})

    # -- Level 1.2b, Section 24: config presets. Every preset below is
    # a NO-OP by default -- calling it with zero overrides returns a
    # config identical, field for field, to ``level12_complete()``'s
    # own output. They exist purely as semantically-named entry points
    # for this milestone's own recurring run contexts (feasibility
    # mapping, open discovery, prospective confirmation, failure
    # analysis, sustained-system analysis, causal collapse ablation,
    # scaling robustness), exactly mirroring Section 17's own
    # ``level12_complete``-is-the-real-baseline posture: no existing
    # Work Package E-R experiment script is refactored to use these
    # (every already-generated/hashed output remains untouched), and a
    # bare ``SimulationConfig()`` remains completely unaffected by any
    # preset defined here. Every preset inherits ``rng_mode=
    # "mechanism_substreams"`` from ``level12_complete`` -- Section 24's
    # "causal presets use rng_mode=mechanism_substreams" therefore holds
    # by construction for all eight, not as a special case for any
    # subset of them. ------------------------------------------------

    @classmethod
    def level12_compat(cls, **overrides) -> "SimulationConfig":
        """The explicit, Level-1.2b-named alias for the exact Level 1.2
        baseline (``level12_complete``'s own defaults). Callers who want
        "Level 1.2's own condition, nothing more, nothing Level-1.2b-
        specific" should prefer this name over ``level12_complete``
        directly -- functionally identical, purely a naming preference
        Section 24 introduces for Level 1.2b's own documentation."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_feasibility_map(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for feasibility-ratio mapping work
        (the ecological/institutional parameter-space characterization
        Work Packages C/E/Q draw on) -- no behavioral change from
        ``level12_complete`` by default."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_open_discovery(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for the open, blind discovery pool
        (Work Packages E/J/K's own joint-design run context) -- no
        behavioral change from ``level12_complete`` by default."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_confirmation(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for prospective confirmation runs
        (Work Package L's own confirmation-pool run context) -- no
        behavioral change from ``level12_complete`` by default."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_failure_analysis(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for failure-trajectory-focused analysis
        (the collapse/failure-outcome side of Work Packages J/K/O's own
        classification work) -- no behavioral change from
        ``level12_complete`` by default."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_sustained_analysis(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for sustained-system-focused analysis
        (the ``sustained_system_eligibility`` side of Work Packages
        J/K/O's own classification work) -- no behavioral change from
        ``level12_complete`` by default."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_collapse_ablation(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for causal collapse-decomposition
        ablations (Work Package N's own matched-seed, single-factor
        ablation run context) -- no behavioral change from
        ``level12_complete`` by default; callers vary exactly one of
        Work Package N's thirteen named factor fields via ``overrides``
        per matched pair, never this preset's own defaults."""
        return cls.level12_complete(**overrides)

    @classmethod
    def level12b_scaling_robustness(cls, **overrides) -> "SimulationConfig":
        """Semantic entry point for the scaling-robustness grid (Work
        Package M's own population/n_patches/network-modularity sweep
        run context) -- no behavioral change from ``level12_complete``
        by default; callers vary ``population_size``, ``n_patches``,
        and ``rewiring_prob`` via ``overrides`` per grid cell, never
        this preset's own defaults."""
        return cls.level12_complete(**overrides)

    # -- Level 1.3, Section 3: the frozen reference preset ------------
    # ``level12b_frozen_reference()`` is the exact condition Level 1.3's
    # Stage 0 compatibility experiment (and every historical-disabled
    # config elsewhere in Level 1.3) must reproduce byte-for-byte/
    # field-for-field. It is, deliberately, nothing more than a
    # Level-1.3-named alias for ``level12_complete()`` -- the same "no
    # behavioral change from level12_complete by default" posture every
    # Level 1.2b preset above already has -- so that "the frozen
    # reference" is unambiguous and never silently drifts if
    # ``level12_complete`` itself is ever touched by a later mistake (a
    # test asserts the two remain equal; see
    # ``tests/test_level13_compatibility.py``). ``historical_module_
    # enabled`` is not set here because ``level12_complete`` (via
    # ``level11_complete`` down to a bare ``SimulationConfig()``)
    # already defaults it to ``False`` -- this preset does not need to,
    # and must not, mention any Level 1.3 field explicitly.
    @classmethod
    def level12b_frozen_reference(cls, **overrides) -> "SimulationConfig":
        """The frozen Level 1.2b reference condition Level 1.3's exact-
        compatibility requirement (Section 3 items 5-7) is checked
        against -- identical to ``level12_complete()`` by construction."""
        return cls.level12_complete(**overrides)

    @classmethod
    def from_yaml(cls, path: str) -> "SimulationConfig":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return cls.from_dict(data)

    def to_yaml(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump(self.to_dict(), fh, sort_keys=False)
