# Reviewer / Author Checklist — Level 1.3b Revision

Purpose: a single triage list of everything in this revised manuscript
that would benefit from author (Kan) confirmation before submission,
separate from the manuscript's own internal limitations section (which
is the disclosure to *readers*; this file is the punch-list for the
*author*).

## 1. Claims needing author confirmation

- **Title change.** The manuscript title changed from a Level 1.2/1.2b-
  scoped title to "From Institutional Emergence to Historically
  Structured Continuity: An Outcome-Blind Agent-Based Search for
  Recurrent Governance Forms." This is a substantive framing decision,
  not a mechanical update — confirm it's the title you want before
  submission.
- **Relationship to the dissertation's three trajectories
  (`sec:disc-relationship-to-dissertation`, `10_discussion.tex` §10.6).**
  This section argues, in four points, that the paper's findings are
  consistent with — but neither confirm nor refute — the dissertation's
  Authoritarian Efficiency / Constrained Liberal / Integrated Equilibrium
  typology. This is the single most theoretically load-bearing argument
  in the revision and the one most likely to draw pushback from a
  dissertation committee or co-author who has a stronger view on how
  hard the ABM evidence should be allowed to lean on the dissertation's
  own trajectories. Recommend a careful author read of this subsection
  specifically.
- **$S_{\text{obs}}$/$Z_{\text{obs}}$ framed only as "weak corroboration."**
  Confirm this is the right strength of claim — it would be easy for a
  reader (or a later paper reusing this material) to overstate the
  coupling as validating the dissertation's $S$/$Z$ constructs, which
  `sec:level13b-measurement` and the limitations section explicitly
  guard against. If you intend a stronger or weaker claim here, this is
  the place to adjust it.
- **Terminological discipline (`sec:terminology-discipline`).** The
  five-term vocabulary (configuration / statistical component /
  recurrent institutional phenotype / dynamical attractor / empirical
  trajectory) and the five explicitly-ruled-out claims are new
  interpretive machinery, not a restatement of anything from the prior
  milestone. Worth an author read to confirm every constraint is one you
  actually want to bind the paper to going forward (e.g., into any
  future Level 1.4 work).

## 2. References needing verification

Per `dev_mem/reference_audit.md` §"Entries not independently
re-verified this session," the following 8 entries are standard,
widely-reproduced citations that were used from training-data confidence
rather than independently re-searched this session (all pre-existing,
carried forward from the Level 1.2/1.2b baseline, not newly added):
`axelrod1981evolution`, `railsback2019agent`, `poteete2010working`,
`north1990institutions`, `mahoney2000path`, `acemoglu2012why`,
`windrum2007empirical`, `efron1993bootstrap`. None is cited for a
page-specific quotation or numeric claim — only for well-established,
uncontested facts — but if the venue requires every reference
independently re-confirmed before submission, this is a fast follow-up.

The 4 new entries added this revision (`capoccia2007critical`,
`fukuyama2014political`, `kaufmann2011worldwide`,
`levi1988ruleandrevenue`) were each individually verified via web search
this session (see `reference_audit.md` for the verification basis of
each) but, like all entries in this bibliography, were not cross-checked
against a second independent source — normal practice for a single-pass
audit, worth a second look if the venue is high-stakes.

## 3. Deliberately weakened / hedged language, by design

These are not oversights — they are the manuscript's own discipline
working as intended — but are worth an author's explicit sign-off since
they are more conservative than a first draft might naturally be:

- The eight-way BIC leading value ($k=8$, BIC=538.17,
  `fig:l13b-bic`) is never presented without its paired
  cross-algorithm/cross-stratum stability figure
  (`fig:l13b-discreteness`) — enforced as a hard figure-pairing rule,
  stated explicitly in the caption of the BIC figure itself.
- The $S_{\text{obs}}$--$Z_{\text{obs}}$ correlation is reported as a
  range (0.264/0.272/0.285 for the raw/partial/between-point variants)
  rather than a single headline number, with the PCA-weighted variant
  (0.136) disclosed as a genuine, separately-flagged outlier rather than
  averaged into the range.
