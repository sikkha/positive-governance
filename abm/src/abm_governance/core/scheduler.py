"""Multi-timescale driver.

Different processes in this model are conceptually meant to run at
different rates (see dev_mem/project_vision.md, section 8): individual
action and memory update happen every tick; imitation/mutation and
relationship exit/rewiring happen on their own, slower, independently
configurable periods. This class is the single place that decides "is it
time for period-X to fire this step?", so the rates are explicit and
testable rather than implicit in loop conditionals scattered through
``simulation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scheduler:
    imitation_period: int
    rewiring_period: int

    def __post_init__(self) -> None:
        if self.imitation_period < 1:
            raise ValueError("imitation_period must be >= 1")
        if self.rewiring_period < 1:
            raise ValueError("rewiring_period must be >= 1")

    def should_imitate(self, step: int) -> bool:
        return step > 0 and step % self.imitation_period == 0

    def should_rewire(self, step: int) -> bool:
        return step > 0 and step % self.rewiring_period == 0
