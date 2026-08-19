## Overview
<font style="color:rgba(0, 0, 0, 0.88);">This document describes the typical business scenarios, core domain capabilities, and end-to-end business processes supported by the Agentic Mobile Protocol (AMP). It is intended to help protocol participants understand the allocation of roles and responsibilities, the applicable trust mechanisms, and the payment execution paths across different agentic commerce scenarios.</font>

## Scenarios
<font style="color:rgba(0, 0, 0, 0.88);">The typical business scenarios supported by AMP can be categorized based on whether the User is present and actively participating at the time of transaction execution. Accordingly, these scenarios fall into two categories: Human-Present and Human-Not-Present. AMP currently supports the following scenarios:</font>

+ **<font style="color:rgba(0, 0, 0, 0.88);">Direct Payment (Human-Present)</font>**<font style="color:rgba(0, 0, 0, 0.88);">: The User provides the Agent with a shopping objective, and the Agent identifies and presents relevant product or service options. The User selects the desired option, confirms the order, and completes the payment directly. The User is actively involved in real time throughout the transaction. </font>
+ **Delegated Payment (Human-Not-Present)**: <font style="color:rgba(0, 0, 0, 0.88);">The User delegates an Agent to execute a clearly defined task on the User's behalf. The delegated task may include product search, order placement, and payment execution with a specified Merchant or within a specified transaction context. Once the User has granted the authorization,</font><font style="color:rgba(0, 0, 0, 0.88);"> the Agent completes the task without requiring the User to be present during execution.</font>

| **Scenario** | **User presence** | **Mandate type** | **Agentic commerce decision autonomy** |
| :--- | :--- | --- | --- |
| Scenario 1: Direct Payment (Human-Present) | The User is present in real time. | `IMMEDIATE`  | The User confirms the order and completes payment in real time. |
| Scenario 2: Delegated Payment (Human-Not-Present) | The User is not present during execution. | `AUTONOMOUS`  | <font style="color:rgba(0, 0, 0, 0.88);">The Agent executes the task based on a User-authorized target or transaction context.</font> |


## Domain and capability list
The following table summarizes <font style="color:rgba(0, 0, 0, 0.88);">the core capabilities of each domain within the AMP protocol framework, including their functional scope, areas of responsibility, and relationships in the end-to-end transaction lifecycle.</font>

