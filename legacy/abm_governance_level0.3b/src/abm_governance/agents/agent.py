"""Minimal heterogeneous agent state for Level 0.

Only microscopic, agent-local quantities live here: resources, coercive
capability (carried for interface stability into later levels; unused in
Level 0 mechanics), per-partner memory and reputation estimates, and a set
of heterogeneous behavioural parameters. No agent ever holds a field named
after a governance-normative concept — see
:data:`FORBIDDEN_ATTRIBUTE_SUBSTRINGS` and its use in
``tests/test_invariants.py`` for the structural guard against this.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque

from abm_governance.agents.ecological_policy import EcologicalPolicy
from abm_governance.agents.policy import Policy

#: Substrings that must never appear as an Agent attribute name. This list
#: is a structural guard, exercised in tests/test_invariants.py, against
#: accidentally reintroducing governance-normative concepts into the
#: generative layer (see dev_mem/project_vision.md, section 5).
FORBIDDEN_ATTRIBUTE_SUBSTRINGS = (
    "democra",
    "authoritarian",
    "rule_of_law",
    "state_capacity",
    "institutional_constraint",
    "legitimacy",
    "governance_type",
    "good_governance",
)


@dataclass
class Agent:
    agent_id: int

    # --- economic / coercive state ---------------------------------------
    resources: float
    coercive_capability: float  # reserved for Level 2+ (peer/group enforcement)

    # --- behaviour ----------------------------------------------------------
    policy: Policy

    # --- heterogeneous individual parameters -------------------------------
    observation_accuracy: float   # P(observe partner's true action correctly)
    learning_rate: float          # EWMA weight for reputation/payoff updates
    forgiveness: float            # per-tick decay of reputation toward neutral
    risk_sensitivity: float       # reserved: scales punishment/exit thresholds
    exit_cost: float

    memory_length: int = 10

    # --- per-partner memory (populated at runtime, not at construction) ---
    memory: dict[int, Deque[int]] = field(default_factory=dict)
    reputation_estimates: dict[int, float] = field(default_factory=dict)
    partner_payoff_estimate: dict[int, float] = field(default_factory=dict)
    relationship_started_at: dict[int, int] = field(default_factory=dict)

    alive: bool = True

    #: Policy-lineage identifier (Level 0.1, Work Package D — policy-evolution
    #: observability). This tracks descent of *adopted strategies*, not
    #: political identity or personhood: it starts equal to ``agent_id``,
    #: propagates to the peer's lineage id on imitation (a "cultural" copy),
    #: and is assigned a fresh id on mutation (a new variant). It is
    #: observer-relevant bookkeeping, not a governance concept, and carries
    #: no meaning beyond "which policy-adoption event chain does this
    #: agent's current strategy trace back to."
    policy_lineage_id: int | None = None

    #: Demographic identity (Level 0.2, Work Package B). Distinct from
    #: ``agent_id`` (the fixed network-node/population-slot index, which
    #: never changes across a run) and from ``policy_lineage_id`` (which
    #: tracks strategy descent, not personhood). Starts equal to
    #: ``agent_id``; a replacement agent occupying the same slot after a
    #: removal (``viability_mode="removal_replacement"``) gets a *fresh*
    #: demographic_id from a monotonically increasing counter, so "the same
    #: individual continued" and "a new individual now occupies this slot"
    #: are always distinguishable in exported data.
    demographic_id: int | None = None

    #: Viability state machine (Level 0.2, Work Package B). One of "active",
    #: "distressed", "dormant", or "nonviable" (a one-step marker just
    #: before removal in removal_replacement mode). Always "active" and
    #: never transitions when ``config.viability_mode == "none"``.
    viability_state: str = "active"
    #: Consecutive steps this agent's resources have been below
    #: ``config.distress_threshold`` (reset to 0 the instant resources are
    #: at/above threshold). Duration-based, not a one-step trigger.
    consecutive_deficit_steps: int = 0
    #: Cumulative steps this agent has spent dormant so far (this dormancy
    #: episode; reset to 0 on recovery).
    dormant_steps: int = 0
    #: Total number of times this population slot has been through a
    #: removal+replacement (0 for an original initial-population agent that
    #: has never been replaced).
    replacement_count: int = 0

    #: Rolling window of this agent's own recent total resources, one
    #: sample appended per step (Level 0.2, Work Package C — the
    #: "resource_delta" fitness signal). Bounded to ``fitness_window``
    #: samples by the simulation loop, which owns the maxlen (set at
    #: construction time from config, since a dataclass field default can't
    #: see the config).
    resource_window: Deque[float] = field(default_factory=deque)
    #: Rolling window of this agent's own *net game-interaction payoff*
    #: (not resources — excludes subsistence/search/exit/punishment costs;
    #: see simulation.py's per-step accounting), one sample appended per
    #: step (Level 0.2, Work Package C — the "recent_payoff" fitness signal).
    payoff_window: Deque[float] = field(default_factory=deque)

    # --- ecological policy (Level 0.3, Work Package B) -----------------
    #: This agent's independent ecological behavioral dimension — see
    #: agents/ecological_policy.py. ``None`` only until __post_init__
    #: fills in a fully-inert default (all three traits 0.0 — requests no
    #: extraction, invests no maintenance, insensitive to scarcity); every
    #: existing call site that constructs an ``Agent`` without an explicit
    #: ecological policy (i.e. every Level-0/0.1/0.2 test and code path)
    #: is therefore unaffected — this field has zero behavioral
    #: consequence unless ``config.ecology_topology == "patches"``, which
    #: is the only code path that ever reads it.
    ecological_policy: EcologicalPolicy | None = None
    #: Lineage id for the ecological policy specifically — tracks descent
    #: of *ecological* strategy variants, independent of
    #: ``policy_lineage_id`` (which tracks the *social* strategy). Starts
    #: equal to ``agent_id``, exactly like ``policy_lineage_id``.
    ecological_policy_lineage_id: int | None = None
    #: Fixed patch membership (Level 0.3, Work Package A) — ``None`` when
    #: ``ecology_topology != "patches"``. Never migrates; see
    #: environment/patches.py's module docstring.
    patch_id: int | None = None
    #: Unbounded running total of this agent's net ecological ledger
    #: (extraction gain - maintenance cost - ecological search cost),
    #: accumulated every step, never reset — the ecological-stream analog
    #: of "cumulative resources" (Level 0.3, Work Package D: lets
    #: ``fitness_signal(..., stream="ecological")`` use the same four
    #: formulas as the social/"total" stream without conflating the two
    #: ledgers; see agents/fitness.py).
    ecological_cumulative_gain: float = 0.0
    #: Rolling window of this agent's net ecological ledger *per step*
    #: (extraction gain - maintenance cost - ecological search cost this
    #: step only) — the ecological-stream analog of ``payoff_window``.
    ecological_payoff_window: Deque[float] = field(default_factory=deque)
    #: Rolling window of ``ecological_cumulative_gain`` samples — the
    #: ecological-stream analog of ``resource_window`` (used by the
    #: ecological "resource_delta" fitness signal).
    ecological_cumulative_window: Deque[float] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.policy_lineage_id is None:
            self.policy_lineage_id = self.agent_id
        if self.demographic_id is None:
            self.demographic_id = self.agent_id
        if self.ecological_policy is None:
            self.ecological_policy = EcologicalPolicy(0.0, 0.0, 0.0)
        if self.ecological_policy_lineage_id is None:
            self.ecological_policy_lineage_id = self.agent_id
        for name in vars(self):
            lowered = name.lower()
            if any(bad in lowered for bad in FORBIDDEN_ATTRIBUTE_SUBSTRINGS):
                raise ValueError(
                    f"Agent has forbidden attribute name {name!r}; the generative "
                    "layer must not encode governance-normative concepts "
                    "(see dev_mem/project_vision.md, section 5)."
                )

    # -- memory / reputation -------------------------------------------------
    def ensure_partner(self, partner_id: int, step: int) -> None:
        if partner_id not in self.memory:
            self.memory[partner_id] = deque(maxlen=self.memory_length)
            self.reputation_estimates[partner_id] = 0.5  # neutral prior
            self.partner_payoff_estimate[partner_id] = 0.0
            self.relationship_started_at[partner_id] = step

    def record_observation(self, partner_id: int, observed_action: int, payoff: float, step: int) -> None:
        """Update memory, reputation estimate, and payoff estimate for one
        partner after one interaction, using this agent's own
        ``learning_rate`` as the EWMA weight."""
        self.ensure_partner(partner_id, step)
        self.memory[partner_id].append(observed_action)
        lr = self.learning_rate
        prev_rep = self.reputation_estimates[partner_id]
        self.reputation_estimates[partner_id] = (1 - lr) * prev_rep + lr * observed_action
        prev_payoff = self.partner_payoff_estimate[partner_id]
        self.partner_payoff_estimate[partner_id] = (1 - lr) * prev_payoff + lr * payoff

    def decay_reputations(self) -> None:
        """Forgiveness: reputation estimates drift back toward the neutral
        prior (0.5) at rate ``forgiveness`` when not refreshed by a new
        observation. Called on the memory/reputation timescale."""
        f = self.forgiveness
        for partner_id in list(self.reputation_estimates):
            rep = self.reputation_estimates[partner_id]
            self.reputation_estimates[partner_id] = (1 - f) * rep + f * 0.5

    def partner_history(self, partner_id: int) -> list[int]:
        return list(self.memory.get(partner_id, ()))

    def forget_partner(self, partner_id: int) -> None:
        """Drop all record of a partner (used on relationship exit)."""
        self.memory.pop(partner_id, None)
        self.reputation_estimates.pop(partner_id, None)
        self.partner_payoff_estimate.pop(partner_id, None)
        self.relationship_started_at.pop(partner_id, None)

    # -- fitness-signal windows (Level 0.2, Work Package C) -----------------
    def record_step_end(self, net_payoff_this_step: float, window: int) -> None:
        """Called once per step (after all of that step's resource changes)
        to sample this agent's current total ``resources`` and that step's
        net game-interaction payoff into two bounded rolling windows. Pure
        bookkeeping — never used inside any policy/decision function itself;
        only the observer-facing fitness-signal properties below (and the
        imitation round, which reads them as data) consume it."""
        if self.resource_window.maxlen != window:
            # maxlen is fixed at deque-construction time; a plain dataclass
            # default can't see config.fitness_window, so re-home the
            # window (preserving existing samples, most-recent-kept) the
            # first time (or if) the configured window size differs.
            self.resource_window = deque(self.resource_window, maxlen=window)
            self.payoff_window = deque(self.payoff_window, maxlen=window)
        self.resource_window.append(self.resources)
        self.payoff_window.append(net_payoff_this_step)

    @property
    def recent_payoff(self) -> float:
        """Sum of net game-interaction payoff over the rolling window.
        0.0 (not NaN) when the window is empty — an agent with no
        interaction history yet has genuinely earned zero, not an unknown
        quantity, so 0.0 is the correct value rather than a missing one."""
        return float(sum(self.payoff_window))

    @property
    def resource_delta(self) -> float:
        """Change in total resources over the rolling window
        (``current - window[0]``). ``float('nan')`` until the window is
        full — a partial window would understate the true interval and
        silently bias early-run comparisons, so it is reported as
        genuinely unknown instead."""
        if len(self.resource_window) < (self.resource_window.maxlen or 1):
            return float("nan")
        return self.resources - self.resource_window[0]

    # -- ecological fitness-signal windows (Level 0.3, Work Package D) ------
    def record_ecological_step_end(self, net_ecological_payoff_this_step: float, window: int) -> None:
        """Ecological-stream analog of :meth:`record_step_end`: samples
        ``ecological_cumulative_gain`` (already updated by the caller for
        this step, exactly like ``resources`` is by the time
        ``record_step_end`` runs) and this step's net ecological payoff
        into their own rolling windows. A strict no-op (never called) when
        ``config.ecology_topology != "patches"``."""
        if self.ecological_cumulative_window.maxlen != window:
            self.ecological_cumulative_window = deque(self.ecological_cumulative_window, maxlen=window)
            self.ecological_payoff_window = deque(self.ecological_payoff_window, maxlen=window)
        self.ecological_cumulative_window.append(self.ecological_cumulative_gain)
        self.ecological_payoff_window.append(net_ecological_payoff_this_step)

    @property
    def ecological_recent_payoff(self) -> float:
        """Ecological-stream analog of ``recent_payoff``: sum of net
        ecological ledger entries (extraction gain - maintenance cost -
        ecological search cost) over the rolling window. 0.0 when empty,
        for the same reason ``recent_payoff`` is."""
        return float(sum(self.ecological_payoff_window))

    @property
    def ecological_cumulative_delta(self) -> float:
        """Ecological-stream analog of ``resource_delta``: change in
        ``ecological_cumulative_gain`` over the rolling window.
        ``float('nan')`` until the window is full, for the same reason
        ``resource_delta`` is."""
        if len(self.ecological_cumulative_window) < (self.ecological_cumulative_window.maxlen or 1):
            return float("nan")
        return self.ecological_cumulative_gain - self.ecological_cumulative_window[0]
