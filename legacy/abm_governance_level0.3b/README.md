> **Publication note (added when this repository was prepared).** This is a **superseded snapshot** of the ABM package at the **Level 0.3b** milestone. It is kept only because the Level 0.1–0.3b outputs in `outputs/` were produced by this code. `../../abm/` is a strict superset of this code (see `../../docs/version_map.md` §2), with tested byte-for-byte backward compatibility (`SimulationConfig.level0_compat()`).
> Do **not** install it into the same environment as `../../abm/`: both use the distribution name `abm-governance`. Use a separate virtual environment.
> Excluded here: `lr/` (dissertation proposal PDF, not distributed) and `outputs/level03b_confirmatory_perturbation/confirmatory_perturbation_trajectories.csv` (24.9 MB; release/archive candidate; regeneration in `../../docs/data_availability.md`). The status text below is original.

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
`docs/odd_level0.2_addendum.md` and `docs/odd_level0.3_addendum.md`
extend it with everything Level 0.2 and Level 0.3 added respectively;
`docs/config_reference.md` documents every configuration field;
`docs/level0.2_scientific_note.md` and `docs/level0.3_scientific_note.md`
report what the Level 0.2 and Level 0.3 experiments actually found.

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

## Current status: Level 0.3b — regime validation and causal replication

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
