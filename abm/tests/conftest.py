"""Test-session isolation (added for the public research archive).

Several tests call experiment/figure code that writes to relative paths such as
``outputs/level13b_figures/``. Run from the repository root, those writes would
replace archived evidence files. This conftest therefore runs the whole test
session in a scratch working directory:

* ``<scratch>/outputs`` is a *copy* of the archived ``outputs/`` tree, so tests
  that read archived results see identical bytes;
* ``docs``, ``experiments``, ``src`` and ``tests`` are symlinked (read-only use);
* the repository root and ``experiments/`` are put on ``sys.path`` so that
  ``import experiments.<module>`` keeps working.

No test logic, model code or tolerance is changed. ``tests/test_zz_archive_integrity.py``
verifies at the end of the session that every archived output still matches
``ARCHIVED_OUTPUTS.sha256``. Set ``ABM_TESTS_IN_PLACE=1`` to disable the
isolation (not recommended).
"""
from __future__ import annotations

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = REPO_ROOT / "outputs"

for p in (str(REPO_ROOT), str(REPO_ROOT / "experiments")):
    if p not in sys.path:
        sys.path.insert(0, p)

SCRATCH: Path | None = None
if os.environ.get("ABM_TESTS_IN_PLACE") != "1":
    SCRATCH = Path(tempfile.mkdtemp(prefix="abm_test_workspace_"))
    shutil.copytree(ARCHIVE, SCRATCH / "outputs")
    for name in ("docs", "experiments", "src", "tests", "dev_mem"):
        if (REPO_ROOT / name).exists():
            (SCRATCH / name).symlink_to(REPO_ROOT / name, target_is_directory=True)
    for name in ("pyproject.toml", "README.md", "ARCHIVED_OUTPUTS.sha256"):
        if (REPO_ROOT / name).exists():
            shutil.copy2(REPO_ROOT / name, SCRATCH / name)
    # the scratch copy must not look like the archive root to the experiment guard
    (SCRATCH / "ARCHIVED_OUTPUTS.sha256").rename(SCRATCH / "ARCHIVED_OUTPUTS.sha256.reference")
    os.chdir(SCRATCH)
    atexit.register(shutil.rmtree, SCRATCH, ignore_errors=True)
    os.environ["ABM_TEST_SCRATCH"] = str(SCRATCH)
    os.environ["ABM_REPO_ROOT"] = str(REPO_ROOT)
