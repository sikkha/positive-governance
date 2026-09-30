# Level 1.3b Revision — Pre-Revision Status Record

**Purpose.** Required preflight record (per this milestone's Section 1)
capturing the manuscript's state *before* any Level 1.3/1.3b revision
edits begin, so every change made during this milestone can be audited
against a known, compiled, version-controlled starting point.

## 1. Archival mechanism

The pre-revision repository state was committed to a local git
repository initialized in `abm_governance_paper/` for this purpose (the
repository previously had no version control) and tagged:

```
git init
git add -A
git commit -m "Baseline: Level 1.2/1.2b manuscript, pre-Level-1.3b revision"
git tag pre-level13b-revision
```

Commit: `318ec4a` — tag `pre-level13b-revision`. This commit is the
authoritative snapshot of the Level 1.2/1.2b manuscript as delivered at
the end of the prior milestone. Nothing in this revision overwrites that
history; all revision work proceeds as further commits on top of it, and
`git diff pre-level13b-revision..HEAD` recovers the complete, exact set
of changes made during this milestone.

## 2. Baseline build status (unchanged manuscript)

Built with `make pdf` (latexmk driving pdflatex + biber) immediately
after the archival commit, with no source changes:

- **Exit status:** clean (`make pdf` returned 0).
- **Output:** `build/manuscript.pdf`, 56 pages, 1,549,516 bytes.
- **LaTeX warnings:** 0 (`grep -c Warning build/manuscript.log` → 0).
- **LaTeX errors:** 0. No undefined references, undefined citations, or
  missing figures.
- **Only diagnostic output:** benign `Underfull \hbox` messages from
  long monospaced identifier strings (e.g.
  `bootstrap_stability`, `missingness_strategy_robustness`) wrapping in
  narrow table columns — cosmetic only, present in the prior milestone's
  delivered PDF as well, not a regression introduced by this check.

**Conclusion:** the pre-revision manuscript is a clean, complete,
citation- and figure-consistent 56-page document. This is the baseline
against which the Level 1.3b revision's own final QC pass (compile +
visual inspection) will be compared.

## 3. Pre-revision manuscript structure (11 sections + appendix)

`manuscript.tex` \input-s, in order:
`00_abstract`, `01_introduction`, `02_theoretical_motivation`,
`03_model_genealogy`, `04_model_and_methods`, `05_level12`,
`06_level12b`, `07_results`, `08_discussion`, `09_limitations`,
`10_conclusion`, `11_reproducibility`, plus `appendix/appendix.tex`.

Scope: Level 1.2 (general microscopic substrate) and Level 1.2b (exact
ecological accounting, feasibility ratios, outcome distributions,
recurrence/discovery-vs-confirmation analysis, causal ablation) only.
No Level 1.3 or Level 1.3b material is present anywhere in this version.
The three dissertation trajectories (Authoritarian Efficiency / Integrated
Equilibrium / Constrained Liberal) are referenced only in the theoretical
framing, not tested against ABM output.

10 tables (`tables/tab_*.tex`), 13 main figures + 14 appendix figures (all
copied byte-for-byte from `abm_governance_level1.0/outputs/level12_figures/`
or `level12b_figures/`, per `dev_mem/figure_manifest.md`, plus one
originally-authored conceptual diagram). 26-entry `references.bib`.

## 4. Scope of the coming revision (recorded here for audit, not yet executed)

This document is written *before* any Level 1.3/1.3b content is added.
The revision that follows will:

- Rewrite the abstract, introduction, theoretical framework, results,
  discussion, limitations, and conclusion to reflect Level 1.3/1.3b as
  the paper's final research position (not merely append new material).
- Add Level 1.3/1.3b sections documenting `M_historical = M_general + H`,
  the historical pressure-channel mechanisms, sequencing/counterfactual
  results, and the eight-way decision-gate verdict.
- Reorganize figures under `figures/level12b/`, `figures/level13b/`,
  `figures/conceptual/`.
- Add a `claim_evidence_manifest.csv` tracing every numerical claim to
  its exact source JSON field.
- Preserve the terminological discipline and negative/boundary claims
  specified for this milestone (configuration ≠ statistical component ≠
  recurrent phenotype ≠ dynamical attractor ≠ empirical trajectory).

No dissertation source file and no `abm_governance_level1.0` generative
code or test file is modified by this or any later step of this
milestone; both are treated as read-only throughout.
