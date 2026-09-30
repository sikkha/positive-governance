# MCMEA specification audit

**Question audited.** Chapter 5 of the dissertation reports a v3 repeated-run result with no terminal Integrated Equilibrium (IE). Chapter 7 (§7.6.2) reports a "recovered specification" in which the macrostate is IE in all 60 recorded generations, with 59 IE→IE transitions. This audit asks where each account comes from and whether the code in this repository supports it.

**Sources examined.**

- `mcmea/notebooks/evidence/MCMEA_v2_regime_aware_governance.ipynb` (SHA-256 `163ba4d0…`; last modified 2026-04-15; kernel "Python (analyticenv)", Python 3.10.14).
- `mcmea/notebooks/evidence/MCMEA_v3_oracle_mode_structural_profiles.ipynb` (SHA-256 `d69dee1e…`; last modified 2026-09-21; Python 3.11.6).
- Dissertation **version 1.2** (`Positive Governance - Final Dissertation 1.2.docx` / `… 1.2 PDF.pdf`, both dated 2026-09-29). **Version 1.3 was not found** in the dissertation folder. Version 1.2 is the latest version present, so every chapter reference below is to v1.2. Any text changed after v1.2 has not been checked.
- Earlier dissertation drafts in the same folder: the untitled-version `Final Dissertation` (2026-09-02), `Final Dissertation 1.1` (2026-09-02/03), `PG_Chapter_5.docx` (2026-09-07) and `materials/chapter_05_mcmea_evolutionary_dynamics.md` (2026-09-01). These were used only to trace where the text came from.

**Method.** The code cells of both notebooks were extracted verbatim into `mcmea/src/mcmea_v2.py` and `mcmea/src/mcmea_v3.py`. They were then run in fresh processes with `mcmea/scripts/reproduce_recorded_outputs.py`, and every stored notebook output was compared with the recomputed value. The model was not changed.

---

## 1. What is verified

### 1.1 Chapter 5 (v1.2) matches the v3 notebook

| Chapter 5 statement (v1.2) | v3 code / recomputation | Status |
|---|---|---|
| Peaks: A 1.20 at (0.82, 0.38), widths 0.16/0.18; B 1.15 at (0.80, 0.80), widths 0.14/0.14; C 1.20 at (0.42, 0.84), widths 0.18/0.16 | `topology_scores` in cell 11 | Match |
| Context payoffs h_A, h_B, h_C and common term b(c) | cells 9, 11 | Match |
| σ_t = 0.10 + 0.18v + 0.16p + 0.06u; m = 5; λ = 1; robust_max | cells 9, 13 | Match |
| Profiles east/anglo/europe as Beta parameters; persistence ρ = 0.85, shock sd 0.08 | cell 7 (`sample_beta_context`, `evolve_context`) | Match |
| Classifier thresholds A: S ≥ 0.72, Z ≤ 0.52; B: S, Z ≥ 0.75; C: Z ≥ 0.75, S ≤ 0.52 | cell 15 | Match |
| Adaptive controller (4/0.40/0.90; 6/0.55/0.80; 10/0.70/0.65); blend α = 0.45; mutation sd 0.09 | cell 17 | Match |
| Seed 7, east: 56 C + 4 Hybrid; 53 C→C, 2 C→H, 3 H→C, 1 H→H | recomputed exactly; also the stored matrix in cell 34 | **Reproduced** |
| Seed 7, anglo and europe: 59 C + 1 Hybrid | recomputed exactly | **Reproduced** (not stored in the notebook) |
| Repeated runs, seeds 20–59, 50 generations: east 34 A / 6 C; anglo 23 / 17; europe 29 / 11; H = 2.367 / 2.554 / 2.460; exp(H) = 10.66 / 12.86 / 11.71 | recomputed exactly; also stored in cell 36 | **Reproduced** |
| "None of the 120 repeated runs terminates in B or Hybrid" | recomputed | **Reproduced** |

**Hidden-state caveat (v3 notebook).** The diagnostic cells 27–34 carry execution counts 14–21. They were therefore run *before* the example cell (count 24, `profile = "anglo"`) and before the cross-profile loop (count 27). Their stored outputs come from an earlier east-profile run. Recomputation confirms this: the stored matrix equals the east result, not the anglo one. If the notebook is run top to bottom, those cells show the **europe** result instead (verified by headless execution of the clean copy). Chapter 5 correctly attributes these figures to the east profile. The clean notebook copy now carries a note explaining this.

### 1.2 What the v2 notebook produces

The v2 notebook is the only executable specification in the repository whose population concentrates in IE.

