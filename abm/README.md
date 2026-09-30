> **Publication note (added when this repository was prepared; the rest of this README is the project's original text).**
> This directory is the **canonical ABM implementation** behind dissertation Chapter 6 and `../paper/`. It is the `abm_governance` package at the **Level 1.3b** milestone.
> The "Current status" block below says Level 1.2b is in progress. **That is out of date:** Levels 1.3 and 1.3b are complete (`docs/level1.3_completion_report.md`, `docs/level1.3b_completion_report.md`, `docs/level1.3b_decision_gate_report.md`: decision `D_persistent_continuum`). The command sections below cover Levels 0.1–0.3 only. Level 1.x commands, the demo/full-experiment split, seeds, determinism controls and runtimes are documented in `../docs/reproducibility.md` §ABM.
> **Archived evidence is protected.** Experiment scripts refuse to run in this directory, because they would overwrite `outputs/`. Re-run any script with `python experiments/run_isolated.py <script>.py --out-dir /tmp/abm_rerun`; it writes `rerun_manifest.json` comparing the new files with the archive. Tests run in a scratch copy (`tests/conftest.py`). `ARCHIVED_OUTPUTS.sha256` lists the checksums of all 200 archived output files, and `tests/test_zz_archive_integrity.py` verifies them after every test session.
> Path placeholders: `<LOCAL_PATH>` and `<AGENT_WORKSPACE>` in `dev_mem/` and `docs/` replace the original absolute local paths. The cross-process test's working directory is now resolved relative to the repository (see `../LIMITATIONS.md`). `lr/Dissertation Proposal X_1 PDF.pdf`, which is referenced in this README, is not distributed.

---

# abm_governance

A research-grade, transparent agent-based model (ABM) investigating the
**bottom-up emergence of macropolitical organization** from elementary
micro-level social interactions.

**Before touching this codebase, read `dev_mem/project_vision.md`.** It
documents the research philosophy, the strict separation between the
generative simulation layer and the observer/analysis layer, and the
level-by-level development roadmap. `dev_mem/status_update.md` is the
living project log — check it for current status and open questions.
`docs/odd_level0.1.md` is a full ODD-style model description;
`docs/odd_level0.2_addendum.md` through `docs/odd_level1.2b_addendum.md`
extend it with everything each subsequent level added;
`docs/config_reference.md` documents every configuration field;
`docs/level0.2_scientific_note.md` through
`docs/level1.2b_scientific_note.md` report what each level's experiments
actually found.

## What this is (and is not)

This project sits alongside the dissertation "Positive Governance" (Kan
Yuenyong, `lr/Dissertation Proposal X_1 PDF.pdf`), which uses structural
equation modeling on survey data to identify a State Capacity (S) /
Institutional Constraint (Z) axis and three empirically-observed governance
trajectories (Authoritarian Efficiency, Constrained Liberalism, Integrated
Equilibrium). **This ABM does not target, reproduce, or optimize toward
those trajectories.** It asks an open-ended generative question instead:

> When heterogeneous agents interact through cooperation, exploitation,
> reciprocity, punishment, reward, exit, delegation, monitoring, and
> environmental feedback, what persistent forms of macroscopic political
> organization — if any — emerge?

Any resemblance (or anomalous non-resemblance) between what this model
generates and the dissertation's typology is a downstream, external,
observer-layer research question — never a design target. See
`dev_mem/project_vision.md` §2–§5 for the full reasoning.

## Current status: Level 1.2b — ecological feasibility envelope and powered blind institutional-phenotype rediscovery

**In progress: Sections 5-25 (Work Packages A through R, plus this
milestone's own documentation set) complete; Section 26
(visualizations) and Sections 27-29 (completion-gate check, stop-
condition audit, final report) not yet run. Level 1.3 has not
started.** Re-runs Level 1.2's own blind discovery question at a much
larger, ecologically-stratified scale — Level 1.2's own 24-run main
sample was too small, and its own near-universal collapse floor erased
most institutional variation before a discovery pipeline ever saw it.
Introduces no new generative mechanism or config field; adds an
ex-ante ecological-feasibility stratification layer
(`observer/feasibility_ratios.py`, `observer/ecological_ledger.py`), a
formal per-dimension phenotype-feature audit
(`observer/phenotype_feature_audit.py`), a recurrence-criteria audit
and cross-run lineage-ID fix (`observer/recurrence_criteria_audit.py`,
`observer/convergence_tests.py`), a 576-run stratified joint discovery
design and pipeline, a 384-run prospective confirmation pool, a
32-run scaling-robustness grid, and a 13-factor/208-run causal
collapse decomposition (`experiments/level12b_stage_*.py`). Six
genuine, previously-undetected ecological-ledger bugs — invisible
below production scale — were found and fixed during this milestone's
own mandatory pre-feasibility-mapping audit. See
`docs/odd_level1.2b_addendum.md` for the model description,
`docs/level1.2b_scientific_note.md` for the complete findings (short
version: **no recurrent, discrete institutional-phenotype structure
was independently supported** at this milestone's much larger scale —
a `continuum` discovery verdict, independently replicated as
`null_replicated` on a fresh, disjoint 384-run confirmation pool; this
extends, not contradicts, Level 1.2's own null result; near-universal
ecological collapse remained the dominant system-level dynamic,
causally characterized via 13-factor matched-seed ablation and shown
robust — with a genuine, disclosed population-vs-ecological recovery
dissociation after a standardized shock — across a scale grid; no
"attractor" label was assigned anywhere), `docs/level1.2b_discovery_
methods.md` for the full discovery/confirmation methodology,
`docs/level1.2b_ecological_accounting.md` for the ledger audit and its
six bug fixes, `docs/level1.2b_feasibility_method.md` for the
feasibility-ratio definitions and feasibility-map results,
`docs/level1.2b_feature_audit.md` for the phenotype-dimension audit,
`docs/level1.2b_recurrence_audit.md` for the recurrence-criteria audit
and lineage-ID fix, `docs/level1.2b_preregistration.md` for the
frozen, hashed manifest, and `docs/level1.2b_completion_report.md` for
current status (to be finalized once Sections 26-29 close). See
`dev_mem/project_vision.md` §9 for Levels 1-5.

### Level 1.2 — open institutional evolution and blind phenotype discovery

Complete, stopped for scientific review per this milestone's own
explicit instruction. Builds seven further generative work packages on
top of Level 1.1b (institutional component representation, local
observation, component-wise transmission, migration/membership
selection, differential persistence, institutional scaling,
environmental heterogeneity — `rules/institution.py`,
`rules/observation.py`, `rules/transmission.py`, `rules/migration.py`,
`rules/scaling.py`, `observer/differential_persistence.py`), an
observer-only ten-dimensional institutional phenotype vector
X=(C,E,L,D,M,R,S,F,V,H) (`observer/institutional_phenotype.py`), temporal
feature extraction and failure/viability classification
(`observer/temporal_features.py`, `observer/institutional_viability.py`),
a blind (never SEM-informed) phenotype-discovery pipeline (GMM/
hierarchical/HDBSCAN, `observer/phenotype_discovery.py`), a twelve-
criterion recurrence test and an inheritance-vs-convergence test
(`observer/recurrence_criteria.py`, `observer/convergence_tests.py`),
and a full Stage 0-7 + causal-ablation experimental program
(`experiments/level12_*.py`). Every new mechanism defaults to a strict,
verified byte-for-byte no-op, reconfirmed after every single change
throughout. See `docs/odd_level1.2_addendum.md` for the model
description, `docs/level1.2_scientific_note.md` for the complete
findings (short version: **no recurrent institutional phenotype
configuration was independently supported** at this milestone's
disclosed scale — replicated null result across two disjoint pooled
samples (n=24, n=12) using an unmodified discovery pipeline both times;
the dominant dynamic instead was near-universal ecological collapse
under the full mechanism set, robust across a population/patch-count
scale grid, with `patch_regen_rate` and `migration_enabled` both
causally implicated via matched-seed ablation — not asserted as three,
one, or any other specific recurrent count, per the milestone's own
closing instruction), `docs/level1.2_discovery_methodology_note.md` for
the Section 9-11 pipeline's full statistical methodology,
`docs/level1.2_causal_ablation_note.md` for Section 13's matched-seed
design and results, `docs/level1.2_preregistration.md` for the frozen,
hashed Stage 0 manifest, and `docs/level1.2_completion_report.md` for
the full Section 21/22 completion-gate audit and final report. See
`dev_mem/project_vision.md` §9 for Levels 1-5.

### Level 1.1b — mechanism validation, artifact-independence, and RNG substream architecture

Complete. A validation-and-audit milestone on top of Level 1.1, not a
new generative layer: adds a per-mechanism RNG substream architecture
(`core/rng.py::STREAM_REGISTRY`, opt-in via
`rng_mode="mechanism_substreams"`, `"legacy_single_stream"` remains the
exact byte-for-byte default), artifact-independent re-verification of
the Level 0.3b pipeline, a 72/72 coordination-acceptance audit, an
appropriation-opportunity-vs-conduct decomposition, an accountability
activity-vs-effective-constraint audit, an institutional-memory
validation sweep, functional shock-recovery beyond simple
reappointment, and `observer/delegation_diagnostics.py`'s audited
classifier (`classify_delegation_audited`) reported alongside (never
replacing) the historical classifier for direct comparison. See
`docs/odd_level1.1b_addendum.md`, `docs/level1.1b_validation_note.md`,
`docs/level1.1b_rng_design.md`, and `docs/level1.1b_reproducibility_note.md`.

### Level 1.1 — delegation, administrative capacity, and institutional scale

Complete. Builds the generative bridge from Level 1.0's proto-institutions
through delegation, administrative capacity, discretion/appropriation,
accountability/constraint, opt-in collective contributions, and minimal
interpatch coordination — explicitly not a search for the dissertation's
three governance trajectories. Adds `rules/delegation.py` (nomination,
candidate evaluation, selection, capacity accumulation, discretion,
accountability), `rules/contributions.py` (opt-in collective
contributions, administrative spending, dissolution-fund disposition),
`rules/coordination.py` (bilateral interpatch coordination links,
deliberately independent of delegation), and
`observer/delegation_diagnostics.py` (Work Package J's 9 separate
dimensions + Work Package K's cautious 12-label mechanism-validation
classifier). Every Level 1.1 mechanism defaults to a strict, verified
byte-for-byte no-op (`delegation_enabled=False`,
`interpatch_coordination_enabled=False`, `contribution_mode="none"`).
See `docs/odd_level1.1.md` for the full model description,
`docs/level1.1_scientific_note.md` for the complete findings (short
version: every mechanism was confirmed reachable and inert-by-default;
activating discretion+accountability together was confirmed, on fresh
seeds with non-overlapping confidence intervals, to shift a rule's
classification from `persistent_delegation` to predominantly
`accountable_delegation`; a causal-decomposition stage found removing
administrative cost or interpatch coordination each causally *increases*
appropriated resources, while accountability's own effect on
appropriation was directionally consistent but not confirmed at the
tested seed count; delegation arrangements recovered from both tested
shock types in every seed tried), and
`docs/level1.1_audit_supplement.md` for the required Work Package A-C
audit of Level 1.0's own observer/accounting layer (a genuine production
bug — institutional memory read but never written — was found and fixed
during this milestone's own verification; negative agent resources were
confirmed a pre-existing Level 0.3/1.0 characteristic, not a Level 1.1
defect). See `dev_mem/project_vision.md` §9 for Levels 1-5.

### Level 1.0 — emergence of proto-institutions under coordination failure

Complete. Begins Level 1: tests whether a locally shared, patch-attached
rule — proposed, voluntarily adopted, imperfectly monitored, imperfectly
enforced, amendable, and dissolvable, all from local information only —
can become socially reproduced and resist the extraction-favoring
evolutionary dynamic Level 0.3b showed causally worsens ecological
occupancy. **Level 0.3b's completion report recommended not proceeding to
Level 1; this project explicitly overruled that recommendation** via the
two-route decision gate the project itself had already agreed to
(spontaneous/partial self-regulation OR causally demonstrated coordination
failure — Level 0.3b produced the second route). See
`docs/level1.0_decision_record.md` for the complete reasoning. A mandatory
preflight audit (Section 3) found and fixed two `coupled_same_model`
imitation-dispatch defects, proved structurally that they never reached
Level 0.3b's principal (`"independent"`-mode) causal finding, and reran
only the two affected fitness-stream cells.

Adds `rules/shared_rule.py` (`SharedRule`, `RuleParameters`),
`rules/dynamics.py` (compliance/monitoring/sanctioning/proposal/adoption/
membership/amendment/dissolution), and `observer/institution_diagnostics.py`
(Work Package J's 6 separate metric categories + Work Package K's
conservative proto-institution classification, never inferred from
ecological occupancy alone). `rule_formation_enabled=False` (the default)
is an exact, verified Level-0.3b-compatible no-op. See
`docs/odd_level1.0.md` for the full model description and
`docs/level1.0_scientific_note.md` for the complete findings (short
version: a reproducible exploratory search found persistent
proto-institutions emerging **unforced** at all three Level 0.3b
registered candidates — though `founder_dependent_arrangement` was the
single most common outcome everywhere; an 11-condition institutional-
counterfactual comparison found a directionally consistent but **not
statistically confirmed at 20 seeds** pattern — conditions with real
monitoring/sanctioning infrastructure tended to show *lower* final
ecological occupancy than no institution at all, while a costless
informal norm or a mechanically-guaranteed imposed rule tended to show
*higher* occupancy; four institutional-shock types each produced a
survival rate strictly between 0 and 1, with genuine lineage-recorded
reconstruction attempts after every shock type). **Per explicit
instruction, Level 1.1 has not been started regardless of this
milestone's findings.** See `dev_mem/project_vision.md` §9 for Levels
1-5.

### Level 0.3b — regime validation and causal replication

Complete. A focused validation milestone, not Level 1: audits Level 0.3's
regime classifier and causal claims against a burn-in-aware, multi-
criterion classifier and a prospectively-registered candidate-selection
and confirmation pipeline. Adds no new generative mechanism — every
config field it uses already existed at the end of Level 0.3; the seven
causal conditions (`endogenous`/`frozen`/`randomized`/`shuffled`/
`environment_only`/`impact_disabled`/`maintenance_disabled`/`ecological_
mutation_disabled`) are combinations of existing fields. See
`docs/level0.3b_validation_note.md` for the full findings (short version:
Level 0.3's "oscillatory"/"intermittent" phase-search labels do not
survive the audited classifier at all — 0 of 144 point-seed runs across
the original and one prespecified supplemental search satisfy the
stricter multi-cycle/amplitude/autocorrelation oscillatory criterion; the
two candidates selected for an interesting *exploratory* n=3 label did
not replicate robustly at n=24 confirmation seeds, one flipping to
unclassified and one to depleted; but the milestone's central causal
question does have a real, prespecified-condition answer: for the primary
candidate, endogenous adaptive ecological behavior causally **worsens**
ecological persistence relative to `frozen` and `randomized`
counterfactuals — paired occupancy is lower under `endogenous` by a mean
of 0.20-0.26 with bootstrap CIs excluding zero — consistent with
extraction propensity drifting up and maintenance propensity drifting
down under free imitation+mutation). See `docs/odd_level0.3b_addendum.md`
for the observer-side additions. **Per explicit instruction, Level 1 has
not been started regardless of this milestone's findings.** See
`dev_mem/project_vision.md` §9 for Levels 1-5.

### Level 0.3 — endogenous niche construction and feedback closure

Complete. Builds on Level 0.2 by giving agents a second, structurally
independent behavioral dimension — an ecological action
(extraction/maintenance/restraint), governed by its own three-trait
continuous policy, that is never equated with or derived from the social
cooperate/defect action — and a spatially-disaggregated alternative to
the single global resource pool: fixed-membership local patches
(`ecology_topology="patches"`, opt-in; `"global_pool"` remains the exact,
byte-for-byte Level 0.2-compatible default). Central question: can local,
unrewarded ecological actions produce persistent or recoverable
macroscopic ecological regimes through the agents' own niche
construction, with no agent ever observing global state? Four experiment
scripts implement the milestone's causal-intervention (WP-F),
viability-threshold (WP-G), phase-search (WP-H), and perturbation-recovery
(WP-J) work packages; a seven-criterion regulation-diagnostics module
(`observer/regulation_diagnostics.py`) reports interior persistence,
feedback dependence, perturbation recovery, and a cautious
nonstationary-regime classification without ever combining them into one
verdict, and never uses the term for a dynamical system's proven stable
fixed point anywhere in the codebase (checked by a structural test). See
`docs/level0.3_scientific_note.md` for the full findings (short version:
the phase search finds genuine regime diversity — interior-persistent,
abundant, depleted, oscillatory, and intermittent outcomes all occur
depending on parameters — but the causal-intervention run at the
default calibration found no detectable feedback dependence, a null
result later discovered to be confounded by that default calibration
being collapse-prone; a viability-sweep side finding shows population
ecological policy drifting toward extraction and away from maintenance
under every tested viability mode, including the mode with no
demographic consequence at all). **Per explicit instruction, Level 1
(public goods, delegated enforcement, government, law, democracy,
legitimacy, S/Z, governance classification) has not been started.** See
`dev_mem/project_vision.md` §9 for Levels 1-5.

### Level 0.2 — viability, participation accounting, and ecological phase mapping

Complete (prior milestone). Builds on Level 0.1 (a heterogeneous population interacting over
a dynamic network with a shared, bounded environment resource pool and
endogenous relationship dynamics — see below) by adding: full
participation-opportunity accounting (every agent-opportunity is
completed, refused by distress, or blocked by dormancy — never silently
uncounted), a disableable, duration-based agent viability state machine
(`viability_mode ∈ {none, dormancy_recovery, removal_replacement}`) with
explicit, non-dominant-policy-by-default replacement inheritance,
configurable imitation fitness signals (`fitness_mode ∈
{cumulative_resources, recent_payoff, resource_delta,
viability_adjusted}`) with a formally-tested translation-invariance
property, ecological supply/demand balance accounting (`observer/
ecological_balance.py`), a two-stage (coarse Latin-Hypercube + boundary-
refinement) ecological phase-space exploration, and operational,
threshold-based dynamical classification definitions (depletion,
collapse, recovery, population failure, behavioural convergence — see
`observer/classification.py`). This milestone investigated *why* Level
0.1's default configuration produced pool collapse, unboundedly negative
agent resources, and near-universal measured cooperation; see
`docs/level0.2_scientific_note.md` for the full findings (short version:
both candidate explanations — selective-participation bias and
relative-fitness invariance to universal impoverishment — are real, with
different regime-dependent weight; the viability state machine alone did
not resolve it, at the tested deficit-duration thresholds). See
`dev_mem/status_update.md`'s newest entry for the full milestone report.
**Per explicit instruction, Level 1 (public goods, delegated enforcement,
government, law, democracy, legitimacy, S/Z, governance classification)
has not been started.** See `dev_mem/project_vision.md` §9 for Levels 1–5.

### Level 0.1 — ecological closure and active relational dynamics

Complete (prior milestone). Builds on Level 0 (a heterogeneous population
interacting over a dynamic network via a repeated prisoner's-dilemma-style
payoff grammar, with imperfect observation, memory/forgiveness, optional
costly punishment, strategy imitation, low-rate mutation, and costly
exit/rewiring) by adding: a shared, bounded environment resource pool
with logistic regeneration and subsistence costs (`ecology_enabled`);
endogenous, ongoing relationship formation/dissolution with an explicit
accept/reject and affordability-gated exit (`relationship_dynamics_enabled`);
an explicit enforcement confusion matrix (true/false positive/negative
punishment) replacing the old under-denominated "erroneous punishment
rate"; policy-lineage/ancestry tracking; reusable (non-classifying)
dynamical diagnostics; and a generic, opt-in perturbation interface. See
`docs/odd_level0.1.md` for the ODD-style model description.
`SimulationConfig.level0_compat()` reproduces the original Level-0
dynamics exactly (see "Determinism" below).

## Project layout

```
abm_governance/
├── dev_mem/                    # mandatory, living project-memory docs — read first
│   ├── project_vision.md
│   └── status_update.md
├── docs/
│   ├── odd_level0.1.md              # ODD-style model description (Level 0.1)
│   ├── odd_level0.2_addendum.md     # Level 0.2 additions to the ODD description
│   ├── odd_level0.3_addendum.md     # Level 0.3 additions to the ODD description
│   ├── config_reference.md          # every SimulationConfig field
│   ├── level0.2_scientific_note.md  # Level 0.2 findings write-up
│   └── level0.3_scientific_note.md  # Level 0.3 findings write-up
├── lr/                          # source literature
│   └── Dissertation Proposal X_1 PDF.pdf
├── src/abm_governance/
│   ├── core/                    # RNG, config, event log, scheduler, export, perturbation — generative substrate
│   ├── agents/                  # Agent state, policies, observation, adaptation, fitness (0.2),
│   │                              #   ecological_policy (0.3) — generative
│   ├── interactions/            # payoff grammar — generative
│   ├── network/                 # relationship graph (legacy) + dynamics (Level 0.1 exit/connection) — generative
│   ├── environment/              # shared resource pool (Level 0.1) + local patches (Level 0.3) — generative
│   ├── observer/                 # metrics, enforcement, network/policy/dynamics diagnostics, participation/
│   │                              #   viability/ecological_balance/classification (Level 0.2),
│   │                              #   niche_metrics/regulation_diagnostics (Level 0.3) — read-only, downstream
│   ├── viz/                      # single-run plotting — downstream
│   ├── simulation.py              # Level 0 / 0.1 / 0.2 / 0.3 orchestrator
│   └── cli.py                     # command-line entry point
├── tests/                        # unit + invariant tests (pytest)
├── experiments/
│   ├── configs/level0_default.yaml
│   ├── batch_run.py              # simple multi-seed / parameter-grid scaffold (pre-Level-0.1)
│   ├── ensemble.py                # Level 0.1: seed-list/grid ensemble runner, manifest, aggregation
│   ├── perturbation_experiment.py # Level 0.1: the one required minimal perturbation experiment
│   ├── dynamics_report.py         # Level 0.1: WP-F diagnostics applied to ensemble output
│   ├── make_visualizations.py     # Level 0.1: ensemble-level figures
│   ├── phase_sweep.py             # Level 0.2, WP-E: coarse LHS sweep + boundary refinement
│   ├── boundary_perturbation.py   # Level 0.2, WP-J: perturbation experiment at the boundary
│   ├── turnover_boundary_sweep.py # Level 0.2, WP-G: relationship-dynamics sweep near the boundary
│   ├── null_model_comparisons.py  # Level 0.2, WP-H: factorial null-model comparisons
│   ├── cooperation_ecology_causality.py  # Level 0.2, WP-F: cooperation/ecology association + lag analysis
│   ├── make_level02_visualizations.py  # Level 0.2: the 10 required figures
│   ├── niche_causal_interventions.py    # Level 0.3, WP-F: endogenous vs. 4 counterfactual conditions
│   ├── niche_viability_threshold_sweep.py  # Level 0.3, WP-G: viability-threshold staged grid
│   ├── niche_phase_search.py            # Level 0.3, WP-H: reproducible LHS phase-space search
│   ├── niche_perturbation_recovery.py   # Level 0.3, WP-J: 7 shocks vs. matched unperturbed controls
│   └── make_level03_visualizations.py  # Level 0.3: the 12 required figures
├── outputs/                       # run artifacts (gitignored; regenerate via the CLI/experiments scripts)
├── pyproject.toml
└── README.md
```

The dependency direction is one-way: `observer`, `viz`, `cli`, and
`experiments` may depend on `core`/`agents`/`interactions`/`network`/
`environment`; never the reverse.

## Install

```bash
pip install -e ".[dev]"
```

## Run a single simulation

```bash
abm-governance run --seed 0 --steps 500 --out outputs/run_0
# or, without installing the console script:
python -m abm_governance.cli run --seed 0 --steps 500 --out outputs/run_0
```

Writes `metrics.csv`, `metrics.json`, `final_state.json`, `config.yaml`,
and `timeseries.png` into the output directory. `--config path.yaml`
loads a full `SimulationConfig`; `--seed`/`--steps` override it.

## Run a small parameter sweep

```bash
python experiments/batch_run.py --out outputs/batch_default --seeds 5 --steps 200
```

Runs every (seed × grid-parameter) combination — no cherry-picking — and
writes a concatenated `batch_summary.csv` alongside each run's full output.

## Run the Level 0.1 ensemble (baseline conditions + ablations)

```bash
python experiments/ensemble.py --out outputs/ensemble_level01 --seeds 30 --steps 500 --workers 2
python experiments/dynamics_report.py --ensemble-dir outputs/ensemble_level01
python experiments/perturbation_experiment.py --out outputs/perturbation_experiment
python experiments/make_visualizations.py --ensemble-dir outputs/ensemble_level01
```

Runs the 3 required baseline-comparison conditions (`original_compat`,
`ecologically_closed`, `closed_ecology_turnover`) and the 7 required
ablations (`no_memory`, `no_punishment`, `no_observation_error`,
`no_imitation`, `no_mutation`, `no_relationship_exit`,
`no_ecological_scarcity`), 30 seeds each, writing one run directory per
`(condition, seed)`, a JSON manifest, and aggregated
quantile/distribution summaries — never just endpoint means. Execution
order does not affect results: every run is fully self-contained (its own
seeded RNG), which `tests/test_ensemble.py::
test_serial_and_parallel_execution_agree` checks directly. See
`dev_mem/status_update.md`'s newest entry for the results of the last
executed run and `--dry-run` to preview the grid without executing
anything.

## Run the Level 0.2 phase-mapping pipeline

```bash
python experiments/phase_sweep.py --out outputs/phase_sweep_level02 \
    --stage1-points 32 --seeds-stage1 10 --seeds-stage2 30 --grid-levels 5 --workers 2
python experiments/boundary_perturbation.py --out outputs/boundary_perturbation_level02 --seeds 20 --workers 2
python experiments/turnover_boundary_sweep.py --out outputs/turnover_boundary_level02 --seeds 10 --workers 2
python experiments/null_model_comparisons.py --out outputs/null_model_comparisons_level02 --seeds 15 --workers 2
python experiments/cooperation_ecology_causality.py --sweep-dir outputs/phase_sweep_level02 \
    --out-dir outputs/cooperation_ecology_causality_level02 --n-seeds 20 --n-steps 250 --max-lag 15
python experiments/make_level02_visualizations.py
```

Run in this order — each later script reads the boundary region(s)
`phase_sweep.py` selected from its manifest. `phase_sweep.py --dry-run`
previews the planned run grid; it is resumable (a prior run's completed
`(point_id, seed)` pairs are skipped, never re-executed — pass
`--no-resume` to force a clean rerun).
`experiments/cooperation_ecology_causality.py` (Work Package F) is the
one script here that does not require a prior boundary-selection step —
its Part 1 reads `phase_sweep.py`'s completed manifest directly (zero
new simulation runs), and its Part 2 runs its own fresh, small time-
series sample of the three representative regions. See
`docs/level0.2_scientific_note.md` for what this pipeline found (32-point
Stage-1 Latin Hypercube sweep + a 5×5 supplemental grid, 630 runs, 0
failures; 2 boundary regions identified and carried through Stages
J/G/H/F) and `dev_mem/status_update.md`'s newest entry for the full
milestone report.

