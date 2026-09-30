"""Level 1.2, Section 14: SEM firewall audit.

Section 14 is absolute: no SEM/dissertation data, labels, or trajectory
counts may be read, imported, or referenced anywhere in Level 1.2's
generative, observer, or experimental code -- Section 2's "GENERATE
FIRST. MEASURE SECOND. DISCOVER THIRD. INTERPRET LATER." depends on it
holding throughout, not just in the modules that happened to get a
dedicated per-file test when they were written.

This module is the milestone-level audit, complementary to (not a
replacement for) the per-file forbidden-terminology tests each new
module/script already carries:

1. Auto-discovers and scans EVERY ``experiments/level12_*.py`` file
   (``pathlib.Path.glob``, not a fixed list -- a new Stage 8+ script
   added later is covered automatically, mirroring
   ``test_level12_structural_guards.py``'s own whole-package
   ``pkgutil.walk_packages`` discipline for ``src/abm_governance``).
2. Confirms no file anywhere under the project root matches a SEM/
   dissertation-data naming pattern (a distinct check from term-
   scanning source code -- this catches an accidentally-committed DATA
   FILE, which source-code scanning cannot).
3. A positive control: confirms the forbidden-term scanner actually
   flags an injected violation, so a silently-broken scanner (e.g. an
   empty file list) cannot pass this audit vacuously."""

from __future__ import annotations

import pathlib

from tests.test_level12_structural_guards import FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

#: Filename patterns that would indicate an accidentally-committed SEM/
#: dissertation data file -- never legitimate anywhere in this
#: repository regardless of extension.
_FORBIDDEN_DATA_FILE_PATTERNS: tuple[str, ...] = (
    "*sem_data*", "*sem_trajector*", "*dissertation_data*", "*sem_score*", "*sem_label*", "*sem_categor*",
)


def _all_level12_experiment_files() -> list[pathlib.Path]:
    # Level 1.2b, Work Package C: extended (Section 3/21's own "extend
    # the guard to every new module" instruction) to also glob
    # ``level12b_*.py`` -- ``level12_*.py`` alone does not match
    # ``level12b_...`` filenames (the character immediately after
    # "level12" differs: "_" vs "b"), so without this the Level 1.2b
    # experiment scripts would silently escape this scan entirely.
    return sorted(set(EXPERIMENTS_DIR.glob("level12_*.py")) | set(EXPERIMENTS_DIR.glob("level12b_*.py")))


class TestSemFirewallAcrossExperimentScripts:
    def test_every_level12_experiment_script_is_covered(self):
        files = _all_level12_experiment_files()
        # a guard against this test silently scanning zero files due to
        # a path regression
        assert len(files) >= 9

    def test_level12b_experiment_scripts_are_included(self):
        files = _all_level12_experiment_files()
        assert any(p.name.startswith("level12b_") for p in files)

    def test_no_experiment_script_contains_forbidden_terms(self):
        offenders = []
        for path in _all_level12_experiment_files():
            source = path.read_text()
            cleaned = _strip_docstrings_and_comments(source).lower()
            for term in FORBIDDEN_LEVEL12_TERMS:
                if term in cleaned or term.replace("_", " ") in cleaned:
                    offenders.append((path.name, term))
        assert offenders == [], f"forbidden Section-3/14 terms found outside docstrings/comments: {offenders}"


class TestNoSemDataFileCommittedAnywhereInRepo:
    def test_no_matching_data_file_exists(self):
        offenders = []
        for pattern in _FORBIDDEN_DATA_FILE_PATTERNS:
            offenders.extend(str(p) for p in PROJECT_ROOT.rglob(pattern))
        assert offenders == [], f"SEM/dissertation-pattern data file(s) found: {offenders}"


class TestScannerPositiveControl:
    def test_scanner_flags_an_injected_violation(self, tmp_path):
        bad_file = tmp_path / "level12_fake_offender.py"
        bad_file.write_text("sem_trajectory = 'this should never appear in real source'\n")
        cleaned = _strip_docstrings_and_comments(bad_file.read_text()).lower()
        found = [term for term in FORBIDDEN_LEVEL12_TERMS if term in cleaned]
        assert "sem_trajectory" in found