- **Seed 7 (60 generations).** 59 generations are IE and 1 is Hybrid (generation 0). The transitions are **58 IE→IE and 1 Hybrid→IE**, which reproduces the stored cell-30 matrix exactly.
- **Repeated runs (seeds 20–59).** Winner entropy H = 1.946, exp(H) = 7.00, 13 winner bins, all reproduced. The notebook does not print terminal macrostates. This audit computed them from the same runs as a supplementary check: **32 IE, 7 A, 1 Hybrid**. This value has not been reported anywhere before.

### 1.3 Where the Chapter 7 account comes from

The Chapter 7 wording ("IE for all 60 recorded generations … 59 IE-to-IE transitions … competing-peak condition, the IE topology remains dominant") matches, almost word for word, the older Chapter 5 found in the earlier drafts:

- `Final Dissertation` and `Final Dissertation 1.1`, §5.8.3 "Macrostate Persistence" and §5.8.4 "Competing-Peak Result".
- `PG_Chapter_5.docx` and `materials/chapter_05_…md`, the same sections.

That older chapter names its own source as a **"recovered article"**. It also states: "It does not display the complete executable configuration … the figures document a result but do not yet permit exact independent replication" (§5.6.6).

Chapter 5 was rewritten around the v3 recomputation in version 1.2. The following passages still carry the older account:

| v1.2 location | Text (abridged) |
|---|---|
| §6.1, first paragraph | "Under the recovered baseline and competing-peak specifications, the population converged strongly toward the Integrated Equilibrium region." |
| §6.13.4 Divergence | "Chapter 5's population converges to the Integrated Equilibrium basin …"; boxed display "MCMEA: IE is strongly selected given the specified landscape" |
| §7.6.2 | "Under the recovered specification … IE for all 60 recorded generations, producing 59 IE-to-IE transitions … In the competing-peak condition, the IE topology remains dominant." |
| §7.6.4 table, rows 2–4 | "Strongly supported under the encoded IE-rewarding landscape"; "Three peaks are imposed; one dominates"; "Additive/persistent β changes scores but not basin order" |
| §7.6.5 | "the evolutionary model shows that an explicitly IE-rewarding landscape can sustain a dominant integrated basin" |

## 2. What differs

### 2.1 Chapter 7 does not match v2 or v3

| Feature | Chapter 7 / older Chapter 5 ("recovered article") | v2 notebook | v3 notebook (Chapter 5, v1.2) |
|---|---|---|---|
| Seed-7 macrostate record | IE in all 60 generations | IE in 59; Hybrid at generation 0 | C in 56–59; never IE |
| IE→IE transitions | 59 | 58 (+1 Hybrid→IE) | 0 |
| Context process | "stochastic and persistent β variants"; common additive β | i.i.d. **uniform** draws each generation, not persistent | persistent profile-conditioned Beta process |
| Best-fitness range | "approximately 2.2 to 3.0" | about 1.4–1.8 (stored summary table, generations 0–9) | about 1.3–1.6 (stored summary table) |
| Entropy sensitivity | 7.83 (m = 1) vs 5.09 (m = 9) | not present | not present |
| Peak amplitudes / B geometry | not stated | A = B = C = 1.25; B at (0.78, 0.78), width 0.16 | A = C = 1.20, B = 1.15; B at (0.80, 0.80), width 0.14 |
| B context reward | not stated | +0.25(1−v) + 0.25(1−p) + 0.10(1−\|u−0.5\|) | +0.18(1−v) + 0.15(1−p) − 0.20u − 0.15\|u−0.5\| |
| Classifier thresholds | not stated | A: S ≥ .68, Z ≤ .58; B: ≥ .65; C: Z ≥ .68, S ≤ .58 | .72 / .52 / .75 (stricter) |
| Repeated-run terminal states | not reported | 32 IE / 7 A / 1 H (supplementary, this audit) | 0 IE across 120 runs |

The v2 result is qualitatively close to the Chapter 7 account: IE dominates when the B basin is broad, equally tall, rewarded by context, and classified leniently. It is **not numerically identical** (58 vs 59 IE→IE transitions; generation 0 is Hybrid). v2 also lacks the persistent-β condition and the fitness scale that the older chapter describes. The v2 notebook's own comment, "More balanced amplitudes than the earlier version", shows that an earlier version existed. That version is not in this repository.

Neither notebook contains the "supplementary temporal experiment" of v1.2 §5.7. That experiment covers the equilibrium score f_eq(S, Z), the β_t = 0.92β_{t−1} + η_t generator, and the TimesFM checkpoint `google/timesfm-2.5-200m-pytorch`. Its code is not in the material provided.

### 2.2 Other v2/v3 specification differences

- v2's `run_mcmea_v2` accepts `base_elite`, `base_cx_rate` and `base_mut_rate` but never uses them. The adaptive controller alone sets these values in both versions.
- In v3, `profile=None` samples a random profile. All reported runs pass the profile explicitly.
- The repeated runs in both notebooks use 50 generations. The examples use 60.
- Both notebooks' `build_markov` put a diagonal 1 in rows with no departures. Chapter 5 (v1.2) correctly reports those rows as "not estimated". The stored heat-map figures still show the filled diagonal.

