# Level 1.2b Ecological Accounting Note — Section 5

Full account of Work Package A: the ledger audit that Section 5.7
requires to close ("exactly zero within documented floating-point
tolerance") before any feasibility ratio (Section 6) may be
constructed. See `docs/level1.2b_scientific_note.md` for how this
audit's findings fit into the milestone's overall results.

## 1. What the ledger reconciles

`observer/ecological_ledger.py` (new, observer-only, never imported by
`rules/*.py`/`simulation.py`) reconciles `system_total_resources()`
(the sum of every patch's stock, every agent's `resources`, and every
active rule's `fund`) against a full SUPPLY / DEMAND / NET-ZERO-TRANSFER
taxonomy: opening stock + total supply − total demand = closing stock,
computed for an arbitrary `[opening_step, closing_step)` window from
the event log plus a `PatchSystem` snapshot at each end.

**Supply categories**: patch regeneration, `AppealEvent.refund`,
`RecallEvent.recovered_funds` (both genuine exogenous credits with no
corresponding debit anywhere in the pre-1.2b model — money enters the
system, disclosed rather than treated as a bug to eliminate).

**Demand categories** (the ones Section 5.3 explicitly names, plus
several this audit found were needed for closure and Section 5.3's own
list did not name): ecological extraction, ecological maintenance
investment, subsistence, administrative cost, appropriation,
contribution/fund-dissolution loss, shock loss (patches-topology,
added this milestone — see §3), monitoring cost, sanction cost/penalty,
bilateral costly-punishment cost/penalty, relationship-exit cost,
relationship-formation search cost, audit cost, voluntary
membership-exit cost, per-active-link coordination maintenance fee.

**Net-zero-transfer categories**: interpatch migration (resources move
with the migrating agent, no system-level gain/loss),
`mutual_assistance_transfer` (interfund transfer between coordinating
rules).

## 2. The production-scale residual and its six root causes

Work Package A itself validated the ledger only at short scale
(`population_size=16, n_patches=3, n_steps=40`) and marked the audit
"complete" on that basis. While preparing Work Package E's design at
its actual production scale (`population_size=32, n_patches=4,
n_steps=700`), the same, unmodified `level12_complete` preset showed a
residual of **9.14**, not ~0 — Section 5.7's gate blocked Work Package
E's real run pending investigation. All six root causes shared one
property: **none could manifest at short scale** (too few steps for
negative-resource distress states to occur, too few dissolutions for a
rare code path to fire, too few active coordination links for a
per-step-gated logging bug to accumulate over enough steps to be
visible against the residual tolerance).

1. **Negative-resources sign flip in every capped-deduction site.**
   `min(cost, target.resources)` evaluates to a *negative* "cost" when
   `target.resources` is already negative (a legitimate distress state
   this model has always allowed) — subtracting a negative cost
   *restores* resources from nowhere. Fixed at every site
   (`sanction_round`'s penalty and bystander cost, `monitoring_round`'s
   monitor cost, `membership_round`'s exit cost, `delegation.py`'s
   audit cost) to compute the deduction as `max(0.0, min(cost,
   before))` before subtracting. `AppealEvent` had no `cost_deducted`
   field at all (used the uncapped intended cost unconditionally) —
   fixed by adding the field, mirroring `MonitoringEvent.cost_deducted`.
2. **`MonitoringEvent.cost_deducted` double/triple-counting.** The
   real monitoring cost is deducted once per `(step, patch, rule)`
   round, but the pre-existing `cost_to_monitor` field is stamped onto
   *every* `MonitoringEvent` produced that round (one per violation
   observed) — summing it over-counts a cost paid once. This alone
   moved `level12_complete`'s residual from roughly +181 to roughly
   −0.5 before the other five fixes.
3. **`CoordinationMaintenanceCostEvent` (new).** The per-active-link
   coordination fee is charged every step unconditionally, but was
   previously only logged via `CoordinationActivityEvent.cost`, gated
   behind a separate probability roll — on any step that roll didn't
   fire, the fee was paid but never recorded. Fixed by logging a new
   event unconditionally once per active link per step;
   `demand_coordination_cost` now sums this new event.
4. **Rule-ID/patch-ID key-space conflation in dissolution routing.**
   `Simulation._rule_formation_round` checked a rule ID against a set
   of patch IDs (false unless they numerically coincide) before
   resolving a dissolved rule's fund, and passed the same patch-ID set
   to the delegate-cleanup routine, which matches on `rule_id` —
   silently corrupting institutional state via unrelated ID
   coincidences, independent of its resource-accounting side effect.
   Fixed by computing correctly-typed ID sets for each consumer.
5. **`amendment_round`'s own dissolution path never removed the rule
   from `rule_registry`,** leaving a stale, inactive entry whose
   nonzero `.fund` kept counting toward `system_total_resources()`
   (which sums every registry-live rule regardless of `.active`) — and
   which a later rule founded at the same patch would silently
   overwrite with no disposal event. Fixed by having `amendment_round`
   delete the entry and record it for the existing dissolution-cleanup
   pipeline to pick up.
6. **Zero-recipient `"distributed_to_members"` disposition, exposed
   only once fix 4 made `resolve_dissolution_fund` actually run.** The
   ledger checked only the literal string `disposition == "lost"`, but
   a `"distributed_to_members"` disposition with zero living recipients
   genuinely falls through to lost — the event's own `disposition`
   field correctly keeps its configured label, not silently rewritten.
   Fixed the ledger to also treat that combination as a loss.

After all six fixes, `level12_complete(population_size=32, n_patches=4,
n_steps=700)` reconciles to a residual on the order of **1e-10** for
every seed tried, and both Work Package E initial-condition families
reconcile cleanly at production scale. Across Work Package E's actual
576-run design, the max observed residual is `5.9e-09`, mean `7.1e-10`
— confirming the fix generalizes across the whole design space, not
just the seed/config first used to find it.

## 3. Generative extensions needed for closure (Work Package C)

Two further, additive extensions were needed once Work Package C began
exercising perturbations under `ecology_topology="patches"`:
`resource_depletion`/`regeneration_reduction` shocks were previously
pool-topology-only (silently no-opped under patches) — extended via
`ResourcePatch.apply_shock_loss`, wired through
`apply_instantaneous_effects`/`_ecological_round`'s per-patch regen
call, mirroring the pre-existing pool-topology handling exactly (save/
scale/restore each patch's own `regen_rate`, never permanently
altered). `ecological_ledger.py` gained a `demand_shock_loss` category
(`ResourcePatch.cumulative_shock_loss`) to sum it — this category
summed to 0.0 for every Work Package A test, since that audit predates
patches-topology shock support; verified closing to ~1e-12 residual on
a run with active shocks.

## 4. Methodology: how the six bugs were found

Patch-side accounting was verified independently first
(`cumulative_regeneration + cumulative_maintenance_effective −
cumulative_extraction` vs. the patch's own actual resource delta) —
this reconciled to ~1e-12 at every stage throughout, meaning every bug
found lived in agent/fund-side bookkeeping, never patch-side. Each
per-step round method (`_run_interactions`, `_apply_subsistence`,
`_ecological_round`, `_relationship_dynamics_round`, `_delegation_
round`, …) was then wrapped to diff `system_total_resources()`
before/after against that round's own predicted delta (computed from
the exact same ledger categories, restricted to events added during
that round/step) — narrowing both residuals down to a single round,
then a single step, before the exact cause was identified.

**Methodological lesson carried forward**: Section 5.7's ledger-closure
gate must be re-validated at the actual scale a downstream Work
Package will run at, not just at whatever scale first established
"complete" — a validation suite can be genuinely correct and still be
run at a scale too small to exercise the code paths that matter at
production scale.

## 5. Verification

`tests/test_level12b_ecological_ledger.py` — 27 hand-computed synthetic
scenarios per Section 5.6's required list plus
`TestFullSimulationResidualIsZero`, `TestProductionScaleResidualIsZero`
(the actual scale that caught the six bugs, 5 seeds, `abs=1e-6`),
`TestCappedDeductionNeverGoesNegative`, `TestCoordinationMaintenanceCostEvent`,
`TestFundDissolutionZeroRecipientsTreatedAsLost`,
`TestAmendmentTriggeredDissolutionCleanup`, `TestShockLoss`. All new
event fields default to `0.0`; every pre-existing event-construction
call site (production and test) kept working unchanged — confirmed by
the full pre-existing suite passing with zero regressions at every
step of this fix sequence.
