## Overview
The Payment Service Domain is the core payment execution domain of the Agentic Mobile Protocol (AMP). It standardizes the end-to-end payment lifecycle, including wallet payment method binding through the Buyer Agent, Payment Token request and provisioning, payment processing by Alipay+ and the Mobile Payment Provider (MPP), and subsequent clearing and settlement among participants.

This domain provides standardized process guidance for participants during the payment execution.

## Scope of responsibility
The Payment Service Domain covers the following:

+ The binding of a User's wallet account and the issuance and standard definitions of Alipay+ Tokens.
+ Payment Token request, issuance, usage restrictions, and Alipay+-side verification.
+ Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present) execution flows.

| **Capability** | **Description** |
| --- | --- |
| Wallet Payment Method Binding | Standardizes the process by which a User authorizes and binds a wallet-based payment method to a specific Agent service scenario, or transaction relationship, and the issuance and definitions of Alipay+ Tokens. |
| Payment Token Request | Supports the request for and issuance of a Payment Token based on the Mandate, Alipay+ Token, and confirmed transaction information. |
| Payment Processing | Supports payment processing in the Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present) scenario:   • Direct Payment (Human-Present): Process payment when the User is present in real time and confirms the specific transaction, using a valid Mandate and Payment Token.   • Delegated Payment (Human-Not-Present): Process payment in Human-Not-Present scenarios, where the Agent requests and uses a Payment Token to complete the payment within the scope authorized by the Mandate. |


## Wallet Payment Method Binding
This capability defines the basic process and requirements for binding a User's wallet account to a Buyer Agent. After binding is completed, the Buyer Agent **MAY** initiate requests related to Intent-delegation based on the wallet account authorized by the User.

The Buyer Agent **SHOULD** store the Alipay+ Token obtained from Alipay+ via the Credential Provider (CP). This Alipay+ Token represents the binding relationship with the User's wallet account and serves as the unique identifier for the Buyer Agent to reference the User's wallet account.

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Confirms whether to bind a wallet-based payment method to the specified Buyer Agent. |
| Buyer Agent | Initiates and forwards the wallet binding request and stores the Alipay+ Token generated upon successful binding. |
| Credential Provider (CP) | Facilitates the routing of the wallet binding request and retrieves the Alipay+ Token from Alipay+. |
| Alipay+ | Generates the Alipay+ Token, manages the binding relationships, maintains the binding status, and verifies token validity. |
| Mobile Payment Provider (MPP) | Performs User identity verification, confirms the User's binding authorization, conducts payment account risk checks, and returns the binding result. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The User has established an active interaction with the Buyer Agent and has explicitly expressed an intention to bind a wallet-based payment method to that Buyer Agent.
+ The Buyer Agent has met the identity onboarding and trust assessment requirements of Alipay+.
+ The MPP is capable of performing User identity verification, confirming the User's binding intent, and returning the binding result. During the wallet binding phase, the Identity Signature Provider (ISP) has also provisioned an ISP Key pair for the User, which is used for subsequent User identity-verification signing during wallet binding and Mandate authorization.
+ Alipay+ is capable of generating Alipay+ Tokens, managing binding relationships, maintaining binding status, and verifying token validity.

### Basic binding process
#### Wallet binding authorization and identity verification
The Buyer Agent requests the CP to initiate a wallet binding request with Alipay+. The User is guided to a Trusted Authorization Surface, where the relevant binding information is presented, including the identity of the Buyer Agent, the wallet payment method to be bound, and the applicable authorization scope. The User then confirms the binding and completes wallet-side identity verification as required by the MPP.

The MPP **SHOULD** be responsible for confirming the User's binding authorization and performing User identity verification. After successful verification, the MPP **SHOULD** provide Alipay+ with the binding result and the relevant identity-verification credential information.

#### Alipay+ Token issuance
After the binding verification is successfully completed, Alipay+ **SHOULD** issue an Alipay+ Token in `activated` status and provision it to the Buyer Agent through the CP. The Buyer Agent **MUST** use this Alipay+ Token as the identifier of the User's wallet payment account when initiating subsequent Mandate requests and Payment Token requests.

