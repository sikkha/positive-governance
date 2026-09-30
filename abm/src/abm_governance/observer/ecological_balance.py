"""Ecological supply/demand balance accounting and region labelling
(Level 0.2, Work Package D).

``observer/metrics.py`` exports the raw per-step ingredients
(``potential_extraction_demand``, ``realized_extraction``,
``realized_regeneration``, ``max_sustainable_regeneration``,
``environment_fraction_of_capacity``) *unmixed* — this module is where
they are combined into the documented dimensionless balance indicator

    B_t = supply_t / demand_t

and the descriptive, purely observer-side, non-normative ecological
region labels ("supply-dominant", "boundary", "demand-dominant",
"depleted"). These labels describe the state of the shared resource pool
only; they are not a claim about agent behaviour, a governance concept, or
a predetermined macrotype (see ``dev_mem/project_vision.md`` §5) — they
are computed entirely from the environment pool's own state and never fed
back into any agent decision.

Two variants of B_t are reported, both with numerator and denominator
exported as their own columns (never hidden inside the ratio, per the
milestone brief):

* ``b_t_realized`` = realized_regeneration / potential_extraction_demand —
  what the pool actually supplied this step vs. what agents actually
  wanted to draw this step (before any pool-imposed cap).
* ``b_t_structural`` = max_sustainable_regeneration / potential_extraction_
  demand — the pool's *structural* sustainable throughput (r*K/4, a fixed
  property of the configured ecological parameters — see
  ``environment/resource_pool.py``) vs. the same demand. This is the one
  that answers "is the configured demand level even in principle
  sustainable," independent of the pool's current occupancy.

Region-classification thresholds (``depleted_occupancy_threshold``,
``demand_dominant_b_threshold``, ``supply_dominant_b_threshold``) are
explicit function parameters with documented defaults, never magic
numbers buried in a conditional — per the milestone's "avoid magic
numbers; every ... threshold must be configurable and documented"
requirement.
"""

from __future__ import annotations

import math

#: Default region-classification thresholds. All three are plain floats,
#: not tied to any one config or scenario, so a caller sweeping ecological
#: parameters can override them without touching this module.
DEFAULT_DEPLETED_OCCUPANCY_THRESHOLD = 0.05
DEFAULT_DEMAND_DOMINANT_B_THRESHOLD = 0.9
DEFAULT_SUPPLY_DOMINANT_B_THRESHOLD = 1.1


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator is None or numerator is None:
        return math.nan
    if math.isnan(denominator) or math.isnan(numerator):
        return math.nan
    return numerator / denominator if denominator > 0 else math.nan


def step_balance_indicators(row: dict) -> dict:
    """Given one ``compute_step_metrics`` row, return the two B_t variants
    (each NaN if the row's ecological columns are themselves NaN — i.e.
    ecology was disabled that run)."""
    demand = row.get("potential_extraction_demand", math.nan)
    return {
        "b_t_realized": _safe_ratio(row.get("realized_regeneration", math.nan), demand),
        "b_t_structural": _safe_ratio(row.get("max_sustainable_regeneration", math.nan), demand),
    }


def ecological_region_label(
    occupancy: float,
    b_t_realized: float,
    depleted_occupancy_threshold: float = DEFAULT_DEPLETED_OCCUPANCY_THRESHOLD,
    demand_dominant_b_threshold: float = DEFAULT_DEMAND_DOMINANT_B_THRESHOLD,
    supply_dominant_b_threshold: float = DEFAULT_SUPPLY_DOMINANT_B_THRESHOLD,
) -> str:
    """Descriptive, observer-side-only label for one step's ecological
    state. Occupancy takes precedence: a pool sitting at/near zero is
    labelled "depleted" regardless of what B_t says that same step
    (B_t can be transiently >1 even at near-zero occupancy, e.g. right
    after a demand shock — occupancy is the more direct signal of
    depletion itself). Returns "unknown" if ``occupancy`` is NaN (ecology
    disabled)."""
    if math.isnan(occupancy):
        return "unknown"
    if occupancy <= depleted_occupancy_threshold:
        return "depleted"
    if math.isnan(b_t_realized):
        return "unknown"
    if b_t_realized >= supply_dominant_b_threshold:
        return "supply_dominant"
    if b_t_realized <= demand_dominant_b_threshold:
        return "demand_dominant"
    return "boundary"


def run_balance_summary(
    metrics_rows: list[dict],
    depleted_occupancy_threshold: float = DEFAULT_DEPLETED_OCCUPANCY_THRESHOLD,
    demand_dominant_b_threshold: float = DEFAULT_DEMAND_DOMINANT_B_THRESHOLD,
    supply_dominant_b_threshold: float = DEFAULT_SUPPLY_DOMINANT_B_THRESHOLD,
) -> dict:
    """Aggregate ecological-balance diagnostics over a whole run's metrics
    series (one dict per step, as produced by
    ``observer/metrics.py::compute_step_metrics``). Returns NaN-safe
    summary statistics plus the per-step region-label sequence (so callers
    building a phase map can also inspect transition timing, not just the
    aggregate)."""
    occupancies = [r.get("environment_fraction_of_capacity", math.nan) for r in metrics_rows]
    b_reals = []
    b_structurals = []
    labels = []
    for r in metrics_rows:
        b = step_balance_indicators(r)
        b_reals.append(b["b_t_realized"])
        b_structurals.append(b["b_t_structural"])
        occ = r.get("environment_fraction_of_capacity", math.nan)
        labels.append(
            ecological_region_label(
                occ, b["b_t_realized"], depleted_occupancy_threshold, demand_dominant_b_threshold, supply_dominant_b_threshold
            )
        )

    def _finite_mean(values: list[float]) -> float:
        finite = [v for v in values if not math.isnan(v)]
        return float(sum(finite) / len(finite)) if finite else math.nan

    n = len(metrics_rows)
    time_depleted = sum(1 for lbl in labels if lbl == "depleted")
    time_near_capacity = sum(
        1 for occ in occupancies if not math.isnan(occ) and occ >= (1.0 - depleted_occupancy_threshold)
    )
    label_counts = {lbl: labels.count(lbl) for lbl in set(labels)}

    return {
        "n_steps": n,
        "mean_occupancy": _finite_mean(occupancies),
        "pool_persistence": _safe_ratio(sum(1 for occ in occupancies if not math.isnan(occ) and occ > 0), n),
        "fraction_time_depleted": _safe_ratio(time_depleted, n),
        "fraction_time_near_capacity": _safe_ratio(time_near_capacity, n),
        "mean_b_t_realized": _finite_mean(b_reals),
        "mean_b_t_structural": _finite_mean(b_structurals),
        "region_label_step_counts": label_counts,
        "region_label_fractions": {k: v / n for k, v in label_counts.items()} if n else {},
        "region_labels": labels,
    }
