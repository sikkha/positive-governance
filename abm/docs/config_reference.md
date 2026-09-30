# Configuration Reference

`SimulationConfig` (`src/abm_governance/core/config.py`) is a frozen
dataclass; every field is validated in `__post_init__` (invalid values
raise `ValueError` immediately — nothing is silently clamped). This
document is a field index; `core/config.py` itself is the source of
truth for exact validation rules and default values, and every field
below has an inline comment there.

Load/save via `SimulationConfig.from_yaml(path)` / `.to_yaml(path)`, or
construct directly: `SimulationConfig(seed=0, population_size=100, ...)`.
`SimulationConfig.level0_compat(**overrides)` is a preset that reproduces
the exact pre-Level-0.1 code path (see "Presets" below).

## Population and policy mix

`population_size`, `n_steps`, `policy_mix` (mapping of policy name →
fraction, must sum to ~1.0, keys restricted to `VALID_POLICIES`),
`memory_length` — unchanged since Level 0.

## Heterogeneous trait distributions

`observation_accuracy_mean/std`, `learning_rate_mean/std`,
`forgiveness_mean/std`, `risk_sensitivity_mean/std`,
`initial_resources_mean/std`, `initial_coercive_capability_mean/std` —
unchanged since Level 0. Each agent's trait is drawn once at
initialization from `Normal(mean, std)`, clipped to a valid range.

## Network

`topology` (`erdos_renyi` | `watts_strogatz` | `regular`), `mean_degree`,
`rewiring_prob` (only used for `watts_strogatz`) — unchanged since Level 0.

## Payoff grammar

`payoff_temptation`, `payoff_reward`, `payoff_punishment`, `payoff_sucker`
— must satisfy `temptation > reward > punishment >= sucker`, validated.

## Punishment

`punishment_enabled`, `punishment_probability`, `punishment_cost`,
`punishment_penalty` — unchanged since Level 0. Set
`punishment_enabled=False` for the "no punishment" ablation.

## Exit / rewiring (shared by both the legacy and Level 0.1 mechanisms)

`exit_cost`, `exit_resource_threshold` — the *decision* threshold is
shared; Level 0.1 additionally gates exit on affordability (see below).

## Adaptation timescales

`imitation_period`, `mutation_rate`, `rewiring_period`,
`interactions_per_step` — unchanged since Level 0.

## Ecological closure — Level 0.1, Work Package A

| field | default | meaning |
|---|---|---|
| `ecology_enabled` | `True` | Master switch. `False` = original Level-0 unbounded/uncapped dynamics (the "compat mode" half of `level0_compat()`), consuming zero extra RNG draws. |
| `environment_capacity` | `2000.0` | `K`, the pool's carrying capacity. **See known limitation:** the default value empties almost immediately under default demand — see `dev_mem/status_update.md`'s newest entry. |
| `environment_regen_rate` | `0.5` | `r` in the discrete logistic update; validated to `[0, 2]` (values outside this range make the discrete update unstable/oscillatory). |
| `environment_initial_fraction` | `0.5` | Pool starts at this fraction of `K`. |
| `subsistence_cost` | `0.3` | Per-agent, per-step upkeep charge, paid unconditionally (not pool-linked). |
| `distress_threshold` | `0.0` | An agent below this resource level at a step's *start* is "distressed" for that whole step. |
| `distress_engagement_prob` | `0.5` | Probability a distressed agent still engages in a given scheduled interaction (complement = a logged `WithholdEvent`). |

## Endogenous relationship dynamics — Level 0.1, Work Package B

| field | default | meaning |
|---|---|---|
| `relationship_dynamics_enabled` | `True` | Master switch. `False` = original Level-0 legacy exit/rewire logic exactly (unconditional exit, blind edge addition, no accept/reject, no failed-exit accounting, no search cost) — the other half of `level0_compat()`. |
| `search_cost` | `0.2` | Cost paid by the proposer for each connection attempt, win or lose. |
| `connection_accept_base_prob` | `0.7` | Baseline acceptance probability before the target's own degree-saturation discount. |
| `relationship_exit_enabled` | `True` | Sub-switch: disable exit specifically while connection formation stays active (the "no relationship exit" ablation). No effect when `relationship_dynamics_enabled=False` (legacy path ignores it). Consumes no RNG draws either way. |

## Adaptation sub-switch — Level 0.1, Work Package E ablation support

| field | default | meaning |
|---|---|---|
| `imitation_enabled` | `True` | Disable imitation specifically while mutation stays active (the "no imitation" ablation). `True` reproduces the original Level-0 behaviour exactly. |

## Perturbations — Level 0.1, Work Package G; extended Level 0.2, Work Package J

`perturbations`: a tuple of mappings, each `{start_step: int >= 0,
duration: int >= 1, kind: str, magnitude: float in [0,1]}`. `kind` must
be one of `VALID_PERTURBATION_KINDS = ("resource_depletion",
"observation_noise_increase", "subsistence_increase",
"regeneration_reduction")` — the last two added at Level 0.2 to give the
boundary-region perturbation experiment (Work Package J) a demand-side
and a supply-side shock in addition to the original pair.
`subsistence_increase`'s `magnitude` is a *fractional* increase to the
per-agent subsistence charge for the perturbation's duration (e.g. `1.0`
= charge doubles); `regeneration_reduction`'s `magnitude` is the
fractional reduction to the pool's logistic regeneration rate for the
duration (floored at 0, never inverting into growth). Empty by default
(`()`) — perturbations are opt-in per experiment and consume no RNG draws
when absent, so an empty tuple is indistinguishable from the field never
having existed for reproducibility purposes. See `core/perturbation.py`
and `docs/odd_level0.1.md` §7 for exactly what each `kind` does. (Random
edge loss and removal of high-resource agents — two other shock kinds the
Level 0.2 milestone brief named as examples — are **not** implemented:
they would require extending the perturbation interface to also receive
the live graph/agent list, which was out of scope for this pass. Documented
here as a known limitation, not silently dropped — see
`docs/level0.2_scientific_note.md`.)

## Viability state machine — Level 0.2, Work Package B

| field | default | meaning |
|---|---|---|
| `viability_mode` | `"none"` | One of `"none"` \| `"dormancy_recovery"` \| `"removal_replacement"`. `"none"` reproduces Level 0.1 exactly: resources may go arbitrarily negative with zero demographic consequence, and this field has **no effect at all** (zero extra RNG draws, no state transitions computed) unless `ecology_enabled` is also `True`. |
| `viability_deficit_steps_threshold` | `20` | Consecutive steps an agent's resources must stay below `distress_threshold` before it transitions distressed → dormant. Duration-based (a running counter), never a one-step trigger. |
| `viability_recovery_resources` | `0.0` | Resources threshold (`>=`) required to transition back to `active` from either `distressed` or `dormant`. A separate field from `distress_threshold` (not reused) so the recovery bar can sit with hysteresis above the distress bar. |
| `viability_max_dormant_steps` | `50` | Steps an agent may remain dormant before (`removal_replacement` mode only) it is marked nonviable and removed. Advisory bookkeeping only in `dormancy_recovery` mode — nothing removes a dormant agent there. |
| `viability_replacement_policy` | `"random_init"` | `removal_replacement` mode only: what a fresh replacement agent starts with — one of `VALID_REPLACEMENT_POLICIES = ("random_init", "dominant_policy", "parent_lineage_imitation", "mutation_fresh")`. **Never defaults to `dominant_policy`** — that requires explicit opt-in, per the milestone's explicit instruction. |

