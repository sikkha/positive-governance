"""abm_governance — generative ABM of bottom-up macropolitical organization.

See dev_mem/project_vision.md for the research philosophy and the strict
generative/observer separation this codebase enforces. In short: this
package's `core`, `agents`, `interactions`, `network`, and `environment`
subpackages form the *generative* layer and must never reference
governance-normative concepts (democracy, rule of law, state capacity,
institutional constraint, legitimacy, governance type). The `observer` and
`viz` subpackages form the *observer* layer: read-only, downstream,
never fed back into agent state or rewards.
"""

__version__ = "0.1.0"
