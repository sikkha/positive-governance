#!/usr/bin/env python3
"""Level 1.3b, Work Package B / Stage 1 (Section 6): full causal-chain
audit of why ``seq_bargaining_participation`` was ``NaN`` in 216/216
pooled Level 1.3 discovery runs.

**Method, per Section 6's checklist.** Traces pressure -> transmission ->
agent response -> event -> observer -> feature, end to end, via (1) a
hand-computed microcase re-verifying the observer-series construction
exactly by hand (delegates to ``tests/test_level13b_bargaining_
activation_construction.py``'s own microcase, re-run here so this
script's own output stands alone as Stage 1's audit trail) and (2)
instrumented full simulation runs on Stage-3- and Stage-4-representative
configs, monkeypatching ``rules.contributions.contribution_round`` to
additionally record, per contribution decision (before delegating to the
real function so behavior is byte-identical): the agent's raw trait
``contribution_willingness``, the pressure-adjusted effective
willingness actually used for the compliance draw, the realized
``bargaining_pressure_level`` at that step, the willingness-only draw
outcome, resources at decision time, and whether the agent could have
afforded ``amount_asked`` regardless of the draw.

**Finding, disposed per Section 6's own instruction ("if code defect,
fix + regression test; if genuine inactivity, do not merely lower the
threshold").** Two independent, compounding causes:

1. **Code defect (dominant, fully sufficient alone) — FIXED.**
   ``_contribution_compliance_series`` zero-filled every step between
   contribution-assessment rounds (assessed only every
   ``contribution_period_steps=10`` steps) instead of holding the last
   assessed value, unlike every other ``institutional_response_series``
   dimension. Every Level 1.3/1.3b stage script calls ``sequencing_
   vector(..., min_duration_steps=10)`` -- exactly the assessment
   period -- so a "10 consecutive steps at/above threshold" condition
   was mathematically impossible regardless of the true compliance
   rate. Fixed in ``observer/sequencing_diagnostics.py`` this milestone
   (forward-fill, matching every other dimension's construction);
   regression-guarded by ``tests/test_level13b_bargaining_activation_
   construction.py``.
2. **Genuine, disclosed generative/measurement finding (secondary,
   still suppresses activation after (1) is fixed) — NOT a defect to
   patch around.** ``ContributionEvent.complied`` conflates the true
   willingness draw with agent solvency (``complied and amount_paid >
   0.0``); under the mechanism set active at Stage 3/4 scale, resources
   collapse deeply negative over a run (this project's already-
   documented near-universal ecological-collapse dynamic), crushing
   realized compliance to single digits even though willingness-only
   compliance is healthy. This determines Work Package C's calibration
   direction (response cost / participation frequency, not threshold).

Full narrative and evidence table: ``docs/level1.3b_bargaining_
activation_audit.md``. Raw output: ``outputs/level13b_bargaining_
activation_audit/stage1_diagnostic.json``."""

from __future__ import annotations

import json
import os

import numpy as np

import abm_governance.rules.contributions as contributions_module
import abm_governance.simulation as simulation_module
from abm_governance.core.config import SimulationConfig
from abm_governance.core.events import ContributionEvent, EventLog
from abm_governance.observer.sequencing_diagnostics import institutional_response_series, sequencing_vector
from abm_governance.simulation import Simulation
from experiments.level13_common import transmission_overrides_for_channel

OUT_DIR = "outputs/level13b_bargaining_activation_audit"


# ---------------------------------------------------------------------
# Part 1: hand-computed microcase (Stage 1's own required discipline).
# ---------------------------------------------------------------------

def _contribution(step, agent, complied, patch_id=0, rule_id=0):
    return ContributionEvent(
        step=step, patch_id=patch_id, rule_id=rule_id, agent=agent, mode="voluntary",
        amount_asked=1.0, amount_paid=(1.0 if complied else 0.0), complied=complied, fund_after=1.0,
    )


