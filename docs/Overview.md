## Why is an agentic mobile protocol needed?

### Rise of agentic commerce

Digital commerce is moving away from a model that requires Users to manually complete every step of a transaction toward one in which Users define goals and authorize an Agent to act on their behalf. In agentic commerce scenarios, an Agent may carry out key transaction-related functions, such as product discovery, order placement, payment execution, and fulfillment tracking, within Users' predefined goals and authorization limits, without requiring Users to remain continuously or immediately involved at every stage of the transaction.

### Existing trust gaps

Agentic commerce reshapes the trust assumptions on which traditional payment systems are built. Conventional payment flows are based on the premise that Users directly initiate transactions and confirm payments in real time, enabling merchants, payment institutions, and digital wallets to verify transaction intent and assign liability. In agentic commerce, transactions or related actions may be performed by an Agent within a pre-authorized scope on behalf of Users. This change introduces new trust challenges for all participants across the transaction chain:

- **Challenges in verifying Agent identity**: When a user authorizes an Agent to complete a transaction on their behalf, all parties in the transaction chain must be able to verify the Agent's identity and have assurance that the Agent satisfies the applicable trust requirements. This is necessary to determine whether the Agent is authorized and qualified to participate in the transaction flow.
- **Ambiguity in accountability**: When an Agent initiates transactions or payment requests on behalf of a user, a clear mechanism is needed to identify the principal it represents, define the scope of authorization, and allocate responsibility and liability accordingly.
- **Greater demands on execution fidelity**: In Agent-mediated transactions, the user may not be present to provide confirmations in real time for every transaction. Therefore, it is essential to ensure that the Agent's subsequent transaction and payment behavior remains consistent with the objectives, constraints, and execution boundaries originally defined by the user.
- **Increased reliance on traceable records for error handling and dispute resolution**: When disputes arise due to Agent misinterpretation, execution deviations, or a merchant's failure to deliver goods or services as agreed, all participants must be able to rely on standardized, verifiable record-keeping mechanisms to reconstruct the key steps from user authorization through payment completion, identify the root cause, and assign responsibility and liability accordingly.

In summary, agentic commerce requires not only adaptations at the payment interface level, but also a fundamental shift in the trust foundation underlying transactions. Trust can no longer rely solely on the user's real-time confirmation of operations; it must be communicated, conveyed, verified, and recorded across the relevant participants through a unified protocol framework.

### Introduction to Agentic Mobile Protocol

In traditional e-commerce and other online transaction scenarios, digital wallets have become an important payment interface within the electronic payment ecosystem, integrating Users' payment preferences, account and asset management functions, and broad merchant acceptance capabilities.

As agentic commerce evolves, there is a growing need for a new application-layer protocol framework that opens up digital wallet payment capabilities and is oriented toward Agent participation in transactions. Such a framework helps Users, Agents, digital wallets, Merchants, and other payment-related parties address authorization, security, execution, and accountability challenges arising from the shift in trust, under unified rules.

The Agentic Mobile Protocol (AMP) is an application-layer trust protocol designed for payment scenarios involving AI agents. This protocol standardizes the collaboration mechanisms and security boundaries among Users, Agents, Mobile Payment Providers, Merchants, Acquirers, and Credential Providers, ensuring that every payment transaction initiated or facilitated by an Agent is authorizable, executable, verifiable, and traceable.

This protocol is layered on top of existing payment networks, merchant systems, identity infrastructure, and clearing and settlement systems. It does not replace underlying payment infrastructure; instead, it defines a trust coordination mechanism for agentic transactions on top of such infrastructure. Under this unified protocol framework, Agent identities can be verified and trusted for admission, user authorization can be expressed and bounded in a structured manner, consistency between transaction execution and authorized intent can be verified, payment security controls can be applied, transaction execution can be traced and verified by assurance records, and thus liability can be assigned.

## Protocol scope

This protocol primarily **standardizes** the following:

