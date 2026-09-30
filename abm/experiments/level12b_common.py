"""Level 1.2b, Section 24: configuration presets and the shared
result-manifest schema.

Section 24 requires two things: (1) a set of named ``SimulationConfig``
presets for Level 1.2b's own recurring run contexts, every one of them
a **no-op by default** (calling any preset bare, with zero overrides,
must produce a config identical in every field to
``SimulationConfig.level12_complete()`` -- these presets exist purely
as semantically-named entry points for future callers, exactly the
same "no existing experiment script was refactored to use them"
posture Level 1.2's own Section 17 presets took; the eight new
classmethods live on ``SimulationConfig`` itself, see
``core/config.py``); and (2) that every RESULT MANIFEST -- the
per-record or per-experiment provenance dict every Work Package E-R's
own ``run()``/``build_*`` functions already emit in some form --
include twelve specific provenance fields. This module is the shared
place that assembles those twelve fields, so future Work Packages (and
this one's own audit/test coverage) have one canonical function to
call rather than each hand-rolling its own subset.

**The twelve fields, and where each one's value actually comes from**
(five already existed as ``SimulationConfig``/module constants before
this Work Package; three did not exist anywhere and were added this
Work Package as new version tags -- disclosed below, not silently
assumed to already exist):

1. ``root_seed`` -- ``config.seed`` (pre-existing field).
2. ``rng_mode`` -- ``config.rng_mode`` (pre-existing field; Section 15
   mandates ``"mechanism_substreams"`` for every Level 1.2/1.2b causal
   experiment -- every preset in this module inherits that value from
   ``level12_complete``, so "causal presets use rng_mode=mechanism_
   substreams" holds by construction, not by a special case here).
3. ``stream_registry_version`` -- ``config.rng_registry_version``
   (pre-existing field, ``"level12_v1"``).
4. ``code_version`` -- ``abm_governance.__version__`` (pre-existing
   package constant, ``"0.1.0"``). No source-control commit hash is
   available in this environment (no ``.git`` directory) -- disclosed
   rather than fabricated; ``CODE_VERSION`` is package-version-only.
5. ``config_hash`` -- SHA-256 over the full, sorted field set of the
   ``SimulationConfig`` instance actually used for the run (mirrors
   ``experiments/level12b_stage_e_joint_discovery.py::_config_hash``
   exactly, factored out here so every future caller shares one
   implementation instead of redefining it per script).
6. ``feasibility_design_hash`` -- caller-supplied (the frozen Work
   Package C/E ecological/feasibility design's own hash; ``None`` when
   not applicable to a given run, e.g. a run outside the joint-design
   pool -- never fabricated).
7. ``institutional_design_hash`` -- caller-supplied (the frozen Work
   Package D institutional design's own hash; same ``None``-when-not-
   applicable discipline).
8. ``preregistration_hash`` -- caller-supplied (Work Package I's own
   ``preregistration_manifest_hash``, or Work Package L's confirmation-
   registry hash for confirmation-pool runs; ``None`` when neither
   applies, e.g. runs that predate Work Package I, exactly as
   ``level12b_stage_e_joint_discovery.py`` itself already discloses).
9. ``feature_schema_version`` -- ``abm_governance.observer.
   phenotype_feature_audit.FEATURE_SCHEMA_VERSION`` (**new this Work
   Package** -- no version tag existed anywhere for the ten-dimension
   phenotype-vector schema before Section 24 required one).
10. ``recurrence_criteria_version`` -- ``abm_governance.observer.
    recurrence_criteria.RECURRENCE_CRITERIA_VERSION`` (**new this Work
    Package**).
11. ``clustering_pipeline_version`` -- ``abm_governance.observer.
    phenotype_discovery.CLUSTERING_PIPELINE_VERSION`` (**new this Work
    Package**).
12. ``ic_family`` -- caller-supplied (the run's own initial-condition
    family label, e.g. ``"institution_free"`` /
    ``"heterogeneous_proto_institution"``; ``None`` for a run with no
    IC-family concept, e.g. Work Package N's causal ablations, which
    use a single fixed initial condition throughout -- disclosed as
    not-applicable rather than a fabricated default).

**Deliberately not retroactive.** Work Packages E through R's own
already-frozen, already-hashed output files (``design.json``,
``manifest.json``, ``confirmation_registry.json``, and every per-run
``results.json``) are NOT edited to add these fields retroactively --
doing so would silently change a hash-verified artifact's content
after the fact, exactly the failure mode ``load_and_verify_*``
functions across this codebase exist to catch. ``build_result_
manifest`` is forward-looking: available to this Work Package's own
new tests (which construct a manifest against representative already-
saved values to prove the function's correctness) and to any future
experiment script that chooses to call it, not a retroactive rewrite
of Work Packages E-Q's own saved JSON."""

from __future__ import annotations

import hashlib
import json

import abm_governance
from abm_governance.core.config import SimulationConfig
from abm_governance.observer.phenotype_discovery import CLUSTERING_PIPELINE_VERSION
from abm_governance.observer.phenotype_feature_audit import FEATURE_SCHEMA_VERSION
from abm_governance.observer.recurrence_criteria import RECURRENCE_CRITERIA_VERSION

#: Field 4 (see module docstring): package-version-only, no commit hash
#: available in this environment.
CODE_VERSION = abm_governance.__version__

#: The twelve required manifest field names (Section 24), exported so
#: tests/callers can assert completeness without hard-coding the list
#: twice.
RESULT_MANIFEST_FIELDS: tuple[str, ...] = (
    "root_seed", "rng_mode", "stream_registry_version", "code_version",
    "config_hash", "feasibility_design_hash", "institutional_design_hash",
    "preregistration_hash", "feature_schema_version", "recurrence_criteria_version",
    "clustering_pipeline_version", "ic_family",
)


def config_hash(config: SimulationConfig) -> str:
    """SHA-256 over the full, sorted field set of ``config`` -- the
    exact same construction as ``experiments/level12b_stage_e_joint_
    discovery.py::_config_hash``, factored out here as the one shared
    implementation."""
    payload = json.dumps({k: v for k, v in vars(config).items()}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_result_manifest(
    *,
    config: SimulationConfig,
    feasibility_design_hash: str | None = None,
    institutional_design_hash: str | None = None,
    preregistration_hash: str | None = None,
    ic_family: str | None = None,
) -> dict:
    """Assembles all twelve Section 24 provenance fields for one run/
    experiment. The five config-derived and three version-tag fields
    are looked up automatically (never re-typed per caller); the four
    genuinely run-specific fields (the three design/preregistration
    hashes and ``ic_family``) are caller-supplied and default to
    ``None`` -- explicit non-applicability, never a fabricated value."""
    return {
        "root_seed": config.seed,
        "rng_mode": config.rng_mode,
        "stream_registry_version": config.rng_registry_version,
        "code_version": CODE_VERSION,
        "config_hash": config_hash(config),
        "feasibility_design_hash": feasibility_design_hash,
        "institutional_design_hash": institutional_design_hash,
        "preregistration_hash": preregistration_hash,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "recurrence_criteria_version": RECURRENCE_CRITERIA_VERSION,
        "clustering_pipeline_version": CLUSTERING_PIPELINE_VERSION,
        "ic_family": ic_family,
    }