Every viability-state transition is logged as a `ViabilityTransitionEvent`
(`from_state`, `to_state`, `resources_at_transition`, `cause`); every
removal+replacement is logged as a `ReplacementEvent` recording the old
and new `demographic_id` (fresh, monotonically increasing — distinct from
the unchanging `agent_id`/network-slot index and from `policy_lineage_id`,
which tracks strategy descent, not personhood) and which inheritance rule
fired. See `observer/viability.py` for the run-level aggregation
functions and `docs/level0.2_scientific_note.md` for the three modes'
observed effects.

## Imitation fitness signal — Level 0.2, Work Package C

| field | default | meaning |
|---|---|---|
| `fitness_mode` | `"cumulative_resources"` | One of `VALID_FITNESS_MODES = ("cumulative_resources", "recent_payoff", "resource_delta", "viability_adjusted")`. `"cumulative_resources"` reproduces Level 0.1's Fermi-rule-over-total-resources imitation signal exactly. See `agents/fitness.py` for each mode's definition and translation-invariance rationale, and `tests/test_fitness.py` for the formal invariance tests. |
| `fitness_window` | `20` | Rolling-window length (steps) for the `recent_payoff` and `resource_delta` signals. |
| `viability_adjusted_dormant_penalty` | `10.0` | `viability_adjusted` mode only: fixed, finite penalty subtracted from a dormant agent's `recent_payoff`-based fitness signal — makes a dormant agent's strategy unlikely, never impossible, to be imitated. |

No fitness mode is asserted "more correct" than another in advance — see
`docs/level0.2_scientific_note.md` for the empirical translation-invariance
and outcome comparisons across all four.

## `seed`

Integer, `>= 0`. The single seed for the run's one
`numpy.random.Generator` (`core/rng.py`) — every stochastic draw in the
codebase passes through it.

## Local ecological patches and niche construction — Level 0.3, Work Packages A-D

Only meaningful when `ecology_topology="patches"`; under the default
`"global_pool"` these fields exist but are never read, consuming zero
extra RNG draws and leaving Level 0.2's exact code path untouched (see
`docs/odd_level0.3_addendum.md` §13 for the full compatibility argument).

| field | default | meaning |
|---|---|---|
| `ecology_topology` | `"global_pool"` | `"global_pool"` (default) = the single shared pool, byte-for-byte Level 0.2 behavior. `"patches"` activates a fixed collection of independent `ResourcePatch` objects and, with it, the entire ecological-action apparatus below. |
| `n_patches` | `4` | Number of independent patches when `ecology_topology="patches"`. |
| `patch_capacity` | `500.0` | `K_j` — per-patch carrying capacity, shared nominally by every patch; per-patch heterogeneity is expressed via `patch_quality_std`, not by varying capacity directly. |
| `patch_regen_rate` | `0.5` | `r_j` (nominal) — per-patch logistic regeneration rate, before the patch's own quality multiplier. |
| `patch_initial_fraction` | `0.5` | Each patch starts at this fraction of `patch_capacity`. |
| `patch_quality_std` | `0.0` | Std. dev. of each patch's productivity multiplier, drawn once at init from `Normal(1.0, patch_quality_std)`, clipped to a small positive floor. `0.0` (default) = every patch has identical quality 1.0 — a neutral no-op. |
| `patch_assignment_mode` | `"network_neighborhood"` | Neutral rule assigning each agent to exactly one patch, once, at initialization — never migrates. `"network_neighborhood"` (multi-source BFS partition tied to initial network structure) or `"random_assignment"` (pure random). |
| `extraction_propensity_mean/std` | `0.5` / `0.2` | Ecological-policy trait distribution (see `agents/ecological_policy.py`) — same `Normal(mean, std)`-then-clip convention as every other heterogeneous trait in this project. |
| `maintenance_propensity_mean/std` | `0.3` / `0.2` | Same convention. |
| `scarcity_sensitivity_mean/std` | `0.3` / `0.2` | Same convention. |
| `ecological_harvest_unit` | `5.0` | Scale constant converting a `[0,1]` extraction propensity into a resource-unit request (`agents/ecological_policy.py::decide_ecological_action`). Preliminary-calibration constant — see the calibration-gap note below and `docs/level0.3_scientific_note.md` §6. |
| `ecological_maintenance_unit` | `5.0` | Same, for the maintenance investment. |
| `maintenance_efficiency` | `0.7` | `eta_m` — fraction of invested maintenance that actually reaches the patch (must be `< 1` to be meaningfully inefficient; values up to `1.0` accepted). |
| `ecological_search_cost` | `0.0` | Per-step cost paid by every agent regardless of extraction success, on top of the maintenance investment's own cost. `0.0` (default) = no extra effort cost. |
| `ecological_allocation_rule` | `"proportional"` | How excess simultaneous extraction demand within one patch is rationed — `"proportional"` or `"sequential_random"` (see `environment/patches.py::allocate_extraction`). |
| `ecological_actions_affect_patch` | `True` | **WP-F counterfactual ("no environmental effect").** `False`: agents still decide and still pay/earn on their own ledgers, but the patch's own stock is left untouched by any agent action — only natural regeneration runs. |
| `ecological_policy_randomized_each_step` | `False` | **WP-F counterfactual ("randomized ecological policy").** `True`: every agent's per-step decision uses a fresh i.i.d. draw from the trait distributions instead of its own inherited policy (which is left untouched but has no behavioral consequence). |
| `ecological_policy_shuffle` | `False` | **WP-F counterfactual ("replay/policy-shuffle").** `True`: the initially-drawn ecological policies are permuted across agents once at init — the exact marginal distribution is preserved, but any correlation with agent identity/patch is broken. |

## Ecological-policy learning — Level 0.3, Work Package D

| field | default | meaning |
|---|---|---|
| `ecological_imitation_enabled` | `True` | **WP-F counterfactual ("frozen ecological policy")** is expressed by setting this `False` (no separate flag needed): policies are drawn once at init and never imitated. |
| `ecological_mutation_rate` | `0.01` | Independent of (may differ from) the social `mutation_rate`. |
| `fitness_mode_ecological` | `"cumulative_resources"` | The fitness signal used for *ecological*-policy imitation specifically — one of the same `VALID_FITNESS_MODES` as `fitness_mode`; may differ from it. Neither is asserted more correct. |
| `ecological_inheritance_mode` | `"independent"` | How the two behavioral dimensions' inheritance is coupled during the adaptation round. `"independent"` (default): social and ecological each get their own peer draw, never entangled. `"coupled_same_model"`: one peer draw and one Fermi decision drives both dimensions together. Only 2 of the milestone's 4 named modes are distinguishable given the current one-peer-per-round imitation architecture — a documented limitation, not a partial implementation (see `docs/level0.3_scientific_note.md` §8). |

