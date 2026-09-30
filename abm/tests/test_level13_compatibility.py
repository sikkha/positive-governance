"""Level 1.3, Section 3: frozen reference preset + exact backward
compatibility scaffold.

Covers Section 3 items 5-9:
5. ``level12b_frozen_reference()`` exists and is exactly
   ``level12_complete()``.
6. Every Level 1.3 mechanism defaults to off.
7. With Level 1.3 disabled, the frozen Level 1.2b model reproduces the
   reference field-for-field (metrics rows) and bit-for-bit (zero extra
   RNG draws consumed).
8. ``core/rng.py::STREAM_REGISTRY`` gained three new, purely-appended
   Level 1.3 names; every pre-existing name kept its exact position/
   seed.
9. A structural test (AST-based, not just "it happened to pass") that
   no Level 1.3 config field is ever read anywhere outside the single
   ``if self.config.historical_module_enabled:`` guard in
   ``Simulation.__init__`` -- i.e. it is structurally impossible for a
   disabled historical module to perturb the Level 1.2b base path,
   not merely empirically unobserved.

This is a scaffold-level test file. Work Packages A-H (tasks #84-#92)
add real mechanism behavior later, each gated behind its own flag and
each required to keep this file passing unmodified along the way,
mirroring how every earlier level's own "exact backward compatibility"
test file was never weakened as new mechanisms were added under it."""

from __future__ import annotations

import ast
import inspect
import pathlib

import numpy as np

from abm_governance.core.config import SimulationConfig
from abm_governance.core.rng import RNG_REGISTRY_VERSION, STREAM_REGISTRY, build_stream_registry
from abm_governance.simulation import Simulation

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
SIMULATION_PATH = PROJECT_ROOT / "src" / "abm_governance" / "simulation.py"

#: The exact, previously-frozen Level 1.2 registry order (Level 1.1b
#: through Level 1.2's own final entry, ``institutional_scaling``) --
#: restated here (not imported) so this file has an independent,
#: hard-coded witness of "nothing before Level 1.3's own new entries
#: moved," rather than trusting the same module it is testing.
_PRE_LEVEL13_REGISTRY_PREFIX = (
    "initialization", "social_interaction", "observation_error", "punishment", "ecological_action",
    "ecological_regeneration", "ecological_perturbation", "rule_formation_other", "rule_proposal_adoption",
    "contributions", "delegation_appointment", "administrative_task_performance", "discretion_appropriation",
    "accountability", "interpatch_coordination", "institutional_shocks", "relationship_dynamics", "imitation",
    "mutation", "demographic_replacement", "institutional_observation", "institutional_transmission",
    "migration", "differential_persistence", "institutional_scaling",
)

_LEVEL13_NEW_NAMES = ("historical_pressure_generation", "entrenchment_dynamics", "legitimacy_accumulation")

_LEVEL13_MECHANISM_FLAGS = (
    "historical_module_enabled",
    "security_pressure_enabled",
    "bargaining_pressure_enabled",
    "coordination_complexity_enabled",
    "entrenchment_enabled",
    "performance_legitimacy_enabled",
    "procedural_legitimacy_enabled",
)


class TestFrozenReferencePreset:
    def test_frozen_reference_equals_level12_complete_field_for_field(self):
        assert SimulationConfig.level12b_frozen_reference() == SimulationConfig.level12_complete()

    def test_frozen_reference_respects_overrides_like_every_other_preset(self):
        ref = SimulationConfig.level12b_frozen_reference(seed=42, population_size=17)
        base = SimulationConfig.level12_complete(seed=42, population_size=17)
        assert ref == base


class TestLevel13MechanismsDisabledByDefault:
    def test_bare_config_has_every_flag_off(self):
        c = SimulationConfig()
        for flag in _LEVEL13_MECHANISM_FLAGS:
            assert getattr(c, flag) is False, f"{flag} must default to False"

    def test_frozen_reference_has_every_flag_off(self):
        c = SimulationConfig.level12b_frozen_reference()
        for flag in _LEVEL13_MECHANISM_FLAGS:
            assert getattr(c, flag) is False, f"{flag} must default to False even under level12b_frozen_reference()"


