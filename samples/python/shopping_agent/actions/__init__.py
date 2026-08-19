"""Shopping Agent Actions — Action class implementations for the protocol steps.

Aligned with ARCHITECTURE.md sequence:
- Phase 1: add_payment_method, query_payment_method_list (after IDV)
- Phase 2: create_mandate_session, inquiry_mandate_session (after IDV)
- Phase 3: search_catalog, create_checkout, create_l3, apply_credential, start_payment
"""

from .add_payment_method import AddPaymentMethodAction
from .query_payment_method_list import QueryPaymentMethodListAction
from .create_mandate_session import CreateMandateSessionAction
from .inquiry_mandate_session import InquiryMandateSessionAction
from .search_catalog import SearchCatalogAction
from .create_checkout import CreateCheckoutAction
from .create_l3 import CreateL3Action
from .apply_credential import ApplyCredentialAction
from .start_payment import StartPaymentAction

# Protocol order constant: RuleBasedPlanner selects from allowed_actions in this order
ACTION_ORDER = [
    "add_payment_method",
    "query_payment_method_list",
    "create_mandate_session",
    "inquiry_mandate_session",
    "search_catalog",
    "create_checkout",
    "create_l3",
    "apply_credential",
    "start_payment",
]

# Immediate mode (human-present): search+checkout BEFORE mandate, no L3
ACTION_ORDER_IMMEDIATE = [
    "add_payment_method",
    "query_payment_method_list",
    "search_catalog",
    "create_checkout",
    "create_mandate_session",
    "inquiry_mandate_session",
    "apply_credential",
    "start_payment",
]

ALL_ACTIONS = [
    AddPaymentMethodAction,
    QueryPaymentMethodListAction,
    CreateMandateSessionAction,
    InquiryMandateSessionAction,
    SearchCatalogAction,
    CreateCheckoutAction,
    CreateL3Action,
    ApplyCredentialAction,
    StartPaymentAction,
]

__all__ = ["ACTION_ORDER", "ACTION_ORDER_IMMEDIATE", "ALL_ACTIONS"] + [cls.__name__ for cls in ALL_ACTIONS]
