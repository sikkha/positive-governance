# Level 1.1b Reproducibility Note

Every Level 1.1b experiment script is self-contained (`experiments/level11b_*.py`),
writes its own JSON summary under `outputs/level11b_<name>/`, and can be
re-run directly:

```bash
python experiments/level11b_coordination_calibration.py
python experiments/level11b_appropriation_decomposition.py
python experiments/level11b_accountability_conditions.py
python experiments/level11b_institutional_memory_validation.py
python experiments/level11b_functional_shock_recovery.py
python -m experiments.level11b_audited_classifier_comparison   # imports experiments.level11_common; run as a module from the repo root
python experiments/make_level11b_visualizations.py             # reads the six JSON summaries above; run last
```

**RNG mode.** Every causal-isolation script above constructs configs via
`SimulationConfig.level11b_substreams(...)` (or a preset built on it),
which sets `rng_mode="mechanism_substreams"`. This is required for the
ceteris-paribus guarantee Work Package A built — running the same
experiments under `rng_mode="legacy_single_stream"` (Level 1.1's original
default) will reproduce Level 1.1's own numbers but does **not** carry the
Work Package A isolation guarantee, and is not how any Level 1.1b causal
contrast should be re-run.

**Determinism.** Every run is fully determined by `(seed, rng_mode,
rng_registry_version)`, all three of which are written into
`SimulationConfig.to_dict()`/`to_yaml()` and therefore into every script's
own JSON summary (`design` key). `rng_registry_version="level11b_v1"`
(`core.rng.RNG_REGISTRY_VERSION`) is exported so a future registry change
(adding/removing a named stream) is immediately visible as a version bump,
not a silent trajectory change for old seeds.

**Bootstrap seeds.** Each script's seed-clustered bootstrap resampling
procedure uses its own fixed `BOOTSTRAP_SEED` constant, distinct per script
(20261 for Work Package D, 20262 for E, 20263 for F, 20264 for G, 20265 for
H) — this seed controls only which bootstrap resamples are drawn from the
already-computed per-seed values; it never affects which underlying
simulation seeds were run or their trajectories.

**Runtime.** On this project's reference environment, the full six-script
sweep (before visualizations) takes roughly 18-20 minutes total; the
slowest individual script is Work Package H's classifier comparison
(~6 minutes, `n_patches=6`/`population_size=60`, 90 runs). None of the
scripts require network access, GPU, or any dependency beyond this
project's existing `numpy`/`matplotlib` requirements.

**Test suite.** `python -m pytest -q -W error` from the repo root runs
every test, including the eight new Level 1.1b test modules
(`tests/test_level11b_*.py`, ~85 new tests across Work Packages A-H). As of
this milestone's completion: 819 passed, 6 skipped (all skips carry an
explicit artifact-missing reason via `pytest.mark.skipif`, per Work Package
B), 0 failed, 0 warnings.

**Config presets added this milestone** (see `docs/config_reference.md`'s
"Level 1.1b" section for the full narrative): `level11_legacy_compat`,
`level11b_substreams`, `level11b_coordination_nondegenerate`,
`level11b_accountability_audit_only`, `level11b_accountability_appeal_only`,
`level11b_accountability_recall_only`, `level11b_accountability_costless`,
`level11b_accountability_perfect_info`,
`level11b_accountability_randomized_placebo`. All are built on
`level11_complete`/`level11b_substreams` and accept the same `**overrides`
kwargs as every other preset in `core/config.py`.