## Run the Level 0.3 niche-construction pipeline

```bash
python -m experiments.niche_causal_interventions
python -m experiments.niche_viability_threshold_sweep
python -m experiments.niche_phase_search
python -m experiments.niche_perturbation_recovery
python -m experiments.make_level03_visualizations
```

The four experiment scripts are independent of each other (no shared
selection step, unlike the Level 0.2 pipeline) and can be run in any
order or in parallel; `make_level03_visualizations` reads all four's
output directories plus a few fresh cheap `level03_patches_default` runs
of its own, so it should be run last. Each script's `run()` accepts an
output directory and scale keyword arguments (seeds, population size,
steps, points); the defaults used above are a documented, stated
reduction from the milestone brief's literal requested scale — see each
script's own `scale_reduction_note` in its output summary JSON.
`make_level03_visualizations` must be run as a module
(`python -m experiments.make_level03_visualizations`), not as a bare
script, because it imports helpers from the other `experiments/` modules
and `experiments/` has no `__init__.py`. See
`docs/level0.3_scientific_note.md` for what this pipeline found — in
short, a genuinely heterogeneous phase space (interior-persistent,
abundant, depleted, oscillatory, and intermittent outcomes all occur) but
a causal-intervention run at the default calibration that found no
detectable feedback dependence, later discovered to be confounded by that
default calibration's collapse-proneness (see the note's §6 for the full
correction and its consequences) — and `dev_mem/status_update.md`'s
newest entries for the full milestone report.

