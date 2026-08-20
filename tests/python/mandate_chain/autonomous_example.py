"""AMP - Autonomous (Human-Not-Present) 3-Layer Mandate Chain Example.

Demonstrates the human-not-present flow:
  1. A+ creates L1 (certifies ISP identity, binds ISP public key)
  2. ISP creates L2 (user authorization + intent constraints, binds Agent key)
  3. Agent creates L3 (purchase decision within constraints)
  4. Payment Network (A+) verifies full 3-layer chain

Run:
  cd tests/python/mandate_chain
  python autonomous_example.py
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
    create_autonomous_layer2,
    create_checkout_layer3,
    verify_agent_chain,
    verify_sd_hash_binding,
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
# Autonomous (Human-Not-Present) 3-Layer Flow
# ==============================================================================


class AutonomousExample:
    """Human-not-present 3-layer mandate chain: L1 -> L2(AUTONOMOUS) -> L3.

    Flow:
      1. A+ creates L1 (certifies ISP identity, binds ISP public key)
      2. ISP creates L2 (user authorization + intent constraints, binds Agent key)
      3. Agent creates L3 (purchase decision within constraints)
      4. Payment Network (A+) verifies full 3-layer chain
    """

    def run(self):
        print_section("AMP - Autonomous 3-Layer Mandate Chain")

        # -- Key Generation --
        print_step(0, "Generate keys for all parties")
        self.alipayplus_key = generate_key_pair(kid="a+_kid_001")
        self.isp_key = generate_key_pair(kid="isp_kid_001")
        self.agent_key = generate_key_pair(kid="agent_kid_001")
        print(f"  A+ Key ID: {self.alipayplus_key['kid']}")
        print(f"  ISP Key ID: {self.isp_key['kid']}")
        print(f"  Agent Key ID: {self.agent_key['kid']}")

        # -- Step 1: L1 --
        self._create_l1()

        # -- Step 2: L2 AUTONOMOUS --
        self._create_l2()

        # -- Step 3: Verify L2 binding --
        print_step(3, "Verify L2 is bound to L1 via sd_hash")
        l2_valid = verify_sd_hash_binding(self.l2_serialized, self.l1_serialized)
        print(f"  L2.sd_hash == B64U(SHA-256(L1)): {l2_valid}")
        assert l2_valid, "L2 sd_hash binding failed!"

        # -- Step 4: L3 --
        self._create_l3()

        # -- Step 5: Verify L3 binding --
        print_step(5, "Verify L3 is bound to L2 via sd_hash")
        l3_valid = verify_sd_hash_binding(self.l3_serialized, self.l2_serialized)
        print(f"  L3.sd_hash == B64U(SHA-256(L2)): {l3_valid}")
        assert l3_valid, "L3 sd_hash binding failed!"

        # -- Step 6: Full chain verification --
        self._verify_chain()

        # -- Step 7: Summary --
        self._print_summary()

        # -- Step 8: Tamper detection --
        self._tamper_detection()

        return True

    def _create_l1(self):
        print_step(1, "A+ creates Layer 1 (certifies ISP identity)")

        self.l1_serialized = create_alipayplus_layer1(
            sub="user_2088_alice_001",
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
        print_step(2, "ISP creates Layer 2 AUTONOMOUS (user authorization + intent)")

        intent = {
            "raw": "Help me buy a wireless headphone within 500 USD from Alibaba",
            "desc": "Purchase wireless headphone with budget constraint",
            "expiry_time": "2026-07-20T23:59:59+08:00",
            "constraints": {
                "budget_amount": {"value": "50000", "currency": "USD"},
                "merchant_name_list": ["Alibaba"],
                "merchant_mcc_list": ["5732"],
            },
        }

        token_info = {
            "token_unique_reference": "TKN_REF_2088_ALICE_001",
            "token_status": "ACTIVE",
            "user_login_id": "852-****0417",
            "wallet_name": "AlipayHK",
        }

        mandate_info = {
            "mandate_id": "MANDATE_20260710_001",
            "mandate_type": "AUTONOMOUS",
            "mandate_status": "ACTIVE",
            "mandate_expiry_time": "2026-08-10T23:59:59+08:00",
        }

        self.l2_serialized = create_autonomous_layer2(
            l1_serialized=self.l1_serialized,
            idv_result="true",
            idv_time="2026-07-10T10:30:00+08:00",
            intent=intent,
            token_info=token_info,
            mandate_info=mandate_info,
            agent_public_key=self.agent_key,
            private_key=self.isp_key,
            kid="isp_kid_001",
            aud="https://www.alipayplus.com",
            nonce="L2_NONCE_abc123def456",
            exp_seconds=30 * 24 * 3600,
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
            "cnf": {"jwk": {"kty": "EC", "crv": "P-256", "kid": "agent_kid_001", "...": "..."}},
            "_sd_alg": l2_payload.get("_sd_alg"),
            "_sd": f"[{len(l2_payload.get('_sd', []))} hashes]",
        })
        print(f"  L2 has {len(l2_disclosures)} selective disclosures: intent, token_info, mandate_info")
        print(f"\n  [L2 Full Serialized Token]")
        print(f"  {self.l2_serialized}")

    def _create_l3(self):
        print_step(4, "Agent creates Layer 3 (purchase decision within constraints)")

        checkout = {
            "total_amount": {"value": "29900", "currency": "USD"},
            "merchant": {
                "reference_merchant_id": "MERCHANT_ALIBABA_001",
                "merchant_name": "Alibaba",
                "merchant_mcc": "5732",
                "merchant_website_url": "https://www.alibaba.com",
            },
            "goods": [
                {
                    "goods_name": "Demo Wireless Headphone",
                    "goods_unit_amount": {"value": "29900", "currency": "USD"},
                    "goods_quantity": "1",
                }
            ],
            "reference_checkout_id": "CHECKOUT_20260710_XM5_001",
        }

        self.l3_serialized = create_checkout_layer3(
            l2_serialized=self.l2_serialized,
            checkout=checkout,
            private_key=self.agent_key,
            kid="agent_kid_001",
            aud="https://www.alipayplus.com",
            nonce="L3_NONCE_xyz789ghi012",
            exp_seconds=300,
        )

        l3_header = parse_jwt_header(self.l3_serialized)
        l3_payload = parse_jwt_payload(self.l3_serialized)
        l3_disclosures = parse_sd_jwt_disclosures(self.l3_serialized)

        print_json("L3 Header", l3_header)
        print_json("L3 Payload (visible claims)", {
            "nonce": l3_payload.get("nonce"),
            "aud": l3_payload.get("aud"),
            "iat": l3_payload.get("iat"),
            "exp": l3_payload.get("exp"),
            "sd_hash": l3_payload.get("sd_hash", "")[:32] + "...",
            "_sd_alg": l3_payload.get("_sd_alg"),
            "_sd": f"[{len(l3_payload.get('_sd', []))} hashes]",
        })
        print(f"  L3 has {len(l3_disclosures)} selective disclosure: checkout")
        print(f"\n  [L3 Full Serialized Token]")
        print(f"  {self.l3_serialized}")

    def _verify_chain(self):
        print_step(6, "Payment Network verifies complete 3-layer chain")

        result = verify_agent_chain(
            l1_serialized=self.l1_serialized,
            l2_serialized=self.l2_serialized,
            l3_serialized=self.l3_serialized,
            alipayplus_public_key=self.alipayplus_key,
        )

        print(f"  Chain valid: {result['valid']}")
        if result["valid"]:
            print("  ✓ L1 signature verified (A+ public key)")
            print("  ✓ L2 sd_hash binding verified (L2 → L1)")
            print("  ✓ L2 signature verified (ISP public key from L1.cnf.jwk)")
            print("  ✓ L3 sd_hash binding verified (L3 → L2)")
            print("  ✓ L3 signature verified (Agent public key from L2.cnf.jwk)")
        else:
            print(f"  Errors: {result['errors']}")

        assert result["valid"], f"Chain verification failed: {result['errors']}"

    def _print_summary(self):
        print_step(7, "Chain Summary")
        print("""
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Verifiable Mandate Chain                      │
  ├─────────────────────────────────────────────────────────────────┤
  │  L1 (A+)                                                        │
  │    iss: alipayplus.com                                          │
  │    sub: user_2088_alice_001                                     │
  │    cnf: ISP public key (kid=isp_kid_001)                        │
  │    isp_type: MPP, isp_name: ALIPAY_HK                          │
  │    Signed by: A+ private key                                    │
  ├─────────────────────────────────────────────────────────────────┤
  │  L2 (ISP) - AUTONOMOUS                                         │
  │    sd_hash: B64U(SHA-256(L1)) ← chain binding                  │
  │    idv_result: true, idv_time: 2026-07-10T10:30:00+08:00       │
  │    mode: AUTONOMOUS                                             │
  │    cnf: Agent public key (kid=agent_kid_001)                    │
  │    [SD] intent: budget 500 USD, merchants: Alibaba       │
  │    [SD] token_info: TKN_REF_2088_ALICE_001                      │
  │    [SD] mandate_info: MANDATE_20260710_001                      │
  │    Signed by: ISP private key                                   │
  ├─────────────────────────────────────────────────────────────────┤
  │  L3 (Agent)                                                     │
  │    sd_hash: B64U(SHA-256(L2)) ← chain binding                  │
  │    [SD] checkout:                                               │
  │      total_amount: 299.00 USD                                   │
  │      merchant: Alibaba (MCC: 5732)                               │
  │      goods: Demo Wireless Headphone                 │
  │    Signed by: Agent private key                                 │
  └─────────────────────────────────────────────────────────────────┘
""")

    def _tamper_detection(self):
        print_step(8, "Demonstrate tamper detection")

        fake_key = generate_key_pair(kid="fake_key")
        tampered_result = verify_agent_chain(
            l1_serialized=self.l1_serialized,
            l2_serialized=self.l2_serialized,
            l3_serialized=self.l3_serialized,
            alipayplus_public_key=fake_key,
        )
        print(f"  Verify with wrong A+ key: valid={tampered_result['valid']}")
        print(f"  Error: {tampered_result['errors'][0]}")


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    AutonomousExample().run()
    print_section("Autonomous chain verification passed!")
