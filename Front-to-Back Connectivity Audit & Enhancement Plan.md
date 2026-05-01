# Front-to-Back Connectivity Audit & Enhancement Plan

This plan addresses the "missing" interactive elements identified in the audit, specifically focusing on the Decentralized Governance (MABC) system and the x402 wallet signing flow.

## User Review Required

> [!IMPORTANT]
> - **Interactive Governance**: I will transform the currently read-only Governance page into a full DAO Dashboard. Users will be able to create proposals, cast votes, and register as voters.
> - **x402 Wallet Simulation**: I will add a "Wallet Signing" simulation to the Trading and Payments flow to fulfill the "wallet signs USDC -> retry" requirement.

## Proposed Changes

---

### Backend Components

*No major backend changes required as the APIs already exist (mabc.py, vuln_scan.py, knowledge.py).*

---

### Frontend Components

#### [MODIFY] [GovernancePage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/GovernancePage.jsx)
- Implement **Proposal Browser**: Fetch and display active proposals from `/api/v1/mabc/proposals`.
- Implement **Voting Interaction**: Add "For/Against/Abstain" voting buttons that call `POST /api/v1/mabc/proposals/{id}/vote`.
- Implement **Voter Registration**: Add a modal/form to register the current wallet as a voter.
- Implement **Proposal Creation**: Add a form to submit new governance proposals.

#### [MODIFY] [TradingDashboard.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/TradingDashboard.jsx)
- Enhance the "Execute" flow with a **Mock Wallet Signature** step.
- When an execution requires x402, show a "Waiting for Signature..." overlay before sending the `X-Payment` header.

#### [MODIFY] [SecurityPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/SecurityPage.jsx)
- Enhance the display of "Model Consensus" in the scan results to explicitly show which models (GLM, Grok) agreed on each vulnerability.

## Verification Plan

### Automated Tests
- Verify that the Governance page correctly loads proposals from the backend.
- Verify that casting a vote updates the local state and sends the correct POST request.

### Manual Verification
- Create a proposal in the Governance page and verify it appears in the list.
- Trigger a trade and verify the "Wallet Signing" simulation appears before execution.