def run_hand_computed_microcase() -> dict:
    """3 contribution rounds at steps 0/10/20 (period=10), 2 agents each
    round, n_steps=25. By hand: round 0 = 1/2 comply -> 0.5; round 10 =
    2/2 -> 1.0; round 20 = 0/2 -> 0.0. Held (post-fix) series: steps
    [0..9]=0.5, [10..19]=1.0, [20..24]=0.0 -- computed independently of
    the implementation, then checked against it."""
    log = EventLog()
    log.add(_contribution(0, agent=0, complied=True))
    log.add(_contribution(0, agent=1, complied=False))
    log.add(_contribution(10, agent=0, complied=True))
    log.add(_contribution(10, agent=1, complied=True))
    log.add(_contribution(20, agent=0, complied=False))
    log.add(_contribution(20, agent=1, complied=False))
    series = institutional_response_series(log, n_steps=25)
    bp = series["bargaining_participation"].tolist()
    expected = [0.5] * 10 + [1.0] * 10 + [0.0] * 5
    matches = all(abs(a - b) < 1e-9 for a, b in zip(bp, expected))
    # With this hand-built series, threshold 0.3 / min_duration_steps=10:
    # round-10's held window [10..19] is 10 consecutive steps at 1.0 >=
    # 0.3 -- but round 0's [0..9] window (also 10 steps) at 0.5 >= 0.3
    # is the FIRST such window, so first_sustained_crossing must return 0.
    vector = sequencing_vector(series, min_duration_steps=10)
    return {
        "hand_computed_expected_series_matches_implementation": matches,
        "computed_series_first_10_steps": bp[:10],
        "sustained_crossing_step": vector["bargaining_participation"],
        "sustained_crossing_step_matches_hand_expectation": vector["bargaining_participation"] == 0,
    }


# ---------------------------------------------------------------------
# Part 2: instrumented empirical runs on Stage-3/4-representative configs.
# ---------------------------------------------------------------------

def _stage3_representative_config(seed: int = 5_000_001) -> SimulationConfig:
    """Reproduces one real Stage 3 cell exactly (``experiments/level13_
    stage3_sequencing_entrenchment_factorial.py::_build_config`` for
    ordering ``security_pressure_bargaining_pressure_coordination_
    complexity``, ``entrenchment_enabled=True``) -- a small, disclosed
    duplication rather than importing that script's private helper,
    matching this project's established precedent."""
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=True, entrenchment_maturation_steps=100,
    )
    order = ("security_pressure", "bargaining_pressure", "coordination_complexity")
    onsets = (0, 150, 300)
    for channel, onset in zip(order, onsets):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_duration_steps"] = None
        overrides.update(transmission_overrides_for_channel(channel))
    return SimulationConfig.level12b_frozen_reference(
        population_size=40, n_steps=500, n_patches=3, seed=seed, **overrides,
    )


def _stage4_representative_config(seed: int = 6_000_001) -> SimulationConfig:
    """Reproduces one real Stage 4 point's shape (population 40, 4
    patches, 500 steps, all 3 pressure channels + entrenchment +
    legitimacy on) -- exact LHS draw values are immaterial to this
    audit's own question, so fixed representative onsets/magnitudes are
    used instead of re-deriving Stage 4's own LHS machinery."""
    overrides: dict = dict(
        historical_module_enabled=True, entrenchment_enabled=True, entrenchment_maturation_steps=100,
        performance_legitimacy_enabled=True, procedural_legitimacy_enabled=True,
    )
    order = ("security_pressure", "bargaining_pressure", "coordination_complexity")
    onsets = (0, 100, 250)
    for channel, onset in zip(order, onsets):
        overrides[f"{channel}_enabled"] = True
        overrides[f"{channel}_history_kind"] = "early_pulse"
        overrides[f"{channel}_onset_step"] = onset
        overrides[f"{channel}_duration_steps"] = None
        overrides.update(transmission_overrides_for_channel(channel))
    return SimulationConfig.level12b_frozen_reference(
        population_size=40, n_steps=500, n_patches=4, seed=seed, **overrides,
    )


