# MCMEA supplementary temporal experiment (TimesFM): status

**Status: NOT VERIFIED. No code, data or output files for this experiment exist in this repository or in the materials supplied for its preparation.**

## What dissertation v1.2 §5.7 describes

| Element | As described in §5.7 |
|---|---|
| Purpose | Test whether simulated governance-score trajectories contain temporal structure that a pretrained forecaster can extrapolate. Supplementary to the evolutionary and macrostate analysis |
| Forecaster | TimesFM (Das, Kong, Sen & Zhou, 2024), checkpoint `google/timesfm-2.5-200m-pytorch`, maximum context 512, maximum horizon 128, input normalization on |
| Generator 1 (independent context) | Candidates represented directly as (S, Z). Equilibrium score f_eq(S,Z) = 1.15√(S+10⁻⁹) + 1.15√(Z+10⁻⁹) + 0.95SZ − 0.60(S² + Z²) − 0.85\|S − Z\|, with independently drawn context |
| Generator 2 (persistent context) | The same equilibrium score plus a common scalar disturbance β_t = 0.92β_{t−1} + η_t, η_t ~ N(0, 0.12²), β₋₁ = 0 |
| Series | 240 observations; forecast input 0–179; horizon 180–209; best score, mean S, mean Z and the contextual series forecast separately; an additional first-difference forecast of the independent-context score |
| Evaluation | Point forecasts only; no prediction intervals, error metrics or benchmark forecasts (the chapter says so itself) |

## What is missing

- The generator code for f_eq and both context processes. This is **not** the Gaussian-peak landscape of the v2/v3 notebooks, and neither notebook contains it.
- Seeds and population settings for the 240-observation series.
- The TimesFM invocation: package version, checkpoint revision, preprocessing, and whether forecasts were run on CPU or GPU.
- The forecast arrays and the plotting code behind the §5.7 figures.

## What readers therefore cannot reproduce or check

1. The simulated score series themselves, and whether they came from the described equations.
2. Every statement in §5.7.4 about the recorded forecasts: the near-horizontal forecast for the independent-context series, the upward forecast path under persistent context, the stability of mean S and Z, and the downward-sloping differenced forecast.
3. Whether the stated checkpoint and settings were actually used.
4. The qualitative contrast §5.7 draws between score-level predictability and structural change, because it rests entirely on items 1–2.

## What remains valid

The v1.2 §5.7 text is already cautious. It calls the exercise supplementary, notes that it does not estimate macrostate transitions, and notes that it lacks intervals and benchmarks. Its formal definitions (§5.7.2) can be stated as a *design*. Its results (§5.7.4–5.7.5) cannot be presented as reproducible evidence until the code is archived.

## Required action (author)

Do one of the following:

- (a) Archive the generator and forecasting code with pinned versions and the forecast outputs, then re-run it once to confirm the figures.
- (b) Label §5.7 explicitly as "illustrative; code not archived" (proposed wording in `the author's dissertation correction package`, item M7).

The repository README and `LIMITATIONS.md` list this gap.
