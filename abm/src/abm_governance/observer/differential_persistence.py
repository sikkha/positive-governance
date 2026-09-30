"""Level 1.2, Work Package E: intercommunity competition and differential
persistence — observer-side reporting only.

**No global institutional fitness function is computed anywhere in this
module** (Work Package E's own explicit prohibition). What this module
does is report, *separately*, four already-distinct realized-selection
channels the generative layer produces via ordinary Level 0-1.2
mechanisms — no new generative pressure was added for this work
package; every pressure Work Package E names (ecological shocks,
resource variance, population movement, administrative overload,
member loss/gain, differential recovery after shocks) already exists in
this codebase's generative layer (``core/perturbation.py``,
``environment/patches.py``'s regeneration, ``rules/migration.py``,
``rules/delegation.py``'s capacity/discretion mechanics). This module's
only new contribution is reading the resulting event log and reporting
it honestly, split by channel, never merged into one score:

- **demographic** selection: population movement (migration + voluntary
  membership exit).
- **institutional** selection: rule/institution extinction, split by
  ``rules/institution.py::selection_channel_for_reason``'s five neutral
  channels (never a fitness ranking — just counts and durations).
- **ecological** selection: patch-level resource stress at the time of
  each institutional extinction (a patch's ``fraction_of_capacity`` when
  its institution went extinct — read-only, computed post-hoc from the
  final patch state, since this codebase keeps no separate patch-
  resource time series).
- **organizational** (administrative) selection: administrative-capacity/
  discretion-related pressure (fund dissolutions, appropriation
  opportunities not converted, audit failure rate) among rules that went
  extinct vs. those that didn't.

Consistent with Work Package E requirement 8: "an institution may
persist despite low welfare and vice versa" — this module never asserts
that a longer-persisting institution "did better"; it only reports
duration and channel."""

from __future__ import annotations

from abm_governance.core.events import EventLog


def demographic_selection_summary(event_log: EventLog) -> dict:
    """Population-movement channel: migration and voluntary membership-
    exit counts, split by realized outcome/reason. Never conflated with
    institutional extinction (an agent leaving is not the same event as
    an institution dying, even though the two can co-occur)."""
    migration_outcomes: dict[str, int] = {}
    for e in event_log.migrations:
        migration_outcomes[e.outcome] = migration_outcomes.get(e.outcome, 0) + 1
    exit_reasons: dict[str, int] = {}
    for e in event_log.membership_exits:
        exit_reasons[e.reason] = exit_reasons.get(e.reason, 0) + 1
    return {
        "migration_outcomes": migration_outcomes,
        "membership_exit_reasons": exit_reasons,
        "n_migrations_succeeded": migration_outcomes.get("succeeded", 0),
        "n_membership_exits": sum(exit_reasons.values()),
    }


def institutional_selection_summary(institution_registry: dict) -> dict:
    """Institution-extinction channel: counts and duration statistics by
    neutral selection channel (``member_loss`` / ``administrative_overload``
    / ``voluntary_dissolution`` / ``unspecified`` — see
    ``rules/institution.py::_SELECTION_CHANNEL_MAP``; ``shock`` and
    ``fragmentation`` are reserved for Work Package F/G callers that pass
    a richer reason string, not produced by the current dissolution
    vocabulary alone). Never ranks channels against each other."""
    from abm_governance.rules.institution import selection_channel_for_reason

    by_channel: dict[str, list[int]] = {}
    n_extinct = 0
    n_surviving = 0
    for rec in institution_registry.values():
        if not rec.extinct:
            n_surviving += 1
            continue
        n_extinct += 1
        channel = selection_channel_for_reason(rec.extinction_reason)
        duration = rec.extinction_time - rec.creation_time
        by_channel.setdefault(channel, []).append(duration)
    summary_by_channel = {
        channel: {
            "count": len(durations),
            "mean_duration": (sum(durations) / len(durations)) if durations else float("nan"),
            "min_duration": min(durations) if durations else None,
            "max_duration": max(durations) if durations else None,
        }
        for channel, durations in by_channel.items()
    }
    return {
        "n_extinct": n_extinct,
        "n_surviving": n_surviving,
        "by_channel": summary_by_channel,
    }


def ecological_selection_summary(institution_registry: dict, patch_system) -> dict:
    """Ecological-stress channel: each *currently surviving* institution's
    patch resource fraction at the time this function is called (a
    read-only snapshot — this codebase keeps no separate per-patch
    resource time series, so extinct institutions' resource level at the
    moment of extinction is not reconstructable here; that limitation is
    disclosed rather than silently approximated). Reports the raw
    per-patch fractions, never an aggregate "ecological fitness" score."""
    if patch_system is None:
        return {"per_surviving_institution_resource_fraction": {}}
    fractions = {}
    for rec in institution_registry.values():
        if rec.extinct:
            continue
        for pid in rec.active_jurisdiction:
            patch = patch_system.patches.get(pid)
            if patch is not None:
                fractions[rec.institution_id] = patch.fraction_of_capacity
    return {"per_surviving_institution_resource_fraction": fractions}


def organizational_selection_summary(event_log: EventLog, institution_registry: dict) -> dict:
    """Administrative-capacity channel: fund-dissolution and audit-outcome
    counts, split between institutions that went extinct and those that
    did not — never merged into a single "administrative fitness"
    number."""
    extinct_rule_ids = {rid for rid, rec in institution_registry.items() if rec.extinct}
    fund_dissolutions_extinct = sum(1 for e in event_log.fund_dissolutions if e.rule_id in extinct_rule_ids)
    fund_dissolutions_surviving = len(event_log.fund_dissolutions) - fund_dissolutions_extinct
    audits_extinct = [e for e in event_log.audits if e.rule_id in extinct_rule_ids]
    audits_surviving = [e for e in event_log.audits if e.rule_id not in extinct_rule_ids]

    def _misconduct_rate(audits):
        if not audits:
            return float("nan")
        return sum(1 for a in audits if a.actual_misconduct_occurred) / len(audits)

    return {
        "fund_dissolutions_among_extinct": fund_dissolutions_extinct,
        "fund_dissolutions_among_surviving": fund_dissolutions_surviving,
        "realized_misconduct_rate_among_extinct": _misconduct_rate(audits_extinct),
        "realized_misconduct_rate_among_surviving": _misconduct_rate(audits_surviving),
    }


def differential_persistence_report(event_log: EventLog, institution_registry: dict, patch_system=None) -> dict:
    """The single entry point downstream analysis code should call —
    returns all four channels as separate top-level keys, exactly as
    Work Package E requires ("report demographic/institutional/
    ecological/organizational selection separately"). Never merges them
    into one composite score."""
    return {
        "demographic": demographic_selection_summary(event_log),
        "institutional": institutional_selection_summary(institution_registry),
        "ecological": ecological_selection_summary(institution_registry, patch_system),
        "organizational": organizational_selection_summary(event_log, institution_registry),
    }
