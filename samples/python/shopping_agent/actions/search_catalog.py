"""SearchCatalogAction — Phase 3.1: search the product catalog (HTTP)."""

from __future__ import annotations
import re
import time
from common.http_client import http_post
from orchestrator import AgentState, ActionResult


def _destination_matches(destination: str, product: dict) -> bool:
    """Word-boundary, case-insensitive destination match against product name + description.

    Prevents substring false positives (e.g. 'Singap' must NOT match 'Singapore').
    """
    text = (product.get("name", "") + " " + product.get("description", "")).lower()
    return re.search(r"\b" + re.escape(destination.lower()) + r"\b", text) is not None


def _get_price_cents(product: dict) -> int:
    """Extract price in cents from product, handling both int and dict formats."""
    raw = product.get("price", 0) or 0
    if isinstance(raw, dict):
        return raw.get("cent") or raw.get("value") or 0
    return raw


class SearchCatalogAction:
    """Phase 3.1: search products via HTTP call to Merchant /searchProducts and select the first item."""

    name = "search_catalog"

    def __init__(self, merchant_url: str, event_bus, **_kwargs):
        self._merchant_url = merchant_url
        self._bus = event_bus

    def can_run(self, state: AgentState) -> bool:
        if state.scenario == "IMMEDIATE":
            # IMMEDIATE: run after wallet binding (token_id), before mandate
            return bool(state.token_id) and state.mandate_requested and not state.products
        # AUTONOMOUS: run when purchase_queue has items (multi-item loop)
        queue = getattr(state, "purchase_queue", None) or []
        if queue:
            return bool(state.l1_serialized) and state.purchase_requested and not state.products
        # Fallback: single-item mode (no travel intent — travel uses queue branch)
        return (
            bool(state.l1_serialized) and state.purchase_requested
            and not state.products and not getattr(state, "travel_intent", None)
        )

    def execute(self, state: AgentState) -> ActionResult:
        # Elapsed time spans from when the Agent starts handling this search
        # request to when a product is matched (full agent-side duration).
        t0 = time.perf_counter()
        # Multi-item mode: search for current queue item; single-item: use shopping_query
        queue = getattr(state, "purchase_queue", None) or []
        if queue:
            current_service = queue[0]
            travel_intent = getattr(state, "travel_intent", None) or {}
            destination = travel_intent.get("destination", "")
            query = f"{destination} {current_service}".strip()
        else:
            query = state.shopping_query or "*"

        self._bus.emit(
            phase="checkout",
            from_role="Shopping Agent",
            to_role="Merchant",
            action="searchProducts",
            request={"query": query},
            response={},
        )

        resp = http_post(
            f"{self._merchant_url}/searchProducts",
            json={"query": query},
            timeout=10,
            logger_name="shopping-agent.http-client",
        )
        resp.raise_for_status()
        body = resp.json()

        # Check for wrapped error response
        if "success" in body and not body["success"]:
            error_msg = body.get("errorMessage") or body.get("error") or "unknown"
            raise RuntimeError(f"searchProducts failed: {error_msg}")

        products_data = body.get("products") or body.get("data", [])
        if not products_data and query != "*":
            # Fallback: keyword search matched nothing; retry with a wildcard
            # so the demo flow keeps moving regardless of what the user typed.
            # Emit the retry so the protocol chain shows the fallback happened.
            self._bus.emit(
                phase="checkout",
                from_role="Shopping Agent",
                to_role="Merchant",
                action="searchProducts",
                request={"query": "*"},
                response={},
            )
            resp = http_post(
                f"{self._merchant_url}/searchProducts",
                json={"query": "*"},
                timeout=10,
                logger_name="shopping-agent.http-client",
            )
            resp.raise_for_status()
            body = resp.json()
            if "success" in body and not body["success"]:
                error_msg = body.get("errorMessage") or body.get("error") or "unknown"
                raise RuntimeError(f"searchProducts failed: {error_msg}")
            products_data = body.get("products") or body.get("data", [])
        if not products_data:
            raise RuntimeError("searchProducts returned no products")

        # Candidate count for frontend evidence display: catalog size BEFORE any
        # budget / destination filtering (the search scope the Agent scanned).
        candidates = len(products_data)

        # Filter by remaining budget (budget_max - spent_total, in USD dollars;
        # product price is in cents)
        budget_max = state.budget_max
        spent = getattr(state, "spent_total", 0.0) or 0.0
        if budget_max is not None:
            remaining = budget_max - spent
            remaining_cents = int(remaining * 100)
            products_data = [p for p in products_data if _get_price_cents(p) <= remaining_cents]
            if not products_data:
                # Multi-item: skip this service item (safety net; the pre-check
                # above normally catches budget issues before any purchase)
                if queue:
                    return ActionResult(updates={
                        "purchase_queue": queue[1:],
                        "products": [],
                        "selected_product": None,
                        "match_reasons": [f"Skipped {queue[0]}: exceeds remaining budget (${remaining:.2f} left)"],
                    })
                raise RuntimeError(
                    f"No products within budget ${remaining:.2f}"
                )

        # AUTONOMOUS intent matching: hard constraint filter on destination + service type
        travel_intent = getattr(state, "travel_intent", None)
        match_reasons: list[str] = []
        if travel_intent and state.scenario == "AUTONOMOUS":
            destination = (travel_intent.get("destination") or "").lower()
            # In multi-item mode, only apply service-specific filter for current item
            current_service = queue[0].lower() if queue else ""

            if destination:
                dest_matched = [
                    p for p in products_data
                    if _destination_matches(destination, p)
                ]
                if not dest_matched:
                    raise RuntimeError(
                        f"No matching product: destination '{travel_intent.get('destination')}' "
                        f"not found in catalog"
                    )
                products_data = dest_matched
                match_reasons.append(f"destination: {travel_intent.get('destination')}")

            # Service-type filter: only when searching for that specific service
            if current_service and "hotel" in current_service:
                hotel_matched = [
                    p for p in products_data
                    if "hotel" in (p.get("name", "") + " " + p.get("description", "")).lower()
                ]
                if not hotel_matched:
                    raise RuntimeError(
                        f"No matching product: no hotel found for "
                        f"'{travel_intent.get('destination')}' in catalog"
                    )
                products_data = hotel_matched
                match_reasons.append("hotel included")
            elif current_service and "flight" in current_service:
                flight_matched = [
                    p for p in products_data
                    if "flight" in (p.get("name", "") + " " + p.get("description", "")).lower()
                ]
                if not flight_matched:
                    raise RuntimeError(
                        f"No matching product: no flight found for "
                        f"'{travel_intent.get('destination')}' in catalog"
                    )
                products_data = flight_matched
                match_reasons.append("flight included")

            if budget_max is not None:
                # Reflect the real filter: products were screened against the
                # remaining quota (budget_max - spent), not the original total.
                match_reasons.append(f"within ${remaining:.0f} remaining budget")

        # Budget pre-check for multi-item delegation: AFTER destination/service
        # filtering so prices reflect real matching products. Searches remaining
        # queue items (emitting events for frontend visibility) and blocks the
        # entire purchase if the total exceeds budget.
        if queue and len(queue) > 1 and budget_max is not None and spent == 0.0:
            current_min = min(_get_price_cents(p) for p in products_data)
            estimated: list[tuple[str, int]] = [(queue[0], current_min)]
            # Lookahead: search + filter remaining queue items
            dest_lower = (travel_intent.get("destination") or "").lower() if travel_intent else ""
            for svc in queue[1:]:
                svc_query = f"{destination} {svc}".strip() if destination else svc
                self._bus.emit(
                    phase="checkout",
                    from_role="Shopping Agent",
                    to_role="Merchant",
                    action="searchProducts",
                    request={"query": svc_query},
                    response={},
                )
                svc_resp = http_post(
                    f"{self._merchant_url}/searchProducts",
                    json={"query": svc_query},
                    timeout=10,
                    logger_name="shopping-agent.http-client",
                )
                svc_resp.raise_for_status()
                svc_body = svc_resp.json()
                svc_products = svc_body.get("products") or svc_body.get("data", [])
                # Apply same destination + service-type filter
                if dest_lower:
                    svc_products = [
                        p for p in svc_products
                        if _destination_matches(dest_lower, p)
                    ]
                if "hotel" in svc.lower():
                    svc_products = [
                        p for p in svc_products
                        if "hotel" in (p.get("name", "") + " " + p.get("description", "")).lower()
                    ]
                elif "flight" in svc.lower():
                    svc_products = [
                        p for p in svc_products
                        if "flight" in (p.get("name", "") + " " + p.get("description", "")).lower()
                    ]
                if svc_products:
                    svc_min = min(_get_price_cents(p) for p in svc_products)
                    estimated.append((svc, svc_min))
            # Validate total against budget
            total_cents = sum(price for _, price in estimated)
            budget_cents = int(budget_max * 100)
            if total_cents > budget_cents:
                items_desc = " + ".join(
                    f"{svc} (${price / 100:.0f})" for svc, price in estimated
                )
                raise RuntimeError(
                    f"Budget ${budget_max:.0f} is not enough for all items: "
                    f"{items_desc} = ${total_cents / 100:.0f} total. "
                    f"Please increase your budget or adjust your travel plan."
                )

        self._bus.emit(
            phase="checkout",
            from_role="Merchant",
            to_role="Shopping Agent",
            action="return_catalog",
            request={},
            response={"products": products_data[:2]},
        )

        selected = products_data[0]
        elapsed_ms = round((time.perf_counter() - t0) * 1000)

        # Emit intent-matching result for frontend display
        if match_reasons:
            self._bus.emit(
                phase="checkout",
                from_role="Shopping Agent",
                to_role="Shopping Agent",
                action="intent_product_match",
                request={"constraints": match_reasons},
                response={"selected": selected.get("name", ""), "imageUrl": selected.get("imageUrl", ""), "price": _get_price_cents(selected), "reasons": match_reasons, "elapsed_ms": elapsed_ms, "candidates": candidates},
            )

        return ActionResult(
            updates={
                "products": products_data,
                "selected_product": selected,
                "match_reasons": match_reasons,
            },
        )