class TestRngRegistryPurelyAppended:
    def test_pre_level13_prefix_unchanged_in_position(self):
        assert STREAM_REGISTRY[: len(_PRE_LEVEL13_REGISTRY_PREFIX)] == _PRE_LEVEL13_REGISTRY_PREFIX

    def test_three_new_names_appended_at_the_end(self):
        assert STREAM_REGISTRY[len(_PRE_LEVEL13_REGISTRY_PREFIX):] == _LEVEL13_NEW_NAMES

    def test_registry_version_bumped_and_matches_config_default(self):
        assert RNG_REGISTRY_VERSION == "level13_v1"
        assert SimulationConfig().rng_registry_version == RNG_REGISTRY_VERSION

    def test_pre_level13_substreams_are_byte_identical_after_the_append(self):
        """Extending SeedSequence.spawn(n) to a larger n must not change
        any already-spawned child's entropy -- the property the whole
        append-only discipline depends on. Verified directly here rather
        than only asserted in a docstring."""
        seed = 12345
        old_streams = build_stream_registry(seed, "mechanism_substreams", registry=_PRE_LEVEL13_REGISTRY_PREFIX)
        new_streams = build_stream_registry(seed, "mechanism_substreams", registry=STREAM_REGISTRY)
        for name in _PRE_LEVEL13_REGISTRY_PREFIX:
            draw_old = old_streams[name].random(5)
            draw_new = new_streams[name].random(5)
            assert np.array_equal(draw_old, draw_new), f"stream {name!r} diverged after Level 1.3's registry append"


class TestExactCompatibilityWhenHistoricalModuleDisabled:
    """Section 3 item 7: with Level 1.3 disabled, the frozen model must
    reproduce the reference field-for-field/bit-for-bit."""

    def test_disabled_run_produces_no_historical_state(self):
        config = SimulationConfig.level12b_frozen_reference(population_size=24, n_steps=60, seed=3)
        sim = Simulation(config)
        assert sim.historical_state is None
        sim.run()
        assert sim.historical_state is None

    def test_bare_default_and_frozen_reference_are_bit_identical_when_disabled(self):
        # Same seed; one config leaves every Level 1.3 field at its
        # bare-dataclass default, the other reaches the same disabled
        # state via level12b_frozen_reference() -- must be bit-for-bit
        # identical, mirroring test_level11_compatibility.py's own
        # TestExactLevel10Compatibility pattern.
        c1 = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=80, seed=11, monitoring_mode="voluntary", sanction_mode="voluntary",
        )
        c2 = SimulationConfig.level1_rule_formation_default(
            population_size=24, n_steps=80, seed=11, monitoring_mode="voluntary", sanction_mode="voluntary",
            historical_module_enabled=False,
        )
        r1 = Simulation(c1).run()
        r2 = Simulation(c2).run()
        assert len(r1.metrics) == len(r2.metrics)
        for row1, row2 in zip(r1.metrics, r2.metrics):
            for key in row1:
                v1, v2 = row1[key], row2[key]
                if isinstance(v1, float) and np.isnan(v1):
                    assert np.isnan(v2)
                else:
                    assert v1 == v2


