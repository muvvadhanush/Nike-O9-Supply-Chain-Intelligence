# Nike Supply Chain Control Tower - Technical Q&A Summary

This document consolidates all technical inquiries and expert responses provided during the parallel orchestration refactor.

---

> [!IMPORTANT]
> **Q1: Why is Ollama falling back to hardcoded reasoning / Why is it behaving like this?**

**Response**: 
The local **Qwen 2.5 (3B)** model was experiencing two primary hurdles:
1.  **Generation Latency**: Local CPUs/GPUs often take longer than 10-20 seconds to generate a full strategy, exceeding the initial timeout.
2.  **Schema Sensitivity**: As a 3B model, Qwen is non-deterministic in its JSON formatting. It would sometimes return a raw list or nest its points under different keys (e.g., `"items"` vs. `"points"`).
*   **Resolution**: I increased the timeout to **60 seconds** and implemented a **Flexible JSON Parser** in `recommendation.py` that dynamically identifies strategy lists regardless of the model's chosen JSON structure.

---

> [!IMPORTANT]
> **Q2: How is the Risk Factor and Monte Carlo Distribution calculated?**

**Response**: 
The Risk Distribution is a result of **Stochastic Stress-Testing**:
1.  **100 Iterations**: The `SimulationAgent` runs the scenario 100 times.
2.  **Stochastic Jitters**: In each run, it applies random Gaussian noise to the inputs (±4% Cost, ±1.2d Lead Time, ±3% Risk).
3.  **ML Scoring**: A **Random Forest Regressor** predicts the score for each "jittered" attempt.
4.  **Distribution**: The "Risk Factor" shown in the UI (Min/Max/Std Dev) is the statistical spread of these 100 outcomes, showing how vulnerable a plan is to real-world randomness.

---

> [!IMPORTANT]
> **Q3: What exactly is the Classifier Task in the program?**

**Response**: 
The **Use Case Classifier** acts as the "Intelligence Bridge." Its role is to:
1.  **Context Identification**: Analyze ingested signals to determine if the event is a `DEMAND_SURGE`, `INVENTORY_REBALANCING`, or `SUPPLIER_DISRUPTION`.
2.  **Sequential Synchronization**: In the parallel architecture, it's the "trigger" that tells the downstream KPI and Recommendation agents which scenario-specific rules and thresholds to apply.

---

> [!IMPORTANT]
> **Q4: Can you provide a "Paper Model" for the calculation of one item (SKU: NK-AM-002)?**

**Response**: 
*   **Initial Gap**: We have 3,376 units, but the Safety Stock target is 3,895. **Current Deficit = 519 units**.
*   **Surge Volume**: Signal Intensity of 0.80 means an uplift of **3,116 additional units** ($3,895 \times 0.80$).
*   **Total Deficit**: $519 + 3,116 = 3,635$ units.
*   **Risk Ratio**: $3,635 \div 3,895 \approx 0.93$.
*   **Decision logic**: Since $0.93 > 0.70$ (threshold), the system selects **Priority Air Express**.

---

> [!IMPORTANT]
> **Q5: Which specific algorithms are used by each ML Agent?**

**Response**: 
*   **Simulation Agent**: **Random Forest Regressor** + **Monte Carlo Simulation**.
*   **Statistical Agent**: **Kolmogorov-Smirnov (KS-Test)** for anomaly confirmation + **Regret Analysis** for decision quality.
*   **Inventory Analysis**: **Min-Max Delta Algorithm** for node-to-node stock rebalancing.
*   **Classifier Agent**: **Heuristic Weighted Logic Gates** (calculating confidence based on signal intensity/history).

---

> [!IMPORTANT]
> **Q6: How is the Intensity (0.80) legally obtained and what is the equivalent industry metric?**

**Response**: 
1.  **Legal Sourcing**: Instead of illegal scraping, enterprise-grade systems use **Authorized API Firehoses** (e.g., Google Trends, Brandwatch) and **EDI 852 Transactions** from retailers (direct store-level sales data).
2.  **Equivalent Industry Metric**: The "Intensity" index is the business name for a **Demand Volatility Z-Score** or **Coefficient of Variation (CV)**. It measures how many standard deviations the current demand signal sits above the historical mean.

---

> [!IMPORTANT]
> **Q7: How is the Description Box data presented?**

**Response**: 
The description is a **Dynamic Template**:
1.  **Backend**: `orchestration.py` generates a JSON packet containing the narrative (`ctx`) and metadata badges (Region, Risk, SKU) based on live CSV data.
2.  **Frontend**: The JavaScript `selectScenario()` function "injects" this JSON into stylized HTML, creating the blue-and-grey badge layout you see when you click a scenario.