**Calibration note:** `ecological_harvest_unit`/`ecological_maintenance_unit`/
`maintenance_efficiency`/`patch_capacity`/`patch_regen_rate`'s literal
defaults above were set as a first pass, without the "small preliminary
calibration" the milestone brief allows for actually being carried out —
individual seeds under these defaults frequently collapse to near-total
patch depletion within the first 60-100 steps. This was discovered late
(while building visualizations) and is documented in full, including its
consequences for how to read the WP-F/WP-J experiment results, in
`docs/level0.3_scientific_note.md` §6 and `dev_mem/status_update.md`'s
Level 0.3 "Important correction" entry — the values are reported as used,
not silently retuned.

## Level 0.3 experiment scripts (Work Packages F, G, H, J)

- `experiments/niche_causal_interventions.py` (WP-F) — runs the
  `level03_patches_default` ("endogenous") condition against the four
  `level03_no_environmental_effect` / `level03_frozen_ecological_policy` /
  `level03_randomized_ecological_policy` / `level03_policy_shuffle`
  presets, paired by identical seed; feeds
  `observer/regulation_diagnostics.py::feedback_dependence`/
  `nontriviality`.
- `experiments/niche_viability_threshold_sweep.py` (WP-G) — sweeps
  `distress_threshold` x `viability_deficit_steps_threshold` x
  `viability_mode` on top of `level03_viability_sweep_base`.
- `experiments/niche_phase_search.py` (WP-H) — `PARAM_NAMES`/
  `PARAM_LOWS`/`PARAM_HIGHS` define the 11-axis Latin Hypercube design
  built on top of `level03_phase_search_base`; region labels come from
  `observer/regulation_diagnostics.py::nonstationary_classification`,
  computed strictly post-hoc.
- `experiments/niche_perturbation_recovery.py` (WP-J) — `SHOCK_TYPES`
  define the seven shocks applied on top of `level03_perturbation_base`
  (four patch/environment shocks via `perturbations`/direct mutation,
  three agent-removal variants via `_remove_agents`); feeds
  `observer/regulation_diagnostics.py::perturbation_recovery`.

See `docs/level0.3_scientific_note.md` for what each script found and
`docs/odd_level0.3_addendum.md` for the full process/equations
specification.

## Presets

`SimulationConfig.level0_compat(**overrides)` — sets `ecology_enabled=False,
relationship_dynamics_enabled=False, perturbations=()`, all other fields
at their normal defaults unless overridden. Reproduces the pre-Level-0.1
code path's exact RNG draw sequence and resource dynamics; this is what
`tests/test_compat_regression.py` checks byte-for-byte against
`outputs/level0_default/metrics.csv`.

`SimulationConfig.level02_compat(**overrides)` — sets
`ecology_topology="global_pool"` explicitly (already the default; this
preset exists so callers can name the intent rather than relying on an
unstated invariant). Every Level 0.1/0.2 field stays at its normal
(ecology and relationship-dynamics both *on*) default.

`SimulationConfig.level03_patches_default(**overrides)` — sets
`ecology_topology="patches"`, every other Level 0.3 field at its normal
endogenous-feedback default. The condition every WP-F counterfactual
preset below is a controlled, single-flag deviation from.

`SimulationConfig.level03_no_environmental_effect` /
`level03_frozen_ecological_policy` / `level03_randomized_ecological_policy`
/ `level03_policy_shuffle` (**overrides**) — the four WP-F causal-
intervention presets; each is `level03_patches_default` plus exactly the
one flag named in its table row above.

`SimulationConfig.level03_viability_sweep_base` /
`level03_phase_search_base` / `level03_perturbation_base` (**overrides**)
— base presets for WP-G/H/J respectively (patches active; WP-G also pins
`viability_mode="dormancy_recovery"`); callers vary the milestone's named
parameter axes on top via `overrides`/`dataclasses.replace`, never these
presets' own defaults (deliberately unremarkable, not pre-tuned toward
any outcome).

## Example config files (`experiments/configs/`)

- `level0_default.yaml` — the original, pre-Level-0.1 file, kept for
  provenance. **Loading it today fills in Level 0.1's *defaults* for the
  fields it predates** (ecology and relationship dynamics both on) —
  it does *not* reproduce Level 0 behaviour by itself.
- `level0_compat.yaml` — `level0_compat(seed=0)`, serialized; every field
  explicit, exact reproduction of the original dynamics.
- `level01_default.yaml` — `SimulationConfig(seed=0)`, serialized; every
  Level 0.1 field explicit at its current default.

## Ensemble/ablation configuration grid

`experiments/ensemble.py::BASELINE_CONDITIONS` and `::ABLATIONS` define
the milestone's required condition/ablation grid as plain dicts of
`SimulationConfig` field overrides — see that module for the exact
overrides used for each of the 3 baseline conditions and 7 ablations, and
`dev_mem/status_update.md`'s newest entry for the rationale behind each
ablation's specific choice of override (e.g. why "no memory" uses
`memory_length=1` rather than 0).

## Level 0.2 experiment scripts

- `experiments/phase_sweep.py::PARAM_RANGES` — the six ecological
  parameters swept for the coarse Stage-1 Latin Hypercube design
  (`environment_regen_rate`, `environment_capacity`, `subsistence_cost`,
  `payoff_temptation`, `payoff_reward`, `distress_threshold`), and
  `BOUNDARY_*` — the explicit, documented thresholds used to select
  Stage-2 boundary regions from Stage-1 results (ecological-dynamics
  columns only — never cooperation).
- `experiments/boundary_perturbation.py::SHOCK_KINDS` — the shock
  kinds/magnitudes applied at each selected boundary region for Work
  Package J.
- `experiments/turnover_boundary_sweep.py::AXIS_SWEEPS` — the one-axis-
  at-a-time relationship-dynamics parameter levels swept at each boundary
  region for Work Package G.
- `experiments/null_model_comparisons.py::VIABILITY_MODES`,
  `::FITNESS_MODES`, and `build_slices()` — the four required 2-way
  factorial comparisons for Work Package H.
- `experiments/cooperation_ecology_causality.py` — Work Package F.
  `cross_sectional_by_point()`/`pooled_confounded_correlation()` compare
  cooperation-vs-ecology association within a fixed parameter point
  (across seeds) against the naive pooled-across-points figure, reading
  `phase_sweep.py`'s completed manifest directly (no new runs);
  `lag_correlations()`/`incremental_r2()` measure within-run lead/lag
  structure and directional predictive power (explicitly not labelled
  Granger causality) from a fresh small time-series sample of the three
  representative regions.

