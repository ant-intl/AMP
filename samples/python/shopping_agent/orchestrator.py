"""Pluggable orchestration kernel: AgentState / Action / Planner / Runtime.

Core infrastructure. Decouples protocol execution from decision logic:
- Planner reads state only and outputs a decision symbol (Action name)
- Action reads state only, executes protocol operations, and returns a result descriptor (never mutates state)
- AgentRuntime is the sole state owner and committer, driving the decision loop and unifying side effects
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class NoRunnableActionError(RuntimeError):
    """No Action can run in the current state, and the state is not terminal. Indicates a deadlock."""

    def __init__(self, state: "AgentState"):
        self.state = state
        super().__init__(
            f"No runnable action and state is not terminal. "
            f"paid={state.paid}, token_id={state.token_id}, mandate_id={state.mandate_id}"
        )


@dataclass
class StopReason:
    """Reason for Runtime termination. Returned at the end of each loop_with_yield.

    kind:
      - "input_required": waiting for the next user input
      - "completed": flow completed successfully (paid=true)
      - "failed": execution exception
      - "deadlocked": incomplete state, no runnable Action and not terminal
    """

    kind: str  # "input_required" | "completed" | "failed" | "deadlocked"
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.kind, self.kind: self.detail}


@dataclass
class AgentIdentity:
    """Encapsulates Agent identity and signing capability.

    Exposes only agent_id and the sign() method externally; never leaks the private key.
    When replacing with real SD-JWT in the future, only this class needs to change.
    """

    agent_id: str
    _agent_sk: str = field(repr=False)  # private key: not serialized, not printed

    def sign(self, payload: str) -> str:
        """Sign the payload with agent_sk (simplified demo signature)."""
        import hashlib
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()[:8]
        return f"mock_sig_{self._agent_sk[:12]}_{payload_hash}"


@dataclass
class AgentState:
    """Agent's cross-phase accumulated protocol state.

    All fields are scalars or JSON-serializable dataclasses.
    The Runtime is the sole state mutator; Planner and Action receive read-only views.
    """

    # Authorization chain credentials
    enrollment_session_id: str | None = None  # Phase 1 output: CP session id returned by add_payment_method
    token_id: str | None = None       # Phase 1 output: wallet binding identifier (via query_payment_method_list)
    mandate_session_id: str | None = None  # Phase 2a output: CP session id returned by create_mandate_session
    mandate_id: str | None = None     # Phase 2b output: returned by inquiry_mandate_session
    l1_serialized: str | None = None  # L1: AlipayPlus signature, binds platform and wallet identity (returned by inquiry)
    l2_serialized: str | None = None  # L2: MPP signature, binds Agent identity to wallet authorization (returned by inquiry)
    l3_serialized: str | None = None  # L3: Agent signature, binds specific transaction to mandate (produced directly by lib)

    # Transaction context
    products: list = field(default_factory=list)          # search results
    selected_product: dict | None = None                  # selected product
    checkout_id: str | None = None
    checkout_amount: float | None = None
    checkout_currency: str | None = None
    checkout_merchant_id: str | None = None
    checkout_merchant_name: str = "Demo Store"
    checkout_merchant_mcc: str = "5411"
    payment_token: str | None = None
    transaction_id: str | None = None
    paid: bool = False

    # Scenario mode: determines action ordering and authorization chain layers.
    # AUTONOMOUS (default): 3-layer chain (L1+L2+L3), mandate before checkout.
    # IMMEDIATE: 2-layer chain (L1+L2, no L3), checkout before mandate.
    scenario: str = "AUTONOMOUS"

    # Phase gates — turn boundary control for multi-turn conversations.
    # CLI auto mode: defaults to True, all Actions can run, behavior unchanged.
    # Web multi-turn mode: server sets to False when creating TaskSession; Commands unlock turn by turn.
    enrollment_requested: bool = True
    mandate_requested: bool = True
    purchase_requested: bool = True  # gates search_catalog; CLI default True (unchanged)

    # User intent (set by ShoppingIntentCommand)
    shopping_query: str = ""
    budget_max: float | None = None
    # Authorization expiry stated by the user (ISO 8601 UTC), e.g.
    # "2026-10-10T23:59:59Z". It bounds the AUTONOMOUS mandate: the wallet
    # derives the L2 lifetime from it, so there is no default — the user is
    # asked for it before the human-not-present mandate flow starts.
    mandate_expire_time: str | None = None

    # IDV interaction gates (web mode only):
    # enrollment_idv_pending: wallet-side auth_session_id (from CP idv info), set by
    #   add_payment_method; cleared by server after /idv/confirm succeeds at MPP.
    # enrollment_idv_done: set by server after IDV confirmed; consumed by query_payment_method_list.
    # mandate_idv_pending: wallet-side auth_session_id (from CP idv info), set by
    #   create_mandate_session; cleared by server after /idv/confirm succeeds at MPP.
    enrollment_idv_pending: str | None = None
    enrollment_idv_done: bool = False
    mandate_idv_pending: str | None = None

    # Travel delegation (P0: intent capture only, no protocol execution).
    # travel_intent: structured TravelIntent dict set by TravelIntentCommand;
    #   cleared by CancelTravelCommand.
    # travel_intent_confirmed: set True by ConfirmTravelCommand;
    #   does NOT unlock mandate_requested (P0 stops at READY_FOR_EXECUTION).
    travel_intent: dict | None = None
    travel_intent_confirmed: bool = False
    match_reasons: list = field(default_factory=list)
    purchase_queue: list = field(default_factory=list)
    spent_total: float = 0.0
    purchased_items: list = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dict."""
        return asdict(self)

    def readonly_view(self) -> AgentState:
        """Return a deep-copy snapshot of the current state for read-only use by Planner / Action."""
        return copy.deepcopy(self)


