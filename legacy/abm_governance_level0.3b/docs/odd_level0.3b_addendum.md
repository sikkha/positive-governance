# ODD-style Model Description — Level 0.3b Addendum

This document extends `docs/odd_level0.1.md`, `docs/odd_level0.2_addendum.md`,
and `docs/odd_level0.3_addendum.md` (read all three first) with what
Level 0.3b added. **Level 0.3b adds no new generative mechanism to the
model itself** — no new agent behavior, no new resource dynamics, no new
config field that changes what a simulation *does*. Every `SimulationConfig`
field Level 0.3b's scripts use already existed at the end of Level 0.3
(the seven "new" causal conditions are combinations of existing fields —
see §4). What Level 0.3b adds is entirely on the **observer side**: an
audited, burn-in-aware regime classifier; a repaired perturbation-recovery
diagnostic; and a disciplined, prospectively-registered experimental
pipeline built on top of both. This is consistent with the project's
strict generative/observer separation (`dev_mem/project_vision.md` §5) —
a validation milestone should not, and here does not, touch the
generative layer at all.

## 1. Purpose

Determine whether Level 0.3's apparent findings — social cooperation
coexisting with near-zero ecological restraint, an extraction-favoring
policy drift, and a diverse phase-search outcome distribution including
"oscillatory"/"intermittent" labels — reflect a real property of the
model, or an artifact of classification looseness, an untuned default
calibration, insufficient replication, or aggregation that hides
within-condition heterogeneity. Central question: under prospectively
selected, nondegenerate ecological conditions, does adaptive ecological
behavior causally improve, worsen, or leave unchanged ecological
persistence and perturbation recovery, relative to static/randomized/
shuffled/environment-only counterfactuals? See
`docs/level0.3b_validation_note.md` for the full findings.

## 2. New observer-side modules and functions

**`observer/regulation_diagnostics.py`, Work Package A section**
(appended after Level 0.3's original seven-criterion module, which is
left completely unmodified): `classify_regime` (the audited classifier,
`CLASSIFIER_VERSION = "0.3b-v1"`), plus 8 supporting diagnostic functions
(`linear_trend`, `rolling_variance`, `detect_peaks_and_troughs`,
`peak_to_trough_amplitude`, `autocorrelation`, `dominant_spectral_power_
ratio`, `band_transitions`, `_burn_in_window`). See §3 for the decision
logic.

**`observer/regulation_diagnostics.py`, Work Package J section**:
`recovery_eligibility`, `recovery_quality`, `assess_perturbation_recovery`
— replace Level 0.3's un-screened `perturbation_recovery` (also left
unmodified) with an eligibility-gated, sustained-recovery-aware
definition. See §6.

No other `src/abm_governance/` module changed. `pyproject.toml` gained a
`scipy>=1.10` declared dependency (a housekeeping fix — `scipy` was
already a de facto dependency via Level 0.2/0.3's `scipy.stats.qmc`
import, never previously declared; Level 0.3b's `classify_regime` is the
first *core-package* use of `scipy` (`scipy.signal.find_peaks`), making
the omission a real gap worth fixing now).

## 3. The audited regime classifier

`classify_regime(occupancy_series, burn_in_fraction=0.2, ...)`:

1. **Burn-in exclusion.** The first `burn_in_fraction` of steps (default
   20%) are excluded from every subsequent computation — reported as
   `analyzed_window`, never silently mixed into the classification.
