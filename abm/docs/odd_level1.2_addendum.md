# ODD Addendum — Level 1.2: Open Institutional Evolution and Blind Phenotype Discovery

This addendum documents only what Level 1.2 adds on top of Level 1.1b
(`docs/odd_level1.1b_addendum.md`) and everything it in turn built on
(`docs/odd_level1.1.md`, `docs/odd_level1.0.md`, and earlier). Read
those first. As with every prior addendum, a bare `SimulationConfig()`
run remains byte-for-byte identical to pre-Level-1.2 behavior — nothing
here is described as "the model now does X" without also stating the
exact flag that must be set for X to occur at all.

## 1. Purpose

Level 1.2 asks two linked questions Level 1.1/1.1b's fixed, single-patch,
non-evolving institutional model could not ask: (1) if institutions can
now be locally observed, imperfectly transmitted between patches,
selected for differential persistence, migrated toward, and scaled
across jurisdictions — an *open*, non-designed evolutionary process,
never predefining target packages or fitness peaks — what configurations,
if any, recur? (2) Can a blind (SEM-uninformed) statistical discovery
procedure applied to an observer-only phenotype vector detect such
recurrence at all, and if so, does its count, shape, or existence bear
any relationship to the dissertation's three governance trajectories —
a question the procedure is explicitly forbidden from being tuned
toward answering "yes" or "three" to (Section 3/14's firewall).

**This is not a search for three governance types.** No macro-cluster,
governance label, or expected trajectory count may affect any generative
decision anywhere in this milestone's code — enforced by
`tests/test_level12_structural_guards.py`'s whole-package forbidden-
terminology scan and `tests/test_level12_sem_firewall.py`'s milestone-
level audit.

## 2. Entities, state variables, and scales

New per-institution state: `InstitutionComponents` (`rules/
institution.py`) — a 14-slot component bundle (proposal/adoption/
contribution/monitoring/sanction/appeal/recall/delegation/
administration/authority/amendment/memory/succession/coordination),
distinct from `RuleParameters`. Honest 3-tier accounting: 4 components
are already behaviorally live via `RuleParameters` (unchanged from Level
1.0/1.1); 8 are newly wired live via `SharedRule.institution_overrides`
(a strict no-op unless a value is present); 2 (`proposal_threshold`,
`authority_concentration`) are descriptive-only this milestone, retained
for lineage/transmission bookkeeping and future wiring.

`InstitutionRecord` — full lineage/provenance record: `institution_id`
(= the corresponding rule's own `rule_id`, a 1:1 correspondence in this
milestone's initial wiring), `lineage_id`, `parent_institution_id`,
`origin_mechanism` (`fresh_proposal`/`component_transmission`/
`reconstruction`/`recombination`), `creation_time`,
`active_jurisdiction` (a `frozenset[int]` of patch ids — Work Package F
is what lets this grow beyond one patch), `amendment_history`,
`transmission_history`, `extinction_time`/`extinction_reason`.
Maintained in `Simulation.institution_registry`, derived each step by
diffing `rule_registry` against the existing registry
(`institution_lifecycle_round`) rather than pushed from every rule-
creation call site — a disclosed architectural simplification.

New per-agent state: `Agent.migration_propensity` (drawn once at
`build_agents()` time when `config.migration_enabled`, else `0.0`).

New per-patch capability: `PatchSystem.migrate(agent_id,
destination_patch_id)` — the first-ever cross-patch relocation
primitive in this project's history; structural-only (no decision
logic — that lives in `rules/migration.py`).

Scale: unchanged (patches, steps, population as in Level 1.0/1.1).

## 3. Process overview and scheduling

Six new per-step rounds, all called at the end of `_run_one_step`'s
existing `if self.patch_system is not None:` block, after
`_coordination_round`, in this fixed order:

1. `_institution_lifecycle_round` (Work Package A bookkeeping — always
   runs when rules exist, not gated by any Level 1.2 flag).
2. `_local_observation_round` (Work Package B).
3. `_institution_transmission_round` (Work Package C).
4. `_migration_round` (Work Package D — migration).
5. (membership exit is folded into the migration round's own module,
   `rules/migration.py::membership_exit_round`, called alongside.)
6. `_institutional_scaling_round` (Work Package F).

Two deliberate one-step lags, disclosed rather than engineered away:
an amendment via transmission is picked up by the lifecycle round at
the START of the NEXT step; `jurisdiction_size_by_patch` (read by the
delegation round for administrative overhead) reflects the PREVIOUS
step's coordination-link state, since this step's own links have not
yet formed at that point in the round order.

## 4. Design concepts

**Basic principles.** Same as every prior level: bottom-up, no global
planner, no designed target state. Level 1.2 adds: institutions now
propagate and compete for persistence across patches, not just persist
or dissolve in place.

**Emergence.** Whether component transmission plus differential
persistence plus migration produces convergent, recurring institutional
configurations is itself the open empirical question — never assumed,
never engineered toward a particular answer.

**Observation.** Two distinct observation concepts must not be
conflated: (a) Work Package B's *in-model* local institutional
observation (an agent's own imperfect, possibly delayed, possibly
distorted perception of another patch's institution — a generative
input to migration/transmission decisions) vs. (b) the *observer-layer*
phenotype vector (Section 6, `observer/institutional_phenotype.py`) —
computed post-hoc, never agent-visible, never a decision input anywhere
in `rules/`.

## 5. Details — sub-models

### 5.1 Work Package B: local institutional observation (`rules/observation.py`)

`compute_true_institution_signal()` derives ground truth from the
generative state; `form_local_observation()` applies observation noise
(`observation_noise_std`), a possible administrative-report distortion
(`administrative_report_distortion_scale`), and a random delay (`0` to
`observation_delay_max_steps`); `local_observation_round()` drives this
across agents/patches on a `observation_period_steps` cadence. No-op
unless `institutional_observation_enabled=True` (requires
`interpatch_coordination_enabled=True`).

### 5.2 Work Package C: component-wise institutional transmission (`rules/transmission.py`)

`TRANSMISSIBLE_COMPONENT_NAMES` (12 of the 14 components — the 2
descriptive-only components are excluded). One-hop transmission over
the existing Level 1.1 coordination-link graph (disclosed topology
reuse, not a new mechanism). Per-component, independent transmission
attempts at `transmission_base_probability`, gated by
`transmission_period_steps`; `transmission_mutation_std` perturbs a
numeric component on successful transfer; `transmission_recombination_
probability` and `transmission_failure_probability` govern the other
two possible outcomes of an attempt. No-op unless
`institutional_transmission_enabled=True`.

### 5.3 Work Package D: migration and membership selection (`rules/migration.py`)

`migration_round()`: each agent (with `migration_propensity > 0`)
periodically (`migration_evaluation_period_steps`) evaluates a
perceived utility of every other patch (`_perceived_patch_signal`,
`_utility`) against `migration_cost` and `migration_capacity_per_patch`,
relocating via `PatchSystem.migrate()` on a favorable, noisy
(`migration_decision_noise_std`) draw. A realized migration
structurally emits `MembershipExitEvent(reason="migration")` — a
mechanical consequence of relocating, not a separate mechanism.
`membership_exit_round()`: a structurally distinct, separately-gated
(`membership_exit_enabled`) mechanism for voluntary exit WITHOUT
migrating (`reason="dissatisfaction"`). No-op unless
`migration_enabled`/`membership_exit_enabled` is set (migration also
requires `ecology_topology="patches"`, always true for Level 1.2).

### 5.4 Work Package E: differential persistence (`observer/differential_persistence.py`, observer-only)

Four separate summaries — `demographic_selection_summary`,
`institutional_selection_summary`, `ecological_selection_summary`,
`organizational_selection_summary` — never merged into one fitness
score. `selection_channel_for_reason()` maps raw Level 1.0/1.1
dissolution reasons onto 5 neutral channels (`member_loss`,
`administrative_overload`, `voluntary_dissolution`, `unspecified`, plus
`shock`/`fragmentation` reserved for future callers).

### 5.5 Work Package F: institutional scaling (`rules/scaling.py`)

`compute_coordination_components()` derives connected components of
the existing coordination-link graph (one-hop topology reuse, as in
Work Package B/C); `jurisdiction_size_by_patch()` feeds the delegation
round's administrative-overhead multiplier (`scaling_admin_overhead_
per_patch`, may be negative — economies of scale — floored at a 0.1×
multiplier). `institutional_scaling_round()` records
`CoordinationScaleChangeEvent` for every jurisdiction that grew, shrank,
merged, fragmented, or dissolved (best-effort patch-set-overlap
matching between consecutive steps — not exhaustively exact for a
pathological simultaneous multi-way split-and-merge within one step, a
disclosed limitation). No-op unless `institutional_scaling_enabled`
(requires `interpatch_coordination_enabled=True`).

### 5.6 Work Package G: environmental heterogeneity

Cross-checked against 9 named heterogeneity dimensions; 8 already
existed as config surface (`patch_regen_rate`, `patch_quality_std`,
`perturbations`, `observation_noise_std`, `migration_cost`,
`coordination_cost_per_step`, `scaling_admin_overhead_per_patch`,
population-density derived from `population_size`/`n_patches`). One
genuine gap filled: `patch_quality_spatial_correlation` (an AR(1)-over-
patch-index chain — "patch index order is the adjacency," a disclosed
simplification since this module has no independent geographic-
adjacency notion to reuse), `0.0` default = exact pre-Level-1.2
behavior (every patch's quality drawn independently).

### 5.7 Section 6: observer phenotype vector X=(C,E,L,D,M,R,S,F,V,H)

`observer/institutional_phenotype.py`. Ten independently-computed
dimensions, each its own function, raw values never collapsed into one
score, NaN propagated (never zero-filled) when undefined:

- **C** (realized administrative capacity) — from `delegate_registry`.
- **E** (effective constraint) — reuses `accountability_diagnostics.
  effective_constraint` directly.
- **L** (legitimacy/voluntary support) — from `rule_by_patch`/
  `patch_system` membership.
- **D** (concentration of delegated authority) — consumes Work Package
  F's `jurisdiction_size_by_patch`/coordination components.
- **M** (institutional memory continuity).
- **R** (administrative appropriation burden).
- **S** (institutional scale/reach) — from coordination components.
- **F** (amendment flexibility) — disclosed as amendment-only, not a
  full constitutional-flexibility measure (Section 5's "no fully
  designed constitution" constraint means no fuller quantity exists to
  measure yet).
- **V** (ecological/demographic viability) — two subparts, both
  reported separately.
- **H** (within-community heterogeneity) — reuses `rules/institution.
  py::structural_distance`.

Observer-only: never agent-visible, never a generative input anywhere
— checked by the existing generative/observer AST import-direction
guard.

### 5.8 Section 7: temporal phenotype representation (`observer/temporal_features.py`)

Preregistered windows (`WINDOW_NAMES`), static vs. dynamic feature
separation, nonstationarity detection (reuses
`regulation_diagnostics.py`'s `linear_trend`/`autocorrelation`/
`_burn_in_window` rather than re-deriving them), lineage turnover,
extinction-reconstruction counts, cross-patch heterogeneity series.
Never clusters raw autocorrelated per-step rows — every exported
feature is a pre-aggregated window summary.

### 5.9 Section 8: failure and viability (`observer/institutional_viability.py`)

`classify_all_outcome()` — closed, first-match-wins, 7-label vocabulary
(`no_institution`, `collapse`, `viable`, `persistent_extractive`,
`fragmented`, `transient`, `unclassified`) — includes a 4th failure
region (`persistent_extractive`) alongside `collapse`, neither excluded
for resembling only 2 of 3 dissertation trajectories.
`sustained_system_eligibility()` — non-normative, data-sufficiency-only
screen; every exclusion reason reported explicitly, never silently
dropped.

### 5.10 Section 9: blind phenotype discovery (`observer/phenotype_discovery.py`)

Preprocessing (3 missingness strategies compared, never silently
chosen; standardization always train-fit-only), 3 candidate methods
(`gmm`, `hierarchical`, `hdbscan` — a disclosed reduction from the
fuller suggested menu; no spectral or trajectory/hidden-state
clustering this milestone), k=1 through 8 where sample size permits
(k=1 never skipped, k=3 never privileged), multiple model-selection
metrics reported side by side (no single decider), consensus via
co-assignment/VI/bootstrap-ARI/cross-algorithm agreement.

### 5.11 Section 10-11: recurrence criteria and convergence tests

`observer/recurrence_criteria.py` — 12 minimum criteria (a conjunction,
not a majority vote), none referencing cluster count or identity.
`observer/convergence_tests.py` — inheritance-vs-convergence
classification via lineage diversity, a permutation-null test, direct
transmission-linkage evidence, and cross-condition recurrence; a closed
4-label vocabulary (`insufficient_data`, `inherited`, `convergent`,
`ambiguous`).

## 6. Initialization and input data

No SEM/dissertation data is ever read (Section 14's firewall,
mechanically audited — see `docs/level1.2_discovery_methodology_note.md`
§5). All Level 1.2 parameters are either config defaults or drawn via
the Stage 3 Latin-Hypercube parameter space (`experiments/
level12_stage3_search.py`) — never fit to or informed by external data.

## 7. Compatibility

A bare `SimulationConfig()` run is unaffected by every mechanism above
— reverified via the full test suite after every single Work
Package/Section/Stage this milestone (final count: 1084 passed, 6
skipped, 0 failed, 0 warnings). See `docs/level1.2_scientific_note.md`
for what was actually found when these mechanisms were turned on.
