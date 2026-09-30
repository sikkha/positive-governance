# Level 0.3 Scientific Note

This note synthesizes what the Level 0.3 milestone's implementation and
experiments actually found on the central question: **can heterogeneous
agents, acting from local incentives with no direct reward for
sustainability, generate persistent or recoverable macroscopic ecological
regimes through their own endogenous niche construction?** Every number
below is read directly from a committed output file (cited inline); none
is asserted from memory or intuition. Full machine-readable data is under
`outputs/niche_*` (exact reproduction commands in §9). The note is
organized by category of claim, per the milestone's explicit discipline —
implementation facts, model assumptions, experimental findings, causal
findings, null findings, anomalies, limitations, and unresolved
questions are kept visibly separate throughout, and nothing below calls a
model behavior "emergent" merely because it was not directly coded; each
such claim is tied to a specific measurement.

## 1. What was built (implementation facts)

Full detail is in `docs/odd_level0.3_addendum.md`; summarized here only to
frame the results. Two structurally independent per-agent action
dimensions now coexist: the pre-existing social action (cooperate/defect,
unchanged from Level 0-0.2) and a new ecological action
(extraction/maintenance/restraint), governed by an independent
three-trait continuous policy (`extraction_propensity`,
`maintenance_propensity`, `scarcity_sensitivity`) that never reads a
social payoff and is never read by the social decision rule
(`tests/test_ecological_policy.py`, `tests/test_level03_niche_construction.py`
enforce this structurally, not just by convention). A new
`ecology_topology="patches"` mode (opt-in; `"global_pool"` remains the
exact, byte-for-byte Level 0.2-compatible default) spatially disaggregates
the single resource pool into fixed-membership patches
(`environment/patches.py`); patch membership never migrates, and is
deliberately kept independent of the continuously-rewiring social network
per the milestone's explicit instruction not to conflate the two. Agents
never observe global state — every ecological decision reads only the
agent's own patch occupancy and its own policy (`decide_ecological_action`'s
signature is structurally checked to expose no other channel). Two of the
milestone's four named ecological-inheritance modes are implemented
(`"independent"`, `"coupled_same_model"`); the other two collapse to
`"independent"` given the model's one-peer-per-imitation-round
architecture — a documented limitation, not a partial result (§8).

## 2. Do agents produce persistent interior ecological regimes at all? (Work Package H, phase search)

`experiments/niche_phase_search.py` ran a reproducible 16-point Latin
Hypercube design (`scipy.stats.qmc.LatinHypercube`, fixed `design_seed
20260817`) over 11 parameter axes, 3 seeds/point (48 runs, 0 failures;
`outputs/niche_phase_search/niche_phase_search_summary.json`), with region
labels computed strictly post-hoc by `nonstationary_classification` — no
point was selected, retried, or excluded by its outcome.

| region label | count | fraction |
|---|---|---|
| oscillatory | 14 | 29.2% |
| depleted | 14 | 29.2% |
| abundant | 9 | 18.8% |
| intermittent | 6 | 12.5% |
| interior-persistent | 5 | 10.4% |

**Finding: the parameter space is genuinely heterogeneous — persistent
interior occupancy, persistent depletion, persistent abundance, and two
non-stationary regimes (oscillatory, intermittent) are all reachable, and
none dominates.** This directly answers the weakest, most basic form of
the milestone's central question: the model is capable of producing
interior-persistent regimes, so "the environment can never do anything but
collapse or saturate" is ruled out as an explanation for any null finding
elsewhere in this note. Joining each point's outcome label back to its own
sampled parameters (`outputs/niche_phase_search/niche_phase_search_design.csv`)
shows a directionally sensible driver: the mean `patch_regen_rate` in
abundant-labelled points (0.92) is roughly double that of depleted-labelled
points (0.41), while mean `ecological_harvest_unit` runs the opposite way
(7.18 abundant vs. 9.48 depleted) — regeneration-versus-extraction pressure
behaves the way it did for the single global pool at Level 0.1/0.2,
extended now to the patch mechanism. This is a descriptive correlation
across 5-14 points per label, not a controlled comparison, and is reported
at that strength only.