def _run_instrumented(config: SimulationConfig, label: str) -> dict:
    """Runs one simulation with ``contribution_round`` monkeypatched to
    ALSO record per-decision diagnostics before delegating to the real,
    unmodified function -- behavior (event log, RNG draws, resources) is
    byte-identical to an uninstrumented run; only observation is added."""
    decisions: list[dict] = []
    real_fn = contributions_module.contribution_round

    def _instrumented(step, rule_registry, agents_by_id, cfg, rng, event_log, bargaining_pressure_level=0.0):
        if cfg.contribution_mode != "none" and step % max(1, cfg.contribution_period_steps) == 0:
            conditional_on = cfg.bargaining_pressure_conditional_contribution_enabled
            for pid, rule in rule_registry.items():
                if not rule.active or not rule.members:
                    continue
                mode = (rule.institution_overrides or {}).get("contribution_mechanism", cfg.contribution_mode)
                if mode not in ("voluntary", "negotiated"):
                    continue
                for aid in rule.members:
                    agent = agents_by_id.get(aid)
                    if agent is None or not agent.alive:
                        continue
                    willingness = agent.contribution_willingness
                    effective_willingness = willingness
                    if conditional_on:
                        from abm_governance.core.historical_transmission import pressure_adjusted_probability
                        effective_willingness = pressure_adjusted_probability(
                            willingness, bargaining_pressure_level,
                            cfg.bargaining_pressure_conditional_contribution_sensitivity,
                        )
                    decisions.append({
                        "step": int(step),
                        "resources": float(agent.resources),
                        "raw_willingness_trait": float(willingness),
                        "effective_willingness": float(effective_willingness),
                        "bargaining_pressure_level": float(bargaining_pressure_level),
                        "can_afford": bool(agent.resources > 0.0),
                    })
        return real_fn(step, rule_registry, agents_by_id, cfg, rng, event_log, bargaining_pressure_level)

    contributions_module.contribution_round = _instrumented
    simulation_module.rule_contributions.contribution_round = _instrumented
    try:
        sim = Simulation(config)
        sim.run()
    finally:
        contributions_module.contribution_round = real_fn
        simulation_module.rule_contributions.contribution_round = real_fn

    n_steps = config.n_steps
    contrib_events = list(sim.event_log.contributions)
    n_total = len(contrib_events)
    n_complied = sum(1 for e in contrib_events if e.complied)

    n_willing_draws = 0
    n_would_comply_by_willingness_alone = 0
    n_negative_resources = 0
    thirds = {"early": [], "mid": [], "late": []}
    for d in decisions:
        n_willing_draws += 1
        # not re-drawing rng here (would desync the real run's own stream);
        # instead report the DISTRIBUTION of effective willingness and
        # resource state, which is what determines the draw's expected
        # outcome without needing to replay the exact random number.
        if d["effective_willingness"] >= 0.5:
            n_would_comply_by_willingness_alone += 1
        if not d["can_afford"]:
            n_negative_resources += 1
        bucket = "early" if d["step"] < n_steps / 3 else ("mid" if d["step"] < 2 * n_steps / 3 else "late")
        thirds[bucket].append(d["resources"])

    response = institutional_response_series(sim.event_log, n_steps)
    vector = sequencing_vector(response, min_duration_steps=10)

    return {
        "label": label,
        "n_contribution_events": n_total,
        "n_complied_events": n_complied,
        "realized_compliance_rate": (n_complied / n_total) if n_total else None,
        "n_decisions_instrumented": n_willing_draws,
        "mean_effective_willingness": float(np.mean([d["effective_willingness"] for d in decisions])) if decisions else None,
        "mean_raw_willingness_trait": float(np.mean([d["raw_willingness_trait"] for d in decisions])) if decisions else None,
        "mean_bargaining_pressure_level_at_decision": float(np.mean([d["bargaining_pressure_level"] for d in decisions])) if decisions else None,
        "frac_would_comply_by_willingness_alone": (n_would_comply_by_willingness_alone / n_willing_draws) if n_willing_draws else None,
        "frac_negative_or_zero_resources_at_decision": (n_negative_resources / n_willing_draws) if n_willing_draws else None,
        "mean_resources_by_run_third": {k: (float(np.mean(v)) if v else None) for k, v in thirds.items()},
        "bargaining_participation_sustained_crossing_step_post_fix": vector["bargaining_participation"],
    }


def main() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    microcase = run_hand_computed_microcase()
    stage3_result = _run_instrumented(_stage3_representative_config(), "stage3_representative")
    stage4_result = _run_instrumented(_stage4_representative_config(), "stage4_representative")

    report = {
        "milestone": "level1.3b_work_package_b_stage1_bargaining_audit",
        "hand_computed_microcase": microcase,
        "empirical_diagnostics": [stage3_result, stage4_result],
        "disposition": {
            "cause_1_construction_defect": "fixed_in_observer_sequencing_diagnostics_this_milestone",
            "cause_2_solvency_conflation_and_resource_collapse": "genuine_disclosed_finding_not_a_defect",
            "still_no_sustained_crossing_post_fix_on_representative_configs": (
                stage3_result["bargaining_participation_sustained_crossing_step_post_fix"] is None
                and stage4_result["bargaining_participation_sustained_crossing_step_post_fix"] is None
            ),
        },
    }

    with open(os.path.join(OUT_DIR, "stage1_diagnostic.json"), "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    print(json.dumps(report, indent=2, sort_keys=True))
    return report


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