After Alipay+ verifies that the User has successfully completed identity verification for wallet binding, Alipay+ signs the ISP Private Key and relevant binding information using its Private Key. This generates the L1 User Identity Confirmation Assurance Data, which provides verifiable evidence that the User's identity has been validated and that the wallet binding operation was authorized by the authenticated User.

### Processing requirements
When using the wallet payment method binding capability, the following requirements SHOULD be met:

+ The Buyer Agent and CP **MUST NOT** store the User's account information in plaintext.
+ In subsequent payment flows, participants **SHOULD** only reference the Alipay+ Token and **SHOULD NOT** directly transmit the User's original payment account information.
+ The MPP **SHOULD** be responsible for User identity verification and binding intent confirmation.
+ The MPP **MAY** determine the applicable verification methods based on account security, fraud prevention, compliance, and risk-control requirements.
+ Alipay+ **SHOULD** maintain the binding relationship between the Alipay+ Token and the associated usage restrictions, and **SHOULD** verify the validity of the Alipay+ Token in subsequent credential provisioning, or payment requests.

For details, refer to [L1 User Identity Assurance Data](Intent%20Trust%20Domain.md#l1-user-identity-assurance-data) in the Intent Trust Domain.

## Payment Token Request
A Payment Token is a payment credential requested by the Buyer Agent from Alipay+ through the CP. It is issued only after the User's wallet payment method has been bound, the relevant delegation Mandate has been authorized, and the specific Merchant and product or service information has been confirmed. The Payment Token is used to support single-transaction payment processing in both Direct Payment (Human-Present) and Delegated Payment (Human-Not-Present) scenarios.

The primary purpose of the Payment Token is to replace the User's original payment account information throughout the payment flow, including interactions among the Merchant, Acquirer, Alipay+, and the MPP. When a payment request is initiated, the Payment Token serves as the payment credential for that specific transaction. By enforcing one-time use, a limited validity period, binding to defined transaction elements, and Alipay+-side verification, the Payment Token helps mitigate risks such as replay attacks, credential tampering, unauthorized reuse, and cross-scenario misuse.

### Main participants and preconditions
| **Participant** | **Responsibility in this capability** |
| --- | --- |
| Buyer Agent | Identifies and confirms specific products or services based on the User-authorized delegated task and requests a Payment Token for the corresponding transaction. |
| Credential Provider (CP) | Assists the Buyer Agent in submitting Payment Token requests to Alipay+ and returning the issuance results. |
| Alipay+ | Performs intent scope validation, risk-control checks, and Payment Token generation and issuance. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The User has completed wallet payment method binding, and the Buyer Agent has obtained the corresponding Alipay+ Token.
+ The Mandate has been authorized by the User and is in `activated` status.
+ The Buyer Agent has completed identity verification and has a verifiable identity.
+ The Buyer Agent has completed necessary product or service search, Merchant selection, and order or service resource confirmation required for the transaction.

### Basic Payment Token Request process
Payment Token requests apply to Direct Payment (Human-Present) and Delegated Payment (Human-Not-Present). In either scenario, the Buyer Agent **MUST** request a Payment Token from Alipay+ through the CP only after the product or service to be paid for in this transaction has been identified and confirmed.

After receiving the request, Alipay+ **MUST** perform the required request validation and provide the MPP with information necessary to conduct S2 Payment Token Request Pre-Verification.

The MPP **MUST** execute S2 pre-verification to determine whether the specific transaction remains within the authorization scope confirmed by the User.

Alipay+ **MAY** proceed with subsequent processing and issue the Payment Token only after the S2 pre-verification is successfully completed.

**Direct Payment (Human-Present) scenario**

In the Direct Payment (Human-Present) scenario, the User is present in real time and confirms the specific transaction. The Buyer Agent **MAY** request a Payment Token from Alipay+ based on the `IMMEDIATE`-type Mandate and the corresponding Alipay+ Token.

Before submitting the request, the Buyer Agent **SHOULD** sign the Mandate and relevant transaction information using the **Agent Key**, and then submit the Payment Token request to Alipay+ through the CP. This signature provides evidence that the payment request was initiated by the authorized Buyer Agent and that the request details are consistent with the User-confirmed payment intent. Alipay+ **MAY** issue the Payment Token after the required verification checks have been successfully completed.

**Delegated Payment (Human-Not-Present) scenario**

In the Delegated Payment (Human-Not-Present) scenario, the User does not need to be present in real time at the time of payment execution. The Buyer Agent **SHOULD** initiate the Payment Token request within the scope of the `AUTONOMOUS`-type Mandate authorized by the User, and include the confirmed product or service order information within the signature scope to ensure that the Payment Token request can be verified against the User-authorized intent.

After completing the required signing using the Agent Key, the Buyer Agent **MUST** submit the Payment Token request to Alipay+ through the CP.

### Processing requirements
When using the Payment Token request capability, the following processing requirements **SHOULD** be met:

+ The Buyer Agent **MUST NOT** arbitrarily modify the core elements of products or services when requesting a Payment Token.
+ In the Delegated Payment (Human-Not-Present) scenario, the same Mandate **MAY** be used to request multiple Payment Tokens within the validity period, budget limits, and other applicable authorization constraints.
+ After receiving the Payment Token request, Alipay+ **MUST** validate that the request was initiated by an admitted and trusted Buyer Agent and **MUST** provide the MPP with the information required for S2 Payment Token Request Pre-Verification.
+ The MPP **MUST** perform S2 Payment Token Request Pre-Verification to confirm that the specific transaction remains within the User-confirmed authorization scope.
+ Alipay+ **MUST** issue the Payment Token only after S2 pre-verification is successfully completed. If S2 pre-verification fails, Alipay+ **MUST NOT** issue the Payment Token.
+ After issuing the Payment Token, Alipay+ **MUST** generate L3 Payment Token Request Assurance Data by recording the relevant information associated with the credential request and issuance process. The L3 Assurance Data serves as verifiable evidence that the transaction was initiated by an authorized Buyer Agent within the User-authorized scope.

For details, refer to [S2 Payment Token Request Pre-Verification](Intent%20Trust%20Domain.md#s2-payment-token-request-pre-verification) and [L3 Payment Token Request Assurance Data](Intent%20Trust%20Domain.md#l3-payment-token-request-assurance-data) in the Intent Trust Domain.

### Payment Token standard
The Payment Token uses a CGCP code with a length of more than 24 bits. A standard CGCP code typically consists of a Header and a Payload.

![](images/Figure%2010.%20Payment%20Token%20structure.png)

Figure 10. Payment Token structure

#### Header
The Header contains the following information:

+ **Primary routing segment**: a 2-digit fixed prefix `28`, used for protocol identification.
+ **Protocol version bit**: a 1-digit value indicating the version of the CGCP code protocol. The version determines the parsing rules and data format of the entire code.
+ **Secondary routing segment**: a 3-digit value, allocated by Alipay+ to its partners for secondary routing.
+ **Business scenario type code**: a code indicating the type of contactless communication business. It consists of two or more integer digits. Under this protocol, the generated Business Type is `23`.

#### Payload
The Payload is the data field following the Header. It contains the business data encoded in the CGCP code and **MUST** contain at least 16 characters.

## Payment Processing
### Direct Payment (Human-Present)
In the Direct Payment (Human-Present) scenario, the Buyer Agent obtains a Payment Token based on the `IMMEDIATE`-type Mandate after the User confirms the transaction in real time. The Buyer Agent then submits an order placement request, and participants in the transaction flow cooperate to complete the payment.

The overall payment flow includes, but is not limited to, Merchant payment acceptance, Acquirer forwarding of the payment request, validation by Alipay+, payment authorization and debit processing by the MPP, and final payment result notifications.

#### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| Buyer Agent | Confirms the Merchant, product, or service order for the transaction, obtains the applicable Payment Token, and initiates the payment process using that Payment Token. |
| Merchant | Accepts the payment request and completes necessary pre-validation before routing the request to the Acquirer. |
| Acquirer | Receives the transaction request from the Merchant and routes it to Alipay+ for further processing. |
| Credential Provider (CP) | Assists the Buyer Agent in submitting Payment Token requests to Alipay+ and returning the issuance results. |
| Alipay+ | Performs validation, risk-control checks, and transaction processing coordination, and routes the request to the relevant MPP where applicable. |
| Mobile Payment Provider (MPP) | Performs wallet-side validation and debit processing, and returns the payment result. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The Buyer Agent has confirmed the merchant, product, or service order for this transaction.
+ The Buyer Agent has applied for and obtained a Payment Token that is valid and usable for the transaction.

#### Interaction flow
##### Merchant initiates payment acceptance request
The Buyer Agent initiates an order placement with the Merchant carrying the Payment Token and L1, L2, and L3 Assurance Data. Upon receiving the request, the Merchant performs basic signature verification. If the verification is successful, the Merchant **MAY** submit this transaction request to the Acquirer.

##### Acquirer submits payment request to Alipay+
After receiving the payment request from the Merchant, the Acquirer **SHOULD** submit a payment acceptance request to Alipay+ with the Payment Token and necessary order transaction information.

##### Alipay+ initiates debit request to MPP
After receiving the payment request, Alipay+ **SHOULD** initiate a debit request to the MPP with the Payment Token and the order and payment information required to complete the debit.

Upon receiving the debit request, the MPP **MUST** perform S3 Payment Request Pre-Verification and S4 Wallet Debit Pre-Verification in sequence. Only after both S3 and S4 pre-verification are successfully completed can the MPP proceed with debit processing and then return the processing result to Alipay+.

If either S3 or S4 pre-verification fails, the MPP **MUST** decline the debit request and return the corresponding processing result to Alipay+.

##### Alipay+ returns payment processing result
Alipay+ **SHOULD** receive the debit result returned by the MPP and return the payment processing result to the Acquirer.

The Acquirer **SHOULD** synchronize the payment processing result to the Merchant. Based on the result, the Merchant **MAY** update the order status, perform service fulfillment, or deliver goods.

If Alipay+ returns a failure result, the Acquirer SHOULD synchronize the failure reason or failure semantics to the Merchant or Seller Agent.

##### Clearing and settlement
After payment processing is completed, Alipay+, the Acquirer, the MPP, and the Merchant **MAY** perform clearing, settlement, and reconciliation in accordance with the agreed rules and settlement cycles.

#### Processing requirements
When using the Direct Payment (Human-Present) processing capability, the following requirements **SHOULD** be met:

+ The payment request constructed by the Buyer Agent **MUST** ensure that the payment amount, payment currency, Merchant-side order information, and shopping cart information are consistent with the transaction details previously confirmed by the User.
+ After receiving the order request from the Buyer Agent, the Merchant **MUST** sequentially verify the encrypted credentials carried in the request (L1 User Identity Confirmation, L2 Mandate Authorization, and L3 Payment Token Request) to ensure that the User identity is valid, Buyer Agent's actions remain within the User-authorized scope, and the transaction is being executed by the authorized Buyer Agent. The payment process can continue only after verification is successfully completed.
+ The MPP **MUST** perform S3 Payment Request Pre-Verification to confirm that the payment request is consistent with the transaction order associated with the Payment Token. This verification can prevent the order information from being replaced, tampered with, or reused in the payment chain.
+ The MPP **MUST** perform S4 Wallet Debit Pre-Verification before the actual debit to confirm that the final payment still remains within the authorization scope confirmed by the User. This verification can prevent over-debit results due to price changes, multi-currency conversion, or cumulative payments.

For details, refer to [Assurance Data Management](Intent%20Trust%20Domain.md#assurance-data-management), [S3 Payment Request Pre-Verification](Intent%20Trust%20Domain.md#s3-payment-request-pre-verification), and [S4 Wallet Debit Pre-Verification](Intent%20Trust%20Domain.md#s4-wallet-debit-pre-verification) in the Intent Trust Domain.

### Delegated Payment (Human-Not-Present)
In the Delegated Payment (Human-Not-Present) scenario, the Buyer Agent obtains a Payment Token based on a valid, User-authorized `AUTONOMOUS`-type Mandate, as well as product or service order information, initiates the payment processing request, and then completes the debit without the User being present in real time.

The Delegated Payment (Human-Not-Present) differs from the Direct Payment (Human-Present) primarily in the following:

+ The basis for authorization and signing before Payment Token request is submitted.
+ Whether the User is present in real time at the time of payment execution.

Except for these differences, Delegated Payment (Human-Not-Present) **SHOULD** follow the same payment processing rules as Direct Payment (Human-Present) across the overall payment flow, including but not limited to Merchant payment acceptance, Acquirer payment request forwarding, Alipay+ validation, MPP debit processing, and payment result notifications.

