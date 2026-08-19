## Overview
<font style="color:rgba(0, 0, 0, 0.88);">The Payment Service Domain is the core payment execution domain of the Agentic Mobile Protocol (AMP). It standardizes the end-to-end payment lifecycle, including wallet payment method binding through the Buyer Agent, Payment Token request and provisioning, payment processing by Alipay+ and the Mobile Payment Provider (MPP), and subsequent clearing and settlement among participants.</font>

<font style="color:rgba(0, 0, 0, 0.88);">This domain provides standardized process guidance for participants during the payment execution.</font>

## Scope of responsibility
The Payment Service Domain covers the following:

+ The binding of a User's wallet account and the issuance and standard definitions of Alipay+ Tokens.
+ Payment Token request, issuance, usage restrictions, and Alipay+-side verification.
+ <font style="color:rgba(0, 0, 0, 0.88);">Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present)</font> execution flows.

| **Capability** | **Description** |
| --- | --- |
| Wallet Payment Method Binding | Standardizes the process by which a User authorizes and binds a wallet-based payment method to a specific Agent <font style="color:rgba(0, 0, 0, 0.88);">service scenario, or transaction relationship, and </font>the issuance and definitions of Alipay+ Tokens. |
| Payment Token Request | <font style="color:rgba(0, 0, 0, 0.88);">Supports the request for and issuance of a Payment Token based on the Mandate, Alipay+ Token, and confirmed transaction information.</font> |
| Payment Processing | <font style="color:rgba(0, 0, 0, 0.88);">Supports payment processing in the Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present) scenario:</font><br/>+ Direct Payment (Human-Present): Process <font style="color:rgba(0, 0, 0, 0.88);">payment when the User is present in real time and confirms the specific transaction, using a valid Mandate and Payment Token.</font><br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Delegated Payment (Human-Not-Present): Process payment in Human-Not-Present scenarios, where the Agent requests and uses a Payment Token to complete the payment within the scope authorized by the Mandate.</font> |


## Wallet Payment Method Binding
This capability defines the basic process and requirements for binding a User's wallet account to a Buyer Agent. After binding is completed, the Buyer Agent **MAY** initiate requests related to Intent-delegation based on the wallet account authorized by the User.

The Buyer Agent **SHOULD** store the Alipay+ Token obtained from Alipay+ via the Credential Provider (CP). This Alipay+ Token represents the binding relationship with the User's wallet account and serves as the unique identifier for the Buyer Agent to reference the User's wallet account.

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Confirms whether to bind a wallet-based payment method to the specified Buyer Agent. |
| Buyer Agent | Initiates and forwards the wallet binding request and stores the Alipay+ Token generated upon successful binding. |
| Credential Provider (CP) | <font style="color:rgba(0, 0, 0, 0.88);">Facilitates the routing of the wallet binding request and retrieves the Alipay+ Token from Alipay+.</font> |
| Alipay+ | Generates the Alipay+ Token, manages the binding relationships, maintains the binding status, and verifies token validity. |
| Mobile Payment Provider <font style="color:rgba(0, 0, 0, 0.88);">(MPP)</font> | <font style="color:rgba(0, 0, 0, 0.88);">Performs User identity verification, confirms the User's binding authorization, conducts payment account risk checks, and returns the binding result.</font> |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ <font style="color:rgba(0, 0, 0, 0.88);">The User has established an active interaction with the Buyer Agent and has explicitly expressed an intention to bind a wallet-based payment method to that Buyer Agent.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent has met the identity onboarding and trust assessment requirements of Alipay+.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The MPP is capable of performing User identity verification, confirming the User's binding intent, and returning the binding result. During the wallet binding phas</font><font style="color:rgba(0, 0, 0, 0.88);">e, the Identity Signature Provider (ISP) has also provisioned an ISP Key pair for the User, which is used for su</font><font style="color:rgba(0, 0, 0, 0.88);">bsequent User identity-verification signing during wallet binding and Mandate authorization.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ is capable of generating Alipay+ Tokens, managing binding relationships, maintaining binding status, an</font><font style="color:rgba(0, 0, 0, 0.88);">d verifying token validity.</font>

### Basic binding process
#### Wallet binding authorization and identity verification
The Buyer Agent requests the CP to initiate a wallet binding request with Alipay+. The User is guided to a Trusted Authorization Surface, <font style="color:rgba(0, 0, 0, 0.88);">where the relevant binding information is presented, including the identity of the Buyer Agent, the wallet payment method to be bound, and the applicable authorization scope. The User then confirms the binding and completes wallet-side identity verification as required by the MPP.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be responsible for confirming the User's binding authorization and performing User identity verification. After successful verification, the MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> provide Alipay+ with the binding result and the relevant identity-verification credential information.</font>

