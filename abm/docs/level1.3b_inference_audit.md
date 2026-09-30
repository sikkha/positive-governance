# Level 1.3b — Inference Audit of the Level 1.3 Decision-Gate Report (Section 5, Work Package A)

**Status: complete. Audits every headline interpretive claim in
`docs/level1.3_decision_gate_report.md` and the Stage-by-stage claims in
`docs/level1.3_scientific_note.md` it draws on, per Section 5's own
required evidence-table format. This document adds no new run and no new
number — every figure cited below is read directly from the already-
committed `outputs/level13_*` JSON and the two Level 1.3 documents named
above, matching this milestone's own "reasoning document over evidence
that already exists" precedent (`docs/level1.3_decision_gate_report.md`
§ header). `docs/level1.3_decision_gate_report.md` is preserved
unedited — this is a new, separate audit, not a rewrite.**

## 1. Disclosed scope note

This session's working context carries Section 5's own exact seven-
question wording only via a compacted summary of an earlier turn
(Level 1.3b's governing specification was pasted once, at length, and
is not recoverable verbatim after this session's own context
compaction) — the same disclosed situation `observer/sequencing_
diagnostics.py`'s own module docstring already flagged for two Level
1.3 dimension definitions. What IS recoverable verbatim is the
required evidence-table schema itself (`| Level 1.3 claim | Evidence |
Design type | Uncertainty available? | Reproduced? | 1.3b disposition
|`), used exactly below. In place of the exact original seven-question
wording, this audit applies seven explicit, disclosed questions
constructed from Section 2's own decision space (does history-dependent
displacement differ from historical institutional speciation?) and this
project's own established audit doctrine (Level 1.2b's own recurrence-
and statistical-requirements audits): for each headline interpretive
claim,

1. What is the claim's exact evidentiary basis (specific numbers,
   specific committed output file)?
2. Is the claim descriptive (restates a measured quantity) or
   inferential (generalizes beyond the runs actually measured)?
3. What design produced the evidence — correlational/pooled-
   observational, matched/causal, or resampling-based?
4. Is uncertainty (a CI, a bootstrap distribution, seed-clustering)
   reported alongside the point estimate, or is it a bare point
   estimate?
5. Has this specific claim been reproduced on data independent of
   whatever data first produced it, or does it rest entirely on the
   data that discovered it?
6. Does the claim risk conflating correlation with causation, or an
   observer-side composite (S_obs/Z_obs) with a generative claim about
   agents, or a discrete in-sample partition with a "natural type"?
7. What Level 1.3b disposition follows — stands as stated, stands with
   an explicit qualification, needs a dedicated confirmatory stage
   (and which one), or should not be treated as established until then?

## 2. Evidence table