See `docs/level0.2_scientific_note.md` for what each script found and
`README.md`'s "Run the Level 0.2 phase-mapping pipeline" section for the
exact commands, in dependency order.

## Level 0.3b — regime validation and causal replication

Level 0.3b adds **no new `SimulationConfig` field**. Every script listed
below runs the exact same config surface Level 0.3 left, combined in new
ways on the observer/experiment side — see `docs/odd_level0.3b_addendum.md`
§4 for the full condition-to-override table (the seven primary causal
conditions plus the preserved `impact_disabled` condition are all
combinations of existing fields, e.g. `ecological_harvest_unit=0.0` +
`ecological_maintenance_unit=0.0` for `environment_only`).

- `observer/regulation_diagnostics.py` — Work Package A section
  (`classify_regime`, `CLASSIFIER_VERSION="0.3b-v1"`, plus 8 supporting
  diagnostics) and Work Package J section (`recovery_eligibility`,
  `recovery_quality`, `assess_perturbation_recovery`) — both appended
  after, and independent of, Level 0.3's original seven-criterion module.
- `experiments/level03b_phase_search_reanalysis.py` — Work Package B:
  deterministic reproduction and reclassification of Level 0.3's
  committed 48-run phase search.
- `experiments/level03b_supplemental_search.py` — the single prespecified
  supplemental LHS batch (design seed `20260817201`), invoked only
  because the reanalysis found no eligible interior-persistent or
  nonstationary candidate.
- `experiments/level03b_candidate_registry.py` — Work Package C: writes
  `outputs/level03b_candidate_registry/candidate_registry.json`, the
  single source every downstream script below reads from (never
  re-selects).
- `experiments/level03b_common.py::CONDITION_OVERRIDES` — the causal-
  condition override table referenced above, shared by every script
  below that builds a candidate's `SimulationConfig`.
- `experiments/level03b_confirmation.py` — Work Package D: 24-seed,
  600-step confirmation of each registered candidate.
- `experiments/level03b_neighborhood_robustness.py` — Work Package E:
  applies the Level 0.3 parameter-neighborhood-robustness diagnostic to
  real confirmation output for the first time.
- `experiments/level03b_causal_interventions.py` — Work Packages F/G:
  the 7(+1) causal conditions at 20 (primary) / 12 (secondary) matched
  seeds, with seed-level paired continuous-outcome effects and bootstrap
  CIs.
- `experiments/level03b_fitness_stream.py` — Work Package H: crosses the
  existing `ecological_inheritance_mode` field (`"independent"` =
  ecological fitness stream, `"coupled_same_model"` = total fitness
  stream) with `endogenous`/`frozen`/`randomized`/`environment_only`.
- `experiments/level03b_micro_macro_linkage.py` — Work Package I: applies
  the Level 0.3 micro-macro-linkage diagnostic to real Work Package D/F
  output for the first time.
- `experiments/level03b_confirmatory_perturbation.py` — Work Package K:
  the 7-shock perturbation-recovery experiment at registered candidates,
  using the repaired eligibility-screened recovery definition; reuses
  Level 0.3's `niche_perturbation_recovery.py` shock implementations
  unchanged.

See `docs/level0.3b_validation_note.md` for what each script found and
`dev_mem/status_update.md`'s Level 0.3b entry for the exact commands and
scale-reduction notes, in work-package order.

## Level 1.0 — locally shared, patch-attached rules

All fields below default to an exact Level-0.3b-compatible no-op
(`rule_formation_enabled=False`; see `docs/odd_level1.0.md` §11 and
`tests/test_level1_rule_formation.py::TestBackwardCompatibility`).

- `rule_formation_enabled: bool = False` — master switch; also requires
  `ecology_topology="patches"` (validated) since a rule attaches to a
  patch.