#### Alipay+ Token issuance
<font style="color:rgba(0, 0, 0, 0.88);">After the binding verification is successfully completed, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> issue an Alipay+ Token in </font>`<font style="color:rgba(0, 0, 0, 0.88);">activated</font>`<font style="color:rgba(0, 0, 0, 0.88);"> status and provision it to the Buyer Agent through the CP. The Buyer Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> use this Alipay+ Token as the identifier of the User's wallet payment account when initiating subsequent Mandate requests and Payment Token requests.</font>

<font style="color:rgba(0, 0, 0, 0.88);">After Alipay+ verifies that the User has successfully completed identity verification for wallet binding, Alipay+ signs the ISP Private Key and relevant binding information using its Private Key. This generates the L1 User Identity Confirmation Assurance Data, which provides verifiable evidence that the User's identity has been validated and that the wallet binding operation was authorized by the authenticated User.</font>

### Processing requirements
When using the wallet payment method binding capability, the following requirements SHOULD be met:

+ The Buyer Agent and CP **MUST NOT** store the User's account information in plaintext.
+ In subsequent payment flows, participants **SHOULD** only reference the Alipay+ Token and **SHOULD NOT **directly transmit the User's original payment account information.
+ The MPP **SHOULD** be responsible for User identity verification and binding intent confirmation.
+ <font style="color:rgba(0, 0, 0, 0.88);">The MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> determine the applicable verification methods based on account security, fraud prevention, compliance, and risk-control requirements.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> maintain the binding relationship between the Alipay+ Token and the associated usage restrictions, and </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> verify the validity of the Alipay+ Token in subsequent credential provisioning, or payment requests.</font>