| Level 1.3 claim | Evidence | Design type | Uncertainty available? | Reproduced? | 1.3b disposition |
|---|---|---|---|---|---|
| A (one family) ruled out: S_obs/Z_obs vary by pressure-onset ORDER (~6-7.5% relative spread across 6 orderings) | `docs/level1.3_decision_gate_report.md` §2; Stage 3, 72 runs | Pooled-observational (matched only on entrenchment on/off, not on the causal question of order itself) | No CI or bootstrap reported on the by-ordering means; spread is descriptive only | Not independently reproduced — single 72-run Stage 3 pool, no fresh replication of the ordering effect specifically | Stands as a descriptive claim (real, nonzero spread exists in this data); the INFERENTIAL step ("is this a real ordering effect and not sampling noise across 6 seeds/cell") is not yet quantified — Level 1.3b's own Stage 3 (task #116, purpose-designed matched factorial with seed-clustered bootstrap CIs, per Section 9) is the correct confirmatory step, not assumed here |
| F (no detectable effect) ruled out: Stage 5 matched-seed counterfactual divergence (mean \|S_obs diff\| erased-vs-base ≈0.0027, reversed-vs-base ≈0.0116; 1/16 and 3/16 seeds show sequencing-vector shift) | `docs/level1.3_decision_gate_report.md` §2; Stage 5, 16 matched triples | Genuinely causal (matched seed triples, base/erased/reversed) — the strongest design type in this milestone's own evidence base | No bootstrap/CI on the 16-triple mean differences; a minority-of-seeds count is reported honestly rather than smoothed into a single "significant" claim | Single-channel (`security_pressure` only, by disclosed design) — not reproduced on other channels or a larger n | Stands, with its own disclosed single-channel scope preserved rather than generalized to "history matters" broadly; Level 1.3b's own Stage 6/Work Package G (task #119, six matched history-erasure interventions) is the direct, broader-scope successor test |
| Stage 6 `headline_k=2` (silhouette 0.334) discovery result | `docs/level1.3_scientific_note.md` §7; 216 pooled runs | Pooled-observational, in-sample (Stage 3+4+5 pooled, fit and scored on the same 216 points) | Bootstrap stability reported (mean ARI 0.917, std 0.216, 30 resamples) — a genuine strength | **Explicitly failed reproduction on fresh data** — Stage 7's 12 fresh points all fell into one cluster, log-likelihood degraded from ≈-1.29 (train) to ≈-6.05 (fresh) | Does NOT stand as an established discrete-family finding — the milestone's own decision-gate report already reaches this same conclusion (D_continuum, not B_two_families) via a fixed threshold rule; this audit independently corroborates that disposition from the reproduction failure alone, not merely the threshold-rule mechanics |
| Cross-algorithm agreement only modest (mean ARI ≈0.291); hdbscan finds 0 clusters | `docs/level1.3_scientific_note.md` §7 | Pooled-observational, in-sample | No CI reported beyond the ARI mean itself | N/A — a property of the fitting procedure on the fixed 216-point pool, not itself something to "reproduce" | Stands; correctly used as evidence AGAINST the discreteness of the k=2 partition, not for it — consistent disposition already in the decision-gate report |
| `cluster_vs_source_stage_ari ≈0.554` (pool heterogeneity confound) | `docs/level1.3_discovery_methods.md` §3 (cited in scientific note §7) | Pooled-observational | Single ARI value, no resampling distribution | N/A | Stands as a disclosed confound, correctly NOT treated as ruling out the k=2 result outright (ARI would be much higher under a pure pooling artifact) but correctly flagged as a reason the pool is not the purpose-designed homogeneous discovery Section 8 requires — directly why Level 1.3b's own Stage 4/Work Package D (task #117) is required rather than optional |
| S_obs-Z_obs coupling: Pearson r≈0.888, Spearman ρ≈0.913, 228 pooled runs | `docs/level1.3_scientific_note.md` §9 | Pooled-observational, correlational | No CI on the correlation coefficients themselves (though p-values are reported: p≈2.4e-78, p≈3.8e-90 — these bound sampling noise given the model, not measurement-construction validity) | Not yet audited for whether the coupling is genuine vs. shared-construction/common-driver/normalization-artifact — explicitly named as an open question by Level 1.3b's own Section 14 | Does NOT yet stand as a claim about genuine construct independence or non-independence — correctly treated by Level 1.3 itself as "strong correlation" only, never as "these are the same thing" or "these are causally linked"; Level 1.3b's own Work Package J (task #122) is the required follow-up, not assumed resolved here |
| Decision-gate verdict D (continuum), reached via Level 1.2b's unmodified `classify_discovery_verdict` threshold rule (0.3 stability bar, 0.15 silhouette floor, ≥3 k's within 0.05 → continuum) | `docs/level1.3_decision_gate_report.md` §4-5 | Rule-based classification applied post hoc to already-collected Stage 6 evidence | The rule itself has no confidence measure of its own; it is a fixed, non-invented decision procedure, which is a different (and disclosed as different) kind of rigor than a statistical CI | The verdict is corroborated (not merely asserted) by Stage 7's independent reproduction failure and Stage 8's unimodal correlation pattern — two different, disclosed lines of evidence pointing the same direction | Stands as this milestone's own reasoned, rule-applied verdict, explicitly NOT to be silently promoted to an established finding per Section 25's own stopping-rule requirement — Level 1.3b's own Stage 4 (purpose-designed discovery) and Stage 7 (Work Package H, discrete-vs-continuous model comparison, task #120) are the direct, more powerful successor tests; this audit does not itself upgrade or downgrade D, only confirms it was reasoned rather than assumed |
| `seq_bargaining_participation` NaN in 216/216 runs, disclosed as a limitation | `docs/level1.3_completion_report.md` §5 | N/A — a missingness/construction fact, not itself a scientific claim | N/A | N/A | **Resolved this milestone, not merely re-disclosed**: root-caused to two compounding, now-fixed/disclosed causes (an observer-construction defect, fixed with a regression test; a genuine resource-collapse-driven solvency effect, disclosed as a real finding) — see `docs/level1.3b_bargaining_activation_audit.md`, Work Package B (task #112) |
| Stage 9: S_obs/Z_obs "qualitatively stable" across 4 scale cells, used indirectly against E (transient differentiation) | `docs/level1.3_decision_gate_report.md` §6; 24 runs | Pooled-observational across scale cells | Ranges reported (S_obs∈[0.649,0.710], Z_obs∈[0.438,0.470]), not a formal stability statistic or CI | Not reproduced independently of the same 24-run design | Correctly labeled "suggestive, not dispositive" already in the source document; this audit does not upgrade that hedge — Level 1.3b's own Stage 5/Work Package F (task #118, `observer/historical_persistence.py`, explicit early/mid/late window diagnostics) is the actual persistence test this claim substitutes for informally |
| Entrenchment is "mechanistically a force AGAINST convergence-over-time" | `docs/level1.3_decision_gate_report.md` §6 | Argued from mechanism design (entrenchment's own definition), not measured via a temporal-persistence run | No empirical uncertainty applies — this is a definitional/mechanistic argument, not a measured quantity | Not empirically tested for whether it actually prevents convergence over the run length used | Correctly labeled "not a formal persistence test" already; stands as a plausible mechanistic argument only, not as evidence — Stage 5/Work Package F (task #118) is the direct empirical test |

## 3. Cross-cutting findings

- **No claim in the audited report was found to be fabricated,
  miscited, or contradicted by the underlying `outputs/level13_*`
  JSON** — every number checked against its source traces correctly.
  This audit's contribution is not correcting errors but making the
  evidentiary STRENGTH of each claim explicit and separating what is
  established from what is a reasoned-but-provisional reading, per
  Section 5's own purpose.
- **The report's own hedging is already unusually disciplined** for
  a document written before this audit existed: it already labels B
  as "the closest runner-up, not a rejected alternative," already
  flags the Stage 8 correlation as "suggestive, not decisive," and
  already states explicitly what would change the verdict (§7 of the
  decision-gate report). This audit finds no instance where that
  self-discipline was contradicted by re-reading the primary evidence.
- **The one systematic pattern this audit surfaces**: every headline
  claim in `docs/level1.3_decision_gate_report.md` rests on the SAME
  216- or 228-run pooled dataset (Stage 3+4+5, or +7 for the S_obs/
  Z_obs mapping) — there is no claim in the report that was tested
  against a truly independent dataset except Stage 7's own 12-point
  fresh confirmation, which is exactly the one claim (headline k=2)
  that failed to reproduce. This is not a new finding so much as a
  quantified restatement of why Level 1.3b's Sections 8 (purpose-
  designed discovery), 9 (matched factorial), and 13 (substantially
  larger fresh confirmation) exist as separate, non-optional Work
  Packages rather than a re-analysis of Level 1.3's existing pool.

## 4. What this audit does NOT do

Per Section 5's own scope and this milestone's Section 25 stopping
rule: this audit does not re-run any Stage, does not compute any new
statistic, and does not itself render a revised decision-gate verdict.
Its output is exclusively the evidence table above and the disposition
column within it — every "next step" named there is a specific,
already-tasked Level 1.3b Work Package (cited by task number), not a
new open-ended recommendation.
