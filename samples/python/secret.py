"""Centralized key-pair management for the AMP demo environment.

Demo-only infrastructure: it lives under ``samples/python`` (not in the shared
``src/python`` library) because holding every role's private key in one process
is a convenience of the local demo, never something a real deployment does —
each role owns and guards its own key material.

Three key-pairs are generated and held in memory:
  - A+ (AlipayPlus platform) — used by network.py for L1/L2 signing & verification
  - Agent — used by the shopping agent for L3 signing
  - MPP — used by mpp/handlers.py for ISP signing

Keys are lazily initialized on first access — no explicit ``init_keys()`` call
is required.  Call ``init_keys()`` once at startup only when you need to
guarantee all key-pairs are ready before any service code runs (e.g. in the
scenario entry-point ``run.py``).

Cross-process key sharing:
  When the ``SECRET_KEY_FILE`` environment variable is set, keys are persisted
to that JSON file on first generation and loaded by subsequent processes so
that all services share the same key material.  The start.sh scripts set this
variable to ``$TEMP_DB_DIR/keys.json`` automatically.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any

import sys, pathlib
_src_python = str(pathlib.Path(__file__).resolve().parents[2] / "src" / "python")
if _src_python not in sys.path:
    sys.path.insert(0, _src_python)

# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

_aplus_private_key: Any = None
_aplus_public_jwk: dict[str, Any] = {}
_aplus_kid: str = ""

_agent_private_key: Any = None
_agent_public_jwk: dict[str, Any] = {}
_agent_kid: str = ""

_mpp_private_key: Any = None
_mpp_public_jwk: dict[str, Any] = {}
_mpp_kid: str = ""

_keys_ready = False
_keys_lock = threading.Lock()


def _ensure_keys() -> None:
    """Lazily generate all three key-pairs on first access."""
    global _keys_ready
    if _keys_ready:
        return
    with _keys_lock:
        if _keys_ready:
            return
        _do_init_keys()
        _keys_ready = True


def _do_init_keys() -> None:
    """Internal: load or generate the key-pairs.

    If ``SECRET_KEY_FILE`` env-var is set and the file exists, keys are loaded
    from it.  If the env-var is set but the file does not exist, newly
    generated keys are persisted there for other processes to share.
    """
    global _aplus_private_key, _aplus_public_jwk, _aplus_kid
    global _agent_private_key, _agent_public_jwk, _agent_kid
    global _mpp_private_key, _mpp_public_jwk, _mpp_kid

    from mandate_chain import generate_key_pair, public_jwk_dict
    from jwcrypto import jwk as _jwk_mod

    key_file = os.environ.get("SECRET_KEY_FILE", "")

    # --- Try loading from shared key file ---
    if key_file and os.path.isfile(key_file):
        with open(key_file, "r") as f:
            data = json.load(f)
        _aplus_private_key = _jwk_mod.JWK(**data["aplus"])
        _aplus_public_jwk = public_jwk_dict(_aplus_private_key)
        _aplus_kid = data.get("aplus_kid", "aplus-key-1")

        _agent_private_key = _jwk_mod.JWK(**data["agent"])
        _agent_public_jwk = public_jwk_dict(_agent_private_key)
        _agent_kid = data.get("agent_kid", "agent-key-1")

        _mpp_private_key = _jwk_mod.JWK(**data["mpp"])
        _mpp_public_jwk = public_jwk_dict(_mpp_private_key)
        _mpp_kid = data.get("mpp_kid", "mpp-key-1")
        return

    # --- Generate fresh key-pairs ---
    _aplus_private_key = generate_key_pair(kid="aplus-key-1")
    _aplus_public_jwk = public_jwk_dict(_aplus_private_key)
    _aplus_kid = "aplus-key-1"

    _agent_private_key = generate_key_pair(kid="agent-key-1")
    _agent_public_jwk = public_jwk_dict(_agent_private_key)
    _agent_kid = "agent-key-1"

    _mpp_private_key = generate_key_pair(kid="mpp-key-1")
    _mpp_public_jwk = public_jwk_dict(_mpp_private_key)
    _mpp_kid = "mpp-key-1"

    # --- Persist to shared key file for cross-process sharing ---
    if key_file:
        os.makedirs(os.path.dirname(key_file) or ".", exist_ok=True)
        data = {
            "aplus": json.loads(_aplus_private_key.export_private()),
            "aplus_kid": _aplus_kid,
            "agent": json.loads(_agent_private_key.export_private()),
            "agent_kid": _agent_kid,
            "mpp": json.loads(_mpp_private_key.export_private()),
            "mpp_kid": _mpp_kid,
        }
        with open(key_file, "w") as f:
            json.dump(data, f, indent=2)


def init_keys() -> None:
    """Explicitly generate all key-pairs.

    Optional — keys are lazily initialized on first accessor call.
    Call this at process startup only when you need keys ready before
    any service code runs (e.g. in scenario ``run.py``).
    """
    global _keys_ready
    with _keys_lock:
        if _keys_ready:
            return
        _do_init_keys()
        _keys_ready = True


# ---------------------------------------------------------------------------
# A+ (AlipayPlus platform) accessors
# ---------------------------------------------------------------------------

def get_aplus_private_key() -> Any:
    """Return the A+ platform EC P-256 private key (JWK object)."""
    _ensure_keys()
    return _aplus_private_key


def get_aplus_public_jwk() -> dict[str, Any]:
    """Return the A+ platform public key as a JWK dict."""
    _ensure_keys()
    return dict(_aplus_public_jwk)


def get_aplus_kid() -> str:
    """Return the A+ platform key ID."""
    _ensure_keys()
    return _aplus_kid


# ---------------------------------------------------------------------------
# Agent accessors
# ---------------------------------------------------------------------------

def get_agent_private_key() -> Any:
    """Return the Agent EC P-256 private key (JWK object)."""
    _ensure_keys()
    return _agent_private_key


def get_agent_public_jwk() -> dict[str, Any]:
    """Return the Agent public key as a JWK dict."""
    _ensure_keys()
    return dict(_agent_public_jwk)


def get_agent_kid() -> str:
    """Return the Agent key ID."""
    _ensure_keys()
    return _agent_kid


# ---------------------------------------------------------------------------
# MPP accessors
# ---------------------------------------------------------------------------

def get_mpp_private_key() -> Any:
    """Return the MPP EC P-256 private key (JWK object)."""
    _ensure_keys()
    return _mpp_private_key


def get_mpp_public_jwk() -> dict[str, Any]:
    """Return the MPP public key as a JWK dict."""
    _ensure_keys()
    return dict(_mpp_public_jwk)


def get_mpp_kid() -> str:
    """Return the MPP key ID."""
    _ensure_keys()
    return _mpp_kid
