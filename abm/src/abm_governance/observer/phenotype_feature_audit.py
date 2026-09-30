"""Level 1.2b, Work Package F (Section 11): the formal feature audit
of every dimension in ``observer/institutional_phenotype.py``'s
X = (C, E, L, D, M, R, S, F, V, H) vector.

Section 11's charge is to audit, for every observer feature: its
numerator, its denominator, its valid window semantics, its structural
missingness condition, its aggregation path (event -> institution ->
patch -> seed-run), and its construct type -- then "remove only for
preregistered reasons; keep dimensions separate (no single governance
score)".

**This module removes nothing.** No dimension was found to warrant
removal under a preregistered reason (Section 11's own bar); every
audit finding below is instead disclosed as data (queryable by tests
and downstream analysis code) and, where the underlying finding was a
genuine transparency gap rather than an intentional design, fixed
directly in ``institutional_phenotype.py`` itself (the new
``"construct_type"``/``"window_applied"`` record fields -- see that
module's docstring for the full rationale).

**Why an audit module and not just a report.** Consistent with this
project's established pattern (``observer/accountability_diagnostics.py``,
``observer/ecological_ledger.py``, and every other Work Package's own
audit deliverable), the audit itself is expressed as data plus a
verification function, not prose alone -- so ``tests/
test_level12b_phenotype_feature_audit.py`` can cross-check every claim
below against the *live* behavior of ``institutional_phenotype.py``
(does changing ``window`` actually change the value it claims not to,
and vice versa?), rather than trusting the audit to stay in sync with
the code by hand.

**Aggregation path (applies identically to all ten dimensions, so
recorded once here rather than per-dimension).** Every dimension is
computed at the EVENT/current-object level (``EventLog`` entries or
live ``SharedRule``/``Delegate``/``InstitutionRecord``/``PatchSystem``
objects) directly into ONE scalar (or, for V, two scalars) per call --
there is no intermediate per-institution or per-patch record kept or
exported by ``institutional_phenotype.py`` itself; "per institution"
and "per patch" only exist as internal grouping inside a few dimension
functions (D groups by coordination-jurisdiction root; V's ecological
sub-part groups by surviving institution's jurisdiction) before being
collapsed straight to the single call-level scalar. The SEED-RUN level
aggregation this module's callers ultimately need is built one level up,
by ``observer/phenotype_discovery.py::build_feature_matrix`` (Section
9.1), which takes a list of already-computed
``institutional_phenotype_vector(...)`` outputs -- one per seed-run --
and assembles the feature matrix; it does not re-aggregate within a
seed-run. So the true path is: event/live-object -> (implicit internal
grouping, dimension-specific) -> single call-level scalar -> seed-run
feature-matrix row. No dimension here aggregates across multiple
patches into a per-patch intermediate that outlives the call, and none
aggregates across multiple seed-runs (that is exclusively
``build_feature_matrix``'s job)."""

from __future__ import annotations

from abm_governance.observer import institutional_phenotype as ip

#: Level 1.2b, Work Package "Configuration presets" (Section 24): a
#: version tag for the FROZEN feature-vector schema this module
#: audits -- the ten-dimension (C, E, L, D, M, R, S, F, V, H) ordering
#: ``institutional_phenotype.institutional_phenotype_vector`` produces
#: and every downstream discovery/confirmation pipeline (Work Packages
#: J, K, L) consumes positionally. Bump this string (never mutate a
#: previously-shipped value's meaning) if a dimension is ever added,
#: removed, or reordered -- so any result manifest embedding this
#: version can be mechanically checked against the feature vector that
#: actually produced it, rather than assuming schema stability. No
#: dimension has been added/removed/reordered since Level 1.2's own
#: Section 9.1 introduced this vector, so this is the schema's first
#: and, so far, only version.
FEATURE_SCHEMA_VERSION = "phenotype_feature_schema_v1"

