# Research design

This repository is the computational companion to the doctoral dissertation *Positive Governance* (Kan Yuenyong, NIDA; latest version examined: **1.2**, September 2026). The dissertation treats governance as a context-conditioned relationship between **state capacity (S)** and **institutional constraint (Z)**, not as a single ladder or a fixed midpoint. It coordinates three methods under the **Triangulated Multimethod Governance Inference Framework (TMGIF)**. Each method has a distinct inferential responsibility, and no method is allowed to answer a question that belongs to another.

| Method | Inferential responsibility | Evidence type | What it cannot establish |
|---|---|---|---|
| **SEM** (`sem/`) | Empirical measurement of governance-related *perceptions* | Survey covariance structure (WVS Wave 7, individual level, pooled, unweighted) | Dynamics, equilibrium, historical causation, country trajectories, discrete governance types |
| **MCMEA** (`mcmea/`) | Conditional evolutionary *deduction* | Computational consequences of an explicitly declared landscape, context process and classifier | Whether real political systems reward the same configurations; national transition probabilities |
| **ABM** (`abm/`, `paper/`) | *Generative* and *historical* boundary testing | Model-bound causal intervention (matched seeds, sham-controlled checkpoint forks) inside an artificial world | Country-level historical validation; real-world validity of any governance type |
| **TMGIF** (dissertation Ch. 1, 7) | Integration | Bounded meta-inference across the three | It does not turn agreement between methods into proof |

## Research questions

The wording below is quoted from dissertation v1.2.

| RQ | Question | Method | Where |
|---|---|---|---|
| RQ1 | *Dimensional structure*: can indicators associated with state capacity, rule of law and democratic accountability be represented as empirically distinguishable dimensions? | SEM, Model 1 | Ch. 3–4; `sem/` |
| RQ2 | *Configurational representation*: does the observed covariance structure support a multidimensional representation more strongly than a single undifferentiated governance factor? | SEM (EFA/parallel analysis, CFA) | Ch. 3–4; `sem/` |
| RQ3 | *Institutional constraint*: can rule of law and democratic accountability be represented as related components of a broader institutional-constraint construct, and how strong is the evidence for that higher-order representation? | SEM, Model 2 | Ch. 4; `sem/` |
| RQ4 | *Evolutionary deduction*: given an explicitly specified governance landscape, fitness function, transition structure and stochastic context, which configurations are selected, sustained or displaced? | MCMEA v3 (v2 archived) | Ch. 5; `mcmea/` |
| RQ5 | *Generative boundary test*: can institutional differentiation, persistence and path dependence emerge from heterogeneous agents and micro-level mechanisms without directly encoding the proposed governance types as model outcomes? | ABM Levels 1.2–1.3b | Ch. 6; `abm/`, `paper/` |

## Keeping the three kinds of evidence separate

1. **Survey evidence (SEM).** Loadings and fit indices describe how respondents' confidence and fairness ratings co-vary. S and Z are *perceptual* constructs. Authoritarian Efficiency, Constrained Liberalism and Integrated Equilibrium are *ideal types*, not clusters found in the data. The SEM does not classify countries.
2. **Computational deduction (MCMEA).** Results hold only for the declared peaks, widths, context functions, noise model and classifier thresholds. The labels A/B/C name regions of the model's field. Which basin dominates depends on the encoded landscape. Under v3 (the version analysed in Ch. 5) none of 120 repeated runs terminates in Integrated Equilibrium. This is a finite-sample result for that specification, not a demonstration that IE is impossible. Under the earlier v2 specification it dominates. See `docs/mcmea_specification_audit.md`.
3. **Model-bound causal intervention (ABM).** The generative layer never sees dissertation labels, SEM output or a target number of types. This is enforced by structural "SEM firewall" tests. Governance-like patterns are identified afterwards by an observer layer. Causal statements, such as "erasing stored history changes later trajectories", are *within-model* statements supported by matched-seed and sham controls. They are not claims about real societies.

**None of the simulations validates the real-world existence, stability or normative superiority of any governance type.** The ABM's main result is negative for discrete typology. Across Levels 1.2–1.3b, outcome-blind discovery finds a persistent continuum rather than a small set of recurrent institutional families (decision gate `D_persistent_continuum`). It is positive for a limited generative claim (institutions can emerge without a planner) and for within-model historical path dependence.

## Component map

```
sem/     RQ1–RQ3   R/lavaan; original scripts + validated reconstruction; no WVS data
mcmea/   RQ4       Jupyter notebooks (evidence copies with outputs + clean copies) + extracted modules
abm/     RQ5       Python package `abm_governance` (canonical, Levels 0.1–1.3b), tests, evidence outputs
paper/   RQ5       LaTeX manuscript on ABM Levels 1.2–1.3b; evidence lives in abm/outputs
legacy/  —         Level 0.x snapshot of the ABM (superseded; kept for provenance of Level 0.x outputs)
```
