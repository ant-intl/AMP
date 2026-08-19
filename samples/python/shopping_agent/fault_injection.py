"""FaultProfile — deterministic exception configuration injected at assembly time.

FaultProfile defines predefined fault scenarios, configured into the corresponding
Mock Stub via configure_fault() during the startup assembly phase. Runtime, Planner,
and Action are unaware of fault names.

Usage:
    profile = get_fault_profile("mpp_kyc_fail")
    configure_fault(profile, {"mpp": mpp_stub})
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FaultProfile:
    """Predefined fault configuration."""

    name: str
    target_stub: str       # stub name (mpp / alipayplus / acquirer)
    target_method: str     # method name to trigger the fault
    error_message: str     # exception message


# 3 predefined FaultProfiles (corresponding to the 3 typical protocol phase failures in v0.3 Spec)
_PROFILES: dict[str, FaultProfile] = {
    "mpp_kyc_fail": FaultProfile(
        name="mpp_kyc_fail",
        target_stub="mpp",
        target_method="create_auth_session_for_binding",
        error_message="MPP KYC verification failed: identity check rejected",
    ),
    "alipayplus_intent_reject": FaultProfile(
        name="alipayplus_intent_reject",
        target_stub="alipayplus",
        target_method="create_intent_session",
        error_message="AlipayPlus rejected intent authorization: mandate policy violation",
    ),
    "acquirer_payment_decline": FaultProfile(
        name="acquirer_payment_decline",
        target_stub="acquirer",
        target_method="process_payment",
        error_message="Acquirer declined payment: insufficient funds",
    ),
}


def get_fault_profile(name: str) -> FaultProfile | None:
    """Get a predefined FaultProfile by name. Returns None if not found."""
    return _PROFILES.get(name)


def list_fault_profiles() -> list[str]:
    """Return all available FaultProfile names."""
    return list(_PROFILES.keys())


def configure_fault(profile: FaultProfile, stubs: dict[str, Any]) -> None:
    """Inject fault configuration into the target Mock Stub at assembly time.

    stubs: {"mpp": mpp_instance, "alipayplus": ap_instance, ...}
    Injection method: sets the _fault_profile attribute on the target stub.
    The stub method entry checks this attribute; if it matches, raises RuntimeError.
    """
    target = stubs.get(profile.target_stub)
    if target is None:
        raise ValueError(
            f"FaultProfile '{profile.name}' targets stub '{profile.target_stub}', "
            f"but it was not found in stubs dict. Available: {list(stubs.keys())}"
        )
    target._fault_profile = profile  # noqa: SLF001