- **Intent Trust**: Defines Agent identity admission standards, structured User Intent authorization credentials that Users can authorize and other participants can verify, and end-to-end intent guard to ensure that all Agent transaction behavior remains within user authorization boundaries.
- **Payment Services**: Defines the full payment-chain specifications covering wallet payment method binding, Payment Token request, payment acceptance, payment processing, result notification, and clearing and settlement, providing standardized process guidance for Agents during the payment execution phase.
- **Wallet Services**: Defines a range of wallet-side, customer-facing service capabilities, including Agent authorization management, visibility controls of tasks, delegation-limit controls, and dispute filing, to enhance Users' control over Agent-mediated transactions.

This protocol **does not standardize** the following:

- Specific interaction experiences between Agents and Users, including frontend interface design, natural language conversation methods, prompt engineering, and task orchestration strategies;
- Specific interaction experiences between Agents and Merchants, including order placing via the Merchant site or Merchant APIs;
- Merchant-side business-management rules, including product pricing, inventory management, order fulfillment, after-sales handling, and other non-payment operational details;
- Fund clearing and settlement rules of underlying payment infrastructure, such as interbank clearing cycles and fee structures;
- Risk-control models, anti-fraud algorithms, and internal review policies of individual institutions;
- Underlying network communication, infrastructure deployment, system operation and maintenance, and other technical implementation details outside the scope of application-layer trust collaboration, such as network protocol selection and server architecture;
- Agent frontend interaction styles, model inference processes, and underlying multimodal recognition algorithms;
- Specific wallet-side identity verification methods and signature implementation mechanisms;
- Payment-channel message specifications, clearing and settlement routing, and other payment processing logic;
- Specific wallet-side UI or UX designs for delegated-task management.

## Design principles

This protocol adheres to the following design principles:

- **Verifiable Intent**: The protocol emphasizes that payment trust should be built on explicit, non-repudiable proof of user intent rather than on inferences drawn by an Agent from user behavior or language. Through structured intent definitions and verification mechanisms, the risk of Agent misoperation or hallucination during delegated execution is mitigated, ensuring that transaction behavior is grounded in authentic, traceable, and tamper-proof intent.
- **Ecosystem Compatibility**: The protocol is designed with full consideration of compatibility with existing commercial systems and payment infrastructure, prioritizing designs that align with current standards, interfaces, and security mechanisms to reduce integration and transformation costs for all participants.
- **Openness and Interoperability**: The protocol is not bound to any specific platform, model, or technology stack, supports multiple implementation approaches, and enables diverse service providers to connect, ensuring that ecosystem participants can interoperate openly.
- **Security and Privacy First**: The protocol incorporates security controls and privacy protection mechanisms into its design, including but not limited to on-demand authorization, encrypted transmission, and trusted identity verification.

## Core concepts

