"""Level 1.3b, Stage 0 (task #115): standing regression guard for a
genuine, previously-undisclosed CROSS-PROCESS reproducibility defect
found and fixed this milestone.

**The bug (introduced at Level 1.2, Work Package C; found at Level
1.3b, Stage 0).** ``rules/transmission.py::TRANSMISSIBLE_COMPONENT_
NAMES`` was built by iterating directly over a frozenset UNION of
string component names. Python randomizes ``str`` hashing per process
by default (``PYTHONHASHSEED``), so frozenset iteration order for
string elements varies across separate process launches even though it
is stable *within* one process. ``institution_transmission_round``
calls ``rng.choice(TRANSMISSIBLE_COMPONENT_NAMES)`` -- the RNG-drawn
INDEX is fully deterministic given the seed, but WHICH component name
sat at that index differed by process, silently producing a different
(though internally self-consistent) simulation trajectory from run to
run of the identical seed and config.

**Why nothing ever caught this before.** Every "matched-seed"/"exact
compatibility" check anywhere in this codebase, from Level 1.1b onward,
builds and runs BOTH compared configs within a single script execution
-- sharing one process, and therefore one hash seed, by construction.
The bug was structurally invisible to that pattern. It was found only
when Level 1.3b's own Stage 0 compared a fresh run against results
archived from an EARLIER, separate process for the first time
(``experiments/level13b_stage0_frozen_compatibility.py``, Comparison
B) -- see ``docs/level1.3b_inference_audit.md`` and this milestone's
own Stage 0 report for the full disclosure and empirical evidence (15
separate process launches gave 15 different contribution-event counts
with the bug present; exactly identical counts in all 15 once fixed).

**The fix**: sort the union before converting to a tuple
(``rules/transmission.py``)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from abm_governance.rules import transmission as rt


class TestTransmissibleComponentNamesIsDeterministicallyOrdered:
    def test_is_sorted(self):
        assert list(rt.TRANSMISSIBLE_COMPONENT_NAMES) == sorted(rt.TRANSMISSIBLE_COMPONENT_NAMES)

    def test_still_excludes_the_two_descriptive_only_components(self):
        assert "proposal_threshold" not in rt.TRANSMISSIBLE_COMPONENT_NAMES
        assert "authority_concentration" not in rt.TRANSMISSIBLE_COMPONENT_NAMES

    def test_still_exactly_twelve_components(self):
        assert len(rt.TRANSMISSIBLE_COMPONENT_NAMES) == 12


class TestCrossProcessDeterminism:
    """The real regression guard: launches the simulation in TWO
    genuinely separate Python processes (not just two calls within this
    test process, which would share one hash seed and could not have
    caught the original bug) and requires byte-identical results."""

    _SCRIPT = (
        "from abm_governance.core.config import SimulationConfig\n"
        "from abm_governance.simulation import Simulation\n"
        "cfg = SimulationConfig.level12b_frozen_reference(population_size=20, n_steps=100, n_patches=2, seed=777)\n"
        "sim = Simulation(cfg)\n"
        "sim.run()\n"
        "print(len(sim.event_log.contributions), len(sim.event_log.rule_adoptions), "
        "len(sim.event_log.coordination_links), len(sim.event_log.monitorings))\n"
    )

    def _run_in_fresh_process(self) -> str:
        result = subprocess.run(
            [sys.executable, "-c", self._SCRIPT],
            capture_output=True, text=True, timeout=120, check=True,
            cwd=str(Path(__file__).resolve().parents[1]),  # publication copy: was a hard-coded agent-workspace path
        )
        return result.stdout.strip()

    def test_three_separate_process_launches_agree_exactly(self):
        outputs = {self._run_in_fresh_process() for _ in range(3)}
        assert len(outputs) == 1, f"cross-process nondeterminism detected: {outputs}"
