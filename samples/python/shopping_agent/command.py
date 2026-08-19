"""Command layer — isolation layer between user input and AgentState.

The input layer (intent_parser / server) never mutates AgentState directly.
All cross-layer state writes must go through apply_command().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Command:
    """Command base class. Subclasses declare intent; apply_command writes to AgentState."""
    pass


@dataclass
class EnrollCommand(Command):
    """User requests wallet binding (Phase 1)."""
    pass


@dataclass
class ShoppingIntentCommand(Command):
    """User enters a shopping intent (triggers Phase 2+3)."""
    query: str = ""
    budget_max: float | None = None
    currency: str = "USD"
    # Authorization expiry stated by the user (ISO 8601 UTC). Required for the
    # human-not-present (AUTONOMOUS) mandate; None means the user said nothing
    # and must be asked — the mandate lifetime is never defaulted.
    expire_time: str | None = None


@dataclass
class ConfirmCommand(Command):
    """User confirms an operation (generic confirmation)."""
    action: str = ""  # target action to confirm


@dataclass
class TravelIntentCommand(Command):
    """User submits a structured travel intent (P0 travel delegation)."""
    intent: dict = field(default_factory=dict)  # TravelIntent.to_dict()


@dataclass
class ConfirmTravelCommand(Command):
    """User confirms the travel intent → task enters READY_FOR_EXECUTION."""
    pass


@dataclass
class CancelTravelCommand(Command):
    """User cancels the travel intent → clear travel_intent, back to intent input."""
    pass


def apply_command(cmd: Command, state: Any) -> None:
    """Apply a Command to AgentState. The sole cross-layer state write point.

    Args:
        cmd: Command instance
        state: AgentState instance (mutable reference)

    Phase gate field conventions (must be added to AgentState):
        enrollment_requested: bool — EnrollCommand unlocks Phase 1
        mandate_requested: bool   — ShoppingIntentCommand unlocks Phase 2+3
    """
    if isinstance(cmd, EnrollCommand):
        state.enrollment_requested = True

    elif isinstance(cmd, ShoppingIntentCommand):
        # ARCHITECTURE.md step 5: user shopping intent triggers mandate creation.
        # Search (Phase 3) starts AFTER mandate is done and user is notified.
        state.mandate_requested = True
        # query is saved for search_catalog to use after mandate completes
        state.shopping_query = cmd.query
        if cmd.budget_max is not None:
            state.budget_max = cmd.budget_max
        if cmd.expire_time:
            state.mandate_expire_time = cmd.expire_time
        # If mandate already done AND reusable (AUTONOMOUS has budget),
        # go straight to search. IMMEDIATE mandates are single-use (closed
        # after payment), so a new mandate must be created each purchase.
        if state.l1_serialized and state.scenario != "IMMEDIATE":
            state.purchase_requested = True

    elif isinstance(cmd, ConfirmCommand):
        # Context: mandate done, waiting for purchase confirmation → start search
        if state.l1_serialized and not state.purchase_requested:
            state.purchase_requested = True

    elif isinstance(cmd, TravelIntentCommand):
        # ARCHITECTURE.md step 5: user submits delegated purchase intent.
        # Travel intent IS the mandate trigger — Confirm on the card = IDV (step 6).
        state.travel_intent = cmd.intent
        state.travel_intent_confirmed = False
        # Unlock Phase 2 (Mandate) + Phase 3 (Purchase)
        state.mandate_requested = True
        state.purchase_requested = True
        # Construct shopping_query from travel intent for search_catalog
        intent = cmd.intent
        destination = intent.get("destination", "")
        services = " ".join(intent.get("services", []))
        state.shopping_query = f"{destination} {services}".strip()
        # Budget pass-through: travel budget constrains search + mandate
        if intent.get("budget_max"):
            state.budget_max = intent["budget_max"]
        # Expiry pass-through: the user-stated authorization window bounds the
        # AUTONOMOUS mandate (and thus the L2 the wallet issues).
        if intent.get("expiry_time"):
            state.mandate_expire_time = intent["expiry_time"]
        # Multi-item purchase queue: each service is a separate purchase cycle
        state.purchase_queue = list(intent.get("services", []))
        state.spent_total = 0.0
        state.purchased_items = []

    elif isinstance(cmd, ConfirmTravelCommand):
        # User confirmed the travel intent → mark as confirmed.
        # P0: does NOT set mandate_requested. P1 will extend this.
        state.travel_intent_confirmed = True

    elif isinstance(cmd, CancelTravelCommand):
        # User cancelled → full reset: clear travel intent AND mandate state,
        # return to "waiting for intent input" stage.
        state.travel_intent = None
        state.travel_intent_confirmed = False
        state.mandate_requested = False
        state.purchase_requested = False
        state.mandate_session_id = None
        state.mandate_idv_pending = None
        state.shopping_query = ""
        state.budget_max = None
        state.mandate_expire_time = None

    else:
        raise ValueError(f"Unknown command type: {type(cmd).__name__}")