| **Concept** | **Description** |
| --- | --- |
| **User Intent** | The objectives, preferences, conditions, and constraints expressed by a User for a specific commercial task. User Intent provides the basis for the Agent to interpret the task, initiate authorization, and conduct subsequent interactions. |
| **Trusted Authorization Surface** | A trusted interaction interface provided or recognized by Alipay+ or another non-agent entity. This interface displays authorization-related content to the User and carries out necessary identity verification, confirmation, or signature processes. The confirmation result obtained through a Trusted Authorization Surface is used to generate a Mandate credential, but the surface does not directly perform payment processing. To mitigate the risk that Mandate credential content is omitted, altered, or presented in a misleading manner, the surface **SHOULD NOT** be under the sole control of the Buyer Agent. |
| **Mandate** | A structured authorization credential that records the User's authorization target, authorization scope and boundaries, and required business information. A Mandate serves as a key basis for the Agent to conduct commercial interactions, apply for Payment Tokens, and support subsequent verification within the authorized scope. |
| **Alipay+ Token** | A payment account token generated and maintained by Alipay+. It indicates that the User has authorized binding a wallet payment method to a specific Agent, service scenario, or transaction. |
| **Payment Token** | A restricted-use credential generated by Alipay+ based on User authorization, the applicable Alipay+ Token, transaction information, and Alipay+ rules. A Payment Token is used to support payment processing for a specific transaction or authorized payment scenario. |
| **Payment Execution** | The end-to-end processing flow within the payment service module involving the Payment Tokens, payment requests, authorization verification, payment processing, funds debiting, and payment result notifications. |
| **Intent Guard** | A capability provided by Alipay+ to continuously verify subsequent transaction behavior against the authorization scope of a Mandate credential. Intent Guard is used to determine whether relevant interactions, credential requests, or payment processing activities remain consistent with the conditions authorized by the User. |
| **Identity Signature Provider Key (ISP Key)** | A trusted key capability provided by the Identity Signature Provider to support user identity verification and authorization signing. The ISP Key is used to sign Mandate authorization.<br/>The ISP Key consists of an ISP Private Key and an ISP Public Key. The ISP Public Key **MUST** be synchronized to Alipay+. |
| **Agent Key** | A trusted key capability used by an Agent to support identity authentication and request signing. When performing operations within the User's authorized scope, the Agent can use its Private Key to complete identity verification and sign requests. This proves that the operation was initiated by the designated Agent and ensures that the request has not been tampered with. <br/>The Agent Key consists of an Agent Private Key and an Agent Public Key. The Public Key **MUST** be synchronized to Alipay+. |
| **Alipay+ Key** | A trusted key capability used to endorse the identity of a trusted Alipay+ partner and establish the cryptographic basis for protocol admission. The Alipay+ Key is managed by Alipay+ and consists of an Alipay+ Private Key and an Alipay+ Public Key. The Alipay+ Public Key is available to all Alipay+ partners. |
| **Assurance Data** | Cryptographic data used in the protocol to demonstrate that a key action has been confirmed, authorized, or executed by the corresponding entity. Assurance Data typically contains the signed content, signature value, signing entity, associated Private Key, timestamp, and necessary contextual information. |
| **Know Your Agent (KYA)** | KYA means the mandatory due diligence and verification process undertaken on Agents, as well as sanction screening conducted in accordance with applicable anti-money laundering (AML) laws and sanctions. |

## Protocol participants and roles

The participants defined in this protocol reflect the allocation of responsibilities across authorization, credential management, payment processing, and trust governance in agentic commerce.

A single entity **MAY** perform one or more protocol roles depending on the applicable business scenarios. Where an entity performs multiple roles, it **SHOULD** satisfy the protocol obligations associated with each role. A participant **MAY** also delegate certain technical access, request forwarding, processing support, or operational support functions to a third-party service provider, provided that such delegation remains consistent with this protocol's requirements for authorization, credentials, payment processing, risk control, and dispute resolution.

**User**

The User is the initiator of the transaction and the source of authorization for using payment funds and executing transaction-related actions by an Agent on the User's behalf.

The User is responsible for expressing transaction objectives, constraints, and preferences, and for confirming the relevant intent. The level of User involvement may vary by payment scenario:

- **Direct Payment (Human-Present)**: The User is present in real time, participates in transaction confirmation at the time of purchase, and completes identity verification and payment confirmation through the digital wallet.
- **Delegated Payment (Human-Not-Present)**: The User may predefine specific transaction objectives and conditions and, upon confirmation, authorize the Agent to complete subsequent transactions within that defined scope and those boundaries.

**Agent**

An Agent is an automated execution entity that participates in the transaction flow. Acting on authorization from the principal it represents, an Agent may perform information processing, transaction negotiation, order preparation, payment request initiation, and result synchronization.

Under the AMP protocol, Agents are categorized as **Buyer Agents** or **Seller Agents** based on the principal they represent and their functional role in the transaction flow.

