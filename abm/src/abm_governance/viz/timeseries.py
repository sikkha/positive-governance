"""Basic visualization of temporal outcomes.

Headless-safe (uses the ``Agg`` backend) — writes a PNG rather than trying
to open an interactive window. This is observer-layer code: it reads a list
of per-step metric dicts (as produced by
``abm_governance.observer.metrics.compute_step_metrics``) and never touches
simulation state.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402


PANELS = [
    ("cooperation_rate", "Cooperation rate"),
    ("resource_gini", "Resource inequality (Gini)"),
    ("network_density", "Network density"),
    ("policy_diversity_bits", "Policy diversity (bits)"),
    ("mean_resources", "Mean resources"),
    ("punishment_frequency", "Punishment frequency"),
]


def plot_timeseries(metrics: list[dict], out_path: str) -> str:
    """Render a multi-panel time-series figure of the run's observer
    metrics and save it to ``out_path``. Returns ``out_path``."""
    df = pd.DataFrame(metrics)

    n = len(PANELS)
    fig, axes = plt.subplots(n, 1, figsize=(8, 2.2 * n), sharex=True)
    if n == 1:  # pragma: no cover - PANELS always has >1 entry today
        axes = [axes]

    for ax, (col, title) in zip(axes, PANELS):
        if col in df.columns:
            ax.plot(df["step"], df[col], linewidth=1.2)
        ax.set_ylabel(title, fontsize=9)
        ax.grid(alpha=0.3)

    axes[-1].set_xlabel("step")
    fig.suptitle("Level 0 — generative-layer observer metrics over time")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
