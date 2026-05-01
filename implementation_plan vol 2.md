# Enhancing Frontend-Backend Integration

The current codebase features a robust backend suite (Governance, RAG, Vulnerability Scanning, x402 Payments), but the frontend UI primarily serves as a "thin client" for trading execution. This plan proposes a significant expansion of the frontend to expose and interact with these backend modules.

## User Review Required

> [!IMPORTANT]
> The expansion will add 4 new primary navigation items. This will significantly change the dashboard layout (switching from a horizontal top nav to a layout that can handle more items).

> [!NOTE]
> Some backend features (like Governance voting or Dispute resolution) are partially implemented or commented out in the backend. The UI will initially focus on "Read-only" status or "Trigger-based" actions (like scanning a contract).

## Proposed Changes

### [NEW] Components & Layout

#### [MODIFY] [App.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/App.jsx)
- Update navigation to include: Knowledge, Security, Governance, Payments.
- Refine layout if necessary to accommodate more links.

---

### [NEW] Knowledge Management (RAG)

#### [NEW] [KnowledgePage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/KnowledgePage.jsx)
- **Stats Dashboard**: Displays ChromaDB collection size, BM25 index status, and recent activity.
- **Ingestion UI**: A simple form/JSON-block editor to manually add documents to the KB.
- **Search Tester**: A dedicated interface to test Semantic vs. Hybrid retrieval results outside of a trade context.

---

### [NEW] Security & Vulnerability Scanning

#### [NEW] [SecurityPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/SecurityPage.jsx)
- **Scan History**: List of previously scanned contracts with their risk scores.
- **On-Demand Scan**: A code editor component to paste Solidity source code and trigger an Ensemble LLM scan (GLM-5.1 + Grok 4.20).
- **Findings Display**: Detailed breakdown of vulnerabilities (Category, Severity, Recommendation).

---

### [NEW] Governance & Compliance

#### [NEW] [GovernancePage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/GovernancePage.jsx)
- **Policy Status**: Display the current governance status, multisig threshold, and active policies.
- **Audit Logs**: A feed of recent "Proof-of-Thought" consensus events and governance-approved trades.

---

### [NEW] Payments (x402 Protocol)

#### [NEW] [PaymentsPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/PaymentsPage.jsx)
- **Pricing Table**: List of resource costs (RAG Query, Security Scan, Live Trade).
- **Payment Help**: Instructions on how to utilize the x402 protocol (USDC on Base).

## Open Questions

- **Knowledge Base Ingestion**: Should we support file uploads (PDF/TXT) or stick to JSON/Text input for this phase?
- **Security Scan**: Should the UI support scanning by Contract Address or stick to Source Code pasting for now?

## Verification Plan

### Automated Tests
- Run `npm run build` in `frontend` to ensure no syntax errors in new pages.
- Verify `frontend/src/App.jsx` connects to all new routes.

### Manual Verification
- Navigate through each new page and verify they pull real data from the backend (`/api/v1/knowledge/stats`, `/api/v1/vuln_scan/history`, etc.).
- Trigger a contract scan and verify the findings appear in the UI.
- Test document addition to the RAG knowledge base.