@dataclass
class VerifyEntry:
    """Verification assertion that an Action wants the Runtime to record."""

    check_name: str
    passed: bool
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Result descriptor returned to the Runtime after Action execution.

    - updates: fields to merge into state (partial update)
    - verification: information for the Runtime to log as a verify entry
    """

    updates: dict[str, Any] | None = None
    verification: VerifyEntry | None = None


@dataclass
class Decision:
    """Decision output from the Planner.

    - next_action_name: the sole Action identifier executed by the Runtime
    - rationale: decision reasoning (filled by LLM; usually empty for rule-based)
    - look_ahead: short-term path preview (for logging/display only; not consumed by Runtime)
    """

    next_action_name: str
    rationale: str = ""
    look_ahead: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Protocol interfaces
# ---------------------------------------------------------------------------


@runtime_checkable
class Action(Protocol):
    """Protocol action interface. Each Action self-describes its preconditions and executes protocol interactions."""

    @property
    def name(self) -> str:
        """Unique identifier for the Action, used for Registry registration and Planner references."""
        ...

    def can_run(self, state: AgentState) -> bool:
        """Precondition: whether this Action is eligible to execute in the current state."""
        ...

    def execute(self, state: AgentState) -> ActionResult:
        """Execute the protocol action and return a result descriptor. Does not mutate state directly."""
        ...


@runtime_checkable
class Planner(Protocol):
    """Decision-maker interface. Reads state + candidate list only; outputs a decision symbol."""

    def decide(self, state: AgentState, allowed_actions: list[str]) -> Decision | None:
        """Decide the next Action based on the current state and the list of runnable Actions.

        - allowed_actions: list of Action names with can_run==True, pre-computed by the Runtime
        - Returning None indicates the Planner voluntarily ends the flow
        """
        ...


# ---------------------------------------------------------------------------
# AgentRuntime
# ---------------------------------------------------------------------------


class AgentRuntime:
    """Sole state owner and execution loop driver.

    Responsibilities:
    - Holds AgentState (single entry point)
    - Holds the Action Registry (instances with injected dependencies)
    - Drives the Planner → Action → apply loop
    - Unifies verify logging and change_log recording
    """

    MAX_STEPS = 100  # guard against infinite decision loops

    def __init__(
        self,
        registry: dict[str, Action],
        planner: Planner,
        logger=None,
        event_bus=None,
        initial_state: dict[str, Any] | None = None,
    ):
        self._state = AgentState()
        if initial_state:
            for k, v in initial_state.items():
                if hasattr(self._state, k):
                    setattr(self._state, k, v)
        self._registry = registry
        self._planner = planner
        self._logger = logger
        self._event_bus = event_bus
        self._change_log: list[dict[str, Any]] = []
        self._step_count = 0

    @property
    def state(self) -> AgentState:
        """Current state (for internal use; external consumers should use state_view for a read-only snapshot)."""
        return self._state

    @property
    def change_log(self) -> list[dict[str, Any]]:
        """State change history."""
        return list(self._change_log)

    @property
    def step_count(self) -> int:
        return self._step_count

    def state_view(self) -> AgentState:
        """Return a read-only state snapshot for external consumption."""
        return self._state.readonly_view()

    def loop(self) -> None:
        """Decision loop: Runtime computes candidates → Planner decides → Action executes → apply, until completion or deadlock."""
        for _ in range(self.MAX_STEPS):
            view = self._state.readonly_view()

            # Runtime computes the list of currently runnable Actions
            allowed = [name for name, action in self._registry.items() if action.can_run(view)]

            if not allowed:
                if self._is_terminal(view):
                    break  # state reached terminal; normal exit
                else:
                    raise NoRunnableActionError(view)  # deadlock; fail immediately

            # Planner selects from candidates
            decision = self._planner.decide(view, allowed)
            if decision is None:
                break  # Planner voluntarily ends

            # Record the decision
            self._log_decision(decision)

            # Retrieve the Action instance from the Registry
            action = self._registry.get(decision.next_action_name)
            if action is None:
                raise RuntimeError(
                    f"Action '{decision.next_action_name}' not found in registry"
                )

            # Action execution: receives a read-only view, returns a result descriptor
            result = action.execute(self._state.readonly_view())

            # Runtime apply: the sole state mutation point
            self._apply(decision.next_action_name, result)
            self._step_count += 1
        else:
            # Exceeded maximum steps
            if self._logger:
                self._logger.log_error(
                    "AgentRuntime", "max_steps_exceeded",
                    f"Loop exceeded {self.MAX_STEPS} steps, forcing stop",
                    context={"last_step": self._step_count},
                )

    def _is_terminal(self, state: AgentState) -> bool:
        """Determine whether the state has reached a terminal state (payment completed)."""
        return state.paid is True

    def _apply(self, action_name: str, result: ActionResult) -> None:
        """Apply Action result: merge state + record verify + append change_log."""
        updates = result.updates or {}

        # Merge state updates
        for key, value in updates.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

        # Append change_log (leaves room for future event replay)
        self._change_log.append({
            "action": action_name,
            "updates": updates,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        # If the Action carries a verification, the Runtime logs it uniformly
        if result.verification and self._logger:
            self._logger.log_verify(
                "ShoppingAgent",
                result.verification.check_name,
                result.verification.passed,
                result.verification.evidence,
            )

    def _log_decision(self, decision: Decision) -> None:
        """Record the Planner decision to execution.jsonl (optional)."""
        if self._logger:
            self._logger.log_decision(
                "AgentRuntime",
                "planner_decide",
                {
                    "next_action": decision.next_action_name,
                    "rationale": decision.rationale,
                    "look_ahead": decision.look_ahead,
                },
            )

    def loop_with_yield(self, sink: Any) -> StopReason:
        """Decision loop + yield variant. Publishes events via sink after each Action execution.

        Differences from loop():
        - Does not raise NoRunnableActionError; returns a StopReason instead
        - Accepts a sink parameter (EventSink); Action results are published via sink
        - Returns a StopReason instead of None

        Runs inside asyncio.to_thread(); sink uses queue.Queue for bridging.
        """
        try:
            for _ in range(self.MAX_STEPS):
                view = self._state.readonly_view()
                allowed = [
                    name for name, action in self._registry.items()
                    if action.can_run(view)
                ]

                if not allowed:
                    if self._is_terminal(view):
                        return StopReason(
                            kind="completed",
                            detail={
                                "transaction_id": self._state.transaction_id,
                                "total_steps": self._step_count,
                            },
                        )
                    else:
                        input_type = self._infer_next_input_type(view)
                        detail: dict[str, Any] = {
                            "type": input_type,
                            "message": self._infer_prompt(view),
                            "scenario": self._state.scenario,
                        }
                        # Card data for the IDV wait, by intent kind (mutually
                        # exclusive): travel delegation → TravelIntentCard;
                        # IMMEDIATE shopping (product already searched) →
                        # ShoppingIntentCard with the product; AUTONOMOUS shopping
                        # (mandate precedes search) → ShoppingIntentCard with the
                        # intent + budget only (no product data yet).
                        if input_type == "idv":
                            if self._state.travel_intent:
                                detail["travel_intent"] = self._state.travel_intent
                            elif self._state.selected_product:
                                detail["selected_product"] = self._state.selected_product
                                detail["checkout_amount"] = self._state.checkout_amount
                            elif self._state.shopping_query:
                                detail["shopping_intent"] = self._state.shopping_query
                                if self._state.budget_max is not None:
                                    detail["intent_amount"] = self._state.budget_max
                        return StopReason(
                            kind="input_required",
                            detail=detail,
                        )

                decision = self._planner.decide(view, allowed)
                if decision is None:
                    return StopReason(
                        kind="input_required",
                        detail={"type": "user_input", "message": "Waiting for input."},
                    )

                self._log_decision(decision)
                action = self._registry.get(decision.next_action_name)
                if action is None:
                    return StopReason(
                        kind="failed",
                        detail={"error": f"Action '{decision.next_action_name}' not found"},
                    )

                sink.emit_event({
                    "type": "action_started",
                    "action": decision.next_action_name,
                    "step": self._step_count + 1,
                })

                result = action.execute(self._state.readonly_view())
                self._apply(decision.next_action_name, result)
                self._step_count += 1

                sink.emit_event({
                    "type": "action_completed",
                    "action": decision.next_action_name,
                    "step": self._step_count,
                })

            return StopReason(
                kind="deadlocked",
                detail={"blocked_actions": [], "message": "Max steps exceeded"},
            )

        except Exception as exc:
            return StopReason(kind="failed", detail={"error": str(exc)})

    @staticmethod
    def _infer_next_input_type(state: AgentState) -> str:
        if state.enrollment_idv_pending or state.mandate_idv_pending:
            return "idv"
        if state.l1_serialized is not None and not state.purchase_requested:
            return "purchase_intent"
        if state.token_id is not None and not state.mandate_requested:
            return "purchase_intent"
        if not state.enrollment_requested:
            return "enrollment"
        return "user_input"

    @staticmethod
    def _infer_prompt(state: AgentState) -> str:
        if state.enrollment_idv_pending or state.mandate_idv_pending:
            return "Complete identity verification to continue."
        if state.l1_serialized is not None and not state.purchase_requested:
            return "You have successfully set up your payment method. What would you like to purchase?"
        if state.token_id is not None and not state.mandate_requested:
            return "You have successfully set up your payment method. What would you like to purchase?"
        if not state.enrollment_requested:
            return "Say 'bind wallet' to get started."
        return "Waiting for your input."
