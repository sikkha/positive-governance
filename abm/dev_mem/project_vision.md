# Project Vision — ABM Governance

**Status:** Foundational document. Read this before writing or reviewing any code.
**Companion doc:** `dev_mem/status_update.md` (living log — update every session).

---

## 1. Project Purpose

This project builds a research-grade, transparent, agent-based model (ABM) that
investigates the **bottom-up emergence of macropolitical organization** from
elementary micro-level social interactions: cooperation, exploitation,
reciprocity, punishment, reward, exit, delegation, monitoring, and
agent-environment feedback.

The project sits alongside — but is methodologically independent of — the
dissertation "Positive Governance" (Kan Yuenyong, NIDA, Rev. 10.1, Oct 2025,
`lr/Dissertation Proposal X_1 PDF.pdf`). The dissertation is a *statistical,
top-down, empirical* study (structural equation modeling on World Values
Survey Wave 7 data). This ABM is a *generative, bottom-up, computational*
study. They ask related questions with different tools and must not be
collapsed into one.

## 2. Research Question

> When heterogeneous agents interact through elementary relations —
> cooperation, exploitation, reciprocity, punishment, reward, exit,
> delegation, monitoring, and environmental feedback — what persistent forms
> of macroscopic political organization, if any, emerge?

This is genuinely open-ended. Candidate answers the architecture must be able
to represent and detect, without bias toward any one of them:

- One or several fixed-point attractors
- Cyclical regimes
- Metastable configurations
- Centralization–fragmentation oscillations
- Collapse and reconstruction
- Strong path dependence
- A continuous manifold without discrete types
- Patterns resembling the dissertation's SEM typology (coincidentally, not by construction)
- Anomalies that contradict or extend the SEM typology

**Anomalies are valuable results.** They must never be tuned away, filtered
out, or treated as bugs merely because they disagree with the dissertation.
If the model produces something the dissertation's typology cannot classify,
that is a finding, not an error.

## 3. Relationship to the Dissertation

The dissertation identifies, via SEM on WVS Wave 7 confidence/trust items:

- **State Capacity (S)** — first-order latent factor: confidence in armed
  forces, national government, political parties, parliament (Q65, Q71,
  Q72, Q73).
- **Rule of Law** — first-order latent factor: confidence in police and
  courts (Q69, Q70).
- **Democratic Accountability** — first-order latent factor: perceived
  fairness of vote counting and election officials (Q224, Q229).
- **Institutional Constraint (Z)** — second-order latent factor combining
  Rule of Law (loading 0.795) and Democratic Accountability (loading 0.349).
- The governance-equilibrium equation **G = f(S, Z) + β**, where β is an
  (unoperationalized) external-influence term.

From this the dissertation *externally, empirically* proposes three
governance trajectories, presented as parallel stable equilibria rather than
developmental stages:

1. **Authoritarian Efficiency** — high S, low/moderate Z (e.g. China, Singapore).
2. **Constrained Liberalism** — high Z, moderate/fragmented S (e.g. US, India, Japan).
3. **Integrated Equilibrium** — high S, high Z, mutually reinforcing (e.g. Nordics, Germany).

**These three trajectories are external empirical/theoretical observations
about real countries in survey data. They are not targets, labels, reward
signals, or design specifications for this ABM.** The ABM does not attempt
to prove, reproduce, calibrate to, or optimize toward them. If the model's
emergent macro-patterns are later compared to the SEM typology, that
comparison happens strictly in a downstream, external, *observer-layer*
analysis stage — never inside the generative mechanics, never as a fitness
or selection criterion.

## 4. Open-Ended and Anomaly-Preserving Philosophy