## 3. What remains unresolved

1. **The code and outputs behind the Chapter 7 / older-Chapter-5 "recovered article" result are not in this repository.** The 60/59 IE account, the 2.2–3.0 fitness range, the entropy figures and the competing-peak run cannot be reproduced or checked. Which article is meant, and which script produced it, is not recorded in any file examined.
2. **The TimesFM supplementary experiment (§5.7) has no code in the repository.** It also depends on an external model checkpoint.
3. **Whether v2 was meant as the "competing-peak condition"** cannot be established from the files.
4. No sensitivity analysis over peak height/width, context persistence or classifier thresholds exists in either notebook. §7.10.2 already proposes this as future work.

## 4. Proposed dissertation corrections (not applied)

> **Superseded by the consolidated package.** The final replacement passages, built on v3 and covering §§6.1, 6.13.4 and 7.6.2–7.6.5 plus §5.7, are maintained by the author in a separate correction package (Part B). The proposals below are kept as the audit's original record.

Nothing in the dissertation has been edited. The proposals below follow only from what the evidence shows. They do not choose a result.

**P1 — §7.6.2, first paragraph.** Replace the "recovered specification" sentences with an account that matches Chapter 5:

> "MCMEA asks what follows if governance is represented by an explicit landscape containing three competing theoretical regions. Under the v3 specification analysed in Chapter 5, in which the Integrated Equilibrium peak is lower and narrower than the other two and its contextual reward is more demanding, no repeated run (0 of 120) terminates in Integrated Equilibrium or Hybrid; terminal outcomes divide between Authoritarian Efficiency and Constrained Liberalism with profile-dependent frequencies, and the seed-7 examples remain in Constrained Liberalism apart from brief Hybrid excursions."

*Optional, only if the author wants to report v2:*

> "An earlier executable specification (v2), with equal peak heights, a broader and contextually favoured IE basin, independently drawn context and more permissive classification thresholds, concentrates in IE (seed 7: 59 of 60 generations; 58 IE-to-IE transitions; 32 of 40 repeated runs terminate in IE). The contrast shows that IE dominance is a property of the encoded landscape rather than of the label."

If the recovered-article figures are kept, they should carry their own source citation and the caveat already used in the earlier drafts: "not independently reproducible from archived code".

**P2 — §6.1, first paragraph.** Replace "Under the recovered baseline and competing-peak specifications, the population converged strongly toward the Integrated Equilibrium region" with "Under the v3 specification, the population selected the strong-capacity or strong-constraint basins and never terminated in Integrated Equilibrium; under an earlier, IE-favouring specification (v2), it concentrated in Integrated Equilibrium." The paragraph's conclusion still holds and becomes stronger: the selected basin follows from the encoded landscape.

**P3 — §6.13.4.** Change "Chapter 5's population converges to the Integrated Equilibrium basin" and the boxed line "MCMEA: IE is strongly selected given the specified landscape" to "MCMEA: the selected basin depends on the specified landscape (A/C under v3; IE under v2)". The boxed conclusion, "the MCMEA equilibrium is landscape-conditional, not a universal generative law", is unaffected.

**P4 — §7.6.4 table.** Row 2, MCMEA column: "Landscape-dependent: IE is not selected under v3 (0/120 runs), and is selected under the IE-favouring v2 specification." Row 3: "Three peaks are imposed; A or C dominates under v3." Row 4: "Persistent profile-conditioned context changes terminal frequencies (A:C ratios) but produces no IE outcomes."

**P5 — §7.6.5.** Replace "an explicitly IE-rewarding landscape can sustain a dominant integrated basin" with wording that covers both results, for example "the evolutionary model shows that which basin dominates follows from the encoded landscape: an IE-favouring specification sustains an integrated basin, whereas the stricter v3 specification does not reach it."

**P6 — Data and code availability statement.** State that the v2 and v3 notebooks are archived with this repository. State that the recovered-article code and the TimesFM supplementary code are not.

## 5. Verification record

```
cd mcmea && python scripts/reproduce_recorded_outputs.py
=== ALL RECORDED MCMEA OUTPUTS REPRODUCED ===    (≈56 s; NumPy 2.2.6, Python 3.10.12)
```

Both clean notebooks were also executed headlessly from top to bottom (v2 about 20 s, v3 about 58 s; NumPy 2.x; no errors). The v3 clean run printed the europe matrix `[[58, 0], [1, 0]]` on the C/Hybrid rows at the position where the evidence notebook stores the east matrix. This is the hidden-state effect described in §1.1.

This is software verification of recorded outputs. It is **not** evidence about real-world governance. MCMEA results are conditional deductions from the declared landscape.
