# Level 1.2 Scientific Note — Open Institutional Evolution and Blind Phenotype Discovery

See `docs/odd_level1.2_addendum.md` for the model description and
`docs/level1.2_completion_report.md` for the full completion-gate
audit. This note reports what the Stage 0-13 experimental program
actually found.

## Headline finding

**No recurrent institutional phenotype configuration was independently
supported at this milestone's disclosed scale.** This is a replicated
null result: Stage 4's blind discovery run (n=24 pooled runs) found
0 of 76 candidate clusters meeting all 12 minimum recurrence criteria,
and Stage 5's independent replication on a genuinely fresh, disjoint
12-run pool — using the identical, un-retuned discovery pipeline —
also found 0 of 72 candidates meeting all 12 criteria. Per this
milestone's own closing instruction: this is reported as "the
recurrent-phenotype hypothesis was not supported [at this sample
size]" — not forced toward any particular number, and not grounds to
alter the model or rerun the search now that the outcome is known.

The dominant dynamic underlying this — and the more interesting finding
this milestone actually produced — was **near-universal ecological
collapse** under the full Level 1.1+1.2 mechanism set, which the
Stage 0-13 program characterized in some depth.

## The collapse dynamic

- **Stage 2** (small pilot, 10 seeds, one fixed condition): 7/10
  collapse, 3/10 fragmented, 0/10 viable.
- **Stage 3** (main search, 24 runs across an 8-dimensional Latin-
  Hypercube parameter sweep): 22/24 collapse, 2/24 fragmented, 0/24
  viable — collapse dominates across the swept range, not just one
  parameter setting.
- **Stage 5** (fresh-seed confirmation, same 12 parameter draws as
  Stage 3, new seeds): 11/12 collapse, **1/12 viable** — the first
  `viable` outcome observed anywhere in this milestone (draw 9, notably
  high `patch_regen_rate=0.97`).
- **Stage 6** (scaling robustness, population ∈ {40,80} × patches ∈
  {3,6}, 8 runs): **8/8 collapse** — the dynamic is not a small-
  population artifact; it holds from population 40-80 and 3-6 patches.
- **Stage 7** (perturbation/transition): inconclusive by design — both
  shocked and unshocked baseline runs already collapsed, leaving no
  non-collapse state for a shock to transition away from (a floor
  effect, explicitly disclosed, not evidence perturbations are inert).

## Causal ablations (Section 13)

Two matched-seed ablations (`rng_mode="mechanism_substreams"`, 8 seeds
each, `experiments/level12_stage13_causal_ablations.py`) tested the two
candidate explanations the correlational stages above surfaced but
never tested causally:

- **Migration ablation** (migration on vs. off, same seed): 5/8 pairs
  favor migration OFF on ecological resource fraction, mean paired
  difference −0.077, 4/8 outcome-label transitions (3 of 4 go
  fragmented→collapse when migration turns on). Wilcoxon p=0.25
  (supplementary only, n too small for confidence). A real but modest,
  somewhat mixed effect — directionally consistent with Stage 2's
  original single-condition finding.
- **Regen-rate ablation** (`patch_regen_rate` at Stage 3's own sampled
  bounds, 0.2 vs. 1.0, same seed): 7/8 pairs favor high regen rate,
  mean paired difference +0.033, 2/8 outcome-label transitions
  (collapse→fragmented). Wilcoxon p=0.039 — a more consistent causal
  signal.
- **Neither ablation overturns the headline collapse finding**: 13/16
  and 14/16 ablation runs respectively still landed in `collapse`.
  These results refine rather than reverse Stages 3-7's conclusion —
  environmental regeneration capacity and migration activation are both
  real, causally-implicated contributing factors, neither sufficient
  alone to make `viable` the typical outcome at the tested population/
  duration scale.

## What this does and does not say about the dissertation's typology

Nothing. Section 14's SEM firewall held throughout (audited explicitly
in `tests/test_level12_sem_firewall.py`, and per-module/per-script in
every one of the 34+ dedicated test files this milestone added) — no
SEM/dissertation data, label, or trajectory count was read, imported,
or referenced anywhere in the generative, observer, or experimental
code. The absence of a 3-way (or any-way) recurrent structure in this
milestone's own pooled samples says nothing about whether the
dissertation's typology holds in survey data; it says that THIS ABM,
at the disclosed scale this session's compute budget supported, did
not produce independently-reproducible institutional phenotype
clusters, and its dominant emergent behavior at that scale was
ecological collapse rather than any form of persistent governance
differentiation.

## Disclosed scope reductions carried by this milestone (summary)

Every stage's own script documents its reduction in its own docstring
before running; collected here for convenience:

- Discovery pipeline: 3 candidate methods (not the fuller suggested
  menu), k=1-8.
- Stage 1: 8 seeds/condition, population 40, 350 steps.
- Stage 2: 10 seeds, population 40, 400 steps.
- Stage 3: 12 parameter draws × 2 seeds (24 total), population 40, 500
  steps.
- Stage 5: 12 fresh runs (same 12 parameter draws, fresh seeds).
- Stage 6: 4 scale conditions × 2 seeds (8 total), 300 steps.
- Stage 7: 2 perturbation types × 3 seeds (6 shocked/unshocked pairs),
  400 steps.
- Section 13: 2 ablations × 8 matched-seed pairs.

None of these numbers were adjusted after viewing results — each is
recorded, before running, in its own script's docstring, per Section
12/20's disclosure discipline.
