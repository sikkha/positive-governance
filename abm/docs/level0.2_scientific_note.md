# Level 0.2 Scientific Note

This note synthesizes what the Level 0.2 milestone's instrumentation and
experiments actually found. It is written to the milestone brief's eight
scientific questions and covers: the universal-impoverishment problem,
participation-denominator bias, the viability and fitness alternatives,
the phase-mapping methodology and its results, the classification
definitions used, and known limitations. Every number below is read
directly from a committed output file (cited inline); none is asserted
from memory or intuition. Full machine-readable data is under `outputs/`
(exact reproduction commands in §11).

## 1. The problem this milestone investigates

Level 0.1's default, ecologically-closed configuration produced: resource
pool collapse, agent resources drifting unboundedly negative, and a
conditional cooperation rate approaching 1.0. `dev_mem/status_update.md`'s
session-3-start entry identified two live candidate explanations —
participation-denominator bias (measured cooperation is conditioned on an
ever-shrinking set of still-interacting agents) and relative-fitness
invariance (the imitation rule compares agents pairwise, so a uniform
resource shift such as unconditional subsistence leaves every ranking,
and therefore every imitation probability, unchanged) — plus a third,
newly identified gap: no viability consequence beyond probabilistic
distress-withholding existed at all. This milestone was **not** asked to
eliminate or tune away the original result; it was asked to determine
which of these mechanisms (or what combination) produces it, using new
instrumentation built for exactly that purpose.

## 2. Participation-denominator bias (Work Package A, Question 3)

`observer/metrics.py` and `observer/participation.py` decompose every
agent-opportunity into a completed interaction or one of four withhold
reasons, making `opportunities_total ==
completed_agent_opportunities + withhold_total` an exact per-step
invariant (verified across every viability mode by
`tests/test_participation.py`). This lets **conditional** cooperation
(P(Cooperate | interaction) — the Level-0.1 legacy metric) be compared
directly against **unconditional** cooperation (P(Cooperate ∩ interaction
| opportunity)).

The null-model comparison (`outputs/null_model_comparisons_level02/
null_model_summary.csv`, `region_x_fitness_mode` slice,
`fitness_mode=cumulative_resources`, `viability_mode=none`, 15 seeds/cell)
found a large, region-dependent gap between the two:

| ecological region | conditional cooperation | unconditional cooperation | gap |
|---|---|---|---|
| depleted | 0.877 | 0.248 | **0.630** |
| boundary | 0.750 | 0.749 | 0.001 |
| abundant | 0.357 | 0.353 | 0.004 |

**Finding: yes, selective participation materially inflates the
conditional cooperation metric — but only in the depleted regime.** In
the depleted region, more than three-quarters of what looks like
near-universal cooperation is an artifact of the conditional metric's
denominator shrinking to the small set of agents still managing to
interact; the same population's *unconditional* cooperation rate (0.248)
is unremarkable. At the boundary and in the abundant region the two
metrics essentially coincide — selective participation is not a general
property of the model, it specifically emerges once the pool has
collapsed. This directly answers scientific question 3: near-unity
cooperation in the depleted regime is substantially explained by
distressed/defecting agents dropping out of the interacting population,
not by universal cooperative behaviour.

## 3. Does the universal-impoverishment problem survive real viability consequences? (Work Packages B, H — Questions 1, 2)

`outputs/null_model_comparisons_level02/null_model_summary.csv`'s
`viability_mode_x_fitness_mode` slice (run at the boundary region, 15
seeds/cell) shows `viability_mode` has **essentially no effect** on
cooperation once `fitness_mode` is held fixed: for
`fitness_mode=cumulative_resources`, conditional cooperation is 0.750
(`none`), 0.740 (`dormancy_recovery`), 0.740 (`removal_replacement`); for
`fitness_mode=resource_delta`, 0.801 / 0.815 / 0.815 respectively. Actual
agent removals under `removal_replacement` were small (mean 0.40 replacements/run
with `recent_payoff`/`viability_adjusted`, 0.13 with `resource_delta`, 0.0
with `cumulative_resources`) — at this particular boundary parameterization
and the default `viability_deficit_steps_threshold=10` used in the
population-trajectory figure, most agents never accumulate a long enough
deficit streak to reach dormancy at all (see
`outputs/figures_level02/03_population_states_over_time.png`, where the
dormant/distressed bands are near zero almost the entire run). **Finding:
adding real viability consequences (dormancy, removal+replacement) does
not, on its own, prevent the underlying result — cooperation stays high
whether or not resource failure has demographic teeth, at least at the
tested deficit-duration threshold.** This is itself informative: it rules
out "agents just never had any real skin in the game" as a full
explanation, and shifts weight toward the fitness-signal mechanism (§4)
and the participation-bias mechanism (§2) as the dominant drivers.
Whether a much shorter deficit threshold would change this conclusion is
an open question — see §10's limitations.

