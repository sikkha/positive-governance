---
name: revision_level13b_change_log
description: Structured before/after change log for the Level 1.3b manuscript revision — every section rewritten or extended, every file created, and every claim added, relative to the pre-level13b-revision git tag.
---

# Level 1.3b Revision — Change Log

**Baseline.** All changes below are relative to git tag
`pre-level13b-revision` (commit `318ec4a`), the unmodified Level 1.2/1.2b
manuscript (56 pages, 11 sections, clean compile). `git diff
pre-level13b-revision..HEAD` recovers the exact, complete diff.

**Scope discipline observed throughout.** No dissertation source file was
edited. No file in `abm_governance_level1.0` (the generative ABM
repository) was edited. No new simulation was run; no existing result was
recalibrated. Level 1.4 was not begun. Every number appearing in new or
revised prose traces to a line in `claim_evidence_manifest.csv`, itself
traced to a specific field in a specific committed JSON/markdown output.

## 1. Manuscript structure: 11 sections → 13 sections

| Before | After |
|---|---|
| `07_results.tex` | renamed `09_results.tex` (git mv, history preserved) |
| `08_discussion.tex` | renamed `10_discussion.tex` |
| `09_limitations.tex` | renamed `11_limitations.tex` |
| `10_conclusion.tex` | renamed `12_conclusion.tex` |
| `11_reproducibility.tex` | renamed `13_reproducibility.tex` |
| — | new `07_level13.tex` |
| — | new `08_level13b.tex` |

`manuscript.tex`'s `\input` list, title (both `\title{}` and the
`hyperref` `pdftitle`), and the abstract were all updated to match. Title
changed from a Level 1.2/1.2b-scoped title to "From Institutional
Emergence to Historically Structured Continuity: An Outcome-Blind
Agent-Based Search for Recurrent Governance Forms" — chosen to name the
paper's actual final position (a continuum, historically conditioned,
not a discrete typology) rather than only its earlier synchronic-null
finding.

## 2. Sections rewritten in full

- **`00_abstract.tex`** — fully rewritten (~450 words). Now covers: the
  dissertation's SEM background and the explicit "theorized, not
  clustered" status of its three trajectories; all four milestones
  (1.2, 1.2b, 1.3, 1.3b) in sequence; the historical operator and its
  sham-validated causal findings; the ordering effect; the
  $S_{\text{obs}}$--$Z_{\text{obs}}$ coupling with correct range framing;
  the eight-way `D_persistent_continuum` verdict with its full evidentiary
  basis (BIC, silhouette, cross-algorithm/cross-stratum ARI); and the
  paper's own final theoretical position in one closing sentence.
- **`10_discussion.tex`** — completely rewritten; the largest single
  theoretical revision in the paper. New subsections: 10.1 general
  governance-generative substrate; 10.2 institutional emergence without
  discrete phenotype convergence; 10.3 "History is real, causal, and
  persistent — without producing discrete families"; 10.4 the richer
  generative state $\mathcal{G}_t$ and the triangulation logic (new
  equation `eq:rich-state`); 10.5 continuum versus typology restated;
  10.6 relationship to the dissertation's $S$/$Z$ trajectories (4-point
  argument for why this paper neither confirms nor refutes the
  dissertation's typology); 10.7 explicit boundary conditions (5 things
  this paper does not claim); 10.8 historical sequencing as confirmed,
  not merely motivated (new equation `eq:historical-decomposition-tested`).
- **`12_conclusion.tex`** — completely rewritten, 3 paragraphs, closing
  on the required sentence (verbatim): "Explaining why real governance
  systems concentrate around particular recurring trajectories is
  deferred to future historically calibrated research."
- **`13_reproducibility.tex`** — completely rewritten: Determinism,
  Preregistration, Software-testing, and future-work paragraphs all
  updated to reflect all four milestones, the final test count
  (2047 passed / 6 skipped / 0 failed / 0 warnings), and the git
  archival mechanism introduced this revision.

## 3. Sections extended (existing content kept, new material added)

- **`01_introduction.tex`** — rewritten with four subsections: 1.1 "From
  a synchronic null to a historically conditioned question"; 1.2 "What
  this paper establishes, in sequence" (6-item enumerate spanning all
  four milestones); 1.3 "Methodological triangulation, not duplication";
  1.4 Roadmap.
