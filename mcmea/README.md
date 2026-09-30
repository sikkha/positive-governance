# MCMEA: conditional evolutionary deduction (RQ4)

MCMEA evolves candidate (S, Z) configurations under an **explicitly declared** landscape. The landscape has three Gaussian topology peaks (A: strong capacity; B: Integrated Equilibrium; C: strong constraint), context-dependent payoffs, noisy robust evaluation and an adaptive search controller. The population is summarised as an elite-centroid macrostate, and a descriptive Markov layer counts transitions between macrostates. Results are **deductions from the encoded assumptions**. They are not estimates of how real regimes behave. The acronym is expanded inconsistently: the notebooks and Ch. 1 use "Markov-Chain Macrostate Evolutionary Algorithm", while Ch. 5 and Ch. 6 use "Markov Chain–Memetic Evolutionary Algorithm" (see `../LIMITATIONS.md`).

## Contents

```
notebooks/evidence/   original notebooks, byte-identical, with stored outputs (evidence)
  MCMEA_v2_regime_aware_governance.ipynb               (2026-04-15; Python 3.10.14 kernel "analyticenv")
  MCMEA_v3_oracle_mode_structural_profiles.ipynb       (2026-09-21; Python 3.11.6)   ← Chapter 5
notebooks/clean/      same code, outputs and execution counts stripped, execution-order note added (v3)
src/mcmea_v2.py, src/mcmea_v3.py   model code cells extracted verbatim (header records source SHA-256)
scripts/reproduce_recorded_outputs.py   recompute every stored numerical output and compare
expected/recorded_notebook_outputs.json values transcribed from stored outputs
requirements.txt
```

## Specifications

| | v2 "regime-aware" | v3 "oracle mode, structural profiles" (Ch. 5) |
|---|---|---|
| Candidate | (S, rule of law, democratic accountability); Z = 0.7·RoL + 0.3·DA | same |
| Peaks (amplitude @ centre, widths) | A 1.25 @ (.82,.38) .16/.18; **B 1.25 @ (.78,.78) .16/.16**; C 1.25 @ (.42,.84) .18/.16 | A 1.20 @ (.82,.38); **B 1.15 @ (.80,.80) .14/.14**; C 1.20 @ (.42,.84) |
| Context | i.i.d. **Uniform(0,1)** threat/volatility/polarization each generation | profile Beta draws (east/anglo/europe), **persistent**: c_t = clip(0.85c_{t−1} + 0.15c̃ + N(0, .08²)) |
| B context reward | +0.25(1−v) + 0.25(1−p) + 0.10(1−\|u−.5\|) | +0.18(1−v) + 0.15(1−p) − 0.20u − 0.15\|u−.5\| |
| Noise, evaluation | σ = .10 + .18v + .16p + .06u; m = 5; robust = mean − 1·sd; robust_max | same |
| Macrostate thresholds | A: S ≥ .68, Z ≤ .58; B: S, Z ≥ .65; C: Z ≥ .68, S ≤ .58 | A: S ≥ .72, Z ≤ .52; B: S, Z ≥ .75; C: Z ≥ .75, S ≤ .52 |
| Adaptive controller | 4/.40/.90; 6/.55/.80; 10/.70/.65 by mean resolution (`base_*` arguments unused) | same |
| Example run | pop 90, 60 generations, seed 7 | pop 90, 60 generations, seed 7, profile set explicitly |
| Repeated runs | seeds 20–59, 50 generations | seeds 20–59, 50 generations, per profile (3 × 40 = 120) |

## Recorded results (all reproduced)

| Result | Value |
|---|---|
| v2 seed 7 | 59 IE + 1 Hybrid (gen 0); transitions 58 IE→IE, 1 H→IE |
| v2 repeated runs | H = 1.946, exp(H) = 7.00, 13 winner bins; terminal macrostates (supplementary, not in notebook): 32 IE, 7 A, 1 H |
| v3 seed 7 east | 56 C + 4 H; 53 C→C, 2 C→H, 3 H→C, 1 H→H |
| v3 repeated runs | east 34 A / 6 C; anglo 23 / 17; europe 29 / 11; **no IE or Hybrid in 120 runs** |

These results do **not** support the Chapter 7 statement "IE for all 60 recorded generations, 59 IE-to-IE transitions". See `../docs/mcmea_specification_audit.md`.

## Hidden notebook state (v3)

The execution counts in the v3 evidence notebook are out of order. The diagnostic cells 27–34 (counts 14–21) ran **before** the example cell (count 24, now `profile = "anglo"`) and the cross-profile loop (count 27). Their stored outputs come from an earlier **east** run, which recomputation confirms. A clean top-to-bottom run shows the **europe** diagnostics at that position. Use the script below for the exact recorded values.

## External services, credentials, paths

Neither notebook calls external services, uses credentials or contains local absolute paths. The TimesFM supplementary experiment in Ch. 5 §5.7 would need the external checkpoint `google/timesfm-2.5-200m-pytorch`, but **its code is not part of this repository** (see `../docs/mcmea_timesfm_status.md`).

## Run

```bash
cd mcmea
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python scripts/reproduce_recorded_outputs.py --quick   # seed-7 examples, ~2 s
python scripts/reproduce_recorded_outputs.py           # everything, ~1 min (measured 56 s)
jupyter nbconvert --to notebook --execute notebooks/clean/MCMEA_v3_oracle_mode_structural_profiles_clean.ipynb --output /tmp/v3_run.ipynb
```

Measured runtime of the clean notebooks: v2 20 s, v3 58 s (single core). With NumPy ≥ 2, dictionaries print as `np.int64(34)` rather than `34`; the values are the same.