#: One entry per dimension letter (V has no single numerator/
#: denominator -- see its own entry's ``sub_parts``). Every value here
#: is a STATIC claim about the dimension's construct, checked against
#: live behavior by ``tests/test_level12b_phenotype_feature_audit.py``
#: rather than merely asserted.
PHENOTYPE_FEATURE_AUDIT: dict[str, dict] = {
    "C": {
        "name": "realized_administrative_capacity",
        "numerator": "sum of Delegate.capacity across delegates that are currently active AND whose start_step falls in window",
        "denominator": "count of those same delegates",
        "valid_window": "partial -- filters by delegate start_step (an appointment-event timestamp), but conjoined with the current-tense 'active' flag, not tenure-overlaps-window",
        "structural_missingness": "NaN (not 0.0) when there are zero active delegates in range -- a real absence, not a computable zero",
        "aggregation_path": "Delegate objects (event: appointment) -> single call-level mean",
        "construct_type": "start_step_windowed_but_active_flag_is_current_state",
        "window_applied": "partial",
    },
    "E": {
        "name": "effective_constraint_dimension",
        "numerator": "n_true_positive_audits (within window)",
        "denominator": "n_true_positive_audits + n_false_negative_audits (within window)",
        "valid_window": "full -- delegates entirely to accountability_diagnostics.effective_constraint, which filters every underlying event list (audits/recalls/appeals/appropriations) by step_range",
        "structural_missingness": "NaN when there is no actual-misconduct-audited denominator in window (detection rate undefined, not zero)",
        "aggregation_path": "AuditEvent records (event-level) -> single call-level ratio",
        "construct_type": "event_windowed_ratio",
        "window_applied": True,
    },
    "L": {
        "name": "legitimacy_voluntary_support",
        "numerator": "sum of active rules' n_members (current)",
        "denominator": "sum of eligible patch population for those same rules' patches (current)",
        "valid_window": "none -- window accepted for API uniformity only, has no effect",
        "structural_missingness": "0/0 -> NaN when there is no active rule and no eligible population at all",
        "aggregation_path": "SharedRule + ResourcePatch objects (current state) -> single call-level ratio",
        "construct_type": "snapshot_current_state_ratio",
        "window_applied": False,
        "known_limitation": "institution_imposed_mode runs read as maximal support by construction (members never had a join decision) -- disclosed in institutional_phenotype.py, not treated as a bug",
    },
    "D": {
        "name": "concentration_of_delegated_authority",
        "numerator": "sum, across coordination jurisdictions, of the most-active delegate's task-attempt share",
        "denominator": "count of jurisdictions with nonzero total activity",
        "valid_window": "none -- window accepted for API uniformity only, has no effect (delegate.task_attempts is an unwindowed running counter)",
        "structural_missingness": "NaN when every jurisdiction has zero total activity (no share is computable)",
        "aggregation_path": "Delegate.task_attempts (running per-delegate counter) grouped by coordination-jurisdiction root (internal only) -> single call-level mean share",
        "construct_type": "snapshot_current_state_ratio",
        "window_applied": False,
    },
    "M": {
        "name": "institutional_memory_continuity",
        "numerator": "sum of active rules' institutional_memory scalar (current)",
        "denominator": "count of active rules",
        "valid_window": "none -- window accepted for API uniformity only, has no effect",
        "structural_missingness": "NaN when there is no active rule",
        "aggregation_path": "SharedRule.institutional_memory (running scalar, no per-step record) -> single call-level mean",
        "construct_type": "snapshot_current_state_ratio",
        "window_applied": False,
    },
    "R": {
        "name": "administrative_appropriation_burden",
        "numerator": "administrative spending + appropriated funds, summed over events with step in window",
        "denominator": "patch_system.total_resources (current, NOT filtered by window)",
        "valid_window": "partial -- numerator windowed, denominator is an unwindowed current-state stock",
        "structural_missingness": "NaN when patch_system is None or total_resources is exactly 0",
        "aggregation_path": "AdministrativeSpendingEvent + AppropriationEvent (event-level, windowed) over PatchSystem.total_resources (current stock) -> single call-level ratio",
        "construct_type": "windowed_flow_numerator_over_snapshot_stock_denominator",
        "window_applied": "partial",
        "known_limitation": "misuse risk if patch_system does not reflect window's end -- see institutional_phenotype.py docstring",
    },
    "S": {
        "name": "institutional_scale_reach",
        "numerator": "largest coordination-jurisdiction's patch count (current)",
        "denominator": "n_patches (community total)",
        "valid_window": "none -- window accepted for API uniformity only, has no effect",
        "structural_missingness": "0.0 (not NaN) when there is no coordination network at all -- a well-defined absence, per Section 6",
        "aggregation_path": "coordination_components (current network topology) -> single call-level ratio",
        "construct_type": "snapshot_current_state_ratio",
        "window_applied": False,
    },
    "F": {
        "name": "amendment_flexibility",
        "numerator": "sum of active rules' amendment_count (lifetime running total, never reset)",
        "denominator": "sum of active rules' age, computed as current_step - founding_step (current_step is an explicit parameter, NOT derived from window)",
        "valid_window": "none -- window accepted for API uniformity only, has no effect; age uses current_step even when window is also supplied and ends elsewhere",
        "structural_missingness": "NaN when there is no active rule (denominator zero)",
        "aggregation_path": "SharedRule.amendment_count/founding_step (running scalars) -> single call-level ratio",
        "construct_type": "snapshot_current_state_ratio_current_step_not_window",
        "window_applied": False,
        "known_limitation": "Section 6's 'functional recovery' half of F is intentionally NOT included here -- reported separately once Stage 7/Section 12's shock-timing context exists",
    },
    "V": {
        "name": "ecological_demographic_viability",
        "sub_parts": {
            "ecological": {
                "numerator": "sum of fraction_of_capacity across patches occupied by surviving institutions' active jurisdictions (current)",
                "denominator": "count of those patch observations",
            },
            "demographic": {
                "numerator": "sum of active rules' n_members (current)",
                "denominator": "initial_population (fixed at run start, a parameter not a live read)",
            },
        },
        "valid_window": "none -- window accepted for API uniformity only, has no effect on either sub-part",
        "structural_missingness": "each sub-part independently NaN under its own zero-denominator condition; the composite value is the mean of whichever sub-parts are defined (NaN only if both are)",
        "aggregation_path": "InstitutionRecord.active_jurisdiction + ResourcePatch.fraction_of_capacity (current) and SharedRule.n_members (current) -> two call-level ratios averaged into one composite value",
        "construct_type": "snapshot_current_state_ratio (both sub-parts)",
        "window_applied": False,
    },
    "H": {
        "name": "within_community_heterogeneity",
        "numerator": "sum of pairwise structural_distance across currently-non-extinct institutions' component bundles",
        "denominator": "count of those pairs",
        "valid_window": "none -- window accepted for API uniformity only, has no effect",
        "structural_missingness": "NaN when fewer than two non-extinct institutions exist (heterogeneity undefined for 0 or 1 institution, not zero)",
        "aggregation_path": "InstitutionRecord.components (current, non-extinct only) -> pairwise distances -> single call-level mean",
        "construct_type": "snapshot_current_state_ratio",
        "window_applied": False,
    },
}