- Proposal traits (drawn per-agent in `build_agents`, only when the
  switch above is `True`): `proposal_probability_mean/_std`,
  `proposal_probability_scarcity_sensitivity` (H1 — local-occupancy-
  scaled proposal probability, an agent trait, not an experimenter
  threshold), `preferred_extraction_ceiling_mean/_std`,
  `preferred_maintenance_requirement_mean/_std`,
  `preferred_monitoring_intensity_mean/_std`,
  `preferred_sanction_magnitude_mean/_std`,
  `preferred_adoption_threshold_mean/_std`,
  `preferred_amendment_threshold_mean/_std`, `rule_mutation_rate`,
  `rule_mutation_std` (Work Package G reconstruction: bounded
  perturbation of an existing lineage, distinct from ecological-policy
  mutation's fresh redraw).
- Adoption: `adoption_process ∈ {"unweighted_voting",
  "resource_weighted_voting"}`, `proposal_window_steps`.
- Membership/compliance traits: `willingness_to_join_mean/_std`,
  `willingness_to_monitor_mean/_std`, `sanction_preference_mean/_std`,
  `violation_tolerance_mean/_std`, `amendment_propensity_mean/_std`,
  `institutional_decision_noise_std`, `membership_exit_cost`.
- Monitoring (Work Package E): `monitoring_mode ∈ {"none", "voluntary",
  "designated", "perfect"}`, `monitoring_cost`,
  `monitoring_detection_accuracy`, `monitoring_false_positive_rate`,
  `monitor_rotation_period_steps`.
- Collective sanctioning (Work Package F): `sanction_mode ∈ {"none",
  "voluntary", "collective_fund", "imposed_perfect"}`,
  `sanction_cost_per_unit` (cost to the sanctioning party),
  `sanction_penalty_unit` (converts `[0,1]`-scale `sanction_magnitude`
  into resource units removed from the target — distinct from
  `sanction_cost_per_unit`), `institutional_fund_contribution_rate`.
- Dissolution (Work Package H): `rule_dissolution_membership_floor`,
  `rule_dissolution_support_floor`, `rule_inactive_dissolution_steps`,
  `rule_fund_depletion_dissolution_steps`.
- Mechanical benchmarks (Stage 4 conditions 7/8): `institution_imposed_
  mode`, `imposed_rule_extraction_ceiling/_maintenance_requirement/
  _monitoring_intensity/_sanction_magnitude`;
  `randomized_pseudo_institution_mode`,
  `randomized_pseudo_institution_compliance_probability`.

New generative-layer module: `rules/shared_rule.py` (`RuleParameters`,
`SharedRule`) and `rules/dynamics.py` (the round functions — compliance
decision, monitoring, sanctioning, proposal/adoption, membership,
amendment, dissolution). New observer module:
`observer/institution_diagnostics.py` (Work Packages J/K).

Level 1.0-specific `SimulationConfig` presets (`core/config.py`):
`level1_rule_formation_default`, `level1_no_institution`,
`level1_proposals_only`, `level1_monitoring_only`,
`level1_sanction_without_reliable_monitoring`,
`level1_monitoring_plus_voluntary_sanction`,
`level1_monitoring_plus_collective_sanction`, `level1_imposed_rule`,
`level1_randomized_pseudo_institution` — each maps directly to one of
Stage 4's 11 named institutional counterfactual conditions.

Level 1.0 experiment scripts (`experiments/level1_*.py`):
`level1_preflight_fitness_stream_rerun.py` (the mandatory preflight
audit's affected-cell rerun — see `dev_mem/status_update.md`),
`level1_common.py` (shared config/run/summarize helpers, reads the
existing `outputs/level03b_candidate_registry/candidate_registry.json`),
`level1_stage1_calibration.py`, `level1_stage2_search.py` +
`level1_stage2_search_secondary.py` + `level1_stage2_analysis.py`,
`level1_stage3_confirmatory.py`, `level1_stage4_counterfactuals.py`,
`level1_shocks.py`. See `docs/level1.0_scientific_note.md` for what each
found and every documented scale reduction from the milestone's literal
numbers.

## Level 1.1: delegation, administrative capacity, and institutional scale

Master no-op flags (each strict, verified byte-for-byte identical to
Level 1.0 when left at its default — `tests/test_level11_compatibility.py`):
`delegation_enabled` (default `False`), `interpatch_coordination_enabled`
(default `False`), `contribution_mode` (default `"none"`).
`delegation_enabled`/`interpatch_coordination_enabled` each require
`rule_formation_enabled=True` (a delegate/link attaches to a rule).

- Delegation (Work Package D): `delegated_tasks` (subset of
  `{"monitoring", "resource_accounting", "sanction_execution",
  "maintenance_coordination", "interpatch_communication"}`),
  `delegate_selection_procedure` (one of `"voluntary_approval",
  "plurality_support", "threshold_acceptance", "lottery"`),
  `delegate_selection_support_threshold`,
  `delegate_nomination_window_steps`, five
  `delegate_evaluation_*_weight` fields (reliability, competence, trust,
  resource, cost-aversion).
- Administrative capacity (Work Package E): `delegation_task_cost`,
  `delegation_workload_penalty_per_task`, `delegation_scale_coefficient`,
  `delegation_capacity_learning_weight`,
  `delegation_inactivity_decay_rate`, `institutional_memory_retention`,
  `institutional_memory_transfer_to_new_delegate`.
- Discretion/appropriation (Work Package F): `discretion_enabled`,
  `appropriation_opportunity_scale`, `appropriation_fraction_of_fund`,
  `effort_reduction_opportunity_scale`.
- Accountability/constraint (Work Package G): `accountability_enabled`,
  `audit_probability_scale`, `audit_accuracy`, `audit_cost`,
  `recall_support_threshold`, `recall_fund_recovery_fraction`,
  `appeal_probability`, `appeal_accuracy_true_positive`,
  `appeal_accuracy_false_positive`, `appeal_refund_fraction`,
  `appeal_cost`.
- Collective contributions (Work Package H): `contribution_mode` (one of
  `"none", "equal", "voluntary", "proportional", "negotiated"`),
  `contribution_period_steps`, `contribution_amount`,
  `contribution_proportional_rate`, `fund_dissolution_disposition` (one
  of `"distributed_to_members", "lost", "retained_for_reconstruction"`).
- Interpatch coordination (Work Package I):
  `interpatch_coordination_enabled`, `coordination_proposal_probability`,
  `coordination_proposal_window_steps`,
  `coordination_activity_probability`, `coordination_info_error_std`,
  `coordination_cost_per_step`, `coordination_assistance_transfer_
  fraction`, `coordination_assistance_occupancy_threshold`,
  `coordination_dissolution_probability`.

New generative-layer modules: `rules/delegation.py` (`Delegate`,
nomination/selection/task-performance/accountability round functions —
Work Packages D/E/F/G), `rules/contributions.py` (contribution round,
administrative spending, dissolution-fund disposition — Work Package H),
`rules/coordination.py` (`CoordinationLink`, the coordination round —
Work Package I). New observer modules:
`observer/replication_units.py` (Work Package A: unit-of-analysis,
naive/seed-clustered/hierarchical bootstrap), `observer/delegation_
diagnostics.py` (Work Packages J/K), plus Work Package B/C additions to
the existing `observer/institution_diagnostics.py`
(`welfare_accounting`, `seed_level_welfare_contrast`,
`eligible_active_rules`, `survival_after_event`, `eligible_dissolutions`,
`reconstruction_metrics`, `lineage_chain`).

Level 1.1-specific `SimulationConfig` presets (`core/config.py`):
`level10_compat`, `level11_delegation_only`, `level11_capacity_only`
(alias of `level11_delegation_only`), `level11_accountability_only`,
`level11_coordination_only`, `level11_complete`, `level11_no_memory`,
`level11_no_accountability`, `level11_no_admin_cost`,
`level11_no_interpatch_coordination`.

Level 1.1 experiment scripts (`experiments/level11_*.py`):
`level11_common.py` (shared run/summarize helpers),
`level11_stage1_activation.py`, `level11_stage2_compatibility_ablations.py`,
`level11_stage3_search.py`, `level11_stage4_confirmatory.py`,
`level11_stage5_causal_decomposition.py`, `level11_stage6_shocks.py`,
`make_level11_visualizations.py`. See `docs/level1.1_scientific_note.md`
for what each found and every documented scale reduction from the
milestone's literal numbers.

## Level 1.1b: causal and measurement validation

Work Package A (RNG architecture) — see `docs/level1.1b_rng_design.md`
for the full account:

- `rng_mode`: one of `"legacy_single_stream"` (default — every mechanism
  resolves to the single pre-existing shared `Generator`, byte-for-byte
  Level 1.1 behavior) or `"mechanism_substreams"` (each name in
  `core.rng.STREAM_REGISTRY` gets its own independent `Generator`,
  spawned once via `numpy.random.SeedSequence(seed).spawn()` —
  **required for every Level 1.1b causal experiment**).
- `rng_registry_version`: informational; set from
  `core.rng.RNG_REGISTRY_VERSION` (`"level11b_v1"`), exported into every
  run's `config.yaml` manifest alongside `rng_mode`.
- New presets (`core/config.py`), experimental conveniences and not
  governance types: `level11_legacy_compat` (`level11_complete` with
  `rng_mode="legacy_single_stream"` made explicit),
  `level11b_substreams` (`level11_complete` with
  `rng_mode="mechanism_substreams"`).
- New tests: `tests/test_level11b_rng_substreams.py` (26 tests —
  registry determinism/versioning, legacy-mode exact-compat, substream
  reproducibility, serial-vs-multiprocess and cross-process stability,
  observer/generative separation, mechanism-ablation draw isolation, the
  `discretion_rng` split).

Work Package B (artifact-independent testing) added no new config
surface — it reworked `tests/test_level03b_pipeline.py` to skip with a
precise reason when historical artifacts are absent and added
in-fixture/pure-function companion tests, and fixed
`experiments/level03b_phase_search_reanalysis.py`'s `run(n_steps=...)`
silently ignoring its own argument. See `dev_mem/status_update.md`'s
2026-08-17 entries for the full account.

Work Package C (interpatch-coordination calibration):

- `level11b_coordination_nondegenerate` preset (`core/config.py`): built
  on `level11b_substreams` with `coordination_proposal_window_steps=1`
  (down from the default 5), removing the multi-attempt retry structure
  so empirical acceptance directly reflects the underlying ~0.5
  per-attempt propensity (typically 35–65% accepted) instead of the
  ~97% *eventual* acceptance the default window produces. The default
  `coordination_proposal_window_steps=5` itself is **unchanged** — the
  historical "72/72" result is explained (see
  `experiments/level11b_coordination_calibration.py` and
  `tests/test_level11b_coordination.py`), not a bug requiring a default
  change.
- New tests: `tests/test_level11b_coordination.py` (8 tests).

Work Package D (appropriation opportunity-vs-conduct decomposition):

- New `AppropriationOpportunityEvent` (`core/events.py`, logged in
  `EventLog.appropriation_opportunities`) fires every time a delegate
  has a nonzero-fund opportunity to appropriate, **regardless of
  whether they attempt it** — unlike the pre-existing
  `AppropriationEvent`, which only fires on an actual appropriation.
  Enables separating opportunity (did fund availability change?) from
  conduct (did attempt propensity or conditional intensity change?).
  No new config fields; `appropriation_opportunity_scale` and
  `appropriation_fraction_of_fund` (pre-existing) are the fields this
  decomposition reads.
- New experiment: `experiments/level11b_appropriation_decomposition.py`
  (12-seed matched `mechanism_substreams` contrast, seed-clustered
  paired bootstrap, `BOOTSTRAP_SEED=20261`).
- New tests: `tests/test_level11b_appropriation.py` (7 tests).

Work Package E (accountability activity vs. effective constraint):

- `audit_enabled: bool = True`, `recall_enabled: bool = True`,
  `appeal_enabled: bool = True` (`core/config.py`, right after
  `accountability_enabled`) — sub-flags gating each accountability
  component independently. **Architectural coupling documented in the
  field docstrings**: a recall can only be triggered by an audit
  finding in this implementation, so `recall_enabled=True` with
  `audit_enabled=False` produces zero recalls (no audit ever fires to
  trigger one) — there is no code path for an isolated "recall only"
  condition; the `level11b_accountability_recall_only` preset below is
  documented and reported as "audit+recall, no appeal," not a genuinely
  isolated recall condition.
- New presets, all built on `level11b_substreams` (matched-seed causal
  work requires substream mode): `level11b_accountability_audit_only`
  (audit only, recall/appeal structurally cannot fire),
  `level11b_accountability_appeal_only` (appeal only — the one
  genuinely architecture-independent isolation of the three),
  `level11b_accountability_recall_only` (audit+recall, no appeal — see
  the coupling note above), `level11b_accountability_costless` (full
  accountability, `audit_cost=0.0`/`appeal_cost=0.0`),
  `level11b_accountability_perfect_info` (full accountability,
  `audit_accuracy=1.0`), `level11b_accountability_randomized_placebo`
  (full accountability, `audit_accuracy=0.5` — a coin flip carrying no
  real detection signal, used as the contrast case for
  activity-vs-effective-constraint).
- New observer module `observer/accountability_diagnostics.py`, two
  deliberately separate read-only functions over an `EventLog`:
  `accountability_activity()` (purely descriptive machinery-ran counts
  — audits/recall-votes/appeals attempted, regardless of correctness)
  and `effective_constraint()` (realized-outcome-only: true-positive
  detections, successfully recovered funds, justified appeal
  corrections — computed strictly from event ground truth, never from
  `config.accountability_enabled` or any other config flag; every
  denominator-undefined rate returns `None`, never `0.0`).
  `effective_constraint()`'s `effectively_constrained` field requires a
  realized true-positive detection AND (a successful recall or a
  successful recall count > 0) — config-flag presence alone never
  qualifies.
- New experiment: `experiments/level11b_accountability_conditions.py`
  (12-seed matched sweep across all 8 named conditions — no
  accountability, audit only, appeal only, recall only, full, costless,
  perfect info, randomized placebo — reporting both
  `accountability_activity` and `effective_constraint` per condition,
  plus seed-clustered bootstrap contrasts on both gross
  `total_appropriated` and **net** `net_appropriated` (gross minus
  `total_recovered_funds` — the more meaningful "what actually stuck"
  measure, since a successful recall recovers funds after an act
  already happened rather than un-happening it). **Anomalous results,
  reported unchanged rather than reframed**: (1) gross
  `total_appropriated` is *higher* under full accountability than under
  none at all (95% CI excludes zero in the positive direction) — driven
  by recall-triggered delegate turnover increasing the count of
  appropriation *opportunities*, not by delegates attempting more; (2)
  `randomized_placebo` and `perfect_info` did **not** produce matched
  audit-activity volumes as originally designed (a genuine
  detection-accuracy → recall → replacement → more-audits feedback
  loop), so the intended clean "same activity, different constraint"
  contrast is confounded and reported as such. The one clean
  confirmatory result at n=12 seeds: net appropriation is
  indistinguishable from the no-accountability baseline under
  `randomized_placebo` (CI includes zero) but significantly *lower*
  under `perfect_info` (CI excludes zero, negative) — i.e. activity
  alone does not reduce net appropriation, accurate detection does.
- New tests: `tests/test_level11b_accountability.py` (11 tests —
  component ablations, the activity/effective-constraint arithmetic
  split on synthetic event logs, and a full-run placebo-vs-perfect-info
  contrast).

Work Package F (institutional memory validation) added no new config
fields — `institutional_memory_retention`/
`institutional_memory_transfer_to_new_delegate` (pre-existing, defaults
0.3/0.5 unchanged) are read directly by the sweep script:

- New experiment:
  `experiments/level11b_institutional_memory_validation.py` (15-seed
  matched `mechanism_substreams` sweep across 5 (retention, transfer)
  conditions: `no_memory` (0.0, 0.5), `default` (0.3, 0.5), `moderate`
  (0.6, 0.5), `high_retention` (1.0, 0.5), `max_dose` (1.0, 1.0) —
  outputs to `outputs/level11b_institutional_memory_validation/`).
  Two outcome measures per successor delegate, both from `EventLog`
  ground truth: `institutional_memory_inherited` on
  `DelegateAppointmentEvent` (the dose actually delivered) and each
  successor's own last `TaskPerformanceEvent.capacity_before` in the run
  (a realized-capacity proxy). Seed-clustered paired bootstrap
  (`BOOTSTRAP_SEED=20263`) against the `no_memory` baseline.
  **Refined finding, not a simple confirm/refute of Level 1.1's
  "negligible effect" claim**: at n=15 seeds the paired design is
  powerful enough to detect even the default condition's effect on mean
  end-capacity as statistically nonzero (95% CI entirely positive,
  excludes zero) — so the mechanism is not literally inert — but its
  *practical* magnitude at Level 1.1's own default parameters is ~0.2%
  relative to baseline capacity, versus ~25% at the `max_dose` ceiling
  condition (also CI-excludes-zero, much larger in absolute terms). The
  effect scales monotonically with dose across all four non-baseline
  conditions. Conclusion: institutional memory is a real, working,
  monotonic dose-response mechanism, correctly negligible in practical
  (not statistical) terms at the specific calibration Level 1.1 chose —
  not a broken or inert one. A plausible but unconfirmed contributing
  factor for why even `max_dose` doesn't produce a larger effect:
  recall-triggered turnover disproportionately removes delegates who
  committed misconduct, whose own `record_quality` was often already
  low at removal, independent of the retention/transfer attenuation
  itself.
- New tests: `tests/test_level11b_institutional_memory.py` (8 tests —
  direct unit-level verification of the retention×transfer
  multiplication and the overwrite-not-accumulate rule on
  `nomination_and_selection_round`, plus two small-scale sweep-script
  smoke tests).

Work Package G (functional shock recovery) added no new config fields —
it reads `level11b_substreams`'s own defaults (accountability/recall on)
directly:

- New experiment: `experiments/level11b_functional_shock_recovery.py`
  (15-seed matched `mechanism_substreams` run,
  `outputs/level11b_functional_shock_recovery/`). Defines a "shock" as
  a `DelegateRemovalEvent` with `reason == "recalled"`; "reappointed" as
  a same-`rule_id` `DelegateAppointmentEvent` within
  `REAPPOINTMENT_WINDOW_STEPS=30` steps; "functional recovery" via
  `recovery_gap = post_shock_capacity - pre_shock_capacity` (a bounded
  difference, not a ratio — capacity sits near 0 often enough at shock
  time that a ratio numerically explodes) computed from
  `TaskPerformanceEvent.capacity_before`, reported at two thresholds
  (`full`: gap≥0; `within_tolerance`: gap≥−0.05) plus the continuous
  mean/median gap itself, and a second independent completion-rate
  dimension (successes/attempts, pre- vs. post-shock).
  **Confirmatory result** (seed-clustered, seed as primary unit, 5000
  resamples, `BOOTSTRAP_SEED=20264`): reappointment_rate=97.5% (95% CI
  [96.4%, 98.4%]) — reproducing Level 1.1's near-100% reappointment
  finding — while full functional recovery (gap≥0) is only 32.2% (CI
  [30.4%, 34.5%]) and within-tolerance recovery only 53.6% (CI [52.0%,
  55.2%]); mean_recovery_gap is −0.10 (CI [−0.11, −0.087], excludes
  zero) — capacity is systematically LOWER after a shock than before
  it, even though mean_pre_shock_completion_rate (0.492) and
  mean_post_shock_completion_rate (0.492) are statistically
  indistinguishable. **Mechanistic explanation, not just an observed
  gap**: `Delegate.capacity` is `0.5*completion_rate + 0.3*record_
  quality + 0.2*experience_term`, and `experience_term =
  min(1, task_attempts/50)` necessarily restarts at 0 for every new
  office-holder regardless of predecessor quality — completion rate (an
  agent-trait-driven, near-immediate quantity) recovers essentially
  fully within the window, while capacity (which partly encodes
  accumulated tenure) structurally cannot, by construction, recover
  within a 40-step window. Reappointment and functional recovery are
  therefore confirmed to be genuinely distinct quantities, exactly as
  this work package was commissioned to demonstrate.
- New tests: `tests/test_level11b_functional_shock_recovery.py` (8
  tests — synthetic-`EventLog` cases covering reappointed-but-not-
  recovered, reappointed-and-recovered, never-reappointed, reappointed-
  but-never-performed-a-task (undefined gap, never coerced to 0),
  empty-log (every rate `None`), non-recall removal reasons excluded, a
  completion-rate/capacity-gap divergence regression guard, plus a
  small-scale full-simulation smoke test).

Work Package H (audited classifier vs. historical classifier) added no
new config fields — it adds a new classifier function alongside the
existing one:

- New function `observer/delegation_diagnostics.classify_delegation_
  audited` — a byte-for-byte structural copy of the existing (Level
  1.1, unchanged) `classify_delegation`, with exactly two ground-truth
  corrections to the accountability-dependent branches only: (1)
  requires a REALIZED true-positive audit detection
  (`AuditEvent.outcome == "true_positive"`) before a recall/appeal can
  count toward `"accountable_delegation"` — the historical classifier
  counts any vote-succeeded recall (`RecallEvent.succeeded`) regardless
  of whether it recovered any funds or was ever triggered by a genuine
  detection; (2) only counts an upheld appeal toward
  `"accountable_delegation"` when `was_false_sanction=True` (a
  genuinely corrective outcome) — the historical classifier's
  `n_appeals_upheld` counts every upheld appeal including an
  *unjustified overturn* (`was_false_sanction=False, upheld=True`, i.e.
  the appeals process wrongly letting a guilty party off), which is
  backwards. `VALID_LABELS` and every non-accountability branch
  (duration-gating, coordination, tenure, completion-rate thresholds)
  are unchanged — `classify_delegation` itself is untouched, preserved
  exactly as Level 1.1 left it.
- New experiment:
  `experiments/level11b_audited_classifier_comparison.py` (15-seed
  matched `mechanism_substreams` sweep, `n_patches=6`/
  `population_size=60` — scaled up from other WP scripts' n_patches=3
  specifically because this comparison's unit is "one classified rule
  per patch per run," across 6 accountability conditions — `default_
  full`, `audit_only`, `recall_only`, `costless`, `perfect_info`,
  `randomized_placebo` — outputs to
  `outputs/level11b_audited_classifier_comparison/`). Reports, per
  condition, the `downgrade_rate`: the fraction of the historical
  classifier's own `"accountable_delegation"` calls the audited
  classifier does not also make. **Pooled results (90 classified rules
  per condition)**: `default_full`=0/30 (0%), `audit_only`=0/0
  (undefined — recall and appeal are both structurally disabled in this
  preset, so `"accountable_delegation"` is unreachable by either
  classifier), `costless`=1/30 (3.3%), `recall_only`=2/36 (5.6%),
  `perfect_info`=1/71 (1.4%), `randomized_placebo`=1/5 (20%, but on a
  small denominator — only 5 of 90 rules across all 15 seeds even
  reached a historical `"accountable_delegation"` call under placebo,
  since chance-level detection makes the underlying recall/appeal
  events themselves rarer, not just less trustworthy when they do
  occur). The ordering is broadly consistent with the milestone's
  expectation (lower detection accuracy → higher downgrade rate) but
  the `randomized_placebo` estimate is reported with its small-sample
  caveat explicit, not smoothed over.
- New tests: `tests/test_level11b_audited_classifier.py` (7 tests — a
  vote-succeeded-but-zero-funds-recovered recall is downgraded; an
  unjustified appeal overturn is downgraded; a genuine true-positive +
  recovered recall agrees on both classifiers; a genuinely justified
  appeal correction agrees on both; three non-accountability branches
  — `delegate_selected`, `no_delegation`, `persistent_delegation` —
  produce identical labels under both classifiers, confirming the
  audited version's corrections are scoped exactly where intended and
  nowhere else).

This completes Work Packages A–H. See `docs/level1.1b_completion_report.md`
for the full 7-stage experimental sequence, visualizations, and
synthesis documentation.

## Level 1.2: open institutional evolution and blind phenotype discovery

Full model description: `docs/odd_level1.2_addendum.md`. Full findings:
`docs/level1.2_scientific_note.md`. New config surface, by Work Package
(every field below defaults to `False`/`0.0`/`None` such that a bare
`SimulationConfig()` remains the exact, byte-for-byte pre-Level-1.2
default):

- **Work Package B (local institutional observation)**:
  `institutional_observation_enabled`, `observation_period_steps`,
  `observation_noise_std`, `observation_delay_max_steps`,
  `administrative_report_distortion_scale`. Requires
  `interpatch_coordination_enabled=True`.
- **Work Package C (component-wise transmission)**:
  `institutional_transmission_enabled`, `transmission_mode` (see
  `VALID_TRANSMISSION_MODES`), `transmission_period_steps`,
  `transmission_base_probability`, `transmission_mutation_std`,
  `transmission_recombination_probability`,
  `transmission_failure_probability`. Requires
  `interpatch_coordination_enabled=True`.
- **Work Package D (migration and membership selection)**:
  `migration_enabled`, `migration_evaluation_period_steps`,
  `migration_cost`, `migration_capacity_per_patch`,
  `migration_decision_noise_std`, `migration_propensity_mean`/`_std`
  (drawn per-agent as `Agent.migration_propensity`),
  `membership_exit_enabled`. Requires `ecology_topology="patches"`
  (`migration_enabled` only) — always true for Level 1.2's own
  experiment scripts.
- **Work Package F (institutional scaling)**:
  `institutional_scaling_enabled`, `scaling_admin_overhead_per_patch`
  (may be negative — administrative economies of scale — floored at a
  0.1× cost multiplier). Requires `interpatch_coordination_enabled=True`.
- **Work Package G (environmental heterogeneity)**:
  `patch_quality_spatial_correlation` (an AR(1)-over-patch-index chain;
  `0.0` default = every patch's quality drawn independently, exactly
  matching pre-Level-1.2 behavior). Reuses pre-existing
  `patch_regen_rate`, `patch_quality_std`, `perturbations`,
  `migration_cost`, `coordination_cost_per_step` as its other named
  heterogeneity dimensions — no new fields needed for those.
- **RNG**: `rng_registry_version` default bumped to `"level12_v1"`
  (`core/rng.py::STREAM_REGISTRY` gained 5 appended — never
  inserted — stream names; appending is verified not to perturb any
  pre-existing stream's spawned values). `rng_mode="mechanism_
  substreams"` is **mandatory** for every Level 1.2 causal experiment
  (Section 15), never `"legacy_single_stream"`.
- **New presets** (`core/config.py`, Section 17): `level12_complete`
  (`level11_complete` + all five Level 1.2 mechanism flags +
  `rng_mode="mechanism_substreams"`), and five isolation presets —
  `level12_observation_only`, `level12_transmission_only`,
  `level12_migration_only`, `level12_membership_exit_only`,
  `level12_scaling_only` — each isolating exactly one Work Package's
  mechanism against a Level-1.0-rule-formation-only base.

Blind-discovery pipeline parameters (`observer/phenotype_discovery.py`)
are not `SimulationConfig` fields — they are function parameters/module
constants (`CANDIDATE_METHODS`, `DEFAULT_K_RANGE`,
`MISSINGNESS_STRATEGIES`) documented in
`docs/level1.2_discovery_methodology_note.md`, since they govern
post-hoc observer-side analysis, never a generative run.

## Level 1.2b: ecological feasibility envelope and powered blind institutional-phenotype rediscovery

No new `SimulationConfig` fields — Level 1.2b's own generative runs
(Work Packages E–N) reuse Level 1.2's config surface unchanged;
Work Package N's causal-ablation factors map onto pre-existing fields
(`migration_capacity_per_patch`, `transmission_base_probability`,
`delegation_task_cost`, etc. — see `experiments/level12b_stage_n_
causal_collapse_decomposition.py`'s own `FACTORS` docstring for the
full field-mapping disclosure) rather than introducing new ones.
Section 24 instead adds two things: named config presets, and a shared
result-manifest schema.

- **New presets** (`core/config.py`, Section 24): `level12_compat` (an
  explicit Level-1.2b-named alias for `level12_complete`'s own
  baseline) and seven semantically-named entry points for this
  milestone's own recurring run contexts —
  `level12b_feasibility_map`, `level12b_open_discovery`,
  `level12b_confirmation`, `level12b_failure_analysis`,
  `level12b_sustained_analysis`, `level12b_collapse_ablation`,
  `level12b_scaling_robustness`. **Every one of the eight is a no-op
  by default**: called bare (zero overrides), each returns a config
  identical, field for field, to `level12_complete()`'s own output —
  they exist purely as named entry points, not behavioral variants,
  mirroring Section 17's own presets' "no existing experiment script
  refactored to use them" posture. Every preset inherits `rng_mode=
  "mechanism_substreams"` from `level12_complete`, so Section 24's
  "causal presets use rng_mode=mechanism_substreams" requirement holds
  by construction for all eight.
- **Result-manifest schema** (`experiments/level12b_common.py`,
  Section 24): `build_result_manifest(...)` assembles the twelve
  required provenance fields for a run/experiment — `root_seed`,
  `rng_mode`, `stream_registry_version`, `code_version`, `config_hash`,
  `feasibility_design_hash`, `institutional_design_hash`,
  `preregistration_hash`, `feature_schema_version`,
  `recurrence_criteria_version`, `clustering_pipeline_version`,
  `ic_family`. Five are read directly off `SimulationConfig`/the
  `abm_governance` package (root seed, RNG mode, stream-registry
  version, code version, and the config's own SHA-256 hash); three are
  new version-tag constants added this Work Package (`observer/
  phenotype_feature_audit.py::FEATURE_SCHEMA_VERSION`, `observer/
  recurrence_criteria.py::RECURRENCE_CRITERIA_VERSION`, `observer/
  phenotype_discovery.py::CLUSTERING_PIPELINE_VERSION` — none existed
  before Section 24 required them); the remaining four (the three
  design/preregistration hashes and `ic_family`) are caller-supplied
  per run and default to `None` — explicit non-applicability, never a
  fabricated value, for runs (e.g. Work Package N's fixed-IC causal
  ablations) where a field genuinely does not apply. **Not applied
  retroactively**: Work Packages E–R's own already-frozen, already-
  hashed `design.json`/`manifest.json`/`results.json` artifacts are
  left untouched — this schema is forward-looking, available to any
  future experiment script that calls it, not a retroactive rewrite of
  already-hash-verified output.