## 3. Is any of this attributable to the agents' own behavior, or to the environment equation alone? (Work Package F, causal interventions)

`experiments/niche_causal_interventions.py` ran the endogenous condition
against all four WP-F counterfactuals (`no_effect` — the ecological
equation runs exactly as if agents had no effect on the patch at all;
`frozen` — ecological policies never imitate or mutate; `randomized` — a
fresh i.i.d. policy draw every step, ignoring inheritance entirely;
`shuffled` — the same drawn policies, permuted across agents once at
init), paired by identical seed, 12 seeds x 24 agents x 300 steps, 0
failures (`outputs/niche_causal_interventions/niche_causal_summary.json`).

| condition | mean fraction_interior (final 150 steps) |
|---|---|
| endogenous | 0.917 |
| no_effect | 1.000 |
| frozen | 1.000 |
| randomized | 0.917 |
| shuffled | 0.917 |

**Null finding: at this calibration, `feedback_dependence.criterion_met`
and `nontriviality.criterion_met` are both `False`** — the bare
environmental equation with *no* agent effect on the patch at all
(`no_effect`) sustains interior occupancy at least as well as the
endogenous condition, so persistence here cannot be attributed to agent
behavior. This is reported as a genuine result, not softened — the
milestone brief is explicit that "no endogenous self-regulation" is an
acceptable outcome. However, §6 below shows this specific null finding is
confounded by a calibration problem discovered after it was already run,
and must be read together with that correction, not in isolation.

## 4. Does adding real viability consequences change agents' ecological behavior? (Work Package G, viability threshold sweep)

`experiments/niche_viability_threshold_sweep.py` ran a 9-point staged grid
(2 distress thresholds x 2 deficit-duration thresholds x 3 viability
modes, `"none"` run once since thresholds do not apply to it) x 5 seeds,
population 24, 200 steps, 0 failures
(`outputs/niche_viability_threshold_sweep/niche_viability_sweep_summary.json`).
**The viability mechanism was measurably active in 8 of 9 grid points**
(at least one agent entered distress) — unlike the Level 0.2 finding that
demographic consequences were rare at the tested thresholds, this
mechanism engages readily under Level 0.3's ecological-scarcity dynamics.

A second, unplanned finding emerged from comparing each run's population
ecological-policy composition before versus after
(`outputs/niche_viability_threshold_sweep/niche_viability_sweep_points.csv`,
means across the 5 seeds per grid cell): population-mean
`extraction_propensity` **rose** from 0.519 at initialization to
0.57-0.69 by the end of the run in every one of the 9 grid cells
(including `mode="none"`, where no demographic consequence exists at
all), while population-mean `maintenance_propensity` **fell** from 0.319
to 0.07-0.22 over the same runs. **Finding: population-level ecological
policy drifts toward extraction and away from maintenance over the
course of a run, under every tested viability mode, including the mode
with no viability consequence at all.** Because this drift occurs even
under `mode="none"`, it cannot be attributed to viability filtering
agents by their ecological behavior — the more likely mechanism is
ecological-policy imitation itself: agents that extract more accumulate
more resources/payoff, which (via the existing fitness-based imitation
rule, reused unchanged from social imitation) makes their policy more
likely to be copied, regardless of the effect on the shared patch. This
is exactly the kind of unrewarded-but-selected-for behavior the milestone
was designed to be able to detect, and at this calibration it points away
from maintenance, not toward it — a genuine, if modest (5 seeds/cell),
piece of evidence that this model's simplest imitation-based inheritance
rule creates a selection pressure *against* the sustaining behavior when
nothing rewards it directly. This was not the outcome anticipated in the
milestone's framing, and is reported exactly as measured.

## 5. Does the system recover from perturbation? (Work Package J)