- **Buyer Agent**: A Buyer Agent represents the User in activities such as product or service discovery, comparison, order preparation, and payment initiation. Currently, AMP only supports Platform Agent.
  - **Platform Agent**: An Agent developed and operated by an enterprise or institution with appropriate legal and business qualifications, and made available to multiple Users. Platform Agents typically provide cross-scenario understanding, task coordination, and service invocation capabilities. ChatGPT is one example.
- **Seller Agent**: A Seller Agent represents a Merchant in processing and responding to requests related to goods or services, quotations, inventory, orders, and fulfillment within the transaction flow.

**Credential Provider (CP)**

The Credential Provider is a technical service provider that assists Agents in integrating with this protocol. It provides services between Agents and Alipay+, including protocol integration, request forwarding, structured intent submission, transfer of signature materials, initiation of Payment Token requests, and result synchronization.

**Alipay+**

Alipay+ serves as the core payment network infrastructure under this protocol. It connects protocol participants and provides standardized services for cross-participant authorization, credential management, payment processing, and trust governance.

Alipay+ primarily provides the following services:

- **Intent trust service**: Alipay+ manages structured intents and their authorization basis, provides network-level credential capabilities, including Alipay+ Tokens and Payment Tokens, and performs network-level verification at key stages such as credential request, payment acceptance, wallet balance debit, and dispute resolution. Alipay+ also works with digital wallets to provide Intent Guard, Assurance Data, and liability verification capabilities, supporting the execution and recording of transactions within authorized boundaries and ensuring traceability of Agent-initiated transactions.
- **Payment service coordination**: Within the payment chain, Alipay+ performs network connectivity and coordination functions. It connects Acquirers and digital wallets, routes payment and debit requests, returns payment results, and coordinates clearing and settlement processing.

**Merchant**

The Merchant is the provider of goods, services, or fulfillment capabilities and represents the supply side of agentic commerce interactions.

During the order placement stage, the Merchant provides the Buyer Agent with product or service information, quotations, and order confirmation results. After the transaction is concluded, the Merchant assumes the corresponding fulfillment, delivery, and after-sales service responsibilities.

During payment processing, the Merchant accesses the Alipay+ payment network through an Acquirer and initiates payment acceptance requests based on the Payment Token. The order, amount, and product or service information submitted by the Merchant serve as important business inputs for subsequent payment processing and bill presentation.

The responsibilities of the Merchant described above may be performed by a Seller Agent on the Merchant's behalf.

**Acquirer**

The Acquirer provides payment acceptance services to Merchants and assists Merchants in accessing the Alipay+ payment network.

Within the payment chain, the Acquirer is responsible for services including merchant onboarding, submission of payment requests, receipt of payment results, synchronization of order status, clearing and settlement, reconciliation, and dispute support.

**Mobile Payment Provider (MPP)**

The Mobile Payment Provider is the provider of the User's wallet-based payment method. It manages the User's source of funds and works with the Acquirer to support services such as digital wallet account binding, user identity verification, and payment debiting.

Under this protocol, in addition to processing payment requests, the Mobile Payment Provider **SHOULD** provide wallet payment-method binding, identity verification capabilities for high risk operations such as Mandate confirmation, and delegated task management capabilities.

**Identity Signature Provider (ISP)**

The Identity Signature Provider (ISP) is the signing party responsible for ISP Key management and Mandate authorization. The ISP issues and manages its own public or private key pair. After the User completes Mandate authorization, the ISP signs the authorization result to generate verifiable proof of Mandate authorization.

## Overall framework

### Framework architecture

This protocol is designed as a modular framework comprising three core domains: Intent Trust Domain, Payment Service Domain, and Wallet Service Domain. These domains interconnect to support the end-to-end transaction lifecycle, from user intent expression and payment credential generation to payment execution, authorization management, and result traceability.

In practice, relevant capabilities from different domains **MAY** be selected and combined based on the applicable business scenario, participant capabilities, and integration scope.

