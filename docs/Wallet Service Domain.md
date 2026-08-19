## Overview
The Wallet Service Domain is a user-facing value-added service and risk management domain of <font style="color:rgba(0, 0, 0, 0.88);">the Agentic Mobile Protocol (AMP).</font> I<font style="color:rgba(0, 0, 0, 0.88);">t is delivered through the Mobile Payment Provider's wallet app and provides Users with services related to agentic payments, including authorization relationship management, delegated task inquiry and control, delegation limit configuration, and dispute resolution. The Wallet Service Domain aims to strengthen the User's visibility, control, and sense of security in agentic commerce. By enabling Users to monitor, manage, and adjust delegated payment activities through their wallets, this domain helps improve User understanding of, and trust in, agentic payments.</font> 

## Scope of responsibility
This Wallet Service Domain covers the following:

+ Inquiry and management of delegated tasks associated with a Mandate.
+ User-side management of delegation limits within the wallet.
+ Management of additional wallet-side services related to agentic payments.

## Capability list
| **Capability** | **Description** |
| :--- | --- |
| Delegated Task Management | Enables the User to view the list of authorized Agents, Mandate history, execution progress, budget consumption, and subtask information. It also supports task cancellation, budget adjustment, and other extended management capabilities. |
| Delegation Limit Management | Enables the User to set, modify, or clear authorization limits, including the limit for a single Mandate and the cumulative daily delegation limit. |


## Delegated Task Management
<font style="color:rgba(0, 0, 0, 0.88);">The Delegated Task Management capability enables Users to view and manage Agent authorization relationships, Mandate authorization records, delegated task execution status, and payment result bills in agentic payment scenarios. Through the wallet app, the User can view the list of authorized Buyer Agents bound to the User's wallet account, the Mandate history associated with each Buyer Agent, and the details of a single Mandate, including execution progress, validity period, budget utilization, subtasks, and related transaction records or bills.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The objective of this capability is to ensure that Users can view and control the activities they delegate to an Agent. Based on the User's authorization and wallet account, the Mobile Payment Provider (MPP) </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> retrieve relevant information associated with the User, including Agent authorization relationships, Mandate data, payment results, and necessary task execution information, and present such information to the User. The information </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be presented in a clear, user-understandable manner.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The Delegated Task Management capability </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be implemented and provided within the wallet app by Alipay+, the MPP, or other non-Agent entities. The specific customer-facing user interface is not prescribed; however, the relevant inquiry services and task-control capabilities </font>**<font style="color:rgba(0, 0, 0, 0.88);">MUST</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be made available to the User.</font>

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Views and manages the tasks delegated by the User to an Agent, authorization relationships, and Mandate records. |
| Mobile Payment Provider (MPP) | Provides the User with wallet-side access to view and manage authorization relationships and task records. |
| Alipay+ | Provides Mandate status, authorization records, payment results, budget consumption, and related credential records. For bill and order display, the MPP **MAY** also serve as a data source for relevant order information and payment results. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The User has completed identity verification or login authorization on the wallet side.
+ The User has authorized and bound at least one Buyer Agent, or at least one Mandate record associated with the User already exists.
+ Alipay+ can retrieve relevant authorization and payment records based on the User identity, Buyer Agent identity, and Mandate identifier.
+ <font style="color:rgba(0, 0, 0, 0.88);">I</font><font style="color:rgba(0, 0, 0, 0.88);">f bill or order information is displayed, the corresponding order or payment result has reached a final state and is available as a queryable record.</font>

### Authorized Agent and Mandate display
<font style="color:rgba(0, 0, 0, 0.88);">The MPP </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> enable the User to view the list of Buyer Agents that have been authorized and linked to the User's wallet account. Each Buyer Agent </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be associated with historical Mandate records created or authorized under that Agent.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The Mandate list</font><font style="color:rgba(0, 0, 0, 0.88);"> </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font><font style="color:rgba(0, 0, 0, 0.88);">help the User understand the current status of each authorization or delegation. The list</font><font style="color:rgba(0, 0, 0, 0.88);"> </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font><font style="color:rgba(0, 0, 0, 0.88);">display information such as the Mandate description, execution status, validity period, total budget, consumed budget, budget utilization ratio, and an entry point for viewing further details. The specific display fields</font><font style="color:rgba(0, 0, 0, 0.88);"> </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> </font><font style="color:rgba(0, 0, 0, 0.88);">be extended based on the applicable business scenario, Mandate type, and Alipay+ rules.</font>

<font style="color:rgba(0, 0, 0, 0.88);">The user-facing copywriting on the wallet app of a Mandate </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD </font>**<font style="color:rgba(0, 0, 0, 0.88);">be mapped from the defined Mandate status as follows:</font>