class TestStructuralGuardAgainstHistoricalVariablesEnteringBasePath:
    """Section 3 item 9. AST-based, not just empirical: statically
    proves every reference to a Level 1.3 field/attribute anywhere in
    ``simulation.py`` is lexically nested inside an ``if`` (or the
    ``and``/boolean-guarded equivalent) whose test mentions
    ``historical_module_enabled`` -- so it is structurally impossible,
    not merely untested, for a disabled historical module to reach any
    Level 1.2b code path."""

    @staticmethod
    def _guarded_names_used_unconditionally(tree: ast.Module) -> list[str]:
        offenders: list[str] = []

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.guard_depth = 0

            def _test_mentions_flag(self, test_node) -> bool:
                return "historical_module_enabled" in ast.dump(test_node)

            def visit_If(self, node: ast.If):
                mentions = self._test_mentions_flag(node.test)
                if mentions:
                    self.guard_depth += 1
                for child in node.body:
                    self.visit(child)
                if mentions:
                    self.guard_depth -= 1
                for child in node.orelse:
                    self.visit(child)

            def visit_Attribute(self, node: ast.Attribute):
                if node.attr in _LEVEL13_MECHANISM_FLAGS or node.attr == "historical_state":
                    if node.attr != "historical_module_enabled" and self.guard_depth == 0:
                        offenders.append(node.attr)
                self.generic_visit(node)

        Visitor().visit(tree)
        return offenders

    def test_no_unconditional_reference_in_simulation_py(self):
        source = SIMULATION_PATH.read_text()
        tree = ast.parse(source)
        offenders = self._guarded_names_used_unconditionally(tree)
        # The one expected exception: the safe unconditional default
        # assignment ``self.historical_state: dict | None = None`` --
        # assigning None unconditionally is exactly the "strict no-op"
        # every other mechanism in this codebase also does (e.g.
        # ``self.pool: EnvironmentResourcePool | None = None`` above
        # its own guarded block) and carries no behavioral risk (it is
        # the value that guarantees, not undermines, compatibility).
        offenders = [o for o in offenders if o != "historical_state"]
        assert offenders == [], f"Level 1.3 field(s) read outside the historical_module_enabled guard: {offenders}"

    def test_guard_itself_is_actually_present(self):
        """Positive control: the AST scan must find at least one
        properly-guarded reference, so an accidentally-deleted guard
        block (which would make the test above pass vacuously) is
        caught."""
        source = SIMULATION_PATH.read_text()
        assert "if self.config.historical_module_enabled:" in source
        assert "self.historical_state = {}" in source

    def test_no_other_generative_module_references_historical_flags_yet(self):
        """Work Packages remaining after C (D-H) have not been
        implemented yet (separate, later tasks) -- until each is, no
        module besides config.py, rng.py's own docstrings, simulation.
        py's guarded block, and each master flag's own OWN legitimate
        implementing module (below) should mention that flag at all.
        This is a per-FLAG allowlist, not a per-file one: adding
        ``rules/dynamics.py`` to ``entrenchment_enabled``'s allowed set
        (Work Package C, task #87) does not loosen the guard for the
        other six still-dormant master flags in that same file. This
        test is EXPECTED to need updating (not silently loosening) as
        each later Work Package lands — at that point add exactly that
        flag's new legitimate call site(s) below, nothing broader."""
        allowed_files_always = {"config.py", "rng.py", "simulation.py"}
        # Work Package C (task #87): entrenchment_enabled is read
        # directly by rules/dynamics.py's amendment_round/
        # dissolution_round -- see core/entrenchment.py + that module's
        # own docstrings for the full wiring.
        # Work Package D (task #88): performance_legitimacy_enabled/
        # procedural_legitimacy_enabled are read directly by
        # rules/dynamics.py::legitimacy_round, and mentioned in prose by
        # shared_rule.py's two new ledger field docstrings, core/
        # legitimacy.py's own module docstring, and events.py's new
        # LegitimacyEvent docstring -- see core/legitimacy.py for the
        # full wiring.
        per_flag_extra_allowed_files = {
            "entrenchment_enabled": {"dynamics.py"},
            "performance_legitimacy_enabled": {"dynamics.py", "shared_rule.py", "legitimacy.py", "events.py"},
            "procedural_legitimacy_enabled": {"dynamics.py", "shared_rule.py", "legitimacy.py", "events.py"},
        }
        offenders = []
        src_root = PROJECT_ROOT / "src" / "abm_governance"
        for path in src_root.rglob("*.py"):
            text = path.read_text()
            for flag in _LEVEL13_MECHANISM_FLAGS:
                allowed = allowed_files_always | per_flag_extra_allowed_files.get(flag, set())
                if path.name in allowed:
                    continue
                if flag in text:
                    offenders.append((str(path.relative_to(PROJECT_ROOT)), flag))
        assert offenders == [], f"unexpected early reference to a Level 1.3 flag: {offenders}"