- Level 1.3's own Stage 3/Stage 5 findings (ordering effect, matched-seed
  counterfactual) are explicitly labeled "descriptive... not yet
  resampled with a bootstrap confidence interval at this milestone,"
  with Level 1.3b's own Stage 3/Stage 6 identified as their direct,
  confirmatory, resampled successor — a distinction easy to blur in a
  compressed retelling.
- Level 1.3b's own sample sizes are disclosed as session-budget-scaled
  *minimums* (Stage 4: 240 of a preferred 432-768 runs; Stage 8: 96 of a
  preferred 144-288), not adjusted after seeing results — stated plainly
  in the limitations section rather than only in a footnote.

## 4. Unresolved limitations (already in the manuscript, flagged here for visibility)

All eleven paragraphs of `11_limitations.tex` are worth an author read,
but the following four are the ones most likely to generate reviewer
questions at a venue:

1. **`shared_lineage_persistence` was never evaluated** — one of six
   candidate explanations for cross-run phenotype similarity, requiring
   a full 576-run re-simulation with per-run lineage identifiers that
   the source project judged low-value and this paper does not fill by
   rerunning simulations (per this milestone's own no-new-experiments
   discipline).
2. **Discrete-vs-continuous comparison uses non-commensurable metrics**
   (log-likelihood vs. reconstruction error) — one of the decision
   gate's own four disclosed "what would change this verdict" items.
3. **Reconstructed governing specifications** — both Level 1.3's and
   Level 1.3b's own governing specifications were authored in an earlier
   session whose exact verbatim text became unrecoverable after a later
   context compaction; every downstream document discloses this rather
   than presenting a reconstruction as a verbatim transcription.
4. **Single research team, single model lineage** — no external,
   independently implemented replication exists yet.

## 5. Dissertation-vs-standalone-paper material suggestions

This paper is written to stand alone (it does not require the reader to
have the dissertation in hand), but a few places would benefit from
material that only the dissertation itself can supply, if this paper is
ultimately meant to accompany rather than merely reference it:

- The dissertation's own SEM fit statistics (CFI=0.889, TLI=0.817,
  RMSEA=0.144, SRMR=0.073) are quoted in this paper's theoretical
  motivation, but the dissertation's own discussion of *why* these
  particular fit statistics were judged acceptable for its purposes is
  not reproduced here — worth adding a cross-reference or short summary
  if this paper is meant to be read by someone without direct access to
  the dissertation.
- The dissertation reports no single $S$-$Z$ correlation coefficient
  for this paper to compare its own $S_{\text{obs}}$-$Z_{\text{obs}}$
  coupling against (noted in the limitations section) — if the
  dissertation's own data would allow computing one, that would let a
  future revision turn this paper's "weak corroboration" claim into a
  direct, quantitative comparison.
- The three named trajectories (Authoritarian Efficiency, Constrained
  Liberal, Integrated Equilibrium) are described in this paper only at
  the level of detail needed to explain why the ABM's own results can't
  confirm or refute them; a reader who wants the dissertation's own full
  qualitative description of each trajectory will need to consult the
  dissertation directly. Consider whether a short appendix summary would
  help a standalone reader, if that is a goal for this paper.

## 6. Mechanical / QC status (for completeness — all passed, no action needed)

- `make pdf`: clean, 93 pages, 0 warnings, 0 errors.
- `python3 scripts/verify_manuscript.py`: all 7 checks `[ok]`,
  `=== VERIFY PASSED ===`.
- Full visual inspection of the rendered PDF (title/abstract, table of
  contents, every new Level 1.3/1.3b subsection, every new figure
  pairing, discussion/triangulation pages, conclusion, reproducibility,
  bibliography, appendix figures) completed with no overflow, no
  clipping, no orphan headings, and every table rendering within page
  width.
- Every numerical claim in the revised prose traces to a row in
  `claim_evidence_manifest.csv`, itself traced to a specific field in a
  specific committed source file.
