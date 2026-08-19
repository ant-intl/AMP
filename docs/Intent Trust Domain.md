## Overview
<font style="color:rgba(0, 0, 0, 0.88);">The Intent Trust Domain is the core trust infrastructure of the Agentic Mobile Protocol (AMP). It establishes the standards for Agent identity onboarding, converts a User's natural-language transaction intent into an authorizable, verifiable, and structured Mandate, and ensures that all Agent-initiated transactions remain within the boundaries expressly authorized by the User through end-to-end Intent Guard controls. It also maintains a three-layer trust Assurance Data to support dispute resolution.</font>

## Scope of responsibility
This Intent Trust Domain covers the following:

+ <font style="color:rgba(0, 0, 0, 0.88);">Agent and Credential Provider (CP) identity onboarding and Know Your Agent (KYA) due diligence standards;</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Capture, semantic interpretation, clarification, and structured Mandate generation based on the User's original intent;</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Presentation of the Mandate through a Trusted Authorization Surface, followed by User identity verification and signature confirmation;</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Definition and management of the Mandate lifecycle;</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">End-to-end Intent Guard through four types of pre-verification;</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Maintenance of three-layer Assurance Data as evidence for dispute resolution.</font>

## Capability list
| **Capability** | **Description** |
| --- | --- |
| Agent Onboarding and Management | <font style="color:rgba(0, 0, 0, 0.88);">Defines the requirements for Agent onboarding, including Agent identity verification, capability registration, key management, and trust assessment prior to accessing the AMP framework and the Agent lifecycle management.</font> |
| Intent Capture and Structured Representation | <font style="color:rgba(0, 0, 0, 0.88);">Specifies how User Intent is captured, clarified, and represented in a structured format, providing the foundation for Mandate authorization and subsequent validation.</font> |
| Mandate Authorization | <font style="color:rgba(0, 0, 0, 0.88);">Defines how a Mandate is presented to the User, confirmed, issued, and recorded, together with the resulting authorization outcome, via a Trusted Authorization Surface.</font> |
| Mandate Lifecycle Management | <font style="color:rgba(0, 0, 0, 0.88);">Governs the end-to-end lifecycle of a Mandate, including creation, activation, revocation, expiration, and closure.</font> |
| End-to-End Intent Guard Management | <font style="color:rgba(0, 0, 0, 0.88);">Performs phased validation throughout subsequent Agent transaction and payment flows against the User-confirmed Mandate boundaries, ensuring that all related requests remain within the User's authorized scope.</font> |
| Assurance Data Management | <font style="color:rgba(0, 0, 0, 0.88);">Defines the requirements for capturing and maintaining Assurance Data of critical events, including identity verification, authorization, signing, credential provisioning, and execution outcomes, to support accountability, auditability, and dispute resolution.</font> |


## <font style="color:rgba(0, 0, 0, 0.88);">Agent Onboardin</font>g and Management
<font style="color:rgba(0, 0, 0, 0.88);">To ensure the secure, compliant, and trustworthy operation of the AMP protocol, Alipay+ establishes a unified Agent onboarding and management system. This capability defines Alipay+ requirements for protocol participants, including qualifications and standards, onboarding processes, and lifecycle management of Agents.</font>

### <font style="color:rgba(0, 0, 0, 0.88);">General rules</font>
<font style="color:rgba(0, 0, 0, 0.88);">These rules apply to CPs and Agents participating in the AMP ecosystem, and are designed to build and maintain a secure, compliant, and trustworthy payment service environment. The AMP ecosystem is operated under the governance of Alipay+ and supports collaboration among multiple participants. CPs serve as technical intermediaries, assisting their downstream Agents with system integration and other related services. Agents act on behalf of Users to initiate payment and order requests.</font>

Under AMP, an Agent is onboarded to Alipay+ through a CP. All Agents and related participating entities **<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> comply with the onboarding standards and compliance requirements set forth in these management rules. </font>

<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ retains the full authority to manage the entire lifecycle of CPs and their downstream Agents. </font><font style="color:rgba(0, 0, 0, 0.88);">This includes onboarding reviews, operational monitoring, risk management, compliance oversight, and violation handling. CPs </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> comply with Alipay+ management requirements and are responsible for providing compliance guidance and ongoing supervision to their downstream Agents. </font>

<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ retains ultimate management and enforcement authority over CPs and their downstream Agents.</font><font style="color:rgba(0, 0, 0, 0.88);"> This authority is intended to ensure that all participants in the AMP ecosystem remain legitimate, compliant, and trustworthy, and that payment interactions remain secure and stable.</font>

### Alipay+ requirements for Agent qualification
<font style="color:rgb(20, 20, 20);">Alipay+ defines the onboarding standards and procedures applicable to Agents. </font><font style="color:rgb(20, 20, 20);">Any Agent seeking access to Alipay+ </font>**<font style="color:rgb(20, 20, 20);">MUST</font>**<font style="color:rgb(20, 20, 20);"> complete the onboarding review in accordance with the requirements specified herein.</font><font style="color:rgb(20, 20, 20);"> This protocol currently applies to Platform Agents, namely Agents developed and operated by legally qualified enterprises or institutions that provide transaction proxy services to the public. Upon successful onboarding, Agents will be brought within the scope of the dynamic trust assessment framework, as further described in </font>[Agent lifecycle management](#BNvjm)<font style="color:rgb(20, 20, 20);">.</font>

#### Step 1: Agent capability and qualification review
<font style="color:rgb(20, 20, 20);">CPs, as the actual reviewing party, </font>**<font style="color:rgb(20, 20, 20);">MUST</font>**<font style="color:rgb(20, 20, 20);"> conduct a substantive review and verification </font><font style="color:rgb(20, 20, 20);">of the Agent's </font><font style="color:rgba(0, 0, 0, 0.88);">capabilities and supporting technical mechanisms</font><font style="color:rgb(20, 20, 20);"> to ensure that the Agent meets the relevant security, compliance, and technical requirements. </font><font style="color:rgba(0, 0, 0, 0.88);">Only Agents that successfully pass this review </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> proceed to the subsequent onboarding steps.</font><font style="color:rgb(20, 20, 20);"> </font>

<font style="color:rgba(0, 0, 0, 0.88);">The review </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);">, </font><font style="color:rgba(0, 0, 0, 0.88);">at a minimum, cover the following: </font>

+ <font style="color:rgba(0, 0, 0, 0.88);">The Agent Profile</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">KYC and entity qualification verification </font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Anti-money laundering (AML) and sanctions compliance</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Cybersecurity and data security capabilities</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Privacy compliance policies</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Anti-bribery and anti-corruption (ABAC) compliance</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">AI compliance capabilities</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The management capability for prohibited transaction scenarios</font>

