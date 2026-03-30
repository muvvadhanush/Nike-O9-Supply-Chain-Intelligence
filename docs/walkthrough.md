# Nike Supply Chain Control Tower - Project Walkthrough

## Tiered Workspace Architecture

The codebase has been reorganized into a professional, tiered architecture to improve maintainability and strategic clarity:
- **`core/`**: Centralized API (`main.py`) and Orchestration logic.
- **`schema/`**: Unified Pydantic data models (`models.py`).
- **`agents/`**: Modular logic collective (Simulation, Recommendation, etc.).
- **`ui/`**: Frontend assets (`nike_algoleap_v2.html`, `favicon.svg`) and branding.
- **`docs/`**: Consolidated technical documentation, flowcharts, and asset captures.
- **`data/`**: Unified repository for all CSV and JSON supply chain datasets.

## Parallel Backend Orchestration
As requested, the primary agent layer now operates in parallel...

## Current System State

### 1. Ollama (Qwen 2.5) Integration
The recommendation engine has been enhanced for the **Qwen 2.5 (3B)** local model:
- **Optimization**: Increased generation timeouts to **60 seconds** to accommodate local CPU/GPU latency.
- **Robust Schema Parsing**: Implemented a flexible JSON parser that handles both raw lists and nested dictionary structures (e.g., `points`, `items`), ensuring the agent never fails due to non-deterministic model formatting.
- **Local Reasoning**: Strategic rationales and implementation roadmaps are now successfully pulled from your local instance.
- **Agent Mode**: The interface correctly displays "Ollama LLM V2" status.

### 2. Scenario Workspace Layout Refinement

I have optimized the Scenario tab for maximum visibility and dynamic interaction:
- **Expanded Height**: Primary panels (Agent Analysis & Execution Logs) are now set to **800px** for high-density log viewing.
- **Dynamic Reveal**: Panels now smoothly expand and fade in when the "Run Agent" process is initiated.
- **Secondary Row (Decision Support - Bottom)**:
    - **Scenario Description**: Bottom-left column.
    - **Generated Options**: Bottom-center (formerly "Generated Recommendations").
    - **Recommendations**: Bottom-right (formerly "AI Recommendation").
- **Identity**: Added the `favicon.svg` to the application header.

### 3. Verification & Stability
- **Parallel Backend**: Verified `concurrent.futures` implementation is stable.
- **Hierarchical Logic**: Updated all flowcharts in `scenario_flowcharts.md` to reflect the master orchestrator pattern.
- **Diagnostic Passed**: Final internal tests confirm the full pipeline (Ingest -> Classify -> Analyze -> Simulate -> KPI -> LLM) is passing with 100% success using the local qwen model.

---
> [!TIP]
> Your local Ollama server is fully integrated. If you encounter any latency, the expanded 800px window and 60s timeout ensure the system remains resilient and transparent.
