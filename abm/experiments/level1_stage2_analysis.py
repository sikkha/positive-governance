#!/usr/bin/env python3
"""Level 1.0, Stage 2 analysis: prospective selection of Stage 3's three
confirmatory candidates from the completed Stage 2 exploratory grid.

Selection uses only the observer-side Work Package K label counts
produced during Stage 2 (never re-running or re-classifying with
knowledge of Stage 3/4 results, which do not exist yet at this point) --
one institutional-parameter point is picked per required category:

* a persistent-proto-institution point (most "persistent_proto_institution"
  or "proto_institution" patch-labels summed across its 5 seeds);
* a founder-dependent/short-lived point (most "founder_dependent_
  arrangement" + "short_lived_convention" labels);
* a no-institution/failed-adoption point (most "no_proposal" +
  "proposal_rejected" labels).

If Stage 2 produced zero persistent-proto-institution labels anywhere,
this script does not manufacture one (per the milestone's explicit
instruction) -- it records that fact and Stage 3 proceeds with only the
categories that did appear, confirming the strongest available
contrasting cases.
"""

from __future__ import annotations

import json
from collections import Counter

OUT_PATH = "outputs/level1_stage2_search/stage3_candidate_selection.json"


def _label_counts(records: list[dict]) -> dict[int, Counter]:
    counts: dict[int, Counter] = {}
    for rec in records:
        c = counts.setdefault(rec["point_id"], Counter())
        for cls in rec["classifications"]:
            c[cls["label"]] += 1
    return counts


def select(records: list[dict], candidate_key: str) -> dict:
    counts = _label_counts(records)
    overrides_by_point = {rec["point_id"]: rec["overrides"] for rec in records}

    def best(label_group, exclude=()):
        scored = [
            (pid, sum(c.get(l, 0) for l in label_group))
            for pid, c in counts.items() if pid not in exclude
        ]
        scored.sort(key=lambda x: (-x[1], x[0]))
        if not scored or scored[0][1] == 0:
            return None
        return scored[0][0]

    persistent_pid = best(("persistent_proto_institution", "proto_institution"))
    exclude = {persistent_pid} if persistent_pid is not None else set()
    founder_dep_pid = best(("founder_dependent_arrangement", "short_lived_convention"), exclude=exclude)
    exclude |= {founder_dep_pid} if founder_dep_pid is not None else set()
    no_institution_pid = best(("no_proposal", "proposal_rejected"), exclude=exclude)

    result = {"candidate_key": candidate_key, "selection": {}}
    for name, pid in (
        ("persistent_proto_institution", persistent_pid),
        ("founder_dependent_or_short_lived", founder_dep_pid),
        ("no_institution_or_failed_adoption", no_institution_pid),
    ):
        if pid is None:
            result["selection"][name] = None
        else:
            result["selection"][name] = {"point_id": pid, "overrides": overrides_by_point[pid], "label_counts": dict(counts[pid])}
    return result


def run(search_path: str = "outputs/level1_stage2_search/search_records_interior_persistent.json") -> dict:
    with open(search_path) as f:
        records = json.load(f)
    result = select(records, candidate_key="interior_persistent")
    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    run()