`experiments/niche_perturbation_recovery.py` ran all seven named shocks,
each against a matched unperturbed control, 6 seeds, population 30, 220
steps, 0 failures
(`outputs/niche_perturbation_recovery/niche_perturbation_summary.json`).

| shock | fraction recovered | mean recovery time (steps) | mean overshoot |
|---|---|---|---|
| local_patch_depletion | 0.667 | 0.0 | 0.065 |
| regen_reduction | 0.5 | 9.3 | 0.107 |
| maintenance_efficiency_reduction | 1.0 | 4.8 | 0.017 |
| random_patch_loss | 0.5 | 0.0 | 0.108 |
| remove_random_agents | 1.0 | 0.17 | 0.008 |
| remove_high_extraction_agents | 0.833 | 17.4 | 0.065 |
| remove_high_maintenance_agents | 1.0 | 11.7 | 0.040 |

**Finding: recovery, when it happens, happens fast (median under 5
steps) and only in a majority (not all) of seeds for 4 of the 7 shocks** —
this model does not show slow, effortful ecological recovery under any
tested shock; it shows either quick re-entry into the pre-shock band or no
recovery within the tested horizon, never something in between. Per the
milestone's explicit instruction, an honesty check compared each shocked
run's post-shock drift direction against its own matched unperturbed
control's drift direction
(`control_drift_check` in the summary JSON): **5 of the 7 shocks
(`local_patch_depletion`, `regen_reduction`, `random_patch_loss`,
`remove_high_extraction_agents`, `remove_high_maintenance_agents`) show
the shocked run drifting in a direction opposite to its control**,
confirming these are real, directionally distinct shock effects rather
than noise; the remaining 2 (`maintenance_efficiency_reduction`,
`remove_random_agents`) drift the same direction as their controls,
meaning the reported near-100%-recovery for those two specific shocks
should be read with the caveat that the control itself was already
trending toward the "recovered" band, not held there by resisting the
shock. The endogenous-vs-`frozen` comparison (run for 2 of 7 shocks, a
documented reduction) found `local_patch_depletion` recovers slightly
*more* often under the endogenous condition (0.667) than under `frozen`
(0.5) and `remove_random_agents` also recovers *more* often under
endogenous (1.0) than under `frozen` (0.667) — a small, two-shock,
same-direction result (endogenous higher on both), not a general
conclusion about whether the feedback loop helps or hinders recovery, and
not itself a robust finding given the calibration and eligibility-
screening problems described in §6 below and repaired at Level 0.3b (see
`docs/level0.3b_validation_note.md`).

**Correction (Level 0.3b, 2026-08-17):** the sentence above originally
read "recovers slightly *less* often under the endogenous condition
(0.667) than under `frozen` (0.5 ...)", which is numerically wrong —
0.667 is greater than 0.5, not less. The comparison direction (endogenous
higher than frozen on both shocks reported here) was already stated
correctly for the second shock; only the wording for the first shock was
in error, caught during Level 0.3b's documentation audit. This
paragraph's substance is otherwise unchanged from the original Level 0.3
record; see `dev_mem/status_update.md`'s Level 0.3b entry.

## 6. A calibration problem discovered late, and how it changes the reading of §3 and §5

