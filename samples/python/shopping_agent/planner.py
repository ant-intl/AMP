"""RuleBasedPlanner — selects the next Action from allowed_actions in protocol order.

This is the default rule-based decision-maker implementation. It contains no
protocol-specific if-else branches — the protocol order is encoded in the
ACTION_ORDER constant and each Action's can_run logic.
A future LLM Planner can seamlessly replace this by implementing the same
Planner interface.
"""

from __future__ import annotations

from orchestrator import AgentState, Decision


# ACTION_ORDER is imported from actions/__init__.py to avoid duplicate definitions
from actions import ACTION_ORDER, ACTION_ORDER_IMMEDIATE


class RuleBasedPlanner:
    """Generic rule-based decision maker: pick the first Action from allowed_actions in ACTION_ORDER.

    - Does not hold a Registry reference
    - Does not evaluate can_run (handled by the Runtime)
    - Only selects by priority from a pre-filtered candidate list
    - Selects ACTION_ORDER_IMMEDIATE when scenario is IMMEDIATE
    """

    def decide(self, state: AgentState, allowed_actions: list[str]) -> Decision | None:
        """Select the first Action from allowed_actions in the scenario-appropriate order."""
        order = ACTION_ORDER_IMMEDIATE if state.scenario == "IMMEDIATE" else ACTION_ORDER
        for name in order:
            if name in allowed_actions:
                return Decision(next_action_name=name)
        return None