| **Mandate status** | **Wallet display copy recommendations** | **Description** |
| --- | --- | --- |
| `activated` | Agent processing | The wallet app **MAY **display execution progress, validity period, budget usage, and an entry point for task cancellation. |
| `finished` | Closed | The wallet app **MAY **display final execution progress, related bills, and budget consumption results. Historical details** MAY** be retained. |
| `revoked` | Cancelled | Execution progress is no longer displayed. Historical details** MAY** be retained. |
| `expired` | Expired | Execution progress is no longer displayed. Historical details** MAY** be retained. |


The above copy recommendations are for reference only. The MPP **MAY** change the customer-facing wording to align with its product design and localization requirements, provided that such wording **MUST NOT** alter the original semantics of the Mandate states defined in this protocol.

### Mandate task execution detail display
The User **MAY** access the details of a single Mandate through the wallet app. The Mandate details **<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> help the User understand the authorization scope, execution progress, budget utilization, and payment results associated with the Mandate.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Mandate task execution details </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> include, but are not limited to, the following information:</font>

+ Mandate description
+ Mandate status
+ Validity period
+ Total budget
+ Consumed budget
+ A list of related payment orders or transaction records

### Payment bill display
The bill or order list is used to present transaction records for delegated tasks associated with a Mandate that have entered the payment processing flow.

Alipay+ **MAY** generate order or billing information based on records from the payment processing flow, associate such information with one or more billing records under the delegated task corresponding to the Mandate of a specific Agent, and provide the relevant data to the MPP for display in the wallet app. 

Order display information **MAY** include, but is not limited to, the following:

+ Transaction time
+ Task or order description
+ Payment currency
+ Payment amount
+ Order status

### Mandate control
Mandate control enables the User to perform cancellation, limit adjustment, and other supported actions on a Mandate in `activated` status.

#### Mandate cancellation
Mandate cancellation mainly applies to Mandates in `activated` status. After the User confirms the cancellation, the MPP **SHOULD** submit a cancellation request to Alipay+, which then completes the Mandate status update and performs the relevant interception process.

Upon successful cancellation, the Mandate **SHOULD** transition to `revoked` status, after which Alipay+ **SHOULD NOT **issue new Payment Tokens based on the Mandate, and **SHOULD NOT** accept any subsequent payment requests initiated under the Mandate. 

The wallet app **MAY** continue to display the historical details of the Mandate and payment results that have already occurred. Canceling a Mandate only terminates further execution and payment processing. By default, it does not automatically reverse completed payments, fulfillment activities, or refund processes.

#### Limit adjustment
Mandate limit adjustment mainly applies to Mandates in `activated` status. Depending on the task execution status, the User **MAY** independently increase or decrease the limit of the current Mandate to maintain control over and enhance the security of fund expenditure.

### Supplemental extended capabilities
The Delegated Task Management capability **MAY** be further extended to support the following functions:

+ **Personalized service recommendations**: Based on the User's Mandate authorization scope, historical transaction behavior, account preferences, usage scenarios, and other relevant information, the wallet app **MAY** recommend financial or value-added services that are more suitable to the User. Such services **MAY **include bill reminders, automatic repayment, budget management, promotional offers, or other benefits. These recommendations are intended to enhance the User experience and improve service engagement and conversion.
+ **Expenditure analysis report generation**: <font style="color:rgba(0, 0, 0, 0.88);">The wallet app </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> categorize, aggregate, and analyze expenditure data generated within the Mandate authorization scope, and generate periodic expenditure reports for the User. Such reports </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> include total expenditure, spending categories, year-over-year and month-over-month changes, abnormal spending alerts, and other relevant insights. These reports help Users better understand their fund flows and spending patterns.</font>
+ **Fulfillment information monitoring**: <font style="color:rgba(0, 0, 0, 0.88);">The wallet app </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> continuously monitor the execution of tasks, services, or agreements associated with a Mandate. Monitoring items </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> include the following:</font>
    - <font style="color:rgba(0, 0, 0, 0.88);">whether a debit was successful</font>
    - <font style="color:rgba(0, 0, 0, 0.88);">whether the relevant service was fulfilled as agreed</font>
    - <font style="color:rgba(0, 0, 0, 0.88);">whether the authorization remains valid</font>
    - <font style="color:rgba(0, 0, 0, 0.88);">whether any failure or abnormal condition has occurred</font>

<font style="color:rgba(0, 0, 0, 0.88);">Through such monitoring mechanisms, fulfillment risks can be identified in a timely manner, and reminders, retries, suspensions, or manual interventions are provided where appropriate.</font>

+ **One-click appeal or dispute entry**: <font style="color:rgba(0, 0, 0, 0.88);">The wallet app </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> p</font>rovide Users <font style="color:rgba(0, 0, 0, 0.88);">with a convenient entry point for submitting appeals, objections, or dispute feedback. If the User has questions or concerns regarding a Mandate-related debit, service fulfillment, authorization usage, or abnormal transaction, the User can initiate an appeal through this entry point. The wallet app </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> automatically associate the relevant task, transaction, and authorization information with the appeal to improve issue-handling efficiency and strengthen User trust.</font>

