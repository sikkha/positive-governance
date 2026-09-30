# Level 1.3 — Historical Mechanisms (Work Package A pressure transmission)

**Status:** written after Work Packages A-H and the Stage 0-9 experimental
program were built and run. Referenced from `src/abm_governance/core/
historical_transmission.py`'s own module docstring since that module was
first written; this document fills that reference, which had been an
outstanding gap until task #107.

---

## 1. Purpose

Section 6 of the governing specification requires that historical pressure
alter local incentives/opportunity structures, never impose a macro outcome
directly. This document records, per channel, exactly which existing formula
each pressure nudges, why that formula was chosen as the transmission site,
and what was deliberately left unimplemented.

## 2. The shared primitives

Every channel below is a thin, individually-flagged wrapper around one of two
pure functions in `core/historical_transmission.py`:

- `pressure_adjusted_probability(base, level, sensitivity)` = `base +
  sensitivity * level`, clipped to `[0.0, 1.0]` — used for every channel that
  nudges a probability-like quantity.
- `pressure_adjusted_scale(base, level, sensitivity)` = `base * (1 +
  sensitivity * level)`, floored at `0.0` — used for every channel that
  nudges a non-negative rate/weight/frequency quantity.

No channel introduces a bespoke formula. This keeps the transmission logic
auditable in one place even though its effects are felt across three
different rule files.

## 3. Disclosed scope reduction

Section 6 lists six candidate microscopic quantities per pressure (eighteen
total). This milestone implements **two** representative, mechanistically
well-defined channels per pressure (six total), chosen for being cleanly
expressible as a nudge to an existing, already-tested formula without
restructuring the underlying mechanism.

### 3.1 `security_pressure`

| Channel | Site | Formula | Config flags |
|---|---|---|---|
| `returns_to_delegation` | `rules/delegation.py::_success_probability` | nudges the delegate's base task-success probability upward under sustained security pressure (interpretation: pressure raises the perceived stakes/return of getting delegated administration right) | `security_pressure_returns_to_delegation_enabled`, `_sensitivity` (default 0.15) |
| `admin_capacity_demand` | same function, the capacity-bonus weight term | nudges the weight placed on the delegate's own accumulated capacity when computing success probability (interpretation: under pressure, administrative capacity matters more, not less) | `security_pressure_admin_capacity_demand_enabled`, `_sensitivity` (default 0.3) |

Both live in the same function because both channels modify the same
task-success formula without introducing a second success pathway or
bypassing the existing capacity/workload/scale terms.

**Not wired this milestone** (Section 6's fuller candidate list for security
pressure): expected loss from coordination failure, cost of fragmented
response, coordination-task frequency. Each would require either a new
agent-level trait or a new observer-side record this codebase does not yet
have.

### 3.2 `bargaining_pressure`

| Channel | Site | Formula | Config flags |
|---|---|---|---|
| `conditional_contribution` | `rules/contributions.py` (contribution compliance willingness) | nudges an agent's willingness to comply with a collective-contribution rule | `bargaining_pressure_conditional_contribution_enabled`, `_sensitivity` (default 0.2) |
| `appeal_recall` | `rules/contributions.py` (appeal-trigger probability) | nudges the probability an agent appeals/recalls a delegate under bargaining pressure | `bargaining_pressure_appeal_recall_enabled`, `_sensitivity` (default 0.2) |

**Not wired this milestone**: propensity to demand information, cost of
exclusion, demand for procedural participation, conditional rule adoption.

### 3.3 `coordination_complexity`

| Channel | Site | Formula | Config flags |
|---|---|---|---|
| `cross_patch_transactions` | `rules/coordination.py` (coordination link activity probability) | nudges how often cross-patch coordination links are actually used | `coordination_complexity_cross_patch_transactions_enabled`, `_sensitivity` (default 0.3) |
| `interoperable_demand` | `rules/coordination.py` (coordination proposal probability) | nudges how often a new coordination proposal is raised | `coordination_complexity_interoperable_demand_enabled`, `_sensitivity` (default 0.3) |

**Not wired this milestone**: stranger-interaction frequency, need for
predictable general rules, administrative record value, cost of local
incompatibility.

## 4. The two-layer activation requirement (task #109's own finding)

Every channel above requires **two** independent flags to be `True` before it
has any behavioral consequence:

1. The pressure's own master flag (`security_pressure_enabled`, etc.) —
   gates whether the pressure **state series** is generated at all.
2. The channel's own transmission sub-flag (`security_pressure_returns_to_
   delegation_enabled`, etc.) — gates whether that state actually **touches
   agent behavior**.

Both default to `False` independently. A run with the master flag on and
every transmission sub-flag off has a fully-formed, well-defined pressure
series in `historical_state`, and zero behavioral consequence — by design,
this is exactly what Stage 1 (task #96) tests. Task #109 found that Stage 3,
4, and Stage 5's first drafts conflated "master flag on" with "channel
active," leaving the transmission sub-flags off in generative experiments
that needed them on. See `docs/level1.3_bug_disclosure_and_reproducibility_
note.md` for the full account, root cause, and fix.

`experiments/level13_common.py::transmission_overrides_for_channel(channel)`
is the single, shared helper every Level 1.3 stage script now uses to turn
both of a channel's own transmission sub-flags on together, so this
two-layer requirement cannot be silently missed again in a future script.

## 5. Why these six, not a different six

Each implemented channel modifies a formula this project had already built
and tested in an earlier milestone (Level 1.1's delegation/administration,
contribution, and coordination mechanisms). This was a deliberate criterion,
not a coincidence: reusing an existing, audited formula as the nudge site
means the transmission mechanism itself introduces no new failure surface —
only the nudge, never a new success/failure pathway. The twelve unwired
channels would each require new state this codebase does not track (e.g., an
explicit "cost of exclusion" ledger, a "predictable general rule" demand
signal) and were left as a disclosed scope reduction rather than built
hastily to reach eighteen.
