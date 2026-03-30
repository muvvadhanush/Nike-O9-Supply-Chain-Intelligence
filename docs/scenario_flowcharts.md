# Nike Supply Chain Scenario Flowcharts - Hierarchical View

This document provides a hierarchical representation of the Nike Supply Chain Control Tower's parallel orchestration logic.

## 🏆 Master Orchestration Hierarchy
This diagram represents the core architectural pattern used for all scenarios (Demand Surge, Inventory Rebalancing, and Supplier Disruption).

```mermaid
flowchart TD
    ORC[Orchestrator]
    
    subgraph ParallelSense["Parallel Sensing & Response Layer"]
        direction TB
        ING["Ingestion Agent (ML)"]
        ANL["Analysis Agent (ML)"]
        SIM["Simulation Agent (ML)"]
    end
    
    ORC --> ING
    ORC --> ANL
    ORC --> SIM
    
    ING --> CLS[Scenario Context Classifier]
    
    CLS --> KPI[KPI & Regret Analysis]
    ANL --> KPI
    SIM --> KPI
    
    KPI --> GEN["Generated Options (LLM)"]
    GEN --> REC["Final Recommendations (LLM)"]
    
    style ORC fill:#000,color:#fff,stroke:#333,stroke-width:2px
    style ParallelSense fill:#f9f9f9,stroke:#ddd,stroke-dasharray: 5 5
    style REC fill:#007bff,color:#fff,stroke:#0056b3,stroke-width:2px
```

---

## 🌩️ Scenario 1: Demand Surge
Focuses on capturing consumer demand spikes and identifying logistics gaps.

```mermaid
flowchart TD
    ORC[Orchestrator]
    
    ORC --> ING["Signal Ingestion Agent (ML)"]
    ORC --> ANL["Signal Analysis Agent (ML)"]
    ORC --> SIM["Simulation Agent (ML)"]
    
    ING --> CLS[Demand Surge Classifier]
    
    CLS --> KPI[KPI & Regret Analysis]
    ANL --> KPI
    SIM --> KPI
    
    KPI --> OPT["Generated Options (LLM)"]
    OPT --> REC["Expedited Logistics (LLM)"]
```

---

## 📦 Scenario 2: Inventory Rebalancing
Optimization logic for redistributing stock across the DC network.

```mermaid
flowchart TD
    ORC[Orchestrator]
    
    ORC --> ING["Stock Ingestion Agent (ML)"]
    ORC --> ANL["Inventory Analysis Agent (ML)"]
    ORC --> SIM["Simulation Agent (ML)"]
    
    ING --> CLS[Inventory Rebalancing Classifier]
    
    CLS --> KPI[KPI & Regret Analysis]
    ANL --> KPI
    SIM --> KPI
    
    KPI --> OPT["Generated Options (LLM)"]
    OPT --> REC["LTL Transfer (LLM)"]
```

---

## 🚢 Scenario 3: Supplier Disruption
Mitigation strategies for production bottlenecks and factory delays.

```mermaid
flowchart TD
    ORC[Orchestrator]
    
    ORC --> ING["Supplier Dataset Load (ML)"]
    ORC --> ANL["Supplier Analysis Agent (ML)"]
    ORC --> SIM["Simulation Agent (ML)"]
    
    ING --> CLS[Supplier Disruption Classifier]
    
    CLS --> KPI[KPI & Regret Analysis]
    ANL --> KPI
    SIM --> KPI
    
    KPI --> OPT["Generated Options (LLM)"]
    OPT --> REC["Divergent Path (LLM)"]
```

---

## 🧬 Data Sourcing & Ingestion Pipeline
Granular view of the external and internal sensing layer.

```mermaid
flowchart TD
    subgraph Sources["Raw Data Sources"]
        Social[Social Media APIs]
        Weather[Weather & News]
        POS[Retailer POS (EDI)]
        ERP[SAP/o9 Inventory]
    end

    subgraph Preprocessing["Pre-Processing Layer"]
        Cleaning[Data Cleaning]
        Vector[NLP Vectorization]
        Norm[Min-Max Normalization]
    end

    subgraph Ingestion["Agent Ingestion Phase"]
        SIG["Signal Ingestion Agent (ML)"]
        INV["Inventory Ingestion Agent (ML)"]
    end

    Social --> Cleaning
    Weather --> Cleaning
    POS --> Vector
    ERP --> Norm

    Cleaning --> SIG
    Vector --> SIG
    Norm --> INV

    SIG --> OBJ_SIG[Signal Object]
    INV --> OBJ_INV[Inventory Objects]

    OBJ_SIG --> ORC[Orchestrator]
    OBJ_INV --> ORC[Orchestrator]
    
    style Sources fill:#f5f5f5,stroke:#333,stroke-dasharray: 5 5
    style Ingestion fill:#e1f5fe,stroke:#01579b
```
