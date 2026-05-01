# Completing the Agent Lifecycle: Monitoring & Adjustment

This plan completes the "Onchain" model by adding the two missing phases of the agent lifecycle: **Observability (Monitoring)** and **Reactivity (Adjustment)**.

## User Review Required

> [!IMPORTANT]
> - **Linear vs Continuous Monitoring**: In this phase, I will implement **In-Graph Monitoring Strategy**. This means the agents will specify *how* the trade should be monitored (e.g., specific trailing stop-loss logic) after execution.
> - **Autonomous Adjustment**: The adjustment node will specify the "Exit Strategy Override" — conditions under which the agents will automatically close the position.

## Proposed Changes

---

### Backend Components

#### [MODIFY] [trading_graph.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/agents/trading_graph.py)
- **New Agent Roles**:
    - `MONITOR_SYSTEM`: Specialises in tracking position health and setting dynamic trailing logic.
    - `ADJUST_SYSTEM`: Specialises in "Early Exit" and "Risk Mitigation" logic.
- **New Graph Nodes**:
    - `monitor_node`: Formulates the monitoring strategy for the active trade.
    - `adjust_node`: Specifies the adjustment/exit conditions.
- **Assembly**: Update the graph flow: `execute` → `monitor` → `adjust` → `END`.

#### [MODIFY] [api/eaac.py](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/backend/app/api/eaac.py)
- Update the Coordination API to track these two new phases for frontend visualization.

---

### Frontend Components

#### [MODIFY] [DebateArenaPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/DebateArenaPage.jsx)
- Update the **Proof-of-Thought Timeline** to include "Monitoring" and "Adjustment" steps.
- Add new visual cues for "Trailing Logic" defined by the agents.

#### [MODIFY] [TradingDashboard.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/TradingDashboard.jsx)
- Add a "Trade Strategy" summary in the result panel showing the Monitoring/Adjustment rules.

## Verification Plan

### Automated Tests
- Run a simulation and verify that the graph completes all 6 nodes (Planner, Verifier, Controller, Execute, Monitor, Adjust).
- Verify the final JSON response contains `monitoring_strategy` and `adjustment_logic` fields.

### Manual Verification
- Verify the Debate Arena timeline correctly visualises the 6-stage lifecycle.
- Confirm the Dashboard result panel displays the "Observability" instructions from the agents.