The capabilities described under each domain represent the core capability scope of the current protocol version. Specific object definitions, state transitions, field requirements, processing rules, and cross-domain reference relationships are governed by the corresponding domain specifications. The figure below provides an overview of the domains and capabilities supported in the current protocol version.

![Figure 1. AMP framework](images/Figure%201.%20AMP%20framework.png)

Figure 1. AMP framework

## Core domains and capabilities

### Intent Trust Domain

The **Intent Trust Domain** provides the authorization and trust foundation for the protocol. It converts the User's transaction intent into a structured Mandate that can be authorized, referenced, verified, and traced, while safeguarding the User's authorization boundaries throughout subsequent transaction flows.

This domain defines requirements and mechanisms for:

- **Agent Onboarding and Management**  
  Defines requirements for Agent identity verification, admission assessment, and trust establishment before an Agent is permitted to access the Alipay+ payment network.
- **User Intent and Mandate Management**  
  Defines how User intent is captured and converted into a structured Mandate that can be authorized, referenced, and verified; specifies the processes through which the User confirms a structured authorization credential, completes identity verification and signing, and generates the corresponding authorization result; and establishes the status management framework for Mandate throughout their lifecycle, including creation, activation, revocation, expiration, and closure.
- **End-to-End Intent Guard Management**  
  Defines the requirements for Alipay+ to continuously verify the User's authorization boundaries at key stages of the transaction lifecycle, including Mandate credential request, payment acceptance, and wallet debiting.
- **Trusted Intent Verification and Assurance Data Management and Dispute Resolution**  
  Defines requirements for recording, verifying, and retaining key authorization events, signatures, credentials, and payment execution results across the transaction chain. These trust records serve as evidence for liability assessment and dispute resolution.

### Payment Service Domain

The **Payment Service Domain** standardizes payment processing among Agents, Merchants, Acquirers, Alipay+, and Mobile Payment Providers. It covers wallet payment-method binding, Payment Token request, payment acceptance, wallet debiting, payment result notification, and clearing and settlement.

The primary capabilities of this domain include:

- **Wallet Payment Method Binding**  
  Defines the process by which a User authorizes the binding of a wallet payment method to an Agent or transaction scenario, resulting in an identifier that can be referenced for subsequent payments.
- **Payment Token Request**  
  Defines the process by which an Agent requests a Payment Token based on an authorization credential, Alipay+ Token, and applicable transaction context.
- **Payment Processing**  
  Defines the payment acceptance, debit request, result return, order status synchronization, and post-payment processes among Acquirers, Alipay+, and Mobile Payment Providers using the Payment Token in the Direct Payment (Human-Present) and Delegated Payment (Human-Not-Present) scenarios.

### Wallet Service Domain

The **Wallet Service Domain** standardizes wallet-side management capabilities provided to Users for authorization management, Agent task visibility, fund boundary configuration, and delegated limit control. Its purpose is to ensure that, after authorization is granted, Users can continue to view, manage, and control Agent-related authorization relationships, task execution, and fund usage through the wallet.

The primary capabilities of this domain include:

- **Delegated Task Management**  
  Defines how the wallet presents and manages authorized Agents, Mandate authorization credentials, task progress, budget consumption, payment results, and other extended User-facing capabilities.
- **Delegation Limit Management**  
  Defines the User's ability to configure amount limits, frequency limits, and other constraints associated with Agent delegated authorization through the wallet.

## Overarching guidelines

Refer to the following table to learn about normative key words in this document:

| **Key words** | **Constraint degree** | **Description** |
| --- | --- | --- |
| **MUST / SHALL / REQUIRED** | Extremely high | Requirements that must be met |
| **MUST NOT** | Extremely high | Requirements that must be prohibited |
| **SHOULD** | High | Actions that are strongly recommended to implement |
| **SHOULD NOT** | High | Actions that are strongly recommended to avoid |
| **MAY / OPTIONAL** | Low | Actions that are optional |

The above key words in this document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119.html) and [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174.html).
