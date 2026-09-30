"""Level 1.3, Work Package H (Section 13): outcome-blind phenotype
discovery, repeated for Level 1.3.

Context-loss disclosure (same caveat as every earlier Level 1.3 work
package this session): Section 13's verbatim text is not recoverable
after this session's compaction. What is recoverable and treated as
authoritative here is Level 1.2's own precedent, which this module
follows deliberately closely: ``observer/institutional_phenotype.py``
builds a raw, un-clustered ``X = (C, E, L, ...)`` feature-vector dict
(one call per seed-run), and the entirely separate, FROZEN,
mechanism-agnostic clustering machinery in
``observer/phenotype_discovery.py`` (``CLUSTERING_PIPELINE_VERSION =
"clustering_pipeline_v1"``) consumes that vector without caring what
generated it. "Repeat for Level 1.3" is read here as: build the
Level-1.3-specific analogue of ``institutional_phenotype_vector`` --
this module -- and feed it into the SAME, UNMODIFIED clustering
pipeline (never fork or re-derive clustering logic here; see this
module's own tests, which call ``observer.phenotype_discovery``
functions directly against this module's output to prove that
contract holds).

**GENERATE FIRST. MEASURE SECOND. DISCOVER THIRD. INTERPRET LATER** --
the same discipline Level 1.2's module states: nothing here reads any
dissertation label, trajectory name, or forbidden Section-2 vocabulary
(see ``tests/test_level13_sem_firewall_extension.py``'s scan, which
covers every module under ``src/abm_governance`` automatically, this
one included, with no per-file update needed).

Fourteen candidate dimensions, each built from a Work Package this
project already independently justified (never invented fresh for
clustering's sake):

- Eight ``seq_<dimension>`` features: Work Package B's own
  ``sequencing_vector`` first-sustained-crossing step for each of its
  eight institutional-response dimensions, normalized to a fraction of
  ``n_steps`` (``NaN`` if that dimension never crossed threshold this
  run -- Section 7's "do not assign a sequencing category where
  activation is absent" applies here too, via ``build_feature_matrix``'s
  existing structural-``NaN``-preserving contract).
- ``entrenchment``: Work Package C's ``entrenchment_level`` at
  ``current_step``, averaged across ``rule_by_patch``'s currently
  active rules.
- ``performance_legitimacy``/``procedural_legitimacy``: Work Package
  D's two ledgers, read directly off each active rule's current
  ``SharedRule`` field (a snapshot, not a time average -- distinguished
  in each record's own ``construct_type``).
- ``conversion_incidence``: Work Package F's
  ``conversion_incidence_series``, final value.
- ``S_obs``/``Z_obs``: Work Package G's ``s_obs_z_obs_summary``,
  full-run mean.

A rule intentionally NOT bent for this module: unlike
``institutional_phenotype.py``'s dimensions, several of these (the
eight sequencing features, ``S_obs``/``Z_obs``) are natively
population/run-wide already, not built per-patch then combined -- so
there is no ``V``-style two-part special case here, and
``build_feature_matrix`` needs no modification to consume this
module's ``dimension_keys`` (every key maps to exactly one scalar
``"value"``, the existing generic case that function already handles)."""

from __future__ import annotations

from abm_governance.core.entrenchment import entrenchment_level
from abm_governance.core.events import EventLog
from abm_governance.observer.institutional_conversion import conversion_incidence_series
from abm_governance.observer.sequencing_diagnostics import (
    INSTITUTIONAL_RESPONSE_DIMENSIONS,
    institutional_response_series,
    sequencing_vector,
)
from abm_governance.observer.sz_obs import s_obs_z_obs_summary

#: The full Level 1.3 candidate dimension key set, in a fixed order --
#: passed to ``phenotype_discovery.build_feature_matrix`` as
#: ``dimension_keys``.
LEVEL13_DIMENSION_KEYS: tuple[str, ...] = tuple(
    f"seq_{name}" for name in INSTITUTIONAL_RESPONSE_DIMENSIONS
) + ("entrenchment", "performance_legitimacy", "procedural_legitimacy", "conversion_incidence", "S_obs", "Z_obs")


def _record(value: float, construct_type: str) -> dict:
    return {"value": value, "construct_type": construct_type}


def level13_phenotype_vector(
    event_log: EventLog,
    rule_by_patch: dict,
    n_steps: int,
    current_step: int,
    entrenchment_maturation_steps: int,
    min_duration_steps: int = 10,
    patch_ids: frozenset[int] | None = None,
) -> dict:
    """The full Level 1.3 candidate feature-vector dict for one seed-run
    -- one call per completed run, exactly mirroring
    ``institutional_phenotype_vector``'s own "seed-run is the primary
    independent observation" convention. Every value is a raw record
    (never combined into a single score anywhere in this function)."""
    response = institutional_response_series(event_log, n_steps, patch_ids)
    vector = sequencing_vector(response, min_duration_steps)
    out: dict[str, dict] = {}
    for name in INSTITUTIONAL_RESPONSE_DIMENSIONS:
        step = vector.get(name)
        value = float("nan") if step is None else step / n_steps
        out[f"seq_{name}"] = _record(value, "first_sustained_crossing_fraction")

    active_rules = [r for r in rule_by_patch.values() if r.active]
    if active_rules:
        mean_entrenchment = sum(
            entrenchment_level(current_step - r.founding_step, entrenchment_maturation_steps) for r in active_rules
        ) / len(active_rules)
        mean_performance = sum(r.performance_legitimacy for r in active_rules) / len(active_rules)
        mean_procedural = sum(r.procedural_legitimacy for r in active_rules) / len(active_rules)
    else:
        mean_entrenchment = mean_performance = mean_procedural = float("nan")
    out["entrenchment"] = _record(mean_entrenchment, "snapshot_current_state_mean")
    out["performance_legitimacy"] = _record(mean_performance, "snapshot_current_state_mean")
    out["procedural_legitimacy"] = _record(mean_procedural, "snapshot_current_state_mean")

    conversion_series = conversion_incidence_series(event_log, n_steps, patch_ids)
    out["conversion_incidence"] = _record(float(conversion_series[-1]) if n_steps > 0 else float("nan"), "final_step_fraction")

    sz_summary = s_obs_z_obs_summary(event_log, n_steps, patch_ids)
    out["S_obs"] = _record(sz_summary["S_obs"], "full_run_temporal_mean")
    out["Z_obs"] = _record(sz_summary["Z_obs"], "full_run_temporal_mean")
    return out
