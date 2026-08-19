"""Intent Parser — rule-based conversion from user input to Command.

Current implementation: rule-based keyword matching. The interface is designed
to allow future replacement with an LLM-based parser without changing callers.
"""
from __future__ import annotations

import re
from typing import Any

from command import (
    Command, EnrollCommand, ShoppingIntentCommand, ConfirmCommand,
    TravelIntentCommand, CancelTravelCommand,
)
from travel_intent import extract_expiry_time, parse_travel_template


# --- Rule definitions ---

_ENROLL_PATTERNS = [
    r"绑定",
    r"bind",
    r"enroll",
    r"add\s*payment",
    r"绑.*钱包",
    r"connect.*wallet",
]

_SHOPPING_PATTERNS = [
    r"(?:帮我|我想|给我)(?:找|搜|买|购)(?:个|一|款)?\s*(.+)",
    r"(?:找|搜索|搜|买)(?:个|一|款)?\s*(.+)",
    r"(?:look|find|search|buy|get)\s+(?:a\s+)?(.+)",
]

# Budget extraction patterns (returns amount in USD dollars)
_BUDGET_PATTERNS = [
    r"(?:under|below|less than|within|budget(?:\s+of)?|max(?:imum)?(?:\s+of)?)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$?\s*(\d+(?:\.\d+)?)\s*(?:or less|at most|max(?:imum)?|budget)",
    r"(?:不超过|低于|以内|以下|预算)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$?\s*(\d+(?:\.\d+)?)\s*(?:刀|美元|块|元)?(?:以内|以下|左右|之内)",
]

_CONFIRM_PATTERNS = [
    r"(确认|确定|好的|ok|yes|confirm|approve|同意|支付|pay)",
]

# Travel cancel pattern (Confirm is handled via /idv/confirm button, not chat)
_CANCEL_TRAVEL_PATTERNS = [
    r"cancel\s+(?:travel|trip|delegation)",
    r"cancel\s+the\s+(?:travel|trip)",
]


def _extract_budget(text: str) -> tuple[float | None, str]:
    """Extract budget amount (in USD dollars) and return (budget, cleaned_text).

    The cleaned_text has the matched budget phrase removed, so downstream
    keyword search is not polluted by budget words like 'under', '50', etc.
    """
    for pattern in _BUDGET_PATTERNS:
        m = re.search(pattern, text)
        if m:
            try:
                budget = float(m.group(1))
                cleaned = text[:m.start()] + text[m.end():]
                return budget, cleaned.strip()
            except (ValueError, IndexError):
                continue
    return None, text


def parse_intent(message: str, state: Any) -> Command:
    """Rule-based: user input → Command object.

    Args:
        message: raw user input text
        state: AgentState (read-only, used for context-aware decisions)

    Returns:
        A Command instance

    Raises:
        ValueError: unrecognized input
    """
    text = message.strip().lower()

    # 1. Check for enrollment intent
    for pattern in _ENROLL_PATTERNS:
        if re.search(pattern, text):
            return EnrollCommand()

    # 2. Check for travel intent (controlled natural language)
    #    Must contain trip/travel + from/to structure; won't match shopping queries.
    travel_intent = parse_travel_template(message.strip())
    if travel_intent is not None:
        return TravelIntentCommand(intent=travel_intent.to_dict())

    # 3. Check for travel cancel (before generic confirm)
    for pattern in _CANCEL_TRAVEL_PATTERNS:
        if re.search(pattern, text):
            return CancelTravelCommand()

    # 4. Check for shopping intent
    for pattern in _SHOPPING_PATTERNS:
        match = re.search(pattern, text)
        if match:
            query = match.group(1).strip()
            if query:
                # Context-aware: guide user through the correct phase sequence
                if not state.token_id:
                    raise ValueError(
                        "Please bind your wallet first. Say 'bind wallet' to get started."
                    )
                # AUTONOMOUS with no mandate yet: let the intent through. The
                # ShoppingIntentCommand sets mandate_requested, which drives the
                # mandate flow first; the purchase resumes automatically after
                # the mandate completes (see inquiry_mandate_session).
                budget, cleaned_query = _extract_budget(query)
                # Use cleaned query (budget/expiry phrases stripped) for keyword search;
                # trim the punctuation those phrases left behind.
                expire_time, cleaned_query = extract_expiry_time(cleaned_query)
                final_query = cleaned_query.strip(" ,.;，。、") or query
                return ShoppingIntentCommand(
                    query=final_query, budget_max=budget, expire_time=expire_time,
                )

    # 5. Check for confirmation intent (generic)
    for pattern in _CONFIRM_PATTERNS:
        if re.search(pattern, text):
            # Phase gate: while IDV is pending, the ONLY valid confirm path
            # is the card button (which calls /idv/confirm BEFORE sending
            # "confirm" to the server). Reject bare chat confirm with guidance.
            if getattr(state, "enrollment_idv_pending", None) or getattr(state, "mandate_idv_pending", None):
                raise ValueError(
                    "Identity verification is in progress. "
                    "Please complete it on the card above."
                )
            return ConfirmCommand()

    raise ValueError(
        f"Cannot parse intent from: '{message}'. "
        f"Supported: bind wallet / find me XX / confirm"
    )