#### Step 2: Assignment of identity identifier 
<font style="color:rgba(0, 0, 0, 0.88);">For each Agent instance that has submitted complete onboarding materials and successfully passed the onboarding review, Alipay+ will assign a unique Agent ID. This Agent ID serves as the Agent's unique identity identifier within the </font><font style="color:rgba(0, 0, 0, 0.88);">AMP ecosystem </font><font style="color:rgba(0, 0, 0, 0.88);">and is used for routing, permission validation, and audit traceability.</font>

#### Step 3: Generation and registration of asymmetric key pair 
1. **<font style="color:rgba(0, 0, 0, 0.88);">Key Generation</font>****<font style="color:rgba(0, 0, 0, 0.88);">:</font>**<font style="color:rgba(0, 0, 0, 0.88);"> The Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> generate an asymmetric public-private key pair in a secure local environment, such as a Trusted Execution Environment (TEE) or Hardware Security Module (HSM), in accordance with protocol requirements, such as RSA-4096 or ECC P-256.</font>
2. **<font style="color:rgba(0, 0, 0, 0.88);">Public Key Registration</font>**<font style="color:rgba(0, 0, 0, 0.88);">:</font><font style="color:rgba(0, 0, 0, 0.88);"> The key pair is generated locally by the Agent. The Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> submit the public key to Alipay+ through a secure channel for </font><font style="color:rgba(0, 0, 0, 0.88);">verification, registration, and storage.</font>
3. **<font style="color:rgba(0, 0, 0, 0.88);">Private Key Custody and Use</font>**<font style="color:rgba(0, 0, 0, 0.88);">: The Agent Private Key </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> remain</font><font style="color:rgba(0, 0, 0, 0.88);"> under the Agent's exclusive control and be subject to strict safeguarding measures</font><font style="color:rgba(0, 0, 0, 0.88);">. At the Payment Token request stage, the Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**<font style="color:rgba(0, 0, 0, 0.88);">use its Private Key to digitally sign the request payload.</font>

### Alipay+ requirements for <font style="color:rgba(0, 0, 0, 0.88);">CP</font><font style="color:rgb(20, 20, 20);"> qu</font>alification and management
<font style="color:rgb(20, 20, 20);">The CP serves as the primary party responsible for Agent onboarding and </font>**<font style="color:rgb(20, 20, 20);">MUST</font>**<font style="color:rgb(20, 20, 20);"> undertake review, monitoring, and risk-handling responsibilities on behalf of Alipay+.</font><font style="color:rgb(20, 20, 20);"> Alipay+'s core requirements for CPs cover three dimensions:</font>

+ **<font style="color:rgb(20, 20, 20);">Onboarding Review Responsibility</font>**<font style="color:rgb(20, 20, 20);">: Conduct onboarding reviews of downstream Agents in accordance with regulatory requirements, </font><font style="color:rgb(20, 20, 20);">verify and retain relevant qualification documentation, and ensure compliance at the source.</font>
+ **<font style="color:rgb(20, 20, 20);">Ongoing Monitoring Obligation</font>**<font style="color:rgb(20, 20, 20);">: Establish a regular monitoring mechanism to continuously track and assess the compliance status and risk profile of downstream Agents, and proactively identify and address risk events.</font>
+ **<font style="color:rgb(20, 20, 20);">Information Coordination Mechanism</font>**<font style="color:rgb(20, 20, 20);">: Where a risk event is triggered or where required by applicable laws or regulations, Alipay+ reserves the right to request from CPs the relevant Agent review materials and operational data.</font>

**<font style="color:rgba(0, 0, 0, 0.88);">CP Onboarding to Alipay+</font>**

<font style="color:rgba(0, 0, 0, 0.88);">Any institution applying to become a CP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**<font style="color:rgba(0, 0, 0, 0.88);">submit a formal onboarding application to Alipay+. Alipay+ will assess the applicant across multiple dimensions, including KYC, cybersecurity capabilities, privacy compliance policies, </font><font style="color:rgba(0, 0, 0, 0.88);">anti-bribery and anti-corruption (ABAC) compliance, and the management capability for prohibited transaction scenarios.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Upon successful completion of the review, the institution will be approved as a CP, and Alipay+ will assign a unique identifier to serve as its formal identity credential within the AMP ecosystem. In subsequent business interactions, the CP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> use this identifier for identification and invocation in accordance with Alipay+ requirements.</font>

**<font style="color:rgba(0, 0, 0, 0.88);">CP Reports Agent Onboarding to Alipay+</font>**

<font style="color:rgba(0, 0, 0, 0.88);">CPs </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> fulfill their qualification verification obligations for downstream Agents. Upon completion of such verification, the CP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> submit to Alipay+ both a qualification verification report and a letter of authenticity commitment. These documents </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> include the review procedures performed, verification results, compliance conclusions, and a commitment to comply with applicable laws and regulations in relation to each Agent's qualifications.</font>

### Agent lifecycle management
<font style="color:rgba(0, 0, 0, 0.88);">Upon completion of the onboarding process, Agents are brought into Alipay+'s ongoing dynamic trust assessment framework. Alipay+ applies a control mechanism based on continuous risk monitoring and dynamic intervention </font><font style="color:rgba(0, 0, 0, 0.88);">to continuously assess and manage Agents throughout their lifecycle. The CP </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHALL </font>**<font style="color:rgba(0, 0, 0, 0.88);">bear joint and several liability for any non-compliance by their downstream Agents.</font>

#### Trust assessment mechanism
<font style="color:rgba(0, 0, 0, 0.88);">Once an Agent is activated, </font><font style="color:rgba(0, 0, 0, 0.88);">Alipay+ and the CP continuously monitor the Agent's transaction activities</font><font style="color:rgba(0, 0, 0, 0.88);">, dynamically assess its risk level, and adjust its permission tier accordingly. Assessment dimensions include transaction compliance, consistency of authorization, abnormal behavior patterns, changes in entity qualifications, runtime environment security, </font><font style="color:rgba(0, 0, 0, 0.88);">and the accuracy of intent interpretation.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> send alerts for Agents and the CP based on predefined thresholds</font><font style="color:rgba(0, 0, 0, 0.88);"> and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> apply differentiated measures according to the applicable risk level.</font>

#### Annual review
<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ maintains an annual review mechanism for certified CPs and Agents.</font><font style="color:rgba(0, 0, 0, 0.88);"> Agents that successfully pass the annual review </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY </font>**<font style="color:rgba(0, 0, 0, 0.88);">continue using the Agent ID assigned by Alipay+.</font>

