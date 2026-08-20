"""AMP - Immediate (Human-Present) 2-Layer Mandate Chain Example.

Demonstrates the human-present flow:
  1. A+ creates L1 (certifies ISP identity, binds ISP public key)
  2. ISP creates L2 with final checkout (user present, no agent delegation)
  3. Payment Network (A+) verifies 2-layer chain (no L3 needed)

Run:
  cd tests/python/mandate_chain
  python immediate_example.py
"""

import json
import sys
from pathlib import Path

# Add src/python to path so mandate_chain package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "python"))

from mandate_chain import (
    generate_key_pair,
    parse_jwt_header,
    parse_jwt_payload,
    parse_sd_jwt_disclosures,
    create_alipayplus_layer1,
    create_immediate_layer2,
    verify_credential_chain,
    verify_sd_hash_binding,
    verify_signature,
)


# ==============================================================================
# Helper: Pretty print
# ==============================================================================


def print_section(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_step(num: int, description: str):
    print(f"\n--- Step {num}: {description} ---")


def print_json(label: str, data: dict, indent: int = 2):
    print(f"  {label}:")
    print(f"    {json.dumps(data, indent=indent, ensure_ascii=False)}")


# ==============================================================================
# Immediate (Human-Present) 2-Layer Flow
# ==============================================================================


class ImmediateExample:
    """Human-present 2-layer mandate chain: L1 -> L2(IMMEDIATE), no L3.

    Flow:
      1. A+ creates L1 (certifies ISP identity, binds ISP public key)
      2. ISP creates L2 with final checkout (user present, no agent delegation)
      3. Payment Network (A+)  verifies 2-layer chain (no L3 needed)
    """

    def run(self):
        print_section("AMP - Immediate 2-Layer Mandate Chain")

        # -- Key Generation --
        print_step(0, "Generate keys for all parties")
        self.alipayplus_key = generate_key_pair(kid="a+_kid_001")
        self.isp_key = generate_key_pair(kid="isp_kid_001")
        print(f"  A+ Key ID: {self.alipayplus_key['kid']}")
        print(f"  ISP Key ID: {self.isp_key['kid']}")
        print(f"  (No Agent key needed - user is present)")

        # -- Step 1: L1 --
        self._create_l1()

        # -- Step 2: L2 IMMEDIATE --
        self._create_l2()

        # -- Step 3: Verify chain --
        self._verify_chain()

        # -- Step 4: Summary --
        self._print_summary()

        return True

    def _create_l1(self):
        print_step(1, "A+ creates Layer 1 (certifies ISP identity)")

        self.l1_serialized = create_alipayplus_layer1(
            sub="user_2088_bob_002",
            isp_public_key=self.isp_key,
            isp_type="MPP",
            isp_name="ALIPAY_HK",
            private_key=self.alipayplus_key,
            kid="a+_kid_001",
            iss="alipayplus.com",
            exp_seconds=365 * 24 * 3600,
        )

        l1_header = parse_jwt_header(self.l1_serialized)
        l1_payload = parse_jwt_payload(self.l1_serialized)

        print_json("L1 Header", l1_header)
        print_json("L1 Payload", {
            "iss": l1_payload["iss"],
            "sub": l1_payload["sub"],
            "iat": l1_payload["iat"],
            "exp": l1_payload["exp"],
            "cnf": {"jwk": {"kty": "EC", "crv": "P-256", "kid": "isp_kid_001", "x": "...", "y": "..."}},
            "isp_type": l1_payload["isp_type"],
            "isp_name": l1_payload["isp_name"],
        })
        print(f"  L1 has 0 disclosures (MUST NOT have _sd or _sd_alg)")
        print(f"\n  [L1 Full Serialized Token]")
        print(f"  {self.l1_serialized}")

    def _create_l2(self):
        print_step(2, "ISP creates Layer 2 IMMEDIATE (user present, final checkout)")

        intent = {
            "raw": "Buy Apple AirPods Pro 2 from Alibaba",
            "desc": "User confirmed purchase of AirPods Pro 2",
        }

        token_info = {
            "token_unique_reference": "TKN_REF_2088_BOB_002",
            "token_status": "ACTIVE",
            "user_login_id": "852-****1234",
            "wallet_name": "AlipayHK",
        }

        mandate_info = {
            "mandate_id": "MANDATE_20260710_002",
            "mandate_type": "IMMEDIATE",
            "mandate_status": "ACTIVE",
            "mandate_expiry_time": "2026-07-10T11:15:00+08:00",
        }

        checkout = {
            "total_amount": {"value": "15900", "currency": "USD"},
            "merchant": {
                "reference_merchant_id": "MERCHANT_ALIBABA_001",
                "merchant_name": "Alibaba",
                "merchant_mcc": "5732",
                "merchant_website_url": "https://www.alibaba.com",
            },
            "goods": [
                {
                    "goods_name": "Apple AirPods Pro 2",
                    "goods_unit_amount": {"value": "15900", "currency": "USD"},
                    "goods_quantity": "1",
                }
            ],
            "reference_checkout_id": "CHECKOUT_20260710_AIRPODS_001",
        }

        self.l2_serialized = create_immediate_layer2(
            l1_serialized=self.l1_serialized,
            idv_result="true",
            idv_time="2026-07-10T11:00:00+08:00",
            intent=intent,
            token_info=token_info,
            mandate_info=mandate_info,
            checkout=checkout,
            private_key=self.isp_key,
            kid="isp_kid_001",
            aud="https://www.alipayplus.com",
            nonce="L2_NONCE_imm_789xyz",
            exp_seconds=900,
        )

        l2_header = parse_jwt_header(self.l2_serialized)
        l2_payload = parse_jwt_payload(self.l2_serialized)
        l2_disclosures = parse_sd_jwt_disclosures(self.l2_serialized)

        print_json("L2 Header", l2_header)
        print_json("L2 Payload (visible claims)", {
            "nonce": l2_payload.get("nonce"),
            "aud": l2_payload.get("aud"),
            "iat": l2_payload.get("iat"),
            "exp": l2_payload.get("exp"),
            "sd_hash": l2_payload.get("sd_hash", "")[:32] + "...",
            "idv_result": l2_payload.get("idv_result"),
            "idv_time": l2_payload.get("idv_time"),
            "mode": l2_payload.get("mode"),
            "_sd_alg": l2_payload.get("_sd_alg"),
            "_sd": f"[{len(l2_payload.get('_sd', []))} hashes]",
        })
        print(f"  L2 has NO cnf (no agent delegation): {'cnf' not in l2_payload}")
        print(f"  L2 has {len(l2_disclosures)} disclosures: intent, token_info, mandate_info, checkout")
        print(f"\n  [L2 Full Serialized Token]")
        print(f"  {self.l2_serialized}")

    def _verify_chain(self):
        print_step(3, "Payment Network verifies 2-layer chain")

        result = verify_credential_chain(
            l1_serialized=self.l1_serialized,
            l2_serialized=self.l2_serialized,
            alipayplus_public_key=self.alipayplus_key,
        )

        print(f"  Chain valid: {result['valid']}")
        if result["valid"]:
            print("  ✓ L1 signature verified (A+ public key)")
            print("  ✓ L2 sd_hash binding verified (L2 → L1)")
            print("  ✓ L2 signature verified (ISP public key from L1.cnf.jwk)")
            print("  ✓ Human-present 2-layer chain verified (no L3 needed)")
        else:
            print(f"  Errors: {result['errors']}")

        assert result["valid"], f"Chain verification failed: {result['errors']}"

    def _print_summary(self):
        print_step(4, "Chain Summary")
        print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Verifiable Mandate Chain                      │
  ├─────────────────────────────────────────────────────────────────┤
  │  L1 (A+)                                                        │
  │    iss: alipayplus.com                                          │
  │    sub: user_2088_bob_002                                       │
  │    cnf: ISP public key (kid=isp_kid_001)                        │
  │    isp_type: MPP, isp_name: ALIPAY_HK                          │
  │    Signed by: A+ private key                                    │
  ├─────────────────────────────────────────────────────────────────┤
  │  L2 (ISP) - IMMEDIATE                                          │
  │    sd_hash: B64U(SHA-256(L1)) ← chain binding                  │
  │    idv_result: true, idv_time: 2026-07-10T11:00:00+08:00       │
  │    mode: IMMEDIATE                                              │
  │    NO cnf (user is present, no agent delegation)                │
  │    [SD] intent: Buy AirPods Pro 2 from Alibaba                  │
  │    [SD] token_info: TKN_REF_2088_BOB_002                        │
  │    [SD] mandate_info: MANDATE_20260710_002                      │
  │    [SD] checkout: 159.00 USD, Alibaba, AirPods Pro 2            │
  │    Signed by: ISP private key                                   │
  ├─────────────────────────────────────────────────────────────────┤
  │  No L3 — user signed final values directly                      │
  └─────────────────────────────────────────────────────────────────┘
""")


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    ImmediateExample().run()
    print_section("Immediate chain verification passed!")
