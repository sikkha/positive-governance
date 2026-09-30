"""Machine-readable results export.

Writes a run's per-step metrics (CSV + JSON), final agent/network snapshot
(JSON), the resolved config (YAML), and — as of Level 0.1 — the final
environment-pool ledger, periodic policy snapshots, and a whole-run
enforcement confusion-matrix summary, to an output directory. Kept
separate from ``cli.py`` so experiment scripts (batch/sweep runs) can call
it directly without going through the command line.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from abm_governance.observer.enforcement import confusion_matrix_summary
from abm_governance.simulation import SimulationResult


def export_results(result: SimulationResult, out_dir: str) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)

    metrics_df = pd.DataFrame(result.metrics)
    metrics_csv_path = os.path.join(out_dir, "metrics.csv")
    metrics_df.to_csv(metrics_csv_path, index=False)

    metrics_json_path = os.path.join(out_dir, "metrics.json")
    with open(metrics_json_path, "w", encoding="utf-8") as fh:
        json.dump(result.metrics, fh, indent=2)

    final_agents = [
        {
            "agent_id": a.agent_id,
            "resources": a.resources,
            "coercive_capability": a.coercive_capability,
            "policy": a.policy.name,
            "policy_lineage_id": a.policy_lineage_id,
            "observation_accuracy": a.observation_accuracy,
            "learning_rate": a.learning_rate,
            "forgiveness": a.forgiveness,
            "risk_sensitivity": a.risk_sensitivity,
            "degree": result.final_graph.degree(a.agent_id) if a.agent_id in result.final_graph else 0,
        }
        for a in result.final_agents
    ]
    final_state = {
        "initial_total_resources": result.initial_total_resources,
        "final_total_resources": sum(a.resources for a in result.final_agents),
        "final_environment_resources": (
            result.final_environment_pool.resources if result.final_environment_pool is not None else None
        ),
        "final_environment_total_extracted": (
            result.final_environment_pool.total_extracted if result.final_environment_pool is not None else None
        ),
        "final_environment_total_regenerated": (
            result.final_environment_pool.total_regenerated if result.final_environment_pool is not None else None
        ),
        "agents": final_agents,
        "edges": [[u, v] for u, v in result.final_graph.edges()],
    }
    final_state_path = os.path.join(out_dir, "final_state.json")
    with open(final_state_path, "w", encoding="utf-8") as fh:
        json.dump(final_state, fh, indent=2)

    config_path = os.path.join(out_dir, "config.yaml")
    result.config.to_yaml(config_path)

    policy_snapshots_path = os.path.join(out_dir, "policy_snapshots.json")
    with open(policy_snapshots_path, "w", encoding="utf-8") as fh:
        json.dump(result.policy_snapshots, fh, indent=2)

    confusion_path = os.path.join(out_dir, "confusion_matrix.json")
    with open(confusion_path, "w", encoding="utf-8") as fh:
        json.dump(confusion_matrix_summary(result.event_log), fh, indent=2, default=_json_safe)

    return {
        "metrics_csv": metrics_csv_path,
        "metrics_json": metrics_json_path,
        "final_state_json": final_state_path,
        "config_yaml": config_path,
        "policy_snapshots_json": policy_snapshots_path,
        "confusion_matrix_json": confusion_path,
    }


def _json_safe(value):
    """json.dump default= hook: NaN isn't valid JSON, but Python's json
    module writes it as the bare token ``NaN`` by default (readable by
    Python's own json.load, not strictly spec-compliant JSON) — that
    default behaviour is what we want here, so this hook only exists to
    handle any other non-serializable type without crashing the export."""
    return str(value)