<font style="color:rgba(0, 0, 0, 0.88);">All assessment records, control measures or enforcement actions, and the supporting basis for such measures or actions </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be formally documented and retained by Alipay+ for no less than the applicable statutory retention period, and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be made available for dispute resolution and regulatory inspection or audit.</font>

## User intent and mandate management
User Intent and Mandate Management <font style="color:rgba(0, 0, 0, 0.88);">converts the commercial requirements expressed by the User to the Agent into structured content that includes task objectives, budget constraints, authorization validity periods, and execution boundaries. Once confirmed by the User, it generates authorization credentials that can be referenced by subsequent transactions in the payment flows. This ensures that all Agent actions throughout the Mandate lifecycle remain within the authorization scope explicitly confirmed by the User.</font>

### Intent Capture and Structured Representation
Intent Capture and Structured Representation transforms transaction requirements expressed by the User<font style="color:rgba(0, 0, 0, 0.88);">—whether through natural language, interactive cards, or other interaction mechanisms—into a structured Mandate that can be reviewed and confirmed by the User, and subsequently used for authorization, transaction validation, and payment processing.</font>

<font style="color:rgba(0, 0, 0, 0.88);">A Mandate is a protocol object that encapsulates the User's commercial intent and authorization boundaries. It defines the task the User authorizes the Agent to perform, the scope within which the Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> act, and the constraints that subsequent transaction and payment requests </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> observe. A Mandate </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> support direct payment scenarios where the User is actively present, as well as delegated payment scenarios where the Agent continues execution based on the User's prior authorization.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Different Buyer Agents </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> implement distinct User interaction models and intent-processing logic according to their product design and user experience requirements. However, the resulting Mandate </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> clearly specify the task objective, transaction objects, budget or spending limit, validity period, applicable scope, and any other authorization boundaries necessary to support subsequent User authorization confirmation, payment validation, risk assessment, and dispute resolution.</font>

#### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability  ** |
| --- | --- |
| User | <font style="color:rgba(0, 0, 0, 0.88);">Expresses the commercial intent, reviews the structured Mandate, and provides explicit confirmation or authorization.</font> |
| Buyer Agent | <font style="color:rgba(0, 0, 0, 0.88);">Captures and interprets the User's transaction intent, clarifies missing or ambiguous information, and generates a structured Mandate in accordance.</font> |
| Credential Provider (CP) | <font style="color:rgba(0, 0, 0, 0.88);">References the authorized Mandate and supports their use in subsequent authorization and payment flows.</font> |
| Alipay+ | <font style="color:rgba(0, 0, 0, 0.88);">Defines the protocol rules, data specifications, verification requirements for Mandate creation, confirmation, and usage.</font> |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The User is able to express transaction needs through interaction methods supported by the Buyer Agent.
+ The Buyer Agent is capable of understanding the User's requirements, identifying and clarifying key transaction information, and producing a structured Mandate t<font style="color:rgba(0, 0, 0, 0.88);">hat accurately reflects the User's commercial intent.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ has made available the applicable protocol rules, data standards, and validation requirements governing Mandate generation, confirmation, and subsequent usage.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The CP is capable of referencing the confirmed Mandate in subsequent authorization, credential issuance, or payment flows.</font>

#### Mandate types
| **Type** | **Description** | **Applicable Scenario** |
| :--- | :--- | :--- |
| `IMMEDIATE` | **Instant Confirmation Authorization**: The transaction target, Merchant, amount, and other core transaction conditions are fully determined at the time of authorization. The User provides real-time confirmation for the specific payment. | Single-transaction scenarios where the User is present and confirms the payment in real time. |
| `AUTONOMOUS` | **Directed Delegation Authorization**: The User authorizes an Agent to execute a clearly defined purchase objective, with a specific Merchant, purchase target, or other explicit transaction boundaries. The Agent **MAY** complete subsequent execution within the authorized scope without requiring real-time User participation at the time of payment execution. | Scenarios where the User's purchase objective is clear and the Agent is permitted to perform subsequent activities, such as search, price comparison, order placement, and payment within the authorized boundaries. The User is not required to participate in the payment in real time. |


##### Data structure and fields
| **Type** | **Core field** |  | **Description** |
| :--- | --- | --- | --- |
| `IMMEDIATE`<br/><br/><br/><br/> | IntentRaw | raw | Original intent content |
| | Checkout | totalAmount | Total amount of products |
| | | totalCurrency | Currency of the total amount |
| | | Merchant | Merchant information |
| | | Goods | Product information |
| `AUTONOMOUS`<br/><br/><br/><br/> | IntentRaw | raw | Original intent content |
| | IntentConstraints | budgetAmount | Total budget amount for a Mandate |
| | | budgetCurrency | Currency of the total budget amount |
| | | merchantNameList | Merchant list authorized for a Mandate |
| | | merchantMccList | MCC list of Merchants authorized for a Mandate |


#### Mandate extension information
A Mandate **MAY** include extension information based on the applicable business scenario. <font style="color:rgba(0, 0, 0, 0.88);">Such information supplements the User's authorization by further defining transaction conditions, merchant scope, fulfillment requirements, delivery details, Agent behavioral constraints, risk-control requirements, or other scenario-specific restrictions. Extension information serves as additional clarification of the Mandate boundaries.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Extension information </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST NOT</font>**<font style="color:rgba(0, 0, 0, 0.88);"> modify the core semantics of the Mandate, bypass any authorization conditions confirmed by the User, network risk-control requirements, or restrictions applicable to Payment Token usage.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Standard extension information under this protocol </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> include, but is not limited to, the following categories:</font>

| **Extension category** | **Description** | **Examples** |
| --- | --- | --- |
| Commercial Transaction | <font style="color:rgba(0, 0, 0, 0.88);">Provides supplementary transaction constraints that enable participants to determine whether a transaction is consistent with the User's authorization.</font> | + Maximum amount per-transaction   <br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Minimum amount per transaction</font>   <br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Specified region or country of the Merchants</font>  <br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Merchant allowlist</font>   <br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Merchant blocklist</font>   <br/>+ <font style="color:rgba(0, 0, 0, 0.88);">Delivery address information</font> |
| Agent Behavior | <font style="color:rgba(0, 0, 0, 0.88);">Defines behavioral constraints or handling rules applicable to the Agent during task execution and payment processing.</font> | + Payment frequency limit during the Mandate validity period   <br/>+ Handling rules after payment failure   <br/>+ Maximum retry attempts after failure |


#### Processing requirements
After receiving the User's natural-language transaction request, the Buyer Agent **SHOULD** interpret the User's original intent in the context of the current interaction, and generate the appropriate type of Mandate once the necessary information is available.

