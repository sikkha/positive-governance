# Level 1.2 Causal Ablation Note — Section 13

Full account of `experiments/level12_stage13_causal_ablations.py`. See
`docs/level1.2_scientific_note.md` for the results summarized in
context alongside Stages 2-7.

## Design

Stages 2-7 (correlational/descriptive throughout) surfaced two candidate
explanations for near-universal ecological collapse without ever
testing either causally: (1) Stage 2's single-condition observation
that `migration_enabled` coincided with ecological depletion; (2)
Stage 3/5's purely descriptive observation that above-default
`patch_regen_rate` coincided with the few non-collapse runs seen.

**Matched-seed design**: for each of 8 seeds, two conditions differing
in exactly one factor are run under the IDENTICAL seed
(`rng_mode="mechanism_substreams"`, Section 15's mandatory discipline
throughout) — every other generative parameter held fixed. Any paired
difference is attributable to that one ablated factor, not to which
random draws happened to occur — a much more statistically powerful
design than comparing across Stage 3's own unpaired parameter draws.

## Ablation 1: migration on/off

8 seeds (9000-9007), population 40, 4 patches, 400 steps,
`level11_complete` base, all Level 1.2 mechanisms except migration held
on in both arms. Result: 5/8 pairs favor migration OFF on ecological
resource fraction (mean paired difference −0.077); 4/8 pairs show an
outcome-label transition — of those, 3 go `fragmented`→`collapse` when
migration turns ON (seeds 9001, 9002, 9007 — ecological fraction drops
from ~0.22-0.24 to ~0.01-0.02), 1 goes the other way (seed 9005: 0.014→
0.051, `collapse`→`fragmented`). Wilcoxon signed-rank p=0.25 (reported
as supplementary only — n=8 is too small for a confident significance
claim on its own). **Interpretation**: a real but modest and somewhat
mixed causal effect, directionally consistent with Stage 2's original
single-condition finding but not as clean or universal.

## Ablation 2: patch_regen_rate low (0.2) vs. high (1.0)

8 seeds (9100-9107), same population/patches/steps, all 5 Level 1.2
mechanisms on in both arms, bounds reused directly from Stage 3's own
sampled `PARAMETER_SPACE` (not re-chosen for this ablation). Result:
7/8 pairs favor high regen rate (mean paired difference +0.033); 2/8
outcome-label transitions, both `collapse`→`fragmented` under high
regen (seed 9102: 0.008→0.186; seed 9104: 0.004→0.055); the remaining
6 pairs stay `collapse` in both arms but the high-regen ecological
fraction is still numerically higher in 5 of those 6. Wilcoxon p=0.039.
**Interpretation**: a more consistent causal signal — environmental
regeneration capacity improves ecological outcomes at these bounds,
even where it isn't (yet) enough to flip the outcome label.

## What this does and does not establish

Neither ablation overturns the headline finding: 13/16 migration-
ablation runs and 14/16 regen-ablation runs still land in `collapse`.
These results REFINE Stages 3-7's conclusion (two real, causally-
supported contributing factors identified) rather than reversing it —
neither factor, at the tested bounds, is sufficient alone to make
`viable` the typical outcome at this population/duration scale. The
Wilcoxon p-values are reported honestly as supplementary, not as a
formal significance claim — n=8 matched pairs is not a large enough
sample for that, and no correction for the two tests run here was
applied or is claimed to be needed at this reporting level.

No earlier stage's design, parameter space, or sample size was altered
based on this ablation's own result (Section 20's stop condition) —
this script ran once, after Stages 3-7 were already complete, using
Stage 3's own already-fixed regen-rate bounds unchanged.

Full per-seed pair data: `outputs/level12_stage13_causal_ablations/stage13_report.json`.