| **<font style="color:rgba(0, 0, 0, 0.88);">Domain</font>** | **<font style="color:rgba(0, 0, 0, 0.88);">Capability</font>** | **<font style="color:rgba(0, 0, 0, 0.88);">Description</font>** |
| --- | --- | --- |
| Intent Trust Domain | Agent Onboarding and Management | <font style="color:rgba(0, 0, 0, 0.88);">Defines the requirements for Agent onboarding, including Agent identity verification, capability registration, key management, and trust assessment prior to accessing the AMP framework and the Agent lifecycle management.</font> |
| | Intent Capture and Structured Representation | <font style="color:rgba(0, 0, 0, 0.88);">Specifies how User Intent is captured, clarified, and represented in a structured format, providing the foundation for Mandate authorization and subsequent validation.</font> |
| | <font style="color:rgba(0, 0, 0, 0.88);">Mandate Authorization</font> | <font style="color:rgba(0, 0, 0, 0.88);">Defines how a Mandate is presented to the User, confirmed, issued, and recorded, together with the resulting authorization outcome, via a Trusted Authorization Surface.</font> |
| | Mandate Lifecycle Management | <font style="color:rgba(0, 0, 0, 0.88);">Governs the end-to-end lifecycle of a Mandate, including creation, activation, revocation, expiration, and closure.</font> |
| | End-to-End Intent Guard Management | <font style="color:rgba(0, 0, 0, 0.88);">Performs phased validation throughout subsequent Agent transaction and payment flows against the User-confirmed Mandate boundaries, ensuring that all related requests remain within the User's authorized scope.</font> |
| | Assurance Data Management | <font style="color:rgba(0, 0, 0, 0.88);">Defines the requirements for capturing and maintaining assurance data of critical events, including identity verification, authorization, signing, credential provisioning, and execution outcomes, to support accountability, auditability, and dispute resolution.</font> |
| Payment Service Domain | Wallet Payment Method Binding | <font style="color:rgba(0, 0, 0, 0.88);">Enables the User to authorize and bind a wallet-based payment method to a specific Agent, service scenario, or transaction relationship, resulting in the issuance of an Alipay+ Token.</font> |
| | Payment Token Request | <font style="color:rgba(0, 0, 0, 0.88);">Standardizes the process by which a User authorizes and binds a wallet-based payment method to a specific Agent, service scenario, or transaction relationship, and the issuance and definitions of Alipay+ Tokens.</font> |
| | Payment Processing | <font style="color:rgba(0, 0, 0, 0.88);">Supports payment processing in the Direct Payment (Human-Present) scenario and the Delegated Payment (Human-Not-Present) scenario:</font><br/>+ Direct Payment (Human-Present): Process <font style="color:rgba(0, 0, 0, 0.88);">payment when the User is present in real time and confirms the specific transaction, using a valid Mandate and Payment Token.</font><br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Delegated Payment (Human-Not-Present): Process payment in Human-Not-Present scenarios, where the Agent requests and uses a Payment Token to complete the payment within the scope authorized by the Mandate.</font> |
| Wallet Service Domain | Delegated Task Management  | <font style="color:rgba(0, 0, 0, 0.88);">Enables the Mobile Payment Provider (MPP) to present and manage information for the User, including authorized Agents, Mandates, task status, budget utilization, and payment outcomes.</font> |
| | Delegation Limit Management | <font style="color:rgba(0, 0, 0, 0.88);">Enables the User to configure transaction limits, usage limits, and other control parameters that govern delegated authorization within the digital wallet.</font> |


## Business processes
### Scenario 1: Direct Payment (Human-Present)
#### Scenario description
<font style="color:rgba(0, 0, 0, 0.88);">This scenario applies where the User is present online in real time and the purchase target is clarified during the current interaction. The Agent interprets the User's purchase request, retrieves suitable Merchants and product information, presents candidate options to the User, and the User then selects the product and confirms the payment.</font>

<font style="color:rgba(0, 0, 0, 0.88);">In this scenario, the final transaction decision and payment confirmation remain under the User's real-time control.</font>

**<font style="color:rgba(0, 0, 0, 0.88);">Applicable Buyer Agent type</font>**<font style="color:rgba(0, 0, 0, 0.88);">: Platform Agent</font>

Example:

> <font style="color:rgba(0, 0, 0, 0.88);">The User says to the Agent: "Help me place an order for this watch." The Agent retrieves the relevant product information and presents it to the User. The User confirms the order and completes the payment.</font>
>

#### Main business process
<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784878794087-0aee7131-1e50-4836-8549-c54ba10b4244.png)

Figure 2. Main workflow of Direct Payment (Human-Present)

:::tips
**Phase 1: Preparation **

:::

**Step 1: ****<font style="color:rgba(0, 0, 0, 0.88);">Agent identity onboarding</font>**

The Agent is onboarded to the Alipay+ network in advance and completes the Know Your Agent (KYA) process to obtain the corresponding Agent ID.

