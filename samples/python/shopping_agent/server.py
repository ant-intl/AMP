"""Web Demo Server — multi-turn conversation + single-connection streaming entry point.

Adapted for the dev/open_amp multi-process architecture:
- CP, Merchant, Acquirer, and other roles are started by external trigger_server.py
- This service only runs the web frontend proxy + ShoppingAgent multi-turn conversation
- External service addresses are discovered via environment variables

Usage:
  # Start external services first (human_not_present/start.sh)
  # Then start this service:
  python server.py                          # default port 8080
  python server.py --port 9090              # custom port

Environment variables (defaults aligned with start.sh):
  CREDENTIALS_PROVIDER_PORT  — CP service port (default 8082)
  MERCHANT_PORT              — Merchant service port (default 8081)
"""
from __future__ import annotations

import asyncio
import os
import queue
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

# --- Path setup ---
_project_root = Path(__file__).resolve().parents[3]
_src_python = str(_project_root / "src" / "python")
_samples_python = str(_project_root / "samples" / "python")
_this_dir = str(Path(__file__).resolve().parent)
for p in (_src_python, _samples_python, _this_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from events import EventBus
from evidence_logger import ExecutionLogger
from orchestrator import StopReason
from command import apply_command, ShoppingIntentCommand, TravelIntentCommand
from intent_parser import parse_intent
from stream_bus import EventSink, format_sse
from session import TaskSession, get_session, register_session


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class RunBody(BaseModel):
    message: str = ""
    # retry=True: re-run the agent on the existing AgentState without parsing a
    # new user intent (used by the frontend Retry button after a failed turn).
    retry: bool = False


def _intent_example(state) -> str:
    """Example intent shown in purchase-stage guidance. Mirrors the frontend
    Composer placeholder (deriveDefaultText): AUTONOMOUS (human-not-present)
    delegates via a travel plan; IMMEDIATE (human-present) buys a single item."""
    if state.scenario == "AUTONOMOUS" and not state.travel_intent:
        return (
            "I'm planning a 3-day trip from Shanghai to Singapore, leaving on October 1. "
            "Please help me book the flights and hotel, with a total budget of no more than $1,500. "
            "The authorization is valid until October 10, 2026"
        )
    return "buy earbuds under $150"


def _stage_guidance(state) -> dict:
    """Stage-aware guidance shown when the user's input matches no intent for the
    current stage. Never an 'error' — it tells the user where they are and what
    to do next. The 'type' mirrors AgentRuntime._infer_next_input_type so the
    frontend Composer placeholder stays consistent with the guidance."""
    if state.enrollment_idv_pending or state.mandate_idv_pending:
        return {
            "type": "idv",
            "message": "Identity verification is in progress. "
                       "Please complete it on the card above.",
        }
    example = _intent_example(state)
    if state.l1_serialized is not None and not state.purchase_requested:
        return {
            "type": "purchaseIntent",
            "message": f"You have successfully set up your payment method. "
                       f"What would you like to purchase? For example: '{example}'.",
        }
    if state.token_id is not None and not state.mandate_requested:
        return {
            "type": "purchaseIntent",
            "message": f"You have successfully set up your payment method. "
                       f"What would you like to purchase? For example: '{example}'.",
        }
    if not state.enrollment_requested:
        return {
            "type": "enrollment",
            "message": "Welcome! Please set up your payment method. "
                       "Say 'bind wallet' to start.",
        }
    return {
        "type": "user_input",
        "message": "I'm here to help you shop. You can say 'bind wallet', tell me "
                   "what to buy (e.g. 'buy earbuds under $150'), or 'confirm' when prompted.",
    }


def _missing_mandate_expiry_message(expire_time: str | None, state) -> str | None:
    """A human-not-present (AUTONOMOUS) authorization expires when the user says
    it does — the wallet derives the L2 lifetime from that expiry and nothing
    defaults it. Return a prompt while the expiry is still unknown, or None when
    it is known or no new mandate is needed (IMMEDIATE / mandate already held)."""
    if state.scenario == "IMMEDIATE" or state.l1_serialized:
        return None
    if expire_time or state.mandate_expire_time:
        return None
    return ("How long should the authorization stay valid? For example: "
            "'the authorization is valid until October 10, 2026' or 'valid for 7 days'.")


def _incomplete_intent_message(cmd, state) -> str | None:
    """A purchase intent must be fully specified before the mandate flow starts:
    a shopping intent names both a product and a budget, and a human-not-present
    intent also states how long the authorization stays valid. Return a friendly
    prompt for exactly whichever part is missing (None when the intent is
    complete), so the user fills the gap before entering the mandate flow."""
    if isinstance(cmd, TravelIntentCommand):
        return _missing_mandate_expiry_message(cmd.intent.get("expiry_time"), state)
    has_product = bool(cmd.query and cmd.query.strip())
    has_budget = cmd.budget_max is not None
    if not has_product and not has_budget:
        return ("Tell me what you'd like to buy and your budget. "
                "For example: 'buy earbuds under $150'.")
    if not has_budget:
        return (f"What's your budget for the {cmd.query}? "
                f"For example: 'buy {cmd.query} under $150'.")
    if not has_product:
        return "Which product did you have in mind? For example: 'buy earbuds under $150'."
    return _missing_mandate_expiry_message(cmd.expire_time, state)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="AMP Shopping Agent Web Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
from common.middleware import HttpLoggingMiddleware
app.add_middleware(HttpLoggingMiddleware, logger_name="shopping-agent.http")

_log_dir = str(Path(__file__).resolve().parent / ".logs")
Path(_log_dir).mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/config")
async def config():
    """Expose the active demo scenario so the frontend can display it.

    Scenario is derived from the FLOW environment variable, the same source
    used by POST /task when constructing the ShoppingAgent.
    """
    flow = os.environ.get("FLOW", "human_not_present")
    scenario = "IMMEDIATE" if flow == "human_present" else "AUTONOMOUS"
    return {"scenario": scenario}


@app.post("/idv/confirm")
async def idv_confirm(body: dict) -> JSONResponse:
    """Frontend → Server → MPP: User completed biometric IDV.

    In production, the user completes biometric verification (fingerprint /
    face-id) directly inside the MPP wallet app, and MPP asynchronously
    notifies the platform. In this Sample there is no real wallet app, so we
    **mock** that step: the Shopping Agent server directly calls MPP's
    /completeIdv endpoint on behalf of the user, simulating a successful
    biometric result. MPP /completeIdv blocks ~5 s to mimic real biometric
    latency.

    After MPP confirms, this handler updates Agent state (clears the pending
    IDV flag) to unblock the next orchestrator turn.

    session_id is optional: if omitted, inferred from agent state.
    """
    import httpx

    task_id = body.get("taskId", "")
    session_id = body.get("sessionId", "")

    # Resolve session_id from agent state if not provided
    session = get_session(task_id) if task_id else None
    if not session_id and session:
        state = session.agent._runtime._state
        session_id = state.enrollment_idv_pending or state.mandate_idv_pending or ""
    if not session_id:
        return JSONResponse({"success": False, "error": "No pending IDV session"}, status_code=400)

    # Resolve MPP address
    mpp_port = os.environ.get("MPP_PORT", "8899")
    mpp_url = f"http://localhost:{mpp_port}/mpp"

    # Mock: directly call MPP /completeIdv to simulate the user finishing
    # biometric verification inside the wallet app (no real biometric here).
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{mpp_url}/completeIdv", json={"authSessionId": session_id})
            resp.raise_for_status()
            mpp_body = resp.json()
    except Exception as exc:
        return JSONResponse({"success": False, "error": f"MPP completeIdv failed: {exc}"}, status_code=502)

    # MPP responds in Alipay+ style: {"result": {"resultCode", "resultStatus", "resultMessage"}, ...}
    result_info = mpp_body.get("result") or {}
    result_status = result_info.get("resultStatus", "")

    if result_status != "S":
        # Tolerate "already completed" case: if MPP session is already in SUCCESS
        # state (e.g. auto-complete raced with manual confirm), treat as pass.
        result_msg = result_info.get("resultMessage", "")
        if "SUCCESS" not in result_msg:
            return JSONResponse({"success": False, "error": result_msg or "unknown"}, status_code=502)

    # Update Agent state: clear pending, mark done
    if session:
        state = session.agent._runtime._state
        if state.enrollment_idv_pending == session_id:
            state.enrollment_idv_pending = None
            state.enrollment_idv_done = True
        elif state.mandate_idv_pending == session_id:
            state.mandate_idv_pending = None

    return JSONResponse({"success": True, "idvResult": "PASS"})


@app.post("/task")
async def create_task() -> JSONResponse:
    """Create a new TaskSession and return the task_id. Phase gates are initialized to False."""
    task_id = uuid.uuid4().hex[:12]

    # Resolve external service addresses (aligned with start.sh environment variables)
    cp_port = os.environ.get("CREDENTIALS_PROVIDER_PORT", "8082")
    merchant_port = os.environ.get("MERCHANT_PORT", "8081")
    cp_url = f"http://localhost:{cp_port}/credential-provider"
    # Merchant routes are served at root (no /merchant prefix) since the
    # merchant service rewrite (searchProducts/startCheckout/startPayment).
    merchant_url = f"http://localhost:{merchant_port}"

    bus = EventBus()
    logger = ExecutionLogger(log_dir=_log_dir)
    logger.start_session(mode="web")

    # Create ShoppingAgent (calls external CP / Merchant services)
    # interactive_idv=True: IDV steps pause the turn; User completes biometric at MPP.
    # scenario from FLOW env: human_present → IMMEDIATE, else AUTONOMOUS.
    flow = os.environ.get("FLOW", "human_not_present")
    scenario = "IMMEDIATE" if flow == "human_present" else "AUTONOMOUS"
    from agent import ShoppingAgent
    agent = ShoppingAgent(
        merchant_url=merchant_url,
        cp_url=cp_url,
        event_bus=bus,
        logger=logger,
        interactive_idv=True,
        scenario=scenario,
    )

    # Phase gates: default to False in web mode; Commands unlock them turn by turn
    runtime = agent._runtime
    runtime._state.enrollment_requested = False
    runtime._state.mandate_requested = False
    runtime._state.purchase_requested = False

    # Scenario mode: set IMMEDIATE when FLOW=human_present (start.sh exports this)
    flow = os.environ.get("FLOW", "")
    if flow == "human_present":
        runtime._state.scenario = "IMMEDIATE"

    session = TaskSession(
        task_id=task_id,
        agent=agent,
        state=runtime._state,
    )
    register_session(session)

    return JSONResponse({
        "taskId": task_id,
        "status": "idle",
        "message": "Task created. Send POST /task/{task_id}/run with a message.",
    })


@app.post("/task/{task_id}/run")
async def run_task(task_id: str, body: RunBody) -> StreamingResponse:
    """Multi-turn conversation entry: parse intent → apply Command → Runtime continuous execution → SSE stream."""
    session = get_session(task_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            session.status = "running"

            # 1-2. Intent parsing → Command → apply (skipped on retry: the
            # AgentState already holds the intent from the original turn, so the
            # Runtime simply re-runs from the failed step).
            if not body.retry:
                try:
                    cmd = parse_intent(body.message, session.state)
                except ValueError:
                    # Input matches no intent for the current stage. Reply with
                    # stage-aware guidance (not an error): tell the user where
                    # they are and what to do next.
                    detail = _stage_guidance(session.state)
                    detail["scenario"] = session.state.scenario
                    session.status = "waiting"
                    # Stop envelope mirrors StopReason.to_dict: {"state": kind, kind: detail}
                    yield format_sse("stop", {"state": "input_required", "input_required": detail})
                    return

                # A purchase intent must be fully specified before the mandate
                # flow starts (product + budget, plus the authorization expiry
                # when the user won't be present). If anything is missing, ask
                # for exactly that and do NOT apply the command — never enter
                # the mandate flow half-specified.
                if isinstance(cmd, (ShoppingIntentCommand, TravelIntentCommand)):
                    missing = _incomplete_intent_message(cmd, session.state)
                    if missing:
                        session.status = "waiting"
                        yield format_sse("stop", {"state": "input_required", "input_required": {
                            "type": "purchaseIntent",
                            "message": missing,
                            "scenario": session.state.scenario,
                        }})
                        return

                # 2. apply Command
                apply_command(cmd, session.state)
                session.add_message("user", body.message)

            # 3. EventSink
            sink = EventSink()

            # 4. Wire sink to Runtime + Actions
            runtime = session.agent._runtime
            runtime._event_bus = sink
            for action in runtime._registry.values():
                if hasattr(action, "_bus"):
                    action._bus = sink

            # 5. Agent thread
            loop = asyncio.get_running_loop()
            stop_reason_holder: list[StopReason | None] = [None]

            def _run_agent():
                try:
                    sr = runtime.loop_with_yield(sink)
                    stop_reason_holder[0] = sr
                except Exception as exc:
                    stop_reason_holder[0] = StopReason(kind="failed", detail={"error": str(exc)})
                finally:
                    sink.close()

            thread = threading.Thread(target=_run_agent, daemon=True)
            thread.start()

            # 6. Read from Queue, yield SSE
            q = sink.event_queue
            while True:
                try:
                    item = await loop.run_in_executor(
                        None, lambda: q.get(block=True, timeout=30)
                    )
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue

                if item is None:
                    break

                session.add_evidence(item)
                yield format_sse("action", item)

            # 7. Join thread
            thread.join(timeout=5)

            # 8. Send StopReason
            sr = stop_reason_holder[0]
            if sr is None:
                sr = StopReason(kind="failed", detail={"error": "Agent did not return StopReason"})

            # Multi-purchase: after successful payment, reset purchase-specific
            # state so the user can initiate another purchase cycle.
            if sr.kind == "completed":
                st = session.state
                st.products = []
                st.selected_product = None
                st.checkout_id = None
                st.checkout_amount = None
                st.checkout_currency = None
                st.checkout_merchant_id = None
                st.l3_serialized = None
                st.payment_token = None
                st.paid = False
                st.transaction_id = None
                st.shopping_query = ""
                st.budget_max = None
                st.purchase_requested = False
                # IMMEDIATE mandates are single-use (bound to specific checkout
                # hash + exact amount); after payment the mandate is CLOSED.
                # Clear mandate state so the next purchase creates a fresh one.
                # AUTONOMOUS mandates have reusable budget — keep them alive.
                if st.scenario == "IMMEDIATE":
                    st.mandate_session_id = None
                    st.mandate_id = None
                    st.l1_serialized = None
                    st.l2_serialized = None
                    st.mandate_idv_pending = None
                sr.detail["next"] = "purchase_again"
                sr.detail["message"] = "What else would you like to buy?"

            session.status = "waiting"  # always ready for next turn (multi-purchase)
            session.add_message("agent", f"[{sr.kind}]", detail=sr.detail)

            yield format_sse("stop", sr.to_dict())

        except Exception as exc:
            yield format_sse("stop", {"state": "failed", "failed": {"error": str(exc)}})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/state/{task_id}")
async def get_state(task_id: str) -> JSONResponse:
    """Return a TaskSession state snapshot."""
    session = get_session(task_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse({
        "taskId": task_id,
        "status": session.status,
        "conversation": session.conversation,
        "evidenceCount": len(session.evidence),
        "agentState": session.state.to_dict() if hasattr(session.state, "to_dict") else {},
    })


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def main(port: int = 8080, host: str = "0.0.0.0") -> None:
    import uvicorn

    cp_port = os.environ.get("CREDENTIALS_PROVIDER_PORT", "8082")
    merchant_port = os.environ.get("MERCHANT_PORT", "8081")

    from common.log_config import setup_logging, uvicorn_log_config

    logger = setup_logging("shopping-agent")
    logger.info("shopping-agent service started on http://%s:%d", host, port)
    logger.info("POST /task                    — create task")
    logger.info("POST /task/{task_id}/run      — run one turn (SSE)")
    logger.info("GET  /state/{task_id}         — session snapshot")
    logger.info("External CP:      http://localhost:%s", cp_port)
    logger.info("External Merchant: http://localhost:%s/merchant", merchant_port)

    uvicorn.run(app, host=host, port=port, log_level="warning", log_config=uvicorn_log_config())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    main(port=args.port, host=args.host)
