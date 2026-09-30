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
