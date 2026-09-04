## Overview
This document describes the typical business scenarios, core domain capabilities, and end-to-end business processes supported by the Agentic Mobile Protocol (AMP). It is intended to help protocol participants understand the allocation of roles and responsibilities, the applicable trust mechanisms, and the payment execution paths across different agentic commerce scenarios.

## Scenarios
The typical business scenarios supported by AMP can be categorized based on whether the User is present and actively participating at the time of transaction execution. Accordingly, these scenarios fall into two categories: Human-Present and Human-Not-Present. AMP currently supports the following scenarios:

+ **Direct Payment (Human-Present)**: The User provides the Agent with a shopping objective, and the Agent identifies and presents relevant product or service options. The User selects the desired option, confirms the order, and completes the payment directly. The User is actively involved in real time throughout the transaction.
+ **Delegated Payment (Human-Not-Present)**: The User delegates an Agent to execute a clearly defined task on the User's behalf. The delegated task may include product search, order placement, and payment execution with a specified Merchant or within a specified transaction context. Once the User has granted the authorization, the Agent completes the task without requiring the User to be present during execution.

| **Scenario** | **User presence** | **Mandate type** | **Agentic commerce decision autonomy** |
| --- | --- | --- | --- |
| Scenario 1: Direct Payment (Human-Present) | The User is present in real time. | `IMMEDIATE` | The User confirms the order and completes payment in real time. |
| Scenario 2: Delegated Payment (Human-Not-Present) | The User is not present during execution. | `AUTONOMOUS` | The Agent executes the task based on a User-authorized target or transaction context. |


## Domain and capability list
The following table summarizes the core capabilities of each domain within the AMP protocol framework, including their functional scope, areas of responsibility, and relationships in the end-to-end transaction lifecycle.

| **Domain** | **Capability** | **Description** |
| --- | --- | --- |
| Intent Trust Domain | Agent Onboarding and Management | Defines the requirements for Agent onboarding, including Agent identity verification, capability registration, key management, and trust assessment prior to accessing the AMP framework and the Agent lifecycle management. |
| Intent Trust Domain | Intent Capture and Structured Representation | Specifies how User Intent is captured, clarified, and represented in a structured format, providing the foundation for Mandate authorization and subsequent validation. |
| Intent Trust Domain | Mandate Authorization | Defines how a Mandate is presented to the User, confirmed, issued, and recorded, together with the resulting authorization outcome, via a Trusted Authorization Surface. |
| Intent Trust Domain | Mandate Lifecycle Management | Governs the end-to-end lifecycle of a Mandate, including creation, activation, revocation, expiration, and closure. |
| Intent Trust Domain | End-to-End Intent Guard Management | Performs phased validation throughout subsequent Agent transaction and payment flows against the User-confirmed Mandate boundaries, ensuring that all related requests remain within the User's authorized scope. |
| Intent Trust Domain | Assurance Data Management | Defines the requirements for capturing and maintaining assurance data of critical events, including identity verification, authorization, signing, credential provisioning, and execution outcomes, to support accountability, auditability, and dispute resolution. |
| Payment Service Domain | Wallet Payment Method Binding | Enables the User to authorize and bind a wallet-based payment method to a specific Agent, service scenario, or transaction relationship, resulting in the issuance of an Alipay+ Token. |
| Payment Service Domain | Payment Token Request | Standardizes the process by which a User authorizes and binds a wallet-based payment method to a specific Agent, service scenario, or transaction relationship, and the issuance and definitions of Alipay+ Tokens. |
| Payment Service Domain | Payment Processing | Supports payment processing in the Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present) scenario:   • Direct Payment (Human-Present): Process payment when the User is present in real time and confirms the specific transaction, using a valid Mandate and Payment Token.   • Delegated Payment (Human-Not-Present): Process payment in Human-Not-Present scenarios, where the Agent requests and uses a Payment Token to complete the payment within the scope authorized by the Mandate. |
| Wallet Service Domain | Delegated Task Management | Enables the Mobile Payment Provider (MPP) to present and manage information for the User, including authorized Agents, Mandates, task status, budget utilization, and payment outcomes. |
| Wallet Service Domain | Delegation Limit Management | Enables the User to configure transaction limits, usage limits, and other control parameters that govern delegated authorization within the digital wallet. |