## 4. Fitness/imitation alternatives and translation invariance (Work Package C — Question 4)

`agents/fitness.py` and `tests/test_fitness.py` formally establish (via a
uniform resource-shift test on a fixed agent pair, not just an assumption)
that `cumulative_resources` and `resource_delta` are translation-invariant
to a uniform per-agent resource shift, `recent_payoff` never reads
`resources` at all and so is trivially unaffected, and
`viability_adjusted` inherits `recent_payoff`'s invariance except when a
shift crosses the discrete dormancy threshold.

The **outcome effect** of fitness mode, holding everything else fixed, is
large and consistent across every tested ecological region
(`region_x_fitness_mode` slice):

| region | cumulative_resources | recent_payoff | resource_delta | viability_adjusted |
|---|---|---|---|---|
| abundant | 0.357 | 0.337 | 0.450 | 0.337 |
| boundary | 0.750 | 0.465 | 0.801 | 0.465 |
| depleted | 0.877 | 0.335 | 0.856 | 0.335 |

**Finding: `recent_payoff`/`viability_adjusted` (both payoff-based, not
resource-based) produce substantially lower cooperation than
`cumulative_resources`/`resource_delta` (both resource-based) in every
region, most dramatically in the depleted regime** (0.877 vs. 0.335 —
essentially the entire depleted-regime "near-unity cooperation" result
is specific to comparing agents by their *cumulative resource stock*
rather than their *recent net payoff*). This is direct evidence for
scientific question 4: relative-fitness invariance to universal
impoverishment is a real and substantial contributor to the original
result, and it is specifically the resource-based fitness signals (which
remain invariant to the uniform subsistence drain) that preserve high
cooperation under collapse — the moment fitness is redefined around
recent payoff (which universal impoverishment does *not* leave
invariant, since payoff differences between strategies are still
visible even as everyone's absolute resources fall), cooperation drops
by roughly half.

## 5. Phase-mapping methodology and results (Work Package E — Question 5, 6)

**Stage 1** (`experiments/phase_sweep.py`): a 32-point Latin Hypercube
design (`scipy.stats.qmc.LatinHypercube`, fixed seed `20260816` for
reproducibility) over six ecological parameters (`environment_regen_rate`,
`environment_capacity`, `subsistence_cost`, `payoff_temptation`,
`payoff_reward`, `distress_threshold`), 10 seeds/point (320 runs), plus a
5×5 supplemental regular grid over `environment_regen_rate` ×
`subsistence_cost` (other parameters at their sampling midpoints, 10
seeds/cell, 250 runs) built specifically for the phase-map heatmap. All
630 runs (320 + 250 + 60 Stage-2, see below) completed successfully — 0
failures (`outputs/phase_sweep_level02/sweep_manifest.json`).

Of the 32 Stage-1 points: **9 settled into a persistently abundant
regime** (mean occupancy > 0.8, fraction of time depleted = 0 for every
one of them), **20 collapsed persistently** (mean occupancy < 0.01,
fraction of time depleted ≈ 1.0 for every one of them, `std ≈ 0`), and
**3 showed genuinely mixed, seed-dependent dynamics** — neither
permanently full nor permanently empty. This confirms scientific question
5: persistent abundance and persistent collapse are both readily
reachable regimes in this parameter space, and they are *not* separated
by a wide, gradual transition zone — the supplemental grid's phase map
(`outputs/figures_level02/01_ecological_phase_map.png`) shows an almost
step-function transition in `environment_regen_rate` alone (holding other
parameters at their midpoints), consistent with the pool's logistic
regeneration having a hard sustainable-throughput ceiling
(`max_sustainable_regeneration = r·K/4`).

**Stage 2** (boundary refinement, ecology-only selection — never by
cooperation level, per the milestone's explicit instruction): of the 3
mixed-dynamics Stage-1 points, 2 met the boundary criteria (interior mean
occupancy in [0.05, 0.95], interior fraction-time-depleted in [0.02,
0.98], seed-to-seed std of fraction-time-depleted ≥ 0.03) and were rerun
at 30 seeds: `s1_031` (occupancy 0.440, fraction depleted 0.476 ± 0.341
across seeds) and `s1_011` (occupancy 0.370, fraction depleted 0.529 ±
0.256). The large seed-to-seed standard deviations (0.34, 0.26) mean these
two points are genuinely **bistable at the seed level** — different seeds
at the identical parameterization land in qualitatively different
long-run states (collapsed vs. not) — which is exactly the kind of
boundary region a robustness question (scientific question 6) needs.

**Robustness across seeds and fitness definitions (Question 6):** the
supply/depleted classification of the 29 non-boundary Stage-1 points was
unanimous across all 10 of their seeds (std = 0 for every one). The 2
selected boundary points were, by construction, the *opposite* — not
robust across seeds. Whether a region's classification is robust across
*fitness definitions* was tested by the `viability_mode_x_fitness_mode`
slice at the boundary region: mean occupancy varies by fitness mode
(0.47–0.49 for `cumulative_resources`, 0.82–0.87 for `recent_payoff`/
`viability_adjusted`, 0.36–0.39 for `resource_delta`) — **the same
ecological parameterization lands in visibly different ecological
regimes depending purely on which fitness signal governs imitation**,
because the fitness signal shapes which policies spread and therefore how
much aggregate extraction pressure the population puts on the pool. This
is a genuinely new finding: ecological regime and behavioural-adaptation
rule are not independent axes in this model.

## 6. Relationship turnover near the boundary (Work Package G — Question 7)

`experiments/turnover_boundary_sweep.py` swept five relationship-dynamics
parameters one axis at a time at both boundary points, 10 seeds/level
(280 runs, 0 failures; `outputs/turnover_boundary_level02/
turnover_boundary_summary.csv`). Two clear, opposite findings:

- **`exit_cost` and `relationship_exit_enabled` had literally zero
  measurable effect** — `relationship_turnover_rate` and
  `final_cooperation_rate` were numerically identical across every tested
  `exit_cost` value (0.2, 1.0, 3.0) and across `relationship_exit_enabled
  ∈ {True, False}`, at both boundary points. Voluntary exit is essentially
  inactive at these boundary parameterizations under the default
  `exit_resource_threshold` — turnover here is driven almost entirely by
  reconnection, not exit.
- **`mean_degree` had by far the largest effect**: at `s1_011`, turnover
  rate rose from 0.011 (`mean_degree=2`) to 0.018 (4) to 0.033 (8), and
  cooperation rose from 0.677 to 0.935 to 0.987 over the same range — a
  large, monotonic effect on both network movement and cooperation.
  `connection_accept_base_prob` and `search_cost` had smaller, mixed-sign
  effects that differed between the two boundary points (e.g. cooperation
  at `s1_031` fell from 0.833 to 0.780 as `search_cost` rose from 0.05 to
  0.8, while `s1_011` was comparatively flat).

**Finding: relationship turnover matters more near the boundary than at
the tested defaults primarily via network *density* (mean_degree), not
via exit/dissolution dynamics** — this is a more specific answer than "turnover
matters," and one the milestone brief's "do not tune turnover merely to
maximize movement" instruction is designed to surface rather than
obscure.

## 7. Perturbation at the boundary (Work Package J — Question 2, 8)

`experiments/boundary_perturbation.py` ran a matched perturbed-vs-control
design at both boundary points, 20 seeds/condition, 4 shock kinds
including the unperturbed control (160 runs, 0 failures;
`outputs/boundary_perturbation_level02/boundary_perturbation_summary.csv`).
Per the milestone's explicit instruction, this used the *boundary*
regions, never the permanently-collapsed Level-0.1 default.

- `resource_depletion` and `regeneration_reduction` shocks drove
  occupancy to ≈0 during the shock window at both boundary points (e.g.
  `s1_011`: pre-shock mean occupancy 0.644 → during-shock 0.004
  (`resource_depletion`) / 0.023 (`regeneration_reduction`)).
- `subsistence_increase` produced **numerically identical** trajectories
  to the unperturbed control. This is not a bug: subsistence is not
  routed through the pool at all (a documented Level-0.1 simplification —
  see `environment/resource_pool.py`), and none of the fixed rule-based
  policies condition their action on own resources, so a subsistence
  increase that does not push agents across the (very negative, at these
  boundary points) `distress_threshold` within the 20-step shock window
  changes nothing about interaction behaviour or pool dynamics. This is
  itself a substantive finding: at these particular boundary
  parameterizations, subsistence-side demand shocks are behaviourally
  inert unless severe or sustained enough to trigger distress.
- **`fraction_recovered` was 0.0 for every condition at both boundary
  points, including the unperturbed control.** Occupancy trended downward
  from the pre-shock window through the post-shock window even with no
  shock applied at all — these two boundary parameterizations are not
  stable equilibria within the tested 320-step horizon; they are
  transient states drifting (at a rate that varies by seed) toward
  collapse. **No recovery was observed under any condition, so none is
  claimed.** Per the classification-discipline requirement (Work Package
  I), the word "attractor" is not used anywhere in this codebase or its
  documentation: convergence, persistence, and perturbation-recovery have
  not all been established for any state this model produces — persistent
  collapse converges and persists, but recovery from it was never
  observed; the boundary region persists in neither direction robustly
  enough to test recovery meaningfully within this horizon.

## 8. Cooperation and ecological causality (Work Package F)

Per the milestone's explicit constraint, this section does not assume
cooperation is ecologically beneficial (or harmful) — it reports measured
association and lead/lag structure, including the absence of a robust
signal, as legitimate findings.
`experiments/cooperation_ecology_causality.py` ran two independent
analyses (`outputs/cooperation_ecology_causality_level02/`).

**Part 1 — cross-sectional, within-parameter-point (59 phase-sweep
points with ≥10 seeds, 0 new simulation runs; correlating each point's
seed-to-seed variation in final cooperation against that same point's
seed-to-seed variation in ecological outcome).** The *pooled* correlation
across all 630 sweep runs — ignoring which point each run came from — is
strongly negative between cooperation and mean occupancy (Pearson
−0.753) and strongly positive between cooperation and both collapse
measures (fraction-time-depleted +0.741, n-collapse-episodes +0.763).
Taken alone this pooled number would suggest "cooperation causes
collapse" — but it is confounded: ecological parameters (regeneration
rate, capacity, subsistence cost, payoff structure) simultaneously drive
*both* how much cooperation emerges and how depleted the pool becomes,
so points with harsher ecological parameters have both higher
cooperation (consistent with §2's participation-selection finding — a
depleted, dormancy-filtered population appears highly cooperative) and
lower occupancy, for reasons that need not have anything to do with each
other causally. **Controlling for this by correlating only *within* each
fixed parameter point** (i.e., across seeds that share identical
ecological parameters and differ only in stochastic realization) gives a
much weaker and inconsistent picture: of the 53 points with a defined
within-point correlation (6 of the 59 had zero seed-to-seed variance in
cooperation or occupancy and are excluded as undefined), median Pearson
correlation −0.090, median Spearman −0.174, interquartile range
[−0.535, +0.239], and only 34.0% show a positive coop-vs-occupancy
correlation at all. **The strong pooled association is overwhelmingly a
parameter confound, not evidence that cooperation and ecological state
are tightly linked once ecological parameters are held fixed** — the
within-point relationship is weak and does not have a consistent sign
across points.

**Part 2 — within-run, time-lagged (60 fresh runs: 20 seeds ×
{abundant, boundary, depleted}, population 30, 250 steps, Level-0.2
defaults; `outputs/cooperation_ecology_causality_level02/
time_lagged_summary.csv`).** In the `depleted` region every run's
occupancy is at (or pinned near) zero throughout, so the correlation is
undefined (NaN) by construction — consistent with §2/§5's finding that
this region is a genuine, near-total collapse regime, not a modeling
artifact. In `abundant`, level correlations are weakly negative (mean
−0.17) and first-differenced (trend-removed) correlations are also
weakly negative (mean −0.28, std 0.08) — a small, fairly consistent
signal that a step-to-step *increase* in cooperation co-occurs with a
step-to-step *decrease* in occupancy, or vice versa, though the
direction cannot be distinguished from the correlation alone (see next
paragraph). In `boundary`, level correlations are strongly negative
(mean −0.83) — dominated by the shared downward trend both series
exhibit as the run drifts toward depletion (§7) — but this weakens
substantially after first-differencing (mean −0.23, std 0.12),
confirming that most of the raw-level correlation is shared trend, not a
tight moment-to-moment coupling.

The lead/lag structure itself shows **no consistent directional signal**:
across seeds, the lag with the strongest first-differenced correlation
is scattered across positive, negative, and (most commonly) zero values
rather than clustering at one particular lead time — i.e., cooperation
changes and occupancy changes are best described as largely
*contemporaneous*, not one reliably preceding the other. The
incremental-R² check (does yesterday's cooperation-change improve a
one-step-ahead prediction of today's occupancy-change beyond
occupancy's own lagged value, and symmetrically) found **negligible
incremental predictive power in both directions** at every region tested
(mean incremental R² ≤ 0.017 in all eight coop/eco/direction
combinations, most well under 0.01). This is explicitly **not**
labelled Granger causality (no stationarity or specification testing was
performed) and explicitly **not** evidence of mechanistic causation in
either direction — a near-zero incremental R² is itself informative: it
means neither series' recent change history meaningfully forecasts the
other's next change, beyond what each series' own momentum already
predicts.

**Conclusion for Question set F:** this milestone found no evidence that
cooperation is ecologically beneficial, nor that it is ecologically
harmful, once ecological parameters and shared trend are accounted for.
The apparent strong pooled association reported by a naive analysis is a
parameter confound. The residual within-point, trend-removed association
is small, inconsistent in sign across points, and carries negligible
lagged predictive power in either direction. The most defensible
reading is that, in this model, ecological state and cooperation are
both largely *driven by the same exogenous ecological parameters*
rather than driving each other.

## 9. Classification definitions used

All defined, thresholded, and sensitivity-testable in
`observer/classification.py` (see `docs/odd_level0.2_addendum.md` §4.5
for the formal statement of each): **Depletion** (occupancy ≤ threshold,
instantaneous), **Ecological collapse** (contiguous depleted run ≥
minimum duration, optionally requiring sustained positive unmet demand
throughout), **Recovery** (contiguous above-threshold run ≥ minimum
duration, following a prior depletion), **Population failure**
(distressed+dormant fraction ≥ threshold), **Behavioural convergence**
(policy-diversity entropy ≤ threshold for ≥ minimum duration). Every
threshold is a documented, overridable function parameter —
`tests/test_classification.py` includes an explicit sensitivity check per
function (a tighter/looser threshold changes the classification result).

## 10. Known limitations

- The Stage-1/Stage-2 phase sweep used a reduced run shape (population 30,
  250 steps) for computational tractability, not the milestone-brief's
  implicit "full-scale" runs — documented, not silently substituted for a
  full-scale sweep. Boundary-region and perturbation follow-ups also used
  population 30.
- `cooperation_by_policy_lineage`/`cooperation_by_recent_payoff` in
  `observer/participation.py` join each interaction against *final* agent
  state rather than the lineage/payoff-bucket the agent held at
  interaction time — a documented approximation, not an exact per-event
  stamp (unlike resource-status/degree, which *are* stamped exactly).
- WP-J's shock vocabulary omits random edge loss and removal of
  high-resource agents (the milestone brief's other two named examples) —
  implementing them would have required extending the perturbation
  interface to also receive the live graph/agent list, out of scope for
  this pass.
- WP-H's factorial comparisons are four explicit 2-way slices, not a full
  Cartesian product across all five candidate factors (viability mode,
  fitness mode, punishment, turnover, ecological region) — an
  intractable ~144-cell design at the required seed counts; the four
  slices the milestone brief named as minimum requirements were run in
  full.
- The viability state machine's demographic effect was small at the
  tested `viability_deficit_steps_threshold=10-20`; a shorter threshold
  (more agents forced into dormancy sooner) was not swept and could
  change §3's conclusion — flagged as a natural next-milestone question,
  not resolved here.
- Every "region" (abundant/boundary/depleted) used in Work Package H's
  factorial comparisons is a single representative parameter point per
  region, not an average over multiple points in that region — a
  documented simplification for tractability.

## 11. Reproducibility

```
python experiments/phase_sweep.py --out outputs/phase_sweep_level02 \
    --stage1-points 32 --seeds-stage1 10 --seeds-stage2 30 --grid-levels 5 --workers 2
python experiments/boundary_perturbation.py --out outputs/boundary_perturbation_level02 --seeds 20 --workers 2
python experiments/turnover_boundary_sweep.py --out outputs/turnover_boundary_level02 --seeds 10 --workers 2
python experiments/null_model_comparisons.py --out outputs/null_model_comparisons_level02 --seeds 15 --workers 2
python experiments/make_level02_visualizations.py
```

`phase_sweep.py` is resumable (`--no-resume` to force a clean rerun); all
four scripts write a JSON manifest recording exactly which runs completed
and a CSV summary table. See `README.md` for the full command reference.
