"""CreateL3Action — Phase 3.3: Agent directly invokes the mandate_chain library to generate a real L3."""

from __future__ import annotations
import logging

from orchestrator import AgentState, ActionResult, AgentIdentity

logger = logging.getLogger("shopping-agent")


class CreateL3Action:
    """Phase 3.3: Calls mandate_chain.create_checkout_layer3() to generate real L3.

    L3 binds the specific checkout to the authorized mandate chain.
    Agent signs with its own EC P-256 private key (agent_sk).
    L3.kid must match L2.cnf.jwk.kid for chain verification to pass.
    Covers protocol step 13 (/create_checkout_layer3).
    """

    name = "create_l3"

    def __init__(self, identity: AgentIdentity, event_bus, **_kwargs):
        self._identity = identity
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        if state.scenario == "IMMEDIATE":
            return False  # User is present; no Agent-signed L3 needed
        return bool(state.checkout_id) and not state.l3_serialized

    def execute(self, state: AgentState) -> ActionResult:
        from mandate_chain import create_checkout_layer3

        self._bus.emit(
            phase="checkout",
            from_role="Shopping Agent",
            to_role="AMP src lib",
            action="create_checkout_layer3",
            request={
                "checkout_id": state.checkout_id,
                "l2_len": len(state.l2_serialized or ""),
            },
            response={},
        )

        # Build chain-format checkout from AgentState
        checkout = {
            "total_amount": {
                "currency": state.checkout_currency or "USD",
                "amount": state.checkout_amount or 0,
            },
            "merchant": {
                "reference_merchant_id": state.checkout_merchant_id or "",
                "merchant_name": state.checkout_merchant_name,
                "merchant_mcc": state.checkout_merchant_mcc,
            },
        }

        # Sign L3 with Agent's real EC P-256 private key
        agent_key = self._identity._agent_key  # jwk.JWK object
        agent_kid = self._identity._public_jwk.get("kid", "agent-key")

        l3_serialized = create_checkout_layer3(
            l2_serialized=state.l2_serialized or "",
            checkout=checkout,
            private_key=agent_key,
            kid=agent_kid,
            aud="alipayplus.com",
        )
        if not l3_serialized:
            raise RuntimeError("create_checkout_layer3 returned empty L3")

        self._bus.emit(
            phase="checkout",
            from_role="AMP src lib",
            to_role="Shopping Agent",
            action="return_l3_serialized",
            request={},
            response={"l3_serialized_len": len(l3_serialized)},
        )

        logger.info("[Shopping Agent] ✓ L3 created (EC P-256) — len=%d", len(l3_serialized))

        return ActionResult(updates={"l3_serialized": l3_serialized})
