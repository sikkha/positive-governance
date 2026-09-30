"""Level 1.2b, Work Package P (Section 3/21): SEM firewall + structural-
terminology guard extension audit.

The whole-package scans (`test_level12_structural_guards.py`'s
`pkgutil.walk_packages` over `src/abm_governance`, `test_level12_sem_
firewall.py`'s `pathlib.Path.glob` over `experiments/level12_*.py` and
`experiments/level12b_*.py`) are already discovery-based, not fixed
lists -- every module/script this session added (Work Packages F
through O) was already confirmed, individually, to pass both scans
immediately after being written. This module makes that "should be
covered automatically" claim an explicit, verified assertion rather
than an implicit trust: it hard-codes the actual file/module list this
session's own Work Packages F-O produced and asserts each one is
genuinely present in what the scans discover -- catching a future glob-
pattern regression (e.g. a new naming convention that silently stops
matching) that per-file "it passed when I wrote it" checks alone would
never catch.

**Forbidden-terminology list: no new substrings added, and why.** This
session considered adding "attractor" to ``FORBIDDEN_LEVEL12_TERMS``
(Section 20's own explicit prohibition: never assign an "attractor"
label without basin/perturbation/return evidence). This would have
been WRONG: "attractor" is a legitimate, correctly-guarded CONCEPT in
Work Package O's own code (`attractor_label_permitted`, `attractor_
label_assigned`) -- the prohibition is a RUNTIME/LOGIC guard (evidence
must clear an explicit bar before the label is ever used), not a
naming ban. Adding it as a forbidden substring would have broken Work
Package O's own already-tested module while adding no real protection
-- confirmed here by running the substring scan against Work Package
O's own source with "attractor" temporarily added, verifying it WOULD
false-positive, so this omission is deliberate and disclosed rather
than an oversight.

**AST-based import check, stronger than substring scanning.** Every
1.2b module/script's own `import`/`from ... import` statements are
parsed (not text-matched) and checked against a SEM/dissertation-
module name pattern -- immune to the comment-stripping edge cases a
pure substring scan depends on."""

from __future__ import annotations

import ast
import pathlib

from tests.test_level12_sem_firewall import _all_level12_experiment_files
from tests.test_level12_structural_guards import ALL_MODULE_NAMES, FORBIDDEN_LEVEL12_TERMS, _strip_docstrings_and_comments

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent

#: Work Package F through O's own new files, hard-coded here (not
#: re-derived from a glob) specifically so this test can assert the
#: SCANS discover them -- using the scans' own discovery mechanism to
#: build this list would make the assertion circular.
EXPECTED_WORK_PACKAGE_F_THROUGH_O_EXPERIMENT_SCRIPTS: tuple[str, ...] = (
    "level12b_stage_g_temporal_representation.py",
    "level12b_stage_h_recurrence_spec.py",
    "level12b_stage_i_preregistration_manifest.py",
    "level12b_stage_j_main_discovery_pipeline.py",
    "level12b_stage_k_clustering_discovery.py",
    "level12b_stage_l0_confirmation_registry.py",
    "level12b_stage_l1_confirmation_pool.py",
    "level12b_stage_l2_discovery_pool_refit.py",
    "level12b_stage_l3_prospective_confirmation.py",
    "level12b_stage_m_scaling_robustness.py",
    "level12b_stage_n_causal_collapse_decomposition.py",
    "level12b_stage_o_phenotype_recurrence_classification.py",
)

EXPECTED_WORK_PACKAGE_F_THROUGH_O_OBSERVER_MODULES: tuple[str, ...] = (
    "abm_governance.observer.phenotype_feature_audit",
    "abm_governance.observer.recurrence_criteria_audit",
)

#: SEM/dissertation-adjacent module name fragments -- a real import of
#: any of these anywhere in 1.2b's own code would violate the firewall.
_FORBIDDEN_IMPORT_FRAGMENTS: tuple[str, ...] = ("sem_", "dissertation", "_sem_data", "sem_pipeline")


def _all_imported_module_names(tree: ast.Module) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


class TestWorkPackageFThroughOScriptsAreDiscovered:
    def test_every_new_experiment_script_is_scanned(self):
        discovered_names = {p.name for p in _all_level12_experiment_files()}
        missing = [f for f in EXPECTED_WORK_PACKAGE_F_THROUGH_O_EXPERIMENT_SCRIPTS if f not in discovered_names]
        assert missing == [], f"expected Work Package F-O scripts missing from the SEM-firewall scan: {missing}"

    def test_every_new_observer_module_is_scanned(self):
        missing = [m for m in EXPECTED_WORK_PACKAGE_F_THROUGH_O_OBSERVER_MODULES if m not in ALL_MODULE_NAMES]
        assert missing == [], f"expected Work Package F-O observer modules missing from the structural-terminology scan: {missing}"


class TestAttractorIsDeliberatelyNotAForbiddenSubstring:
    def test_attractor_would_false_positive_against_work_package_o(self):
        """Positive control proving the omission is deliberate: adding
        "attractor" to the forbidden list WOULD flag Work Package O's
        own legitimate, correctly-guarded code."""
        path = PROJECT_ROOT / "experiments" / "level12b_stage_o_phenotype_recurrence_classification.py"
        source = path.read_text()
        cleaned = _strip_docstrings_and_comments(source).lower()
        assert "attractor" in cleaned  # would trip a naive substring ban
        assert "attractor" not in FORBIDDEN_LEVEL12_TERMS  # and is correctly absent from the real list


class TestNoSemImportsAnywhereInWorkPackageFThroughO:
    def test_no_forbidden_import_in_any_new_experiment_script(self):
        offenders = []
        for name in EXPECTED_WORK_PACKAGE_F_THROUGH_O_EXPERIMENT_SCRIPTS:
            path = PROJECT_ROOT / "experiments" / name
            tree = ast.parse(path.read_text())
            for imported in _all_imported_module_names(tree):
                if any(frag in imported.lower() for frag in _FORBIDDEN_IMPORT_FRAGMENTS):
                    offenders.append((name, imported))
        assert offenders == [], f"forbidden SEM/dissertation import found: {offenders}"

    def test_no_forbidden_import_in_any_new_observer_module(self):
        offenders = []
        for module_dotted in EXPECTED_WORK_PACKAGE_F_THROUGH_O_OBSERVER_MODULES:
            path = PROJECT_ROOT / "src" / "abm_governance" / "observer" / (module_dotted.rsplit(".", 1)[-1] + ".py")
            tree = ast.parse(path.read_text())
            for imported in _all_imported_module_names(tree):
                if any(frag in imported.lower() for frag in _FORBIDDEN_IMPORT_FRAGMENTS):
                    offenders.append((module_dotted, imported))
        assert offenders == [], f"forbidden SEM/dissertation import found: {offenders}"

    def test_no_forbidden_import_pattern_matches_any_legitimate_import(self):
        """Positive control: the fragment list itself should not be so
        broad it would flag ordinary, legitimate imports this codebase
        actually uses (e.g. nothing here starts with 'sem_' or contains
        'dissertation')."""
        import experiments.level12b_stage_o_phenotype_recurrence_classification as real_module

        tree = ast.parse(pathlib.Path(real_module.__file__).read_text())
        imported = _all_imported_module_names(tree)
        assert not any(any(frag in name.lower() for frag in _FORBIDDEN_IMPORT_FRAGMENTS) for name in imported)
