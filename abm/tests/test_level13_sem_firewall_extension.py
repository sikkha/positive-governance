"""Level 1.3, Section 2: SEM firewall + structural-terminology guard
extension audit.

Section 2's forbidden-vocabulary list is broader than any earlier
milestone's: named countries (the dissertation's own empirical
analogues for its three trajectories), the trajectory names themselves,
"State Capacity"/"Institutional Constraint" as named constructs, and
"the preferred number three." ``tests/test_level12_structural_guards.py``'s
whole-package ``pkgutil.walk_packages`` scan over ``src/abm_governance``
already covers every module added this milestone automatically (no
per-file update needed here) -- this file only extends the forbidden-
term list itself and re-runs the same scan against it, plus adds a
Level-1.3-specific "attractor" runtime-guard check (Section 2: "Do not
use 'attractor' unless strict dynamical evidence is demonstrated" --
the same naming-vs-logic distinction ``test_level12b_sem_firewall_
extension.py`` already established for Level 1.2b, restated here since
Level 1.3 introduces its own new observer-side classification code)."""

from __future__ import annotations

import importlib
import inspect
import pathlib

from tests.test_level12_structural_guards import (
    ALL_MODULE_NAMES,
    FORBIDDEN_LEVEL12_TERMS,
    _EXCLUDED_FROM_SCAN,
    _strip_docstrings_and_comments,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"

#: Section 2's additional prohibited vocabulary for Level 1.3, not
#: already covered by ``FORBIDDEN_LEVEL12_TERMS``. Country names are
#: the dissertation's own empirical analogues for its three named
#: trajectories (docs/level1.3_theoretical_translation.md §2/§5) --
#: never legitimate as generative code identifiers, config values, or
#: classification labels here. "state_capacity"/"institutional_
#: constraint" are the dissertation's own construct names (as opposed
#: to the bare symbols S/Z, which are too short/common to guard by
#: substring and are in any case only permitted, per Section 12, in
#: the observer-side ``S_obs``/``Z_obs`` measurement layer). "three" is
#: NOT included as a bare substring (it would false-positive on
#: ordinary counting code, e.g. "three_way", loop bounds, or docstrings
#: about "the third pillar" -- Section 20's "no candidate manufactured"
#: convention this project already established for Level 1.2b applies
#: here too: guard by RUNTIME LOGIC -- Section 23's decision-gate
#: function must not special-case k==3 -- not by banning a common
#: English word).
FORBIDDEN_LEVEL13_TERMS = FORBIDDEN_LEVEL12_TERMS + (
    "china",
    "singapore",
    "united_states",
    "india",
    "japan",
    "nordic",
    "germany",
    "authoritarian_efficiency",
    "constrained_liberalism",
    "constrained_liberal",
    "integrated_equilibrium",
    "state_capacity",
    "institutional_constraint",
    "vietnam",
    "denmark",
    "finds_model",
    "positive_governance",
)


def _all_level13_experiment_files() -> list[pathlib.Path]:
    return sorted(EXPERIMENTS_DIR.glob("level13_*.py"))


class TestLevel13StructuralTerminologyGuard:
    def test_every_source_module_free_of_forbidden_terms(self):
        offenders = []
        for module_name in ALL_MODULE_NAMES:
            if module_name in _EXCLUDED_FROM_SCAN:
                # abm_governance.agents.agent legitimately lists
                # "state_capacity"/"institutional_constraint"/etc. as
                # DEFENSIVE data in its own FORBIDDEN_ATTRIBUTE_
                # SUBSTRINGS guard list (already present since Level
                # 1.1, now also covering Level 1.3's vocabulary) — the
                # opposite of target-shaping usage. Same exclusion
                # test_level12_structural_guards.py already applies.
                continue
            module = importlib.import_module(module_name)
            try:
                source = inspect.getsource(module)
            except (OSError, TypeError):
                continue
            cleaned = _strip_docstrings_and_comments(source).lower()
            for term in FORBIDDEN_LEVEL13_TERMS:
                if term in cleaned or term.replace("_", " ") in cleaned:
                    offenders.append((module_name, term))
        assert offenders == [], f"forbidden Section-2 terms found outside docstrings/comments: {offenders}"

    def test_every_level13_experiment_script_free_of_forbidden_terms(self):
        offenders = []
        for path in _all_level13_experiment_files():
            source = path.read_text()
            cleaned = _strip_docstrings_and_comments(source).lower()
            for term in FORBIDDEN_LEVEL13_TERMS:
                if term in cleaned or term.replace("_", " ") in cleaned:
                    offenders.append((path.name, term))
        assert offenders == [], f"forbidden Section-2 terms found outside docstrings/comments: {offenders}"


class TestForbiddenTermListIsGenuinelyExtended:
    def test_level13_list_is_a_strict_superset(self):
        assert set(FORBIDDEN_LEVEL13_TERMS) >= set(FORBIDDEN_LEVEL12_TERMS)
        assert len(FORBIDDEN_LEVEL13_TERMS) > len(FORBIDDEN_LEVEL12_TERMS)

    def test_scanner_actually_flags_an_injected_violation(self):
        """Positive control: a config-like snippet containing a
        forbidden country/trajectory name must be caught."""
        # Deliberately NOT in a comment (comments are stripped before
        # scanning, by design -- see _strip_docstrings_and_comments):
        # these are actual code string-literal values, exactly what the
        # scanner is meant to catch.
        poisoned_source = 'GOVERNANCE_TRACK = ["authoritarian_efficiency", "china", "singapore"]'
        cleaned = _strip_docstrings_and_comments(poisoned_source).lower()
        hits = [t for t in FORBIDDEN_LEVEL13_TERMS if t in cleaned]
        assert "authoritarian_efficiency" in hits
        assert "china" in hits
        assert "singapore" in hits


class TestAttractorRemainsANamingNonBanForLevel13:
    """Mirrors ``test_level12b_sem_firewall_extension.py``'s own
    documented rationale: "attractor" is not a forbidden substring,
    because Section 2's prohibition is a runtime-evidence guard (never
    assign the label without demonstrated basin/perturbation/return
    dynamics), not a naming ban. Restated as an explicit test here
    (rather than only inherited) because Level 1.3 introduces its own
    new observer-side conversion/discovery code where this distinction
    matters again (Work Packages F/H)."""

    def test_attractor_is_not_in_the_level13_forbidden_list(self):
        assert "attractor" not in FORBIDDEN_LEVEL13_TERMS