- **`02_theoretical_motivation.tex`** — two new subsections inserted
  before the existing "Why null discovery is theoretically informative":
  2.4 "Historical institutionalism, path dependence, and critical
  junctures" (new citations: `pierson2000increasing`, `mahoney2000path`,
  `capoccia2007critical`, `acemoglu2012why`, `northwallisweingast2009`,
  `fukuyama2014political`, `north1990institutions`,
  `kaufmann2011worldwide`); 2.5 "Terminological discipline" — the
  canonical statement of the five-term vocabulary (configuration /
  statistical component / recurrent institutional phenotype / dynamical
  attractor / empirical trajectory) and the five specific claims this
  paper never makes.
- **`03_model_genealogy.tex`** — extended intro paragraph plus two new
  subsections: "Why Level 1.3 was the appropriate historical-extension
  gate" and "Level 1.3b: purpose-designed validation and causal
  intervention".
- **`04_model_and_methods.tex`** — three new subsections inserted before
  "Preregistration and confirmation logic": historical pressure /
  entrenchment / legitimacy mechanisms and the $S_{\text{obs}}$/
  $Z_{\text{obs}}$ observer composites; sequencing, persistence, and
  sham-controlled causal intervention; the extended six-way/eight-way
  decision-gate vocabulary. The preregistration subsection itself gained
  a paragraph on the Level 1.3/1.3b manifests and a disclosure paragraph
  about the unrecoverable verbatim governing specification (carried
  forward from the Level 1.2/1.2b limitation, not new).
- **`09_results.tex`** — new subsection "Level 1.3 / Level 1.3b: the
  historically extended substrate" appended after the existing
  Level 1.2b results, with five evidence paragraphs and two new tables
  (`tab:l13-vs-l13b-discreteness`, `tab:history-intervention`).
- **`11_limitations.tex`** — old single paragraph "No historical-
  sequencing test" replaced with five new paragraphs reflecting that the
  test has now been run: its own disclosed scope; the non-commensurable
  discrete-vs-continuous metric comparison; the $S_{\text{obs}}$/
  $Z_{\text{obs}}$-vs-SEM-latent distinction; the reconstructed-
  specification limitation (carried forward); and the still-untested
  real-governance-systems limitation. New table `tab:conclusion-boundary`
  referenced at the end.
- **`appendix/appendix.tex`** — extended in five places: an addendum
  paragraph in the ODD summary; the eight-way vocabulary added to the
  clustering-procedures section; updated test counts in the software/
  testing section; a pointer to `claim_evidence_manifest.csv` in the
  evidence-ledger section; and 11 new appendix figures appended at the
  end of the file.

## 4. New sections (full new content)

- **`07_level13.tex`** (new, ~130 lines) — "Level 1.3: Historically
  Structured Open Discovery". Subsections: experimental design (9
  stages); ordering and counterfactual evidence; discovery result and
  fresh-data reproduction failure (headline $k=2$, silhouette 0.334,
  cross-algorithm ARI $\approx0.291$, HDBSCAN found zero clusters,
  fresh-pool log-likelihood collapse $-1.29\to-6.05$, formal verdict
  `D_continuum`); the $S_{\text{obs}}$--$Z_{\text{obs}}$ coupling ($r=0.888$,
  $\rho=0.913$, $n=228$); why a purpose-designed successor was still
  required. Three figures.
- **`08_level13b.tex`** (new, ~330+ lines, the largest new section) —
  "Level 1.3b: Purpose-Designed Validation and Causal Intervention".
  Subsections 8.1-8.8: the eight-hypothesis design; H1-H2 (bargaining
  activation, ordering contrasts); H3-H4; H5-H6 (sham-validated causal
  intervention, cites `levi1988ruleandrevenue` for the performance/
  procedural legitimacy distinction); H7-H8 (fresh-data generalization
  gap, cross-algorithm/cross-stratum discreteness evidence); the
  `D_persistent_continuum` decision gate; the Stage 9 measurement audit
  (raw correlation 0.264, PCA-weighted variant 0.136 flagged as an
  outlier, partial correlation 0.272, between/within-point breakdown);
  nulls, anomalies, and limitations. Seven figures.