While building the milestone's required visualizations (after §2-§5's
experiments had already been run and recorded), direct inspection of
*individual* per-seed trajectories — not just the cross-seed summary
statistics reported above — showed that `level03_patches_default`'s
literal default constants (`ecological_harvest_unit=5.0`,
`ecological_maintenance_unit=5.0`, `maintenance_efficiency=0.7`,
`patch_capacity=500.0`, `patch_regen_rate=0.5`) are **collapse-prone**:
many individual seeds crash to near-total patch depletion (aggregate
occupancy below 0.005) within the first 60-100 of 300 steps and stay
there (e.g. seed 0, population 30, 4 patches, reaches 0.0027 aggregate
occupancy by step 60). This mirrors a phenomenon already documented for
the single global pool at Level 0.1 (`experiments/perturbation_experiment.py`'s
docstring: "the shared resource pool collapses to its floor... within the
first ~25 of 500 steps") — the same collapse-proneness, now showing up in
the patches mechanism.

This matters because it was never checked before §3 and §5's experiments
were run — the milestone brief's own design allowance for "a small
preliminary calibration... documented before the main experiment" was
promised in this project's planning notes but not actually carried out.
The consequence is a **measurement problem, not a modeling problem**:
`interior_persistence`'s default [0.05, 0.95] occupancy band does not
distinguish "sitting stably around 0.25" from "having crashed to 0.001" —
both simply fail to qualify as "interior" — so when a batch of seeds
mixes collapsed and non-collapsed trajectories, the resulting
`fraction_interior` scalar can look similar across conditions whose raw
trajectories are visibly different (figure `08_causal_conditions.png`'s
raw trajectory plot shows a real, visible ~0.20-occupancy-point
separation between `endogenous`/`shuffled` and `no_effect`/`randomized`
that §3's scalar diagnostic did not register). A perturbation applied to
an already-collapsed patch (§5) also has an ill-defined "pre-shock band"
to recover into; `perturbation_recovery`'s zero-band-width guard only
partially catches this, since a nearly-zero-width band from a
nearly-collapsed pre-shock window still satisfies its `> 0` check.

**What this does and does not change.** Per the milestone's explicit
instruction that repeated recalibration in search of a preferred outcome
is exactly the wrong response, and that collapse is an explicitly
acceptable finding, §3 and §5's results are **not** re-run or discarded —
they stand exactly as measured and are reported above exactly as run.
What changes is the *interpretation*: the honest reading of §3's null
finding is "at the one untuned default point used, the model's patches
are collapse-prone, and the apparent absence of feedback dependence is
confounded by that collapse-proneness — it is not established as a clean
null result about the mechanism itself." §2's phase search is not subject
to this problem in the same way, because it was run independently, over a
wide parameter range that was not centered tightly on the collapse-prone
default point, and it already directly demonstrates the parameter space
contains real interior-persistent (10.4%) and abundant (18.8%) outcomes
alongside the 29.2%/29.2% depleted/oscillatory share — proving
collapse-proneness is a property of the *specific default calibration
point*, not a structural inevitability of the model. **Concrete
recommendation for the next work session**: re-run WP-F's
causal-intervention design and WP-J's perturbation design at one of the
phase search's own interior-persistent-labelled parameter points (rather
than the untuned `level03_patches_default` constants) before drawing any
further conclusion about feedback dependence or recovery.

## 7. Answering the central question, at the appropriate strength

- **Implementation fact:** the model, as built, structurally supports
  independent social and ecological actions with no direct reward
  pathway from ecological outcome to fitness under the default
  (`"total"`) fitness stream, and a separate `"ecological"` stream is
  available but was not the stream used to select agents in any
  experiment reported here (all four experiments used the default
  `"total"` stream) — a scope note, not a defect (§8).
- **Model assumption, not a finding:** patch membership is fixed and
  never migrates; this is a deliberate simplification, not a result
  about whether migration would change anything.
- **Experimental finding (§2):** the model is capable of producing
  interior-persistent, abundant, depleted, oscillatory, and intermittent
  regimes from the same mechanism, depending on parameters — genuine
  regime diversity exists.
- **Causal finding, currently null and confounded (§3, §6):** at the one
  calibration point tested for causal attribution, no detectable
  feedback dependence or nontriviality was found, but this reading is
  confounded by an undiagnosed collapse-proneness at that specific point
  and should not be treated as a settled null result about the
  mechanism.
- **Null finding (§4, mechanism-activity sense):** viability consequences
  are readily triggered (8/9 grid points) — unlike Level 0.2, "agents
  never have real skin in the game" is not a viable explanation for any
  null result at Level 0.3's calibration.
- **Unanticipated finding (§4, selection-pressure sense):** population
  ecological policy drifted toward extraction and away from maintenance
  in every tested viability-mode grid cell, including the mode with no
  viability consequence — evidence that this model's baseline
  imitation-based inheritance selects against unrewarded maintenance
  behavior, not for it, at this calibration.
- **Anomaly, explained (§5, §6):** recovery is fast-or-absent, never
  gradual; the two shocks with the highest apparent recovery rates are
  the two whose unperturbed controls were already drifting the same
  direction, so those two specific recovery-rate numbers overstate the
  shock-specific effect.
- **Unresolved:** whether feedback dependence, nontriviality, or a
  different recovery profile would appear at a non-collapse-prone
  calibration is not yet answered by any experiment in this milestone —
  it is the concrete next step (§6).

## 8. Known limitations

- Only 2 of the milestone's 4 named ecological-inheritance modes are
  distinguishable given the current one-peer-per-round imitation
  architecture (`"independent"`, `"coupled_same_model"`) — a documented
  architectural limitation, not a partial implementation of the other
  two.
- All four experiments used the default `"total"` fitness stream for
  agent selection, not the newly-added `"ecological"` stream — whether
  selecting agents purely on ecological outcome (rather than total
  resources/payoff) changes §4's extraction-drift finding is untested.
- `observer/regulation_diagnostics.py`'s `parameter_neighborhood_
  robustness` and `micro_macro_linkage` criteria are implemented and
  unit-tested against hand-constructed trajectories
  (`tests/test_regulation_diagnostics.py`) but were **not** applied to
  any of this milestone's real experiment output — only
  `interior_persistence`, `feedback_dependence`, `nontriviality`, and
  `nonstationary_classification` (WP-F, WP-H) and `perturbation_recovery`
  (WP-J) were exercised on real data. This is a gap in the regulation
  assessment, not a claim that those two criteria would or would not
  change any conclusion above.
- "Agent removal" (WP-J) is operationalized as `alive=False` plus
  severing every incident graph edge, not full removal from the
  population data structure — a documented, scoped approximation (see
  `docs/odd_level0.3_addendum.md` §14).
- The joint social/ecological action categorization
  (`observer/niche_metrics.py::joint_action_frequencies`) uses one
  documented operationalization (majority social vote per step, ties
  toward defect; extraction-dominant iff requested extraction exceeds
  requested maintenance) among several defensible alternatives.
- Every experiment script ran at a documented, stated reduction from the
  milestone brief's literal seed/point counts for compute-budget
  reasons (see each script's own `scale_reduction_note` in its output
  summary JSON) — 12 not >=20 seeds (WP-F), 5 seeds/cell (WP-G), 16
  points x 3 seeds not >=48 points x 8-10 seeds (WP-H), 6 not >=20
  seeds and 2 not 7 shocks compared against `frozen` (WP-J).
- The calibration-gap finding itself (§6) is a limitation of the
  experiment design, not of the model: it means §3 and §5's specific
  numeric conclusions should not yet be treated as final answers about
  feedback dependence or recovery.

## 9. Reproducibility

```
python -m experiments.niche_causal_interventions
python -m experiments.niche_viability_threshold_sweep
python -m experiments.niche_phase_search
python -m experiments.niche_perturbation_recovery
python -m experiments.make_level03_visualizations
```

Each script's `run()` function accepts an output directory and scale
parameters (seeds, population size, steps, points) as keyword arguments
with the documented-reduced defaults used above; see each script's
module docstring for the milestone brief's literal (larger) requested
scale. All four write a JSON summary (`n_failures`, per-condition/
per-point statistics, and a `scale_reduction_note`) plus per-run CSVs
under `outputs/niche_*`. `make_level03_visualizations` must be run as a
module (`python -m experiments.make_level03_visualizations`), not as a
bare script, because it imports helper functions from the other
`experiments/` modules and `experiments/` has no `__init__.py` — running
it directly does not put the project root on `sys.path`.