## Test

```bash
pytest
pytest --cov=abm_governance --cov-report=term-missing   # coverage
```

Tests cover payoff arithmetic, resource accounting (exact ledger
identities — one for compatibility mode, one for the extended Level 0.1
ledger including ecological and relationship-dynamics terms),
memory/reputation EWMA updates against hand-derived sequences,
observation error, punishment, strategy adaptation timing and rates,
network exit/rewiring (legacy and Level 0.1), the environment resource
pool, endogenous relationship dynamics, the enforcement confusion matrix
(hand-computed cases), policy-lineage tracking, dynamical diagnostics
(hand-computed autocorrelation/rolling-statistics cases), the
perturbation interface (including the Level 0.2 `subsistence_increase`/
`regeneration_reduction` shock kinds), the ensemble runner (including a
parallel-vs-serial determinism check), seed reproducibility
(bit-for-bit), a byte-for-byte regression against the pre-Level-0.1
committed baseline run, config validation, and population/attribute-naming
invariants — including a structural guard that fails the build if any
agent ever holds an attribute named after a governance-normative concept
(democracy, rule of law, state capacity, institutional constraint,
legitimacy, governance type).

**Level 0.2 additions:** participation-opportunity accounting (including
a hand-computed micro-scenario and a full-simulation invariant check
across every viability mode), the viability state machine (hand-computed
deficit-duration trace, every replacement-inheritance policy, population/
lineage-continuity accounting), all four fitness modes (including a
formal translation-invariance test and the one mode that should, and
does, break invariance under a dormancy-crossing shift), ecological
balance indicators and region labelling, the dynamical-classification
functions (with an explicit threshold-sensitivity check per function),
and the five new experiment-runner scripts (`phase_sweep.py` —
LHS-sampling determinism, resume correctness including a regression test
for a stage-leakage bug found during development, serial/parallel
equivalence, ecology-only boundary selection; `boundary_perturbation.py`,
`turnover_boundary_sweep.py`, `null_model_comparisons.py` — config
construction, end-to-end tiny runs, and aggregation correctness;
`cooperation_ecology_causality.py` — hand-computed lag-correlation and
incremental-R² micro-scenarios with a known planted lead/lag, and a
synthetic-manifest test that reproduces the within-point-vs-pooled
confound directly).

