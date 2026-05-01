# Update install.md with Today's Systemic Upgrades

This plan will update the central documentation to reflect the major architectural and functional shifts made today.

## User Review Required

> [!IMPORTANT]
> - **Unified Documentation**: I will update all diagrams (Architecture, Execution Flow) to reflect the new 6-stage lifecycle: **Perceive → Plan → Verify → Act → Monitor → Adjust**.
> - **Model Strictness**: I will document the exclusion of Claw402 and the strict enforcement of the primary reasoning models (Grok, GLM, MiniMax).

## Proposed Changes

---

### Documentation Components

#### [MODIFY] [install.md](file:///Users/ptpkjhrt/Documents/AI%20Agent%20In%20Blockchain%20Trading/install.md)
- **Architecture Overview**: Update the ASCII diagram and the Agent Roles table to include **Monitor** and **Adjuster** agents.
- **Model Circles**: add a section on strictly enforced trading and backtesting model circles.
- **Execution Flow**: Redraw the execution flow to show the "Observability" and "Reactivity" loops.
- **New Features**: Document the **Strategy Page** (Rule Builder) and **FAQ Page** (Education center).
- **API Reference**: Add documentation for the new `Strategy` and `FAQ` endpoints/routes.

## Verification Plan

### Manual Verification
- Verify that all internal links in `install.md` remain valid.
- Verify that the new diagrams accurately represent the code in `trading_graph.py`.
- Final proofread for clarity and professional tone.
