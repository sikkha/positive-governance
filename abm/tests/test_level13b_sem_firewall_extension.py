"""Level 1.3b (Section 3): extends the SEM/structural-terminology guard
to this milestone's own `experiments/level13b_*.py` files.

`tests/test_level13_sem_firewall_extension.py`'s own experiment-script
scan globs `level13_*.py` only -- which does NOT match `level13b_*.py`
(the "b" falls before the underscore), so every Level 1.3b experiment
script needs its own explicit coverage, exactly mirroring how Level
1.3's own file extended Level 1.2's. Source-module coverage (`src/
abm_governance/**`) is already automatic and unaffected: `pkgutil.
walk_packages` in `tests/test_level12_structural_guards.py` walks the
whole `abm_governance` package regardless of which milestone a module
was added in, so `observer/sequencing_diagnostics.py`'s Work-Package-B
fix this milestone is already covered by that existing scan (run
against `FORBIDDEN_LEVEL13_TERMS`, which Level 1.3b reuses unmodified --
this milestone's own governing spec introduces no new forbidden
vocabulary beyond what Level 1.3 already forbade)."""

from __future__ import annotations

import pathlib

from tests.test_level12_structural_guards import _strip_docstrings_and_comments
from tests.test_level13_sem_firewall_extension import FORBIDDEN_LEVEL13_TERMS

EXPERIMENTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "experiments"
DOCS_DIR = pathlib.Path(__file__).resolve().parent.parent / "docs"


def _all_level13b_experiment_files() -> list[pathlib.Path]:
    return sorted(EXPERIMENTS_DIR.glob("level13b_*.py"))


class TestLevel13bExperimentScriptTerminologyGuard:
    def test_at_least_one_level13b_script_exists(self):
        # Guards against this test silently scanning zero files if the
        # glob or directory ever moves.
        assert len(_all_level13b_experiment_files()) >= 1

    def test_every_level13b_experiment_script_free_of_forbidden_terms(self):
        offenders = []
        for path in _all_level13b_experiment_files():
            source = path.read_text()
            cleaned = _strip_docstrings_and_comments(source).lower()
            for term in FORBIDDEN_LEVEL13_TERMS:
                if term in cleaned or term.replace("_", " ") in cleaned:
                    offenders.append((path.name, term))
        assert offenders == [], f"forbidden Section-2 terms found outside docstrings/comments: {offenders}"


class TestLevel13bDocsTerminologyGuard:
    """Documentation is prose, not code -- docstrings/comments are not
    stripped here (the whole file IS docstring-shaped), so this checks
    the raw file text directly. Deliberately narrower than the source/
    experiment guards: docs are allowed to discuss what is forbidden
    (as this very file's own docstring does, and as `docs/level1.3b_
    bargaining_activation_audit.md` does not need to), so this test
    only guards the small subset of terms that would be a genuine
    Section 2 violation if they appeared in a Level 1.3b doc's own
    substantive claims -- the highest-risk country/label terms, not the
    full inherited list (which includes generic words like ones already
    legitimately used in this project's own defensive-guard code)."""

    _HIGH_RISK_TERMS = (
        "china", "singapore", "united_states", "india", "japan", "nordic", "germany", "vietnam", "denmark",
    )

    def test_no_level13b_doc_names_a_real_country(self):
        offenders = []
        for path in sorted(DOCS_DIR.glob("level1.3b_*.md")):
            text = path.read_text().lower()
            for term in self._HIGH_RISK_TERMS:
                if term in text or term.replace("_", " ") in text:
                    offenders.append((path.name, term))
        assert offenders == [], f"forbidden country/label terms found in Level 1.3b docs: {offenders}"