2. **Decision sequence**, first match wins: `depleted` (terminal
   occupancy at/below a depletion threshold, minimum duration, no more
   than 5% of post-burn-in time above threshold — the "no sustained
   recovery" requirement) → `abundant` (symmetric, at/above an abundance
   threshold) → **`oscillatory`** (>= 3 completed cycles by peak/trough
   counting, minimum median peak-to-trough amplitude, minimum
   autocorrelation at the best non-zero lag, no strong secular trend,
   and — the "persistence across multiple windows" requirement — both
   halves of the analyzed window independently show near-enough the
   required cycle count) → **`intermittent`** (more than a configured
   minimum number of depleted/interior/abundant band transitions, after
   collapsing dwells shorter than a minimum-dwell floor, and not already
   classified oscillatory) → `interior-persistent` (minimum fraction of
   post-burn-in steps inside the interior band, terminal occupancy
   inside it, no strong secular trend) → `unclassified` (the explicit
   fallback; never forced).
3. Every supporting statistic (trend slope/R², fraction interior/
   depleted/abundant, peak-to-trough amplitude, cycle count, best-lag
   autocorrelation, dominant spectral power ratio, band-transition count
   and segments, and a `has_multi_cycle_oscillation_signature` flag
   computed *regardless* of the final label) is exported unconditionally.

