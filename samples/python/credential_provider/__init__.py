"""AMP Credential Provider — Integrator reference service.

Bridges shopping-agent (upstream) and AlipayPlus (downstream) for wallet
enrollment, mandate authorization, and payment credential issuance.

Call chain:
    shopping-agent -> credential-provider (integrator) -> AlipayPlus

=== Contract Keys ===

session_id: CP-generated (cps-xxx), returned by every initiate endpoint and
required by every follow-up call. The downstream AlipayPlus session id is an
internal mapping (cp_session.downstream_session_id) and never acts as the
upstream contract key.

status: PENDING_IDV | COMPLETED | FAILED. addPaymentMethod always uses
sync blocking mode (waits for callback). createMandateSession supports
both sync (CLI) and async (web, defer_idv=true) modes.

=== Interfaces (CP Contract, all POST) ===

Interface 1: POST /credential-provider/addPaymentMethod
    Direction: Shopping Agent → CP
    Purpose: Trigger ENROLLMENT flow; L1 arrives via /credential-provider/notifyAuthorization
    Internal: CP → AlipayPlus /createAuthorization (ENROLLMENT)
    Request: {wallet_name, agent_id?}
    Response: {success, session_id, status,
               token_id?              # when status == COMPLETED
               idv?: {auth_url, auth_session_id}}  # when status == PENDING_IDV

Interface 2: POST /credential-provider/queryPaymentMethodList
    Direction: Shopping Agent → CP
    Purpose: Query bound payment methods — always returns a collection
    Request: {session_id?, wallet_name?, token_id?}   # all filters optional
             # session_id narrows to the token produced by that enrollment session
    Response: {success, payment_methods: [{token_id, wallet_name, l1_serialized, gmt_create}]}

Interface 3: POST /credential-provider/notifyAuthorization
    Direction: AlipayPlus → CP
    Purpose: Unified callback when authorization completes
    Request: {session_id, auth_context?, token_id?, l1_serialized?,
              mandate_id?, l2_serialized?, mandate_type?}
              # session_id here is the AlipayPlus session; CP maps it back
              # to its own cp session via downstream_session_id
    Response: {success}

Interface 4: POST /credential-provider/createMandateSession
    Direction: Shopping Agent → CP
    Purpose: Trigger MANDATE flow; L2 arrives via /credential-provider/notifyAuthorization
    Internal: CP → AlipayPlus /createAuthorization (MANDATE)
    Request: {token_id,            # REQUIRED — from queryPaymentMethodList
              agent_id?, intent_raw,
              constraints?, checkout?, defer_idv}
              # agent_public_jwk NOT passed via API; obtained from common.secret
    Response: {success, session_id, status,
               mandate_id?           # when status == COMPLETED
               idv?: {auth_url, auth_session_id}}  # when status == PENDING_IDV

Interface 5: POST /credential-provider/inquiryMandateSession
    Direction: Shopping Agent → CP
    Purpose: Query mandate session state — strict lookup by cp session_id
    Request: {session_id}          # REQUIRED — from createMandateSession
    Response: {success, session_id, status,
               mandate_id?, mandate_type?, token_id?, l1_serialized?, l2_serialized?}
               # serialized fields present only when status == COMPLETED

Interface 6: (outbound) /createAuthorization
    Direction: CP → AlipayPlus (NOT an HTTP endpoint on CP)
    Implemented in: client.py (AlipayPlusClient.create_authorization)

Interface 7: POST /credential-provider/applyCredential
    Direction: Shopping Agent → CP
    Purpose: Submit L1+L2(+L3) chain for payment token issuance
    Internal: CP resolves token_id + mandate_id from the mandate session,
              then CP → AlipayPlus /applyCredential → chain verification → token
    Request: {session_id,          # REQUIRED — the mandate session
              l1_serialized, l2_serialized, l3_serialized?, checkout?}
    Response: {success, payment_token, mandate_type}

=== Call Sequence (Happy Path) ===

1. Agent calls POST /credential-provider/addPaymentMethod
   → CP generates cps session, creates ENROLLMENT authorization on AlipayPlus
   → MPP completes IDV out-of-band → AlipayPlus issues L1
   → AlipayPlus calls back CP /credential-provider/notifyAuthorization {token_id, l1_serialized}
   → CP stores the binding, marks the session COMPLETED
   → Agent keeps the returned session_id

2. Agent calls POST /credential-provider/queryPaymentMethodList {session_id}
   → CP returns the payment method bound by that enrollment session

3. Agent calls POST /credential-provider/createMandateSession {token_id, ...}
   → CP generates a new cps session, creates MANDATE session on AlipayPlus
     (passing token_id + intent; agent_public_jwk obtained from common.secret)
   → MPP generates L2 out-of-band → AlipayPlus verifies L2, creates mandate
   → AlipayPlus calls back CP /credential-provider/notifyAuthorization {mandate_id, l2_serialized}
   → CP stores the mandate, marks the session COMPLETED
   → Agent keeps the returned session_id

4. Agent calls POST /credential-provider/inquiryMandateSession {session_id}
   → CP returns stored mandate data (l1_serialized, l2_serialized, mandate_id)

5. Agent generates L3, then calls POST /credential-provider/applyCredential {session_id, L1, L2, L3}
   → CP resolves token_id + mandate_id from the session, submits the chain
     to AlipayPlus for verification
   → AlipayPlus returns payment_token
"""

__version__ = "2.0.0"