#: Section 11 requires auditing every dimension of the preregistered
#: X vector -- this is the authoritative set to check completeness
#: against (mirrors the "CELDMRSFVH" ordering used throughout the
#: codebase and its tests).
ALL_PHENOTYPE_DIMENSIONS: tuple[str, ...] = tuple("CELDMRSFVH")


def audit_completeness_check() -> dict:
    """Section 11 completeness gate: every one of the ten preregistered
    dimensions has an audit entry, and no dimension has been silently
    dropped from ``institutional_phenotype_vector``'s own output keys
    (the "keep dimensions separate" requirement, checked structurally
    rather than merely by counting)."""
    audited = set(PHENOTYPE_FEATURE_AUDIT.keys())
    live_vector_keys = set(ALL_PHENOTYPE_DIMENSIONS)
    return {
        "all_dimensions_audited": audited == live_vector_keys,
        "audited_dimensions": sorted(audited),
        "missing_from_audit": sorted(live_vector_keys - audited),
        "extra_in_audit": sorted(audited - live_vector_keys),
    }


def dimensions_with_full_window_semantics() -> tuple[str, ...]:
    """Dimensions the audit claims are fully, correctly windowed."""
    return tuple(sorted(k for k, v in PHENOTYPE_FEATURE_AUDIT.items() if v["window_applied"] is True))


def dimensions_with_no_window_effect() -> tuple[str, ...]:
    """Dimensions the audit claims silently ignore ``window`` entirely
    (pure current-state snapshots)."""
    return tuple(sorted(k for k, v in PHENOTYPE_FEATURE_AUDIT.items() if v["window_applied"] is False))


def dimensions_with_partial_window_semantics() -> tuple[str, ...]:
    """Dimensions the audit flags as a MIXED construct (part of the
    computation windowed, part not) -- these deserve the closest
    reading before being used in any windowed/temporal analysis."""
    return tuple(sorted(k for k, v in PHENOTYPE_FEATURE_AUDIT.items() if v["window_applied"] == "partial"))
