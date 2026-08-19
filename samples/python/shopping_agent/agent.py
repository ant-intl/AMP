"""ShoppingAgent — public facade for the AMP Shopping Agent.

Responsibilities: accept tasks, assemble the runtime environment, start the
Runtime, and return execution results.
Callers only see ``ShoppingAgent(...).run(auto=...)``; internal structure is
fully encapsulated.
"""

from __future__ import annotations

from typing import Optional

from events import EventBus
from evidence_logger import ExecutionLogger
from orchestrator import AgentIdentity, AgentRuntime

from actions import ACTION_ORDER, ALL_ACTIONS


class ShoppingAgent:
    """Public entry point for the Shopping Agent — assembly + Runtime launch.

    AgentIdentity holds its own EC P-256 JWK key pair; the public key is
    passed to the MPP via createMandateSession.
    """

    AGENT_ID = "shopping_agent_001"

    def __init__(
        self,
        merchant_url: str,
        cp_url: str,
        event_bus: EventBus,
        logger: Optional[ExecutionLogger] = None,
        planner=None,
        interactive_idv: bool = False,
        scenario: str = "AUTONOMOUS",
    ):
        self._merchant_url = merchant_url
        self._cp_url = cp_url
        self._event_bus = event_bus
        self._logger = logger
        self._scenario = scenario

        # --- Assemble AgentIdentity (keys from centralized secret store) ---
        from secret import get_agent_private_key, get_agent_public_jwk
        agent_key = get_agent_private_key()
        identity = AgentIdentity(agent_id=self.AGENT_ID, _agent_sk=agent_key)
        identity._agent_key = agent_key  # full JWK object for L3 signing
        identity._public_jwk = get_agent_public_jwk()

        # --- Assemble Action instances (inject URL dependencies) ---
        self._registry = self._build_registry(
            identity=identity,
            merchant_url=merchant_url,
            cp_url=cp_url,
            event_bus=event_bus,
            interactive_idv=interactive_idv,
        )

        # --- Assemble Planner (supports external injection; defaults to RuleBasedPlanner) ---
        if planner is None:
            from planner import RuleBasedPlanner
            planner = RuleBasedPlanner()
        self._planner = planner

        # --- Assemble Runtime ---
        self._runtime = AgentRuntime(
            registry=self._registry,
            planner=self._planner,
            logger=logger,
            event_bus=event_bus,
            initial_state={"scenario": scenario},
        )

    @staticmethod
    def _build_registry(*, identity, merchant_url, cp_url, event_bus, interactive_idv: bool = False) -> dict:
        """Build Action Registry with HTTP URL dep injection per action.

        Mapping per ARCHITECTURE.md spec:
        - add_payment_method, create_mandate_session: cp_url + bus + identity + interactive_idv
        - query_payment_method_list, inquiry_mandate_session: cp_url + bus
        - search_catalog, create_checkout, start_payment: merchant_url + bus
        - create_l3: identity + bus
        - apply_credential: cp_url + bus
        """
        deps_cp = {"cp_url": cp_url, "event_bus": event_bus, "identity": identity}
        deps_merchant = {"merchant_url": merchant_url, "event_bus": event_bus, "identity": identity}

        registry = {}
        for action_cls in ALL_ACTIONS:
            name = action_cls.name
            if name in ("add_payment_method", "create_mandate_session"):
                action = action_cls(**deps_cp, interactive_idv=interactive_idv)
            elif name in ("query_payment_method_list", "inquiry_mandate_session"):
                action = action_cls(cp_url=cp_url, event_bus=event_bus)
            elif name in ("search_catalog", "create_checkout", "start_payment"):
                action = action_cls(**deps_merchant)
            elif name == "create_l3":
                action = action_cls(identity=identity, event_bus=event_bus)
            elif name == "apply_credential":
                action = action_cls(cp_url=cp_url, event_bus=event_bus)
            else:
                # fallback: pass all deps, let **_kwargs absorb extras
                action = action_cls(
                    cp_url=cp_url,
                    merchant_url=merchant_url,
                    event_bus=event_bus,
                    identity=identity,
                )
            registry[name] = action
        return registry

    def run(self, auto: bool = False) -> None:
        """Start the orchestration kernel and drive all Actions through the full AMP protocol flow."""
        if self._logger:
            self._logger.log_state(
                "ShoppingAgent", "run_start",
                {"auto": auto, "agent_id": self.AGENT_ID},
            )

        self._runtime.loop()