**Level 0.3 additions:** local ecological patches (`tests/test_patches.py`
— pure-function allocation rationing, exact per-patch ledger identities,
both neutral assignment rules including disconnected-component and
more-patches-than-agents edge cases), the independent ecological policy
(`tests/test_ecological_policy.py` — range validation, RNG determinism,
a structural check that the decision function's signature exposes no
global/cross-patch information channel), the full niche-construction
mechanism (`tests/test_level03_niche_construction.py` — exact per-agent
and per-patch ledger identities, all four social x ecological joint-action
combinations, both implemented inheritance modes, all four WP-F
counterfactual flags, exact byte-for-byte Level 0.2 compatibility under
`ecology_topology="global_pool"`, deterministic replay under patches
topology, and a structural guard extending the governance-terminology
check over every new Level 0.3 field/event/mode-string), the new observer
metrics (`tests/test_niche_metrics.py` — hand-computed cases including
every zero-denominator/no-mechanism degenerate case), the seven
regulation-diagnostics criteria (`tests/test_regulation_diagnostics.py`
— hand-constructed trajectories per criterion, plus a structural check
that no allowed emitted label, and no code comment, ever uses the term
for a dynamical system's proven stable fixed point), and smoke/integration
tests for all four Level 0.3 experiment scripts
(`tests/test_niche_experiments.py`, including a direct check that the
documented agent-removal operationalization actually isolates an agent).

**470 tests, 97% statement coverage** (2515 statements, 64 missed) as of
the Level 0.3 milestone, `-W error::RuntimeWarning -W
error::pandas.errors.PerformanceWarning` — see `dev_mem/status_update.md`.

## Determinism

Every stochastic draw in the codebase passes through one explicit,
seeded `numpy.random.Generator` (`core/rng.py`). No module calls the
global `numpy.random` or stdlib `random`. Two runs with the same
`SimulationConfig` (including `seed`) are bit-for-bit identical —
verified in `tests/test_rng.py` and `tests/test_cli_smoke.py`. Every
Level 0.1 mechanism (ecology, relationship dynamics, perturbations, the
`imitation_enabled`/`relationship_exit_enabled` ablation switches) and
every Level 0.2 mechanism (`viability_mode`, `fitness_mode`, the two new
perturbation kinds) is gated so that disabling it / leaving it at its
default consumes *zero* extra RNG draws — a `SimulationConfig
.level0_compat()` run therefore still reproduces the original
pre-Level-0.1 draw sequence exactly, which
`tests/test_compat_regression.py` checks against the committed
`outputs/level0_default/metrics.csv` baseline byte-for-byte, and a
default-`SimulationConfig()` Level-0.2 run reproduces Level 0.1's
dynamics exactly (`viability_mode="none"`,
`fitness_mode="cumulative_resources"` are both no-ops relative to Level
0.1 — see `docs/odd_level0.2_addendum.md` §5), and every Level 0.3
mechanism is gated the same way behind `ecology_topology`: a
`SimulationConfig(ecology_topology="global_pool")` run (the default)
never constructs a `PatchSystem`, never draws an ecological policy that
affects behavior, and never logs an ecological event, so it reproduces
Level 0.2's dynamics exactly (`SimulationConfig.level02_compat()` names
this intent explicitly — see `docs/odd_level0.3_addendum.md` §13).