This step **MUST **comply with the requirements for [Agent Onboarding and Management](intent#GKEnT) in the Intent Trust Domain.



:::tips
**Phase 2: ****<font style="color:rgba(0, 0, 0, 0.88);">Purchase intent capture</font>**

:::

**Step 2: User expresses purchase intent**

The User <font style="color:rgba(0, 0, 0, 0.88);">expresses a purchase request to the Agent using natural language. Through interaction with the User, the Agent clarifies the User's intent and converts the natural-language request into structured information, which is then used to generate</font> an `IMMEDIATE`-type Mandate.

This step **MUST** comply with the requirements for [Intent Capture and Structured Representation](intent#dy3Dj) in the Intent Trust Domain.

**Step 3: Wallet payment method binding**

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784621792479-094478c8-5ce7-4259-b0b1-3c45b2a7158f.png)

Figure 3. User experience sample of binding a wallet account

<font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent guides the User through the process of binding a digital wallet account. For the same Agent, the User is required to complete wallet binding only once before the first purchase. For subsequent transactions, the User delegates intents based on the existing binding relationship without repeatedly binding the wallet account.</font>

<font style="color:rgba(0, 0, 0, 0.88);">After the User completes the binding process, the Agent stores the L1 Assurance Data returned by the Credential Provider (CP).</font>

**<font style="color:rgba(0, 0, 0, 0.88);">L1 User Identity Assurance Data verification: </font>**<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ confirms the successful binding of the User's wallet account. It signs core binding data, including the ISP Public Key, with its private key and records the signed data as Assurance Data. The Assurance Data serves as verifiable evidence of the authorization relationship among the User, the MPP, and the Agent, and attests to the authenticity and validity of the User's identity information.</font>

This step** MUST** comply with the requirements for [Wallet Payment Method Binding](payment#aoQeg) in the Payment Service Domain.



:::tips
**Phase 3: Product and service query**

:::

**(OPTIONAL) Step 4: Service resource discovery and capability negotiation **

<font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent and Merchants </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> publish their respective profile information in advance. They may also conduct service resource discovery and exchange service capability information prior to transaction execution. Based on the resulting capability negotiation, the Buyer Agent identifies Merchants that meet the User's purchase requirements, payment compatibility requirements, and service fulfillment criteria.</font>

<font style="color:rgba(0, 0, 0, 0.88);">This step is outside the scope of the AMP specification and is not standardized by this protocol.</font>

<font style="color:rgba(0, 0, 0, 0.88);"></font>

**(OPTIONAL) Step 5: Product and service query and confirmation**

The Agent retrieves product or service information from candidate Merchants and presents suitable options to the User for confirmation.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.



**Step 6: User completes Mandate authorization**

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784621834257-5a2a7704-622b-4b60-9199-8206fa2a15e4.png)

Figure 4. User experience sample of confirming order and payment

The Agent guides the User to review and authorize the product order through the Trusted Authorization Surface. After the User completes identity verification, the Identity Signature Provider (ISP) signs the authorized intent using the ISP Key pair. The resulting `IMMEDIATE`-type Mandate serves as the authorization basis for subsequent Payment Token <font style="color:rgba(0, 0, 0, 0.88);">provisioning</font> and payment request verification. After Mandate authorization is completed, the Buyer Agent stores the L2 Assurance Data returned by the CP.

**L2 Mandate Authorization Assurance Data**: <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ records the identity verification result and signature result associated with the User's authorization of intent delegation. This provides evidence that the User has granted the Agent limited authority within a specified budget, validity period, product scope, Merchant scope, or other defined authorization boundaries.</font>

This step **MUST** comply with the requirements for [Mandate Authorization](intent#PY5i1) in the Intent Trust Domain.



:::tips
**Phase 4: Payment execution and Merchant fulfillment**

:::

**Step 7: Payment Token provision**

Based on the authorized User Intent issued Mandate, the Agent requests a Payment Token from Alipay+ through the CP. <font style="color:rgba(0, 0, 0, 0.88);">This step </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> comply with the requirements for </font>[Payment Token Request](payment#ggPzK)<font style="color:rgba(0, 0, 0, 0.88);"> in the Payment Service Domain.</font> 



**Step 8: Payment processing**

<font style="color:rgba(0, 0, 0, 0.88);">The Agent places the order with the Merchant and initiates the payment request by providing the Payment Token together with the L1 and L2 Assurance Data.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The Merchant is recommended to verify the L1 and L2 signatures before proceeding with the payment process. T</font><font style="color:rgba(0, 0, 0, 0.88);">he Merchant continues payment processing after the relevant verification checks have been successfully completed.</font><font style="color:rgba(0, 0, 0, 0.88);"> This verification step </font>**MUST**<font style="color:rgba(0, 0, 0, 0.88);"> comply with the requirements for </font>[Assurance Data Management ](intent#gwpyL)<font style="color:rgba(0, 0, 0, 0.88);">in the Intent Trust Domain.</font>

<font style="color:rgba(0, 0, 0, 0.88);">After verification succeeds, the Merchant forwards the Payment Token to Alipay+ through the Acquirer to complete the final payment. This step </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> comply with the requirements for </font>[Payment Processing in the Direct Payment (Human-Present)](payment#D9I5a)<font style="color:rgba(0, 0, 0, 0.88);"> in the Payment Service Domain.</font> 



**(OPTIONAL) Step 9: Merchant fulfillment**  
After confirming payment, the Merchant completes fulfillment, such as issuing tickets, shipping goods, or delivering services.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

### Scenario 2: Delegated Payment (Human-Not-Present)
#### Scenario description
<font style="color:rgba(0, 0, 0, 0.88);">This scenario applies to Human-Not-Present payment scenarios where the User is not online in real time during order placement and payment execution, but has explicitly delegated the purchase intent to the Agent during the initial interaction. At the outset, the User completes task definition, intent confirmation, identity verification, and authorization signing. Through this process, the User authorizes the Buyer Agent to perform product or service search, price comparison, transaction selection or confirmation, and payment execution within the defined authorization boundaries.</font>

**Applicable Buyer Agent type**: Platform Agent

Example:

> The User says to the Agent (e.g., Gemini), "Book me a flight to Kuala Lumpur tomorrow morning and a 5-star hotel there for 3 nights, with a total budget not exceeding 10,000 HKD." After the User completes identity verification and authorization as guided, the Agent proceeds to complete order placement and payment within the authorized scope, without requiring the User to be present at the time of payment execution.
>

#### Main business process
<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784878771365-6e6be282-b42a-4df2-830f-0ed57996c93a.png)

Figure 5. Main workflow of Delegated Payment (Human-Not-Present)

:::tips
**Phase 1: Preparation **

:::

**Step 1: ****<font style="color:rgba(0, 0, 0, 0.88);">Agent identity onboarding</font>**

The Agent is onboarded to the Alipay+ network in advance and completes the Know Your Agent (KYA) process to obtain the corresponding Agent ID.

This step **MUST **comply with the requirements for [Agent Onboarding and Management](intent#GKEnT) in the Intent Trust Domain.



:::tips
**Phase 2: ****<font style="color:rgba(0, 0, 0, 0.88);">Purchase intent capture</font>**** and wallet payment method binding**

:::

**Step 2: User expresses shopping Intent**

The User <font style="color:rgba(0, 0, 0, 0.88);">expresses a purchase request to the Agent using natural language. Through interaction with the User, the Agent clarifies the User's intent and converts the natural-language request into structured information, which is then used to generate</font> an `AUTONOMOUS`-type Mandate.

This step **MUST** comply with the requirements for [Intent Capture and Structured Representation](intent#dy3Dj) in the Intent Trust Domain.



**Step 3: Wallet payment method binding**

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784621851635-6c0d0685-a3cf-479e-b335-e5f7069226a7.png)

Figure 6. User experience sample of binding a wallet account

The Buyer Agent guides the User through the process of binding a digital wallet account. <font style="color:rgba(0, 0, 0, 0.88);">For the same Agent, the User is required to complete wallet binding only once before the first purchase. For subsequent transactions, the User delegates intents based on the existing binding relationship without repeatedly binding the wallet account.</font>

<font style="color:rgba(0, 0, 0, 0.88);">After the User completes the binding process, the Agent stores the L1 Assurance Data returned by the CP.</font>

**L1 User Identity Assurance ****<font style="color:rgba(0, 0, 0, 0.88);">Data verification</font>**: <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ confirms the successful binding of the User's wallet account. It signs core binding data, including the ISP Public Key, with its Private Key and records the signed data as Assurance Data. The Assurance Data serves as verifiable evidence of the authorization relationship among the User, the MPP, and the Agent, and attests to the authenticity and validity of the User's identity information.</font>

This step **MUST** comply with the requirements for [Wallet Payment Method Binding](payment#aoQeg) in the Payment Service Domain.



**Step 4: User completes Mandate authorization confirmation**

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784621866739-1ee7d204-d8ef-49d6-9caf-24fd85175675.png)

Figure 7. User experience sample of confirming an order

<font style="color:rgba(0, 0, 0, 0.88);">The Agent guides the User to review and authorize the product order through the Trusted Authorization Surface. After the User completes identity verification, the ISP signs the authorized intent using the ISP Key pair. The resulting </font>`<font style="color:rgba(0, 0, 0, 0.88);">AUTONOMOUS</font>`<font style="color:rgba(0, 0, 0, 0.88);">-type Mandate serves as the authorization basis for subsequent Payment Token provisioning and payment request verification. After Mandate authorization is completed, the Buyer Agent stores the L2 Assurance Data returned by the CP.</font>

**L2 Mandate Authorization Assurance ****<font style="color:rgba(0, 0, 0, 0.88);">Data verification</font>**: <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ records the identity verification result and signature result associated with the User's authorization of intent delegation. This provides evidence that the User has granted the Agent limited authority within a specified budget, validity period, product scope, Merchant scope, or other defined authorization boundaries.</font>

This step **MUST** comply with the requirements for [Mandate Authorization](intent#PY5i1) in the Intent Trust Domain.



:::tips
**Phase 3: Product and service query**

:::

**(OPTIONAL) Step 5: Service resource discovery and capability negotiation **

<font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent and Merchants </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> publish their respective profile information in advance. They may also conduct service resource discovery and exchange service capability information prior to transaction execution. Based on the resulting capability negotiation, the Buyer Agent identifies Merchants that meet the User's purchase requirements, payment compatibility requirements, and service fulfillment criteria.</font>

<font style="color:rgba(0, 0, 0, 0.88);">This step is outside the scope of the AMP specification and is not standardized by this protocol.</font>



**(OPTIONAL) Step 6: Product and service query and confirmation**

The Agent retrieves product or service information from candidate Merchants and presents suitable options to the User for confirmation.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.



:::tips
**Phase 4: Payment execution and Merchant fulfillment**

:::

**Step 7: Payment Token provision**

Based on the User-authorized `AUTONOMOUS`-type Mandate and the selected product order information, the Agent signs the Payment Token request using the Agent Key and submits the request to Alipay+ through the CP.

**L3 Payment Token Request Assurance ****<font style="color:rgba(0, 0, 0, 0.88);">Data verification</font>**: Alipay+ records the Agent's signing result associated with the Payment Token request as Assurance Data. The data serves as <font style="color:rgba(0, 0, 0, 0.88);">verifiable evidence that the Agent completed product selection, order initiation, or payment initiation in accordance with the User-authorized intent and within the scope of the issued Mandate.</font>

This step **MUST** comply with the requirements for [Payment Token Request](payment#ggPzK) in the Payment Service Domain.



**Step 8: Payment processing**

The Agent submits the order and payment request to the Merchant, including the Payment Token and L1, L2, and L3 Assurance Data. The Merchant is recommended to verify the L1, L2, and L3 signatures and related Assurance Data. After the <font style="color:rgba(0, 0, 0, 0.88);">verification checks have been successfully completed, the Merchant then </font>proceeds with payment processing.

<font style="color:rgba(0, 0, 0, 0.88);">After successful verification, the Merchant forwards the Payment Token to Alipay+ through the Acquirer to complete the final payment.</font>

This step **MUST** comply with the requirements <font style="color:rgba(0, 0, 0, 0.88);">for </font>[Assurance Data Management ](intent#gwpyL)<font style="color:rgba(0, 0, 0, 0.88);">in</font> the Intent Trust Domain and for [Payment Processing in Delegated Payment (Human-Not-Present)](payment#JDQLL) in the Payment Service Domain.



**(OPTIONAL) Step 9: Merchant fulfillment**  
After confirming payment, the Merchant completes fulfillment, such as issuing tickets, shipping goods, or delivering services.

This step is outside the scope of the AMP specification and is not specifically standardized by this protocol.