- The simulation is a generator of possibility space, not a proof engine.
- No metric, reward, mutation-selection rule, or calibration step may be
  chosen *because* it pushes outcomes toward Authoritarian Efficiency /
  Constrained Liberalism / Integrated Equilibrium (or toward any other
  preconceived taxonomy, including this project's own prior runs).
- Parameter sweeps must explore, not cherry-pick. A "good" run is not one
  that looks like a clean political system; it is one that is a faithful,
  reproducible consequence of the stated micro-rules.
- Null and negative results (e.g. "no persistent macro-structure formed",
  "the system is chaotic across all tested seeds") are legitimate and
  reportable outcomes.
- Every claim about emergent macro-organization must be traceable to
  specific micro-mechanisms and parameters — no unexplained "emergence,"
  only mechanistically grounded emergence.

## 5. Generative vs. Observer Separation (strict, load-bearing)

This is the most important architectural invariant in the whole codebase and
must be enforced in code review, module boundaries, and naming.

### Generative layer (the simulated world)
May contain only microscopic entities and mechanisms: agents, resources,
relationships/networks, signals/observations, elementary actions, memory,
reputation, learning, imitation, mutation/experimentation, environmental
conditions, agent-environment feedback.

**Forbidden inside the generative layer** — as variable names, class names,
concepts, or fitness/reward terms — anywhere in `src/abm_governance/core/`,
`agents/`, `interactions/`, `environment/`:

- Democracy / Authoritarianism
- Rule of law
- State capacity
- Institutional constraint
- Legitimacy (see the Level 1.3 amendment immediately below — no longer
  an absolute, project-wide ban as of Level 1.3, but a narrowly-scoped
  one)
- Good governance / governance type
- Any encoding of `G = f(S, Z)` (or S, Z themselves) as an agent objective

**Level 1.3 amendment to the "Legitimacy" ban (disclosed, deliberate, narrow
— mirrors the documented exception Level 1.0 itself required to this
project's "do not skip levels" rule, `dev_mem/project_vision.md` §9).**
Level 1.3's own governing specification, Work Package D (Section 9), titled
"DUAL LEGITIMACY CHANNELS," requires two named, config-level, opt-in
generative ledgers (`L_P` performance legitimacy, `L_R` procedural/
reciprocal legitimacy) and a document (Section 22) about them by that name.
As of Level 1.3, "legitimacy" is therefore sanctioned as a `core/config.py`
config-field-name and dedicated-module concept, strictly opt-in (every
related flag defaults to `False`) and never a fitness/reward term — but
the ban is **not lifted for `Agent`**: no `Agent` attribute may ever be
named with "legitimacy" as a substring (still runtime-enforced by
`Agent.__post_init__` via `FORBIDDEN_ATTRIBUTE_SUBSTRINGS`, still asserted
directly by `tests/test_memory.py`). Legitimacy remains an
institution/rule-level ledger — never an agent's own intrinsic trait or
"political identity" (§7 above) — exactly the same generative/observer-style
discipline this project already applies to delegation, discretion, and
accountability: real mechanisms with real names, kept off agents' own
identity fields. See `tests/test_level03_niche_construction.py`'s narrowly-
scoped exception and its own positive control proving the Agent-level ban
is unaffected, and `docs/level1.3_theoretical_translation.md` §4 point F
for the full sourcing/rationale.

Agents never know they are "in" a governance system. They only know their
own resources, relationships, memories, and local payoffs.

### Observer layer (post-hoc / concurrent analysis)
A structurally separate module (`src/abm_governance/observer/`) may compute
aggregate observables from simulation state/event logs: cooperation rate,
defection/exploitation rate, punishment frequency (including erroneous or
antisocial punishment), resource inequality (e.g. Gini), network
centralization, concentration of coercive capability, public-goods
provision, voluntary compliance, relationship duration, coalition
structure, leadership/enforcement concentration, institutional persistence,
population survival, collapse/recovery, behavioral diversity.

**Hard rule:** observer-layer computations are read-only with respect to the
generative layer. They may read logged state/events; they may never write
back into agent state, policies, payoffs, or the RNG stream. Only in later
research stages may an external, offline analysis attempt to map observer
metrics onto SEM-derived S/Z/legitimacy/typology categories — and even then,
that mapping must never feed back into agent rewards or generative dynamics.

## 6. Conceptual Inspiration (grammar, not blueprint)

Axelrod-style repeated interaction and reciprocity; the prisoner's dilemma;
public-goods games; common-pool-resource games; trust/delegation games;
bargaining and fairness games; costly punishment and second-order free
riding; endogenous relationship formation and exit; cultural evolution and
strategy imitation; Daisyworld-style agent–environment feedback; generative
social science / ABM tradition.

**Game theory defines the consequences of elementary interactions — it does
not dictate complete agent strategies or prescribe macroscopic outcomes.**
Payoff matrices tell an agent what happens *this round* given the joint
action; they do not encode what kind of political system should result.

**Daisyworld analogy (central):** individual daisies do not optimize
planetary temperature; their local reproduction changes the environment,
which changes subsequent reproductive fitness. Analogously, agents here do
not optimize for "good governance"; their local actions change the social
environment (reputations, network structure, resource distribution,
enforcement concentration), which changes the payoffs and viability of
subsequent behavior. Macro-order, if it appears, is a side effect of
distributed micro-feedback loops, never a target function.

## 7. Atomic Agent Assumptions

- No universal representative agent. Populations are heterogeneous by
  construction — every numeric trait is drawn from a distribution, not a
  shared constant.
- Candidate minimal agent state: resources/wealth, coercive capability,
  current relationships, memory of past interactions, reputation estimates
  of others, behavioral policy, observation accuracy, learning rate,
  forgiveness/memory-decay rate, risk sensitivity, exit cost.
- Agents act through elementary primitives: give, withhold, take,
  cooperate, refuse, signal, observe, reward, punish, approach, avoid, exit.
- Agents never hold a fixed "political identity." Any label such as
  "authoritarian agent" or "democratic agent" is strictly forbidden in the
  generative layer.
- Initial policies are transparent finite-state controllers or interpretable
  conditional rule sets — never opaque neural networks. The model must
  remain causally inspectable: for any agent, at any tick, it must be
  possible to explain in plain language why it acted as it did.

## 8. Multiple Timescales

The architecture supports (and Level 0 already scaffolds interfaces for)
independently configurable update rates across: individual action, memory/
learning, reputation propagation, relationship formation/dissolution,
strategy imitation, population replacement, persistent relational/
institutional pattern formation, environmental change. Processes are not
forced onto a single global tick rate purely for implementation convenience.

## 9. Development Sequence (do not skip levels)

- **Level 0 — atomic relational ecology** (first implementation milestone):
  heterogeneous population, dynamic interaction network, repeated bilateral
  cooperation/defection, optional costly punishment, imperfect observation,
  memory + forgiveness, strategy adaptation/imitation, low-rate mutation,
  costly relationship exit/rewiring.
    - **Level 0.1 — ecological closure and active relational dynamics**
      (completed sub-milestone; see `status_update.md`'s newest entry for
      the full report): closes the resource loop with a *minimal* shared,
      bounded environment pool (logistic regeneration, subsistence costs,
      extraction-capped payoffs) and a survival consequence (reduced
      interaction engagement under resource distress, chosen over
      biological reproduction as the smaller, more defensible mechanism);
      makes relationship exit/formation genuinely endogenous and ongoing
      (affordability-gated exit, accept/reject connection proposals,
      typed events) rather than an init-time-only artifact; replaces the
      under-denominated "erroneous punishment rate" with an explicit
      confusion matrix; adds policy-lineage/ancestry tracking; adds
      reusable (deliberately non-classifying) dynamical diagnostics; adds
      a generic perturbation interface. This is *not* Level 5's full
      agent-environment feedback loop (no environment-mediated behavioral
      adaptation beyond the minimal survival consequence, no economic
      volatility, no environment-side population dynamics) — it is the
      smallest closure needed to make Level 0's previously-unbounded,
      init-frozen dynamics into a genuinely closed, ongoing system, kept
      deliberately free of any governance concept per §5 below.
    - **Level 0.2 — viability, participation accounting, and ecological
      phase mapping** (completed sub-milestone; see `status_update.md`'s
      newest entry and `docs/level0.2_scientific_note.md` for the full
      report): investigates, rather than tunes away, Level 0.1's
      resource-pool collapse and near-universal measured cooperation.
      Adds a disableable, duration-based viability state machine (agents
      may become distressed, go dormant, and — only in an explicit
      opt-in mode — be removed and replaced), a swappable imitation
      fitness signal (`agents/fitness.py`, four modes, translation-
      invariance formally tested rather than assumed), an unconditional/
      conditional participation-accounting decomposition
      (`observer/participation.py`) that distinguishes genuine universal
      cooperation from selective-participation artifacts, explicit
      supply/demand ecological-balance accounting
      (`observer/ecological_balance.py`), and duration-gated dynamical
      classification (`observer/classification.py`, deliberately never
      using the word "attractor"). A two-stage Latin-Hypercube phase
      sweep, boundary perturbations, a relationship-turnover sweep, and
      four factorial null-model comparisons were run to answer this
      sub-milestone's scientific questions. All new mechanisms default
      to exact Level-0.1-compatible no-ops (`viability_mode="none"`,
      `fitness_mode="cumulative_resources"`); no governance concept was
      introduced anywhere in the generative layer.
    - **Level 0.3 — endogenous niche construction and feedback closure**
      (completed sub-milestone; see `status_update.md`'s newest entries
      and `docs/level0.3_scientific_note.md` for the full report): tests
      whether heterogeneous agents acting from local incentives, with no
      direct reward for sustainability, generate persistent or
      recoverable macroscopic ecological regimes through their own
      niche construction. Adds a second, structurally independent
      per-agent action dimension — an ecological action
      (extraction/maintenance/restraint, `agents/ecological_policy.py`)
      that is never equated with or derived from the social
      cooperate/defect action — and an opt-in spatially-disaggregated
      alternative to the single global pool: fixed-membership local
      patches (`ecology_topology="patches"`, `environment/patches.py`;
      `"global_pool"` remains the exact Level-0.2-compatible default).
      Patch membership is assigned once by a neutral rule and never
      migrates, deliberately kept independent of the continuously-
      rewiring social network. Four causal-intervention counterfactuals
      (no environmental effect, frozen/randomized/shuffled ecological
      policy) isolate whether any observed persistence is attributable
      to agent behavior at all, rather than to the bare environmental
      equation; a seven-criterion regulation-diagnostics module
      (`observer/regulation_diagnostics.py`) reports interior
      persistence, feedback dependence, perturbation recovery,
      parameter-neighborhood robustness, micro-macro linkage, and a
      cautious nonstationary-regime classification as separate,
      never-combined criteria, and never uses the term for a dynamical
      system's proven stable fixed point anywhere in the codebase
      (structurally enforced). A reproducible Latin-Hypercube phase
      search, a viability-threshold sweep, and a perturbation-recovery
      experiment were run to answer this sub-milestone's scientific
      questions; a late-discovered calibration gap (the untuned default
      parameterization is collapse-prone) is documented as a genuine
      finding, not silently retuned — see the scientific note §6. All
      new mechanisms default to exact Level-0.2-compatible no-ops
      (`ecology_topology="global_pool"`); no governance concept was
      introduced anywhere in the generative layer.
    - **Level 0.3b — regime validation and causal replication**
      (completed sub-milestone; see `status_update.md`'s newest entries
      and `docs/level0.3b_validation_note.md` for the full report): a
      focused validation milestone, adding no new generative mechanism —
      only an audited, burn-in-aware regime classifier and a repaired,
      eligibility-screened perturbation-recovery diagnostic on the
      observer side (`observer/regulation_diagnostics.py`), plus a
      prospectively-registered candidate-selection and confirmation
      pipeline built on top of both
      (`outputs/level03b_candidate_registry/candidate_registry.json`).
      Found that Level 0.3's phase-search "oscillatory"/"intermittent"
      labels do not survive the audited classifier at all (0 of 144
      point-seed runs across the original and one prespecified
      supplemental search satisfy the stricter multi-cycle/amplitude/
      autocorrelation criterion), and that neither candidate selected
      for an interesting exploratory (n=3-seed) label replicated
      robustly at n=24 confirmation seeds. The milestone's central causal
      question was answered directly, with all three outcomes (improve/
      worsen/no effect) left open going in: for the primary candidate,
      endogenous adaptive ecological behavior causally *worsens*
      ecological persistence relative to `frozen` and `randomized`
      counterfactuals (paired occupancy lower by a mean of 0.20-0.26,
      bootstrap CIs excluding zero), consistent with extraction
      propensity drifting up and maintenance propensity drifting down
      under free imitation+mutation. No Level 1 mechanism was introduced.
- **Level 1 — reputation and network formation:** indirect reciprocity,
  socially transmitted (noisy) reputation, cooperative clustering,
  ostracism, rewiring.
    - **Level 1.0 — emergence of proto-institutions under coordination
      failure** (completed sub-milestone; see `status_update.md`'s newest
      entries, `docs/level1.0_decision_record.md`, and
      `docs/level1.0_scientific_note.md` for the full report). **Naming
      note, stated plainly so this doesn't read as an unexplained
      renumbering**: this milestone's content — proposal, adoption,
      membership, monitoring, enforcement, lineage of a locally shared
      rule — is the subject matter this document's own §9 roadmap
      originally assigned to **Level 3 (delegation)**, not to "Level 1"
      as defined above (reputation/network formation). The project's
      explicit instruction named this milestone "Level 1.0" because it is
      the *first* Level-1-and-beyond milestone undertaken, directly in
      response to Level 0.3b's causally demonstrated coordination
      failure, rather than because its content matches this section's
      original Level-1 definition. Levels 1-5 as originally defined above
      are not renumbered or reordered by this decision; this sub-bullet
      is a deliberate, documented exception to "do not skip levels,"
      made because the *reason* to introduce institutional mechanisms
      (a demonstrated commons-dilemma micro-mechanism) became available
      before reputation/network-formation mechanisms were built, and the
      project's own two-route Level 1 gate (spontaneous regulation OR
      causally demonstrated coordination failure — see
      `docs/level0.3b_validation_note.md` §12) was satisfied by the
      second route. See `docs/level1.0_decision_record.md` for the full
      reasoning, including why Claude's Level 0.3b recommendation to
      delay was overruled. Adds a locally-attached, patch-scoped shared
      rule (proposal/adoption/membership/compliance/monitoring/
      sanctioning/amendment/dissolution/lineage) as a new opt-in
      generative mechanism, default-inert; does not build states,
      governments, democracy, authoritarianism, rule-of-law/state-
      capacity scores, or SEM variables; does not attempt to reproduce
      the dissertation's three governance trajectories.
- **Level 2 — public goods and group enforcement:** public-goods
  production, free riding, peer punishment, second-order free riding,
  antisocial/predatory punishment, group membership and coalitions.
- **Level 3 — delegation:** agents may transfer resources or enforcement
  responsibility to others. No predefined `Government` or `Court` object is
  ever created by the model. If an agent or coalition organically
  accumulates repeated contributions, issues signals, coordinates action, or
  punishes third parties, an external observer may *later* label that
  pattern an "enforcement centre" or "proto-institution" — the generative
  layer itself has no such object.
- **Level 4 — monitoring and constraint:** agents may monitor, resist,
  replace, appeal against, or withdraw support from concentrated
  enforcement. Constraint is costly and endogenous — never an automatically
  beneficial normative good injected into payoffs.
- **Level 5 — agent-environment feedback:** external threat, resource
  scarcity, economic volatility, population growth, interaction complexity,
  destruction/recovery. Agent behavior changes the environment; the changed
  environment alters subsequent payoffs. Attractor/persistence/
  reconstruction/phase-transition analysis becomes central only from here.

**Current milestone: Level 1.0, completed.** The Level 0.3b completion
report recommended not proceeding to Level 1; this recommendation was
explicitly reviewed and overruled by the project's own previously-agreed
two-route decision gate (spontaneous/partial regulation OR causally
demonstrated coordination failure — Level 0.3b produced the second route,
not the absence of both). See `docs/level1.0_decision_record.md` for the
complete reasoning, `docs/odd_level1.0.md` for the model description, and
`docs/level1.0_scientific_note.md` for the full Stage 1-4/§19 findings
(short version: persistent proto-institutions emerged unforced at all
three Level 0.3b registered candidates, but real monitoring/sanctioning
infrastructure showed a directionally consistent, not-yet-statistically-
confirmed *negative* point-estimate effect on ecological occupancy
relative to no institution at all — none of Stage 4's 10 seed-paired
deltas excluded zero at 20 seeds). **Level 1.1 (delegation,
administrative capacity, discretion/appropriation, accountability/
constraint, collective contributions, minimal interpatch coordination)
is now complete** — see `docs/odd_level1.1.md`,
`docs/level1.1_scientific_note.md`, and `docs/level1.1_audit_supplement.md`
for the full model description, findings, and required Work Package A-C
audit of Level 1.0's own observer/accounting layer. Every Level 1.1
mechanism defaults to a verified byte-for-byte no-op; the milestone
found and fixed one genuine production bug (institutional memory read
but never written) during its own verification. **Level 1.1b
(mechanism validation, artifact-independent testing, and a per-
mechanism RNG substream architecture) is now also complete** — see
`docs/odd_level1.1b_addendum.md` and `docs/level1.1b_validation_note.md`.
**Level 1.2 (open institutional evolution and blind phenotype
discovery) is now also complete, stopped for scientific review per
its own explicit instruction.** Adds seven
further generative work packages (institutional component
representation, local observation, component-wise transmission,
migration/membership selection, differential persistence, institutional
scaling, environmental heterogeneity), an observer-only ten-dimensional
phenotype vector, a blind (never SEM-informed) discovery pipeline, and
a twelve-criterion recurrence test — see `docs/odd_level1.2_addendum.md`
and `docs/level1.2_scientific_note.md` for the full model description
and findings (short version: no recurrent institutional phenotype
configuration was independently supported at this milestone's disclosed
scale, a null result replicated across two disjoint samples; near-
universal ecological collapse under the full mechanism set was the
dominant finding instead, robust across a scale grid and causally
implicated, via matched-seed ablation, in both `patch_regen_rate` and
`migration_enabled`).
**Level 1.2b (ecological feasibility envelope and powered blind
institutional-phenotype rediscovery) is now in progress: Sections 5-25
(Work Packages A-R plus documentation) complete, Sections 26-29
(visualizations, completion-gate check, final report) not yet run —
Level 1.3 has not started.** Re-runs Level 1.2's own blind-discovery
question at roughly 24x the sample size (a 576-run stratified joint
discovery design, ex-ante ecological-feasibility stratification via
`observer/feasibility_ratios.py`, a 384-run prospective confirmation
pool, a 32-run scaling-robustness grid, a 13-factor/208-run causal
collapse decomposition), introducing no new generative mechanism or
config field. Found and fixed six genuine, previously-undetected
ecological-ledger bugs invisible below production scale (see
`docs/level1.2b_ecological_accounting.md`). Result so far: no
recurrent, discrete institutional-phenotype structure was
independently supported at this larger scale either (a `continuum`
discovery verdict, independently replicated as `null_replicated` on
fresh confirmation data) — extending, not contradicting, Level 1.2's
own null result; near-universal ecological collapse remained the
dominant dynamic, now causally characterized and shown robust across
scale, with no "attractor" label assigned anywhere. See
`docs/odd_level1.2b_addendum.md` and `docs/level1.2b_scientific_note.md`
for the full model description and findings (the latter includes this
milestone's required verbatim non-tuning statement). See
`status_update.md`'s newest entries for the
full implementation log. Per this project's own established
convention, no further Level 1.x milestone should begin regardless of
any milestone's findings without a separate review decision. Built so
Levels 1-5 can
be added without rewriting the core (stable `Agent`, `Interaction`,
`Network`, `Environment`, `Observer` interfaces; event-sourced state so
later layers can subscribe without touching earlier ones) — Level 0.2
exercised this directly: the viability state machine, fitness-mode
module, and three new observer submodules (`participation.py`,
`ecological_balance.py`, `classification.py`) were all added alongside
the existing ones without modifying `agents/policy.py`,
`interactions/game.py`, or any generative/observer boundary rule. Level
0.3 exercised it again at a larger scale: a second independent action
dimension, a second spatial topology, and a new observer diagnostics
module were all added alongside the existing Level 0/0.1/0.2 mechanisms
— every one of them gated behind `ecology_topology="patches"` — without
modifying the social game, the network mechanism, or any existing
observer module's own logic.

## 10. Verification and Experimental Discipline (summary — see status_update.md for current state)

- Deterministic, seeded execution; no hidden global randomness — every
  stochastic draw passes through an explicit, injected RNG.
- Unit + invariant tests precede substantive interpretation of any run:
  payoff calculations, resource accounting, memory updates, observation
  error, punishment costs, strategy updating, exit/rewiring, seed
  reproducibility, config validation, population invariants.
- No single "attractive" run is ever presented as evidence. The architecture
  supports multiple seeds, parameter sweeps, alternative initial conditions
  and network structures, sensitivity analysis, and distributional summaries
  — even at Level 0, where full sensitivity analysis may be deferred but the
  batch-execution scaffolding must already exist. As of Level 0.1,
  `experiments/ensemble.py` executes this for real (30 seeds × 10
  conditions, quantile/distribution summaries, not endpoint means — see
  `status_update.md`), rather than only providing the scaffold.

## 11. Project Organization

```
abm_governance/
├── dev_mem/
│   ├── project_vision.md      # this file — durable, rarely changes
│   └── status_update.md       # living log — update every session
├── lr/
│   └── Dissertation Proposal X_1 PDF.pdf
├── src/abm_governance/
│   ├── core/                  # RNG, config, event log — generative substrate
│   ├── agents/                # Agent state + policies (generative)
│   ├── interactions/          # game-theoretic payoff grammar (generative)
│   ├── network/                # relationship graph (legacy) + dynamics (Level 0.1) (generative)
│   ├── environment/            # Level 0.1 minimal resource pool; full Level 5 feedback loop still pending (generative)
│   ├── observer/               # metrics, enforcement/network/policy/dynamics/participation/viability/ecological_balance/classification diagnostics — read-only (observer layer)
│   ├── viz/                    # plotting (observer layer)
│   └── cli.py                  # command-line entry point
├── tests/
├── experiments/                # run configs, batch/sweep/ensemble/perturbation scripts
├── outputs/                    # run artifacts (gitignored)
├── pyproject.toml
└── README.md
```

Keep the generative engine, observer/metrics layer, visualization, experiment
configuration, and CLI in separate modules with a one-directional dependency
(observer/viz/cli depend on core/agents/interactions/network; never the
reverse).