### Processing requirements
When using the Delegated Task Management capability, the following processing requirements **SHOULD** be met:

+ The Mandate status, budget consumption, and payment results displayed by this capability **SHOULD** be based primarily on records maintained by Alipay+.
+ Before the User initiates revocation of a Mandate, the MPP **SHOULD** clearly inform the User of the expected impact of the cancellation.
+ Orders for which payment has been completed and that require refund, after-sales, or dispute resolution **SHOULD** be handled in accordance with the applicable rules of the Merchant, Acquirer, MPP, and Alipay+.
+ The MPP **SHOULD **maintain basic visibility of a Mandate for the User. Even after a Mandate has been canceled, expired, or closed, the User **SHOULD** still be able to view historical authorizations, execution records, billing or transaction results, and necessary status descriptions.

## Delegation Limit Management
The Delegation Limit Management capability is used in agentic payment scenarios to enable the User to set and manage delegation limits for Mandates within the wallet app. <font style="color:rgba(0, 0, 0, 0.88);">This capability helps the User apply fund control constraints to the budget for the delegated tasks that </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> be initiated or generated by an Agent.</font>

<font style="color:rgba(0, 0, 0, 0.88);">Based on the User's own risk preference, the User </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> set an authorization limit for a single Mandate and a daily cumulative delegation limit. The User </font>**<font style="color:rgba(0, 0, 0, 0.88);">MAY</font>**<font style="color:rgba(0, 0, 0, 0.88);"> also modify or clear delegation limits through the wallet app. Any modified limit rules apply only to Mandates that will be created or authorized later. They do not affect Mandates that have already been authorized.</font>

### Main participants and preconditions
**Main participants**

| **Participant** | **Responsibility in this capability** |
| --- | --- |
| User | Sets and manages delegation limits for Mandates. |
| Mobile Payment Provider (MPP) | Provides the User with the ability to set, modify, clear, and save delegation limits, and synchronizes limit rules to Alipay+ or makes them available for query by Alipay+. |
| Alipay+ | Performs limit validation during Mandate creation or authorization. |


**Preconditions**

Before this capability is invoked, the following preconditions **SHOULD** be met:

+ The User has completed identity verification or login authorization on the wallet side.
+ <font style="color:rgba(0, 0, 0, 0.88);">The wallet app can maintain the corresponding delegation limit rules based on the User's wallet identity.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ can obtain or query the limit rules set by the User.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">The Buyer Agent or Credential Provider (CP) can receive the limit validation result from Alipay+ during Mandate creation or authorization.</font>
+ <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ can perform limit validation based on the User, Agent, and Mandate information.</font>

### Limit types
The MPP **MAY** enable Users to set the delegation limit, including but not limited to the following:

| **Limit type** | **Customer-facing name** | **Definition** | **Currency** | **User configurable** |
| --- | --- | --- | --- | --- |
| Single-Mandate Authorization Limit | Per-task Budget Limit | The maximum budget amount that can be authorized for a single Mandate. The user **MAY** confirm the per-task budget limit via natural language input or other supported interaction methods. | Wallet currency | Yes |
| Single-Day Cumulative Delegation Limit | Daily Agent Spending Limit | The maximum aggregate amount that a User authorizes an Agent to spend under Mandates within a single day. | Wallet currency | Yes |


Additional control dimensions **MAY** be extended in the future to support more personalized customer preferences and risk-management requirements.

### Processing requirements
When using the Delegation Limit Management capability, the following processing requirements **SHOULD** be met:

+ Alipay+ **SHOULD** validate the delegation limits set by the User during Mandate creation or authorization. The limit validation result **SHOULD** serve as evidence to determine whether the Mandate is permitted to be created or authorized.
+ If the User has set a single Mandate authorization limit, the budget amount of the current Mandate **MUST NOT** exceed that limit. If the limit is exceeded, <font style="color:rgba(0, 0, 0, 0.88);">Alipay+ </font>**<font style="color:rgba(0, 0, 0, 0.88);">SHOULD</font>**<font style="color:rgba(0, 0, 0, 0.88);"> reject the Mandate creation or authorization request and return the corresponding validation result.</font>
+ If the User has set a single-day cumulative delegation limit, the sum of the current Mandate budget and the User's cumulative delegated amount for the same day **MUST NOT **exceed the daily limit. If the daily limit is exceeded, Alipay+ **SHOULD** <font style="color:rgba(0, 0, 0, 0.88);">reject the Mandate creation or authorization request and return the corresponding validation result.</font>
+ If limit validation fails, the Agent **SHOULD** display the rejection reason returned by Alipay+ to the User and guide the User to adjust the current Mandate budget or modify the corresponding limit on the wallet app before re-initiating the process.