<font style="color:rgba(0, 0, 0, 0.88);">For details, refer to </font>[L1 User Identity Assurance Data](intent#faUja)<font style="color:rgba(0, 0, 0, 0.88);"> in the Intent Trust Domain. </font>

## Payment Token Request
<font style="color:rgba(0, 0, 0, 0.88);">A Payment Token is a payment credential requested by the Buyer Agent from Alipay+ through the CP. It is issued only after the User's wallet payment method has been bound, the relevant delegation Mandate has been authorized, and the specific Merchant and product or service information has been confirmed. The Payment Token is used to support single-transaction payment processing in both Direct Payment (Human-Present) and Delegated Payment (Human-Not-Present) scenarios.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The primary purpose of the Payment Token is to replace the User's original payment account information throughout the payment flow, including interactions among the Merchant, Acquirer, Alipay+, and the MPP. When a payment request is initiated, the Payment Token serves as the payment credential for that specific transaction. By enforcing one-time use, a limited validity period, binding to defined transaction elements, and Alipay+-side verification, the Payment Token helps mitigate risks such as replay attacks, credential tampering, unauthorized reuse, and cross-scenario misuse.</font>

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
Payment Token requests apply to Direct Payment (Human-Present) and Delegated Payment (Human-Not-Present). In either scenario, the Buyer Agent **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>request a Payment Token from Alipay+ through the CP only after the product or service to be paid for in this transaction has been identified and confirmed.

After receiving the request, Alipay+ **MUST** perform the required request validation and provide the MPP with information necessary to conduct S2 Payment Token Request Pre-Verification.

The MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>execute S2 pre-verification to determine whether the specific transaction remains within the authorization scope confirmed by the User. 

<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> proceed with subsequent processing and issue the Payment Token only after the S2 pre-verification is successfully completed.</font>

<font style="color:rgba(0, 0, 0, 0.88);"></font>

**Direct Payment (Human-Present) scenario**

In the Direct Payment (Human-Present) scenario, the User is present in real time and confirms the specific transaction. The Buyer Agent **MAY** request a Payment Token from Alipay+ based on the `IMMEDIATE`-type Mandate and the corresponding Alipay+ Token.

<font style="color:rgba(0, 0, 0, 0.88);">Before submitting the request, the Buyer Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> sign the Mandate and relevant transaction information using the </font>**<font style="color:rgba(0, 0, 0, 0.88);">Agent Key</font>**<font style="color:rgba(0, 0, 0, 0.88);">, and then submit the Payment Token request to Alipay+ through the CP. </font>Thi<font style="color:rgba(0, 0, 0, 0.88);">s signature provides evidence that the payment request was initiated by the authorized Buyer Agent and that the request details are consistent with the User-confirmed payment intent. Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> issue the Payment Token after the required verification checks have been successfully completed.</font>



**Delegated Payment (Human-Not-Present) scenario**

In the Delegated Payment (Human-Not-Present) scenario, the User does not need to be present in real time at the time of  payment execution. The Buyer Agent **SHOULD** <font style="color:rgba(0, 0, 0, 0.88);">initiate the Payment Token request within the scope of the </font>`<font style="color:rgba(0, 0, 0, 0.88);">AUTONOMOUS</font>`<font style="color:rgba(0, 0, 0, 0.88);">-type Mandate authorized by the User, and include the confirmed product or service order information within the signature scope </font><font style="color:rgba(0, 0, 0, 0.88);">to ensure that the Payment Token request can be verified against the User-authorized intent.</font>

<font style="color:rgba(0, 0, 0, 0.88);">After completing the required signing using the Agent Key, the Buyer Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> submit the Payment Token request to Alipay+ through the CP.</font>

### Processing requirements
When using the Payment Token request capability, the following processing requirements **SHOULD **be met:

+ The Buyer Agent **MUST NOT** arbitrarily modify the core elements of products or services when requesting a Payment Token.
+ In the Delegated Payment (Human-Not-Present) scenario, the same Mandate **MAY** be used to request multiple Payment Tokens within the validity period, budget limits, and other applicable authorization constraints.
+ After receiving the Payment Token request, Alipay+ **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>validate that the request was initiated by an admitted and trusted Buyer Agent and** ****<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>provide the MPP with the information required for <font style="color:rgba(0, 0, 0, 0.88);">S2 Payment Token Request Pre-Verification.</font>
+ The MPP** ****<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>perform <font style="color:rgba(0, 0, 0, 0.88);">S2 Payment Token Request Pre-Verification </font>to confirm that the specific transaction remains within the User-confirmed authorization scope. 
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**<font style="color:rgba(0, 0, 0, 0.88);">issue the Payment Token only after S2 pre-verification is successfully completed. If S2 pre-verification fails, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST NOT</font>**<font style="color:rgba(0, 0, 0, 0.88);"> issue the Payment Token. </font>
+ <font style="color:rgba(0, 0, 0, 0.88);">After issuing the Payment Token, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> generate L3 Payment Token Request Assurance Data by recording the relevant information associated with the credential request and issuance process. The L3 Assurance Data serves as verifiable evidence that the transaction was initiated by an authorized Buyer Agent within the User-authorized scope.</font>

For details, refer to [S2 Payment Token Request Pre-Verification](intent#DIg1f) and [L3 Payment Token Request Assurance Data](intent#jIx2S) in the Intent Trust Domain.

### Payment Token standard
The Payment Token uses a CGCP code with a length of more than 24 bits. A standard CGCP code typically consists of a Header and a Payload.

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784622376918-68bf0125-caf3-46ec-aabd-444720a8e9a9.png)

Figure 10. Payment Token structure

#### Header
The Header contains the following information:

+ **Primary routing segment**: a 2-digit fixed prefix `28`, used for protocol identification.
+ **Protocol version bit**: a 1-digit value indicating the version of the CGCP code protocol. The version determines the parsing rules and data format of the entire code.
+ **Secondary routing segment**: a 3-digit value, allocated by Alipay+ to its partners for secondary routing.
+ **Business scenario type code**: a code indicating the type of contactless communication business. It consists of two or more integer digits. Under this protocol, the generated Business Type is `23`. 

#### Payload
<font style="color:rgba(0, 0, 0, 0.88);">The Payload is the data field following the Header. It contains the business data encoded in the CGCP code and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> contain at least 16 characters.</font>

## <font style="color:rgba(0, 0, 0, 0.88);">Payment Processing</font>
### Direct Payment (Human-Present)
In the Direct Payment (Human-Present) scenario, the Buyer Agent obtains a Payment Token based on the `IMMEDIATE`-type Mandate after the User confirms the transaction in real time. <font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent then submits an order placement request, and participants in the transaction flow cooperate to complete the payment.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The overall payment flow includes, but is not limited to, Merchant payment acceptance, Acquirer forwarding of the payment request, validation by Alipay+, payment authorization and debit processing by the MPP, and final payment result notifications.</font>

#### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| Buyer Agent | <font style="color:rgba(0, 0, 0, 0.88);">Confirms the Merchant, product, or service order for the transaction, obtains the applicable Payment Token, and initiates the payment process using that Payment Token.</font> |
| Merchant | <font style="color:rgba(0, 0, 0, 0.88);">Accepts the payment request and completes necessary pre-validation before routing the request to the Acquirer.</font> |
| Acquirer | <font style="color:rgba(0, 0, 0, 0.88);">Receives the transaction request from the Merchant and routes it to Alipay+ for further processing.</font> |
| Credential Provider (CP) | Assists the Buyer Agent in submitting Payment Token requests to Alipay+ and returning the issuance results. |
| Alipay+ | <font style="color:rgba(0, 0, 0, 0.88);">Performs validation, risk-control checks, and transaction processing coordination, and routes the request to the relevant MPP where applicable.</font> |
| Mobile Payment Provider <font style="color:rgba(0, 0, 0, 0.88);">(MPP)</font> | <font style="color:rgba(0, 0, 0, 0.88);">Performs wallet-side validation and debit processing, and returns the payment result.</font> |


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
<font style="color:rgba(0, 0, 0, 0.88);">After receiving the payment request, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> initiate a debit request to the MPP with the Payment Token and the order and payment information required to complete the debit.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Upon receiving the debit request, the MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> perform S3 Payment Request Pre-Verification and S4 Wallet Debit Pre-Verification in sequence. Only after both S3 and S4 pre-verification are successfully completed can the MPP proceed with debit processing and  then return the processing result to Alipay+.</font>

<font style="color:rgba(0, 0, 0, 0.88);">If either S3 or S4 pre-verification fails, the MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> decline the debit request and return the corresponding processing result to Alipay+.</font>

##### Alipay+ returns payment processing result
Alipay+** SHOULD **receive the debit result returned by the MPP and return the payment processing result to the Acquirer.

The Acquirer **SHOULD** synchronize the payment processing result to the Merchant. Based on the result, the Merchant **MAY** update the order status, perform service fulfillment, or deliver goods.

If Alipay+ returns a failure result, the Acquirer SHOULD synchronize the failure reason or failure semantics to the Merchant or Seller Agent.

##### Clearing and settlement
<font style="color:rgba(0, 0, 0, 0.88);">After payment processing is completed, Alipay+, the Acquirer, the MPP, and the Merchant </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> perform clearing, settlement, and reconciliation in accordance with the agreed rules and settlement cycles.</font> 

#### Processing requirements
When using the Direct Payment (Human-Present) processing capability, the following requirements** SHOULD **be met:

+ The payment request constructed by the Buyer Agent**** **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>ensure that the payment amount, payment currency, Merchant-side order information, and shopping cart information are consistent with the transaction details previously confirmed by the User. 
+ After receiving the order request from the Buyer Agent, the Merchant **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>sequentially verify the encrypted credentials carried in the request (<font style="color:rgba(0, 0, 0, 0.88);">L1 User Identity Confirmation, L2 Mandate Authorization, and L3 Payment Token Request</font>) to ensure that the User identity is valid, Buyer Agent's actions remain within the User-authorized scope, and the transaction is being executed by the authorized Buyer Agent. The payment process can continue only after verification is successfully completed. 
+ The MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>perform S3 Payment Request Pre-Verification to confirm that the payment request is consistent with the transaction order associated with the Payment Token. This verification can prevent the order information from being replaced, tampered with, or reused in the payment chain. 
+ The MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font>perform S4 Wallet Debit Pre-Verification before the actual debit to confirm that the final payment still remains within the authorization scope confirmed by the User. This verification can prevent over-debit results due to price changes, multi-currency conversion, or cumulative payments. 

For details, refer to [Assurance Data Management](intent#gwpyL), [S3 Payment Request Pre-Verification](intent#wXxRp), and [S4 Wallet Debit Pre-Verification](intent#zRyjH) in the Intent Trust Domain.

### Delegated Payment **(Human-Not-Present)**
In the Delegated Payment (Human-Not-Present) scenario, the Buyer Agent obtains a Payment Token based on a valid, User-authorized `AUTONOMOUS`-type Mandate, as well as product or service order information, initiates the payment processing request, and then completes the debit without the User being present in real time.

The Delegated Payment (Human-Not-Present) differs from the Direct Payment (Human-Present) primarily in the following:

+ The basis for authorization and signing before Payment Token request is submitted.
+ Whether the User is present in real time at the time of payment execution.

Except for these differences, Delegated Payment (Human-Not-Present) **SHOULD** <font style="color:rgba(0, 0, 0, 0.88);">follow the same payment processing rules as Direct Payment (Human-Present) across the overall payment flow, including but not limited to Merchant payment acceptance, Acquirer payment request forwarding, Alipay+ validation, MPP debit processing, and payment result notifications.</font>