## Business processes
### Scenario 1: Direct Payment (Human-Present)
#### Scenario description
This scenario applies where the User is present online in real time and the purchase target is clarified during the current interaction. The Agent interprets the User's purchase request, retrieves suitable Merchants and product information, presents candidate options to the User, and the User then selects the product and confirms the payment.

In this scenario, the final transaction decision and payment confirmation remain under the User's real-time control.

**Applicable Buyer Agent type**: Platform Agent

Example:

> The User says to the Agent: "Help me place an order for this watch." The Agent retrieves the relevant product information and presents it to the User. The User confirms the order and completes the payment.
>

#### Main business process
![](images/Figure%202.%20Main%20workflow%20of%20Direct%20Payment%20%28Human-Present%29.png)

Figure 2. Main workflow of Direct Payment (Human-Present)

**Phase 1: Preparation**

**Step 1: Agent identity onboarding**

The Agent is onboarded to the Alipay+ network in advance and completes the Know Your Agent (KYA) process to obtain the corresponding Agent ID.

This step **MUST** comply with the requirements for [Agent Onboarding and Management](Intent%20Trust%20Domain.md#agent-onboarding-and-management) in the Intent Trust Domain.

**Phase 2: Purchase intent capture**

**Step 2: User expresses purchase intent**

The User expresses a purchase request to the Agent using natural language. Through interaction with the User, the Agent clarifies the User's intent and converts the natural-language request into structured information, which is then used to generate an `IMMEDIATE`-type Mandate.

This step **MUST** comply with the requirements for [Intent Capture and Structured Representation](Intent%20Trust%20Domain.md#intent-capture-and-structured-representation) in the Intent Trust Domain.

**Step 3: Wallet payment method binding**

![](images/Figure%203.%20User%20experience%20sample%20of%20binding%20a%20wallet%20account.png)

Figure 3. User experience sample of binding a wallet account

The Buyer Agent guides the User through the process of binding a digital wallet account. For the same Agent, the User is required to complete wallet binding only once before the first purchase. For subsequent transactions, the User delegates intents based on the existing binding relationship without repeatedly binding the wallet account.

After the User completes the binding process, the Agent stores the L1 Assurance Data returned by the Credential Provider (CP).

**L1 User Identity Assurance Data verification**: Alipay+ confirms the successful binding of the User's wallet account. It signs core binding data, including the ISP Public Key, with its private key and records the signed data as Assurance Data. The Assurance Data serves as verifiable evidence of the authorization relationship among the User, the MPP, and the Agent, and attests to the authenticity and validity of the User's identity information.

This step **MUST** comply with the requirements for [Wallet Payment Method Binding](Payment%20Service%20Domain.md#wallet-payment-method-binding) in the Payment Service Domain.

**Phase 3: Product and service query**

**(OPTIONAL) Step 4: Service resource discovery and capability negotiation**

The Buyer Agent and Merchants **MAY** publish their respective profile information in advance. They may also conduct service resource discovery and exchange service capability information prior to transaction execution. Based on the resulting capability negotiation, the Buyer Agent identifies Merchants that meet the User's purchase requirements, payment compatibility requirements, and service fulfillment criteria.

This step is outside the scope of the AMP specification and is not standardized by this protocol.

**(OPTIONAL) Step 5: Product and service query and confirmation**

The Agent retrieves product or service information from candidate Merchants and presents suitable options to the User for confirmation.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

**Step 6: User completes Mandate authorization**

![](images/Figure%204.%20User%20experience%20sample%20of%20confirming%20order%20and%20payment.png)

Figure 4. User experience sample of confirming order and payment

The Agent guides the User to review and authorize the product order through the Trusted Authorization Surface. After the User completes identity verification, the Identity Signature Provider (ISP) signs the authorized intent using the ISP Key pair. The resulting `IMMEDIATE`-type Mandate serves as the authorization basis for subsequent Payment Token provisioning and payment request verification. After Mandate authorization is completed, the Buyer Agent stores the L2 Assurance Data returned by the CP.

**L2 Mandate Authorization Assurance Data**: Alipay+ records the identity verification result and signature result associated with the User's authorization of intent delegation. This provides evidence that the User has granted the Agent limited authority within a specified budget, validity period, product scope, Merchant scope, or other defined authorization boundaries.

This step **MUST** comply with the requirements for [Mandate Authorization](Intent%20Trust%20Domain.md#mandate-authorization) in the Intent Trust Domain.

**Phase 4: Payment execution and Merchant fulfillment**

**Step 7: Payment Token provision**

Based on the authorized User Intent issued Mandate, the Agent requests a Payment Token from Alipay+ through the CP. This step **MUST** comply with the requirements for [Payment Token Request](Payment%20Service%20Domain.md#payment-token-request) in the Payment Service Domain.

**Step 8: Payment processing**

The Agent places the order with the Merchant and initiates the payment request by providing the Payment Token together with the L1 and L2 Assurance Data.

The Merchant is recommended to verify the L1 and L2 signatures before proceeding with the payment process. The Merchant continues payment processing after the relevant verification checks have been successfully completed. This verification step **MUST** comply with the requirements for [Assurance Data Management](Intent%20Trust%20Domain.md#assurance-data-management) in the Intent Trust Domain.

After verification succeeds, the Merchant forwards the Payment Token to Alipay+ through the Acquirer to complete the final payment. This step **MUST** comply with the requirements for [Payment Processing in the Direct Payment (Human-Present)](Payment%20Service%20Domain.md#direct-payment-human-present) in the Payment Service Domain.

**(OPTIONAL) Step 9: Merchant fulfillment**

After confirming payment, the Merchant completes fulfillment, such as issuing tickets, shipping goods, or delivering services.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

### Scenario 2: Delegated Payment (Human-Not-Present)
#### Scenario description
This scenario applies to Human-Not-Present payment scenarios where the User is not online in real time during order placement and payment execution, but has explicitly delegated the purchase intent to the Agent during the initial interaction. At the outset, the User completes task definition, intent confirmation, identity verification, and authorization signing. Through this process, the User authorizes the Buyer Agent to perform product or service search, price comparison, transaction selection or confirmation, and payment execution within the defined authorization boundaries.

**Applicable Buyer Agent type**: Platform Agent

Example:

> The User says to the Agent (e.g., Gemini), "Book me a flight to Kuala Lumpur tomorrow morning and a 5-star hotel there for 3 nights, with a total budget not exceeding 10,000 HKD." After the User completes identity verification and authorization as guided, the Agent proceeds to complete order placement and payment within the authorized scope, without requiring the User to be present at the time of payment execution.
>

#### Main business process
![](images/Figure%205.%20Main%20workflow%20of%20Delegated%20Payment%20%28Human-Not-Present%29.png)

Figure 5. Main workflow of Delegated Payment (Human-Not-Present)

**Phase 1: Preparation**

**Step 1: Agent identity onboarding**

The Agent is onboarded to the Alipay+ network in advance and completes the Know Your Agent (KYA) process to obtain the corresponding Agent ID.

This step **MUST** comply with the requirements for [Agent Onboarding and Management](Intent%20Trust%20Domain.md#agent-onboarding-and-management) in the Intent Trust Domain.

**Phase 2: Purchase intent capture and wallet payment method binding**

**Step 2: User expresses shopping Intent**

The User expresses a purchase request to the Agent using natural language. Through interaction with the User, the Agent clarifies the User's intent and converts the natural-language request into structured information, which is then used to generate an `AUTONOMOUS`-type Mandate.

This step **MUST** comply with the requirements for [Intent Capture and Structured Representation](Intent%20Trust%20Domain.md#intent-capture-and-structured-representation) in the Intent Trust Domain.

**Step 3: Wallet payment method binding**

![](images/Figure%206.%20User%20experience%20sample%20of%20binding%20a%20wallet%20account.png)

Figure 6. User experience sample of binding a wallet account

The Buyer Agent guides the User through the process of binding a digital wallet account. For the same Agent, the User is required to complete wallet binding only once before the first purchase. For subsequent transactions, the User delegates intents based on the existing binding relationship without repeatedly binding the wallet account.

After the User completes the binding process, the Agent stores the L1 Assurance Data returned by the CP.

**L1 User Identity Assurance Data verification**: Alipay+ confirms the successful binding of the User's wallet account. It signs core binding data, including the ISP Public Key, with its Private Key and records the signed data as Assurance Data. The Assurance Data serves as verifiable evidence of the authorization relationship among the User, the MPP, and the Agent, and attests to the authenticity and validity of the User's identity information.

This step **MUST** comply with the requirements for [Wallet Payment Method Binding](Payment%20Service%20Domain.md#wallet-payment-method-binding) in the Payment Service Domain.

**Step 4: User completes Mandate authorization confirmation**

![](images/Figure%207.%20User%20experience%20sample%20of%20confirming%20an%20order.png)

Figure 7. User experience sample of confirming an order

The Agent guides the User to review and authorize the product order through the Trusted Authorization Surface. After the User completes identity verification, the ISP signs the authorized intent using the ISP Key pair. The resulting `AUTONOMOUS`-type Mandate serves as the authorization basis for subsequent Payment Token provisioning and payment request verification. After Mandate authorization is completed, the Buyer Agent stores the L2 Assurance Data returned by the CP.

**L2 Mandate Authorization Assurance Data verification**: Alipay+ records the identity verification result and signature result associated with the User's authorization of intent delegation. This provides evidence that the User has granted the Agent limited authority within a specified budget, validity period, product scope, Merchant scope, or other defined authorization boundaries.

This step **MUST** comply with the requirements for [Mandate Authorization](Intent%20Trust%20Domain.md#mandate-authorization) in the Intent Trust Domain.

**Phase 3: Product and service query**

**(OPTIONAL) Step 5: Service resource discovery and capability negotiation**

The Buyer Agent and Merchants **MAY** publish their respective profile information in advance. They may also conduct service resource discovery and exchange service capability information prior to transaction execution. Based on the resulting capability negotiation, the Buyer Agent identifies Merchants that meet the User's purchase requirements, payment compatibility requirements, and service fulfillment criteria.

This step is outside the scope of the AMP specification and is not standardized by this protocol.

**(OPTIONAL) Step 6: Product and service query and confirmation**

The Agent retrieves product or service information from candidate Merchants and presents suitable options to the User for confirmation.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

**Phase 4: Payment execution and Merchant fulfillment**

**Step 7: Payment Token provision**

Based on the User-authorized `AUTONOMOUS`-type Mandate and the selected product order information, the Agent signs the Payment Token request using the Agent Key and submits the request to Alipay+ through the CP.

**L3 Payment Token Request Assurance Data verification**: Alipay+ records the Agent's signing result associated with the Payment Token request as Assurance Data. The data serves as verifiable evidence that the Agent completed product selection, order initiation, or payment initiation in accordance with the User-authorized intent and within the scope of the issued Mandate.

This step **MUST** comply with the requirements for [Payment Token Request](Payment%20Service%20Domain.md#payment-token-request) in the Payment Service Domain.

**Step 8: Payment processing**

The Agent submits the order and payment request to the Merchant, including the Payment Token and L1, L2, and L3 Assurance Data. The Merchant is recommended to verify the L1, L2, and L3 signatures and related Assurance Data. After the verification checks have been successfully completed, the Merchant then proceeds with payment processing.

After successful verification, the Merchant forwards the Payment Token to Alipay+ through the Acquirer to complete the final payment.

This step **MUST** comply with the requirements for [Assurance Data Management](Intent%20Trust%20Domain.md#assurance-data-management) in the Intent Trust Domain and for [Payment Processing in Delegated Payment (Human-Not-Present)](Payment%20Service%20Domain.md#delegated-payment-human-not-present) in the Payment Service Domain.

**(OPTIONAL) Step 9: Merchant fulfillment**

After confirming payment, the Merchant completes fulfillment, such as issuing tickets, shipping goods, or delivering services.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