The Mandate **SHOULD** capture the key elements of the User's requirements, including the task objective, budget, validity period, product or service scope, Merchant scope, payment method, and the wallet account to be used for this transaction, together with other necessary conditions and boundaries. Before User confirmation, such information constitutes only pending Mandate content and has no authorization effect. Only after the User confirms and authorizes the Mandate, it can serve as the basis for Payment Token request, payment request validation, and subsequent Intent Guard.

If the User's original intent is ambiguous, incomplete, or internally inconsistent, the Buyer Agent **SHOULD** prompt the User to provide, clarify, or confirm key information until the conditions for generating a Mandate are met.

If a generated Mandate is rejected by the CP, Alipay+, or the Mobile Payment Provider (MPP) due to insufficient information, incomplete constraints, or non-compliance with applicable rules, the Buyer Agent **MAY** request additional confirmation from the User based on the returned rejection reason and, upon User confirmation, regenerate or update the Mandate accordingly.

### Mandate Authorization
Mandate Authorization established the authorization basis to be referenced by subsequent transaction and payment flows after the User has reviewed and confirmed the structured representation of the original intent.

This capability follows the generation of a pending Mandate through the Intent Capture and Structured Representation capability. The MPP** MUST** perform S1 Mandate Creation Pre-Verification on the pending Mandate to confirm that the authorization content is sufficiently clear, complete, and compliant with the User's settings and applicable rules. <font style="color:#000000;">The Mandate</font>**<font style="color:#000000;"> MAY</font>**<font style="color:#000000;"> proceed only after this pre-verification is successfully completed. If the pre-verification fails, the Mandate </font>**<font style="color:#000000;">MUST NOT</font>**<font style="color:#000000;"> be presented to the User for confirmation and authorization.</font>

After the S1 pre-verification succeeds, Alipay+ **MUST** present the pending Mandate content to the User through a Trusted Authorization Surface. Upon User confirmation, the MPP completes User identity verification, and the ISP signs the Mandate. The User's original natural-language input **MUST NOT** be used directly as the signing object for this capability. Instead, the signing scope **MUST** be limited to the finalized Mandate content that can be understood by the User and verified by participants in subsequent processes.

#### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Reviews and confirms the pending Mandate content, and completes authorization through wallet-side identity verification and signing. |
| Buyer Agent | Submits the pending Mandate that has passed creation pre-verification to the authorization confirmation flow and receives the authorization result for subsequent execution. |
| Alipay+ | Provides or hosts the Trusted Authorization Surface to present the pending Mandate content to the User. Alipay+ also provides creation pre-verification results, signature result recording, validation, and Mandate authorization status management. |
| Mobile Payment Provider (MPP) | Provides User identity verification capabilities and returns the User's authorization result to the relevant flow. |
| Identity Signature Provider (ISP) | Serves as the core role responsible for providing signature endorsement of the User intent. After the User completes Mandate authorization, the ISP signs the User intent and completes the associated identity verification result using ISP Private Key, thus generating a tamper-resistant and verifiable Mandate proof. |
| Credential Provider (CP) | Supports the transmission of the Mandate, signing materials, and authorization results based on the integration approach. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The Mandate has been generated by the preceding stage and contains task objectives, authorization scope, validity period, and necessary constraint information required for User confirmation.
+ The Mandate has been associated with the relevant User, Buyer Agent, and authorization scenario.
+ The Buyer Agent has an identity identifier that can be recognized by Alipay+.
+ Alipay+ provides a Trusted Authorization Surface and is capable of recording authorization results and maintaining Mandate status.
+ The MPP is capable of performing User identity verification. 
+ The ISP is capable of signing a Mandate.

#### Processing requirements
##### **Mandate presentation**
<font style="color:#000000;">For pending Mandates that have passed </font>S1 pre-verification<font style="color:#000000;">, Alipay+</font>**<font style="color:#000000;"> MUST </font>**<font style="color:#000000;">present the authorization content to the User through a Trusted Authorization Surface.</font> <font style="color:rgba(0, 0, 0, 0.88);">The information presented </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> enable the User to clearly understand the transaction objective, authorization scope, payment or funding limits, validity period, authorized Agent, and other key execution constraints associated with the authorization.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Different Mandate types </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> apply different presentation priorities based on their business purpose and authorization characteristics:</font>

| **Mandate Type** | **Presentation Priority** |
| --- | --- |
| `IMMEDIATE` | Emphasize the key information for the specific real-time transaction, including the authorized Agent, product or service, Merchant, amount, currency, and payment-related details. |
| `AUTONOMOUS` | <font style="color:rgba(0, 0, 0, 0.88);">Emphasize the pre-authorized delegation scope, including the task objective, authorized Agent, budget limit, validity period, and other execution constraints.</font> |


##### **User identity verification and authorization confirmation**
<font style="color:rgba(0, 0, 0, 0.88);">After reviewing the pending Mandate content on the Trusted Authorization Surface, the User </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> provide explicit confirmation of the authorization.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The Mandate content </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be presented in a manner that is clear and understandable to the User, enabling the User to make an informed decision on whether to authorize the Agent to execute the task within the boundaries defined by the Mandate.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> perform User identity verification based on its security capabilities, the User's risk profile, and applicable Alipay+ requirements.</font>

<font style="color:rgba(0, 0, 0, 0.88);">If the User does not confirm the authorization content, fails identity verification, or actively rejects the authorization, the Mandate </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST NOT</font>**<font style="color:rgba(0, 0, 0, 0.88);"> enter the </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> state and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST NOT</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be used as the authorization basis for any subsequent transaction or payment flow.</font>

##### **Mandate signing and generation**
<font style="color:rgba(0, 0, 0, 0.88);">After the User confirms the Mandate content and the MPP completes User identity verification, the </font><font style="color:rgba(0, 0, 0, 0.88);">ISP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> use</font><font style="color:rgba(0, 0, 0, 0.88);"> the ISP Private Key to sign the Mandate content confirmed by the User.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> return the User identity verification result and any required authorization materials to </font>**<font style="color:rgba(0, 0, 0, 0.88);">Alipay+</font>**<font style="color:rgba(0, 0, 0, 0.88);">.</font>

##### **<font style="color:#000000;">Mandate verification and Assurance Data retention</font>**
<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> verify the signature result and the required authorization materials. Upon successful verification, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> update the Mandate status to </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);">.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Only a Mandate in the </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> state</font>**<font style="color:rgba(0, 0, 0, 0.88);"> MAY </font>**<font style="color:rgba(0, 0, 0, 0.88);">serve as the authorization basis for subsequent Payment Token requests, payment request validation, and Assurance Data records.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> generate and maintain the L2 Mandate Authorization Assurance Data. This Assurance Data provides evidence that the User has confirmed the authorization content contained in the Mandate and has authorized the Agent to initiate subsequent transaction requests within the confirmed authorization boundaries.</font>

