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

    # --- locally shared rules (Level 1.0) -----------------------------------
    # A small set of heterogeneous, individually-mutable proposal/
    # membership/enforcement traits (Work Package C) -- every field below
    # is read only when config.rule_formation_enabled is True; at its
    # default False, none of these fields is ever read for a decision (a
    # strict no-op, exactly like ecological_policy's inertness before
    # Level 0.3). None of these is a governance concept: each is a
    # continuous behavioral propensity, not a role, title, or normative
    # judgment.
    #: Per-step probability of proposing a rule at a patch with none
    #: active (Work Package C).
    proposal_probability: float = 0.0
    #: This agent's own preferred rule parameters, used as the content of
    #: any rule it proposes (Work Package B) -- never optimized for future
    #: patch survival, just this agent's own stated preference.
    preferred_extraction_ceiling: float = 0.5
    preferred_maintenance_requirement: float = 0.3
    preferred_monitoring_intensity: float = 0.3
    preferred_sanction_magnitude: float = 0.3
    preferred_adoption_threshold: float = 0.5
    preferred_amendment_threshold: float = 0.5
    #: Propensity to join an active rule this agent is not yet a member
    #: of, and (via the same trait, compared against a rule's actual
    #: content) to support a proposal's adoption.
    willingness_to_join: float = 0.5
    #: Propensity to volunteer as a monitor (voluntary monitoring mode).
    willingness_to_monitor: float = 0.5
    #: Propensity to volunteer as a sanctioning bystander once a violation
    #: is detected (voluntary sanction mode).
    sanction_preference: float = 0.5
    #: How much expected private gain from violating a rule this agent
    #: requires before actually violating (Work Package D compliance
    #: decision) -- higher means more rule-abiding, all else equal.
    violation_tolerance: float = 0.5
    #: Propensity to propose an amendment to a rule this agent is already
    #: a member of.
    amendment_propensity: float = 0.03
    #: Which rule (if any) this agent currently belongs to. ``None`` =
    #: not a member of any rule. This is bookkeeping the rule-formation
    #: round itself maintains; it is never read by
    #: ``decide_ecological_action`` or any other Level 0-0.3b decision
    #: function -- an institution can influence *actual* behavior (via the
    #: compliance-adjustment step in ``_ecological_round``) but never
    #: silently overwrites ``ecological_policy`` itself (Work Package I).
    rule_member_of: int | None = None

    # --- delegation, administrative capacity, accountability (Level 1.1) ---
    # Every field below is read only when config.delegation_enabled is
    # True (and, for the interpatch-coordination fields, only when
    # config.interpatch_coordination_enabled is True) -- exactly like the
    # Level 1.0 block above, each is a continuous behavioral propensity,
    # never a role, title, or governance concept. Defaults are the
    # dataclass's own inert values; the *drawing* of a heterogeneous
    # population only ever happens in build_agents() when the relevant
    # master flag is set (see simulation.py), so every Level-0-1.0-
    # compatible run leaves every field below untouched.
    #: Per-step propensity to nominate a candidate (self or another
    #: member) for delegation when a rule has no active delegate
    #: (Work Package D).
    nomination_probability: float = 0.0
    #: This agent's own perceived competence at administrative tasks, as
    #: judged *by other members* evaluating it as a candidate -- a fixed
    #: trait standing in for "observed reliability" until this agent has
    #: an actual delegate track record (Work Package D candidate
    #: evaluation: "perceived competence").
    perceived_competence: float = 0.5
    #: How much members trust this agent independent of observed
    #: performance (Work Package D: "social trust") -- a separate
    #: dimension from perceived_competence, e.g. a popular but
    #: inexperienced candidate vs. a competent but distrusted one.
    social_trust: float = 0.5
    #: This agent's own baseline task-execution reliability *as a
    #: delegate* -- combined with realized, accumulating capacity (Work
    #: Package E) to determine per-task success probability; never
    #: itself the sole determinant (a trait alone cannot substitute for
    #: "measured through realized performance," Work Package E
    #: requirement 8).
    administrative_reliability: float = 0.6
    #: How readily this agent, once a delegate, appropriates from a
    #: rule's collective fund for private benefit when the opportunity
    #: and private incentive exist (Work Package F) -- 0.0 means never
    #: appropriates regardless of opportunity; misconduct is possible but
    #: never inevitable (Work Package F requirement 1).
    appropriation_propensity: float = 0.1
    #: How readily this agent, once a delegate, reduces effort or
    #: selectively monitors/sanctions rather than executing faithfully
    #: (Work Package F) -- independent of appropriation_propensity, since
    #: effort reduction and appropriation are separable forms of
    #: discretion.
    effort_reduction_propensity: float = 0.1
    #: This agent's own propensity to audit a delegate, appeal a
    #: sanction, or push for recall when it is a rule member (Work
    #: Package G) -- costly, so higher values mean more willing to bear
    #: that cost, not higher accuracy (accuracy is governed by
    #: config.audit_accuracy, an imperfect-information constant shared by
    #: all members, never an individual trait).
    audit_diligence: float = 0.2
    #: Willingness to pay a collective contribution when this rule's
    #: contribution mode calls for a voluntary or negotiated decision
    #: (Work Package H) -- deliberately independent of
    #: violation_tolerance (contribution compliance and ecological-rule
    #: compliance are two separate ledgers, Work Package H requirement
    #: 2).
    contribution_willingness: float = 0.5
    #: This agent's own preferred per-step contribution amount, read only
    #: under ``config.contribution_mode == "negotiated"`` (Work Package
    #: H) -- the negotiated amount is the mean of participating members'
    #: preferences, never a single agent's unilateral choice.
    preferred_contribution_amount: float = 0.1
    #: Propensity for this agent's own rule (if it is a member of one) to
    #: initiate an interpatch coordination proposal, when this agent is
    #: drawn as this step's proposal-initiating member (Work Package I)
    #: -- independent of proposal_probability (initiating a *rule*
    #: proposal) and of nomination_probability (nominating a *delegate*).
    interpatch_proposal_probability: float = 0.0
    #: Propensity to support an incoming interpatch coordination proposal
    #: when this agent's own rule is evaluating one (Work Package I).
    interpatch_acceptance_propensity: float = 0.5

    #: Level 1.2, Work Package D: this agent's own baseline sensitivity to
    #: a favorable stay-vs-move utility gap -- a multiplicative scale on
    #: the migration-decision probability, not a fixed "wants to move"
    #: flag (a utility gap of ~0 still yields a low migration probability
    #: regardless of this trait's value). Deliberately not read anywhere
    #: except ``rules/migration.py``; ``0.0`` (default) makes an agent
    #: structurally immobile even when ``config.migration_enabled`` is
    #: True, matching every other Level 1.1+ mechanism-conditional trait's
    #: "drawn only when its own mechanism is enabled" discipline.
    migration_propensity: float = 0.0

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