## 5. New tables

`tab_l13b_design.tex`, `tab_l13b_hypotheses.tex`,
`tab_l13_vs_l13b_discreteness.tex`, `tab_history_intervention.tex` (n/r
cells used rather than fabricated numbers for unreported per-window
values, with a footnote explaining the reported aggregate pattern),
`tab_method_triangulation.tex`, `tab_expanded_state.tex`,
`tab_conclusion_boundary.tex`. Existing `tab_mechanism_layer.tex`
extended with two new rows (Level 1.3, Level 1.3b).

## 6. New figures (19 total)

8 new main-text figures in the new `figures/level13b/` directory and 11
new appendix figures added to the existing `figures/appendix/`
directory — full provenance table in `dev_mem/figure_manifest.md`. The
BIC-curve figure (`l13b_fig5a_bic_curve.png`) is never presented without
its paired cross-algorithm/cross-stratum stability figure
(`l13b_fig5b_discreteness_evidence.png`), per this paper's own
figure-pairing rule; verified visually on the compiled PDF.

**Disclosed organizational deviation.** The pre-existing `figures/main/`
and `figures/appendix/` directories were left unrenamed rather than moved
into a `figures/level12b/` directory as the task brief's figure plan
suggested, to avoid a disruptive rename of 27 pre-existing
`\includegraphics` references. Full rationale in `figure_manifest.md`.

## 7. Bibliography: 4 new entries

`capoccia2007critical`, `fukuyama2014political`, `kaufmann2011worldwide`,
`levi1988ruleandrevenue` — all verified via web search before addition
(`dev_mem/reference_audit.md`), all cited at least once, none invented.

## 8. Claims added, strengthened, weakened, or ruled out

**Added** (new empirical content, absent from the pre-revision
manuscript): the entire Level 1.3/1.3b evidentiary record — ordering
effects, sham-validated causal history effects, the eight-way
`D_persistent_continuum` verdict, the $S_{\text{obs}}$--$Z_{\text{obs}}$
coupling and its measurement audit, the fresh-data generalization gap,
the richer generative state $\mathcal{G}_t$, the triangulation logic
connecting SEM + ABM + historical counterfactuals.

**Strengthened**: the paper's own central negative claim (no discrete
governance typology emerges) now has *two* independent discovery
programs behind it (Level 1.2b's synchronic search and Level 1.3b's
historically extended search), each reaching a qualitatively convergent
but methodologically distinct null — a stronger and more general claim
than either alone.

**Weakened / hedged relative to what a naive read of the raw numbers
might suggest**: the eight-way BIC leading value ($k=8$, BIC=538.17) is
never presented as evidence of eight species; it is explicitly and
repeatedly paired with near-zero/negative cross-stratum ARI and weak
cross-algorithm ARI, framed as evidence *against* a discrete reading.
The $S_{\text{obs}}$--$Z_{\text{obs}}$ correlation is reported as a range
(0.26-0.29 for most variants) rather than a single headline number,
with the PCA-weighted 0.136 variant disclosed as a separate, genuine
outlier rather than averaged away.

**Explicitly ruled out** (new `sec:disc-boundary-claims` subsection,
five boundary conditions, restated in `tab:conclusion-boundary`): this
paper does not claim the ABM discovered exactly three or exactly eight
governance species; does not claim the ABM's discovery pipeline found
attractors corresponding to the dissertation's trajectories; does not
claim path dependence in this model is universal or historically
deterministic; does not claim any simulation result empirically
validates the dissertation's own trajectory typology; and does not claim
real governance systems were tested (only a purpose-built ABM).

**Nothing was removed** from the pre-revision manuscript's claims —
Level 1.2/1.2b's own results, figures, and tables are carried forward
unchanged; the revision is additive and reframing, not subtractive.

## 9. New root-level and dev_mem deliverable files

`claim_evidence_manifest.csv`, `dev_mem/revision_level13b_status.md`,
`dev_mem/revision_level13b_change_log.md` (this file),
`build_instructions.md`, `reviewer_checklist.md`.