<font style="color:#000000;">For details, refer to </font>[S1 Mandate Creation Pre-Verification](intent#vDQdX) and [L2 Mandate Authorization Assurance Data](intent#Y23o3)<font style="color:#000000;">.</font>

### Mandate lifecycle management
Mandate Lifecycle Management standardizes the status semantics of a Mandate from creation through User authorization, active use, and termination. It enables all participants referencing the same Mandate to make consistent status-based judgments about whether the Mandate remains valid and usable.

A Mandate is the foundational object through which the User authorizes the Agent to perform specified transaction and payment-related activities. Alipay+, as the Mandate status maintainer, **MUST** record the creation, authorization, activation, revocation, expiration, and closure of each Mandate, and return the latest status when participants reference or invoke the Mandate.

#### Mandate lifecycle status
A Mandate **MAY** be in one of the following states during its lifecycle:

| **State** | **State name** | **Description** | **Available for payment-related processing** |
| --- | --- | --- | --- |
| `inactive` | Pending Authorization | The Mandate has been created, but the User has not yet completed identity verification or authorization confirmation. | No |
| `activated` | Activated | The User has completed authorization. The Agent can continue executing tasks within the authorization boundaries. | Yes |
| `revoked` | Revoked | The User has actively revoked the authorization, or the payment system has cancelled <font style="color:rgba(0, 0, 0, 0.88);">the authorization in accordance with applicable rules.</font> | No |
| `expired` | Expired | The Mandate has exceeded its authorization validity period, or the pending authorization has timed out. | No |
| `finished` | Closed | The task associated with the Mandate has been completed, the authorization budget has been exhausted, or closure conditions defined by Alipay+ rules have been met. | No |


The `revoked`, `expired`, and `finished` status are terminal statuses. Once a Mandate enters a terminal state, it **MUST NOT** revert to `inactive` or `activated`, and **MUST NOT** be used for any subsequent payment-related processing.

#### Usage rules
+ <font style="color:rgba(0, 0, 0, 0.88);">A Mandate </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be used for payment-related task processing and subsequent payment flows only when it is in the </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> status.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">When invoking an </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> Mandate, participants </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> still evaluate the transaction content, authorization boundaries, Payment Token status, and applicable risk-control rules to determine whether the current request remains within the authorization scope confirmed by the User. Subsequent processing </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> proceed only if the transaction content is consistent with the User-confirmed authorization boundaries.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">A Mandate in the </font>`inactive`<font style="color:rgba(0, 0, 0, 0.88);"> status indicates that the User has not yet completed authorization confirmation. It </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST NOT</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be used for Payment Token request, payment request validation, or debit processing.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">A Mandate in the </font>`revoked`<font style="color:rgba(0, 0, 0, 0.88);">, </font>`expired`<font style="color:rgba(0, 0, 0, 0.88);">, or </font>`finished`<font style="color:rgba(0, 0, 0, 0.88);"> status indicates that the authorization is no longer valid or usable. If a participant submits a request based on such Mandate, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> reject the request and return the corresponding Mandate status result.</font>

## End-to-End Intent Guard Management
Intent Guard is a risk-control capability through which the Mobile Payment Provider and Alipay+, based on the User-confirmed Mandate authorization boundaries, perform phased validation and control across the end-to-end Agent-initiated transactions and payment processing.

Intent Guard does not replace Mandate issuance, payment processing, or Assurance Data records. Its role is to continuously verify at critical stages whether the current request remains consistent with the User's original authorization, and to provide supporting evidence for subsequent risk control, audit, and dispute resolution.

In the end-to-end Intent Guard process, Alipay+ provides supporting information such as Mandate status, authorization boundaries, cumulative amounts, currency handling, credential status, and risk rules. This assists the MPP, Agent, Merchant, and Acquirer in maintaining consistent judgment throughout the transaction flow.

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Acts as the source of authorization by confirming the budget, validity period, Merchant or product scope, and other authorization boundaries in the Mandate. |
| Mobile Payment Provider (MPP) | Serves as the primary Intent Guard decisioning and enforcement role. At each relevant stage, including authorization creation, transaction execution, payment processing, and final debit, the MPP determines whether the current request remains consistent with the User's authorization boundaries. |
| Alipay+ | Provides supporting information, including Mandate status, authorization boundaries, cumulative amounts, currency handling, credential status, and risk rules, to assist all participants in maintaining consistent judgment across the transaction and payment flow. |
| Buyer Agent | Executes tasks within the User's authorization boundaries and provides necessary transaction information when initiating Mandate creation, transaction execution, or payment-related requests. |
| Merchant or Seller Agent | Provides product, service, pricing, order, and fulfillment information to support the MPP in determining whether the current transaction is consistent with the User's authorization. |


**Preconditions**

Before this capability is invoked, the following requirements **SHOULD** be met:

+ <font style="color:rgba(0, 0, 0, 0.88);">The Mandate has been created through structured representation and contains the authorization information required for the applicable scenario, including the budget limit, validity period, Merchant or product scope, and payment method.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The MPP is capable of identifying and associating the relevant User, Buyer Agent, Mandate, and Payment Token.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ is capable of providing supporting information, including Mandate status, authorization boundaries, accumulated amounts, currency handling rules, credential status, and applicable risk control rules.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Except for pre-verification performed before Mandate creation or authorization activation, any subsequent operation involving Payment Token request, payment request processing, or wallet debit requires the Mandate to be in the </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> status and available for continued use.</font>

### Intent Guard capability scope 
<font style="color:rgba(0, 0, 0, 0.88);">Intent Guard is applied in</font><font style="color:rgba(0, 0, 0, 0.88);"> key stages </font><font style="color:rgba(0, 0, 0, 0.88);">as an Agent-initiated transaction progresses. The MPP, acting as the primary decisioning and enforcement party, </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**<font style="color:rgba(0, 0, 0, 0.88);">determine at each stage whether the transaction remains within the User-confirmed authorization boundaries. Alipay+ provides Mandate status, rule validation, and Assurance Data as support.</font>

#### S1 Mandate Creation Pre-Verification
<font style="color:rgba(0, 0, 0, 0.88);">Before a Mandate is created or activated, the MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> verify that the authorization content is clear, complete, and compliant with the User's preferences and applicable rules. This verification is designed to ensure that the User's authorization boundaries, including the budget limit, validity period, transaction scope, and the permissions granted to the Agent, are sufficiently defined before the authorization is presented to the User for confirmation. </font>

#### S2 Payment Token Request Pre-Verification 
When the Agent selects specific products or services based on the Mandate and requests a Payment Token, the MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**verify whether the transaction remains within the User's authorization scope. This verification focuses on whether the transaction is consistent with the budget, validity period, Merchant scope, product or service scope, and payment method, thus preventing the Agent from deviating from the User's original intent during execution.

#### S3 Payment Request Pre-Verification 
When the Merchant or Seller Agent submits a payment request, the MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**verify whether the request is consistent with the transaction order bound to the Payment Token. This verification helps prevent order information, amounts, currencies, Merchant details, or service information from being substituted, tampered with, or improperly reused in the payment flow.

#### S4 Wallet Debit Pre-Verification
Before actually debiting the User's wallet account, the MPP **<font style="color:rgba(0, 0, 0, 0.88);">MUST </font>**perform a final verification of the expected payment instruction and debit outcome. This verification ensures that the final debit amount, payment currency, and cumulative amount still comply with the User's authorization. This is particularly important in multi-currency, price-change, or multiple-payment scenarios, where the final debit outcome can be different from the earlier transaction estimate. 

### Processing requirements
If any Intent Guard verification fails, the MPP **SHOULD** reject further processing of the relevant transaction or payment. The relevant flow **MUST NOT** proceed, including but not limited to: 

+ not completing Mandate authorization; 
+ not requesting or using a Payment Token;
+ not processing the payment request; and
+ not completing the wallet debit.

During status inquiry, rule validation, and result synchronization, Alipay+ **SHOULD** return the applicable status and rule validation results to assist the MPP and other participants in identifying the cause of verification failure. Based on the specific scenario, the Buyer Agent or MPP **MAY** present appropriate prompts to the User, such as:

+ The authorization has expired.
+ <font style="color:rgba(0, 0, 0, 0.88);">The amount exceeds the authorized budget limit.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The Merchant is outside the authorized scope.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The amount exceeds the permitted limit after currency conversion.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The Payment Token is invalid.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The order information is inconsistent with the authorized transaction.</font>

## Assurance Data Management<font style="color:#df2a3f;"> </font>
Alipay+ is responsible for defining and maintaining the relevant specifications of Assurance Data Management. This capability enables the <font style="color:rgba(0, 0, 0, 0.88);">capture, preservation, and verification of critical identity, authorization, and execution evidence across the agentic payment flow. </font><font style="color:rgba(0, 0, 0, 0.88);">It provides three-layer Assurance Data management, covering Assurance Data generation, verification, and evidence retention, to ensure that the data remains verifiable and traceable, thus supporting transaction dispute resolution, accountability determination, and auditability. </font>

The primary objective of this capability is to connect <font style="color:rgba(0, 0, 0, 0.88);">three critical elements—User wallet account binding, User intent authorization, and Agent transaction execution—into a verifiable, traceable, and auditable trust chain. This trust chain supports the integrity and trustworthiness of authorization and execution in AMP.</font>

<font style="color:rgba(0, 0, 0, 0.88);">This capability is designed to provide non-repudiation, traceability, and multi-party verifiability. It primarily addresses the following risks:</font>

+ <font style="color:rgba(0, 0, 0, 0.88);">Identity Trust: An Agent that has not completed the required identity onboarding or trust assessment impersonates a trusted Agent to initiate transactions.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Authorization Trust</font><font style="color:rgba(0, 0, 0, 0.88);">: A platform claims that the User has granted authorization, but other participants in the AMP network are unable to independently verify that claim.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Intent Authenticity</font><font style="color:rgba(0, 0, 0, 0.88);">: During transaction execution, an Agent </font><font style="color:rgba(0, 0, 0, 0.88);">hallucinates,</font><font style="color:rgba(0, 0, 0, 0.88);"> fabricates transaction details, tampers with order information, substitutes the Merchant, or modifies the transaction amount.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Execution Boundary Control</font><font style="color:rgba(0, 0, 0, 0.88);">: When the User is not present in real time, subsequent Agent operations exceed the authorization scope previously established by the User, resulting in uncontrolled permission expansion.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Accountability and Traceability: In the event of a dispute, it's difficult to determine whether the responsibility lies with the User, the Agent, the Merchant, or another participant in the transaction.</font>

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | <font style="color:rgba(0, 0, 0, 0.88);">Initiates wallet account binding, expresses transaction intent, and authorizes the applicable Mandate.</font> |
| <font style="color:rgba(0, 0, 0, 0.88);">Identity Signature Provider</font> | Serves as the core role responsible for providing signature endorsement of the User intent. After the User completes Mandate authorization, the ISP signs the User intent and completes the associated identity verification result using ISP Private Key, thus generating a tamper-resistant and verifiable Mandate proof. |
| Buyer Agent | <font style="color:rgba(0, 0, 0, 0.88);">Manages the Agent Private Key and signs relevant operations using that key.</font> |
| Alipay+ | <font style="color:rgba(0, 0, 0, 0.88);">Defines and maintains the rules for intent verification and Assurance Data management, manages public key registration, endorsement, and assurance records, publishes the Alipay+ Public Key for participants' access and signature verification, and stores and manages</font> <font style="color:rgba(0, 0, 0, 0.88);">ISP Public Key</font> <font style="color:rgba(0, 0, 0, 0.88);">and Agent Public Key.</font> |
| Merchant | <font style="color:rgba(0, 0, 0, 0.88);">Receives order requests and payment requests. The Merchant </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> verify the complete trust chain and confirm the trustworthiness of User intent before proceeding with subsequent order fulfilment and payment processing.</font> |


**<font style="color:rgba(0, 0, 0, 0.88);">Preconditions</font>**

<font style="color:rgba(0, 0, 0, 0.88);">Before this capability is invoked, the following requirements </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be met:</font>

+ <font style="color:rgba(0, 0, 0, 0.88);">The Identity Signature Provider, Buyer Agent, and Alipay+ have the required capabilities for key registration, distribution, and lifecycle management.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The Merchant has the required capability for verifying signatures. </font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ has the required capability for recording the signed Assurance Data.</font>

### Three-tier signing key trust model
<font style="color:rgba(0, 0, 0, 0.88);">AMP uses a three-tier asymmetric signing key trust model to establish a cryptographically verifiable chain of trust.</font>

| **<font style="color:rgba(0, 0, 0, 0.88);">Key type</font>** | **<font style="color:rgba(0, 0, 0, 0.88);">Holder</font>** | **<font style="color:rgba(0, 0, 0, 0.88);">Governance and registration</font>** | **<font style="color:rgba(0, 0, 0, 0.88);">Trust role</font>** |
| :--- | :--- | --- | :--- |
| <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ Key</font> | <font style="color:rgba(0, 0, 0, 0.88);">Alipay+</font> | <font style="color:rgba(0, 0, 0, 0.88);">Managed by Alipay+. The Alipay+ Public Key is made available to all participants under this protocol.</font> | <font style="color:rgba(0, 0, 0, 0.88);">Serves as the network-level root of trust. It is used to endorse trusted entities within the Alipay+ network and establish the protocol onboarding foundation.</font> |
| <font style="color:rgba(0, 0, 0, 0.88);">ISP Key</font> | <font style="color:rgba(0, 0, 0, 0.88);">Identity Signature Provider</font> | Generated and managed by the Identity Signature Provider. The ISP is responsible for ISP Key registration, usage, and private key storage. The ISP Public Key **MUST** be made available to Alipay+ for signature verification and trust validation.  | <font style="color:rgba(0, 0, 0, 0.88);">Used by the ISP to digitally attest that the User has completed the required identity verification and has authorized the relevant Mandate. The resulting signature provides verifiable evidence that the authorization originated from the User and was confirmed by a trusted ISP.</font> |
| <font style="color:rgba(0, 0, 0, 0.88);">Agent Key</font> | <font style="color:rgba(0, 0, 0, 0.88);">Agent</font> | Generated by or assigned to the Agent runtime.  The Agent Public Key **MUST** be registered with Alipay+. | <font style="color:rgba(0, 0, 0, 0.88);">Represents the Agent's execution authority under the protocol. It is used to sign specific transaction requests, providing verifiable evidence that the operation was initiated by the designated and authorized Agent.</font> |


### Three-layer Assurance Data generation
AMP leverages the [SD-JWT](https://datatracker.ietf.org/doc/html/rfc9901) protocol to generate Assurance Data across the following three layers of the payment flow: 

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784632859741-f72fcdaa-0ed4-46a1-bef2-2eb82f0050bc.png)

Figure 8. Three-layer Assurance Data

#### L1 User Identity Assurance Data
L1 provides assurance that the User has been authenticated by the Alipay+ payment network and is not a forged or impersonated identity, and that the wallet account binding was initiated and completed by the User. The Assurance Data generated at this stage includes the following:

+ **Signing Entity**: Alipay+ 
+ **Signing Stage**: User wallet account binding stage
+ **Signed Content**: The payload, signed in accordance with the applicable SD-JWT signing requirements  
+ **Signing Key**: Alipay+ Private Key  
+ **Evidence Custodian**: Alipay+

#### L2 Mandate Authorization Assurance Data
L2 provides assurance that the Agent's execution authority has been explicitly confirmed and authorized by the User, thereby establishing the authorization boundary for the Agent's actions and providing the basis for the subsequent Agent-initiated actions. The generated Assurance Data includes the following:

+ **Signing Entity**: ISP
+ **Signing Stage**: After the User completes Mandate authorization, the ISP signs the Mandate authorization result using the ISP Private Key. 
+ **Signed Content**: The payload, signed in accordance with the applicable SD-JWT signing requirements  
+ **Signing Key**: ISP Private Key  
+ **Evidence Custodian**: Alipay+

#### L3 Payment Token Request Assurance Data
L3 provides assurance that a specific transaction action was initiated by a specific Agent, thereby establishing a verifiable link between the transaction action and the User's authorization. The generated Assurance Data includes the following:

+ **Signing Entity**: Agent  
+ **Signing Stage**: Payment Token request stage, where the Agent requests a payment credential  
+ **Signed Content**: The payload, signed in accordance with the applicable SD-JWT signing requirements  
+ **Signing Key**: Agent Private Key  
+ **Evidence Custodian**: Alipay+

Depending on the payment scenario, the applicable Assurance Data generation requirements vary.

| **Scenario** | **Generation ** | **Verification and evidence retention** |
| --- | --- | --- |
| Scenario 1: Direct Payment (Human-Present) | L1 and L2 | L1 and L2 |
| Scenario 2: Delegated Payment (Human-Not-Present) | L1, L2, and L3 | L1, L2, and L3 |


Once generated, all L1, L2, and L3 Assurance Data is retained by Alipay+. Alipay+ **SHOULD** implement necessary data governance measures for all retained L1, L2, and L3 assurance evidence. The specific scope of retained evidence, retention period, access control requirements, and deletion mechanisms **MAY **be determined by Alipay+ in accordance with applicable laws and regulations, Alipay+ rules, and agreements with participants.

#### Assurance Data field details
The table below provides the details of the Assurance Data fields.

| **Stage** | **Category** | **Claim or field** | **Type** | **Must include** | **Description** |
| --- | --- | --- | --- | --- | --- |
| **L1** | Header | `alg` | string | **MUST** | Signing algorithm: `ES256` |
| | | `typ` | string | **MUST** | SD-JWT type: `sd+jwt` |
| | | `kid` | string | **MUST** | Issuer signing key ID |
| | Payload | `iss` | string | **MUST** | Issuer URI from Alipay+. This URI supports SD-JWT iss domain. |
| | | `sub` | string | **MUST** | User identifier |
| | | `iat` | integer | **MUST** | Issuance time |
| | | `exp` | integer | **MUST** | Expiration time, which must be set to a sufficiently long period.   |
| | | `cnf` | object | **MUST** | ISP Public Key used for binding ISP identity |
| | | `isp_type` | string | **MUST** | ISP identity type, e.g., `MPP` |
| | | `isp_name` | string | **MUST** | ISP identity name, e.g., `ALIPAY_HK`  |
| | | `_sd_alg` | string | **MUST NOT** | Disclosure signing algorithm: `sha-256` |
| | | `_sd` | array | **MUST NOT** | Disclosure hash array |
| **L2** | Header | `alg` | string | **MUST** | Signing algorithm: `ES256` |
| | | `typ` | string | **MUST** | SD-JWT type: `sd+jwt`; subject to extension |
| | | `kid` | string | **MUST** | ISP signing key ID. This string MUST match `cnf.kid` in L1 message. |
| | Payload | `nonce` | string | **MUST** | Random number for replay protection |
| | | `aud` | string | **MUST** | Verifier identifier |
| | | `iat` | integer | **MUST** | Issuance time |
| | | `exp` | integer | **MUST** | Expiration time |
| | | `sd_hash` | string | **MUST** | Binds to L1 |
| | | `idv_result` | string | **MUST** | ISP's identity verification result for the User |
| | | `idv_time` | string | **MUST** | Time when ISP completes User identity verification |
| | | `mode` | string | **MUST** | Supports `IMMEDIATE` and `AUTONOMOUS` |
| | | `_sd_alg` | string | **MUST** | Disclosure signing algorithm: `sha-256` |
| | | `_sd` | array | **MUST** | Disclosure hash array |
| | SD Disclosure | `intent` | object | **MUST** | Original intent information |
| | | `intent.raw` | string | **MUST** | Original intent |
| | | `intent.desc` | string | **MUST** | Original description |
| | | `token_info` | object | **MUST** | Payment Token information |
| | | `mandate_info` | object | **MUST** | Mandate authorization information |
| | Payload for `IMMEDIATE` Mandate | `cnf` | object | **MUST NOT** | Binds Agent Public Key |
| | SD Disclosure for `IMMEDIATE` Mandate | `intent.expiry_time` | string | **MUST NOT** | Intent expiration time |
| | | `intent.constraints` | object | **MUST NOT** | Delegated payment constraint information |
| | | `checkout` | object | **MUST** | Checkout information |
| | Payload for `AUTONOMOUS` Mandate | `cnf` | object | **MUST** | Binds Agent Public Key |
| | SD Disclosure for `AUTONOMOUS` Mandate | `intent.expiry_time` | string | **MUST** | Intent expiration time |
| | | `intent.constraints` | object | **MUST** | Delegated payment constraint information |
| | | `checkout` | object | **MUST NOT** | Checkout information |
| **L3** | Header | `alg` | string | **MUST** | Signing algorithm: `ES256` |
| | | `typ` | string | **MUST** | SD-JWT type: `sd+jwt` |
| | | `kid` | string | **MUST** | This string MUST match `cnf.kid` in L2 message. |
| | Payload | `nonce` | string | **MUST** | Random number for replay protection |
| | | `aud` | string | **MUST** | Verifier identifier: payment network URI |
| | | `iat` | integer | **MUST** | Issuance time |
| | | `exp` | integer | **MUST** | Expiration time |
| | | `sd_hash` | string | **MUST** | Binds to L2 |
| | | `_sd_alg` | string | **MUST** | Disclosure signing algorithm: `sha-256` |
| | | `_sd` | array | **MUST** | Disclosure hash array |
| | SD Disclosure | `checkout` | object | **MUST** | Selectively disclosed `checkout` information |
| | | `checkout.total_amount` | object | **MUST** | Selectively disclosed `checkout.total_amount` information |


### Three-layer Assurance Data verification and evidence retention
Alipay+ **MUST** verify the three-layer Assurance Data and durably retain the successfully verified Assurance Data.

<!-- 这是一张图片，ocr 内容为： -->
![](https://intranetproxy.alipay.com/skylark/lark/0/2026/png/161856449/1784632895560-78f52e6c-f5be-4dd8-b414-4137f354b7d7.png)

Figure 9. Three-layer Assurance Data verification

+ **<font style="color:rgba(0, 0, 0, 0.88);">L1 User Identity Assurance Data verification</font>**<font style="color:rgba(0, 0, 0, 0.88);">: After receiving a payment request, Alipay+ verifies the L1 User Identity Confirmation Assurance Data using the Alipay+ Public Key. This verification confirms that the ISP Public Key has been endorsed by Alipay+ and that the User identity has been verified by the Alipay+ payment network. Upon successful verification, Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> retain the verified L1 Assurance Data as verification evidence.</font>
+ **<font style="color:rgba(0, 0, 0, 0.88);">L2 Mandate Authorization Assurance Data verification</font>**<font style="color:rgba(0, 0, 0, 0.88);">: When the User authorizes the intent, the wallet guides the User through identity verification and Mandate authorization confirmation. After authorization is completed, the ISP signs the Mandate authorization result using the ISP Private Key, thus </font>generating the L2 Mandate Authorization Assurance Data<font style="color:rgba(0, 0, 0, 0.88);">, and submits the Assurance Data to Alipay+. Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> first verify the signature using the ISP Public Key and confirm that the </font>`sd_hash`<font style="color:rgba(0, 0, 0, 0.88);"> in the L2 message matches the L1 message hash result. Successful verification confirms that the Mandate authorization was completed by the User and the authorization content has not been tampered with. Upon successful verification, Alipay+ registers the Mandate as </font>`activated`<font style="color:rgba(0, 0, 0, 0.88);"> and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> retain the verified L2 Assurance Data as verification evidence.</font>
+ **<font style="color:rgba(0, 0, 0, 0.88);">L3 Payment Token Request Assurance Data verification</font>**<font style="color:rgba(0, 0, 0, 0.88);">: When requesting a Payment Token, the Agent signs the request using the Agent Private Key, and then submits the request with the L3 Payment Token Request Assurance Data to Alipay+ to exchange for a Payment Token. Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> first </font>verify the signature<font style="color:rgba(0, 0, 0, 0.88);"> using the Agent Public Key and confirm that the </font>`sd_hash`<font style="color:rgba(0, 0, 0, 0.88);"> in the L3 message matches the L2 message hash result. Successful verification confirms that the Payment Token request was initiated by the authorized Agent. After successful verification, Alipay+ issues the Payment Token and </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> retain the verified L3 Assurance Data as verification evidence.</font>

Depending on the payment scenario, the applicable Assurance Data verification and evidence retention requirements vary.

| **Scenario** | **Verification and evidence retention** |
| --- | --- |
| Scenario 1: Direct Payment (Human-Present) | L1 and L2 |
| Scenario 2: Delegated Payment (Human-Not-Present) | L1, L2, and L3 |


The Merchant **MAY** also perform verification of all three-layer Assurance Data for the transaction. After the <font style="color:rgba(0, 0, 0, 0.88);">L1, L2, and L3 verification succeeds, </font>the Merchant confirms that the order request is authentic and trustworthy, and requests the Acquirer to proceed with payment, debit, and order processing.

### Dispute resolution
<font style="color:rgb(0, 0, 0);">Alipay+ </font>**<font style="color:rgb(0, 0, 0);">MUST</font>**<font style="color:rgb(0, 0, 0);"> durably retain end-to-end Assurance Data from User identity binding through payment and settlement. Such retained Assurance Data serves as a single source of truth that is tamper-evident and authoritative for dispute resolution.</font>

<font style="color:rgb(0, 0, 0);">In the event of a transaction dispute, Alipay+ traces the cryptographic chain of trust to determine accountability, accurately identify the responsible entity, and impose protocol-level sanctions in accordance with the applicable Alipay+ rules. All participating entities </font>**<font style="color:rgb(0, 0, 0);">SHOULD</font>**<font style="color:rgb(0, 0, 0);"> cooperate in good faith by submitting relevant evidence and accepting the applicable arbitration outcomes.</font>

