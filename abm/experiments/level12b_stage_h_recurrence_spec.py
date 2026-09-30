#!/usr/bin/env python3
"""Level 1.2b, Work Package H (Section 13): builds, versions, saves,
and hashes the frozen Level 1.2b recurrence spec -- BEFORE Section 15's
discovery pipeline runs, exactly like Work Packages D/E/G each already
freeze+hash their own design/definitions before consuming or generating
data.

The spec assembles, from ``observer/recurrence_criteria_audit.py`` (the
audit artifact, not hand-duplicated here): the twelve criteria's names,
their per-criterion audit findings (construct/unit of
analysis/sample size/redundancy/feasibility), their default thresholds
(read live from ``recurrence_criteria.py``'s own function signatures via
``inspect.signature``, never hand-copied, so the spec cannot silently
drift out of sync with the code that actually enforces it), and the
four-level similarity taxonomy (Section 13's within-run-lineage /
cross-run-structural-similarity / independent-convergence /
component-homology-vs-analogy distinction)."""

from __future__ import annotations

import hashlib
import json
import os

from abm_governance.observer import recurrence_criteria as rc
from abm_governance.observer import recurrence_criteria_audit as rca

OUT_DIR = "outputs/level12b_stage_h_recurrence_spec"

#: Section 13: "create VERSIONED Level 1.2b recurrence spec". Bumped
#: whenever this spec's content changes; the spec's own hash (below)
#: is the mechanical integrity check, this version string is the
#: human-readable one.
RECURRENCE_SPEC_VERSION = "level1.2b-recurrence-spec-v1"


def build_recurrence_spec() -> dict:
    completeness = rca.audit_completeness_check()
    if not completeness["all_criteria_audited"]:
        raise ValueError(f"recurrence criteria audit is incomplete: {completeness}")
    return {
        "version": RECURRENCE_SPEC_VERSION,
        "source_criteria_names": list(rc.RECURRENCE_CRITERIA_NAMES),
        "criteria_audit": rca.RECURRENCE_CRITERIA_AUDIT,
        "default_thresholds": rca.extract_default_thresholds(),
        "similarity_level_taxonomy": rca.SIMILARITY_LEVEL_TAXONOMY,
        "audit_completeness": completeness,
    }


def recurrence_spec_hash(spec: dict) -> str:
    payload = json.dumps(spec, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def save_and_hash(spec: dict | None = None) -> dict:
    spec = spec if spec is not None else build_recurrence_spec()
    os.makedirs(OUT_DIR, exist_ok=True)
    spec_hash = recurrence_spec_hash(spec)
    with open(f"{OUT_DIR}/recurrence_spec.json", "w") as f:
        json.dump(spec, f, indent=2, sort_keys=True)
    with open(f"{OUT_DIR}/recurrence_spec_hash.txt", "w") as f:
        f.write(spec_hash)
    return {"spec": spec, "hash": spec_hash}


def load_and_verify_recurrence_spec(out_dir: str = OUT_DIR) -> dict:
    """Section 13's own "before discovery" gate: Section 15's discovery
    pipeline (or any consumer) should call this rather than
    ``build_recurrence_spec`` directly, so a spec silently edited on
    disk after freezing is caught rather than trusted."""
    with open(f"{out_dir}/recurrence_spec.json") as f:
        spec = json.load(f)
    with open(f"{out_dir}/recurrence_spec_hash.txt") as f:
        stored_hash = f.read().strip()
    recomputed = recurrence_spec_hash(spec)
    if recomputed != stored_hash:
        raise ValueError(
            f"Level 1.2b recurrence spec at {out_dir}/recurrence_spec.json has been altered "
            f"since it was frozen (stored hash {stored_hash}, recomputed hash {recomputed})."
        )
    return {"spec": spec, "hash": recomputed}


def main() -> None:
    result = save_and_hash()
    print(f"Level 1.2b recurrence spec version {result['spec']['version']} saved to {OUT_DIR}/recurrence_spec.json")
    print(f"hash: {result['hash']}")


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    main()
