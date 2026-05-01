# UI Refactor: Sidebar Layout & Dual-Mode Navigation

This plan outlines the transition from a top-navigation bar to a modern fixed-sidebar design, introducing a high-level toggle between **DASHBOARD (Live)** and **BACKTESTING (Simulated)**.

## User Review Required

> [!IMPORTANT]
> - The top navigation bar will be replaced by a left-oriented sidebar.
> - A major **Mode Switcher** will be added to the sidebar to pivot between the Live environment and the Simulated environment.
> - The application will land in **BACKTESTING (Simulation)** mode by default.
> - Topic pages (Security, Debate, Config, etc.) will be wrapped in a context that tells them whether to operate in "Live" or "Simulated" mode.

## Proposed Changes

### Core Architecture

#### [NEW] [AppModeContext.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/contexts/AppModeContext.jsx)
- Manage `activeMode` ('live' | 'backtest') and `activeTopic`.
- Provides a hook to detect if features should use free local models (Ollama) or mock data.

### Navigation & Layout

#### [MODIFY] [App.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/App.jsx)
- Redesign the layout with a fixed sidebar and a dynamic main content area.
- Add a high-visibility mode toggle in the sidebar.
- Implement routing logic that maps sidebar topics to components based on the `activeMode`.

### Component Adaptation

#### [MODIFY] [TradingDashboard.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/TradingDashboard.jsx) & [BacktestPage.jsx](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/frontend/src/pages/BacktestPage.jsx)
- Both will be accessible under the "Trading" topic.
- `TradingDashboard` shows in **Dashboard** mode.
- `BacktestPage` shows in **Backtest** mode.

#### [MODIFY] Other Topic Pages
- Topics like Strategy, Security, Debate Arena, etc., will remain identical in structure but will look for the `simulationMode` flag from the context.
- When `simulationMode` is active, UI will show "SIMULATION" indicators and actions will use free local logic.

## Open Questions

> [!WARNING]
> - For topics like **Security Scan**, should the "Backtest" version use a different backend endpoint, or just force the UI to use the free local models?
> - Are there any sections (like **Payments**) that should *only* be visible in one mode?
> - Where would you prefer the Theme Toggle (Light/Dark) to be placed in the new sidebar?

## Verification Plan

### Manual Verification
1.  Verify the sidebar is correctly rendered and fixed on the left.
2.  Switch between **DASHBOARD** and **BACKTESTING** modes via the toggle.
3.  Confirm that "Trading" switches correctly between the live dashboard and the backtesting engine.
4.  Verify that all other sidebar topic links work correctly and update the main content area.
5.  Check for visual consistency across themes.
