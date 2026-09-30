"""Level 1.2, Section 3: prohibited target-shaping terminology guard.

Extends Level 1.1's ``FORBIDDEN_LEVEL11_TERMS`` (``tests/
test_level11_compatibility.py``) with the additional vocabulary Section 3
explicitly names, and scans the ENTIRE ``abm_governance`` source tree
(not a fixed module list) so every new Level 1.2 module — added
throughout this milestone's work packages — is covered automatically
without this file needing an update per new file. As in the Level 1.1
guard, docstrings and comments are stripped first: this project's own
module docstrings routinely *explain* what a term is deliberately not
(the spec's own Section 3 allowance: "Observer/scientific docs may
discuss the prohibition methodologically but never use the categories
to classify Level 1.2 outcomes") — the guard that matters is over actual
code (identifiers, string literals used as values), not explanatory
prose."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import re

import abm_governance

#: Level 1.1's own list (restated here rather than imported, so this
#: file has no import-order dependency on the test module namespace).
FORBIDDEN_LEVEL11_TERMS = (
    "authoritarian",
    "liberal",
    "democratic",
    "integrated_equilibrium",
    "constrained_liberalism",
    "authoritarian_efficiency",
    "governance_type",
    "governance_species",
    "primordial_form",
    "recurrent_institutional_phenotype",
    "positive_governance",
    "fukuyama",
    "sem_trajectory",
)

#: Section 3's additional prohibited vocabulary, not already covered
#: above.
FORBIDDEN_LEVEL12_TERMS = FORBIDDEN_LEVEL11_TERMS + (
    "governance_trajectory",
    "governance_trajectories",
    "sem_category",
    "sem_score",
    "sem_label",
    "preferred_governance",
    "three_governance",
    "expected_trajectory",
)


def _strip_docstrings_and_comments(source: str) -> str:
    no_triple = re.sub(r'"""[\s\S]*?"""', "", source)
    no_triple = re.sub(r"'''[\s\S]*?'''", "", no_triple)
    no_comments = re.sub(r"#.*", "", no_triple)
    return no_comments


def _iter_module_names(package):
    yield package.__name__
    if not hasattr(package, "__path__"):
        return
    for _finder, name, _ispkg in pkgutil.walk_packages(package.__path__, prefix=package.__name__ + "."):
        yield name


ALL_MODULE_NAMES = sorted(set(_iter_module_names(abm_governance)))

#: Modules excluded from the scan because they themselves *define* a
#: guard list of banned substrings (the terms appear as literal defensive
#: data, not as generative usage) -- ``agents/agent.py``'s own
#: ``FORBIDDEN_ATTRIBUTE_SUBSTRINGS`` legitimately lists "authoritarian"/
#: "governance_type" as strings to reject, which is the opposite of
#: target-shaping. ``tests/test_invariants.py``'s own guard already
#: covers this module directly.
_EXCLUDED_FROM_SCAN = frozenset({"abm_governance.agents.agent"})


class TestLevel12StructuralTerminologyGuard:
    def test_every_source_module_free_of_forbidden_terms(self):
        offenders = []
        for module_name in ALL_MODULE_NAMES:
            if module_name in _EXCLUDED_FROM_SCAN:
                continue
            module = importlib.import_module(module_name)
            try:
                source = inspect.getsource(module)
            except (OSError, TypeError):
                continue
            cleaned = _strip_docstrings_and_comments(source).lower()
            for term in FORBIDDEN_LEVEL12_TERMS:
                if term in cleaned or term.replace("_", " ") in cleaned:
                    offenders.append((module_name, term))
        assert offenders == [], f"forbidden Section-3 terms found outside docstrings/comments: {offenders}"

    def test_at_least_the_expected_module_count_was_scanned(self):
        # A guard against this test silently scanning zero modules due to
        # a package-discovery regression (e.g. a bad __path__).
        assert len(ALL_MODULE_NAMES) > 20
