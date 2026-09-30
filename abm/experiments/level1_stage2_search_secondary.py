#!/usr/bin/env python3
"""Level 1.0, Stage 2 (secondary): a reduced-scale spot-check of the same
institutional search space (``level1_stage2_search.py``) at the two
*secondary* Level 0.3b registered candidates, ``nonstationary`` and
``near_collapse``. 8 points x 3 seeds each (vs. the primary candidate's
32 x 5) -- a documented reduction from the milestone's literal "≥32
points" instruction, made because both candidates are already the
milestone's own "secondary" confirmation targets and because of this
session's compute-time budget (see ``docs/level1.0_scientific_note.md``).
"""

from __future__ import annotations

from experiments.level1_stage2_search import run

if __name__ == "__main__":
    import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from _archive_guard import refuse_archive_overwrite; refuse_archive_overwrite()  # archive protection (publication copy)
    for candidate in ("nonstationary", "near_collapse"):
        run(candidate_key=candidate, n_points=8, n_seeds=3, n_steps=600, search_seed=20260817, tag="_secondary")