**Documented, disclosed deviation from the milestone brief's prose
category-listing order**: oscillatory/intermittent are checked *before*
interior-persistent (the brief's prose lists interior-persistent first).
Checking interior-persistence first would silently absorb any trajectory
that oscillates *within* the interior band into "interior-persistent"
before the oscillatory test is ever reached — exactly the failure mode
this audit exists to catch. See the module's own extensive comment and
`dev_mem/status_update.md`'s Level 0.3b entry for the full rationale.

**A numerical bug found and fixed while building the validation tests**:
a mathematically constant series carries floating-point variance on the
order of 1e-33 to 1e-36, not exactly `0.0` — an unguarded `var == 0`
check let this near-zero-but-nonzero variance amplify float noise into
spurious near-1.0 "autocorrelation" on a perfectly flat series. Fixed
with an explicit tolerance constant (`_NEAR_ZERO_ATOL = 1e-9`).

## 4. The seven (plus one preserved) causal conditions

`experiments/level03b_common.py::CONDITION_OVERRIDES` — each condition is
a small dict of `SimulationConfig` field overrides applied on top of a
candidate's own endogenous parameters, exactly the orthogonal-flags
design Level 0.3's WP-F already established:

| condition | mechanism |
|---|---|
| `endogenous` | no override — full imitation/mutation/patch-effect active |
| `frozen` | `ecological_imitation_enabled=False, ecological_mutation_rate=0.0` |
| `randomized` | `ecological_policy_randomized_each_step=True` |
| `shuffled` | `ecological_policy_shuffle=True` |
| `environment_only` | `ecological_harvest_unit=0.0, ecological_maintenance_unit=0.0, ecological_search_cost=0.0` — patch regeneration proceeds untouched; agent ecological ledgers are structurally zero throughout (no request magnitude to speak of), the genuine environmental baseline |
| `impact_disabled` | `ecological_actions_affect_patch=False` — preserves Level 0.3's original `no_effect` condition under a name that states its actual meaning: agents still decide/pay/earn on their own ledger via the same allocation arithmetic, but the patch itself is untouched by any agent action (only regeneration runs) — an artificial impact-disabled intervention, not a physically conserved economy |
| `maintenance_disabled` | `ecological_maintenance_unit=0.0` — extraction unaffected; every agent's maintenance investment and its effect are structurally zero regardless of `maintenance_propensity` |
| `ecological_mutation_disabled` | `ecological_mutation_rate=0.0` only — imitation stays active, isolating mutation's specific contribution |

`environment_only` and `impact_disabled` differ in one load-bearing way:
under `environment_only` there is no agent ecological payoff at all (the
ledger is trivially zero — see `tests/test_level03b_pipeline.py::
test_environment_only_condition_zeroes_agent_ecological_ledgers`); under
`impact_disabled` the agent ledger is fully populated (nonzero,
meaningful extraction/maintenance gains computed by the same pure
`allocate_extraction` arithmetic the endogenous condition uses) but never
reaches the patch.

## 5. The fitness-stream axis

No new mechanism: `experiments/level03b_fitness_stream.py` crosses the
already-implemented `ecological_inheritance_mode` values.
`"independent"` (this project's default) is the `"ecological"` stream —
ecological-policy imitation selects on `fitness_signal(..., stream=
"ecological")`, governed by `fitness_mode_ecological`. `"coupled_same_
model"` is the `"total"` stream — one shared peer draw and Fermi decision,
computed on `stream="total"`, drives both the social and ecological copy
together.

**An architectural interaction discovered while building this
experiment, documented rather than patched around**:
`coupled_dual_imitation_round` does not check
`ecological_policy_randomized_each_step` before copying a peer's
ecological policy (the copied value is behaviorally inert under
`"randomized"`, since the per-step decision never reads the stored
policy either way, but the *reported* before/after propensity
composition under coupled+randomized reflects imitation noise on an
already-irrelevant field); and freezing ecology under
`"coupled_same_model"` requires `imitation_enabled=False` (not
`ecological_imitation_enabled`, which the coupled dispatch branch never
reads), which necessarily freezes social imitation too, since the two
dimensions share one decision by the coupled mode's own design. Both are
handled explicitly in `_condition_overrides_for_mode`, not worked around
in the generative layer.

## 6. The repaired perturbation-recovery diagnostic

`recovery_eligibility(pre_shock_series, post_shock_series,
control_post_shock_series=None, ...)` screens five conditions (pre-shock
occupancy above the depletion threshold; the matched control not itself
already collapsing, when supplied; a minimum meaningful early post-shock
displacement; a minimum post-shock horizon) before any recovery statistic
is computed at all — an ineligible run reports `eligible: False` with
explicit reasons, never `recovered: False`.

`recovery_quality(...)` (called only when eligible) distinguishes
`time_to_first_reentry` (the first instantaneous single-step crossing
back into the tolerance-widened pre-shock band) from
`time_to_sustained_recovery` (the first entry that stays in-band for a
minimum consecutive duration) — `recovered` reflects only the sustained
definition. Also exports `max_displacement`, `post_recovery_persistence_
fraction`, `residual_distance_from_control`, and `overshoot`.

`assess_perturbation_recovery(...)` combines both calls; every Level
0.3b perturbation script calls this, never the two pieces separately.

## 7. The candidate-selection pipeline (observer-side orchestration, not a new mechanism)

`experiments/level03b_phase_search_reanalysis.py` re-materializes the
exact 48 `(point_id, seed)` pairs Level 0.3's phase search already
committed (deterministic reproduction, cross-checked bit-for-bit against
the committed outcomes — see the module docstring), applying
`classify_regime` to the full trajectory. `experiments/
level03b_supplemental_search.py` is the single prespecified supplemental
LHS batch (fixed design seed, fixed ranges reused unchanged from Level
0.3's own `PARAM_LOWS`/`PARAM_HIGHS`), invoked only because the
reanalysis found no eligible candidate — see
`dev_mem/status_update.md`'s Level 0.3b entry for the pre-registration
record. `experiments/level03b_candidate_registry.py` applies fixed,
outcome-blind eligibility rules to the combined 144 (16+32)×3-seed points
and writes `outputs/level03b_candidate_registry/candidate_registry.json`
— the single source every downstream script reads from.

## 8. Compatibility

Level 0.3b changes nothing about `Simulation`, `Agent`, any `agents/`
module, `environment/patches.py`, or any Level 0-0.3 config field's
default value or validated range. A default `SimulationConfig()` run
(`ecology_topology="global_pool"`) is exactly as Level 0.3 left it —
`tests/test_compat_regression.py` and the Level 0.2/0.3 compatibility
structural checks in `tests/test_level03_niche_construction.py` are
unmodified and still pass. `nonstationary_classification` and
`perturbation_recovery` (Level 0.3's originals) are still present,
unmodified, still what every already-committed `outputs/niche_*` file
was computed with.
